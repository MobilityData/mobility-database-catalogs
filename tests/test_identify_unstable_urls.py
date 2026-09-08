import importlib.util
import json
import os
from tempfile import TemporaryDirectory
from unittest import TestCase

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "identify_unstable_urls.py")

# The script is standalone by design, so that it can run without the GDAL dependencies
# that tools.helpers pulls in. Load it by path rather than turning scripts/ into a package.
spec = importlib.util.spec_from_file_location("identify_unstable_urls", SCRIPT_PATH)
identify_unstable_urls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identify_unstable_urls)

is_unstable = identify_unstable_urls.is_unstable

# Producer URLs that carry a date or a version, paired with the rule that must fire.
# Every URL here is taken from the catalog.
UNSTABLE_URLS = [
    (
        "wordpress_upload_folder",
        "https://moosejaw.ca/wp-content/uploads/2023/11/moosejaw-GTFS.zip",
    ),
    (
        "wordpress_upload_folder",
        "https://www.metrofor.ce.gov.br/wp-content/uploads/sites/32/2025/01/gtfs_metrofor.zip",
    ),
    ("iso_date", "https://www.dtpm.cl/descargas/gtfs/GTFS_20260704.zip"),
    ("iso_date", "https://storage.googleapis.com/gtfs-estaticos/GTFS-2026-04-29.zip"),
    (
        "iso_date",
        "https://zdzit.olsztyn.eu/wp-content/uploads/2025/05/GTFS_2025_05_26.zip",
    ),
    ("iso_date", "https://mts.pt/imt/MTS-20240129.zip"),
    (
        "iso_date",
        "https://transport-data-gouv-fr-resource-history-prod.cellar-c2.services."
        "clever-cloud.com/80742/80742.20241107.160916.535554.zip",
    ),
    # A date carrying a time. The trailing time must not defeat the rule.
    (
        "iso_date",
        "https://www.mvv-muenchen.de/fileadmin/mediapool/02-Fahrplanauskunft/"
        "03-Downloads/openData/mvv_ohneShape_20241004095702.zip",
    ),
    (
        "year_month",
        "https://dados.fortaleza.ce.gov.br/dataset/51afc610-d48b-4fa8-8dea-9c65747148c7/"
        "resource/51e3d494-3b41-4328-a971-964e2cdd8a22/download/gtff-202311.zip",
    ),
    (
        "locale_date",
        "https://datos.jalisco.gob.mx/sites/default/files/"
        "rutas_mitransporte_puertovallarta_03.12.2021.zip",
    ),
    (
        "locale_date",
        "https://www.circumetnea.it/download/"
        "general-transit-feed-specification-fce-01-02-2025-28-02-2028/?wpdmdl=17798",
    ),
    (
        "dated_version_tag",
        "https://github.com/aruneko/DonanbusGTFS/archive/refs/tags/2020.0401.1.zip",
    ),
    (
        "delimited_year",
        "https://static.oebb.at/open-data/soll-fahrplan-gtfs/GTFS_OP_2024_obb.zip",
    ),
    ("delimited_year", "https://www.santaeulaliaferry.com/gtfs_feed_2025.zip"),
    (
        "delimited_year",
        "https://data.opentransportdata.swiss/dataset/timetable-2026-gtfs2020/permalink",
    ),
    ("delimited_year", "https://maxtransit.org/GTFS/2026/google_transit_Working.zip"),
    (
        "labelled_year",
        "https://opendata.hamilton.ca/GTFS-Static/2025Winter_GTFSStatic.zip",
    ),
    (
        "labelled_year",
        "http://go-rts.com/wp-content/uploads/2025/01/RTSGTFS_Spring2025.zip",
    ),
    (
        "labelled_year",
        "https://www.fredericksburgva.gov/DocumentCenter/View/31122/FXBGO-GTFS---CY2026",
    ),
    (
        "labelled_year",
        "https://www.fredericksburgva.gov/DocumentCenter/View/28958/FXBGO-GTFS-Q1-CY2025",
    ),
    (
        "month_name",
        "https://data.opencity.in/dataset/88e2d145-7ec6-4666-88dd-6cf18b18312e/resource/"
        "1b0d18bb-b2fb-4a79-8ed0-1e071da5790c/download/"
        "telangana_opendata_gtfs_tgsrtc_08_february_2026.zip",
    ),
    (
        "month_name",
        "https://dfef8f.p3cdn2.secureserver.net/wp-content/uploads/2023/08/"
        "RMTD_GTFS_AUGUST_2023.zip",
    ),
    ("month_name", "https://www.dtpm.cl/descargas/gtfs/03%20GTFS_Final_03marzo.zip"),
    (
        "month_abbreviation_with_digits",
        "http://datos.gob.cl/dataset/c77c9a50-6dd1-449d-b5ab-947ec0139b31/resource/"
        "a4edcf07-0657-456d-bbbc-54b2aec1de8d/download/coquimbo10feb16.zip",
    ),
    (
        "month_abbreviation_with_digits",
        "http://datos.gob.cl/dataset/cef4c471-2837-412b-a78e-1d4c6a261bf9/resource/"
        "7887a7e7-9af6-4fc8-b19f-8ff4ea474d1c/download/temuco24nov16.zip",
    ),
    # gateway.carris.pt really did move from v2.8 to v2.11,
    (
        "version_query_parameter",
        "https://solweb.tper.it/web/tools/open-data/open-data-download.aspx?"
        "source=solweb.tper.it&filename=gommagtfsbo&version=20260122&format=zip",
    ),
    (
        "epoch_timestamp",
        "https://www.wroclaw.pl/open-data/87b09b32-f076-4475-8ec9-6020ed1f9ac0/"
        "1513602900.0_OtwartyWroclaw_rozklad_jazdy_GTFS.zip",
    ),
]

# Producer URLs whose digits look like a date or a version but never change. Every URL
# here is taken from the catalog, and each one stands for a whole cluster of feeds.
STABLE_URLS = [
    # Digits in the hostname, not the path.
    "https://www3.septa.org/developer/google_bus.zip",
    "http://apps2.saskatoon.ca/app/data/google_transit.zip",
    # A raw IPv4 host reads as a version number.
    "http://70.34.208.164/gtfs.zip",
    "http://193.23.225.211:8002/export-gtfs-static",
    # An explicit port reads as a year.
    "https://cat.cadavl.com:4431/CAT/GTFS/GTFS_CAT.zip",
    # The v2 is the GTFS-Flex spec version, not the feed's.
    "https://data.trilliumtransit.com/gtfs/tracy-ca-us/tracy-ca-us--flex-v2.zip",
    "https://data.trilliumtransit.com/gtfs/pueblo-co-us/pueblo-co-us--flex-v2.zip",
    # Stable API version paths.
    "https://api.transport.nsw.gov.au/v2/gtfs/alerts/all",
    "https://transport.api.act.gov.au/gtfs/data/gtfs/v2/gtfs.zip",
    "https://gitlab.com/api/v4/projects/vekejsn%2Fgtfs-generators/packages/generic/"
    "nis-gtfs/latest/nis_gtfs.zip",
    # A bare API version path segment.
    "https://data.waltti.fi/tampere/api/gtfsrealtime/v1.0/feed/tripupdate",
    "https://stibmivb.opendatasoft.com/api/datasets/1.0/gtfs-files-production/"
    "alternative_exports/gtfszip/",
    # The numeric TransitFeeds feed key.
    "https://transitfeeds.com/p/rodoviaria-de-lisboa/998/latest/download",
    # A permanent ArcGIS item id.
    "https://www.arcgis.com/sharing/rest/content/items/"
    "1a25440bf66f499bae2657ec7fb40144/data",
    # A 40 hex character Mecatran credential.
    "https://app.mecatran.com/utw/ws/gtfsfeed/static/lio"
    "?apiKey=2b160d626f783808095373766f18714901325e45&type=gtfs_lio",
    # A Google Drive file id.
    "https://drive.usercontent.google.com/uc"
    "?id=1l8BUIOaNZiu7hbO1UxMB1e9EaXm5s4Wa&export=download",
    # Place and agency names that collide with month and season words.
    "http://data.trilliumtransit.com/gtfs/winterpark-co-us/winterpark-co-us.zip",
    "https://data.trilliumtransit.com/gtfs/cedarfalls-ia-us/cedarfalls-ia-us.zip",
    "http://data.trilliumtransit.com/gtfs/centralmarylandrta-md-us/"
    "centralmarylandrta-md-us.zip",
    "https://s3.amazonaws.com/datatools-511ny/public/"
    "Greater_Glens_Falls_Transit_System.zip",
    # Stable numeric ids that contain a year-like run.
    "https://addtransit.com/gtfsfile/42017/TheVictoriaClipper.zip",
    "https://www.tib.org/documents/20124/478141/ctm-mallorca-es.zip",
    # A plain producer URL with nothing rotating in it.
    "http://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip",
    # The MobilityData mirror template, which the script never scans but must not match.
    "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/"
    "at-wien-wiener-lokalbahnen-wlb-gtfs-648.zip?alt=media",
]


class TestIsUnstable(TestCase):
    def test_flags_dates_and_versions(self):
        for expected_rule, url in UNSTABLE_URLS:
            with self.subTest(url=url):
                rules = [rule for rule, _ in is_unstable(url)]
                self.assertTrue(rules, f"expected {url} to be flagged")
                self.assertIn(expected_rule, rules)

    def test_leaves_stable_urls_alone(self):
        for url in STABLE_URLS:
            with self.subTest(url=url):
                self.assertEqual(is_unstable(url), [], f"expected {url} to be stable")


class TestScannable(TestCase):
    def test_drops_scheme_and_host(self):
        under_test = identify_unstable_urls.scannable(
            "https://www3.septa.org:8443/developer/google_bus.zip?a=b#c"
        )
        self.assertEqual(under_test, "/developer/google_bus.zip?a=b#c")

    def test_decodes_percent_encoding(self):
        under_test = identify_unstable_urls.scannable(
            "https://www.dtpm.cl/descargas/gtfs/03%20GTFS_Final_03marzo.zip"
        )
        self.assertIn("03 GTFS_Final_03marzo.zip", under_test)


# The exact row shape the reports use: inline style attributes on every tag, a th header
# row, and the producer URL wrapped in an anchor.
HTML_REPORT = """
<html><body><table><tbody>
<tr><th style="padding:8px">stable_id</th><th style="padding:8px">producer_url</th>
    <th style="padding:8px">identifier</th><th style="padding:8px">matched_text</th></tr>
<tr><td style="padding:8px; white-space:nowrap;">  mdb-1260  </td>
    <td style="padding:8px">200<a href="https://example.org/20200911/gtfs.zip"
        style="color:#3959FA" target="_blank">https://example.org/20200911/gtfs.zip</a></td>
    <td style="padding:8px">iso_date</td>
    <td style="padding:8px">20200911</td></tr>
<tr><td style="padding:8px">tld-4253</td>
    <td style="padding:8px">200https://example.org/RMTDGTFS4.4.25update.zip</td>
    <td style="padding:8px">locale_date</td>
    <td style="padding:8px">4.4.25</td></tr>
<tr><td style="padding:8px">ntd-80010</td>
    <td style="padding:8px">404https://example.org/wp-content/uploads/2022/10/a.zip</td>
    <td style="padding:8px">wordpress_upload_folder|delimited_year</td>
    <td style="padding:8px">wp-content/uploads/2022/10/|2022</td></tr>
</tbody></table></body></html>
"""


class TestToSourceId(TestCase):
    def test_strips_the_mdb_prefix(self):
        self.assertEqual(identify_unstable_urls.to_source_id("mdb-1234"), 1234)

    def test_accepts_a_bare_number(self):
        self.assertEqual(identify_unstable_urls.to_source_id(" 1234 "), 1234)

    def test_rejects_other_catalogs(self):
        for stable_id in ("tld-4253", "ntd-80010", "ntd-90164-2", "tfs-7", "tdg-1"):
            with self.subTest(stable_id=stable_id):
                self.assertIsNone(identify_unstable_urls.to_source_id(stable_id))


class TestParseHtmlReport(TestCase):
    def setUp(self):
        self.rows = identify_unstable_urls.parse_html_report(HTML_REPORT)

    def test_skips_the_header_row(self):
        self.assertEqual(len(self.rows), 3)
        self.assertNotIn("stable_id", [row["stable_id"] for row in self.rows])

    def test_reads_the_stable_id_column(self):
        self.assertEqual(
            [row["stable_id"] for row in self.rows],
            ["mdb-1260", "tld-4253", "ntd-80010"],
        )

    def test_carries_the_provenance_columns(self):
        self.assertEqual(self.rows[0]["rules"], "iso_date")
        self.assertEqual(self.rows[0]["matched_text"], "20200911")
        self.assertEqual(
            self.rows[2]["rules"], "wordpress_upload_folder|delimited_year"
        )


class TestParseCsvReport(TestCase):
    def test_reads_a_stable_id_column(self):
        rows = identify_unstable_urls.parse_csv_report(
            "stable_id,rules,matched_text\nmdb-561,iso_date,20160210\n"
        )
        self.assertEqual(
            rows,
            [{"stable_id": "mdb-561", "rules": "iso_date", "matched_text": "20160210"}],
        )

    def test_reads_the_mdb_source_id_column_this_script_writes(self):
        rows = identify_unstable_urls.parse_csv_report(
            "mdb_source_id,provider,rules,matched_text\n561,LISERCO,iso_date,20160210\n"
        )
        self.assertEqual(rows[0]["stable_id"], "561")
        self.assertEqual(rows[0]["rules"], "iso_date")

    def test_skips_rows_without_an_id(self):
        rows = identify_unstable_urls.parse_csv_report("stable_id\nmdb-561\n\n  \n")
        self.assertEqual(len(rows), 1)


class TestParsePlainReport(TestCase):
    def test_reads_one_id_per_line_and_skips_comments(self):
        rows = identify_unstable_urls.parse_plain_report(
            "# feeds to flag\nmdb-561\n\n  mdb-1260  \n"
        )
        self.assertEqual([row["stable_id"] for row in rows], ["mdb-561", "mdb-1260"])


class TestParseReports(TestCase):
    def test_merges_on_stable_id_keeping_the_first_mention(self):
        with TemporaryDirectory() as directory:
            first = os.path.join(directory, "first.csv")
            second = os.path.join(directory, "second.txt")
            with open(first, "w") as fp:
                fp.write("stable_id,rules\nmdb-561,iso_date\n")
            with open(second, "w") as fp:
                fp.write("mdb-561\nmdb-1260\n")

            rows, total = identify_unstable_urls.parse_reports([first, second])

        self.assertEqual(total, 3)
        by_id = {row["stable_id"]: row for row in rows}
        self.assertEqual(sorted(by_id), ["mdb-1260", "mdb-561"])
        self.assertEqual(by_id["mdb-561"]["rules"], "iso_date")


class TestFlagSource(TestCase):
    SOURCE = {
        "mdb_source_id": 561,
        "data_type": "gtfs",
        "urls": {"direct_download": "https://example.org/gtfs.zip"},
    }

    def flag(self, ends_with_newline):
        with TemporaryDirectory() as directory:
            path = os.path.join(directory, "source.json")
            with open(path, "w") as fp:
                json.dump(self.SOURCE, fp, indent=4, ensure_ascii=False)
                if ends_with_newline:
                    fp.write("\n")

            source = dict(self.SOURCE)
            identify_unstable_urls.flag_source(path, source)
            with open(path) as fp:
                return fp.read()

    def test_appends_the_field_as_the_last_key(self):
        written = json.loads(self.flag(ends_with_newline=False))
        self.assertEqual(written["is_producer_url_unstable"], "True")
        self.assertEqual(list(written)[-1], "is_producer_url_unstable")

    def test_keeps_a_trailing_newline(self):
        self.assertTrue(self.flag(ends_with_newline=True).endswith("}\n"))

    def test_keeps_the_absence_of_a_trailing_newline(self):
        self.assertTrue(self.flag(ends_with_newline=False).endswith("}"))
        self.assertFalse(self.flag(ends_with_newline=False).endswith("\n"))
