# Data lineage

This document traces where the toolkit's inputs and analytical context come from and how key values travel to the final outputs. Column-by-column definitions are in the `output_fields` tab of `code_reference.xlsx`, and every configuration value is in its `config_tables` tab.

| Source | Use in the toolkit |
| --- | --- |
| Warehouse `stops_curbside_analysis_<run_stamp>.csv` | Statewide in-scope stop records and GTFS/warehouse attributes used as the analysis source. |
| Warehouse `shared_stop_records_scored_<run_stamp>.csv` | Only `stop_key`, `source_record_key` (checked against the pair keys), and `direction_token` (a boarding-position clue in the two-agency recommendation) are used. |
| Warehouse `shared_stop_pair_scores_<run_stamp>.csv` | Cross-agency pair universe used as the starting relationship set for pair scoring. Every row is scored exactly once. |
| Warehouse `shared_stop_groups_refined_<run_stamp>.csv` (optional) | Row count only, reported as `upstream_group_count`. |
| `config/agency_aliases.csv` | Consistent agency/operator labels keyed by warehouse feed name. |
| `config/source_exclusions.csv` | Explicit regional-feed and rail-only exclusions applied during source cleaning. |
| Pair-scoring configuration tables | Distance bands, scoring rules, thresholds, and output-field definitions used by the shared-stop analysis. |
| Cal-ITP BigQuery `mart_gtfs` served-shape data | Route, direction, shape, service-date, nearest shape-segment, and travel-bearing context. Results are cached locally so the same extraction can be reused. |
| Caltrans All Roads | Nearest-road and road-distance context used for review and permitted tie-breaking only. Road context does not contribute to the Shared Stop Score. |

## Source preparation

The workflow maps the warehouse pair endpoints back to the statewide stop source before cleaning. Agency labels are normalized from the configured feed-name mapping. Regional aggregate copies, qualifying precursor duplicates, rail-only records, and exact cross-feed duplicates are excluded from the analysis source and written to an audit product.

The original GTFS-facing fields are kept separately from toolkit-derived fields. `agency_name` is the toolkit's normalized operator label; it should not be interpreted as the raw `agency.txt` agency name.

## Pair scoring and grouping

Pair scoring operates on cross-agency relationships and uses precise geographic distance rather than geohash membership as proof that records are the same stop. Name, intersection, platform, parent-station, location-type, direction, boarding-side, and other configured evidence can support or conflict with a candidate relationship. The configured rules determine the score and review classification.

Candidate groups are constructed from qualifying pair relationships. Group membership is therefore an analytical candidate relationship, not an assertion that every record in the group is definitely the same physical boarding point.

## Recommended locations and stop-location issues

The recommendation analysis compares the existing stop points represented within each candidate group. A normal recommendation requires cross-agency location support under the configured agreement rules. The workflow recommends an existing published point; it does not calculate a synthetic replacement coordinate.

Potential stop-location issues identify records whose published point is more than 25 feet from a sufficiently supported recommended location, subject to the evidence gates in the recommendation logic.

## Served-shape context

Served-shape context links relevant stops to scheduled GTFS trips and shapes, finds the nearest local shape segment, and derives travel-bearing information. This supports route-direction and boarding-side interpretation, including cases where nearby points represent different travel movements rather than a simple coordinate disagreement.

The extraction is cached in the warehouse folder. A base cache covers the initial service-date lookup; a recovery pass broadens service-date coverage for targets missed by that lookup, and the combined result is saved as the complete cache.

## Road context

Caltrans All Roads centerlines are used to calculate nearest-road context and stop-to-road distance for records needing location review. Road distance is intentionally downstream of the Shared Stop Score and candidate grouping. It can provide review context and a constrained tie-break when the recommendation logic permits it, but it cannot independently establish that two stops are shared or that a stop is incorrect.

## How key values travel

- **Stop ID:** warehouse `stop_id` → `GTFS_stop_id` → used in pair scoring and recommendation → if this record is chosen as the recommended point, its value fills `recommended_stop_id` → CSV "Recommended Stop ID" → layer field `rec_stop_id`.
- **Coordinates:** warehouse `stop_lat` / `stop_lon` → `GTFS_stop_lat` / `GTFS_stop_lon` → every distance calculation → the chosen point's values fill `recommended_lat` / `recommended_lon` → QA `latitude` / `longitude`, which are also the layer geometry.
- **Agency:** warehouse `analysis_name` → `agency_aliases.csv` (keyed on `feed_name`) → `agency_name` → QA `agency` → CSV "Agency". After cleaning, `analysis_name` holds the same normalized label.
- **BoardingSide:** served shapes (BigQuery cache) → which side of travel each shape places the stop on → `boarding_side` per stop → final pair score (+4 when both stops are LIKELY, -6 when LIKELY vs UNLIKELY, same-direction pairs only) and the two-agency recommendation → CSV "BoardingSide" → layer field `board_side`.
- **Road distance:** stop coordinates + All Roads centerlines → `road_nearest_distance_ft` → `road_dist_ft` ("RoadDistFt") → `farthest_road` ("FarthestRoad") → `tiebreak_rec` ("TieBreakRec").
- **Status wording:** internal codes such as `NO_OPERATOR_MAJORITY_WITHIN_25FT` stay unchanged inside the analysis; `status_labels.csv` turns them into the wording people see, such as "No agency majority agrees within 25 ft".

## Evidence and context

Evidence can change the Shared Stop Score, grouping, or the normal recommendation: distance band, names and intersections, platform codes, parent station, direction words, near/far-side wording, location type, and BoardingSide for same-direction pairs.

Context never changes the score or grouping: road-centerline distance feeds only RoadDistFt / FarthestRoad / TieBreakRec, and TieBreakRec applies only when no normal recommendation exists. One road measure does take part in the two-agency recommendation: a stop with a single unambiguous nearby roadway (road_context_ambiguous = N) gets +1 in its boarding-position score, alongside side-of-intersection wording (+2), a named direction matching the served-route direction (+3), a platform code (+1), and available served-shape context (+1).

## Final products

The workflow writes detailed and summary QA CSVs and feature classes, pair/group review outputs, recommendation and issue tables, served-shape and road-context support products, and a run manifest recording the code fingerprint and git commit, the source run, inputs, configuration row counts, caches used, output files, and headline counts.
