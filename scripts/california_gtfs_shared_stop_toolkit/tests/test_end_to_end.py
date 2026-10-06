"""End-to-end test: run the whole toolkit on synthetic data and compare every
output with the expected outputs saved in tests/expected_outputs/.

No ArcGIS Pro, BigQuery, or network access is needed:
  * synthetic_data.py writes made-up warehouse CSVs plus served-shape and road caches
  * fake_arcpy/ is a small in-memory stand-in for arcpy
  * the toolkit runs with offline_context_only=True, so it only reads the caches

Every CSV is compared cell by cell (row order ignored), along with the
geodatabase layer schemas and rows and the run's summary counts. Any
difference fails the test and is listed.

A few named scenarios are also checked directly, with plain-language
messages, so a failure says what behavior broke (see scenario_checks).

Usage (needs pandas 2.x, the version ArcGIS Pro ships):
    python tests/test_end_to_end.py
    python tests/test_end_to_end.py --update-expected   # only after an intended change

Use --update-expected only when a change to the analysis is deliberate and has
been reviewed. It replaces the expected outputs with the current results.
"""
import argparse, json, os, shutil, sys, tempfile
from pathlib import Path
import pandas as pd

tests_dir = Path(__file__).resolve().parent
toolkit_root = tests_dir.parent
expected_dir = tests_dir / "expected_outputs"
sys.path.insert(0, str(tests_dir))
sys.path.insert(0, str(tests_dir / "fake_arcpy"))
sys.path.insert(0, str(toolkit_root))
skipped_files = {"run_manifest.json", "pair_scoring_review.zip"}  # contain run times / zip timestamps


def run_toolkit(work):
    import synthetic_data
    warehouse = work / "warehouse"; road_gdb = work / "road_cache.gdb"; road_gdb.mkdir(parents=True)
    seed = work / "road_cache_seed.json"
    synthetic_data.build(warehouse, seed, str(road_gdb))
    os.environ["FAKE_ARCPY_SEED"] = str(seed)
    import arcpy  # the fake one
    from shared_stop_toolkit import road_context
    road_context._post_json = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network disabled in tests"))
    from shared_stop_toolkit.workflow import run_shared_stop_analysis
    result = run_shared_stop_analysis(warehouse_dir=warehouse, output_root=work / "outputs", add_to_map=False,
                                      offline_context_only=True, road_cache_gdb=str(road_gdb))
    out_dir = Path(result["output_dir"])
    layers = {}
    gdb_key = os.path.normpath(str(out_dir / "analysis.gdb")).lower()
    for key, fc in arcpy._registry.items():
        if key.startswith(gdb_key):
            layers[fc["name"]] = {"fields": fc["fields"], "rows": sorted(json.dumps(r, sort_keys=True, default=str) for r in fc["rows"])}
    counts = {k: (None if v is None else str(v)) for k, v in result.items() if k.endswith("_count") or k.endswith("_error") or k.endswith("_rows")}
    return out_dir, layers, counts


def csv_files(folder):
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*.csv"))


def read_sorted(path):
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    df = df[sorted(df.columns)]
    return df.sort_values(list(df.columns), kind="stable").reset_index(drop=True) if len(df.columns) else df


def scenario_checks(out_dir):
    """Named behaviors the synthetic data was built to exercise."""
    problems = []
    date = next(out_dir.glob("shared_stop_pairs_*.csv")).stem.split("_")[-1]
    pairs = pd.read_csv(out_dir / f"shared_stop_pairs_{date}.csv", dtype=str, keep_default_na=False)
    full = pd.read_csv(out_dir / f"all_stops_scored_full_{date}.csv", dtype=str, keep_default_na=False)
    excluded = pd.read_csv(out_dir / f"source_exclusions_{date}.csv", dtype=str, keep_default_na=False)

    # Cross-format intersection names ("Pioneer / South" vs "PIONEER-SOUTH",
    # about 52 ft apart, two agencies) must be recognized as the same stop.
    sp = pairs[pairs.apply(lambda r: {r["stop_id_a"], r["stop_id_b"]} == {"4389", "0732"}, axis=1)]
    if len(sp) != 1:
        problems.append(f"scenario cross-format names: expected 1 pair for stops 4389/0732, found {len(sp)}")
    else:
        r = sp.iloc[0]
        if r["shared_stop_classification"] != "High-Confidence Shared Stop Candidate":
            problems.append(f"scenario cross-format names: classified as {r['shared_stop_classification']!r}")
        if "same normalized intersection (cross-format)" not in r["shared_stop_evidence"]:
            problems.append("scenario cross-format names: intersection evidence not recognized")
        groups = set(full.loc[full["GTFS_stop_id"].isin(["4389", "0732"]), "physical_location_id"])
        if len(groups) != 1 or "" in groups:
            problems.append("scenario cross-format names: the two stops are not in one physical location")

    # Each source-cleaning rule must remove its synthetic stop.
    by_feed = dict(zip(excluded.get("feed_name", []), excluded.get("source_exclusion_reason", [])))
    expected_exclusions = {
        "Bay Area 511 Regional Schedule": ("regional feed", "BAY_AREA_511_REGIONAL_DUPLICATE"),
        "Foothill Precursor Schedule": ("regional precursor feed", "REGIONAL_PRECURSOR_DUPLICATE"),
        "Metro Light Rail Schedule": ("rail-only route type 0", "RAIL_ONLY"),
        "Metro Rail Schedule": ("rail-only route type 1", "RAIL_ONLY"),
        "Metrolink Schedule": ("rail-only route type 2", "RAIL_ONLY"),
        "Commute Raw Feed": ("exact cross-feed duplicate", "EXACT_CROSS_FEED_DUPLICATE"),
    }
    for feed, (label, reason) in expected_exclusions.items():
        if by_feed.get(feed) != reason:
            problems.append(f"scenario source cleaning: {label} stop was not excluded as {reason} (got {by_feed.get(feed)!r})")
    return problems


def compare(out_dir, layers, counts):
    problems = []
    exp_files, got_files = csv_files(expected_dir / "csv"), csv_files(out_dir)
    for f in sorted(set(exp_files) ^ set(got_files)):
        problems.append(f"{f}: present in only one of expected/actual")
    for f in sorted(set(exp_files) & set(got_files)):
        e, g = read_sorted(expected_dir / "csv" / f), read_sorted(out_dir / f)
        if list(e.columns) != list(g.columns):
            problems.append(f"{f}: columns differ ({sorted(set(e.columns) ^ set(g.columns))[:6]})")
        elif len(e) != len(g):
            problems.append(f"{f}: {len(g)} rows, expected {len(e)}")
        elif not e.equals(g):
            problems.append(f"{f}: values differ in {[c for c in e.columns if not e[c].equals(g[c])][:6]}")
    exp_layers = json.loads((expected_dir / "gdb_layers.json").read_text(encoding="utf-8"))
    for name in sorted(set(exp_layers) | set(layers)):
        if name not in exp_layers or name not in layers:
            problems.append(f"analysis.gdb/{name}: present in only one of expected/actual")
        elif exp_layers[name]["fields"] != layers[name]["fields"]:
            problems.append(f"analysis.gdb/{name}: field names/types/lengths/aliases differ")
        elif exp_layers[name]["rows"] != layers[name]["rows"]:
            problems.append(f"analysis.gdb/{name}: rows differ")
    exp_counts = json.loads((expected_dir / "counts.json").read_text(encoding="utf-8"))
    for k in sorted(set(exp_counts) | set(counts)):
        if exp_counts.get(k) != counts.get(k):
            problems.append(f"count {k}: {counts.get(k)}, expected {exp_counts.get(k)}")
    return problems


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--update-expected", action="store_true")
    ap.add_argument("--keep-work-dir", action="store_true")
    a = ap.parse_args()
    work = Path(tempfile.mkdtemp(prefix="shared_stop_test_"))
    try:
        out_dir, layers, counts = run_toolkit(work)
        if a.update_expected:
            if expected_dir.exists(): shutil.rmtree(expected_dir)
            (expected_dir / "csv").mkdir(parents=True)
            for f in csv_files(out_dir):
                (expected_dir / "csv" / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(out_dir / f, expected_dir / "csv" / f)
            (expected_dir / "gdb_layers.json").write_text(json.dumps(layers, indent=1, sort_keys=True), encoding="utf-8")
            (expected_dir / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True), encoding="utf-8")
            print(f"Expected outputs updated in {expected_dir}")
            return 0
        problems = scenario_checks(out_dir) + compare(out_dir, layers, counts)
        print()
        if problems:
            print(f"END-TO-END TEST FAILED: {len(problems)} difference(s)")
            for p in problems: print("  - " + p)
            return 1
        print(f"END-TO-END TEST PASSED: {len(csv_files(out_dir))} CSV files, {len(layers)} geodatabase layers, "
              f"and {len(counts)} summary counts match the expected outputs.")
        return 0
    finally:
        if a.keep_work_dir: print(f"work folder kept: {work}")
        else: shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
