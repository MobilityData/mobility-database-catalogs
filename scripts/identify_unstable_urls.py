# Flag feeds whose producer URL carries evidence of a date or a version with
# is_producer_url_unstable = "True".
#
# A producer URL containing a date or a rotating version number will stop resolving once
# the producer publishes again, so the feed needs manual attention more than twice a year.
# See the is_producer_url_unstable row of README.md for the field definition.
#
# There are two ways to pick the feeds to flag:
#
#   Consume a report. The identification has already happened elsewhere, and the report
#   names the feeds. This is the usual path, because the reports are produced against the
#   whole Mobility Database, whose feeds are not all in this catalog, and because the rule
#   table below is deliberately narrower than the one those reports were built with.
#
#     python scripts/identify_unstable_urls.py unstable_feeds.html --apply
#
#   Scan the catalog with the rule table, which is what --scan does. Useful for spotting
#   feeds that have drifted since the last report.
#
#     python scripts/identify_unstable_urls.py --scan --report unstable_urls.csv --weak
#
# Dry run by default in both modes. Nothing is written unless --apply is passed, and the
# field is only ever set to "True" -- feeds not named or not matched are left untouched.
#
# This script is intentionally standalone (standard library only). tools.helpers pulls in
# gtfs_kit, which needs GDAL, so scripts/ re-declares the handful of constants it needs
# instead of importing the tools package. Same convention as scripts/create_urls_matrix.py.
import argparse
import csv
import io
import json
import os
import re
from html.parser import HTMLParser
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

# Report input constants
STABLE_ID = "stable_id"
RULES = "rules"
MATCHED_TEXT = "matched_text"
# Only mdb- stable ids live in this catalog. A report covers the whole Mobility Database,
# so the other prefixes it carries are counted and skipped rather than treated as errors.
MDB_PREFIX = "mdb-"
HTML_EXTENSIONS = (".html", ".htm")
CSV_EXTENSIONS = (".csv",)

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
    ("version_query_parameter", re.compile(r"[?&]version=\d{4,}", re.IGNORECASE)),
    ("epoch_timestamp", re.compile(r"(?<!\d)1\d{9}(?:\.0)?(?!\d)")),
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
    text = scannable(url)
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
# REPORT INPUT
#########################


class ReportTableParser(HTMLParser):
    """
    Collects the cells of every table row in an HTML report.

    The reports carry inline style attributes on every tag and wrap the producer URL in an
    anchor, so the cell text has to be gathered across nested tags rather than read off a
    single data event. Header rows are dropped: a th cell marks the row as a header.

    Attributes:
        rows (list): One list of cell strings per body row, in document order.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None
        self._is_header_row = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
            self._is_header_row = False
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            if tag == "th":
                self._is_header_row = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row and not self._is_header_row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def report_row(stable_id, rules="", matched_text=""):
    """
    Builds one parsed report row.

    Args:
        stable_id (str): The feed's stable id, as the report spells it.
        rules (str, optional): The rules the report says fired. Defaults to empty.
        matched_text (str, optional): The text the report says matched. Defaults to empty.

    Returns:
        dict: The row, keyed by STABLE_ID, RULES and MATCHED_TEXT.
    """
    return {STABLE_ID: stable_id, RULES: rules, MATCHED_TEXT: matched_text}


def parse_html_report(text):
    """
    Reads the rows of an HTML report table.

    The column order is the one the reports use: stable id, producer URL, identifier,
    matched text. The identifier and matched text columns are carried through so the
    review CSV keeps the provenance of each flag instead of re-deriving it.

    Args:
        text (str): The contents of the HTML report.

    Returns:
        list: The parsed rows.
    """
    parser = ReportTableParser()
    parser.feed(text)
    parser.close()
    rows = []
    for cells in parser.rows:
        # A header row that used td rather than th still names its first column.
        if not cells[0] or cells[0] == STABLE_ID:
            continue
        rows.append(
            report_row(
                cells[0],
                cells[2] if len(cells) > 2 else "",
                cells[3] if len(cells) > 3 else "",
            )
        )
    return rows


def parse_csv_report(text):
    """
    Reads the rows of a CSV report.

    Accepts either a stable_id column or the mdb_source_id column this script's own
    --report writes, so a review CSV can be fed straight back in.

    Args:
        text (str): The contents of the CSV report.

    Returns:
        list: The parsed rows.
    """
    rows = []
    for record in csv.DictReader(io.StringIO(text)):
        stable_id = record.get(STABLE_ID) or record.get(MDB_SOURCE_ID) or ""
        if not stable_id.strip():
            continue
        rows.append(
            report_row(
                stable_id.strip(),
                (record.get(RULES) or "").strip(),
                (record.get(MATCHED_TEXT) or "").strip(),
            )
        )
    return rows


def parse_plain_report(text):
    """
    Reads a plain list of stable ids, one per line.

    Blank lines and lines starting with # are skipped, so a list can be commented.

    Args:
        text (str): The contents of the list.

    Returns:
        list: The parsed rows.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(report_row(line))
    return rows


def parse_report(path):
    """
    Reads one report, picking the parser from the file extension.

    Args:
        path (str): The path of the report to read.

    Returns:
        list: The parsed rows.
    """
    with open(path, encoding="utf-8") as fp:
        text = fp.read()
    extension = os.path.splitext(path)[1].lower()
    if extension in HTML_EXTENSIONS:
        return parse_html_report(text)
    if extension in CSV_EXTENSIONS:
        return parse_csv_report(text)
    return parse_plain_report(text)


def parse_reports(paths):
    """
    Reads every report and merges them on stable id.

    The first mention of a stable id wins, so a rerun that passes both an old and a new
    report keeps the earlier provenance rather than the later empty one.

    Args:
        paths (list): The paths of the reports to read.

    Returns:
        tuple: The merged rows and the total number of rows read before merging.
    """
    merged = {}
    total = 0
    for path in paths:
        for row in parse_report(path):
            total += 1
            merged.setdefault(row[STABLE_ID], row)
    return list(merged.values()), total


def to_source_id(stable_id):
    """
    Converts a stable id to the mdb_source_id this catalog keys on.

    Args:
        stable_id (str): A stable id, either mdb- prefixed or a bare number.

    Returns:
        int: The source id, or None when the id belongs to another catalog.
    """
    value = stable_id.strip()
    if value.startswith(MDB_PREFIX):
        value = value[len(MDB_PREFIX) :]
    try:
        return int(value)
    except ValueError:
        return None


def id_prefix(stable_id):
    """
    Names the catalog a skipped stable id belongs to, for the run summary.

    Args:
        stable_id (str): The stable id that could not be converted.

    Returns:
        str: The prefix ahead of the first dash, or the id itself when there is no dash.
    """
    return stable_id.split("-")[0] if "-" in stable_id else stable_id


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


def index_sources(data_type):
    """
    Reads every source file and keys them on mdb_source_id.

    Args:
        data_type (str): One of GTFS, GTFS_RT or ALL.

    Returns:
        dict: mdb_source_id mapped to its (file path, source dict) pair.
    """
    return {
        source.get(MDB_SOURCE_ID): (file_path, source)
        for file_path, source in load_sources(data_type)
    }


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
            'date or a version by setting is_producer_url_unstable to "True". Give one '
            "or more reports naming the feeds to flag, or --scan to identify them with "
            "the rule table instead."
        )
    )
    parser.add_argument(
        "reports",
        nargs="*",
        help=(
            "Reports naming the feeds to flag. An .html report table, a .csv with a "
            "stable_id or mdb_source_id column, or a file of stable ids one per line. "
            "Ids outside this catalog are counted and skipped."
        ),
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Identify feeds with the rule table instead of reading a report.",
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
        help='Write is_producer_url_unstable = "True" into the selected files.',
    )
    parser.add_argument(
        "--include-deprecated",
        action="store_true",
        help=(
            "Scan mode only. Also scan sources whose status is deprecated, which are "
            "skipped by default. A report is authoritative, so consuming one never "
            "filters on status."
        ),
    )
    parser.add_argument("--report", help="Path of the review CSV to write.")
    parser.add_argument(
        "--weak",
        action="store_true",
        help=(
            "Scan mode only. Also list the weak signals that are never flagged, for "
            "manual review."
        ),
    )
    args = parser.parse_args(argv)
    if args.scan and args.reports:
        parser.error("give reports to consume or --scan to identify, not both.")
    if not args.scan and not args.reports:
        parser.error("give at least one report to consume, or --scan to identify.")
    for option, name in (
        (args.include_deprecated, "--include-deprecated"),
        (args.weak, "--weak"),
    ):
        if option and not args.scan:
            parser.error(f"{name} only applies to --scan.")
    return args


def consume_reports(args):
    """
    Flags the feeds the given reports name.

    The report decides which feeds are unstable, so nothing here re-tests the URL and
    nothing filters on status. An id the catalog does not hold is reported rather than
    passed over, because it means the report and the catalog have drifted apart.

    Args:
        args (Namespace): The parsed command line arguments.

    Returns:
        list: The review rows for the feeds that were flagged.
    """
    rows, total = parse_reports(args.reports)
    sources = index_sources(args.data_type)

    flagged = []
    already_set = []
    unresolved = []
    skipped = {}

    for row in rows:
        stable_id = row[STABLE_ID]
        source_id = to_source_id(stable_id)
        if source_id is None:
            prefix = id_prefix(stable_id)
            skipped[prefix] = skipped.get(prefix, 0) + 1
            continue
        if source_id not in sources:
            unresolved.append(stable_id)
            continue

        file_path, source = sources[source_id]
        url = source.get(URLS, {}).get(DIRECT_DOWNLOAD, "")

        # A value that is already there was set by a human, whose judgement beats this
        # script. A hand-set "False" therefore suppresses a false positive permanently.
        if source.get(IS_PRODUCER_URL_UNSTABLE) is not None:
            already_set.append((source, url))
            continue

        flagged.append(
            {
                "mdb_source_id": source_id,
                "data_type": source.get(DATA_TYPE),
                "provider": source.get(PROVIDER),
                "status": source.get(STATUS) or "",
                "direct_download": url,
                "rules": row[RULES],
                "matched_text": row[MATCHED_TEXT],
            }
        )
        if args.apply:
            flag_source(file_path, source)

    flagged.sort(key=lambda row: row["mdb_source_id"])
    for row in flagged:
        print(f"{row['mdb_source_id']:>5}  {row['rules']:<40}  {row['matched_text']}")
        print(f"       {row['direct_download']}")

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
        print(f"Skipped {sum(skipped.values())} ids outside this catalog: {detail}.")
    print(f"Unstable producer URLs: {len(flagged)}")

    if already_set:
        print()
        print(f"Named but left alone, the field is already set: {len(already_set)}")
        for source, url in already_set:
            value = source.get(IS_PRODUCER_URL_UNSTABLE)
            print(f"  {source.get(MDB_SOURCE_ID):>5}  {value:<6}  {url}")

    if unresolved:
        print()
        print(
            f"Named but not in the catalog, the report has drifted: {len(unresolved)}"
        )
        for stable_id in unresolved:
            print(f"  {stable_id}")

    return flagged


def scan_catalog(args):
    """
    Flags the feeds whose producer URL the rule table matches.

    Args:
        args (Namespace): The parsed command line arguments.

    Returns:
        list: The review rows for the feeds that were flagged.
    """
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

    return flagged


def main(argv=None):
    args = parse_args(argv)

    flagged = scan_catalog(args) if args.scan else consume_reports(args)

    if args.report:
        write_report(args.report, flagged)
        print()
        print(f"Report written to {args.report}")

    print()
    if args.apply:
        print(f"Wrote is_producer_url_unstable to {len(flagged)} files.")
    else:
        print("Dry run, nothing written. Pass --apply to write.")


if __name__ == "__main__":
    main()
