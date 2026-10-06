"""
Pair scoring for the California GTFS shared-stop toolkit.

Purpose
-------
Score nearby stop pairs from DIFFERENT operators and decide which pairs may
describe the same physical passenger boarding point. Pairs come from the
warehouse nearby-pair universe (up to 300 ft). Within 150 ft is the primary
shared-stop range; 150-300 ft is evidence-assisted rescue only and never
connects records into a group.

Then join records into shared-stop groups through connectable pairs.

Source preservation
-------------------
No agency GTFS record is merged, deleted, rewritten, or chosen between here.
Every source record stays in the output. This module only adds review
evidence and shared-stop group IDs.

Group review routing
--------------------
- CONFIRM_SHARED_STOP: coherent high-confidence group; formal confirmation.
- RESOLVE_UNCERTAIN_GROUP: mixed/moderate/incomplete evidence; human resolution.

High-confidence is still a heuristic finding, not physical verification.

Configuration
-------------
Call configure(config_dir) once before scoring. The required tables are read
from the toolkit's config folder. A missing file, a missing or unknown
setting, or a value that cannot be read stops the run with a clear error.
There is no silent fallback to built-in values.
"""

import os
import re
import math
import zipfile
import hashlib
import difflib
from collections import defaultdict
from pathlib import Path

import pandas as pd

# Expected threshold settings and the number type each one is read as.
# (Whole-number settings are compared as int; distances as float.)
threshold_types = {
    "candidate_max_ft": float,
    "primary_max_ft": float,
    "rescue_min_ft": float,
    "rescue_max_ft": float,
    "high_confidence_score": int,
    "likely_score": int,
    "uncertain_score": int,
    "group_edge_min_score": int,
    "group_high_confidence_min_score": int,
    "large_exact_group_caution_size": int,
}

# Every scoring rule the pair scorer uses. All must be present in
# shared_stop_scoring_rules.csv; any other rule name is treated as a typo.
required_scoring_rules = (
    "exact_coordinate",
    "normalized_name_exact",
    "normalized_name_high_similarity",
    "normalized_name_medium_similarity",
    "intersection_signature_exact",
    "shared_name_tokens",
    "same_platform_code",
    "different_platform_code_same_feed",
    "different_platform_code_cross_feed",
    "explicit_different_platform_token",
    "opposite_direction",
    "side_position_conflict",
    "opposite_side_text_conflict",
    "same_parent_station_same_feed",
    "different_parent_station_same_feed",
    "station_vs_boarding_level_conflict",
    "large_exact_coordinate_group",
    "boarding_side_both_likely_same_direction",
    "boarding_side_likely_unlikely_same_direction",
)

# Loaded by configure(config_dir).
thresholds = None
distance_bands = None
scoring_rules = None
final_feature_fields = None


def _clean_pair_text(v):
    return re.sub(r"\s+", " ", str(v if v is not None else "").strip())


def _is_pair_blank(v):
    return _clean_pair_text(v).lower() in {"", "nan", "none", "null", "na", "n/a"}


def _read_config_table(config_dir, name):
    path = Path(config_dir) / name
    if not path.exists():
        raise FileNotFoundError(f"Required config file not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def _require_columns(tbl, columns, name):
    missing = sorted(set(columns) - set(tbl.columns))
    if missing:
        raise ValueError(f"{name} is missing required column(s): {', '.join(missing)}")


def _load_thresholds(config_dir):
    name = "shared_stop_thresholds.csv"
    tbl = _read_config_table(config_dir, name)
    _require_columns(tbl, {"setting", "value"}, name)
    loaded = {}
    for _, r in tbl.iterrows():
        key = _clean_pair_text(r.get("setting"))
        if not key:
            continue
        if key not in threshold_types:
            raise ValueError(f"{name}: unknown setting '{key}' (check spelling)")
        if key in loaded:
            raise ValueError(f"{name}: setting '{key}' appears more than once")
        try:
            raw = float(r.get("value"))
        except Exception:
            raise ValueError(f"{name}: setting '{key}' has a value that is not a number: {r.get('value')!r}")
        loaded[key] = int(raw) if threshold_types[key] is int else float(raw)
    missing = [k for k in threshold_types if k not in loaded]
    if missing:
        raise ValueError(f"{name} is missing required setting(s): {', '.join(missing)}")
    return {k: loaded[k] for k in threshold_types}


def _load_distance_bands(config_dir):
    name = "shared_stop_distance_bands.csv"
    tbl = _read_config_table(config_dir, name)
    _require_columns(tbl, {"min_ft", "max_ft", "base_score", "label"}, name)
    rows = []
    for i, r in tbl.iterrows():
        try:
            rows.append({
                "min_ft": float(r.get("min_ft", 0) or 0),
                "max_ft": float(r.get("max_ft", 0) or 0),
                "base_score": int(float(r.get("base_score", 0) or 0)),
                "label": _clean_pair_text(r.get("label", "")),
            })
        except Exception:
            raise ValueError(f"{name}: row {i + 2} has a value that cannot be read")
    if not rows:
        raise ValueError(f"{name} has no distance bands")
    return rows


def _load_scoring_rules(config_dir):
    name = "shared_stop_scoring_rules.csv"
    tbl = _read_config_table(config_dir, name)
    _require_columns(tbl, {"rule", "score_delta"}, name)
    loaded = {}
    for _, r in tbl.iterrows():
        key = _clean_pair_text(r.get("rule"))
        if not key:
            continue
        if key not in required_scoring_rules:
            raise ValueError(f"{name}: unknown rule '{key}' (check spelling)")
        if key in loaded:
            raise ValueError(f"{name}: rule '{key}' appears more than once")
        try:
            loaded[key] = int(float(r.get("score_delta", 0) or 0))
        except Exception:
            raise ValueError(f"{name}: rule '{key}' has a score_delta that is not a number")
    missing = [k for k in required_scoring_rules if k not in loaded]
    if missing:
        raise ValueError(f"{name} is missing required rule(s): {', '.join(missing)}")
    return {k: loaded[k] for k in required_scoring_rules}


def _load_final_feature_fields(config_dir):
    name = "final_feature_fields.csv"
    tbl = _read_config_table(config_dir, name)
    _require_columns(tbl, {"field_name"}, name)
    if "display_order" in tbl.columns:
        tbl["_order"] = pd.to_numeric(tbl["display_order"], errors="coerce").fillna(999999)
        tbl = tbl.sort_values("_order")
    vals = [_clean_pair_text(v) for v in tbl["field_name"] if _clean_pair_text(v)]
    if not vals:
        raise ValueError(f"{name} lists no fields")
    return vals


def configure(config_dir):
    """Load the required pair-scoring config tables. Returns row counts per file."""
    global thresholds, distance_bands, scoring_rules, final_feature_fields
    thresholds = _load_thresholds(config_dir)
    distance_bands = _load_distance_bands(config_dir)
    scoring_rules = _load_scoring_rules(config_dir)
    final_feature_fields = _load_final_feature_fields(config_dir)
    counts = {
        "shared_stop_thresholds.csv": len(thresholds),
        "shared_stop_distance_bands.csv": len(distance_bands),
        "shared_stop_scoring_rules.csv": len(scoring_rules),
        "final_feature_fields.csv": len(final_feature_fields),
    }
    for name, n in counts.items():
        print(f"[config] {name}: {n} row(s) loaded from {Path(config_dir) / name}")
    return counts


def _require_configured():
    if thresholds is None or scoring_rules is None or distance_bands is None:
        raise RuntimeError("pair_scoring.configure(config_dir) must be called before scoring.")


def _get_distance_band(distance_ft):
    for b in distance_bands:
        if distance_ft >= b["min_ft"] - 1e-9 and distance_ft <= b["max_ft"] + 1e-9:
            return b
    return {"min_ft": 0, "max_ft": thresholds["candidate_max_ft"], "base_score": 0, "label": "outside configured band"}


def _normalize_stop_name(v):
    s = _clean_pair_text(v).lower().replace("&", " and ")
    s = re.sub(r"\b(?:northbound|southbound|eastbound|westbound|n/b|s/b|e/b|w/b|nb|sb|eb|wb)\b", " ", s)
    s = re.sub(r"\b(?:far side|near side|farside|nearside|opposite|opp)\b", " ", s)
    s = re.sub(r"\b(?:street|st\.?|avenue|ave\.?|av\.?|boulevard|blvd\.?|road|rd\.?|drive|dr\.?|highway|hwy\.?|parkway|pkwy\.?)\b", " ", s)
    s = re.sub(r"\b(?:stop|station)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokenize_stop_name(v):
    return {t for t in _normalize_stop_name(v).split() if len(t) >= 2}


def _intersection_signature(v):
    """
    Return a normalized two-part intersection signature when the stop name uses
    an explicit intersection delimiter such as &, /, @, "at", or "and".

    Accept delimiters with or without surrounding spaces and remove a
    trailing two-letter compass corner suffix (NE/NW/SE/SW) from a street
    segment. A bare hyphen is intentionally NOT treated as an intersection
    delimiter by itself because many facilities/place names legitimately
    contain hyphens.
    """
    raw = _clean_pair_text(v)

    # "Park and Ride" and "Kiss and Ride" are facility names, not
    # intersections. Protect them before using "and" as a separator.
    split_text = re.sub(
        r"\b(?:park|kiss)\s+and\s+ride\b",
        lambda m: m.group(0).replace(" ", "_"),
        raw,
        flags=re.I,
    )

    parts = re.split(
        r"(?:\s*&\s*|\s*/\s*|\s*@\s*|\s+at\s+|\s+and\s+)",
        split_text,
        flags=re.I,
    )

    cleaned = []
    for p in parts:
        n = _normalize_stop_name(p)
        if not n:
            continue
        toks = n.split()
        if len(toks) > 1 and toks[-1] in {"ne", "nw", "se", "sw"}:
            toks = toks[:-1]
        n = " ".join(toks).strip()
        if n:
            cleaned.append(n)

    return " & ".join(sorted(cleaned[:2])) if len(cleaned) >= 2 else ""


def _intersection_signature_tokens(signature):
    out = set()
    for part in _clean_pair_text(signature).split(" & "):
        out.update(t for t in _tokenize_stop_name(part) if t not in {"and", "at", "ne", "nw", "se", "sw"})
    return out


def _identity_name_tokens(v):
    return {
        t for t in _tokenize_stop_name(v)
        if t not in {"and", "at", "ne", "nw", "se", "sw"}
    }


def _operator_key(row):
    # Prefer the cleaned agency name. Fallbacks keep pair scoring usable when
    # attribution is incomplete, but the key is still only a grouping aid.
    for c in ["agency_name", "GTFS_agency_id", "feed_name"]:
        v = _clean_pair_text(row.get(c, ""))
        if v:
            return v.lower()
    return "unresolved"


def _side_position_set(row):
    """Keep side-of-intersection clues separate from the normalized name."""
    blob = " | ".join(
        _clean_pair_text(row.get(c, ""))
        for c in [
            "GTFS_stop_name",
            "GTFS_tts_stop_name",
            "GTFS_stop_desc",
            "attribute_detected",
        ]
    ).lower()

    out = set()
    if re.search(r"\b(?:near\s*side|nearside)\b", blob, re.I):
        out.add("NEAR_SIDE")
    if re.search(r"\b(?:far\s*side|farside)\b", blob, re.I):
        out.add("FAR_SIDE")
    if re.search(r"\b(?:opposite|opp)\b", blob, re.I):
        out.add("OPPOSITE")
    return out


def _has_side_position_conflict(a, b, normalized_name_a="", normalized_name_b=""):
    """Return a hard conflict when stop text clearly points to different sides."""
    sa = _side_position_set(a)
    sb = _side_position_set(b)
    if (("NEAR_SIDE" in sa and "FAR_SIDE" in sb) or ("FAR_SIDE" in sa and "NEAR_SIDE" in sb)):
        return "NEAR_SIDE_VS_FAR_SIDE"
    if (("OPPOSITE" in sa) != ("OPPOSITE" in sb) and normalized_name_a and normalized_name_a == normalized_name_b):
        return "OPPOSITE_SIDE_TEXT"
    return ""


def _direction_set(row):
    blob = " | ".join(_clean_pair_text(row.get(c, "")) for c in [
        "GTFS_stop_name", "GTFS_tts_stop_name", "GTFS_stop_desc", "attribute_detected"
    ]).lower()
    out = set()
    if re.search(r"\b(?:northbound|north bound|n/b|nb)\b", blob, re.I): out.add("N")
    if re.search(r"\b(?:southbound|south bound|s/b|sb)\b", blob, re.I): out.add("S")
    if re.search(r"\b(?:eastbound|east bound|e/b|eb)\b", blob, re.I): out.add("E")
    if re.search(r"\b(?:westbound|west bound|w/b|wb)\b", blob, re.I): out.add("W")
    return out


def _has_opposite_direction(a, b):
    return bool(("N" in a and "S" in b) or ("S" in a and "N" in b) or ("E" in a and "W" in b) or ("W" in a and "E" in b))


def _platform_tokens(row):
    text = " | ".join(_clean_pair_text(row.get(c, "")) for c in ["GTFS_stop_name", "GTFS_tts_stop_name", "GTFS_stop_desc", "attribute_detected"])
    found = set()
    for rx, prefix in [
        (r"\bplatform\s*#?\s*([A-Za-z0-9]+)", "platform"),
        (r"\bbay\s*#?\s*([A-Za-z0-9]+)", "bay"),
        (r"\bgate\s*#?\s*([A-Za-z0-9]+)", "gate"),
        (r"\btrack\s*#?\s*([A-Za-z0-9]+)", "track"),
    ]:
        for m in re.finditer(rx, text, re.I):
            found.add(prefix + ":" + m.group(1).lower())
    return found


def _location_type(row):
    v = _clean_pair_text(row.get("GTFS_location_type", ""))
    return "0" if v == "" else v


def _exact_coordinate_group_size(row):
    try:
        return int(float(row.get("exact_coordinate_group_size", 1) or 1))
    except Exception:
        return 1


def _haversine_ft(lat1, lon1, lat2, lon2):
    radius_m = 6371008.8
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1)); dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 3.280839895 * (2 * radius_m * math.asin(min(1.0, math.sqrt(a))))


def _stable_id(prefix, values, chars=12):
    seed = "|".join(sorted(_clean_pair_text(v) for v in values if _clean_pair_text(v)))
    return prefix + hashlib.sha1(seed.encode("utf-8", errors="ignore")).hexdigest()[:chars]


def _score_pair(a, b, distance_ft, pair_context=None):
    band = _get_distance_band(distance_ft)
    score = int(band["base_score"])
    evidence = [f"distance={distance_ft:.1f} ft ({band['label']})"]
    hard_conflicts = []
    cautions = []

    exact_name = False
    high_name = False
    intersection_exact = False
    shared_tokens = False

    if distance_ft < 0.05:
        score += scoring_rules.get("exact_coordinate", 35)
        evidence.append("exact coordinates")

    an, bn = _normalize_stop_name(a.get("GTFS_stop_name", "")), _normalize_stop_name(b.get("GTFS_stop_name", ""))

    side_conflict = _has_side_position_conflict(a, b, an, bn)
    if side_conflict == "NEAR_SIDE_VS_FAR_SIDE":
        score += scoring_rules.get("side_position_conflict", -50)
        hard_conflicts.append("NEAR_SIDE_VS_FAR_SIDE")
        evidence.append("near-side vs far-side stop-position conflict")
    elif side_conflict == "OPPOSITE_SIDE_TEXT":
        score += scoring_rules.get("opposite_side_text_conflict", -50)
        hard_conflicts.append("OPPOSITE_SIDE_TEXT")
        evidence.append("opposite-side stop text conflict")

    sa = _side_position_set(a)
    sb = _side_position_set(b)
    if not side_conflict and sa != sb and (sa or sb) and not (sa and sb):
        cautions.append("SIDE_POSITION_UNSPECIFIED_OTHER_RECORD")
        evidence.append("side-position wording present in only one record")

    similarity = 0.0
    if an and bn:
        similarity = difflib.SequenceMatcher(None, an, bn).ratio()
        if an == bn:
            exact_name = True
            high_name = True
            score += scoring_rules.get("normalized_name_exact", 25)
            evidence.append("normalized stop names exact")
        elif similarity >= 0.88:
            high_name = True
            score += scoring_rules.get("normalized_name_high_similarity", 18)
            evidence.append(f"high name similarity={similarity:.2f}")
        elif similarity >= 0.72:
            score += scoring_rules.get("normalized_name_medium_similarity", 8)
            evidence.append(f"medium name similarity={similarity:.2f}")
        common = _tokenize_stop_name(a.get("GTFS_stop_name", "")) & _tokenize_stop_name(b.get("GTFS_stop_name", ""))
        if len(common) >= 2:
            shared_tokens = True
            score += scoring_rules.get("shared_name_tokens", 8)
            evidence.append("shared stop-name tokens")

    ia, ib = _intersection_signature(a.get("GTFS_stop_name", "")), _intersection_signature(b.get("GTFS_stop_name", ""))
    if ia and ib and ia == ib:
        intersection_exact = True
        score += scoring_rules.get("intersection_signature_exact", 20)
        evidence.append("same normalized intersection")
    elif ia and not ib:
        # Cross-format case such as "Main / 1st" vs "MAIN-1ST".
        # Require the explicit-delimiter side's two street-token set to match
        # the other name exactly after removing connector/corner tokens.
        sig_tokens = _intersection_signature_tokens(ia)
        other_tokens = _identity_name_tokens(b.get("GTFS_stop_name", ""))
        if len(sig_tokens) >= 2 and sig_tokens == other_tokens:
            intersection_exact = True
            score += scoring_rules.get("intersection_signature_exact", 20)
            evidence.append("same normalized intersection (cross-format)")
    elif ib and not ia:
        sig_tokens = _intersection_signature_tokens(ib)
        other_tokens = _identity_name_tokens(a.get("GTFS_stop_name", ""))
        if len(sig_tokens) >= 2 and sig_tokens == other_tokens:
            intersection_exact = True
            score += scoring_rules.get("intersection_signature_exact", 20)
            evidence.append("same normalized intersection (cross-format)")

    # Cross-operator status selects the pair; it does not add same-stop evidence.
    evidence.append("cross-operator pair (selection criterion; 0 score)")

    same_feed = _clean_pair_text(a.get("feed_name", "")) == _clean_pair_text(b.get("feed_name", "")) and not _is_pair_blank(a.get("feed_name", ""))
    pa, pb = _clean_pair_text(a.get("GTFS_platform_code", "")).lower(), _clean_pair_text(b.get("GTFS_platform_code", "")).lower()
    if pa and pb:
        if pa == pb:
            score += scoring_rules.get("same_platform_code", 6); evidence.append("same explicit platform_code")
        elif same_feed:
            score += scoring_rules.get("different_platform_code_same_feed", -45)
            hard_conflicts.append("DIFFERENT_PLATFORM_OR_BAY_SAME_FEED")
            evidence.append("different platform_code within same feed")
        else:
            score += scoring_rules.get("different_platform_code_cross_feed", -20)
            cautions.append("CROSS_FEED_PLATFORM_CODE_DIFFERENCE")
            evidence.append("different platform_code across feeds (caution; identifiers are feed-specific)")

    pta, ptb = _platform_tokens(a), _platform_tokens(b)
    if pta and ptb and pta != ptb:
        score += scoring_rules.get("explicit_different_platform_token", -45)
        hard_conflicts.append("EXPLICIT_DIFFERENT_PLATFORM_OR_BAY")
        evidence.append("different explicit platform/bay/gate/track in stop text")

    da, db = _direction_set(a), _direction_set(b)
    if da and db and _has_opposite_direction(da, db):
        score += scoring_rules.get("opposite_direction", -50)
        hard_conflicts.append("OPPOSITE_DIRECTION")
        evidence.append("opposite direction evidence")

    # parent_station is feed-local; raw values are comparable only inside one feed.
    if same_feed:
        psa, psb = _clean_pair_text(a.get("GTFS_parent_station", "")), _clean_pair_text(b.get("GTFS_parent_station", ""))
        if psa and psb and psa == psb:
            score += scoring_rules.get("same_parent_station_same_feed", 10); evidence.append("same parent_station within one feed")
        elif psa and psb and psa != psb:
            score += scoring_rules.get("different_parent_station_same_feed", -25)
            hard_conflicts.append("DIFFERENT_PARENT_STATION_SAME_FEED")
            evidence.append("different parent_station within one feed")

    lta, ltb = _location_type(a), _location_type(b)
    if ({lta, ltb} & {"1"}) and ({lta, ltb} & {"0", "4"}):
        score += scoring_rules.get("station_vs_boarding_level_conflict", -35)
        hard_conflicts.append("STATION_VS_BOARDING_LEVEL")
        evidence.append("station-level vs boarding-level record")

    if max(_exact_coordinate_group_size(a), _exact_coordinate_group_size(b)) >= int(thresholds["large_exact_group_caution_size"]):
        score += scoring_rules.get("large_exact_coordinate_group", -15)
        cautions.append("LARGE_EXACT_COORDINATE_GROUP")
        evidence.append("large exact-coordinate subgroup context")

    # Boarding-side evidence from served-shape direction context.
    # Only use it when served-shape evidence says both records represent
    # substantially the same direction of travel. This prevents left/right
    # geometry from being treated as a conflict when the routes are simply
    # moving in different directions.
    if pair_context is None:
        pair_context = {}
    pair_direction_status = _clean_pair_text(
        pair_context.get("shape_pair_direction_status", "")
    ).upper()
    same_direction_pair = pair_direction_status.startswith("SAME_DIRECTION")

    boarding_a = _clean_pair_text(a.get("boarding_side", "")).upper()
    boarding_b = _clean_pair_text(b.get("boarding_side", "")).upper()

    if same_direction_pair:
        if boarding_a == "LIKELY" and boarding_b == "LIKELY":
            score += scoring_rules.get(
                "boarding_side_both_likely_same_direction",
                4,
            )
            evidence.append(
                "both points on plausible curbside for same-direction served routes"
            )
        elif {boarding_a, boarding_b} == {"LIKELY", "UNLIKELY"}:
            score += scoring_rules.get(
                "boarding_side_likely_unlikely_same_direction",
                -6,
            )
            cautions.append("BOARDING_SIDE_POSITION_DISAGREEMENT")
            evidence.append(
                "same-direction served routes but one point is on implausible boarding side"
            )

    score = max(0, min(100, int(round(score))))
    primary_max = float(thresholds["primary_max_ft"])
    rescue_min = float(thresholds.get("rescue_min_ft", primary_max))
    rescue_max = float(thresholds.get("rescue_max_ft", thresholds["candidate_max_ft"]))
    # Rescue is review-only. Distance contributes no positive points in this
    # band, so use strong identity evidence and no hard physical conflict.
    strong_identity = bool(
        exact_name
        or (high_name and intersection_exact)
        or (intersection_exact and shared_tokens)
    )
    rescue_eligible = bool(
        distance_ft > rescue_min
        and distance_ft <= rescue_max
        and strong_identity
        and not hard_conflicts
    )

    if hard_conflicts:
        classification = "Likely Separate Physical Points"
    elif distance_ft <= primary_max and score >= int(thresholds["high_confidence_score"]) and not cautions:
        classification = "High-Confidence Shared Stop Candidate"
    elif distance_ft <= primary_max and score >= int(thresholds["likely_score"]):
        classification = "Likely Shared Stop Candidate"
    elif distance_ft <= primary_max and score >= int(thresholds["uncertain_score"]):
        classification = "Uncertain Shared Stop Candidate"
    elif rescue_eligible:
        classification = "Evidence-Assisted Rescue Candidate"
        cautions.append("RESCUE_DISTANCE_150_300_FT")
        evidence.append("150-300 ft rescue: review candidate only; does not connect groups")
    else:
        classification = "Context Only / Not Shared Stop Candidate"

    if classification == "High-Confidence Shared Stop Candidate":
        review_required, review_type = "Y", "CONFIRM_SHARED_STOP"
    elif classification in {"Likely Shared Stop Candidate", "Uncertain Shared Stop Candidate", "Evidence-Assisted Rescue Candidate"}:
        review_required, review_type = "Y", "RESOLVE_UNCERTAIN_GROUP"
    elif hard_conflicts and score >= int(thresholds["uncertain_score"]):
        review_required, review_type = "Y", "RESOLVE_UNCERTAIN_GROUP"
    else:
        review_required, review_type = "N", ""

    return {
        "shared_stop_score": score,
        "shared_stop_classification": classification,
        "shared_stop_evidence": "; ".join(evidence),
        "shared_stop_conflict_codes": " | ".join(sorted(set(hard_conflicts))),
        "shared_stop_caution_codes": " | ".join(sorted(set(cautions))),
        "shared_stop_name_similarity": round(similarity, 3),
        "strong_identity_evidence": "Y" if strong_identity else "N",
        "rescue_eligible": "Y" if rescue_eligible else "N",
        "shared_stop_review_required": review_required,
        "shared_stop_review_type": review_type,
        "distance_band": band["label"],
    }


def _pair_can_connect(scored, distance_ft):
    if _clean_pair_text(scored.get("shared_stop_conflict_codes", "")):
        return False
    primary_max = float(thresholds["primary_max_ft"])
    if distance_ft <= primary_max:
        return int(scored["shared_stop_score"]) >= int(thresholds["group_edge_min_score"])
    # Rescue candidates are review-only. They are retained in the pair
    # output but do not connect records into a shared-stop group.
    return False


class DisjointSet:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[rb] = ra


def _group_max_span_ft(member_rows):
    coords=[]
    for r in member_rows:
        try: coords.append((float(r.get("GTFS_stop_lat")), float(r.get("GTFS_stop_lon"))))
        except Exception: pass
    mx=0.0
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            mx=max(mx, _haversine_ft(coords[i][0],coords[i][1],coords[j][0],coords[j][1]))
    return mx


def build_shared_stop_analysis(source_df, relationship_pairs):
    _require_configured()
    required_source = {"source_key", "agency_name", "feed_name", "GTFS_stop_id", "GTFS_stop_name", "GTFS_stop_lat", "GTFS_stop_lon"}
    missing = sorted(required_source - set(source_df.columns))
    if missing:
        raise RuntimeError("Pair scoring needs the prepared analysis source. Missing fields: " + ", ".join(missing))

    out = source_df.copy()
    for c in [
        "cross_agency_shared_stop_candidate", "shared_stop_group_id", "shared_stop_group_recommendation",
        "shared_stop_confidence", "shared_stop_best_score", "shared_stop_pair_count",
        "shared_stop_nearest_distance_ft", "shared_stop_best_match_source_key",
        "shared_stop_best_match_agency_name", "shared_stop_evidence_summary", "shared_stop_conflict_codes",
        "shared_stop_operator_count", "shared_stop_group_review_required", "shared_stop_group_review_type",
    ]:
        out[c] = ""

    out["_original_index"] = out.index
    rows_by_key = {}
    idx_by_key = {}
    for _, r in out.iterrows():
        sk = _clean_pair_text(r.get("source_key", ""))
        if sk:
            rows_by_key[sk] = r.to_dict(); idx_by_key[sk] = int(r["_original_index"])

    rel = relationship_pairs.copy()
    rel["_pair_distance_ft"] = pd.to_numeric(rel.get("distance_ft", ""), errors="coerce")
    rel = rel[rel["_pair_distance_ft"].notna() & rel["_pair_distance_ft"].le(float(thresholds["candidate_max_ft"]))].copy()

    dsu = DisjointSet(len(out))
    pair_rows=[]
    candidate_pairs_by_index=defaultdict(list)
    pair_lookup={}

    for _, rp in rel.iterrows():
        ska, skb = _clean_pair_text(rp.get("source_key_a", "")), _clean_pair_text(rp.get("source_key_b", ""))
        if ska not in rows_by_key or skb not in rows_by_key or ska == skb:
            continue
        a, b = rows_by_key[ska], rows_by_key[skb]
        opa, opb = _operator_key(a), _operator_key(b)
        if opa == opb:
            continue
        dist = float(rp["_pair_distance_ft"])
        scored = _score_pair(a, b, dist, rp)
        rec={
            "relationship_id": _clean_pair_text(rp.get("relationship_id", "")),
            "source_key_a": ska, "source_key_b": skb,
            "operator_a": opa, "operator_b": opb,
            "agency_name_a": _clean_pair_text(a.get("agency_name", "")),
            "agency_name_b": _clean_pair_text(b.get("agency_name", "")),
            "feed_name_a": _clean_pair_text(a.get("feed_name", "")), "feed_name_b": _clean_pair_text(b.get("feed_name", "")),
            "stop_id_a": _clean_pair_text(a.get("GTFS_stop_id", "")), "stop_id_b": _clean_pair_text(b.get("GTFS_stop_id", "")),
            "stop_name_a": _clean_pair_text(a.get("GTFS_stop_name", "")), "stop_name_b": _clean_pair_text(b.get("GTFS_stop_name", "")),
            "platform_code_a": _clean_pair_text(a.get("GTFS_platform_code", "")), "platform_code_b": _clean_pair_text(b.get("GTFS_platform_code", "")),
            "parent_station_a": _clean_pair_text(a.get("GTFS_parent_station", "")), "parent_station_b": _clean_pair_text(b.get("GTFS_parent_station", "")),
            "location_type_a": _clean_pair_text(a.get("GTFS_location_type", "")), "location_type_b": _clean_pair_text(b.get("GTFS_location_type", "")),
            "exact_coordinate_group_size_a": _exact_coordinate_group_size(a), "exact_coordinate_group_size_b": _exact_coordinate_group_size(b),
            "distance_ft": round(dist,2),
            **scored,
        }
        pair_rows.append(rec)
        ia, ib = idx_by_key[ska], idx_by_key[skb]
        candidate_pairs_by_index[ia].append((rec, skb, b))
        candidate_pairs_by_index[ib].append((rec, ska, a))
        pair_lookup[frozenset([ska,skb])] = rec
        if _pair_can_connect(scored, dist):
            dsu.union(ia,ib)

    pair_df=pd.DataFrame(pair_rows)

    members_by_root=defaultdict(list)
    grouped_indices=set()
    for idx in range(len(out)):
        root=dsu.find(idx); members_by_root[root].append(idx)

    group_rows=[]; group_id_by_idx={}; group_rec_by_id={}
    out_records={int(r["_original_index"]):r for _,r in out.iterrows()}
    for members in members_by_root.values():
        if len(members)<2: continue
        # A component is only a shared-stop group when it contains at least one qualifying edge.
        has_edge=False
        for i in range(len(members)):
            for j in range(i+1,len(members)):
                ka=_clean_pair_text(out_records[members[i]].get("source_key","")); kb=_clean_pair_text(out_records[members[j]].get("source_key",""))
                p=pair_lookup.get(frozenset([ka,kb]))
                if p and _pair_can_connect(p, float(p["distance_ft"])): has_edge=True
        if not has_edge: continue

        member_rows=[out_records[i] for i in members]
        keys=[_clean_pair_text(r.get("source_key","")) for r in member_rows]
        gid=_stable_id("SSG_", [r.get("source_key","") for r in member_rows])
        for i in members: group_id_by_idx[i]=gid; grouped_indices.add(i)

        expected_cross=0; observed=[]
        for i in range(len(member_rows)):
            for j in range(i+1,len(member_rows)):
                if _operator_key(member_rows[i]) == _operator_key(member_rows[j]):
                    continue
                expected_cross += 1
                p=pair_lookup.get(frozenset([keys[i],keys[j]]))
                if p: observed.append(p)
        if not observed: continue

        scores=[int(p["shared_stop_score"]) for p in observed]
        dists=[float(p["distance_ft"]) for p in observed]
        conflicts=sorted({c for p in observed for c in _clean_pair_text(p.get("shared_stop_conflict_codes","")).split(" | ") if c})
        cautions=sorted({c for p in observed for c in _clean_pair_text(p.get("shared_stop_caution_codes","")).split(" | ") if c})
        operators=sorted({_operator_key(r) for r in member_rows})
        complete=(len(observed)==expected_cross)
        max_span=_group_max_span_ft(member_rows)
        high_pairs=sum(1 for p in observed if p["shared_stop_classification"]=="High-Confidence Shared Stop Candidate")
        likely_pairs=sum(1 for p in observed if p["shared_stop_classification"]=="Likely Shared Stop Candidate")
        exact_pairs=sum(1 for d in dists if d<0.05)
        rescue_pairs=sum(1 for p in observed if p.get("rescue_eligible") == "Y")
        all_strong=complete and all(s>=int(thresholds["group_high_confidence_min_score"]) for s in scores)

        if all_strong and rescue_pairs == 0 and not conflicts and not cautions and max_span <= float(thresholds["primary_max_ft"]):
            recommendation="High-Confidence Shared Stop Candidate"
            confidence="High"
            review_type="CONFIRM_SHARED_STOP"
            review_reason="Strong, coherent cross-operator evidence; formal confirmation requested"
        else:
            recommendation="Uncertain Shared Stop Group"
            confidence="Review"
            review_type="RESOLVE_UNCERTAIN_GROUP"
            bits=[]
            if conflicts: bits.append("physical-separation conflict evidence")
            if cautions: bits.append("caution evidence")
            if not complete: bits.append("incomplete cross-operator pair graph")
            if rescue_pairs: bits.append(f"{rescue_pairs} evidence-assisted rescue pair(s) in 150-300 ft range")
            if max_span > float(thresholds["primary_max_ft"]): bits.append(f"group span {max_span:.1f} ft exceeds primary range")
            if min(scores) < int(thresholds["group_high_confidence_min_score"]): bits.append("not all pair scores meet high-confidence threshold")
            review_reason="; ".join(bits) or "Automated evidence is not sufficient for a definitive physical-stop determination"

        gr={
            "shared_stop_group_id":gid,
            "record_count":len(member_rows),
            "operator_count":len(operators),
            "operators":" | ".join(operators),
            "source_keys":" | ".join(keys),
            "stop_names":" | ".join(sorted({_clean_pair_text(r.get('GTFS_stop_name','')) for r in member_rows if _clean_pair_text(r.get('GTFS_stop_name',''))})),
            "cross_operator_pair_count_observed":len(observed),
            "cross_operator_pair_count_expected":expected_cross,
            "complete_cross_operator_pair_graph":"Y" if complete else "N",
            "min_shared_stop_score":min(scores),
            "max_shared_stop_score":max(scores),
            "mean_shared_stop_score":round(sum(scores)/len(scores),1),
            "max_group_span_ft":round(max_span,2),
            "exact_coordinate_pair_count":exact_pairs,
            "high_confidence_pair_count":high_pairs,
            "likely_pair_count":likely_pairs,
            "rescue_pair_count":rescue_pairs,
            "conflict_codes":" | ".join(conflicts),
            "caution_codes":" | ".join(cautions),
            "group_recommendation":recommendation,
            "group_confidence":confidence,
            "group_review_required":"Y",
            "group_review_type":review_type,
            "group_review_reason":review_reason,
        }
        group_rows.append(gr); group_rec_by_id[gid]=gr

    group_df=pd.DataFrame(group_rows)

    # Record-level summaries keep every source field and append pair-scoring evidence.
    for idx, r in out.iterrows():
        pairs_here=candidate_pairs_by_index.get(idx,[])
        if not pairs_here:
            out.at[idx,"cross_agency_shared_stop_candidate"]="N"
            out.at[idx,"shared_stop_pair_count"]="0"
            continue
        out.at[idx,"cross_agency_shared_stop_candidate"]="Y"
        out.at[idx,"shared_stop_pair_count"]=str(len(pairs_here))
        out.at[idx,"shared_stop_nearest_distance_ft"]=f"{min(float(x[0]['distance_ft']) for x in pairs_here):.2f}"
        ops={_operator_key(r.to_dict())}
        for _,_,other in pairs_here: ops.add(_operator_key(other))
        out.at[idx,"shared_stop_operator_count"]=str(len(ops))
        best=sorted(pairs_here, key=lambda x:(-int(x[0]["shared_stop_score"]), float(x[0]["distance_ft"])))[0]
        bp,bkey,brow=best
        out.at[idx,"shared_stop_best_score"]=str(bp["shared_stop_score"])
        out.at[idx,"shared_stop_best_match_source_key"]=bkey
        out.at[idx,"shared_stop_best_match_agency_name"]=_clean_pair_text(brow.get("agency_name",""))
        out.at[idx,"shared_stop_evidence_summary"]=f"{bp['shared_stop_classification']}; {bp['shared_stop_evidence']}"
        hard=sorted({c for p,_,_ in pairs_here for c in _clean_pair_text(p.get("shared_stop_conflict_codes","")).split(" | ") if c})
        out.at[idx,"shared_stop_conflict_codes"]=" | ".join(hard)
        gid=group_id_by_idx.get(idx,"")
        out.at[idx,"shared_stop_group_id"]=gid
        if gid and gid in group_rec_by_id:
            gr=group_rec_by_id[gid]
            out.at[idx,"shared_stop_group_recommendation"]=gr["group_recommendation"]
            out.at[idx,"shared_stop_confidence"]=gr["group_confidence"]
            out.at[idx,"shared_stop_operator_count"]=str(gr["operator_count"])
            out.at[idx,"shared_stop_group_review_required"]=gr["group_review_required"]
            out.at[idx,"shared_stop_group_review_type"]=gr["group_review_type"]
            if gr["conflict_codes"]:
                out.at[idx,"shared_stop_conflict_codes"]=gr["conflict_codes"]
            out.at[idx,"shared_stop_evidence_summary"]=(out.at[idx,"shared_stop_evidence_summary"] + "; group: " + gr["group_review_reason"])[-1500:]
        else:
            any_hard=bool(hard); any_caution=any(bool(_clean_pair_text(p.get("shared_stop_caution_codes",""))) for p,_,_ in pairs_here)
            out.at[idx,"shared_stop_group_recommendation"]="Weak / Likely Separate Candidate(s)"
            out.at[idx,"shared_stop_confidence"]="Conflict" if any_hard else ("Low" if not any_caution else "Low / Caution")
            out.at[idx,"shared_stop_group_review_required"]="N"
            out.at[idx,"shared_stop_group_review_type"]=""

    out=out.drop(columns=["_original_index"], errors="ignore")
    return out, pair_df, group_df


def _clear_directory(path):
    os.makedirs(path, exist_ok=True)
    for fn in os.listdir(path):
        p=os.path.join(path,fn)
        if os.path.isfile(p): os.remove(p)


def _zip_directory(folder, zip_path):
    if os.path.exists(zip_path): os.remove(zip_path)
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as zf:
        for root,_,files in os.walk(folder):
            for fn in files:
                p=os.path.join(root,fn); zf.write(p,arcname=os.path.relpath(p,folder))


def write_pair_scoring_review_outputs(pairs_df, groups_df, review_dir, review_zip):
    """Write the pair-scoring review folder and zip it.

    The folder is emptied (files only) before writing, so it must be the
    dedicated pair_scoring_review folder, never a general output folder.
    """
    if Path(review_dir).name != "pair_scoring_review":
        raise ValueError(f"Refusing to clear a folder not named pair_scoring_review: {review_dir}")
    review_dir_text = str(review_dir)
    _clear_directory(review_dir_text)
    pairs_df.to_csv(os.path.join(review_dir_text,"00_shared_stop_pairs_all.csv"),index=False)
    pairs_df.to_csv(os.path.join(review_dir_text,"01_cross_operator_candidate_pairs.csv"),index=False)
    if not pairs_df.empty:
        pairs_df[pairs_df["shared_stop_classification"].eq("High-Confidence Shared Stop Candidate")].to_csv(os.path.join(review_dir_text,"02_high_confidence_shared_stop_pairs.csv"),index=False)
        pairs_df[pairs_df["shared_stop_review_type"].eq("RESOLVE_UNCERTAIN_GROUP")].to_csv(os.path.join(review_dir_text,"03_pairs_for_uncertainty_resolution.csv"),index=False)
        pairs_df[pairs_df["shared_stop_classification"].eq("Likely Separate Physical Points")].to_csv(os.path.join(review_dir_text,"04_likely_separate_conflict_pairs.csv"),index=False)
        pairs_df.groupby(["shared_stop_classification","distance_band"],dropna=False).size().reset_index(name="pair_count").to_csv(os.path.join(review_dir_text,"05_pair_classification_distance_summary.csv"),index=False)
        pairs_df.groupby(["operator_a","operator_b","shared_stop_classification"],dropna=False).size().reset_index(name="pair_count").sort_values("pair_count",ascending=False).to_csv(os.path.join(review_dir_text,"06_operator_pair_summary.csv"),index=False)
    if not pairs_df.empty:
        sensitivity_rows=[]
        for radius in [25,50,75,100,125,150,200,250,300]:
            sub=pairs_df[pd.to_numeric(pairs_df["distance_ft"],errors="coerce").le(radius)].copy()
            keys=set(sub.get("source_key_a",pd.Series(dtype=str)).astype(str)) | set(sub.get("source_key_b",pd.Series(dtype=str)).astype(str))
            sensitivity_rows.append({
                "radius_ft":radius,
                "pair_count":len(sub),
                "unique_source_record_count":len({k for k in keys if k}),
                "connectable_pair_count":sum(1 for _,p in sub.iterrows() if _pair_can_connect(p,float(p["distance_ft"]))),
                "high_confidence_pair_count":int(sub["shared_stop_classification"].eq("High-Confidence Shared Stop Candidate").sum()),
                "likely_pair_count":int(sub["shared_stop_classification"].eq("Likely Shared Stop Candidate").sum()),
                "uncertain_pair_count":int(sub["shared_stop_classification"].eq("Uncertain Shared Stop Candidate").sum()),
                "rescue_pair_count":int(sub["shared_stop_classification"].eq("Evidence-Assisted Rescue Candidate").sum()),
            })
        pd.DataFrame(sensitivity_rows).to_csv(os.path.join(review_dir_text,"07_candidate_radius_sensitivity.csv"),index=False)
    groups_df.to_csv(os.path.join(review_dir_text,"10_shared_stop_groups.csv"),index=False)
    if not groups_df.empty:
        groups_df[groups_df["group_review_type"].eq("CONFIRM_SHARED_STOP")].to_csv(os.path.join(review_dir_text,"11_groups_for_confirmation.csv"),index=False)
        groups_df[groups_df["group_review_type"].eq("RESOLVE_UNCERTAIN_GROUP")].to_csv(os.path.join(review_dir_text,"12_groups_for_resolution.csv"),index=False)
    with open(os.path.join(review_dir_text,"README.txt"),"w",encoding="utf-8") as f:
        f.write("California GTFS Shared-Stop Toolkit - Pair Scoring Review\n")
        f.write("========================================================\n\n")
        f.write("These files explain how nearby stop pairs from different operators were scored and grouped.\n")
        f.write("Every agency/source record is preserved. No source record is merged, deleted, or overwritten.\n")
        f.write(f"Shared-stop discovery envelope: <= {thresholds['candidate_max_ft']:.0f} ft; primary range: <= {thresholds['primary_max_ft']:.0f} ft; 150-300 ft is evidence-assisted rescue only.\n")
        f.write("The warehouse nearby-pair file supplies the candidate pairs; pair scoring decides which pairs are shared-stop candidates.\n")
        f.write("Different operators contribute 0 points to physical same-stop evidence.\n")
        f.write("The Shared Stop Score is an evidence score, not a probability. High-confidence is heuristic, not verification.\n")
        f.write("CONFIRM_SHARED_STOP = strong coherent group for formal confirmation.\n")
        f.write("RESOLVE_UNCERTAIN_GROUP = mixed/moderate/incomplete evidence requiring human resolution.\n")
    _zip_directory(review_dir_text, str(review_zip))


def build_pair_scoring_review_dataframe(df):
    cols = [c for c in final_feature_fields if c in df.columns]
    return df[cols].copy()
