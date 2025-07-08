# GTFS Catalog Automation Test Checklist

This checklist will help you verify that the GTFS catalog automation script and workflow are working as intended.

## 1. Local Script Test
- [ ] Download the Google Sheet as CSV and save as `OpenMobilityData source updates - PROD - GTFS Catalog.csv` in the repo root.
- [ ] Run the script locally:
  ```sh
  python3 scripts/gtfs_catalog_automation.py
  ```
- [ ] Confirm that new/updated JSON files are created in:
  - `catalogs/sources/gtfs/schedule/`
  - `catalogs/sources/gtfs/realtime/`
- [ ] Open a few generated JSON files and check:
  - [ ] Correct schema (fields, types, required keys)
  - [ ] Correct filename conventions
  - [ ] Fuzzy static references are set for realtime feeds

## 2. Schema & Integration Test
- [ ] Run integration tests:
  ```sh
  pytest tests/test_integration.py
  ```
- [ ] Confirm all tests pass (schema, uniqueness, incrementality)

## 3. GitHub Actions Workflow Test
- [ ] Push changes to a branch and open a PR, or manually trigger the workflow in GitHub Actions.
- [ ] Confirm the workflow:
  - [ ] Downloads the correct Google Sheet as CSV
  - [ ] Runs the automation script
  - [ ] Commits and pushes changes
  - [ ] Opens a PR if there are updates
- [ ] Review the PR for correct file changes

## 4. Error Handling
- [ ] Test with a row missing required fields (e.g., no Download URL) and confirm the script logs a clear error or fails gracefully.
- [ ] Test with duplicate Download URLs and confirm only one static reference is created per unique feed.

## 5. Slack Notification (if enabled)
- [ ] Confirm Slack notifications are sent on success and failure (if configured in your secrets).

---

**If all boxes are checked, your automation is working as intended!**
