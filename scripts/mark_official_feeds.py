# Set is_official on catalog sources from a reviewed report.
#
# is_official says whether a feed comes directly from the agency ("True") or was built by
# researchers or partners unaffiliated with it ("False"). See the is_official row of
# README.md for the field definition.
#
# The judgement is not something this script can make, so it comes from the report: a
# final_decision column holding true or false, the outcome of a review. The report is
# produced against the whole Mobility Database, which holds feeds this catalog does not,
# so ids outside it are counted and skipped.
#
#   python scripts/mark_official_feeds.py query_result.csv
#   python scripts/mark_official_feeds.py decisions.html --apply --report official.csv
#
# Dry run by default. Nothing is written unless --apply is passed. A decision that
# disagrees with the value already in the file wins, because it is the later review, and
# every such overwrite is called out as CHANGED in the run summary and the review CSV.
#
# This script is intentionally standalone (standard library only). tools.helpers pulls in
# gtfs_kit, which needs GDAL, so scripts/ re-declares the handful of constants it needs
# instead of importing the tools package. Same convention as scripts/create_urls_matrix.py.
import argparse
import os
import sys

# The report reading and catalog writing live next door, shared with the other marking
# scripts. Reach them by directory rather than as a package, because scripts/ is not one
# and this file is also loaded by path from the tests.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from catalog_reports import (  # noqa: E402
    ALL,
    DIRECT_DOWNLOAD,
    FALSE,
    GTFS,
    GTFS_RT,
    IS_OFFICIAL,
    PROVIDER,
    STABLE_ID,
    STATUS,
    TRUE,
    URLS,
    id_prefix,
    index_sources,
    parse_reports,
    set_source_field,
    to_source_id,
    write_report,
)

# The column carrying the review's verdict. The scripts' own review CSV spells it
# is_official, so a CSV this script wrote can be fed straight back in.
DECISION_COLUMNS = ("final_decision", "is_official")

# What the report may say, and the string the catalog stores. The field is a string enum
# in schemas/gtfs_schedule_source_schema.json, not a JSON boolean, so "true" becomes the
# string "True" rather than true.
DECISIONS = {
    "true": TRUE,
    "false": FALSE,
    TRUE.lower(): TRUE,
    FALSE.lower(): FALSE,
    "1": TRUE,
    "0": FALSE,
    "yes": TRUE,
    "no": FALSE,
}

# Outcomes, which double as the review CSV's outcome column.
SET = "set"
CHANGED = "changed"
UNCHANGED = "unchanged"

REPORT_COLUMNS = [
    "stable_id",
    "mdb_source_id",
    "provider",
    "status",
    "direct_download",
    "decision",
    "is_official",
    "previous",
    "outcome",
]


def read_decision(row):
    """
    Reads the review's verdict out of a report row.

    Args:
        row (dict): A parsed report row.

    Returns:
        tuple: The raw value as the report spells it, and the string to store, which is
            None when the row carries no verdict this script recognises.
    """
    for name in DECISION_COLUMNS:
        raw = (row.get(name) or "").strip()
        if raw:
            return raw, DECISIONS.get(raw.lower())
    return "", None


def mark_sources(args):
    """
    Sets is_official on the sources the reports name.

    Args:
        args (Namespace): The parsed command line arguments.

    Returns:
        list: The review rows for every source the reports resolved to.
    """
    rows, total = parse_reports(args.reports)
    sources = index_sources(args.data_type)

    reviewed = []
    unresolved = []
    unrecognised = []
    skipped = {}

    for row in rows:
        stable_id = row[STABLE_ID]
        raw, value = read_decision(row)
        source_id = to_source_id(stable_id)

        if source_id is None:
            prefix = id_prefix(stable_id)
            skipped[prefix] = skipped.get(prefix, 0) + 1
            continue
        if source_id not in sources:
            unresolved.append(stable_id)
            continue
        if value is None:
            unrecognised.append((stable_id, raw))
            continue

        file_path, source = sources[source_id]
        previous = source.get(IS_OFFICIAL)
        if previous is None:
            outcome = SET
        elif previous != value:
            outcome = CHANGED
        else:
            outcome = UNCHANGED

        reviewed.append(
            {
                "stable_id": stable_id,
                "mdb_source_id": source_id,
                "provider": source.get(PROVIDER),
                "status": source.get(STATUS) or "",
                "direct_download": source.get(URLS, {}).get(DIRECT_DOWNLOAD, ""),
                "decision": raw,
                "is_official": value,
                "previous": previous or "",
                "outcome": outcome,
            }
        )
        # A source already carrying the right value is left alone, so a rerun touches
        # nothing and the diff stays honest about what the review actually changed.
        if args.apply and outcome != UNCHANGED:
            # The catalog carries is_official right after provider in 833 of the 1196
            # files that have it, so a new field goes there.
            set_source_field(file_path, source, IS_OFFICIAL, value, after=PROVIDER)

    reviewed.sort(key=lambda row: row["mdb_source_id"])
    for row in reviewed:
        if row["outcome"] == UNCHANGED:
            continue
        label = "CHANGED" if row["outcome"] == CHANGED else "set    "
        was = f" was {row['previous']}" if row["outcome"] == CHANGED else ""
        print(f"{label}  {row['stable_id']:>12}  is_official {row['is_official']}{was}")
        print(f"                       {row['provider']}")

    counts = {outcome: 0 for outcome in (SET, CHANGED, UNCHANGED)}
    for row in reviewed:
        counts[row["outcome"]] += 1

    print()
    report_count = len(args.reports)
    plural = "" if report_count == 1 else "s"
    print(
        f"Read {report_count} report{plural}, {total} rows, {len(rows)} unique stable ids."
    )
    if skipped:
        detail = ", ".join(
            f"{prefix} {count}"
            for prefix, count in sorted(skipped.items(), key=lambda item: -item[1])
        )
        count = sum(skipped.values())
        noun = "id" if count == 1 else "ids"
        print(f"Skipped {count} {noun} outside this catalog: {detail}.")
    print(
        f"Resolved {len(reviewed)} sources: {counts[SET]} newly set, "
        f"{counts[CHANGED]} changed, {counts[UNCHANGED]} already correct."
    )
    for value in (TRUE, FALSE):
        count = sum(1 for row in reviewed if row["is_official"] == value)
        print(f'  {count:>4}  is_official "{value}"')

    if unrecognised:
        print()
        print(f"Skipped, the decision column was not understood: {len(unrecognised)}")
        for stable_id, raw in unrecognised:
            print(f"  {stable_id:>12}  {raw!r}")

    if unresolved:
        print()
        print(
            f"Named but not in the catalog, the report has drifted: {len(unresolved)}"
        )
        for stable_id in unresolved:
            print(f"  {stable_id}")

    return reviewed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Set is_official on catalog sources from a reviewed report, taking the "
            "verdict from its final_decision column."
        )
    )
    parser.add_argument(
        "reports",
        nargs="+",
        help=(
            "Reports naming the feeds and their verdict. An .html report table or a "
            ".csv, either way carrying a stable_id column and a final_decision column. "
            "Ids outside this catalog are counted and skipped."
        ),
    )
    parser.add_argument(
        "--data-type",
        choices=[GTFS, GTFS_RT, ALL],
        default=ALL,
        help="Which catalog to work on. Defaults to all.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write is_official into the resolved files.",
    )
    parser.add_argument("--report", help="Path of the review CSV to write.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    reviewed = mark_sources(args)
    written = [row for row in reviewed if row["outcome"] != UNCHANGED]

    if args.report:
        write_report(args.report, REPORT_COLUMNS, reviewed)
        print()
        print(f"Report written to {args.report}")

    print()
    if args.apply:
        print(f"Wrote is_official to {len(written)} files.")
    else:
        print("Dry run, nothing written. Pass --apply to write.")


if __name__ == "__main__":
    main()
