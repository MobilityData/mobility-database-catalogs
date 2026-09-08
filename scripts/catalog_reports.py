# Shared plumbing for the scripts that mark catalog sources from a report.
#
# A report names the feeds to act on. It is produced elsewhere -- usually by a query
# against the whole Mobility Database, which holds feeds this catalog does not -- so
# these helpers read the rows, translate stable ids into the mdb_source_id this catalog
# keys on, and write a single field back into a source file without disturbing the rest.
#
# Standard library only, on purpose. tools.helpers pulls in gtfs_kit, which needs GDAL,
# so scripts/ re-declares the handful of constants it needs instead of importing the
# tools package. Same convention as scripts/create_urls_matrix.py.
import csv
import io
import json
import os
from html.parser import HTMLParser

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
IS_OFFICIAL = "is_official"
IS_PRODUCER_URL_UNSTABLE = "is_producer_url_unstable"

# Field constants
TRUE = "True"
FALSE = "False"
DEPRECATED = "deprecated"

# Report constants
STABLE_ID = "stable_id"
# Only mdb- stable ids live in this catalog. A report covers the whole Mobility Database,
# so the other prefixes it carries are counted and skipped rather than treated as errors.
MDB_PREFIX = "mdb-"
HTML_EXTENSIONS = (".html", ".htm")
CSV_EXTENSIONS = (".csv",)


#########################
# REPORT INPUT
#########################


class ReportTableParser(HTMLParser):
    """
    Collects the header and body rows of the first table in an HTML report.

    The reports carry inline style attributes on every tag and wrap the producer URL in an
    anchor, so cell text has to be gathered across nested tags rather than read off a
    single data event. A row of th cells is taken as the header.

    Attributes:
        header (list): The header cell strings, empty when the table has no th row.
        rows (list): One list of cell strings per body row, in document order.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.header = []
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
            if self._row:
                if self._is_header_row and not self.header:
                    self.header = self._row
                elif not self._is_header_row:
                    self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def column_name(value, index):
    """
    Normalises a report column heading into a key.

    Args:
        value (str): The heading as the report spells it.
        index (int): The column's position, used when the heading is blank.

    Returns:
        str: The lower case, underscore separated key.
    """
    key = "_".join(value.strip().lower().split())
    return key or f"column_{index}"


def build_row(header, cells):
    """
    Pairs a row's cells with the column names, and resolves its stable id.

    A report written by this repo names the column mdb_source_id rather than stable_id, so
    either is accepted and the result always carries STABLE_ID.

    Args:
        header (list): The column names.
        cells (list): The row's cell strings.

    Returns:
        dict: The row, keyed by column name, with STABLE_ID filled in.
    """
    row = {
        name: cells[index] for index, name in enumerate(header) if index < len(cells)
    }
    stable_id = row.get(STABLE_ID) or row.get(MDB_SOURCE_ID) or ""
    row[STABLE_ID] = stable_id.strip()
    return row


def parse_html_report(text):
    """
    Reads the rows of an HTML report table.

    Args:
        text (str): The contents of the HTML report.

    Returns:
        list: The parsed rows, keyed by column name.
    """
    parser = ReportTableParser()
    parser.feed(text)
    parser.close()

    body = parser.rows
    header = parser.header
    if not header:
        # A report whose header row used td rather than th. Its first cell still names
        # the id column, which is how it is told apart from a body row.
        if (
            body
            and body[0]
            and body[0][0].strip().lower() in (STABLE_ID, MDB_SOURCE_ID)
        ):
            header, body = body[0], body[1:]
        else:
            return []
    header = [column_name(value, index) for index, value in enumerate(header)]

    rows = []
    for cells in body:
        row = build_row(header, cells)
        if row[STABLE_ID]:
            rows.append(row)
    return rows


def parse_csv_report(text):
    """
    Reads the rows of a CSV report.

    Args:
        text (str): The contents of the CSV report, byte order mark already stripped.

    Returns:
        list: The parsed rows, keyed by column name.
    """
    reader = csv.reader(io.StringIO(text))
    try:
        header = [column_name(value, index) for index, value in enumerate(next(reader))]
    except StopIteration:
        return []

    rows = []
    for cells in reader:
        row = build_row(header, cells)
        if row[STABLE_ID]:
            rows.append(row)
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
        rows.append({STABLE_ID: line})
    return rows


def parse_report(path):
    """
    Reads one report, picking the parser from the file extension.

    Read as utf-8-sig, because the query exports come with a byte order mark and it would
    otherwise end up glued to the first column name, hiding the id column entirely.

    Args:
        path (str): The path of the report to read.

    Returns:
        list: The parsed rows.
    """
    with io.open(path, encoding="utf-8-sig") as fp:
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
    report keeps the earlier row rather than a later, emptier one.

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
    Lists the catalog directories to read for the given data type.

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


def place_field(source, field, value, after=None):
    """
    Returns the source with the field set, positioned to match the catalog.

    A field already present keeps the position it has, so re-running never shuffles a
    file. A new field goes straight after the named key when there is one, because that
    is where the catalog carries it; with no such key it is appended, which leaves the
    existing key order alone and holds the diff to the added line.

    Args:
        source (dict): The parsed source.
        field (str): The field to set.
        value (str): The value to write.
        after (str, optional): The key the new field belongs after. Defaults to None,
            meaning append.

    Returns:
        dict: The source to write. The argument is returned itself where it can be.
    """
    if field in source:
        source[field] = value
        return source
    if after is None or after not in source:
        source[field] = value
        return source

    placed = {}
    for key, existing in source.items():
        placed[key] = existing
        if key == after:
            placed[field] = value
    return placed


def write_source(file_path, source):
    """
    Writes a source back to its file.

    The dump matches tools.helpers.to_json: four space indent and non-ASCII preserved.
    Whether the file ends in a newline is carried over from the file itself, because the
    catalog is split on that point and rewriting it either way would only add noise.

    Args:
        file_path (str): The path of the source file to rewrite.
        source (dict): The source to write.

    Returns:
        None
    """
    with open(file_path) as fp:
        ends_with_newline = fp.read().endswith("\n")
    with open(file_path, "w") as fp:
        json.dump(source, fp, indent=4, ensure_ascii=False)
        if ends_with_newline:
            fp.write("\n")


def set_source_field(file_path, source, field, value, after=None):
    """
    Sets one field on a source and writes the file.

    Args:
        file_path (str): The path of the source file to rewrite.
        source (dict): The parsed source.
        field (str): The field to set.
        value (str): The value to write.
        after (str, optional): The key a new field belongs after. Defaults to None.

    Returns:
        dict: The source that was written.
    """
    source = place_field(source, field, value, after)
    write_source(file_path, source)
    return source


#########################
# REPORTING
#########################


def write_report(path, columns, rows):
    """
    Writes a review report.

    Args:
        path (str): The path of the CSV file to write.
        columns (list): The column names, in order.
        rows (list): The report rows, as dicts keyed by those column names.

    Returns:
        None
    """
    with open(path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
