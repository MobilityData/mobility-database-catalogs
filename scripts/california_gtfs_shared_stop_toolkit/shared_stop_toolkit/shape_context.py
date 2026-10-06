"""
Served-shape context from Cal-ITP BigQuery (mart_gtfs).

Adds served GTFS shape-segment and travel-direction context for records in
groups that have a stop location issue or an unresolved location. The
per-stop shape rows also feed BoardingSide (see workflow._boarding_side_lookup).

Cache note: BigQuery results are cached in the warehouse folder so later runs
can reuse served-shape context without repeating a paid query. The workflow
uses a base cache plus a complete cache that includes broader service-date
recovery for stops missed by the initial lookup.

The BigQuery extraction runs in a separate Python 3.12 environment. Set the
environment variable GTFS_SHARED_STOP_BQ_PYTHON to that python.exe if it is
not at ~/python312-nuget/tools/python.exe.
"""

from pathlib import Path
import math
import os
import statistics
import subprocess
import pandas as pd

shape_context_cache_tag = "base"
max_bytes_billed = 50 * 1024**3

strong_median_diff_deg = 15.0
strong_max_diff_deg = 30.0
compatible_median_diff_deg = 30.0
compatible_max_diff_deg = 60.0
conflict_min_diff_deg = 120.0


def _bigquery_python():
    """Path to the standalone Python 3.12 used for BigQuery extraction."""
    override = os.environ.get("GTFS_SHARED_STOP_BQ_PYTHON", "").strip()
    if override:
        return Path(override)
    return Path.home() / "python312-nuget" / "tools" / "python.exe"


def _clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def _safe_float(v):
    try:
        x = float(v)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def _angle_difference(a, b):
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def _bearing_to_compass(deg):
    x = _safe_float(deg)
    if x is None:
        return ""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return labels[int((x % 360.0 + 22.5) // 45) % 8]


def _relevant_group_ids(issue_records, unresolved_locations):
    ids = set()
    for df in (issue_records, unresolved_locations):
        if df is not None and not df.empty and "shared_stop_group_id" in df.columns:
            ids.update(df["shared_stop_group_id"].astype(str).str.strip())
    ids.discard("")
    return ids


def _build_shape_targets(final_scored, issue_records, unresolved_locations):
    gids = _relevant_group_ids(issue_records, unresolved_locations)
    if not gids:
        return pd.DataFrame()

    df = final_scored[
        final_scored["shared_stop_group_id"].astype(str).isin(gids)
    ].copy()

    stop_col = "GTFS_stop_id" if "GTFS_stop_id" in df.columns else "stop_id"
    lat_col = "GTFS_stop_lat" if "GTFS_stop_lat" in df.columns else "stop_lat"
    lon_col = "GTFS_stop_lon" if "GTFS_stop_lon" in df.columns else "stop_lon"
    agency_col = "agency_name" if "agency_name" in df.columns else "analysis_name"
    name_col = "GTFS_stop_name" if "GTFS_stop_name" in df.columns else "stop_name"

    required = ["source_key", "feed_key", stop_col, lat_col, lon_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError("Served-shape stage missing: " + ", ".join(missing))

    cols = required + [c for c in [agency_col, name_col] if c in df.columns]
    out = df[cols].copy().rename(
        columns={
            stop_col: "stop_id",
            lat_col: "stop_lat",
            lon_col: "stop_lon",
            agency_col: "agency_name",
            name_col: "stop_name",
        }
    )
    if "agency_name" not in out.columns:
        out["agency_name"] = ""
    if "stop_name" not in out.columns:
        out["stop_name"] = ""

    for c in ["source_key", "feed_key", "stop_id", "agency_name", "stop_name"]:
        out[c] = out[c].map(_clean)

    out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    out = out[
        out["source_key"].ne("")
        & out["feed_key"].ne("")
        & out["stop_id"].ne("")
        & out["stop_lat"].notna()
        & out["stop_lon"].notna()
    ].copy()

    bad = []
    for key, g in out.groupby(["feed_key", "stop_id"], sort=False):
        if len(g[["stop_lat", "stop_lon"]].round(7).drop_duplicates()) > 1:
            bad.append(key)
    if bad:
        raise RuntimeError(
            f"{len(bad):,} feed_key+stop_id target(s) have conflicting coordinates."
        )

    return out.drop_duplicates(
        ["source_key", "feed_key", "stop_id"], keep="first"
    ).reset_index(drop=True)


def _query_shape_context_base(targets, warehouse_dir, source_run_stamp, reuse_cache=True):
    """Cost-controlled, partition-pruned served-shape extraction."""
    warehouse_dir = Path(warehouse_dir)
    cache_csv = warehouse_dir / f"shared_stop_shape_context_shapes_{shape_context_cache_tag}_{source_run_stamp}.csv"
    target_csv = warehouse_dir / f"shared_stop_shape_context_targets_{shape_context_cache_tag}_{source_run_stamp}.csv"
    service_target_csv = warehouse_dir / f"shared_stop_shape_context_service_targets_{shape_context_cache_tag}_{source_run_stamp}.csv"

    if reuse_cache and cache_csv.exists():
        print(f"[shapes] reusing cached served-shape context: {cache_csv}")
        return pd.read_csv(cache_csv, dtype=str, keep_default_na=False), cache_csv

    targets.to_csv(target_csv, index=False)

    python312 = _bigquery_python()
    if not python312.exists():
        raise FileNotFoundError(f"Standalone Python 3.12 not found: {python312}")

    run_date_text = str(source_run_stamp)[:8]
    child = 'import csv\nimport datetime as dt\nimport sys\nimport truststore\n\ntruststore.inject_into_ssl()\n\nfrom google.cloud import bigquery\n\ntarget_csv = sys.argv[1]\noutput_csv = sys.argv[2]\nservice_target_csv = sys.argv[3]\nrun_date_text = sys.argv[4]\nmax_total_bytes = int(sys.argv[5])\n\nrun_date = dt.datetime.strptime(run_date_text, "%Y%m%d").date()\nwindow_start = run_date - dt.timedelta(days=7)\nwindow_end = run_date + dt.timedelta(days=7)\n\nwith open(target_csv, newline="", encoding="utf-8-sig") as f:\n    raw = list(csv.DictReader(f))\n\nseen = {}\nfor r in raw:\n    key = (str(r["feed_key"]).strip(), str(r["stop_id"]).strip())\n    if not key[0] or not key[1]:\n        continue\n    coord = (float(r["stop_lat"]), float(r["stop_lon"]))\n    if key in seen and seen[key] != coord:\n        raise RuntimeError(f"Conflicting coordinates for feed_key+stop_id {key}")\n    seen[key] = coord\n\ndef q(v):\n    return "\'" + str(v).replace("\\\\", "\\\\\\\\").replace("\'", "\\\\\'") + "\'"\n\ndef timestamp_sql(v):\n    s = v.isoformat() if hasattr(v, "isoformat") else str(v)\n    return "TIMESTAMP(" + q(s) + ")"\n\ndef date_sql(v):\n    s = v.isoformat() if hasattr(v, "isoformat") else str(v)\n    return "DATE(" + q(s) + ")"\n\nbase_fields = [\n    "feed_key", "stop_id", "route_id", "direction_id", "shape_id",\n    "service_date", "feed_valid_from", "stop_to_shape_segment_ft",\n    "travel_bearing_deg", "segment_start_lat", "segment_start_lon",\n    "segment_end_lat", "segment_end_lon",\n]\n\nif not seen:\n    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:\n        csv.DictWriter(f, fieldnames=base_fields).writeheader()\n    with open(service_target_csv, "w", newline="", encoding="utf-8-sig") as f:\n        csv.writer(f).writerow(["feed_key", "stop_id", "service_date", "feed_valid_from"])\n    print("[shapes] no targets")\n    raise SystemExit(0)\n\ntarget_structs=[]\nfor (feed_key, stop_id), (lat, lon) in seen.items():\n    target_structs.append(\n        "STRUCT(" + q(feed_key) + " AS feed_key, " + q(stop_id) + " AS stop_id, "\n        + repr(float(lat)) + " AS stop_lat, " + repr(float(lon)) + " AS stop_lon)"\n    )\ntarget_sql = ",\\n".join(target_structs)\nclient = bigquery.Client(project="cal-itp-data-infra")\n\nphase1_sql = f"""\nWITH targets AS (\n    SELECT * FROM UNNEST([\n        {target_sql}\n    ])\n),\ncandidates AS (\n    SELECT\n        x.feed_key,\n        x.stop_id,\n        x.stop_lat,\n        x.stop_lon,\n        s.service_date,\n        s._feed_valid_from,\n        ROW_NUMBER() OVER (\n            PARTITION BY x.feed_key, x.stop_id\n            ORDER BY\n                ABS(DATE_DIFF(s.service_date, DATE(\'{run_date.isoformat()}\'), DAY)),\n                s.service_date\n        ) AS rn\n    FROM targets x\n    JOIN `cal-itp-data-infra.mart_gtfs.fct_daily_scheduled_stops` s\n      ON s.feed_key = x.feed_key\n     AND s.stop_id = x.stop_id\n    WHERE s.service_date BETWEEN DATE(\'{window_start.isoformat()}\') AND DATE(\'{window_end.isoformat()}\')\n)\nSELECT feed_key, stop_id, stop_lat, stop_lon, service_date, _feed_valid_from\nFROM candidates\nWHERE rn = 1\n"""\n\nphase1_dry = client.query(\n    phase1_sql,\n    job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),\n)\nphase1_estimated = int(phase1_dry.total_bytes_processed or 0)\nprint(f"[shapes] service-date lookup estimated scan: {phase1_estimated / (1024**3):.3f} GiB")\nif phase1_estimated > max_total_bytes:\n    raise RuntimeError(\n        "Served-shape service-date lookup alone exceeds the "\n        f"{max_total_bytes / (1024**3):.1f} GiB total safety budget."\n    )\n\nphase1_rows = list(\n    client.query(\n        phase1_sql,\n        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=max_total_bytes),\n    ).result()\n)\n\nresolved=[]\nfor r in phase1_rows:\n    resolved.append({\n        "feed_key": str(r.feed_key),\n        "stop_id": str(r.stop_id),\n        "stop_lat": float(r.stop_lat),\n        "stop_lon": float(r.stop_lon),\n        "service_date": r.service_date,\n        "feed_valid_from": r._feed_valid_from,\n    })\n\nwith open(service_target_csv, "w", newline="", encoding="utf-8-sig") as f:\n    writer=csv.DictWriter(f, fieldnames=["feed_key","stop_id","service_date","feed_valid_from"])\n    writer.writeheader()\n    for r in resolved:\n        writer.writerow({\n            "feed_key": r["feed_key"],\n            "stop_id": r["stop_id"],\n            "service_date": r["service_date"],\n            "feed_valid_from": r["feed_valid_from"],\n        })\n\nprint(f"[shapes] target stops matched to nearby scheduled service: {len(resolved):,} / {len(seen):,}")\nprint(f"[shapes] target stops without scheduled service in +/-7 days: {len(seen)-len(resolved):,}")\n\nif not resolved:\n    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:\n        csv.DictWriter(f, fieldnames=base_fields).writeheader()\n    raise SystemExit(0)\n\nresolved_structs=[]\nfor r in resolved:\n    resolved_structs.append(\n        "STRUCT(" + q(r["feed_key"]) + " AS feed_key, " + q(r["stop_id"]) + " AS stop_id, "\n        + repr(float(r["stop_lat"])) + " AS stop_lat, " + repr(float(r["stop_lon"])) + " AS stop_lon, "\n        + date_sql(r["service_date"]) + " AS service_date, "\n        + timestamp_sql(r["feed_valid_from"]) + " AS feed_valid_from)"\n    )\nresolved_sql = ",\\n".join(resolved_structs)\nvalid_timestamps = sorted({r["feed_valid_from"] for r in resolved}, key=str)\nservice_dates = sorted({r["service_date"] for r in resolved})\nvalid_ts_filter = ",\\n".join(timestamp_sql(v) for v in valid_timestamps)\nservice_date_filter = ",\\n".join(date_sql(v) for v in service_dates)\n\nphase2_sql = f"""\nWITH targets AS (\n    SELECT * FROM UNNEST([\n        {resolved_sql}\n    ])\n),\nserved_shape_ids AS (\n    SELECT DISTINCT\n        x.feed_key,\n        x.stop_id,\n        x.stop_lat,\n        x.stop_lon,\n        x.service_date,\n        x.feed_valid_from,\n        t.route_id,\n        t.direction_id,\n        t.shape_id\n    FROM targets x\n    JOIN `cal-itp-data-infra.mart_gtfs.dim_stop_times` st\n      ON st.feed_key = x.feed_key\n     AND st.stop_id = x.stop_id\n     AND st._feed_valid_from = x.feed_valid_from\n    JOIN `cal-itp-data-infra.mart_gtfs.dim_trips` t\n      ON t.feed_key = st.feed_key\n     AND t.trip_id = st.trip_id\n     AND t._feed_valid_from = x.feed_valid_from\n    WHERE st._feed_valid_from IN ({valid_ts_filter})\n      AND t._feed_valid_from IN ({valid_ts_filter})\n      AND t.shape_id IS NOT NULL\n),\nshape_arrays AS (\n    SELECT feed_key, service_date, shape_id, pt_array\n    FROM `cal-itp-data-infra.mart_gtfs.fct_daily_scheduled_shapes`\n    WHERE service_date IN ({service_date_filter})\n),\nserved_shapes AS (\n    SELECT s.*, a.pt_array\n    FROM served_shape_ids s\n    JOIN shape_arrays a\n      ON a.feed_key = s.feed_key\n     AND a.service_date = s.service_date\n     AND a.shape_id = s.shape_id\n    WHERE ARRAY_LENGTH(a.pt_array) >= 2\n),\nsegments AS (\n    SELECT\n        s.* EXCEPT(pt_array),\n        seg_idx,\n        s.pt_array[OFFSET(seg_idx)] AS p1,\n        s.pt_array[OFFSET(seg_idx + 1)] AS p2\n    FROM served_shapes s,\n    UNNEST(GENERATE_ARRAY(0, ARRAY_LENGTH(s.pt_array)-2)) AS seg_idx\n),\nscored AS (\n    SELECT\n        *,\n        ST_DISTANCE(\n            ST_GEOGPOINT(stop_lon, stop_lat),\n            ST_MAKELINE(p1, p2)\n        ) AS stop_to_segment_m\n    FROM segments\n),\nnearest AS (\n    SELECT * EXCEPT(rn)\n    FROM (\n        SELECT\n            *,\n            ROW_NUMBER() OVER (\n                PARTITION BY feed_key, stop_id, service_date, route_id, direction_id, shape_id\n                ORDER BY stop_to_segment_m, seg_idx\n            ) AS rn\n        FROM scored\n    )\n    WHERE rn = 1\n)\nSELECT\n    feed_key,\n    stop_id,\n    route_id,\n    direction_id,\n    shape_id,\n    service_date,\n    feed_valid_from,\n    ROUND(stop_to_segment_m * 3.28084, 2) AS stop_to_shape_segment_ft,\n    ST_AZIMUTH(p1, p2) * 180 / ACOS(-1) AS travel_bearing_deg,\n    ST_Y(p1) AS segment_start_lat,\n    ST_X(p1) AS segment_start_lon,\n    ST_Y(p2) AS segment_end_lat,\n    ST_X(p2) AS segment_end_lon\nFROM nearest\nORDER BY feed_key, stop_id, route_id, direction_id, shape_id\n"""\n\nphase2_dry = client.query(\n    phase2_sql,\n    job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),\n)\nphase2_estimated = int(phase2_dry.total_bytes_processed or 0)\ncombined_estimated = phase1_estimated + phase2_estimated\nprint(f"[shapes] partition-pruned served-shape estimated scan: {phase2_estimated / (1024**3):.3f} GiB")\nprint(f"[shapes] estimated total served-shape scan: {combined_estimated / (1024**3):.3f} GiB")\n\nif combined_estimated > max_total_bytes:\n    raise RuntimeError(\n        "Optimized served-shape query still exceeds the "\n        f"{max_total_bytes / (1024**3):.1f} GiB total safety budget. "\n        "The expensive phase was NOT executed."\n    )\n\nremaining_budget = max(1, max_total_bytes - phase1_estimated)\nrows = list(\n    client.query(\n        phase2_sql,\n        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=remaining_budget),\n    ).result()\n)\n\nwith open(output_csv, "w", newline="", encoding="utf-8-sig") as f:\n    writer=csv.DictWriter(f, fieldnames=base_fields)\n    writer.writeheader()\n    for row in rows:\n        writer.writerow({field: getattr(row, field) for field in base_fields})\n\nprint(f"[shapes] served shape rows written: {len(rows):,}")\nprint(f"[shapes] output: {output_csv}")\nprint(f"[shapes] service-date audit: {service_target_csv}")\n'

    result = subprocess.run(
        [
            str(python312),
            "-c",
            child,
            str(target_csv),
            str(cache_csv),
            str(service_target_csv),
            run_date_text,
            str(max_bytes_billed),
        ],
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )

    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print("[shapes] STDERR:")
        print(result.stderr.rstrip())
    if result.returncode != 0:
        raise RuntimeError(
            "Served-shape BigQuery extraction failed. "
            f"Return code: {result.returncode}"
        )

    return pd.read_csv(cache_csv, dtype=str, keep_default_na=False), cache_csv


def _query_shape_context(targets, warehouse_dir, source_run_stamp, reuse_cache=True):
    """
    Combine the partition-pruned base cache with broader service-date recovery
    for targets that were missed by the initial +/-7-day lookup.
    """
    warehouse_dir = Path(warehouse_dir)

    combined_cache = (
        warehouse_dir
        / f"shared_stop_shape_context_shapes_complete_{source_run_stamp}.csv"
    )
    base_cache = (
        warehouse_dir
        / f"shared_stop_shape_context_shapes_base_{source_run_stamp}.csv"
    )
    base_service_csv = (
        warehouse_dir
        / f"shared_stop_shape_context_service_targets_base_{source_run_stamp}.csv"
    )
    unmatched_csv = (
        warehouse_dir
        / f"shared_stop_shape_context_unmatched_targets_{source_run_stamp}.csv"
    )
    broad_service_csv = (
        warehouse_dir
        / f"shared_stop_shape_context_broad_service_targets_{source_run_stamp}.csv"
    )
    recovery_cache = (
        warehouse_dir
        / f"shared_stop_shape_context_shapes_recovery_{source_run_stamp}.csv"
    )

    if reuse_cache and combined_cache.exists():
        print(
            f"[shapes] reusing complete served-shape cache: "
            f"{combined_cache}"
        )
        return (
            pd.read_csv(
                combined_cache,
                dtype=str,
                keep_default_na=False,
            ),
            combined_cache,
        )

    # Reuse the base extraction when available to avoid repeating the paid query.
    if base_cache.exists():
        print(
            f"[shapes] reusing base served-shape cache: "
            f"{base_cache}"
        )
        base_df = pd.read_csv(
            base_cache,
            dtype=str,
            keep_default_na=False,
        )
    else:
        print(
            "[shapes] base served-shape cache not found; "
            "running the partition-pruned base extraction first"
        )
        base_df, _ = _query_shape_context_base(
            targets,
            warehouse_dir,
            source_run_stamp,
            reuse_cache=reuse_cache,
        )

    # Identify the records that the initial +/-7-day service-date lookup did
    # not match, so the recovery pass can search a wider service-date window
    # for them.
    if base_service_csv.exists():
        service_df = pd.read_csv(
            base_service_csv,
            dtype=str,
            keep_default_na=False,
        )
        service_keys = set(
            zip(
                service_df["feed_key"].astype(str),
                service_df["stop_id"].astype(str),
            )
        )

        unmatched = targets[
            ~targets.apply(
                lambda r: (
                    str(r["feed_key"]),
                    str(r["stop_id"]),
                ) in service_keys,
                axis=1,
            )
        ].copy()
    else:
        # Fallback: if the service audit is absent, recover targets not
        # represented in the base shape cache.
        base_keys = set()
        if not base_df.empty:
            base_keys = set(
                zip(
                    base_df["feed_key"].astype(str),
                    base_df["stop_id"].astype(str),
                )
            )

        unmatched = targets[
            ~targets.apply(
                lambda r: (
                    str(r["feed_key"]),
                    str(r["stop_id"]),
                ) in base_keys,
                axis=1,
            )
        ].copy()

    unmatched.to_csv(
        unmatched_csv,
        index=False,
    )

    print(
        f"[shapes] broad service-date recovery targets: "
        f"{len(unmatched):,}"
    )

    if unmatched.empty:
        combined = base_df.copy()
        combined.to_csv(
            combined_cache,
            index=False,
        )
        return combined, combined_cache

    if reuse_cache and recovery_cache.exists():
        print(
            f"[shapes] reusing broad recovery shape cache: "
            f"{recovery_cache}"
        )
        recovery_df = pd.read_csv(
            recovery_cache,
            dtype=str,
            keep_default_na=False,
        )
    else:
        python312 = _bigquery_python()

        if not python312.exists():
            raise FileNotFoundError(
                f"Standalone Python 3.12 not found: {python312}"
            )

        child = '\nimport csv\nimport datetime as dt\nimport json\nimport os\nimport sys\nimport truststore\n\ntruststore.inject_into_ssl()\n\nfrom google.cloud import bigquery\n\nunmatched_target_csv = sys.argv[1]\nbroad_service_csv = sys.argv[2]\nrecovery_output_csv = sys.argv[3]\nrun_date_text = sys.argv[4]\nmax_bytes = int(sys.argv[5])\n\nrun_date = dt.datetime.strptime(run_date_text, "%Y%m%d").date()\nwindow_start = run_date - dt.timedelta(days=730)\nwindow_end = run_date + dt.timedelta(days=180)\n\nbase_fields = [\n    "feed_key",\n    "stop_id",\n    "route_id",\n    "direction_id",\n    "shape_id",\n    "service_date",\n    "feed_valid_from",\n    "stop_to_shape_segment_ft",\n    "travel_bearing_deg",\n    "segment_start_lat",\n    "segment_start_lon",\n    "segment_end_lat",\n    "segment_end_lon",\n]\n\ndef q(v):\n    return "\'" + str(v).replace("\\\\", "\\\\\\\\").replace("\'", "\\\\\'") + "\'"\n\ndef date_sql(v):\n    s = v.isoformat() if hasattr(v, "isoformat") else str(v)\n    return "DATE(" + q(s) + ")"\n\ndef timestamp_sql(v):\n    s = v.isoformat() if hasattr(v, "isoformat") else str(v)\n    return "TIMESTAMP(" + q(s) + ")"\n\ndef read_csv(path):\n    with open(path, newline="", encoding="utf-8-sig") as f:\n        return list(csv.DictReader(f))\n\ntargets = read_csv(unmatched_target_csv)\nclient = bigquery.Client(project="cal-itp-data-infra")\n\n# ------------------------------------------------------------\n# Phase A: broad service-date lookup.\n# Reuse the diagnostic output when it already exists.\n# ------------------------------------------------------------\n\nif os.path.exists(broad_service_csv):\n    resolved = read_csv(broad_service_csv)\n    print(\n        "[shapes] reusing broad service-date audit: "\n        + broad_service_csv\n    )\nelse:\n    seen = {}\n    for r in targets:\n        key = (\n            str(r["feed_key"]).strip(),\n            str(r["stop_id"]).strip(),\n        )\n        if not key[0] or not key[1]:\n            continue\n\n        seen[key] = {\n            "agency_name": str(r.get("agency_name", "")),\n            "stop_name": str(r.get("stop_name", "")),\n            "stop_lat": float(r["stop_lat"]),\n            "stop_lon": float(r["stop_lon"]),\n        }\n\n    structs = []\n    for (feed_key, stop_id), info in seen.items():\n        structs.append(\n            "STRUCT("\n            + q(feed_key) + " AS feed_key, "\n            + q(stop_id) + " AS stop_id, "\n            + repr(info["stop_lat"]) + " AS stop_lat, "\n            + repr(info["stop_lon"]) + " AS stop_lon"\n            + ")"\n        )\n\n    if not structs:\n        resolved = []\n    else:\n        target_sql = ",\\n".join(structs)\n\n        phase_a_sql = f"""\nWITH targets AS (\n    SELECT *\n    FROM UNNEST([\n        {target_sql}\n    ])\n),\ncandidates AS (\n    SELECT\n        x.feed_key,\n        x.stop_id,\n        x.stop_lat,\n        x.stop_lon,\n        s.service_date,\n        s._feed_valid_from,\n        ROW_NUMBER() OVER (\n            PARTITION BY\n                x.feed_key,\n                x.stop_id\n            ORDER BY\n                ABS(\n                    DATE_DIFF(\n                        s.service_date,\n                        DATE(\'{run_date.isoformat()}\'),\n                        DAY\n                    )\n                ),\n                s.service_date DESC\n        ) AS rn\n    FROM targets x\n    JOIN\n        `cal-itp-data-infra.mart_gtfs.fct_daily_scheduled_stops` s\n      ON s.feed_key = x.feed_key\n     AND s.stop_id = x.stop_id\n    WHERE\n        s.service_date BETWEEN\n            DATE(\'{window_start.isoformat()}\')\n        AND DATE(\'{window_end.isoformat()}\')\n)\nSELECT\n    feed_key,\n    stop_id,\n    stop_lat,\n    stop_lon,\n    service_date,\n    _feed_valid_from\nFROM candidates\nWHERE rn = 1\n"""\n\n        dry = client.query(\n            phase_a_sql,\n            job_config=bigquery.QueryJobConfig(\n                dry_run=True,\n                use_query_cache=False,\n            ),\n        )\n        phase_a_bytes = int(dry.total_bytes_processed or 0)\n\n        print(\n            "[shapes] broad service-date lookup estimated scan: "\n            f"{phase_a_bytes / (1024**3):.3f} GiB"\n        )\n\n        if phase_a_bytes > 10 * 1024**3:\n            raise RuntimeError(\n                "Broad service-date lookup exceeds the "\n                "10 GiB recovery safety limit."\n            )\n\n        rows = list(\n            client.query(\n                phase_a_sql,\n                job_config=bigquery.QueryJobConfig(\n                    maximum_bytes_billed=10 * 1024**3\n                ),\n            ).result()\n        )\n\n        resolved = []\n        for r in rows:\n            info = seen[\n                (\n                    str(r.feed_key),\n                    str(r.stop_id),\n                )\n            ]\n            resolved.append(\n                {\n                    "feed_key": str(r.feed_key),\n                    "stop_id": str(r.stop_id),\n                    "agency_name": info["agency_name"],\n                    "stop_name": info["stop_name"],\n                    "stop_lat": float(r.stop_lat),\n                    "stop_lon": float(r.stop_lon),\n                    "service_date": r.service_date,\n                    "feed_valid_from": r._feed_valid_from,\n                }\n            )\n\n        with open(\n            broad_service_csv,\n            "w",\n            newline="",\n            encoding="utf-8-sig",\n        ) as f:\n            writer = csv.DictWriter(\n                f,\n                fieldnames=[\n                    "feed_key",\n                    "stop_id",\n                    "agency_name",\n                    "stop_name",\n                    "stop_lat",\n                    "stop_lon",\n                    "service_date",\n                    "feed_valid_from",\n                ],\n            )\n            writer.writeheader()\n            writer.writerows(resolved)\n\n        print(\n            "[shapes] broad service-date recovery: "\n            f"{len(resolved):,} / {len(seen):,}"\n        )\n\nif not resolved:\n    with open(\n        recovery_output_csv,\n        "w",\n        newline="",\n        encoding="utf-8-sig",\n    ) as f:\n        csv.DictWriter(f, fieldnames=base_fields).writeheader()\n    print("[shapes] no broad recovery targets")\n    raise SystemExit(0)\n\n# Normalize rows loaded from CSV or query result.\nnorm = []\nfor r in resolved:\n    norm.append(\n        {\n            "feed_key": str(r["feed_key"]).strip(),\n            "stop_id": str(r["stop_id"]).strip(),\n            "stop_lat": float(r["stop_lat"]),\n            "stop_lon": float(r["stop_lon"]),\n            "service_date": str(r["service_date"]).strip(),\n            "feed_valid_from": str(r["feed_valid_from"]).strip(),\n        }\n    )\n\n# The target rows used to be pasted directly into the SQL text. With a few\n# thousand recovered stops that can push BigQuery over its 1 MB SQL limit.\n# Pass the target rows as one JSON query parameter instead.\ntargets_json = json.dumps(norm, separators=(",", ":"))\n\nvalid_timestamps = sorted(\n    {r["feed_valid_from"] for r in norm}\n)\n\nservice_dates = sorted(\n    {r["service_date"] for r in norm}\n)\n\nvalid_ts_filter = ",\\n".join(\n    timestamp_sql(v)\n    for v in valid_timestamps\n)\n\nservice_date_filter = ",\\n".join(\n    date_sql(v)\n    for v in service_dates\n)\n\nphase_b_sql = f"""\nWITH targets AS (\n    SELECT\n        JSON_VALUE(item, \'$.feed_key\') AS feed_key,\n        JSON_VALUE(item, \'$.stop_id\') AS stop_id,\n        CAST(JSON_VALUE(item, \'$.stop_lat\') AS FLOAT64) AS stop_lat,\n        CAST(JSON_VALUE(item, \'$.stop_lon\') AS FLOAT64) AS stop_lon,\n        DATE(JSON_VALUE(item, \'$.service_date\')) AS service_date,\n        TIMESTAMP(JSON_VALUE(item, \'$.feed_valid_from\')) AS feed_valid_from\n    FROM UNNEST(\n        JSON_QUERY_ARRAY(PARSE_JSON(@targets_json, wide_number_mode=>\'round\'))\n    ) AS item\n),\nserved_shape_ids AS (\n    SELECT DISTINCT\n        x.feed_key,\n        x.stop_id,\n        x.stop_lat,\n        x.stop_lon,\n        x.service_date,\n        x.feed_valid_from,\n        t.route_id,\n        t.direction_id,\n        t.shape_id\n    FROM targets x\n    JOIN\n        `cal-itp-data-infra.mart_gtfs.dim_stop_times` st\n      ON st.feed_key = x.feed_key\n     AND st.stop_id = x.stop_id\n     AND st._feed_valid_from = x.feed_valid_from\n    JOIN\n        `cal-itp-data-infra.mart_gtfs.dim_trips` t\n      ON t.feed_key = st.feed_key\n     AND t.trip_id = st.trip_id\n     AND t._feed_valid_from = x.feed_valid_from\n    WHERE\n        st._feed_valid_from IN (\n            {valid_ts_filter}\n        )\n        AND\n        t._feed_valid_from IN (\n            {valid_ts_filter}\n        )\n        AND\n        t.shape_id IS NOT NULL\n),\nshape_arrays AS (\n    SELECT\n        feed_key,\n        service_date,\n        shape_id,\n        pt_array\n    FROM\n        `cal-itp-data-infra.mart_gtfs.fct_daily_scheduled_shapes`\n    WHERE\n        service_date IN (\n            {service_date_filter}\n        )\n),\nserved_shapes AS (\n    SELECT\n        s.*,\n        a.pt_array\n    FROM served_shape_ids s\n    JOIN shape_arrays a\n      ON a.feed_key = s.feed_key\n     AND a.service_date = s.service_date\n     AND a.shape_id = s.shape_id\n    WHERE\n        ARRAY_LENGTH(a.pt_array) >= 2\n),\nsegments AS (\n    SELECT\n        s.* EXCEPT(pt_array),\n        seg_idx,\n        s.pt_array[OFFSET(seg_idx)] AS p1,\n        s.pt_array[OFFSET(seg_idx + 1)] AS p2\n    FROM\n        served_shapes s,\n    UNNEST(\n        GENERATE_ARRAY(\n            0,\n            ARRAY_LENGTH(s.pt_array) - 2\n        )\n    ) AS seg_idx\n),\nscored AS (\n    SELECT\n        *,\n        ST_DISTANCE(\n            ST_GEOGPOINT(\n                stop_lon,\n                stop_lat\n            ),\n            ST_MAKELINE(\n                p1,\n                p2\n            )\n        ) AS stop_to_segment_m\n    FROM segments\n),\nnearest AS (\n    SELECT\n        * EXCEPT(rn)\n    FROM (\n        SELECT\n            *,\n            ROW_NUMBER() OVER (\n                PARTITION BY\n                    feed_key,\n                    stop_id,\n                    service_date,\n                    route_id,\n                    direction_id,\n                    shape_id\n                ORDER BY\n                    stop_to_segment_m,\n                    seg_idx\n            ) AS rn\n        FROM scored\n    )\n    WHERE rn = 1\n)\nSELECT\n    feed_key,\n    stop_id,\n    route_id,\n    direction_id,\n    shape_id,\n    service_date,\n    feed_valid_from,\n    ROUND(\n        stop_to_segment_m * 3.28084,\n        2\n    ) AS stop_to_shape_segment_ft,\n    ST_AZIMUTH(\n        p1,\n        p2\n    ) * 180 / ACOS(-1)\n        AS travel_bearing_deg,\n    ST_Y(p1) AS segment_start_lat,\n    ST_X(p1) AS segment_start_lon,\n    ST_Y(p2) AS segment_end_lat,\n    ST_X(p2) AS segment_end_lon\nFROM nearest\nORDER BY\n    feed_key,\n    stop_id,\n    route_id,\n    direction_id,\n    shape_id\n"""\n\nphase_b_query_parameters = [\n    bigquery.ScalarQueryParameter(\n        "targets_json",\n        "STRING",\n        targets_json,\n    )\n]\n\ndry_b = client.query(\n    phase_b_sql,\n    job_config=bigquery.QueryJobConfig(\n        dry_run=True,\n        use_query_cache=False,\n        query_parameters=phase_b_query_parameters,\n    ),\n)\n\nphase_b_bytes = int(\n    dry_b.total_bytes_processed or 0\n)\n\nprint(\n    "[shapes] broad recovery served-shape estimated scan: "\n    f"{phase_b_bytes / (1024**3):.3f} GiB"\n)\n\nprint(\n    "[shapes] broad recovery targets passed as query parameter: "\n    f"{len(norm):,}"\n)\nprint("[shapes] JSON numeric parsing mode: round")\nprint(\n    "[shapes] broad recovery SQL text size: "\n    f"{len(phase_b_sql.encode(\'utf-8\')) / 1024:.1f} KiB"\n)\n\nif phase_b_bytes > max_bytes:\n    raise RuntimeError(\n        "Broad served-shape recovery exceeds the "\n        f"{max_bytes / (1024**3):.1f} GiB recovery safety limit. "\n        "The recovery query was NOT executed."\n    )\n\nrows = list(\n    client.query(\n        phase_b_sql,\n        job_config=bigquery.QueryJobConfig(\n            maximum_bytes_billed=max_bytes,\n            query_parameters=phase_b_query_parameters,\n        ),\n    ).result()\n)\n\nwith open(\n    recovery_output_csv,\n    "w",\n    newline="",\n    encoding="utf-8-sig",\n) as f:\n    writer = csv.DictWriter(\n        f,\n        fieldnames=base_fields,\n    )\n    writer.writeheader()\n    for row in rows:\n        writer.writerow(\n            {\n                field: getattr(row, field)\n                for field in base_fields\n            }\n        )\n\nprint(\n    "[shapes] broad recovery served shape rows written: "\n    f"{len(rows):,}"\n)\nprint(\n    "[shapes] broad recovery output: "\n    + recovery_output_csv\n)\n'

        result = subprocess.run(
            [
                str(python312),
                "-c",
                child,
                str(unmatched_csv),
                str(broad_service_csv),
                str(recovery_cache),
                str(source_run_stamp)[:8],
                str(20 * 1024**3),
            ],
            text=True,
            capture_output=True,
            env=os.environ.copy(),
        )

        if result.stdout:
            print(result.stdout.rstrip())

        if result.stderr:
            print("[shapes] STDERR:")
            print(result.stderr.rstrip())

        if result.returncode != 0:
            raise RuntimeError(
                "Broad served-shape recovery failed. "
                f"Return code: {result.returncode}"
            )

        recovery_df = pd.read_csv(
            recovery_cache,
            dtype=str,
            keep_default_na=False,
        )

    combined = pd.concat(
        [
            base_df,
            recovery_df,
        ],
        ignore_index=True,
        sort=False,
    )

    if not combined.empty:
        combined = combined.drop_duplicates().reset_index(
            drop=True
        )

    combined.to_csv(
        combined_cache,
        index=False,
    )

    base_keys = set()
    recovery_keys = set()
    combined_keys = set()

    if not base_df.empty:
        base_keys = set(
            zip(
                base_df["feed_key"].astype(str),
                base_df["stop_id"].astype(str),
            )
        )

    if not recovery_df.empty:
        recovery_keys = set(
            zip(
                recovery_df["feed_key"].astype(str),
                recovery_df["stop_id"].astype(str),
            )
        )

    if not combined.empty:
        combined_keys = set(
            zip(
                combined["feed_key"].astype(str),
                combined["stop_id"].astype(str),
            )
        )

    print(
        f"[shapes] base served-shape rows: "
        f"{len(base_df):,}"
    )
    print(
        f"[shapes] broad recovery served-shape rows: "
        f"{len(recovery_df):,}"
    )
    print(
        f"[shapes] combined served-shape rows: "
        f"{len(combined):,}"
    )
    print(
        f"[shapes] target stop keys with shape context: "
        f"{len(combined_keys):,} / "
        f"{targets[['feed_key','stop_id']].drop_duplicates().shape[0]:,}"
    )
    print(
        f"[shapes] newly covered stop keys from broad recovery: "
        f"{len(recovery_keys - base_keys):,}"
    )
    print(
        f"[shapes] complete served-shape cache: "
        f"{combined_cache}"
    )

    return combined, combined_cache

def _attach_source_keys(raw_shapes, targets):
    if raw_shapes is None or raw_shapes.empty:
        return pd.DataFrame()

    mapping = targets[
        ["source_key","feed_key","stop_id","agency_name","stop_name","stop_lat","stop_lon"]
    ].copy()

    out = raw_shapes.merge(mapping, on=["feed_key", "stop_id"], how="inner")

    for c in [
        "stop_to_shape_segment_ft","travel_bearing_deg",
        "segment_start_lat","segment_start_lon","segment_end_lat","segment_end_lon",
        "stop_lat","stop_lon",
    ]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out



def _build_shape_record_summary(shape_rows, targets=None, warehouse_dir=None, source_run_stamp=None):
    detail_cols = [
        "shape_context_status",
        "shape_context_reason",
        "shape_context_available",
        "shape_served_shape_count",
        "shape_served_route_count",
        "shape_direction_id_values",
        "shape_route_ids",
        "shape_bearings_deg",
        "shape_compass_directions",
        "shape_min_segment_distance_ft",
        "shape_median_segment_distance_ft",
        "shape_max_segment_distance_ft",
    ]

    rows = []

    if shape_rows is not None and not shape_rows.empty:
        for source_key, g in shape_rows.groupby("source_key", sort=False):
            dists = pd.to_numeric(
                g["stop_to_shape_segment_ft"],
                errors="coerce",
            ).dropna()

            bearings = sorted({
                round(float(v) % 360.0, 1)
                for v in pd.to_numeric(
                    g["travel_bearing_deg"],
                    errors="coerce",
                ).dropna()
            })

            routes = sorted({
                _clean(v)
                for v in g["route_id"]
                if _clean(v)
            })

            shapes = sorted({
                _clean(v)
                for v in g["shape_id"]
                if _clean(v)
            })

            dirs = sorted({
                _clean(v)
                for v in g["direction_id"]
                if _clean(v)
            })

            rows.append({
                "source_key": source_key,
                "shape_context_status": "SHAPE_CONTEXT_AVAILABLE",
                "shape_context_reason": "SERVED_GTFS_SHAPE_AVAILABLE",
                "shape_context_available": "Y",
                "shape_served_shape_count": len(shapes),
                "shape_served_route_count": len(routes),
                "shape_direction_id_values": " | ".join(dirs),
                "shape_route_ids": " | ".join(routes),
                "shape_bearings_deg": " | ".join(
                    f"{v:.1f}"
                    for v in bearings
                ),
                "shape_compass_directions": " | ".join(
                    sorted({
                        _bearing_to_compass(v)
                        for v in bearings
                        if _bearing_to_compass(v)
                    })
                ),
                "shape_min_segment_distance_ft":
                    round(float(dists.min()), 2)
                    if len(dists) else "",
                "shape_median_segment_distance_ft":
                    round(float(dists.median()), 2)
                    if len(dists) else "",
                "shape_max_segment_distance_ft":
                    round(float(dists.max()), 2)
                    if len(dists) else "",
            })

    summary = pd.DataFrame(rows)

    if targets is None or targets.empty:
        return summary

    target_info = (
        targets[
            [
                "source_key",
                "feed_key",
                "stop_id",
            ]
        ]
        .drop_duplicates("source_key")
        .copy()
    )

    audit_map = {}

    if warehouse_dir is not None and source_run_stamp is not None:
        audit_path = (
            Path(warehouse_dir)
            / f"shared_stop_shape_context_missing_shape_audit_{source_run_stamp}.csv"
        )

        if audit_path.exists():
            try:
                audit = pd.read_csv(
                    audit_path,
                    dtype=str,
                    keep_default_na=False,
                )

                if {
                    "feed_key",
                    "stop_id",
                    "missing_shape_reason",
                }.issubset(audit.columns):
                    audit_map = {
                        (
                            _clean(r["feed_key"]),
                            _clean(r["stop_id"]),
                        ):
                        _clean(r["missing_shape_reason"])
                        for _, r in audit.iterrows()
                    }

                print(
                    f"[shapes] reusing missing-shape lineage audit: "
                    f"{audit_path}"
                )

            except Exception as exc:
                print(
                    "[shapes] WARNING: could not read missing-shape "
                    f"lineage audit: {exc}"
                )

    available_keys = set(
        summary["source_key"].astype(str)
        if not summary.empty
        else []
    )

    missing_rows = []

    for _, r in target_info.iterrows():
        source_key = _clean(r["source_key"])

        if source_key in available_keys:
            continue

        reason = audit_map.get(
            (
                _clean(r["feed_key"]),
                _clean(r["stop_id"]),
            ),
            "",
        )

        if reason == "SERVED_TRIPS_HAVE_NO_SHAPE_ID":
            status = "NO_GTFS_SHAPE_ID"
        elif reason:
            status = "NO_SHAPE_CONTEXT_OTHER"
        else:
            status = "NO_SHAPE_CONTEXT_UNDIAGNOSED"

        row = {
            "source_key": source_key,
            "shape_context_status": status,
            "shape_context_reason": reason,
            "shape_context_available": "N",
        }

        for c in detail_cols:
            row.setdefault(c, "")

        row["shape_context_status"] = status
        row["shape_context_reason"] = reason
        row["shape_context_available"] = "N"

        missing_rows.append(row)

    if missing_rows:
        missing_df = pd.DataFrame(missing_rows)
        summary = pd.concat(
            [
                summary,
                missing_df,
            ],
            ignore_index=True,
            sort=False,
        )

    for c in detail_cols:
        if c not in summary.columns:
            summary[c] = ""
        else:
            summary[c] = summary[c].fillna("")

    return summary


def _bearing_sets(shape_rows):
    out = {}
    if shape_rows is None or shape_rows.empty:
        return out
    for source_key, g in shape_rows.groupby("source_key", sort=False):
        vals = [
            float(v) % 360.0
            for v in pd.to_numeric(g["travel_bearing_deg"], errors="coerce").dropna()
        ]
        out[source_key] = sorted({round(v, 3) for v in vals})
    return out



def _compare_bearings(a_vals, b_vals):
    if not a_vals or not b_vals:
        return (
            "NO_SHAPE_CONTEXT",
            None,
            None,
            None,
            "NEUTRAL_NO_DIRECTION_EVIDENCE",
        )

    all_diffs = [_angle_difference(a, b) for a in a_vals for b in b_vals]
    nearest = (
        [min(_angle_difference(a, b) for b in b_vals) for a in a_vals]
        + [min(_angle_difference(b, a) for a in a_vals) for b in b_vals]
    )

    min_diff = min(all_diffs)
    median_nearest = statistics.median(nearest)
    max_nearest = max(nearest)

    if (
        median_nearest <= strong_median_diff_deg
        and max_nearest <= strong_max_diff_deg
    ):
        status = "SAME_DIRECTION_STRONGLY_CORROBORATES"
        modifier = "POSITIVE_SAME_DIRECTION_EVIDENCE"

    elif (
        median_nearest <= compatible_median_diff_deg
        and max_nearest <= compatible_max_diff_deg
    ):
        status = "SAME_DIRECTION_CORROBORATES"
        modifier = "POSITIVE_SAME_DIRECTION_EVIDENCE"

    elif min_diff >= conflict_min_diff_deg:
        # Important: a different route bearing does NOT contradict a shared
        # physical stop. Routes can share a pole/platform and diverge,
        # converge, turn, loop, or continue in different directions.
        status = "DIFFERENT_ROUTE_MOVEMENT_CONTEXT"
        modifier = "NEUTRAL_ROUTE_MOVEMENT_DIFFERENCE"

    else:
        status = "MIXED_ROUTE_MOVEMENT_CONTEXT"
        modifier = "NEUTRAL_ROUTE_MOVEMENT_VARIATION"

    return (
        status,
        round(min_diff, 1),
        round(median_nearest, 1),
        round(max_nearest, 1),
        modifier,
    )



def _annotate_pairs_with_shape_context(pair_df, shape_rows, record_summary=None):
    out = pair_df.copy()
    bsets = _bearing_sets(shape_rows)

    vals = []
    for _, row in out.iterrows():
        a = _clean(row.get("source_key_a"))
        b = _clean(row.get("source_key_b"))

        vals.append(
            _compare_bearings(
                bsets.get(a, []),
                bsets.get(b, []),
            )
        )

    out["shape_pair_direction_status"] = [
        v[0]
        for v in vals
    ]

    out["shape_pair_min_bearing_diff_deg"] = [
        ""
        if v[1] is None
        else v[1]
        for v in vals
    ]

    out["shape_pair_median_nearest_bearing_diff_deg"] = [
        ""
        if v[2] is None
        else v[2]
        for v in vals
    ]

    out["shape_pair_max_nearest_bearing_diff_deg"] = [
        ""
        if v[3] is None
        else v[3]
        for v in vals
    ]

    out["shape_pair_confidence_modifier"] = [
        v[4]
        for v in vals
    ]

    status_map = {}

    if (
        record_summary is not None
        and not record_summary.empty
        and "shape_context_status" in record_summary.columns
    ):
        status_map = dict(
            zip(
                record_summary["source_key"].astype(str),
                record_summary["shape_context_status"].astype(str),
            )
        )

    out["shape_context_status_a"] = (
        out["source_key_a"]
        .astype(str)
        .map(status_map)
        .fillna("")
    )

    out["shape_context_status_b"] = (
        out["source_key_b"]
        .astype(str)
        .map(status_map)
        .fillna("")
    )

    return out



def _annotate_groups_with_shape_context(group_df, final_scored, pair_df):
    groups = group_df.copy()

    source_to_group = dict(
        zip(
            final_scored["source_key"].astype(str),
            final_scored["shared_stop_group_id"].astype(str),
        )
    )

    p = pair_df.copy()

    p["_ga"] = (
        p["source_key_a"]
        .astype(str)
        .map(source_to_group)
        .fillna("")
    )

    p["_gb"] = (
        p["source_key_b"]
        .astype(str)
        .map(source_to_group)
        .fillna("")
    )

    p = p[
        p["_ga"].ne("")
        & p["_ga"].eq(p["_gb"])
    ].copy()

    rows = []

    for gid, g in p.groupby("_ga", sort=False):
        status = (
            g["shape_pair_direction_status"]
            .astype(str)
        )

        evaluated = g[
            ~status.eq("NO_SHAPE_CONTEXT")
        ]

        strong = int(
            evaluated[
                "shape_pair_direction_status"
            ]
            .eq(
                "SAME_DIRECTION_STRONGLY_CORROBORATES"
            )
            .sum()
        )

        compat = int(
            evaluated[
                "shape_pair_direction_status"
            ]
            .eq(
                "SAME_DIRECTION_CORROBORATES"
            )
            .sum()
        )

        different = int(
            evaluated[
                "shape_pair_direction_status"
            ]
            .eq(
                "DIFFERENT_ROUTE_MOVEMENT_CONTEXT"
            )
            .sum()
        )

        mixed = int(
            evaluated[
                "shape_pair_direction_status"
            ]
            .eq(
                "MIXED_ROUTE_MOVEMENT_CONTEXT"
            )
            .sum()
        )

        same_direction = strong + compat
        route_variation = different + mixed

        if len(evaluated) == 0:
            group_status = "NO_SHAPE_DIRECTION_EVIDENCE"
            modifier = "NEUTRAL_NO_DIRECTION_EVIDENCE"

        elif same_direction == len(evaluated):
            group_status = "SAME_DIRECTION_CORROBORATION_ONLY"
            modifier = "POSITIVE_SAME_DIRECTION_EVIDENCE"

        elif same_direction > 0:
            group_status = (
                "SAME_DIRECTION_CORROBORATION_WITH_ROUTE_VARIATION"
            )
            modifier = (
                "POSITIVE_SAME_DIRECTION_EVIDENCE_WITH_NEUTRAL_VARIATION"
            )

        else:
            group_status = "ROUTE_MOVEMENT_VARIATION_ONLY"
            modifier = "NEUTRAL_ROUTE_MOVEMENT_VARIATION"

        rows.append({
            "shared_stop_group_id": gid,
            "shape_group_pairs_evaluated": len(evaluated),
            "shape_group_strong_corroboration_pairs": strong,
            "shape_group_corroboration_pairs": compat,
            "shape_group_same_direction_pairs": same_direction,
            "shape_group_different_movement_pairs": different,
            "shape_group_mixed_movement_pairs": mixed,
            "shape_group_route_variation_pairs": route_variation,
            "shape_group_direction_status": group_status,
            "shape_group_confidence_modifier": modifier,
        })

    summary = pd.DataFrame(rows)

    shape_cols = [
        "shape_group_pairs_evaluated",
        "shape_group_strong_corroboration_pairs",
        "shape_group_corroboration_pairs",
        "shape_group_same_direction_pairs",
        "shape_group_different_movement_pairs",
        "shape_group_mixed_movement_pairs",
        "shape_group_route_variation_pairs",
        "shape_group_direction_status",
        "shape_group_confidence_modifier",
        # Not produced by this summary; dropped if an input table carries them
        # so they cannot be mistaken for this run's results.
        "shape_group_conflict_pairs",
        "shape_group_mixed_pairs",
    ]

    for c in shape_cols:
        if c in groups.columns:
            groups = groups.drop(columns=[c])

    if not summary.empty:
        groups = groups.merge(
            summary,
            on="shared_stop_group_id",
            how="left",
        )

    return groups, summary



def _triage_unresolved_locations(unresolved, group_summary):
    out = unresolved.copy()

    if out.empty:
        return out

    if (
        group_summary is not None
        and not group_summary.empty
    ):
        keep = [
            "shared_stop_group_id",
            "shape_group_direction_status",
            "shape_group_confidence_modifier",
            "shape_group_pairs_evaluated",
            "shape_group_same_direction_pairs",
            "shape_group_route_variation_pairs",
        ]

        for c in keep[1:]:
            if c in out.columns:
                out = out.drop(columns=[c])

        out = out.merge(
            group_summary[keep],
            on="shared_stop_group_id",
            how="left",
        )

    positive_statuses = {
        "SAME_DIRECTION_CORROBORATION_ONLY",
        "SAME_DIRECTION_CORROBORATION_WITH_ROUTE_VARIATION",
    }

    triage = []

    for _, r in out.iterrows():
        reason = _clean(
            r.get("recommendation_review_reason")
        )

        status = _clean(
            r.get("shape_group_direction_status")
        )

        if (
            reason
            == "TWO_OPERATOR_DISAGREEMENT_OVER_25FT"
            and status in positive_statuses
        ):
            label = (
                "IMAGERY_PRIORITY_SAME_DIRECTION_POSITION_DISAGREEMENT"
            )

        elif (
            reason
            == "NO_OPERATOR_MAJORITY_WITHIN_25FT"
            and status in positive_statuses
        ):
            label = (
                "POSITION_CLUSTER_REVIEW_WITH_SAME_DIRECTION_CORROBORATION"
            )

        elif status in positive_statuses:
            label = (
                "SAME_DIRECTION_CORROBORATES_KEEP_REFERENCE_REVIEW"
            )

        elif status == "ROUTE_MOVEMENT_VARIATION_ONLY":
            label = (
                "ROUTE_MOVEMENT_VARIATION_NEUTRAL_KEEP_REFERENCE_REVIEW"
            )

        else:
            label = "NO_SHAPE_TRIAGE_CHANGE"

        triage.append(label)

    out["shape_recommendation_triage"] = triage

    return out



def _annotate_issues_with_shape_context(issues, shape_rows, record_summary=None):
    out = issues.copy()

    if out.empty:
        return out

    bsets = _bearing_sets(shape_rows)
    vals = []

    for _, r in out.iterrows():
        bad = _clean(
            r.get("likely_incorrect_source_key")
        )

        ref = _clean(
            r.get("recommended_source_key")
        )

        vals.append(
            _compare_bearings(
                bsets.get(bad, []),
                bsets.get(ref, []),
            )
        )

    out["issue_to_recommended_shape_direction_status"] = [
        v[0]
        for v in vals
    ]

    out["issue_to_recommended_shape_min_bearing_diff_deg"] = [
        ""
        if v[1] is None
        else v[1]
        for v in vals
    ]

    out["issue_to_recommended_shape_median_nearest_diff_deg"] = [
        ""
        if v[2] is None
        else v[2]
        for v in vals
    ]

    out["issue_to_recommended_shape_max_nearest_diff_deg"] = [
        ""
        if v[3] is None
        else v[3]
        for v in vals
    ]

    out["issue_to_recommended_shape_confidence_modifier"] = [
        v[4]
        for v in vals
    ]

    status_map = {}

    if (
        record_summary is not None
        and not record_summary.empty
        and "shape_context_status" in record_summary.columns
    ):
        status_map = dict(
            zip(
                record_summary["source_key"].astype(str),
                record_summary["shape_context_status"].astype(str),
            )
        )

    bad_statuses = []
    ref_statuses = []
    triage = []

    for _, r in out.iterrows():
        bad = _clean(
            r.get("likely_incorrect_source_key")
        )

        ref = _clean(
            r.get("recommended_source_key")
        )

        bad_status = status_map.get(bad, "")
        ref_status = status_map.get(ref, "")

        bad_statuses.append(bad_status)
        ref_statuses.append(ref_status)

        status = _clean(
            r.get(
                "issue_to_recommended_shape_direction_status"
            )
        )

        # The direction status column was just assigned to `out`, so use
        # the corresponding row value from vals after the loop below.
        triage.append("")

    out["likely_incorrect_shape_context_status"] = bad_statuses
    out["recommended_shape_context_status"] = ref_statuses

    final_triage = []

    for idx, status in enumerate(
        out["issue_to_recommended_shape_direction_status"].astype(str)
    ):
        if status in {
            "SAME_DIRECTION_STRONGLY_CORROBORATES",
            "SAME_DIRECTION_CORROBORATES",
        }:
            label = "SAME_DIRECTION_CORROBORATES_CURRENT_ISSUE"

        elif status in {
            "DIFFERENT_ROUTE_MOVEMENT_CONTEXT",
            "MIXED_ROUTE_MOVEMENT_CONTEXT",
        }:
            label = "ROUTE_MOVEMENT_VARIATION_NEUTRAL"

        else:
            bad_status = _clean(
                out.iloc[idx].get(
                    "likely_incorrect_shape_context_status"
                )
            )

            ref_status = _clean(
                out.iloc[idx].get(
                    "recommended_shape_context_status"
                )
            )

            if (
                bad_status == "NO_GTFS_SHAPE_ID"
                or ref_status == "NO_GTFS_SHAPE_ID"
            ):
                label = "NO_GTFS_SHAPE_ID"
            else:
                label = "NO_SHAPE_EVIDENCE"

        final_triage.append(label)

    out["shape_issue_triage"] = final_triage

    return out


def _merge_shape_record_summary(final_scored, record_summary):
    out = final_scored.copy()

    cols = [
        "shape_context_status",
        "shape_context_reason",
        "shape_context_available",
        "shape_served_shape_count",
        "shape_served_route_count",
        "shape_direction_id_values",
        "shape_route_ids",
        "shape_bearings_deg",
        "shape_compass_directions",
        "shape_min_segment_distance_ft",
        "shape_median_segment_distance_ft",
        "shape_max_segment_distance_ft",
    ]

    for c in cols:
        if c in out.columns:
            out = out.drop(columns=[c])

    if record_summary is not None and not record_summary.empty:
        out = out.merge(
            record_summary,
            on="source_key",
            how="left",
        )

    for c in cols:
        if c not in out.columns:
            out[c] = ""
        else:
            out[c] = out[c].fillna("")

    return out


def _write_shape_segment_feature_class(shape_rows, out_gdb, source_run_stamp):
    if shape_rows is None or shape_rows.empty:
        print("[shapes] no nearest-segment rows; feature class not created")
        return None

    import arcpy

    name = "served_shape_segments"
    out_fc = os.path.join(str(out_gdb), name)
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)

    sr = arcpy.SpatialReference(4326)
    arcpy.management.CreateFeatureclass(str(out_gdb), name, "POLYLINE", spatial_reference=sr)

    for fn, ft, length in [
        ("src_key","TEXT",64),("agency","TEXT",255),("stop_id","TEXT",100),
        ("route_id","TEXT",100),("direction_id","TEXT",20),("shape_id","TEXT",150),
        ("distance_ft","DOUBLE",None),("bearing_deg","DOUBLE",None),("compass","TEXT",10),
    ]:
        if ft == "TEXT":
            arcpy.management.AddField(out_fc, fn, ft, field_length=length)
        else:
            arcpy.management.AddField(out_fc, fn, ft)

    fields = [
        "SHAPE@","src_key","agency","stop_id","route_id","direction_id",
        "shape_id","distance_ft","bearing_deg","compass",
    ]

    inserted = 0
    with arcpy.da.InsertCursor(out_fc, fields) as cur:
        for _, r in shape_rows.iterrows():
            coords = [
                _safe_float(r.get("segment_start_lon")),
                _safe_float(r.get("segment_start_lat")),
                _safe_float(r.get("segment_end_lon")),
                _safe_float(r.get("segment_end_lat")),
            ]
            if any(v is None for v in coords):
                continue

            lon1, lat1, lon2, lat2 = coords
            geom = arcpy.Polyline(
                arcpy.Array([arcpy.Point(lon1, lat1), arcpy.Point(lon2, lat2)]),
                sr,
            )
            bearing = _safe_float(r.get("travel_bearing_deg"))
            dist = _safe_float(r.get("stop_to_shape_segment_ft"))

            cur.insertRow([
                geom,
                _clean(r.get("source_key"))[:64],
                _clean(r.get("agency_name"))[:255],
                _clean(r.get("stop_id"))[:100],
                _clean(r.get("route_id"))[:100],
                _clean(r.get("direction_id"))[:20],
                _clean(r.get("shape_id"))[:150],
                dist,
                bearing,
                _bearing_to_compass(bearing) if bearing is not None else "",
            ])
            inserted += 1

    print(f"[shapes] wrote nearest served-shape segments: {out_fc}; inserted={inserted:,}")
    return out_fc


def run_served_shape_context(
    final_scored,
    pair_df,
    group_df,
    issue_records,
    unresolved_locations,
    warehouse_dir,
    out_gdb,
    source_run_stamp,
    reuse_cache=True,
):
    targets = _build_shape_targets(final_scored, issue_records, unresolved_locations)

    print(
        f"[shapes] relevant GTFS records: {len(targets):,} "
        f"across {targets['source_key'].nunique() if not targets.empty else 0:,} source records"
    )

    if targets.empty:
        return {
            "final_scored": final_scored,
            "pair_df": pair_df,
            "group_df": group_df,
            "issue_records": issue_records,
            "unresolved_locations": unresolved_locations,
            "shape_rows": pd.DataFrame(),
            "shape_record_summary": pd.DataFrame(),
            "shape_group_summary": pd.DataFrame(),
            "shape_segments_feature_class": None,
            "shape_cache_csv": None,
        }

    raw_shapes, cache_csv = _query_shape_context(
        targets, warehouse_dir, source_run_stamp, reuse_cache=reuse_cache
    )
    shape_rows = _attach_source_keys(raw_shapes, targets)

    if not shape_rows.empty and "travel_bearing_deg" in shape_rows.columns:
        bearing_num = pd.to_numeric(
            shape_rows["travel_bearing_deg"],
            errors="coerce",
        )
        missing_bearings = int(bearing_num.isna().sum())
        print(
            f"[shapes] served-shape rows with usable local bearing: "
            f"{len(shape_rows) - missing_bearings:,} / {len(shape_rows):,}"
        )
        if missing_bearings:
            print(
                f"[shapes] rows with null/degenerate local bearing: "
                f"{missing_bearings:,} "
                "(kept for distance context; excluded from direction evidence)"
            )

    record_summary = _build_shape_record_summary(
        shape_rows,
        targets=targets,
        warehouse_dir=warehouse_dir,
        source_run_stamp=source_run_stamp,
    )

    if (
        record_summary is not None
        and not record_summary.empty
        and "shape_context_status" in record_summary.columns
    ):
        print("[shapes] target record context status:")
        print(
            record_summary[
                "shape_context_status"
            ].value_counts().to_string()
        )

    final_out = _merge_shape_record_summary(final_scored, record_summary)
    pair_out = _annotate_pairs_with_shape_context(pair_df, shape_rows, record_summary)
    group_out, group_summary = _annotate_groups_with_shape_context(group_df, final_out, pair_out)
    unresolved_out = _triage_unresolved_locations(unresolved_locations, group_summary)
    issue_out = _annotate_issues_with_shape_context(issue_records, shape_rows, record_summary)
    segment_fc = _write_shape_segment_feature_class(shape_rows, out_gdb, source_run_stamp)

    return {
        "final_scored": final_out,
        "pair_df": pair_out,
        "group_df": group_out,
        "issue_records": issue_out,
        "unresolved_locations": unresolved_out,
        "shape_rows": shape_rows,
        "shape_record_summary": record_summary,
        "shape_group_summary": group_summary,
        "shape_segments_feature_class": segment_fc,
        "shape_cache_csv": cache_csv,
    }
