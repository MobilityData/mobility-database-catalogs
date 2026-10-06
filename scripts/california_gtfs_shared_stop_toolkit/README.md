# California GTFS Shared-Stop Toolkit

The California GTFS Shared-Stop Toolkit reviews statewide GTFS stop records to identify places where different transit agencies may be using the same physical boarding location. It combines GTFS stop attributes, precise stop-to-stop distances, served-route direction context, and road context to support statewide quality assurance without changing the source GTFS data.

## What the toolkit does

The workflow starts from the prepared statewide warehouse stop files and evaluates cross-agency stop relationships. It scores candidate pairs, groups records that may represent shared boarding locations, evaluates whether an existing stop point is supported as the recommended location, and flags records that are more than 25 feet from a supported location for review.

Served-shape context is used to distinguish route-movement and boarding-side situations that coordinates and stop names alone cannot explain. Caltrans All Roads centerlines provide additional road context and a limited tie-break measure. Road context does not contribute to the Shared Stop Score or grouping. Road distance is used only in the post-scoring tie-break (RoadDistFt, FarthestRoad, TieBreakRec). The one other road measure in use is whether a stop has a single unambiguous nearby roadway, which adds 1 point to the boarding-position score in the two-agency recommendation.

The toolkit does not create synthetic replacement stop coordinates. When it recommends a location, the recommendation is an existing published stop point supported by the available evidence.

## Repository structure

```text
california_gtfs_shared_stop_toolkit/
├── README.md
├── arcgis_pro_notebook.ipynb
├── run_shared_stop_analysis.py
├── shared_stop_toolkit/
│   ├── __init__.py
│   ├── workflow.py
│   ├── pair_scoring.py
│   ├── recommendation.py
│   ├── road_context.py
│   ├── shape_context.py
│   └── config/
│       ├── agency_aliases.csv
│       ├── source_exclusions.csv
│       ├── status_labels.csv
│       ├── shared_stop_scoring_rules.csv
│       ├── shared_stop_thresholds.csv
│       ├── shared_stop_distance_bands.csv
│       ├── field_defs.csv
│       └── final_feature_fields.csv
├── docs/
│   ├── data_lineage.md
│   └── code_reference.xlsx
└── tests/
    ├── test_end_to_end.py
    ├── synthetic_data.py
    ├── fake_arcpy/
    └── expected_outputs/
```

## Main Python modules

`workflow.py` coordinates the statewide run: input discovery, source preparation and cleaning, pair scoring, context analysis, QA products, geodatabase outputs, and the run manifest.

`pair_scoring.py` calculates the Shared Stop Score for cross-agency pairs, applies the configured evidence and conflict rules, and builds candidate shared-stop groups.

`recommendation.py` evaluates the physical locations represented within a group, determines whether an existing published point has sufficient cross-agency support, and identifies potential stop-location issues.

`shape_context.py` obtains or reuses served GTFS shape context and summarizes travel-direction evidence used for boarding-side and route-movement review.

`road_context.py` measures stops against Caltrans All Roads centerlines for review context and permitted tie-breaking. It does not alter pair scores or candidate grouping. See the road note above for the two places road context is used.

`run_shared_stop_analysis.py` is the command-line launcher.

## Configuration tables

Rules and lookup values that should be reviewable outside Python are stored under `shared_stop_toolkit/config/`. Every table is checked when a run starts. A missing file or column, an unknown setting, rule, category, or exclusion type, a blank value, a duplicate key, or a number that cannot be read stops the run with a message naming the problem. The number of rows loaded from each table is printed and saved in the run manifest.

Two further checks happen during the run. If a feed name in `agency_aliases.csv` or a regional feed in `source_exclusions.csv` does not appear in the warehouse run, a warning is printed and recorded in the manifest, because a misspelled feed name would otherwise do nothing. If the analysis produces a status code that has no row in `status_labels.csv`, the run stops and names the code, instead of inventing wording for it.

A deleted row that is still well-formed (for example removing one rail route type) cannot be told apart from an intended edit. The end-to-end test is the safety net for that: it includes a stop for each exclusion rule and fails if any of them stops being excluded.

- `agency_aliases.csv` maps warehouse feed names to the consistent agency/operator labels used by the analysis.
- `source_exclusions.csv` defines explicit regional-feed and rail-only source exclusions.
- `status_labels.csv` translates internal machine-readable status codes into plain-language review labels.
- `shared_stop_scoring_rules.csv`, `shared_stop_thresholds.csv`, and `shared_stop_distance_bands.csv` define the pair-scoring logic and distance ranges.
- `field_defs.csv` lists the fields this toolkit creates or uses, with plain-language notes, and sets their column order in the full scored CSV. Columns not listed keep their incoming order after the listed ones.
- `final_feature_fields.csv` lists the 19 fields in the shorter review CSV, in order.

The 25-ft stop-location threshold is not a config setting. It is `issue_threshold_ft` in `recommendation.py`, and the same 25 ft is built into the two-agency rule and the review wording, so changing it is a code change that should be reviewed as one.

## Analysis sequence

1. Find the newest warehouse run containing the required stop, candidate-record, and pair files.
2. Prepare source records and apply the configured agency labels and source-cleaning rules.
3. Score cross-agency stop pairs using precise distance and other shared-stop evidence.
4. Build candidate shared-stop groups from qualifying pair relationships.
5. Obtain served-shape context for records that need route-direction or boarding-side evidence, then finalize pair scoring.
6. Evaluate physical-location agreement and determine whether an existing stop point is sufficiently supported as a recommended location.
7. Add road context and the permitted road-distance tie-break information.
8. Produce statewide QA tables, review CSVs, ArcGIS feature classes, and a run manifest.

## Inputs

The workflow expects one matching warehouse run containing:

- `stops_curbside_analysis_<run_stamp>.csv`
- `shared_stop_records_scored_<run_stamp>.csv`
- `shared_stop_pair_scores_<run_stamp>.csv`

Served-shape cache files may also be present in the warehouse folder. The toolkit looks for `shared_stop_shape_context_shapes_complete_<run_stamp>.csv` first, then the `_base_` cache. When neither exists, the normal workflow queries Cal-ITP BigQuery, subject to a dry-run cost ceiling, and saves the results as caches for later runs. Road context can likewise be reused from an existing geodatabase cache named `Caltrans_All_Roads_GTFS_Context_<run_stamp>`.

See `docs/data_lineage.md` for the source and purpose of the major input and derived fields.

## Running the toolkit

The primary workflow is an **ArcGIS Pro notebook**, because the analysis writes geodatabase products and can add the final QA layers to the active ArcGIS Pro map. Open `arcgis_pro_notebook.ipynb` in ArcGIS Pro, edit the paths and settings at the top of its code cell, and run the cell.

The notebook settings are:

- `toolkit_location`: the toolkit, either a ZIP downloaded from GitHub or a folder such as a git clone. A ZIP is extracted to a short local folder first to avoid Windows path-length problems.
- `warehouse_dir`: the folder with the warehouse CSVs and served-shape caches.
- `road_cache_gdb`: a geodatabase that already holds the road cache for this warehouse run, or `None`.
- `offline_context_only`: `True` (default) uses only cached shapes and roads and stops if a cache is missing, so the run never queries BigQuery or the road service by surprise. `False` uses caches when they exist and queries the services when they don't.
- `add_to_map`: add the two final QA layers to the active map.
- `replace_existing_outputs`: allow overwriting an output folder made by different toolkit code.

If the repository itself is already on the Python path, the workflow can also be called directly:

```python
from shared_stop_toolkit.workflow import run_shared_stop_analysis

result = run_shared_stop_analysis(
    warehouse_dir=r"C:\path\to\california_gtfs_warehouse"
)
```

A command-line runner is also included for users who do not want to launch the analysis from a notebook:

```text
python run_shared_stop_analysis.py --warehouse-dir "C:\path\to\california_gtfs_warehouse"
```

By default, outputs are written under:

```text
<warehouse>/outputs/<run_stamp>/analysis/
```

The folder uses the full warehouse run stamp (for example `outputs/20260916_135658/analysis/`), so two warehouse runs on the same day never share a folder. File names inside it use the 8-digit source date.

Use `--offline-context-only` when a run must use existing served-shape and road caches rather than querying external services. `--road-cache-gdb` can point to a geodatabase containing an existing road-context cache.

If the output folder already holds results made by different toolkit code, the run stops rather than overwriting them. Move or rename that folder, choose a different `--output-root`, or pass `--replace-existing-outputs`.

## Outputs

Each run writes to `<warehouse>/outputs/<run_stamp>/analysis/`:

| File | What it is |
|---|---|
| `shared_stop_candidates_<date>.csv` | Every stop in a shared-stop group, with its recommendation |
| `stop_location_issues_over_25ft_<date>.csv` | Stops that are probably misplaced by more than 25 ft |
| `gtfs_stops_qa_detail_<date>.csv`, `shared_stop_qa_summary_<date>.csv` | QA tables; also map layers in `analysis.gdb` |
| `all_stops_scored_full_<date>.csv`, `all_stops_scored_review_<date>.csv` | Every in-scope stop, with all fields or with the 19 review fields |
| `shared_stop_pairs_<date>.csv`, `shared_stop_groups_<date>.csv` | Pair scores and shared-stop groups |
| `shared_stop_recommendation_summary_<date>.csv`, `shared_stop_unresolved_locations_<date>.csv` | Recommended points, and locations that need a person |
| `stop_location_issues_detail_<date>.csv`, `stop_location_issues_suppressed_<date>.csv` | Issue details, and >25-ft records that were not flagged and why |
| `road_context_*`, `served_shape_context_*`, `shape_*_summary_*` | Supporting context tables |
| `source_exclusions_<date>.csv`, `boarding_side_diagnostic_<date>.csv` | Source-cleaning audit and BoardingSide diagnostic |
| `pair_scoring_review/` and `.zip` | Pair-scoring review files |
| `analysis.gdb` | Map layers: `gtfs_stops_qa_detail`, `shared_stop_qa_summary`, `road_context_points`, `served_shape_segments`, and the road cache |
| `run_manifest.json` | Code fingerprint and git commit, source run, inputs and row counts, config row counts, caches used, outputs, and headline counts |

The `output_fields` tab of `docs/code_reference.xlsx` explains every column. The Shared Stop Score is an evidence score, not a probability.

## Documentation

`docs/code_reference.xlsx` has one worksheet for each Python file, including the tests. Each worksheet lists every module-level setting, function, class, and method, with its parameters, values, what it does, and why it works that way. The `config_tables` tab lists every configuration row with its purpose, and the `output_fields` tab explains every output column.

`docs/data_lineage.md` traces values from their outside sources to the final outputs.

## Testing

`tests/test_end_to_end.py` runs the whole toolkit on synthetic data and compares every output CSV, geodatabase layer, and summary count with the saved results in `tests/expected_outputs/`. It also checks named scenarios directly, such as two agencies writing the same intersection in different formats ("Pioneer / South" and "PIONEER-SOUTH") and each source-cleaning rule removing its test stop, so a failure says which behavior changed. It needs only Python with pandas 2.x; ArcGIS Pro, BigQuery, and network access are not required, because it uses an in-memory stand-in for arcpy and cached context.

```text
python tests/test_end_to_end.py
```

Run it after any code or configuration change. If a difference is intended and has been reviewed, rebuild the expected outputs with `python tests/test_end_to_end.py --update-expected`, and commit them together with the change so the difference is visible in the pull request.
