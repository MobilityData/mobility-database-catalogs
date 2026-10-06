"""
California GTFS Shared-Stop Toolkit: main workflow.

Data flow (beginning to end):
  1. Find the newest warehouse run that has all three required CSVs.
  2. Source preparation: map pair endpoints to stop records, copy the GTFS
     stop fields into the GTFS_ interface fields, create agency_name.
  3. Source cleaning: alias normalization, regional duplicate / precursor /
     rail-only exclusions, exact cross-feed duplicates (audit CSV written).
  4. Pair scoring, pass 1: find groups that need served-shape context.
  5. Served-shape context for that cohort -> BoardingSide per stop.
  6. Pair scoring, pass 2 (final): BoardingSide can adjust same-direction pairs.
  7. Physical-location analysis and existing-point recommendation.
  8. Road context (Caltrans All Roads) - context and tie-break only.
  9. Served-shape context on the final groups + two-agency recommendations.
 10. QA products, headline CSVs, geodatabase layers, run manifest.

Both final map layers contain every in-scope cleaned statewide stop. Records
excluded by the source-cleaning rules are written to an audit CSV. No
synthetic stop coordinates are created.
"""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math
import os
import re

import pandas as pd

from . import pair_scoring
from .recommendation import run_recommendation_issue_analysis
from .road_context import run_road_context
from .shape_context import run_served_shape_context

# Source-cleaning reference tables. Keeping these values in CSV files makes
# feed/operator mappings and exclusion rules reviewable without editing Python.
config_dir_default = Path(__file__).resolve().parent / "config"

# Served-shape cache files accepted when external-context queries are disabled.
offline_shape_cache_names = (
    "shared_stop_shape_context_shapes_complete_{stamp}.csv",
    "shared_stop_shape_context_shapes_base_{stamp}.csv",
)
road_cache_feature_class = "Caltrans_All_Roads_GTFS_Context_{stamp}"


def _clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def _normalize_text(v):
    return " ".join(_clean(v).lower().split())


def _read_config_table(config_dir, basename):
    path = Path(config_dir) / basename
    if not path.exists():
        raise FileNotFoundError(f"Required config file not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


status_label_categories = ("recommendation_reason", "route_evidence", "shape_context", "road_context")
source_exclusion_types = ("regional_feed", "rail_route_type")


def _require_config_columns(tbl, required, name):
    missing = required - set(tbl.columns)
    if missing:
        raise ValueError(f"{name} is missing column(s): " + ", ".join(sorted(missing)))


def _load_agency_aliases(config_dir):
    """Return feed-name to agency-label mappings used during source cleaning.

    Every row needs both a feed_name and an agency_name, and each feed_name may
    appear only once, so a typo or a pasted duplicate stops the run instead of
    quietly changing which label a feed gets.
    """
    name = "agency_aliases.csv"
    tbl = _read_config_table(config_dir, name)
    _require_config_columns(tbl, {"feed_name", "agency_name"}, name)
    aliases = {}
    for i, r in tbl.iterrows():
        feed, agency = _clean(r["feed_name"]), _clean(r["agency_name"])
        if not feed and not agency:
            continue
        if not feed or not agency:
            raise ValueError(f"{name} row {i + 2}: feed_name and agency_name are both required")
        if feed in aliases:
            raise ValueError(f"{name}: feed_name '{feed}' appears more than once")
        aliases[feed] = agency
    print(f"[config] {name}: {len(aliases)} row(s) loaded from {Path(config_dir) / name}")
    return aliases


def _load_source_exclusions(config_dir):
    """Return feed and route-type exclusions used to define the curbside source.

    exclusion_type must be one of source_exclusion_types. An unknown type (for
    example a misspelling) stops the run, because silently ignoring it would
    switch that exclusion off.
    """
    name = "source_exclusions.csv"
    tbl = _read_config_table(config_dir, name)
    _require_config_columns(tbl, {"exclusion_type", "value"}, name)
    found = {t: set() for t in source_exclusion_types}
    for i, r in tbl.iterrows():
        kind, value = _clean(r["exclusion_type"]), _clean(r["value"])
        if not kind and not value:
            continue
        if kind not in found:
            raise ValueError(
                f"{name} row {i + 2}: unknown exclusion_type '{kind}'. "
                f"Use one of: {', '.join(source_exclusion_types)}"
            )
        if not value:
            raise ValueError(f"{name} row {i + 2}: value is blank")
        if kind == "rail_route_type" and not value.isdigit():
            raise ValueError(
                f"{name} row {i + 2}: rail_route_type '{value}' is not a GTFS route_type number"
            )
        if value in found[kind]:
            raise ValueError(f"{name}: {kind} '{value}' appears more than once")
        found[kind].add(value)
    for kind, values in found.items():
        if not values:
            print(f"[config] WARNING: {name} has no {kind} rows; that exclusion will remove nothing")
    print(f"[config] {name}: {sum(len(v) for v in found.values())} row(s) loaded from {Path(config_dir) / name}")
    return found["regional_feed"], found["rail_route_type"]


def _load_status_labels(config_dir):
    """Return plain-language labels for internal status codes, keyed by (category, code).

    The internal codes stay as written by the analysis; this table only controls
    the wording people see. Unknown categories, blank labels, and duplicate
    codes stop the run.
    """
    name = "status_labels.csv"
    tbl = _read_config_table(config_dir, name)
    _require_config_columns(tbl, {"category", "code", "plain_language_label"}, name)
    labels = {}
    for i, r in tbl.iterrows():
        category, code, label = _clean(r["category"]), _clean(r["code"]), _clean(r["plain_language_label"])
        if not category and not code and not label:
            continue
        if category not in status_label_categories:
            raise ValueError(
                f"{name} row {i + 2}: unknown category '{category}'. "
                f"Use one of: {', '.join(status_label_categories)}"
            )
        if not code or not label:
            raise ValueError(f"{name} row {i + 2}: code and plain_language_label are both required")
        if (category, code) in labels:
            raise ValueError(f"{name}: {category} code '{code}' appears more than once")
        labels[(category, code)] = label
    print(f"[config] {name}: {len(labels)} row(s) loaded from {Path(config_dir) / name}")
    return labels


def _load_field_schema(config_dir):
    """Read field_defs.csv. In this workflow it controls full-CSV column order."""
    tbl = _read_config_table(config_dir, "field_defs.csv")
    if "field_name" not in tbl.columns:
        raise ValueError("field_defs.csv is missing the field_name column")
    order = {}
    for i, r in tbl.iterrows():
        name = _clean(r.get("field_name", ""))
        if not name:
            continue
        raw_order = _clean(r.get("order", ""))
        try:
            order[name] = float(raw_order)
        except Exception:
            order[name] = 999999.0
    print(f"[config] field_defs.csv: {len(tbl)} row(s) loaded from {Path(config_dir) / 'field_defs.csv'}")
    return order, len(tbl)


def _build_schema_helpers(config_dir):
    order_lookup, n_rows = _load_field_schema(config_dir)

    def _order_columns_for_export(df):
        defined = sorted(
            [c for c in df.columns if c in order_lookup],
            key=lambda c: (order_lookup.get(c, 999999), list(df.columns).index(c)),
        )
        extras = [c for c in df.columns if c not in defined]
        return df[defined + extras].copy()

    return _order_columns_for_export, n_rows


def _extract_source_run_stamp(path, prefix):
    m = re.fullmatch(re.escape(prefix) + r"_(\d{8}_\d{6})\.csv", path.name)
    return m.group(1) if m else None


def _find_latest_common_warehouse_run(warehouse_dir):
    warehouse_dir = Path(warehouse_dir)
    required_prefixes = [
        "stops_curbside_analysis",
        "shared_stop_records_scored",
        "shared_stop_pair_scores",
    ]

    by_prefix = {}
    for prefix in required_prefixes:
        items = {}
        for p in warehouse_dir.glob(prefix + "_*.csv"):
            source_run_stamp = _extract_source_run_stamp(p, prefix)
            if source_run_stamp:
                items[source_run_stamp] = p
        by_prefix[prefix] = items

    common = set.intersection(*(set(v) for v in by_prefix.values()))
    if not common:
        details = "\n".join(
            f"  {k}: {len(v)} stamped file(s)" for k, v in by_prefix.items()
        )
        raise FileNotFoundError(
            "Could not find one warehouse run stamp shared by all required files.\n"
            + details
        )

    source_run_stamp = sorted(common)[-1]
    return source_run_stamp, {prefix: by_prefix[prefix][source_run_stamp] for prefix in required_prefixes}


def _build_fallback_source_key(row):
    vals = [
        _clean(row.get("stop_key", "")),
        _clean(row.get("_gtfs_key", "")),
        _clean(row.get("feed_key", "")),
        _clean(row.get("stop_id", "")),
        _clean(row.get("stop_lat", "")),
        _clean(row.get("stop_lon", "")),
    ]
    return "WH_" + hashlib.md5("|".join(vals).encode("utf-8")).hexdigest()


def _build_pair_endpoint_table(pair_df):
    frames = []
    for side in ("a", "b"):
        cols = {
            f"source_key_{side}": "source_key",
            f"agency_{side}": "agency",
            f"feed_{side}": "feed",
            f"stop_id_{side}": "stop_id",
            f"stop_name_{side}": "stop_name",
        }
        missing = [c for c in cols if c not in pair_df.columns]
        if missing:
            raise RuntimeError(
                "Warehouse pair file is missing endpoint field(s): "
                + ", ".join(missing)
            )
        t = pair_df[list(cols)].rename(columns=cols).copy()
        frames.append(t)

    endpoints = pd.concat(frames, ignore_index=True)
    endpoints = endpoints[endpoints["source_key"].astype(str).str.strip().ne("")].copy()

    for c in ["agency", "feed", "stop_id", "stop_name"]:
        endpoints[c + "_n"] = endpoints[c].map(_normalize_text)

    # A source key should always describe one source endpoint.
    core = ["agency_n", "feed_n", "stop_id_n"]
    conflicts = []
    for sk, g in endpoints.groupby("source_key", sort=False):
        combos = g[core].drop_duplicates()
        if len(combos) > 1:
            conflicts.append(sk)

    if conflicts:
        raise RuntimeError(
            f"{len(conflicts):,} pair source key(s) have inconsistent "
            "agency/feed/stop_id metadata. First few: "
            + ", ".join(conflicts[:10])
        )

    endpoints = (
        endpoints.sort_values(["source_key"])
        .drop_duplicates("source_key", keep="first")
        .reset_index(drop=True)
    )
    return endpoints


def _build_pair_source_crosswalk(full_df, candidate_df, pair_df):
    full = full_df.copy().reset_index(drop=True)
    full["_row_id"] = full.index.astype(int)

    for c, source_c in [
        ("agency_n", "analysis_name"),
        ("feed_n", "feed_name"),
        ("stop_id_n", "stop_id"),
        ("stop_name_n", "stop_name"),
    ]:
        full[c] = full[source_c].map(_normalize_text)

    endpoints = _build_pair_endpoint_table(pair_df)

    # Build exact candidate-file anchors where they exist.
    anchor_by_stop_key = {}
    if {"stop_key", "source_record_key"}.issubset(candidate_df.columns):
        anchors = candidate_df[["stop_key", "source_record_key"]].copy()
        anchors["stop_key"] = anchors["stop_key"].map(_clean)
        anchors["source_record_key"] = anchors["source_record_key"].map(_clean)
        anchors = anchors[
            anchors["stop_key"].ne("") & anchors["source_record_key"].ne("")
        ]
        bad = anchors.groupby("stop_key")["source_record_key"].nunique()
        bad = bad[bad > 1]
        if len(bad):
            raise RuntimeError(
                f"{len(bad):,} stop_key value(s) map to multiple source_record_key "
                "values in the shared_stop_records_scored candidate file."
            )
        anchor_by_stop_key = dict(
            anchors.drop_duplicates("stop_key")
            .set_index("stop_key")["source_record_key"]
        )

    row_anchor = full["stop_key"].map(anchor_by_stop_key).fillna("").map(_clean)

    # Fast lookup on the exact fields exported to the warehouse pair file.
    core_lookup = defaultdict(list)
    core_name_lookup = defaultdict(list)

    for _, r in full.iterrows():
        core = (r["agency_n"], r["feed_n"], r["stop_id_n"])
        core_lookup[core].append(int(r["_row_id"]))
        core_name_lookup[core + (r["stop_name_n"],)].append(int(r["_row_id"]))

    endpoint_to_row = {}
    unresolved = []
    ambiguous = []

    for _, ep in endpoints.iterrows():
        sk = _clean(ep["source_key"])
        core = (ep["agency_n"], ep["feed_n"], ep["stop_id_n"])
        candidates = core_lookup.get(core, [])

        if len(candidates) == 1:
            endpoint_to_row[sk] = candidates[0]
            continue

        # If duplicated at the core key, use the exported stop name.
        if len(candidates) > 1:
            named = core_name_lookup.get(core + (ep["stop_name_n"],), [])
            if len(named) == 1:
                endpoint_to_row[sk] = named[0]
                continue

            # Last safe discriminator: an existing candidate-file source-key anchor.
            anchored = [rid for rid in candidates if row_anchor.iloc[rid] == sk]
            if len(anchored) == 1:
                endpoint_to_row[sk] = anchored[0]
                continue

            ambiguous.append((sk, len(candidates), _clean(ep["agency"]),
                              _clean(ep["feed"]), _clean(ep["stop_id"]),
                              _clean(ep["stop_name"])))
            continue

        unresolved.append(
            (sk, _clean(ep["agency"]), _clean(ep["feed"]),
             _clean(ep["stop_id"]), _clean(ep["stop_name"]))
        )

    if unresolved or ambiguous:
        msg = [
            "Could not safely map every warehouse pair endpoint back to the full "
            "warehouse source. The run is stopped rather than silently dropping pairs."
        ]
        if unresolved:
            msg.append(f"Unresolved endpoint keys: {len(unresolved):,}")
            for x in unresolved[:10]:
                msg.append("  UNRESOLVED: " + " | ".join(map(str, x)))
        if ambiguous:
            msg.append(f"Ambiguous endpoint keys: {len(ambiguous):,}")
            for x in ambiguous[:10]:
                msg.append("  AMBIGUOUS: " + " | ".join(map(str, x)))
        raise RuntimeError("\n".join(msg))

    # Verify one warehouse row is not being assigned two different pair keys.
    row_to_keys = defaultdict(list)
    for sk, rid in endpoint_to_row.items():
        row_to_keys[rid].append(sk)

    collisions = {rid: keys for rid, keys in row_to_keys.items() if len(set(keys)) > 1}
    if collisions:
        examples = list(collisions.items())[:10]
        raise RuntimeError(
            f"{len(collisions):,} warehouse row(s) map to multiple pair source keys. "
            f"Examples: {examples}"
        )

    print(
        f"[pair-key map] resolved {len(endpoint_to_row):,} / "
        f"{len(endpoints):,} unique pair endpoint source keys"
    )

    return full, endpoint_to_row, row_anchor


def _prepare_analysis_source(full_df, candidate_df, pair_df):
    full, endpoint_to_row, row_anchor = _build_pair_source_crosswalk(
        full_df, candidate_df, pair_df
    )

    # From the warehouse candidate file, keep only what this toolkit uses:
    # source_record_key (source-key consistency check) and direction_token
    # (boarding-position specificity in the two-agency recommendation).
    keep_from_candidate = ["stop_key", "source_record_key", "direction_token"]
    keep_from_candidate = [c for c in keep_from_candidate if c in candidate_df.columns]
    cand = candidate_df[keep_from_candidate].copy()
    cand = cand.rename(columns={"source_record_key": "candidate_source_record_key"})

    out = full.merge(cand, how="left", on="stop_key")

    # Start with a unique fallback key for rows that never occur in the nearby-pair file.
    out["source_key"] = out.apply(_build_fallback_source_key, axis=1)

    # Overwrite all nearby-pair endpoints with the EXACT source keys from the pair file.
    for sk, rid in endpoint_to_row.items():
        out.at[rid, "source_key"] = sk

    # Check the candidate-file source keys against the pair-derived crosswalk.
    anchored = out.get(
        "candidate_source_record_key",
        pd.Series("", index=out.index)
    ).fillna("").astype(str).map(_clean)

    mismatched = out[
        anchored.ne("") & out["source_key"].astype(str).ne(anchored)
    ]
    if len(mismatched):
        raise RuntimeError(
            f"{len(mismatched):,} candidate-file row(s) disagree with the "
            "pair-derived source-key mapping."
        )

    # Confirm that every pair endpoint now exists in the source universe.
    source_keys = set(out["source_key"].astype(str))
    pair_keys = set(pair_df["source_key_a"].astype(str)) | set(
        pair_df["source_key_b"].astype(str)
    )
    missing_keys = sorted(k for k in pair_keys if k and k not in source_keys)
    if missing_keys:
        raise RuntimeError(
            f"{len(missing_keys):,} warehouse pair endpoint key(s) are still missing "
            "from the prepared source. First few: " + ", ".join(missing_keys[:10])
        )

    print(
        f"[pair-key map] all {len(pair_keys):,} unique pair endpoint keys are present "
        "in the prepared source"
    )

    # GTFS_ interface fields: deliberate copies of the warehouse GTFS stop fields.
    out["GTFS_stop_id"] = out["stop_id"].fillna("").astype(str)
    out["GTFS_stop_name"] = out["stop_name"].fillna("").astype(str)
    out["GTFS_stop_code"] = out["stop_code"].fillna("").astype(str)
    out["GTFS_stop_lat"] = out["stop_lat"].fillna("").astype(str)
    out["GTFS_stop_lon"] = out["stop_lon"].fillna("").astype(str)
    out["GTFS_stop_desc"] = out["stop_desc"].fillna("").astype(str)
    out["GTFS_tts_stop_name"] = out["tts_stop_name"].fillna("").astype(str)
    out["GTFS_parent_station"] = out["parent_station"].fillna("").astype(str)
    out["GTFS_location_type"] = out["location_type"].fillna("").astype(str)
    out["GTFS_platform_code"] = out["platform_code"].fillna("").astype(str)

    # agency_name is the toolkit's agency/operator label. It starts as the
    # warehouse analysis_name and is re-set after alias normalization in
    # source cleaning. It is NOT the original GTFS agency.txt agency_name.
    out["agency_name"] = out["analysis_name"].fillna("").astype(str)

    return out


def _report_config_values_not_in_source(source, agency_aliases, excluded_regional_feeds):
    """Warn about configured feed names that do not appear in this warehouse run.

    A feed can legitimately disappear from the warehouse, so this is a warning
    rather than an error, but it also catches a misspelled feed name, which
    would otherwise make an alias or exclusion silently do nothing. The
    warnings are returned so the run manifest can record them.
    """
    feeds = set(source["feed_name"].fillna("").astype(str).str.strip())
    warnings = []
    missing_regional = sorted(f for f in excluded_regional_feeds if f not in feeds)
    if missing_regional:
        warnings.append("source_exclusions.csv regional_feed not found in this warehouse run: " + "; ".join(missing_regional))
    missing_alias = sorted(f for f in agency_aliases if f not in feeds)
    if missing_alias:
        warnings.append(f"agency_aliases.csv feed_name not found in this warehouse run ({len(missing_alias)}): " + "; ".join(missing_alias))
    for w in warnings:
        print(f"[config] WARNING: {w}")
    return warnings


def _serves_only_rail_routes(value, excluded_rail_route_types):
    types = {x.strip() for x in _clean(value).split(",") if x.strip()}
    return bool(types) and types <= set(excluded_rail_route_types)


def _apply_source_cleaning(source, pair_df, agency_aliases, excluded_regional_feeds, excluded_rail_route_types):
    """
    Apply the source-cleaning rules after the warehouse source keys have been
    mapped, so the pair file and the stop list stay consistent.

    Agency labels and explicit exclusions come from configuration tables so the
    source rules are reviewable independently of the workflow code. The exact
    cross-feed duplicate rule is applied after those configured rules.
    """
    src = source.copy()
    pairs = pair_df.copy()
    src["_original_order"] = range(len(src))

    # Normalize agency attribution using the configured feed-name mapping.
    # analysis_name is overwritten with the normalized label because the
    # precursor and duplicate rules below compare normalized operator labels.
    mapped = src["feed_name"].map(agency_aliases)
    alias_mask = mapped.notna() & mapped.astype(str).str.strip().ne("")
    src.loc[alias_mask, "analysis_name"] = mapped[alias_mask]
    src["agency_name"] = src["analysis_name"].fillna("").astype(str)

    reason = pd.Series("", index=src.index, dtype=object)

    # Regional aggregate copies.
    dup_511 = src["feed_name"].isin(excluded_regional_feeds)
    reason.loc[dup_511] = "BAY_AREA_511_REGIONAL_DUPLICATE"

    # Regional precursor feeds are removed only when the same normalized
    # operator also has a non-precursor feed.
    if "regional_feed_type" in src.columns:
        precursor = src["regional_feed_type"].eq("Regional Precursor Feed")
        label_has_other = (~precursor).groupby(src["analysis_name"]).transform("any")
        dup_precursor = precursor & label_has_other & reason.eq("")
        reason.loc[dup_precursor] = "REGIONAL_PRECURSOR_DUPLICATE"
    else:
        print("[source cleaning] WARNING: regional_feed_type column not found; regional precursor filter skipped")
        dup_precursor = pd.Series(False, index=src.index)

    # Rail-only stations.
    if "route_types" in src.columns:
        rail = src["route_types"].map(lambda v: _serves_only_rail_routes(v, excluded_rail_route_types)) & reason.eq("")
        reason.loc[rail] = "RAIL_ONLY"
    else:
        print("[source cleaning] WARNING: route_types column not found; rail-only filter skipped")
        rail = pd.Series(False, index=src.index)

    # Apply those exclusions before exact cross-feed dedupe.
    eligible = src[reason.eq("")].copy()

    # Exact cross-feed duplicates: keep one record. Prefer a mapped operator label
    # over a raw feed-name fallback. Stable source_key order breaks any remaining
    # ties deterministically.
    exact_cols = ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    for c in exact_cols:
        if c not in eligible.columns:
            raise RuntimeError(
                "Exact-duplicate cleaning requires source field: " + c
            )

    eligible["_fallback"] = (
        eligible["analysis_name"].fillna("").astype(str)
        == eligible["feed_name"].fillna("").astype(str)
    )
    eligible = eligible.sort_values(
        ["_fallback", "source_key"],
        kind="stable",
    )

    kept_by_exact = (
        eligible.drop_duplicates(exact_cols, keep="first")
        .set_index(exact_cols)["source_key"]
        .to_dict()
    )
    duplicate_mask = eligible.duplicated(exact_cols, keep="first")
    duplicate_idx = eligible.index[duplicate_mask]
    reason.loc[duplicate_idx] = "EXACT_CROSS_FEED_DUPLICATE"

    # Build an exclusion audit before removing rows.
    excluded = src[reason.ne("")].copy()
    excluded["source_exclusion_reason"] = reason.loc[excluded.index]

    if len(excluded):
        kept_source = []
        kept_agency = []
        kept_feed = []
        kept_lookup = src.set_index("source_key", drop=False)
        for _, r in excluded.iterrows():
            if r["source_exclusion_reason"] == "EXACT_CROSS_FEED_DUPLICATE":
                key = tuple(r[c] for c in exact_cols)
                keep_sk = kept_by_exact.get(key, "")
            else:
                keep_sk = ""
            kept_source.append(keep_sk)
            if keep_sk and keep_sk in kept_lookup.index:
                kr = kept_lookup.loc[keep_sk]
                kept_agency.append(_clean(kr.get("analysis_name")))
                kept_feed.append(_clean(kr.get("feed_name")))
            else:
                kept_agency.append("")
                kept_feed.append("")
        excluded["kept_source_key"] = kept_source
        excluded["kept_agency"] = kept_agency
        excluded["kept_feed"] = kept_feed

    keep_mask = reason.eq("")
    cleaned = src[keep_mask].copy()
    cleaned = (
        cleaned.sort_values("_original_order")
        .drop(columns=["_original_order"], errors="ignore")
        .reset_index(drop=True)
    )
    excluded = excluded.drop(columns=["_original_order"], errors="ignore")

    kept_keys = set(cleaned["source_key"].astype(str))
    pair_keep = (
        pairs["source_key_a"].astype(str).isin(kept_keys)
        & pairs["source_key_b"].astype(str).isin(kept_keys)
    )
    dropped_pairs = int((~pair_keep).sum())
    pairs = pairs[pair_keep].copy().reset_index(drop=True)

    print("[source cleaning] upstream stop-cleaning rules applied")
    print(f"[source cleaning] starting source rows: {len(src):,}")
    print(
        "[source cleaning] alias-normalized rows: "
        f"{int(alias_mask.sum()):,}"
    )
    print(
        "[source cleaning] Bay Area 511 regional duplicates: "
        f"{int(dup_511.sum()):,}"
    )
    print(
        "[source cleaning] regional precursor duplicates: "
        f"{int(dup_precursor.sum()):,}"
    )
    print(f"[source cleaning] rail-only rows: {int(rail.sum()):,}")
    print(
        "[source cleaning] exact cross-feed duplicates: "
        f"{int((reason == 'EXACT_CROSS_FEED_DUPLICATE').sum()):,}"
    )
    print(f"[source cleaning] retained source rows: {len(cleaned):,}")
    print(f"[source cleaning] pair rows removed with excluded records: {dropped_pairs:,}")
    print(f"[source cleaning] retained pair rows: {len(pairs):,}")

    return cleaned, pairs, excluded



def _add_outputs_to_current_map(path):
    try:
        import arcpy
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        if m is None:
            return
        norm = os.path.normcase(os.path.normpath(str(path)))
        for lyr in m.listLayers():
            try:
                if getattr(lyr, "dataSource", None):
                    ds = os.path.normcase(os.path.normpath(lyr.dataSource))
                    if ds == norm:
                        return
            except Exception:
                pass
        m.addDataFromPath(str(path))
        print(f"[gis] added to map: {path}")
    except Exception as exc:
        print(f"[gis] could not auto-add final layer: {exc}")


def _safe_num(v):
    try:
        s = _clean(v)
        return float(s) if s else None
    except Exception:
        return None


def _status_label(status_labels, category, value):
    """Translate an internal status code into the wording people see.

    A blank code gives blank wording. Any other code must have a row in
    status_labels.csv; if it does not, the run stops and names the missing
    category and code, instead of inventing wording for it.
    """
    code = _clean(value)
    if not code:
        return ""
    label = status_labels.get((category, code))
    if label is None:
        raise ValueError(
            f"status_labels.csv has no {category} label for status code '{code}'. "
            "Add a row with that category and code."
        )
    return label


def _friendly_recommendation_reason(v, status_labels):
    return _status_label(status_labels, "recommendation_reason", v)


def _friendly_route_evidence(v, status_labels, shape_context_status=""):
    """Describe route direction for a review row.

    A direction comparison (for example SAME_DIRECTION_CORROBORATES) is shown
    when one exists. When there is none (blank or NO_SHAPE_CONTEXT), the
    record's own served-shape status explains why, for example "No GTFS
    route shape".
    """
    status = _clean(v)
    if status and status != "NO_SHAPE_CONTEXT":
        return _status_label(status_labels, "route_evidence", status)
    context = _clean(shape_context_status)
    if context:
        return _status_label(status_labels, "shape_context", context)
    return _status_label(status_labels, "route_evidence", "NO_SHAPE_CONTEXT")


def _friendly_road_context(v, status_labels):
    return _status_label(status_labels, "road_context", v)




def _build_physical_route_lookup(final_scored, pair_df, status_labels):
    if pair_df is None or pair_df.empty:
        return {}

    source_to_location = dict(zip(
        final_scored["source_key"].astype(str),
        final_scored.get(
            "physical_location_id",
            pd.Series("", index=final_scored.index),
        ).astype(str),
    ))

    flags = defaultdict(lambda: {"same": False, "variation": False, "seen": False})

    for _, r in pair_df.iterrows():
        a = _clean(r.get("source_key_a"))
        b = _clean(r.get("source_key_b"))
        loc_a = source_to_location.get(a, "")
        loc_b = source_to_location.get(b, "")

        if not loc_a or loc_a != loc_b:
            continue

        status = _clean(r.get("shape_pair_direction_status"))
        modifier = _clean(r.get("shape_pair_confidence_modifier"))
        f = flags[loc_a]

        if modifier == "POSITIVE_SAME_DIRECTION_EVIDENCE" or status in {
            "SAME_DIRECTION_STRONGLY_CORROBORATES",
            "SAME_DIRECTION_CORROBORATES",
        }:
            f["same"] = True
            f["seen"] = True
        elif modifier == "NEUTRAL_ROUTE_MOVEMENT_VARIATION" or status in {
            "DIFFERENT_ROUTE_MOVEMENT_CONTEXT",
            "MIXED_ROUTE_MOVEMENT_CONTEXT",
        }:
            f["variation"] = True
            f["seen"] = True
        elif status and status != "NO_SHAPE_CONTEXT":
            f["seen"] = True

    out = {}
    for loc_id, f in flags.items():
        if f["same"] and f["variation"]:
            code = "SAME_DIRECTION_CORROBORATION_WITH_ROUTE_VARIATION"
        elif f["same"]:
            code = "SAME_DIRECTION_CORROBORATION_ONLY"
        elif f["variation"]:
            code = "ROUTE_MOVEMENT_VARIATION_ONLY"
        elif f["seen"]:
            code = "NO_SHAPE_CONTEXT"
        else:
            continue
        out[loc_id] = _status_label(status_labels, "route_evidence", code)

    return out


def _build_physical_road_lookup(final_scored, status_labels):
    if "physical_location_id" not in final_scored.columns:
        return {}
    if "road_nearest_route_id" not in final_scored.columns:
        return {}

    out = {}
    use = final_scored[
        final_scored["physical_location_id"].astype(str).str.strip().ne("")
    ]

    for loc_id, g in use.groupby("physical_location_id", sort=False):
        routes = sorted({
            _clean(v)
            for v in g["road_nearest_route_id"].tolist()
            if _clean(v)
        })
        if len(routes) == 1:
            out[str(loc_id)] = _status_label(status_labels, "road_context", "SAME_NEAREST_ALL_ROADS_ROUTE")
        elif len(routes) > 1:
            out[str(loc_id)] = _status_label(status_labels, "road_context", "DIFFERENT_NEAREST_ALL_ROADS_ROUTE")

    return out



def _boarding_position_specificity_score(row):
    """Score clues that one existing point is more specifically tied to a boarding position.

    Points: side-of-intersection wording in the name or description (+2), a
    named direction that agrees with the served-route compass direction (+3),
    a platform code (+1), served-route shape context available (+1), and a
    single unambiguous nearby roadway (+1). Road-centerline distance is not
    used. BoardingSide is not scored here because it is applied separately,
    only as comparative evidence when both points have usable same-direction
    BoardingSide results.
    """
    score = 0
    reasons = []

    name_blob = " ".join([
        _clean(row.get("GTFS_stop_name")),
        _clean(row.get("GTFS_stop_desc")),
        _clean(row.get("GTFS_tts_stop_name")),
    ]).lower()

    if re.search(r"\b(?:near\s*side|nearside|far\s*side|farside|opposite|opp)\b", name_blob):
        score += 2
        reasons.append("explicit side-of-intersection wording")

    direction = _clean(row.get("direction_token")).upper()
    compass = _clean(row.get("shape_compass_directions")).upper()
    compass_tokens = {
        x.strip()
        for x in re.split(r"[|,;/]+", compass)
        if x.strip()
    }
    if direction in {"N", "S", "E", "W"} and compass_tokens:
        direction_matches_shape = any(
            token.startswith(direction) for token in compass_tokens
        )
        if direction_matches_shape:
            score += 3
            reasons.append("named direction agrees with served-route shape")

    if _clean(row.get("GTFS_platform_code")):
        score += 1
        reasons.append("platform code present")

    if _clean(row.get("shape_context_status")) == "SHAPE_CONTEXT_AVAILABLE":
        score += 1
        reasons.append("served-route shape context available")

    if _clean(row.get("road_context_ambiguous")).upper() == "N":
        score += 1
        reasons.append("unambiguous roadway context")

    return score, reasons


def _two_record_location_direction_status(g, pair_df):
    """Return the served-shape direction comparison for a two-record location."""
    if pair_df is None or pair_df.empty or len(g) != 2:
        return ""

    keys = sorted(
        g["source_key"].fillna("").astype(str).str.strip().tolist()
    )
    if len(keys) != 2 or not keys[0] or not keys[1]:
        return ""

    a, b = keys
    mask = (
        (
            pair_df["source_key_a"].fillna("").astype(str).eq(a)
            & pair_df["source_key_b"].fillna("").astype(str).eq(b)
        )
        | (
            pair_df["source_key_a"].fillna("").astype(str).eq(b)
            & pair_df["source_key_b"].fillna("").astype(str).eq(a)
        )
    )
    hit = pair_df.loc[mask]
    if hit.empty:
        return ""
    return _clean(hit.iloc[0].get("shape_pair_direction_status")).upper()


def _apply_two_agency_recommendations(final_scored, pair_df=None):
    """Recommend one existing point in unresolved two-agency locations.

    With only two agencies there is no majority, so one point is recommended
    only when boarding-position clues clearly favor it. Each point gets a
    small boarding-position score (see _boarding_position_specificity_score)
    plus comparative BoardingSide. BoardingSide counts only when it
    distinguishes the two points:

    * missing BoardingSide data are neutral;
    * BOTH_LIKELY, MIXED, and other non-clean patterns are neutral;
    * LIKELY vs UNLIKELY contributes only when pair served-shape evidence says
      the two records represent the same/compatible direction of travel.

    RoadDistFt / FarthestRoad / TieBreakRec are a later, separate fallback.
    """
    df = final_scored.copy()

    for c in [
        "recommended_point_flag",
        "recommended_source_key",
        "recommended_agency",
        "recommended_stop_id",
        "recommended_lat",
        "recommended_lon",
        "recommendation_method",
        "recommendation_confidence",
        "recommendation_support_operator_count",
        "distance_to_recommended_ft",
        "recommendation_status_code",
    ]:
        if c not in df.columns:
            df[c] = ""

    recommended_locations = 0
    recommended_within25 = 0
    recommended_over25 = 0

    use = df[
        df["physical_location_id"].astype(str).str.strip().ne("")
        & df["recommendation_status_code"].astype(str).isin(
            ["AGREEMENT_WITHIN_25FT_NO_REFERENCE", "UNRESOLVED"]
        )
    ]

    for loc_id, g in use.groupby("physical_location_id", sort=False):
        if len(g) != 2:
            continue

        statuses = set(
            g["recommendation_status_code"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        pair_direction_status = _two_record_location_direction_status(
            g,
            pair_df,
        )
        same_direction_pair = pair_direction_status.startswith("SAME_DIRECTION")

        sides_by_idx = {
            idx: _clean(row.get("boarding_side")).upper()
            for idx, row in g.iterrows()
        }
        sides = sorted(sides_by_idx.values())
        clean_boarding_comparison = (
            same_direction_pair
            and sides == ["LIKELY", "UNLIKELY"]
        )

        if statuses == {"AGREEMENT_WITHIN_25FT_NO_REFERENCE"}:
            if not bool(
                g["physical_location_match"]
                .astype(str)
                .eq("High Confidence")
                .all()
            ):
                continue
            distance_bucket = "WITHIN_25FT"

        elif statuses == {"UNRESOLVED"}:
            # For >25-ft/review cases, comparative BoardingSide must actually
            # distinguish both candidates and the route movements must be
            # comparable. One-sided/missing BoardingSide never qualifies.
            if not clean_boarding_comparison:
                continue
            distance_bucket = "OVER_25FT_OR_REVIEW"

        else:
            continue

        scored = []
        for idx, row in g.iterrows():
            score, reasons = _boarding_position_specificity_score(row)

            # Comparative BoardingSide only. Missing data remain neutral.
            if clean_boarding_comparison:
                side = sides_by_idx[idx]
                if side == "LIKELY":
                    score += 2
                    reasons.append(
                        "comparative served-shape geometry supports plausible boarding side"
                    )
                elif side == "UNLIKELY":
                    score -= 2
                    reasons.append(
                        "comparative served-shape geometry indicates implausible boarding side"
                    )

            scored.append((score, idx, reasons))

        scored.sort(key=lambda x: (-x[0], _clean(df.at[x[1], "source_key"])))
        top_score, top_idx, top_reasons = scored[0]
        second_score = scored[1][0]

        # Recommend only with clear evidence: the top point must score at least
        # 3 and lead the other point by at least 2.
        if top_score < 3 or (top_score - second_score) < 2:
            continue

        recommended_row = df.loc[top_idx]
        recommended_lat = _clean(recommended_row.get("GTFS_stop_lat"))
        recommended_lon = _clean(recommended_row.get("GTFS_stop_lon"))
        recommended_source = _clean(recommended_row.get("source_key"))
        recommended_agency = _clean(recommended_row.get("agency_name"))
        recommended_stop_id = _clean(recommended_row.get("GTFS_stop_id"))

        for idx, row in g.iterrows():
            df.at[idx, "recommended_point_flag"] = "Y" if idx == top_idx else "N"
            df.at[idx, "recommended_source_key"] = recommended_source
            df.at[idx, "recommended_agency"] = recommended_agency
            df.at[idx, "recommended_stop_id"] = recommended_stop_id
            df.at[idx, "recommended_lat"] = recommended_lat
            df.at[idx, "recommended_lon"] = recommended_lon
            df.at[idx, "recommendation_method"] = (
                "TWO_OPERATOR_BOARDING_POSITION_EVIDENCE"
            )
            df.at[idx, "recommendation_confidence"] = "MEDIUM"
            df.at[idx, "recommendation_support_operator_count"] = "2"
            df.at[idx, "recommendation_status_code"] = (
                "RESOLVED_TWO_OPERATOR_RECOMMENDED"
            )

            if idx == top_idx:
                df.at[idx, "distance_to_recommended_ft"] = "0"

            df.at[idx, "two_operator_recommendation_basis"] = "; ".join(top_reasons)
            df.at[idx, "two_operator_recommendation_score"] = str(top_score)

        recommended_locations += 1
        if distance_bucket == "WITHIN_25FT":
            recommended_within25 += 1
        else:
            recommended_over25 += 1

    print(
        "[recommended point] unresolved two-agency locations newly recommended: "
        f"{recommended_locations:,}"
    )
    print(f"  <=25 ft evidence recommendations: {recommended_within25:,}")
    print(
        "  >25 ft/review clean comparative BoardingSide recommendations: "
        f"{recommended_over25:,}"
    )
    return (
        df,
        recommended_locations,
        recommended_within25,
        recommended_over25,
    )

def _recommendation_location_score(support_n, operator_n, resolved):
    """Score how strongly the agency consensus supports the recommended point.

    This is an evidence score from 0 to 100, not a probability.
    """
    if not resolved:
        return None

    support = _safe_num(support_n)
    operators = _safe_num(operator_n)
    if support is None or operators is None or operators <= 0:
        return None

    score = round(50 + 50 * max(0.0, min(1.0, support / operators)))
    if operators <= 2:
        score = min(score, 80)

    return int(max(0, min(100, score)))



def _boarding_side_lookup(shape_rows, min_offset_ft=3.0):
    """BoardingSide: stop side relative to served-shape travel direction.

    LIKELY   = usable served shapes consistently place the stop on the right
               (the conventional boarding side)
    UNLIKELY = usable served shapes consistently place the stop on the left
    MIXED    = served shapes disagree
    blank    = not evaluated for this record (shapes are only looked up for
               groups with an issue or unresolved location), or evaluated
               without enough stable geometry (offset under min_offset_ft)

    BoardingSide is used in final pair scoring (+4 when both points are
    LIKELY, -6 when LIKELY vs UNLIKELY, only for same-direction pairs) and as
    comparative evidence in the two-agency recommendation.
    """
    if shape_rows is None or shape_rows.empty:
        return {}

    required = {
        "source_key",
        "stop_lat",
        "stop_lon",
        "segment_start_lat",
        "segment_start_lon",
        "segment_end_lat",
        "segment_end_lon",
        "stop_to_shape_segment_ft",
    }
    if not required.issubset(shape_rows.columns):
        return {}

    row_sides = []

    for _, r in shape_rows.iterrows():
        source_key = _clean(r.get("source_key"))
        if not source_key:
            continue

        stop_lat = _safe_num(r.get("stop_lat"))
        stop_lon = _safe_num(r.get("stop_lon"))
        a_lat = _safe_num(r.get("segment_start_lat"))
        a_lon = _safe_num(r.get("segment_start_lon"))
        b_lat = _safe_num(r.get("segment_end_lat"))
        b_lon = _safe_num(r.get("segment_end_lon"))
        offset_ft = _safe_num(r.get("stop_to_shape_segment_ft"))

        if None in (stop_lat, stop_lon, a_lat, a_lon, b_lat, b_lon):
            continue

        # Very small offsets make left/right classification unstable.
        if offset_ft is None or offset_ft < min_offset_ft:
            continue

        mean_lat = math.radians((a_lat + b_lat + stop_lat) / 3.0)
        xscale = math.cos(mean_lat)

        ax, ay = a_lon * xscale, a_lat
        bx, by = b_lon * xscale, b_lat
        sx, sy = stop_lon * xscale, stop_lat

        vx, vy = bx - ax, by - ay
        wx, wy = sx - ax, sy - ay

        if (vx * vx + vy * vy) <= 1e-18:
            continue

        cross = vx * wy - vy * wx
        if abs(cross) <= 1e-15:
            continue

        row_sides.append(
            (source_key, "LEFT" if cross > 0 else "RIGHT")
        )

    if not row_sides:
        return {}

    side_df = pd.DataFrame(row_sides, columns=["source_key", "side"])
    lookup = {}

    for source_key, g in side_df.groupby("source_key", sort=False):
        sides = set(g["side"].astype(str))
        if sides == {"RIGHT"}:
            status = "LIKELY"
        elif sides == {"LEFT"}:
            status = "UNLIKELY"
        elif sides:
            status = "MIXED"
        else:
            status = ""
        lookup[source_key] = status

    return lookup



def _attach_boarding_side_to_source(source_df, shape_rows):
    """Attach the BoardingSide value to source rows before final pair scoring."""
    out = source_df.copy()
    lookup = _boarding_side_lookup(shape_rows)
    out["boarding_side"] = (
        out["source_key"]
        .astype(str)
        .map(lookup)
        .fillna("")
    )
    return out, lookup


def _merge_shape_pair_context(relationship_pairs, shaped_pairs):
    """Carry served-shape pair direction fields into the pair universe used by pair scoring."""
    rel = relationship_pairs.copy()

    wanted = [
        "source_key_a",
        "source_key_b",
        "shape_pair_direction_status",
        "shape_pair_min_bearing_diff_deg",
        "shape_pair_median_nearest_bearing_diff_deg",
        "shape_pair_max_nearest_bearing_diff_deg",
        "shape_pair_confidence_modifier",
    ]
    if shaped_pairs is None or shaped_pairs.empty:
        for c in wanted[2:]:
            if c not in rel.columns:
                rel[c] = ""
        return rel

    available = [c for c in wanted if c in shaped_pairs.columns]
    if not {"source_key_a", "source_key_b"}.issubset(available):
        return rel

    ctx = shaped_pairs[available].copy()

    # Build order-independent pair keys in case endpoint ordering differs.
    def pair_key(a, b):
        a = str(a).strip()
        b = str(b).strip()
        return "||".join(sorted([a, b]))

    ctx["_boarding_pair_key"] = [
        pair_key(a, b)
        for a, b in zip(ctx["source_key_a"], ctx["source_key_b"])
    ]
    ctx = ctx.drop_duplicates("_boarding_pair_key", keep="first")

    rel["_boarding_pair_key"] = [
        pair_key(a, b)
        for a, b in zip(rel["source_key_a"], rel["source_key_b"])
    ]

    keep = ["_boarding_pair_key"] + [
        c for c in wanted[2:] if c in ctx.columns
    ]
    rel = rel.merge(
        ctx[keep],
        how="left",
        on="_boarding_pair_key",
        suffixes=("", "_shape"),
    )

    for c in wanted[2:]:
        shape_c = f"{c}_shape"
        if shape_c in rel.columns:
            if c in rel.columns:
                rel[c] = rel[shape_c].where(
                    rel[shape_c].astype(str).str.strip().ne(""),
                    rel[c],
                )
                rel = rel.drop(columns=[shape_c])
            else:
                rel = rel.rename(columns={shape_c: c})
        if c not in rel.columns:
            rel[c] = ""

    return rel.drop(columns=["_boarding_pair_key"], errors="ignore")



def _build_user_facing_products(
    final_scored,
    group_df,
    issue_records,
    unresolved_locations,
    pair_df=None,
    road_group_context=None,
    road_record_context=None,
    shape_rows=None,
    status_labels=None,
):
    """Make the two final stop layers.

    Both layers keep every statewide stop. Detail has more evidence and
    Summary keeps the shorter field set.
    """
    status_labels = status_labels or {}
    detail_src = final_scored.copy()
    groups = group_df.copy()
    issues = issue_records.copy() if issue_records is not None else pd.DataFrame()
    unresolved = (
        unresolved_locations.copy()
        if unresolved_locations is not None
        else pd.DataFrame()
    )

    issue_by_source = {}
    if not issues.empty:
        issue_by_source = {
            _clean(r.get("likely_incorrect_source_key")): r.to_dict()
            for _, r in issues.iterrows()
        }

    unresolved_by_location = {}
    if not unresolved.empty and "physical_location_id" in unresolved.columns:
        unresolved_by_location = {
            _clean(r.get("physical_location_id")): r.to_dict()
            for _, r in unresolved.iterrows()
            if _clean(r.get("physical_location_id"))
        }

    group_by_id = {
        _clean(r.get("shared_stop_group_id")): r.to_dict()
        for _, r in groups.iterrows()
        if _clean(r.get("shared_stop_group_id"))
    }

    name_by_source = dict(zip(
        detail_src["source_key"].astype(str),
        detail_src["GTFS_stop_name"].astype(str),
    ))

    route_by_location = _build_physical_route_lookup(detail_src, pair_df, status_labels)
    road_by_location = _build_physical_road_lookup(detail_src, status_labels)

    # RoadDistFt is a post-scoring review measurement. It is not used by the
    # shared-stop score, candidate grouping, QA status, or normal recommendation.
    road_dist_by_source = {}
    if road_record_context is not None and not road_record_context.empty:
        if {
            "source_key",
            "road_nearest_distance_ft",
        }.issubset(road_record_context.columns):
            for _, rr in road_record_context.iterrows():
                sk = _clean(rr.get("source_key"))
                dist = _safe_num(rr.get("road_nearest_distance_ft"))
                if sk and dist is not None:
                    road_dist_by_source[sk] = dist

    # BoardingSide shown for review (it was already applied in final pair scoring).
    boarding_side_by_source = _boarding_side_lookup(shape_rows)

    detail_rows = []

    for _, r in detail_src.iterrows():
        gid = _clean(r.get("shared_stop_group_id"))
        loc_id = _clean(r.get("physical_location_id"))
        source_key = _clean(r.get("source_key"))
        issue = issue_by_source.get(source_key, {})
        unresolved_row = unresolved_by_location.get(loc_id, {})

        physical_match = _clean(r.get("physical_location_match"))
        physical_status = _clean(r.get("physical_location_status"))
        status_code = _clean(r.get("recommendation_status_code")).upper()
        resolved = status_code.startswith("RESOLVED")
        agreement_without_recommendation = (
            status_code == "AGREEMENT_WITHIN_25FT_NO_REFERENCE"
        )
        recommendation_unresolved = status_code == "UNRESOLVED"
        unmatched = (
            physical_status == "NO_CROSS_OPERATOR_LOCATION_MATCH_SELECTED"
        )

        if source_key in issue_by_source:
            qa_status = "Likely Position Issue"
        elif gid and (
            recommendation_unresolved
            or unmatched
            or physical_match != "High Confidence"
        ):
            qa_status = "Review Needed"
        else:
            qa_status = "No Detected Issue"

        review_reasons = []
        if source_key in issue_by_source:
            review_reasons.append("Stop is >25 ft from recommended location")
        else:
            if gid and (
                unmatched
                or physical_match != "High Confidence"
            ):
                review_reasons.append("Shared-stop match needs review")
            if recommendation_unresolved:
                review_reasons.append("Recommended location needs review")

        review_reason = "; ".join(review_reasons)

        if not gid:
            shared_status = "No Shared Stop Detected"
            shared_match = ""
        elif loc_id:
            shared_status = (
                "Shared Stop Detected"
                if physical_match == "High Confidence"
                else "Shared Stop Candidate - Review"
            )
            shared_match = physical_match or "Needs Review"
        else:
            shared_status = "Shared Stop Candidate - Review"
            shared_match = "Needs Review"

        if not gid:
            recommendation_status = "Not Applicable"
        elif resolved:
            recommendation_status = "Resolved"
        elif agreement_without_recommendation:
            recommendation_status = "Agreement Within 25 ft"
        elif recommendation_unresolved:
            recommendation_status = "Review Needed"
        else:
            recommendation_status = "Not Established"

        operator_n = _clean(r.get("physical_location_operator_count"))
        support_n = _clean(r.get("recommendation_support_operator_count"))
        recommendation_score = _recommendation_location_score(
            support_n,
            operator_n,
            resolved,
        )

        if agreement_without_recommendation:
            location_basis = (
                "2 of 2 agencies are within 25 ft; no recommended point selected"
            )
        elif (
            resolved
            and _clean(r.get("recommendation_method"))
            == "TWO_OPERATOR_BOARDING_POSITION_EVIDENCE"
        ):
            evidence_basis = _clean(r.get("two_operator_recommendation_basis"))
            location_basis = (
                "Recommended from stronger boarding-position evidence"
                + (f": {evidence_basis}" if evidence_basis else "")
            )
        elif resolved and support_n and operator_n:
            location_basis = (
                f"{support_n} of {operator_n} agencies agree within 25 ft"
            )
        elif recommendation_unresolved:
            location_basis = _friendly_recommendation_reason(
                unresolved_row.get(
                    "recommendation_review_reason",
                    r.get("recommendation_review_reason"),
                ),
                status_labels,
            )
        elif unmatched:
            location_basis = _friendly_recommendation_reason(
                "NO_CROSS_OPERATOR_LOCATION_MATCH_SELECTED", status_labels
            )
        else:
            location_basis = ""

        if issue:
            route_evidence = _friendly_route_evidence(
                issue.get("issue_to_recommended_shape_direction_status"),
                status_labels,
                issue.get("likely_incorrect_shape_context_status"),
            )
            road_context = _friendly_road_context(
                issue.get("issue_road_context_status"), status_labels
            )
            issue_type = "Stop position >25 ft from recommended location"
            issue_confidence = _clean(issue.get("issue_confidence"))
        else:
            route_evidence = route_by_location.get(loc_id, "")
            if loc_id and not route_evidence:
                route_evidence = _friendly_route_evidence(
                    "",
                    status_labels,
                    r.get("shape_context_status"),
                )

            road_context = road_by_location.get(loc_id, "")
            issue_confidence = ""

            if recommendation_unresolved:
                issue_type = "Recommended location needs review"
            elif gid and (
                unmatched
                or physical_match != "High Confidence"
            ):
                issue_type = "Shared stop needs review"
            else:
                issue_type = ""

        physical_score = _safe_num(r.get("physical_location_score"))
        if physical_score is None:
            physical_score = _safe_num(r.get("shared_stop_best_score"))

        detail_rows.append({
            "qa_status": qa_status,
            "shared_stop_status": shared_status,
            "shared_stop_score": physical_score,
            "shared_stop_match": shared_match,
            "review_reason": review_reason,
            "recommendation_status": recommendation_status,
            "recommendation_location_score": recommendation_score,
            "distance_from_recommended_ft": _safe_num(
                r.get("distance_to_recommended_ft")
            ),
            "recommended_agency": _clean(r.get("recommended_agency")),
            "recommended_stop_id": _clean(r.get("recommended_stop_id")),
            "recommended_stop_name": name_by_source.get(
                _clean(r.get("recommended_source_key")), ""
            ),
            "recommended_lat": _safe_num(r.get("recommended_lat")),
            "recommended_lon": _safe_num(r.get("recommended_lon")),
            "location_basis": location_basis,
            "issue_type": issue_type,
            "issue_confidence": issue_confidence,
            "route_evidence": route_evidence,
            "road_context": road_context,
            "shared_stop_group_id": gid,
            "physical_location_id": loc_id,
            "agency": _clean(
                r.get("agency_name", r.get("analysis_name", ""))
            ),
            "feed_name": _clean(r.get("feed_name")),
            "feed_key": _clean(r.get("feed_key")),
            "stop_id": _clean(r.get("GTFS_stop_id", r.get("stop_id", ""))),
            "stop_name": _clean(
                r.get("GTFS_stop_name", r.get("stop_name", ""))
            ),
            "latitude": _safe_num(
                r.get("GTFS_stop_lat", r.get("stop_lat", ""))
            ),
            "longitude": _safe_num(
                r.get("GTFS_stop_lon", r.get("stop_lon", ""))
            ),
            "source_key": source_key,
            "evidence_summary": _clean(r.get("shared_stop_evidence_summary")),
            "road_dist_ft": road_dist_by_source.get(source_key),
            "boarding_side": boarding_side_by_source.get(source_key, ""),
        })

    detail = pd.DataFrame(detail_rows)

    # Post-scoring road tie-break fields. These never overwrite the normal
    # evidence-based recommendation fields.
    detail["farthest_road"] = ""
    detail["tiebreak_rec"] = ""
    detail["tiebreak_basis"] = ""

    usable = detail[
        detail["physical_location_id"].astype(str).str.strip().ne("")
    ]
    for _, idx in usable.groupby("physical_location_id", sort=False).groups.items():
        g = detail.loc[idx]
        distances = pd.to_numeric(g["road_dist_ft"], errors="coerce")

        # Compare only when every point in the candidate boarding location has
        # a usable centerline distance and there are at least two points.
        if len(g) < 2 or distances.isna().any():
            continue

        max_dist = distances.max()
        farthest_idx = distances.index[
            (distances - max_dist).abs() <= 0.01
        ]

        detail.loc[idx, "farthest_road"] = "N"
        detail.loc[farthest_idx, "farthest_road"] = "Y"

        # The tie-break is post-scoring and applies to unresolved locations
        # both <=25 ft and >25 ft. No tie-break is flagged when the normal
        # evidence logic already selected a recommended stop.
        has_existing_recommendation = (
            g["recommendation_status"].fillna("").astype(str).eq("Resolved").any()
            or g["recommended_agency"].fillna("").astype(str).str.strip().ne("").any()
            or g["recommended_stop_id"].fillna("").astype(str).str.strip().ne("").any()
        )

        if not has_existing_recommendation and len(farthest_idx) == 1:
            winner = farthest_idx[0]
            detail.at[winner, "tiebreak_rec"] = "Y"

    summary_cols = [
        "qa_status", "review_reason", "shared_stop_status",
        "shared_stop_match", "shared_stop_score", "recommendation_status",
        "recommendation_location_score", "recommended_agency", "recommended_stop_id",
        "distance_from_recommended_ft", "location_basis", "issue_type",
        "issue_confidence", "route_evidence", "road_context",
        "road_dist_ft", "farthest_road", "tiebreak_rec", "boarding_side",
        "shared_stop_group_id", "physical_location_id", "agency", "stop_id",
        "stop_name", "latitude", "longitude", "source_key",
    ]
    summary = detail[summary_cols].copy()
    return detail, summary

def _write_qa_feature_class(
    df,
    out_gdb,
    name,
    schema,
    lat_col="latitude",
    lon_col="longitude",
):
    """Write one of the final point layers with readable field aliases."""
    import arcpy

    out_fc = os.path.join(str(out_gdb), name)

    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)

    sr = arcpy.SpatialReference(4326)
    arcpy.management.CreateFeatureclass(
        str(out_gdb),
        name,
        "POINT",
        spatial_reference=sr,
    )

    added = []

    for source_col, field_name, alias, field_type, field_length in schema:
        kwargs = {}
        if field_type == "TEXT":
            kwargs["field_length"] = field_length or 255

        arcpy.management.AddField(
            out_fc,
            field_name,
            field_type,
            field_alias=alias,
            **kwargs,
        )

        added.append((source_col, field_name, field_type))

    cursor_fields = ["SHAPE@XY"] + [
        field_name
        for _, field_name, _ in added
    ]

    inserted = 0

    with arcpy.da.InsertCursor(out_fc, cursor_fields) as cur:
        for _, row in df.iterrows():
            lat = _safe_num(row.get(lat_col))
            lon = _safe_num(row.get(lon_col))

            if lat is None or lon is None:
                continue

            values = [(lon, lat)]

            for source_col, _, field_type in added:
                value = row.get(source_col)

                if field_type in {"LONG", "SHORT"}:
                    n = _safe_num(value)
                    values.append(
                        int(round(n))
                        if n is not None
                        else None
                    )
                elif field_type in {"DOUBLE", "FLOAT"}:
                    values.append(_safe_num(value))
                else:
                    values.append(
                        _clean(value)
                        if value is not None
                        else ""
                    )

            cur.insertRow(values)
            inserted += 1

    print(
        f"[final product] wrote {out_fc}; "
        f"inserted={inserted:,}"
    )

    return out_fc



def _write_headline_csvs(detail, source_data_date, out_dir):
    """Write the two headline CSVs: shared-stop candidates and >25-ft location issues."""
    out_dir = Path(out_dir)

    shared_path = out_dir / f"shared_stop_candidates_{source_data_date}.csv"
    issue_path = out_dir / f"stop_location_issues_over_25ft_{source_data_date}.csv"

    shared = detail[
        detail["shared_stop_group_id"].astype(str).str.strip().ne("")
    ].copy()
    shared = shared.sort_values(
        ["shared_stop_group_id", "physical_location_id", "agency", "stop_id"],
        kind="stable",
    )

    shared_export = pd.DataFrame({
        "Shared Stop Group ID": shared["shared_stop_group_id"],
        "Physical Location ID": shared["physical_location_id"],
        "QA Status": shared["qa_status"],
        "Review Reason": shared["review_reason"],
        "Agency": shared["agency"],
        "GTFS Feed": shared["feed_name"],
        "Stop ID": shared["stop_id"],
        "Stop Name": shared["stop_name"],
        "Latitude": shared["latitude"],
        "Longitude": shared["longitude"],
        "Shared Stop Score": shared["shared_stop_score"],
        "Shared Stop Match": shared["shared_stop_match"],
        "Recommendation Status": shared["recommendation_status"],
        "Recommendation Location Score": shared["recommendation_location_score"],
        "Recommended Agency": shared["recommended_agency"],
        "Recommended Stop ID": shared["recommended_stop_id"],
        "Distance From Recommended (ft)": shared["distance_from_recommended_ft"],
        "Route Evidence": shared["route_evidence"],
        "Road Context": shared["road_context"],
        "RoadDistFt": shared["road_dist_ft"],
        "FarthestRoad": shared["farthest_road"],
        "TieBreakRec": shared["tiebreak_rec"],
        "BoardingSide": shared["boarding_side"],
        "Location Basis": shared["location_basis"],
    })
    shared_export.to_csv(shared_path, index=False, encoding="utf-8-sig")

    issue = detail[detail["qa_status"].eq("Likely Position Issue")].copy()
    issue = issue.sort_values(
        ["agency", "stop_name", "stop_id"],
        kind="stable",
    )

    issue_export = pd.DataFrame({
        "Agency With Possible Issue": issue["agency"],
        "Stop ID": issue["stop_id"],
        "Stop Name": issue["stop_name"],
        "Current Latitude": issue["latitude"],
        "Current Longitude": issue["longitude"],
        "Recommended Agency": issue["recommended_agency"],
        "Recommended Stop ID": issue["recommended_stop_id"],
        "Recommended Stop Name": issue["recommended_stop_name"],
        "Recommended Latitude": issue["recommended_lat"],
        "Recommended Longitude": issue["recommended_lon"],
        "Distance From Recommended (ft)": issue["distance_from_recommended_ft"],
        "Issue Confidence": issue["issue_confidence"].astype(str).str.title(),
        "Recommendation Location Score": issue["recommendation_location_score"],
        "Location Basis": issue["location_basis"],
        "Route Evidence": issue["route_evidence"],
        "Road Context": issue["road_context"],
        "Recommended Action": "Verify stop location",
        "Shared Stop Group ID": issue["shared_stop_group_id"],
        "Physical Location ID": issue["physical_location_id"],
    })
    issue_export.to_csv(issue_path, index=False, encoding="utf-8-sig")

    print(
        f"[final product] shared-stop candidates CSV: {shared_path} "
        f"({len(shared_export):,} rows)"
    )
    print(
        f"[final product] stop location issues CSV: {issue_path} "
        f"({len(issue_export):,} rows)"
    )
    return shared_path, issue_path

def _toolkit_code_identity():
    """Identify exactly which toolkit code produced a run.

    code_fingerprint: SHA-256 of every .py file and config table in the
    package, with line endings normalized so a Windows checkout and a Mac or
    Linux checkout of the same code give the same value.
    git_commit: the checked-out commit, read from the .git folder when the
    toolkit is a git clone (git itself does not need to be installed).
    """
    package_dir = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    files = sorted(list(package_dir.glob("*.py")) + list((package_dir / "config").glob("*.csv")))
    for f in files:
        digest.update(f.relative_to(package_dir).as_posix().encode("utf-8"))
        digest.update(f.read_bytes().replace(b"\r\n", b"\n"))
    commit = None
    for folder in [package_dir.parent, *package_dir.parent.parents]:
        git_dir = folder / ".git"
        if not git_dir.is_dir():
            continue
        try:
            head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
            if head.startswith("ref:"):
                ref = head.split(":", 1)[1].strip()
                ref_file = git_dir / ref
                if ref_file.exists():
                    commit = ref_file.read_text(encoding="utf-8").strip()
                elif (git_dir / "packed-refs").exists():
                    for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
                        if line.endswith(" " + ref):
                            commit = line.split(" ", 1)[0]
            else:
                commit = head
        except Exception:
            commit = None
        break
    return {"code_fingerprint": digest.hexdigest(), "git_commit": commit}


def _write_run_manifest(path, result, input_files, input_rows, config_dir, config_counts, config_warnings, cache_used, offline_context_only):
    """Record what this run used and produced. Has no effect on the analysis."""
    outputs = {}
    for key, value in result.items():
        if key.endswith("_csv") and value:
            p = Path(value)
            rows = None
            if p.exists():
                with open(p, encoding="utf-8-sig") as fh:
                    rows = max(sum(1 for _ in fh) - 1, 0)
            outputs[key] = {"file": p.name, "rows": rows}
    manifest = {
        **_toolkit_code_identity(),
        "source_data_date": result.get("source_data_date"),
        "source_run_stamp": str(result.get("source_run_stamp")),
        "run_completed": datetime.now().isoformat(timespec="seconds"),
        "status": "completed",
        "offline_context_only": bool(offline_context_only),
        "cached_external_context": cache_used,
        "warehouse_inputs": {k: {"file": Path(v).name, "rows": input_rows.get(k)} for k, v in input_files.items()},
        "config": {"folder": str(config_dir), "row_counts": config_counts, "warnings": config_warnings},
        "outputs": outputs,
        "analysis_geodatabase": str(result.get("analysis_geodatabase")),
        "counts": {k: v for k, v in result.items() if k.endswith("_count") or k.endswith("_error")},
    }
    Path(path).write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    print(f"[manifest] {path}")


def run_shared_stop_analysis(
    warehouse_dir=None,
    output_root=None,
    add_to_map=True,
    out_gdb=None,
    config_dir=None,
    offline_context_only=False,
    road_cache_gdb=None,
    replace_existing_outputs=False,
):
    """Run the full shared-stop analysis.

    warehouse_dir: folder with the warehouse CSVs (and the shape caches).
    output_root:   where outputs go; default warehouse_dir / "outputs".
                   Outputs land in output_root / {source_run_stamp} / analysis, so two
                   warehouse runs on the same day never share a folder.
    out_gdb:       optional geodatabase path; default analysis.gdb in the output folder.
    offline_context_only: use only cached served-shape and road context. Stops
                   with a clear error if a required cache is missing instead
                   of querying external services.
    road_cache_gdb: optional geodatabase containing an existing road-context
                   cache to copy into this run's analysis geodatabase.
    replace_existing_outputs: allow this run to overwrite an output folder
                   that was produced by different toolkit code. Without it the
                   run stops, so earlier results are never replaced silently.
    """
    config_dir = Path(config_dir) if config_dir else config_dir_default
    print("[toolkit] California GTFS Shared-Stop Toolkit")
    print(f"[toolkit] config folder: {config_dir}")
    config_counts = pair_scoring.configure(config_dir)
    agency_aliases = _load_agency_aliases(config_dir)
    excluded_regional_feeds, excluded_rail_route_types = _load_source_exclusions(config_dir)
    status_labels = _load_status_labels(config_dir)
    config_counts["agency_aliases.csv"] = len(agency_aliases)
    config_counts["status_labels.csv"] = len(status_labels)
    config_counts["source_exclusions.csv"] = len(excluded_regional_feeds) + len(excluded_rail_route_types)
    order_columns, field_defs_rows = _build_schema_helpers(config_dir)
    config_counts["field_defs.csv"] = field_defs_rows

    if warehouse_dir is None:
        warehouse_dir = Path.home() / "Downloads" / "california_gtfs_warehouse"
    warehouse_dir = Path(warehouse_dir)

    source_run_stamp, files = _find_latest_common_warehouse_run(warehouse_dir)
    full_path = files["stops_curbside_analysis"]
    candidate_path = files["shared_stop_records_scored"]
    pair_path = files["shared_stop_pair_scores"]
    source_data_date = str(source_run_stamp)[:8]

    # Optional fifth warehouse file, used only for a printed/returned count.
    old_group_path = warehouse_dir / f"shared_stop_groups_refined_{source_run_stamp}.csv"

    # One output folder per warehouse run (full run stamp, YYYYMMDD_HHMMSS).
    output_root = Path(output_root) if output_root else warehouse_dir / "outputs"
    out_dir = output_root / str(source_run_stamp) / "analysis"
    manifest_path = out_dir / "run_manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("source_run_stamp") not in (None, str(source_run_stamp)):
            raise RuntimeError(
                f"{out_dir} already holds outputs from source run "
                f"{previous.get('source_run_stamp')}, not {source_run_stamp}. "
                "Stopping instead of overwriting. Move or rename that folder first."
            )
        current_code = _toolkit_code_identity()["code_fingerprint"]
        previous_code = previous.get("code_fingerprint")
        if previous_code and previous_code != current_code and not replace_existing_outputs:
            raise RuntimeError(
                f"{out_dir} already holds outputs made by different toolkit code "
                f"(code_fingerprint {previous_code[:12]}..., this code {current_code[:12]}...). "
                "Stopping instead of overwriting. Move or rename that folder, choose a "
                "different output_root, or pass replace_existing_outputs=True."
            )
    out_dir.mkdir(parents=True, exist_ok=True)

    if out_gdb:
        analysis_gdb = str(out_gdb)
    else:
        analysis_gdb = str(out_dir / "analysis.gdb")
        if not Path(analysis_gdb).exists():
            import arcpy
            arcpy.management.CreateFileGDB(str(out_dir), "analysis.gdb")

    road_cache_name = road_cache_feature_class.format(stamp=source_run_stamp)
    if road_cache_gdb:
        import arcpy
        source_fc = os.path.join(str(road_cache_gdb), road_cache_name)
        target_fc = os.path.join(analysis_gdb, road_cache_name)
        if not arcpy.Exists(target_fc):
            if not arcpy.Exists(source_fc):
                raise FileNotFoundError(f"Road cache not found: {source_fc}")
            arcpy.management.Copy(source_fc, target_fc)
            print(f"[cache] copied road cache: {source_fc} -> {target_fc}")

    cache_used = {}
    if offline_context_only:
        # Preflight: refuse to run if the cached external context is missing.
        import arcpy
        shape_caches = [warehouse_dir / n.format(stamp=source_run_stamp) for n in offline_shape_cache_names]
        if not any(p.exists() for p in shape_caches):
            raise FileNotFoundError(
                "Offline context mode needs a served-shape cache. None found: "
                + ", ".join(str(p) for p in shape_caches)
            )
        road_fc = os.path.join(analysis_gdb, road_cache_name)
        if not arcpy.Exists(road_fc):
            raise FileNotFoundError(
                f"Offline context mode needs the road cache in the analysis geodatabase: {road_fc}"
            )
        cache_used = {
            "shape_cache": str(next(p for p in shape_caches if p.exists())),
            "road_cache": road_fc,
        }
        print(f"[cache] using served shapes: {cache_used['shape_cache']}")
        print(f"[cache] using roads:  {cache_used['road_cache']}")

    print("=" * 78)
    print("CALIFORNIA GTFS SHARED-STOP ANALYSIS")
    print("=" * 78)
    print(f"Run stamp: {source_run_stamp}")
    print(f"Full cleaned warehouse source: {full_path.name}")
    print(f"Warehouse candidate records:   {candidate_path.name}")
    print(f"Warehouse pair universe:       {pair_path.name}")
    print(f"Output folder:                 {out_dir}")
    print("-" * 78)

    full = pd.read_csv(full_path, dtype=str, keep_default_na=False)
    candidate = pd.read_csv(candidate_path, dtype=str, keep_default_na=False)
    pair = pd.read_csv(pair_path, dtype=str, keep_default_na=False)

    source = _prepare_analysis_source(full, candidate, pair)

    # Apply the upstream stop-cleaning rules before any shared-stop scoring.
    source_preclean_rows = len(source)
    pair_preclean_rows = len(pair)
    config_warnings = _report_config_values_not_in_source(source, agency_aliases, excluded_regional_feeds)
    source, pair, source_exclusions = _apply_source_cleaning(source, pair, agency_aliases, excluded_regional_feeds, excluded_rail_route_types)
    source_exclusion_audit = (
        out_dir / f"source_exclusions_{source_data_date}.csv"
    )
    source_exclusions.to_csv(
        source_exclusion_audit,
        index=False,
        encoding="utf-8-sig",
    )
    print(
        f"[source cleaning] exclusion audit: {source_exclusion_audit} "
        f"({len(source_exclusions):,} rows)"
    )

    # ------------------------------------------------------------------
    # PASS 1: preliminary pair scoring is used only to identify the initial
    # cohort that needs served-shape context. No final outputs are based on
    # this preliminary pass.
    # ------------------------------------------------------------------
    prelim_scored, prelim_pairs, prelim_groups = pair_scoring.build_shared_stop_analysis(
        source,
        pair,
    )

    if len(prelim_pairs) != len(pair):
        raise RuntimeError(
            f"Pair-universe validation failed in preliminary pass: "
            f"warehouse pair file has {len(pair):,} rows but pair scoring scored "
            f"{len(prelim_pairs):,}."
        )

    (
        prelim_scored,
        prelim_recommendation_summary,
        prelim_issue_records,
        prelim_unresolved_locations,
        prelim_suppressed,
    ) = run_recommendation_issue_analysis(
        prelim_scored,
        prelim_groups,
        prelim_pairs,
    )

    print(
        "[boarding-side prepass] gathering served-shape evidence before "
        "final pair scoring"
    )

    pre_shape_result = run_served_shape_context(
        final_scored=prelim_scored,
        pair_df=prelim_pairs,
        group_df=prelim_groups,
        issue_records=prelim_issue_records,
        unresolved_locations=prelim_unresolved_locations,
        warehouse_dir=warehouse_dir,
        out_gdb=analysis_gdb,
        source_run_stamp=source_run_stamp,
        reuse_cache=True,
    )

    pre_shape_rows = pre_shape_result["shape_rows"]
    pre_shaped_pairs = pre_shape_result["pair_df"]

    scored_source, boarding_lookup = _attach_boarding_side_to_source(
        source,
        pre_shape_rows,
    )
    scored_pair_universe = _merge_shape_pair_context(
        pair,
        pre_shaped_pairs,
    )

    print(
        "[boarding-side prepass] source records with usable BoardingSide: "
        f"{sum(1 for v in boarding_lookup.values() if v in {'LIKELY','UNLIKELY','MIXED'}):,}"
    )

    # ------------------------------------------------------------------
    # PASS 2: final pair scoring. In this pass BoardingSide adds to or
    # subtracts from the pair score when served shapes show both records on
    # the same direction of travel. This pass drives grouping and all later outputs.
    # ------------------------------------------------------------------
    final_scored, new_pairs, new_groups = pair_scoring.build_shared_stop_analysis(
        scored_source,
        scored_pair_universe,
    )

    if len(new_pairs) != len(pair):
        raise RuntimeError(
            f"Pair-universe validation failed: warehouse pair file has {len(pair):,} "
            f"rows but final pair scoring scored {len(new_pairs):,}. "
            "No outputs were finalized."
        )

    boarding_adjusted_pairs = int(
        new_pairs["shared_stop_evidence"]
        .fillna("")
        .astype(str)
        .str.contains(
            "plausible curbside|implausible boarding side",
            regex=True,
        )
        .sum()
    )
    print(
        f"[pair validation] final pair scoring scored all {len(new_pairs):,} "
        f"warehouse pair rows; BoardingSide affected {boarding_adjusted_pairs:,} pairs"
    )

    print(
        "[recommended location] running final existing-point recommendation "
        "/ >25-ft issue analysis"
    )
    (
        final_scored,
        recommendation_summary,
        issue_records,
        unresolved_locations,
        suppressed_issue_candidates,
    ) = run_recommendation_issue_analysis(
        final_scored,
        new_groups,
        new_pairs,
    )

    road_context_error = ""
    try:
        road_result = run_road_context(
            final_scored=final_scored,
            issue_records=issue_records,
            unresolved_locations=unresolved_locations,
            out_gdb=analysis_gdb,
            source_run_stamp=source_run_stamp,
            reuse_cache=True,
            validate_service=not offline_context_only,
        )
        final_scored = road_result["final_scored"]
        issue_records = road_result["issue_records"]
        unresolved_locations = road_result["unresolved_locations"]
        road_record_context = road_result["road_record_context"]
        road_group_context = road_result["road_group_context"]
        road_roads_fc = road_result["roads_feature_class"]
        road_points_fc = road_result["points_feature_class"]
    except Exception as exc:
        road_context_error = str(exc)
        print(f"[roads] WARNING: road-context stage failed: {exc}")
        print("[roads] Core GTFS shared-stop/recommendation outputs will still be written.")
        road_record_context = pd.DataFrame()
        road_group_context = pd.DataFrame()
        road_roads_fc = None
        road_points_fc = None

    shape_context_error = ""
    try:
        shape_result = run_served_shape_context(
            final_scored=final_scored,
            pair_df=new_pairs,
            group_df=new_groups,
            issue_records=issue_records,
            unresolved_locations=unresolved_locations,
            warehouse_dir=warehouse_dir,
            out_gdb=analysis_gdb,
            source_run_stamp=source_run_stamp,
            reuse_cache=True,
        )
        final_scored = shape_result["final_scored"]
        new_pairs = shape_result["pair_df"]
        new_groups = shape_result["group_df"]
        issue_records = shape_result["issue_records"]
        unresolved_locations = shape_result["unresolved_locations"]
        shape_rows = shape_result["shape_rows"]
        shape_record_summary = shape_result["shape_record_summary"]
        shape_group_summary = shape_result["shape_group_summary"]
        shape_segments_fc = shape_result["shape_segments_feature_class"]
        shape_cache_csv = shape_result["shape_cache_csv"]

        # Preserve BoardingSide from the final scoring source even if the
        # shape stage rebuilds/merges context columns.
        final_boarding_lookup = _boarding_side_lookup(shape_rows)
        if "boarding_side" not in final_scored.columns:
            final_scored["boarding_side"] = ""
        final_scored["boarding_side"] = (
            final_scored["source_key"]
            .astype(str)
            .map(final_boarding_lookup)
            .fillna(final_scored["boarding_side"])
        )

        (
            final_scored,
            two_agency_recommended_locations,
            two_agency_recommended_within25,
            two_agency_recommended_over25,
        ) = _apply_two_agency_recommendations(
            final_scored,
            pair_df=new_pairs,
        )

    except Exception as exc:
        two_agency_recommended_locations = 0
        two_agency_recommended_within25 = 0
        two_agency_recommended_over25 = 0
        shape_context_error = str(exc)
        print(f"[shapes] WARNING: served-shape context stage failed: {exc}")
        print("[shapes] Core GTFS/road/recommendation outputs will still be written.")
        shape_rows = pre_shape_rows.copy()
        shape_record_summary = pd.DataFrame()
        shape_group_summary = pd.DataFrame()
        shape_segments_fc = None
        shape_cache_csv = None

    final_scored = order_columns(final_scored)

    d = source_data_date
    working_csv = out_dir / f"all_stops_scored_full_{d}.csv"
    slim_csv = out_dir / f"all_stops_scored_review_{d}.csv"
    pair_csv = out_dir / f"shared_stop_pairs_{d}.csv"
    group_csv = out_dir / f"shared_stop_groups_{d}.csv"
    review_dir = out_dir / "pair_scoring_review"
    review_zip = out_dir / "pair_scoring_review.zip"
    recommendation_summary_csv = out_dir / f"shared_stop_recommendation_summary_{d}.csv"
    issues_csv = out_dir / f"stop_location_issues_detail_{d}.csv"
    unresolved_csv = out_dir / f"shared_stop_unresolved_locations_{d}.csv"
    suppressed_csv = out_dir / f"stop_location_issues_suppressed_{d}.csv"
    road_records_csv = out_dir / f"road_context_records_{d}.csv"
    road_groups_csv = out_dir / f"road_context_groups_{d}.csv"
    shape_rows_csv = out_dir / f"served_shape_context_{d}.csv"
    shape_records_csv = out_dir / f"shape_record_summary_{d}.csv"
    shape_groups_csv = out_dir / f"shape_group_summary_{d}.csv"

    qa_detail_csv = out_dir / f"gtfs_stops_qa_detail_{d}.csv"
    qa_summary_csv = out_dir / f"shared_stop_qa_summary_{d}.csv"

    final_scored.to_csv(working_csv, index=False)
    pair_scoring.build_pair_scoring_review_dataframe(final_scored).to_csv(slim_csv, index=False)
    new_pairs.to_csv(pair_csv, index=False)
    new_groups.to_csv(group_csv, index=False)
    recommendation_summary.to_csv(recommendation_summary_csv, index=False)
    issue_records.to_csv(issues_csv, index=False)
    unresolved_locations.to_csv(unresolved_csv, index=False)
    suppressed_issue_candidates.to_csv(suppressed_csv, index=False)
    road_record_context.to_csv(road_records_csv, index=False)
    road_group_context.to_csv(road_groups_csv, index=False)
    shape_rows.to_csv(shape_rows_csv, index=False)
    shape_record_summary.to_csv(shape_records_csv, index=False)
    shape_group_summary.to_csv(shape_groups_csv, index=False)

    pair_scoring.write_pair_scoring_review_outputs(new_pairs, new_groups, review_dir, review_zip)

    out_gdb = analysis_gdb

    qa_detail, qa_summary = _build_user_facing_products(
        final_scored=final_scored,
        group_df=new_groups,
        issue_records=issue_records,
        unresolved_locations=unresolved_locations,
        pair_df=new_pairs,
        road_group_context=road_group_context,
        road_record_context=road_record_context,
        shape_rows=shape_rows,
        status_labels=status_labels,
    )

    qa_detail.to_csv(
        qa_detail_csv,
        index=False,
        encoding="utf-8-sig",
    )
    qa_summary.to_csv(
        qa_summary_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # Diagnostic: remaining unresolved two-record locations and whether
    # BoardingSide cleanly distinguishes them.
    boarding_diag_rows = []
    physical_detail = qa_detail[
        qa_detail["physical_location_id"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    ].copy()

    for loc_id, g in physical_detail.groupby(
        "physical_location_id",
        sort=False,
    ):
        if len(g) != 2:
            continue

        resolved_normally = (
            g["recommendation_status"].fillna("").astype(str).eq("Resolved").any()
            or g["recommended_agency"].fillna("").astype(str).str.strip().ne("").any()
            or g["recommended_stop_id"].fillna("").astype(str).str.strip().ne("").any()
        )
        if resolved_normally:
            continue

        sides = (
            g["boarding_side"]
            .fillna("")
            .astype(str)
            .str.strip()
            .tolist()
        )
        clean_distinction = sorted(sides) == ["LIKELY", "UNLIKELY"]

        statuses = set(
            g["recommendation_status"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        if statuses == {"Agreement Within 25 ft"}:
            distance_bucket = "WITHIN_25FT"
        elif "Review Needed" in statuses:
            distance_bucket = "OVER_25FT_OR_REVIEW"
        else:
            distance_bucket = "OTHER_UNRESOLVED"

        boarding_diag_rows.append({
            "Physical Location ID": loc_id,
            "Distance Bucket": distance_bucket,
            "Agency 1": g.iloc[0]["agency"],
            "Stop ID 1": g.iloc[0]["stop_id"],
            "BoardingSide 1": sides[0],
            "Agency 2": g.iloc[1]["agency"],
            "Stop ID 2": g.iloc[1]["stop_id"],
            "BoardingSide 2": sides[1],
            "Clean Distinction": "Y" if clean_distinction else "N",
        })

    boarding_diag = pd.DataFrame(boarding_diag_rows)
    boarding_diag_csv = out_dir / f"boarding_side_diagnostic_{source_data_date}.csv"
    boarding_diag.to_csv(
        boarding_diag_csv,
        index=False,
        encoding="utf-8-sig",
    )

    shared_stop_candidates_csv, stop_location_issues_over_25ft_csv = _write_headline_csvs(
        qa_detail,
        source_data_date,
        out_dir,
    )

    detail_schema = [
        ("qa_status", "qa_status", "QA Status", "TEXT", 40),
        (
            "shared_stop_status",
            "shared_status",
            "Shared Stop Status",
            "TEXT",
            50,
        ),
        (
            "shared_stop_score",
            "shared_score",
            "Shared Stop Score",
            "SHORT",
            None,
        ),
        (
            "shared_stop_match",
            "shared_match",
            "Shared Stop Match",
            "TEXT",
            30,
        ),
        (
            "review_reason",
            "review_reason",
            "Review Reason",
            "TEXT",
            255,
        ),
        (
            "recommendation_status",
            "rec_status",
            "Recommendation Status",
            "TEXT",
            30,
        ),
        (
            "recommendation_location_score",
            "rec_loc_score",
            "Recommendation Location Score",
            "SHORT",
            None,
        ),
        (
            "distance_from_recommended_ft",
            "dist_rec_ft",
            "Distance From Recommended (ft)",
            "DOUBLE",
            None,
        ),
        (
            "recommended_agency",
            "rec_agency",
            "Recommended Agency",
            "TEXT",
            180,
        ),
        (
            "recommended_stop_id",
            "rec_stop_id",
            "Recommended Stop ID",
            "TEXT",
            100,
        ),
        (
            "location_basis",
            "loc_basis",
            "Location Basis",
            "TEXT",
            255,
        ),
        ("issue_type", "issue_type", "Issue Type", "TEXT", 100),
        (
            "issue_confidence",
            "issue_conf",
            "Issue Confidence",
            "TEXT",
            20,
        ),
        (
            "route_evidence",
            "route_ev",
            "Route Evidence",
            "TEXT",
            100,
        ),
        (
            "road_context",
            "road_ctx",
            "Road Context",
            "TEXT",
            100,
        ),
        ("road_dist_ft", "road_dist", "Road Distance (ft)", "DOUBLE", None),
        ("farthest_road", "far_road", "Farthest From Road", "TEXT", 1),
        ("tiebreak_rec", "tie_rec", "Tie-Break Recommendation", "TEXT", 1),
        ("boarding_side", "board_side", "Boarding Side Diagnostic", "TEXT", 12),
        (
            "shared_stop_group_id",
            "group_id",
            "Shared Stop Group ID",
            "TEXT",
            40,
        ),
        (
            "physical_location_id",
            "location_id",
            "Physical Location ID",
            "TEXT",
            40,
        ),
        ("agency", "agency", "Agency", "TEXT", 180),
        ("feed_name", "feed_name", "GTFS Feed", "TEXT", 180),
        ("stop_id", "stop_id", "Stop ID", "TEXT", 100),
        ("stop_name", "stop_name", "Stop Name", "TEXT", 255),
        (
            "source_key",
            "source_key",
            "Source Key",
            "TEXT",
            80,
        ),
        (
            "evidence_summary",
            "evidence",
            "Evidence Summary",
            "TEXT",
            1000,
        ),
    ]

    summary_schema = [
        ("qa_status", "qa_status", "QA Status", "TEXT", 40),
        ("review_reason", "review_reason", "Review Reason", "TEXT", 255),
        ("shared_stop_status", "shared_status", "Shared Stop Status", "TEXT", 50),
        ("shared_stop_match", "shared_match", "Shared Stop Match", "TEXT", 30),
        ("shared_stop_score", "shared_score", "Shared Stop Score", "SHORT", None),
        ("recommendation_status", "rec_status", "Recommendation Status", "TEXT", 30),
        ("recommendation_location_score", "rec_loc_score", "Recommendation Location Score", "SHORT", None),
        ("recommended_agency", "rec_agency", "Recommended Agency", "TEXT", 180),
        ("recommended_stop_id", "rec_stop_id", "Recommended Stop ID", "TEXT", 100),
        ("distance_from_recommended_ft", "dist_rec_ft", "Distance From Recommended (ft)", "DOUBLE", None),
        ("location_basis", "loc_basis", "Location Basis", "TEXT", 255),
        ("issue_type", "issue_type", "Issue Type", "TEXT", 100),
        ("issue_confidence", "issue_conf", "Issue Confidence", "TEXT", 20),
        ("route_evidence", "route_ev", "Route Evidence", "TEXT", 100),
        ("road_context", "road_ctx", "Road Context", "TEXT", 100),
        ("road_dist_ft", "road_dist", "Road Distance (ft)", "DOUBLE", None),
        ("farthest_road", "far_road", "Farthest From Road", "TEXT", 1),
        ("tiebreak_rec", "tie_rec", "Tie-Break Recommendation", "TEXT", 1),
        ("boarding_side", "board_side", "Boarding Side Diagnostic", "TEXT", 12),
        ("shared_stop_group_id", "group_id", "Shared Stop Group ID", "TEXT", 40),
        ("physical_location_id", "location_id", "Physical Location ID", "TEXT", 40),
        ("agency", "agency", "Agency", "TEXT", 180),
        ("stop_id", "stop_id", "Stop ID", "TEXT", 100),
        ("stop_name", "stop_name", "Stop Name", "TEXT", 255),
        ("source_key", "source_key", "Source Key", "TEXT", 80),
    ]

    qa_detail_fc = _write_qa_feature_class(
        qa_detail,
        out_gdb,
        "gtfs_stops_qa_detail",
        detail_schema,
    )

    qa_summary_fc = _write_qa_feature_class(
        qa_summary,
        out_gdb,
        "shared_stop_qa_summary",
        summary_schema,
    )

    if add_to_map:
        for path in (
            qa_detail_fc,
            qa_summary_fc,
        ):
            if path:
                _add_outputs_to_current_map(path)

    upstream_group_count = None
    if old_group_path.exists():
        try:
            upstream_group_count = len(pd.read_csv(old_group_path, usecols=[0]))
        except Exception:
            upstream_group_count = None

    candidate_rows = int(
        final_scored["cross_agency_shared_stop_candidate"].astype(str).eq("Y").sum()
    )
    high_groups = int(
        new_groups.get("group_confidence", pd.Series(dtype=str))
        .astype(str).str.lower().eq("high").sum()
    ) if not new_groups.empty else 0
    review_groups = len(new_groups) - high_groups

    print("=" * 78)
    print("SHARED-STOP ANALYSIS COMPLETE")
    print("=" * 78)
    print(f"Full warehouse source rows before cleaning: {len(full):,}")
    print(f"In-scope source rows after source cleaning: {len(source):,}")
    print(f"Source rows excluded by source cleaning: {len(source_exclusions):,}")
    print(f"Cleaned warehouse pair rows: {len(pair):,}")
    print(f"Pair rows scored:           {len(new_pairs):,}")
    print(f"BoardingSide-adjusted pairs: {boarding_adjusted_pairs:,}")
    if upstream_group_count is not None:
        print(f"Upstream groups (refined file): {upstream_group_count:,}")
    print(f"Shared-stop groups:         {len(new_groups):,}")
    print(f"  High groups:              {high_groups:,}")
    print(f"  Review groups:            {review_groups:,}")
    print(f"Records with any <=300-ft cross-operator context: {candidate_rows:,}")
    print(f"Final source rows retained: {len(final_scored):,}")
    if 'qa_detail' in locals():
        print("Final QA Status (all statewide stops):")
        print(qa_detail["qa_status"].value_counts().to_string())
        print(f"Final QA summary stop rows: {len(qa_summary):,}")
    print(f"Resolved recommendation locations: {len(recommendation_summary):,}")
    print(f"Unresolved locations:              {len(unresolved_locations):,}")
    print(f"Potential >25-ft issues:    {len(issue_records):,}")
    print(f"Suppressed spatial outliers:{len(suppressed_issue_candidates):,}")
    if not suppressed_issue_candidates.empty:
        print("Suppressed by reason:")
        print(
            suppressed_issue_candidates["suppression_reason"]
            .value_counts()
            .to_string()
        )
    if not issue_records.empty:
        two_op_issues = int(
            (pd.to_numeric(issue_records["physical_location_operator_count"], errors="coerce") < 3).sum()
        )
        same_agency_issues = int(
            (
                issue_records["likely_incorrect_agency"].astype(str).str.lower()
                ==
                issue_records["recommended_agency"].astype(str).str.lower()
            ).sum()
        )
        print(f"Validation - issues from <3-operator groups: {two_op_issues:,}")
        print(f"Validation - issue agency equals recommended agency: {same_agency_issues:,}")
    if road_context_error:
        print(f"Road-context stage: FAILED - {road_context_error}")
    else:
        print(f"Road-context records:        {len(road_record_context):,}")
        print(f"Road-context groups:         {len(road_group_context):,}")
        if not road_group_context.empty and "road_context_status" in road_group_context.columns:
            print("Road-context group status:")
            print(road_group_context["road_context_status"].value_counts().to_string())

    if shape_context_error:
        print(f"Served-shape stage: FAILED - {shape_context_error}")
    else:
        print(f"Served-shape rows:           {len(shape_rows):,}")

        shape_available = 0
        no_gtfs_shape_id = 0
        shape_targets = len(shape_record_summary)

        if (
            not shape_record_summary.empty
            and "shape_context_status" in shape_record_summary.columns
        ):
            status_counts = (
                shape_record_summary[
                    "shape_context_status"
                ]
                .astype(str)
                .value_counts()
            )

            shape_available = int(
                status_counts.get(
                    "SHAPE_CONTEXT_AVAILABLE",
                    0,
                )
            )

            no_gtfs_shape_id = int(
                status_counts.get(
                    "NO_GTFS_SHAPE_ID",
                    0,
                )
            )

        print(f"Shape target source records: {shape_targets:,}")
        print(f"Shape context available:     {shape_available:,}")
        print(f"No GTFS shape_id:            {no_gtfs_shape_id:,}")
        print(f"Shape-context groups:        {len(shape_group_summary):,}")
        if not shape_group_summary.empty and "shape_group_direction_status" in shape_group_summary.columns:
            print("Shape-direction group status:")
            print(shape_group_summary["shape_group_direction_status"].value_counts().to_string())
        if not unresolved_locations.empty and "shape_recommendation_triage" in unresolved_locations.columns:
            print("Unresolved-location shape triage:")
            print(unresolved_locations["shape_recommendation_triage"].value_counts().to_string())
        if not issue_records.empty and "shape_issue_triage" in issue_records.columns:
            print("Issue-candidate shape triage:")
            print(issue_records["shape_issue_triage"].value_counts().to_string())
    print()
    print(f"Working full CSV: {working_csv}")
    print(f"Slim review CSV:  {slim_csv}")
    print(f"Pairs:            {pair_csv}")
    print(f"Groups:           {group_csv}")
    print(f"Review ZIP:        {review_zip}")
    print(f"Recommendation summary:{recommendation_summary_csv}")
    print(f">25-ft issues:     {issues_csv}")
    print(f"Unresolved locations:{unresolved_csv}")
    print(f"Suppressed outliers:{suppressed_csv}")
    print(f"Road records:       {road_records_csv}")
    print(f"Road groups:        {road_groups_csv}")
    print(f"Served shapes:      {shape_rows_csv}")
    print(f"Shape records:      {shape_records_csv}")
    print(f"Shape groups:       {shape_groups_csv}")
    road_dist_populated = int(pd.to_numeric(
        qa_detail.get("road_dist_ft", pd.Series(dtype=float)),
        errors="coerce",
    ).notna().sum())
    farthest_road_count = int(
        qa_detail.get("farthest_road", pd.Series(dtype=str))
        .astype(str).eq("Y").sum()
    )
    tiebreak_count = int(
        qa_detail.get("tiebreak_rec", pd.Series(dtype=str))
        .astype(str).eq("Y").sum()
    )
    print()
    print("POST-SCORING ROAD FLAGS")
    print(f"RoadDistFt populated: {road_dist_populated:,}")
    print(f"FarthestRoad=Y:       {farthest_road_count:,}")
    print(f"TieBreakRec=Y:        {tiebreak_count:,}")

    boarding_side_counts = (
        qa_detail.get("boarding_side", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .replace("", "NO_DATA")
        .value_counts()
    )
    boarding_clean_total = (
        int((boarding_diag["Clean Distinction"] == "Y").sum())
        if not boarding_diag.empty else 0
    )
    boarding_clean_over25 = (
        int((
            (boarding_diag["Clean Distinction"] == "Y")
            & (boarding_diag["Distance Bucket"] == "OVER_25FT_OR_REVIEW")
        ).sum())
        if not boarding_diag.empty else 0
    )
    boarding_clean_within25 = (
        int((
            (boarding_diag["Clean Distinction"] == "Y")
            & (boarding_diag["Distance Bucket"] == "WITHIN_25FT")
        ).sum())
        if not boarding_diag.empty else 0
    )

    print()
    print("BOARDING-SIDE DIAGNOSTIC (REMAINING UNRESOLVED LOCATIONS)")
    print(boarding_side_counts.to_string())
    print(
        "Unresolved 2-record locations cleanly distinguished: "
        f"{boarding_clean_total:,}"
    )
    print(f"  <=25 ft clean distinctions: {boarding_clean_within25:,}")
    print(f"  >25 ft/review clean distinctions: {boarding_clean_over25:,}")
    print(f"Diagnostic CSV: {boarding_diag_csv}")

    print()
    print("FINAL REVIEW PRODUCTS")
    print(f"QA detail CSV:       {qa_detail_csv}")
    print(f"QA summary CSV:      {qa_summary_csv}")
    print(f"QA detail layer:     {qa_detail_fc}")
    print(f"QA summary layer:    {qa_summary_fc}")
    print(f"Shared-stop candidates:   {shared_stop_candidates_csv}")
    print(f"Stop location issues >25ft:{stop_location_issues_over_25ft_csv}")
    print()
    print("SUPPORT / CALCULATION FEATURE CLASSES (not added to map)")
    print(f"Road context points: {road_points_fc}")
    print(f"Caltrans All Roads:  {road_roads_fc}")
    print(f"Served-shape segments: {shape_segments_fc}")

    result = {
        "source_data_date": source_data_date,
        "output_dir": out_dir,
        "source_run_stamp": source_run_stamp,
        "source_rows_before_cleaning": len(full),
        "source_rows_after_cleaning": len(source),
        "source_rows_excluded": len(source_exclusions),
        "source_exclusion_audit_csv": str(source_exclusion_audit),
        "pair_rows_before_cleaning": pair_preclean_rows,
        "pair_rows_after_cleaning": len(pair),
        "pair_rows_scored": len(new_pairs),
        "upstream_group_count": upstream_group_count,
        "shared_stop_group_count": len(new_groups),
        "high_confidence_group_count": high_groups,
        "review_group_count": review_groups,
        "cross_agency_context_record_count": candidate_rows,
        "resolved_recommendation_location_count": len(recommendation_summary),
        "unresolved_location_count": len(unresolved_locations),
        "stop_location_issue_count": len(issue_records),
        "two_agency_recommendation_count": two_agency_recommended_locations,
        "two_agency_recommendation_within_25ft_count": two_agency_recommended_within25,
        "two_agency_recommendation_over_25ft_count": two_agency_recommended_over25,
        "road_distance_record_count": road_dist_populated,
        "farthest_road_record_count": farthest_road_count,
        "tiebreak_recommendation_count": tiebreak_count,
        "boarding_side_adjusted_pair_count": boarding_adjusted_pairs,
        "boarding_side_clean_distinction_count": boarding_clean_total,
        "boarding_side_clean_distinction_over_25ft_count": boarding_clean_over25,
        "boarding_side_clean_distinction_within_25ft_count": boarding_clean_within25,
        "boarding_side_diagnostic_csv": boarding_diag_csv,
        "suppressed_spatial_outlier_count": len(suppressed_issue_candidates),
        "road_context_record_count": len(road_record_context),
        "road_context_group_count": len(road_group_context),
        "road_context_error": road_context_error,
        "shape_context_error": shape_context_error,
        "served_shape_row_count": len(shape_rows),
        "shape_target_record_count": len(shape_record_summary),
        "shape_context_record_count": (
            int(
                shape_record_summary[
                    "shape_context_status"
                ]
                .astype(str)
                .eq(
                    "SHAPE_CONTEXT_AVAILABLE"
                )
                .sum()
            )
            if (
                not shape_record_summary.empty
                and "shape_context_status"
                    in shape_record_summary.columns
            )
            else len(shape_record_summary)
        ),
        "shape_no_gtfs_shape_id_count": (
            int(
                shape_record_summary[
                    "shape_context_status"
                ]
                .astype(str)
                .eq(
                    "NO_GTFS_SHAPE_ID"
                )
                .sum()
            )
            if (
                not shape_record_summary.empty
                and "shape_context_status"
                    in shape_record_summary.columns
            )
            else 0
        ),
        "shape_context_group_count": len(shape_group_summary),
        "all_stops_scored_full_csv": working_csv,
        "all_stops_scored_review_csv": slim_csv,
        "shared_stop_pairs_csv": pair_csv,
        "shared_stop_groups_csv": group_csv,
        "pair_scoring_review_zip": review_zip,
        "shared_stop_recommendation_summary_csv": recommendation_summary_csv,
        "stop_location_issues_detail_csv": issues_csv,
        "shared_stop_unresolved_locations_csv": unresolved_csv,
        "stop_location_issues_suppressed_csv": suppressed_csv,
        "road_context_records_csv": road_records_csv,
        "road_context_groups_csv": road_groups_csv,
        "served_shape_context_csv": shape_rows_csv,
        "shape_record_summary_csv": shape_records_csv,
        "shape_group_summary_csv": shape_groups_csv,
        "shape_cache_csv": shape_cache_csv,
        "qa_detail_rows": len(qa_detail),
        "qa_summary_rows": len(qa_summary),
        "qa_detail_csv": qa_detail_csv,
        "qa_summary_csv": qa_summary_csv,
        "shared_stop_candidates_csv": shared_stop_candidates_csv,
        "stop_location_issues_over_25ft_csv": stop_location_issues_over_25ft_csv,
        "qa_detail_feature_class": qa_detail_fc,
        "qa_summary_feature_class": qa_summary_fc,
        "road_context_points_feature_class": road_points_fc,
        "road_context_roads_feature_class": road_roads_fc,
        "served_shape_segments_feature_class": shape_segments_fc,
        "analysis_geodatabase": analysis_gdb,
        "run_manifest": manifest_path,
    }

    _write_run_manifest(
        manifest_path,
        result,
        input_files={"stops_curbside_analysis": full_path, "shared_stop_records_scored": candidate_path,
                     "shared_stop_pair_scores": pair_path},
        input_rows={"stops_curbside_analysis": len(full), "shared_stop_records_scored": len(candidate),
                    "shared_stop_pair_scores": pair_preclean_rows},
        config_dir=config_dir,
        config_counts=config_counts,
        config_warnings=config_warnings,
        cache_used=cache_used,
        offline_context_only=offline_context_only,
    )
    return result
