# Find schedule and realtime feeds whose producer URL carries evidence of a date or a
# version, and flag them with is_producer_url_unstable = "True".
#
# A producer URL containing a date or a rotating version number will stop resolving once
# the producer publishes again, so the feed needs manual attention more than twice a year.
# See the is_producer_url_unstable row of README.md for the field definition.
#
# Dry run by default. Nothing is written unless --apply is passed, and the field is only
# ever set to "True" -- feeds without evidence are left untouched.
#
#   python scripts/identify_unstable_urls.py --report unstable_urls.csv --weak
#   python scripts/identify_unstable_urls.py --apply
#
# This script is intentionally standalone (standard library only). tools.helpers pulls in
# gtfs_kit, which needs GDAL, so scripts/ re-declares the handful of constants it needs
# instead of importing the tools package. Same convention as scripts/create_urls_matrix.py.
import argparse
import csv
import json
import os
import re
from urllib.parse import unquote, urlsplit

# OS constants
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# tools.constants
GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/schedule"
GTFS_REALTIME_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/realtime"
GTFS = "gtfs"
GTFS_RT = "gtfs-rt"
ALL = "all"
MDB_SOURCE_ID = "mdb_source_id"
DATA_TYPE = "data_type"
PROVIDER = "provider"
STATUS = "status"
URLS = "urls"
DIRECT_DOWNLOAD = "direct_download"
IS_PRODUCER_URL_UNSTABLE = "is_producer_url_unstable"

# Field constants
TRUE = "True"
DEPRECATED = "deprecated"

# Report constants
REPORT_COLUMNS = [
    "mdb_source_id",
    "data_type",
    "provider",
    "status",
    "direct_download",
    "rules",
    "matched_text",
]

# A sentinel that no pattern can match, used to blank out stable tokens before scanning.
SENTINEL = "\x00"


#########################
# STABLE TOKENS
#########################

# Substrings that look like dates or versions but never change when the feed is
# republished. They are blanked out before the unstable patterns run, so they cannot
# contribute a match. Every entry here corresponds to a real cluster in the catalog.
STABLE_PATTERNS = [
    # CKAN dataset and resource keys.
    (
        "uuid",
        re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE,
        ),
    ),
    # ArcGIS item ids, Wix and hibu site keys, opendatasoft file ids. Deliberately only
    # 32 hex characters: a 40 character run is a git commit SHA, which is not stable.
    ("hex_id", re.compile(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])", re.IGNORECASE)),
    # Azure storage service API version. This is the freshest looking date in a SAS URL
    # and it never changes, unlike the st= and se= window which we do want to see.
    ("azure_service_version", re.compile(r"[?&]sv=\d{4}-\d{2}-\d{2}")),
    ("azure_signature", re.compile(r"[?&]sig=[^&]*")),
    # Credentials. A 40 hex character Mecatran apiKey reads exactly like a pinned git
    # commit, and no date inside a key ever means anything.
    (
        "credential",
        re.compile(
            r"(?<=[?&])(?:api_?key|access_?token|token|key|subscription-key)=[^&]*",
            re.IGNORECASE,
        ),
    ),
    # A bare /vN/ path segment is an API version, not a feed version.
    ("api_version_segment", re.compile(r"(?<=/)v\d{1,2}(?=/|$)", re.IGNORECASE)),
    # So is a /vN.0/ segment: the zero minor is decorative. data.waltti.fi serves eleven
    # feeds from /v1.0/. A non-zero minor is kept, because gateway.carris.pt really did
    # move from /v2.8/ to /v2.11/.
    (
        "api_version_segment_dotted",
        re.compile(r"(?<=/)v?\d{1,2}\.0(?=/|$)", re.IGNORECASE),
    ),
    # The numeric feed key in a transitfeeds.com permalink.
    ("transitfeeds_id", re.compile(r"/p/[^/]+/\d+(?=/latest)")),
    # Google Drive file ids.
    ("drive_file_id", re.compile(r"(?<=[?&]id=)[A-Za-z0-9_-]{25,}")),
]


#########################
# UNSTABLE PATTERNS
#########################

MONTHS_ABBREVIATED = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"

# Full month names only. Short and ambiguous forms (may, mai, mars, marco, marz, aout)
# are left out because they collide with place and agency names.
MONTHS_SPELLED_OUT = "|".join(
    [
        # English
        "january|february|march|april|june|july|august|september|october|november|december",
        # Spanish
        "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre",
        # Portuguese
        "janeiro|fevereiro|março|maio|junho|julho|setembro|outubro|novembro|dezembro",
        # French
        "janvier|fevrier|février|avril|juin|juillet|decembre|décembre",
        # German
        "januar|februar|märz|juni|juli|oktober|dezember",
        # Italian
        "gennaio|febbraio|aprile|maggio|giugno|luglio|settembre|ottobre|dicembre",
    ]
)

SEASONS = "winter|spring|summer|fall|autumn"

# Evidence that the producer URL encodes a point in time or a revision. Any match means
# the URL is unstable. Each rule is named so the report can say which one fired.
UNSTABLE_PATTERNS = [
    # Republishing to a WordPress media library moves the file to a new year/month
    # folder. The optional inner segments absorb the /sites/<n>/ multisite id.
    (
        "wordpress_upload_folder",
        re.compile(r"wp-content/uploads/(?:[^/]+/){0,2}(?:19|20)\d{2}/\d{1,2}/"),
    ),
    # YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD, YYYY.MM.DD, optionally carrying an HHMM or
    # HHMMSS time, as in mvv_ohneShape_20241004095702.zip.
    (
        "iso_date",
        re.compile(
            r"(?<!\d)(?:19|20)\d{2}([-_./]?)(?:0[1-9]|1[0-2])\1(?:0[1-9]|[12]\d|3[01])"
            r"(?:\d{4}|\d{6})?(?!\d)"
        ),
    ),
    # A bare year and month, as in gtff-202311. Six digits exactly, with a valid month,
    # which is tight enough to leave every stable numeric id in the catalog alone.
    ("year_month", re.compile(r"(?<!\d)20(?:1\d|2\d)(?:0[1-9]|1[0-2])(?!\d)")),
    # Day first dates, which a year-anchored pattern misses entirely: 03.10.2025, 5.12.21.
    (
        "locale_date",
        re.compile(
            r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])([-_.])(?:0?[1-9]|1[0-2])\1(?:19|20)?\d{2}(?!\d)"
        ),
    ),
    # Release tags built out of a date: 2020.0401.1.
    (
        "dated_version_tag",
        re.compile(r"(?<!\d)(?:19|20)\d{2}[-_.]\d{2,4}[-_.]\d{1,4}(?!\d)"),
    ),
    # A standalone year. Anchored to delimiters on both sides: an unanchored 20\d\d also
    # matches hex id fragments, feed keys and the WordPress multisite id.
    ("delimited_year", re.compile(r"(?<![0-9A-Za-z])20(?:1\d|2\d)(?![0-9A-Za-z])")),
    # A year fused to a season, quarter or year-type label, which delimited_year skips
    # on purpose: 2025Winter, Spring2025, Q1-CY2025, CY2026.
    (
        "labelled_year",
        re.compile(
            r"20\d{2}[-_ ]?(?:" + SEASONS + r"|q[1-4])"
            r"|(?:" + SEASONS + r"|q[1-4])[-_ ]?20\d{2}"
            r"|(?<![a-z])(?:cy|fy|sy)[-_ ]?20\d{2}(?!\d)",
            re.IGNORECASE,
        ),
    ),
    (
        "month_name",
        re.compile(
            r"(?<![a-z])(?:" + MONTHS_SPELLED_OUT + r")(?![a-z])", re.IGNORECASE
        ),
    ),
    # An abbreviated month only counts when it is fused to digits, as in coquimbo10feb16.
    # On its own it collides with maryland, septa, octranspo, juneau and friends.
    (
        "month_abbreviation_with_digits",
        re.compile(
            r"(?:(?<!\d)\d{1,2}[-_. ]?(?:"
            + MONTHS_ABBREVIATED
            + r")\.?[-_. ]?\d{2,4}(?!\d)"
            r"|(?<![a-z])(?:" + MONTHS_ABBREVIATED + r")\.?[-_. ]?(?:19|20)\d{2}(?!\d))"
            r"(?![a-z])",
            re.IGNORECASE,
        ),
    ),
    # A dotted version bumps on every publication: api/v2.8/, ?v=0.16.0, v1.0.0.
    (
        "dotted_version",
        re.compile(r"(?<![\w.])v?\d{1,4}\.\d{1,4}(?:\.\d{1,4})?(?!\d)", re.IGNORECASE),
    ),
    # A multi digit counter, as in GTFS-V126. A bare vN is an API version, not a feed one.
    ("large_version_counter", re.compile(r"(?<![a-z0-9])v\d{2,}(?!\d)", re.IGNORECASE)),
    ("version_query_parameter", re.compile(r"[?&]version=\d{4,}", re.IGNORECASE)),
    ("epoch_timestamp", re.compile(r"(?<!\d)1\d{9}(?:\.0)?(?!\d)")),
    # .NET DateTime.Ticks, which changes on every republish.
    ("dotnet_ticks", re.compile(r"(?<!\d)6\d{17}(?!\d)")),
    ("pinned_git_sha", re.compile(r"(?<=/)[0-9a-f]{40}(?=/)", re.IGNORECASE)),
    (
        "cache_buster",
        re.compile(
            r"[?&](?:refresh|cachebust|nocache|timestamp|_ts)=[0-9a-f]{8,}",
            re.IGNORECASE,
        ),
    ),
    # The expiry window of an Azure shared access signature is a hard rotation deadline.
    ("shared_access_signature_window", re.compile(r"[?&]s[te]=\d{4}-\d{2}-\d{2}")),
]

# Signals too noisy to act on, surfaced by --weak so they can be reviewed by hand.
WEAK_PATTERNS = [
    ("bare_api_version", re.compile(r"(?<![a-z0-9])v\d(?![0-9])", re.IGNORECASE)),
    (
        "unanchored_month_abbreviation",
        re.compile(
            r"(?<![a-z])(?:" + MONTHS_ABBREVIATED + r")(?![a-z])", re.IGNORECASE
        ),
    ),
    ("long_digit_run", re.compile(r"(?<!\d)\d{8,}(?!\d)")),
]


#########################
# DETECTION
#########################


def scannable(url):
    """
    Reduces a URL to the part worth scanning for dates and versions.

    Only the path, query and fragment can carry a rotating identifier. Dropping the
    scheme and the host removes the three largest sources of false positives in the
    catalog: digits inside hostnames, raw IPv4 hosts and explicit port numbers.

    Args:
        url (str): The URL to reduce.

    Returns:
        str: The percent-decoded path, query and fragment of the URL.
    """
    parts = urlsplit(url)
    return unquote(f"{parts.path}?{parts.query}#{parts.fragment}")


def redact_stable_tokens(text):
    """
    Blanks out substrings that look like a date or a version but never change.

    Args:
        text (str): The text to redact.

    Returns:
        str: The text with every stable token replaced by sentinel characters.
    """
    for _, pattern in STABLE_PATTERNS:
        text = pattern.sub(lambda match: SENTINEL * len(match.group()), text)
    return text


def find_signals(url, patterns):
    """
    Applies a set of named patterns to the scannable part of a URL.

    Every pattern is tried and every match is kept, rather than stopping at the first
    one: a URL can carry conflicting dates, such as a 2018 upload folder holding a file
    named for 2025, and the report is more useful when it shows both.

    Args:
        url (str): The URL to scan.
        patterns (list): A list of (rule name, compiled pattern) tuples.

    Returns:
        list: A list of (rule name, matched text) tuples, in pattern order.
    """
    text = redact_stable_tokens(scannable(url))
    signals = []
    for name, pattern in patterns:
        for match in pattern.finditer(text):
            matched = match.group().strip()
            if matched:
                signals.append((name, matched))
    return signals


def is_unstable(url):
    """
    Tells whether a producer URL shows evidence of a date or a version.

    Args:
        url (str): The producer URL to test.

    Returns:
        list: The (rule name, matched text) signals found. Empty when the URL looks stable.
    """
    return find_signals(url, UNSTABLE_PATTERNS)


#########################
# CATALOG
#########################


def catalog_paths(data_type):
    """
    Lists the catalog directories to scan for the given data type.

    Args:
        data_type (str): One of GTFS, GTFS_RT or ALL.

    Returns:
        list: The absolute paths of the catalog directories to walk.
    """
    paths = []
    if data_type in (GTFS, ALL):
        paths.append(os.path.join(ROOT, GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT))
    if data_type in (GTFS_RT, ALL):
        paths.append(os.path.join(ROOT, GTFS_REALTIME_CATALOG_PATH_FROM_ROOT))
    return paths


def load_sources(data_type):
    """
    Reads every source file for the given data type.

    Args:
        data_type (str): One of GTFS, GTFS_RT or ALL.

    Returns:
        list: A list of (file path, source dict) tuples, sorted by mdb_source_id.
    """
    sources = []
    for catalog_path in catalog_paths(data_type):
        for path, _, files in os.walk(catalog_path):
            for file in files:
                if not file.endswith(".json"):
                    continue
                file_path = os.path.join(path, file)
                with open(file_path) as fp:
                    sources.append((file_path, json.load(fp)))
    return sorted(sources, key=lambda entry: entry[1].get(MDB_SOURCE_ID, 0))


def flag_source(file_path, source):
    """
    Writes is_producer_url_unstable = "True" into a source file.

    The field is appended as the last top-level key so the rest of the file keeps its
    existing key order, which holds the diff down to the added line. The dump matches
    tools.helpers.to_json: four space indent and non-ASCII preserved. Whether the file
    ends in a newline is carried over from the file itself, because the catalog is split
    on that point and rewriting it either way would only add noise to the diff.

    Args:
        file_path (str): The path of the source file to rewrite.
        source (dict): The parsed source, which is mutated in place.

    Returns:
        None
    """
    with open(file_path) as fp:
        ends_with_newline = fp.read().endswith("\n")
    source[IS_PRODUCER_URL_UNSTABLE] = TRUE
    with open(file_path, "w") as fp:
        json.dump(source, fp, indent=4, ensure_ascii=False)
        if ends_with_newline:
            fp.write("\n")


#########################
# REPORTING
#########################


def format_signals(signals):
    """
    Renders signals into the two report columns.

    Args:
        signals (list): A list of (rule name, matched text) tuples.

    Returns:
        tuple: A pipe delimited rule name string and a pipe delimited matched text string.
    """
    names = []
    for name, _ in signals:
        if name not in names:
            names.append(name)
    matches = []
    for _, matched in signals:
        if matched not in matches:
            matches.append(matched)
    return "|".join(names), "|".join(matches)


def write_report(path, rows):
    """
    Writes the review report.

    Args:
        path (str): The path of the CSV file to write.
        rows (list): The report rows, as dicts keyed by REPORT_COLUMNS.

    Returns:
        None
    """
    with open(path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


#########################
# MAIN
#########################


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Flag schedule and realtime feeds whose producer URL shows evidence of a "
            'date or a version by setting is_producer_url_unstable to "True".'
        )
    )
    parser.add_argument(
        "--data-type",
        choices=[GTFS, GTFS_RT, ALL],
        default=ALL,
        help="Which catalog to scan. Defaults to all.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help='Write is_producer_url_unstable = "True" into matching files.',
    )
    parser.add_argument(
        "--include-deprecated",
        action="store_true",
        help="Also scan sources whose status is deprecated. Skipped by default.",
    )
    parser.add_argument("--report", help="Path of the review CSV to write.")
    parser.add_argument(
        "--weak",
        action="store_true",
        help="Also list the weak signals that are never flagged, for manual review.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    flagged = []
    already_set = []
    skipped_deprecated = 0
    weak = []
    scanned = 0

    for file_path, source in load_sources(args.data_type):
        status = source.get(STATUS)
        if status == DEPRECATED and not args.include_deprecated:
            skipped_deprecated += 1
            continue
        url = source.get(URLS, {}).get(DIRECT_DOWNLOAD)
        if not url:
            continue
        scanned += 1

        signals = is_unstable(url)
        if args.weak and not signals:
            weak_signals = find_signals(url, WEAK_PATTERNS)
            if weak_signals:
                weak.append((source, url, weak_signals))
        if not signals:
            continue

        # A value that is already there was set by a human, whose judgement beats this
        # script. A hand-set "False" therefore suppresses a false positive permanently.
        if source.get(IS_PRODUCER_URL_UNSTABLE) is not None:
            already_set.append((source, url, signals))
            continue

        rules, matched = format_signals(signals)
        flagged.append(
            {
                "mdb_source_id": source.get(MDB_SOURCE_ID),
                "data_type": source.get(DATA_TYPE),
                "provider": source.get(PROVIDER),
                "status": status or "",
                "direct_download": url,
                "rules": rules,
                "matched_text": matched,
            }
        )
        if args.apply:
            flag_source(file_path, source)

    for row in flagged:
        print(f"{row['mdb_source_id']:>5}  {row['rules']:<40}  {row['matched_text']}")
        print(f"       {row['direct_download']}")

    print()
    print(f"Scanned {scanned} sources, skipped {skipped_deprecated} deprecated.")
    print(f"Unstable producer URLs: {len(flagged)}")

    counts = {}
    for row in flagged:
        for name in row["rules"].split("|"):
            counts[name] = counts.get(name, 0) + 1
    for name, count in sorted(counts.items(), key=lambda item: -item[1]):
        print(f"  {count:>4}  {name}")

    if already_set:
        print()
        print(f"Matched but left alone, the field is already set: {len(already_set)}")
        for source, url, _ in already_set:
            value = source.get(IS_PRODUCER_URL_UNSTABLE)
            print(f"  {source.get(MDB_SOURCE_ID):>5}  {value:<6}  {url}")

    if args.weak:
        print()
        print(f"Weak signals, never flagged, review by hand: {len(weak)}")
        for source, url, weak_signals in weak:
            rules, matched = format_signals(weak_signals)
            print(f"  {source.get(MDB_SOURCE_ID):>5}  {rules:<40}  {matched}")
            print(f"         {url}")

    if args.report:
        write_report(args.report, flagged)
        print()
        print(f"Report written to {args.report}")

    if args.apply:
        print()
        print(f"Wrote is_producer_url_unstable to {len(flagged)} files.")
    else:
        print()
        print("Dry run, nothing written. Pass --apply to write.")


if __name__ == "__main__":
    main()
