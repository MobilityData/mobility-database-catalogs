import importlib.util
import json
import os
from tempfile import TemporaryDirectory
from unittest import TestCase

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
MODULE_PATH = os.path.join(PROJECT_ROOT, "scripts", "catalog_reports.py")

# The scripts are standalone by design, so that they can run without the GDAL
# dependencies that tools.helpers pulls in. Load by path rather than turning scripts/
# into a package.
spec = importlib.util.spec_from_file_location("catalog_reports", MODULE_PATH)
catalog_reports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_reports)

# The exact row shape the unstable feed reports use: inline style attributes on every
# tag, a th header row, and the producer URL wrapped in an anchor.
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
</tbody></table></body></html>
"""

# A header row built out of td rather than th, which the parser has to recognise by the
# name of the first column.
HTML_REPORT_WITHOUT_TH = """
<table><tr><td>stable_id</td><td>final_decision</td></tr>
<tr><td>mdb-1067</td><td>true</td></tr></table>
"""


class TestToSourceId(TestCase):
    def test_strips_the_mdb_prefix(self):
        self.assertEqual(catalog_reports.to_source_id("mdb-1234"), 1234)

    def test_accepts_a_bare_number(self):
        self.assertEqual(catalog_reports.to_source_id(" 1234 "), 1234)

    def test_rejects_other_catalogs(self):
        for stable_id in (
            "tld-4253",
            "ntd-80010",
            "ntd-90164-2",
            "tfs-7",
            "tld-5509_1",
        ):
            with self.subTest(stable_id=stable_id):
                self.assertIsNone(catalog_reports.to_source_id(stable_id))


class TestIdPrefix(TestCase):
    def test_names_the_other_catalog(self):
        self.assertEqual(catalog_reports.id_prefix("ntd-90164-2"), "ntd")

    def test_falls_back_to_the_id_itself(self):
        self.assertEqual(catalog_reports.id_prefix("garbage"), "garbage")


class TestParseHtmlReport(TestCase):
    def setUp(self):
        self.rows = catalog_reports.parse_html_report(HTML_REPORT)

    def test_skips_the_header_row(self):
        self.assertEqual(len(self.rows), 2)
        self.assertNotIn("stable_id", [row["stable_id"] for row in self.rows])

    def test_reads_the_stable_id_column(self):
        self.assertEqual(
            [row["stable_id"] for row in self.rows], ["mdb-1260", "tld-4253"]
        )

    def test_keys_cells_by_column_heading(self):
        self.assertEqual(self.rows[0]["identifier"], "iso_date")
        self.assertEqual(self.rows[0]["matched_text"], "20200911")

    def test_gathers_cell_text_across_nested_tags(self):
        self.assertEqual(
            self.rows[0]["producer_url"],
            "200https://example.org/20200911/gtfs.zip",
        )

    def test_reads_a_header_row_that_used_td(self):
        rows = catalog_reports.parse_html_report(HTML_REPORT_WITHOUT_TH)
        self.assertEqual(rows, [{"stable_id": "mdb-1067", "final_decision": "true"}])


class TestParseCsvReport(TestCase):
    def test_reads_a_stable_id_column(self):
        rows = catalog_reports.parse_csv_report(
            "stable_id,final_decision\nmdb-1067,true\n"
        )
        self.assertEqual(rows, [{"stable_id": "mdb-1067", "final_decision": "true"}])

    def test_reads_the_mdb_source_id_column_the_scripts_write(self):
        rows = catalog_reports.parse_csv_report(
            "mdb_source_id,provider,rules\n561,LISERCO,iso_date\n"
        )
        self.assertEqual(rows[0]["stable_id"], "561")
        self.assertEqual(rows[0]["rules"], "iso_date")

    def test_normalises_column_headings(self):
        rows = catalog_reports.parse_csv_report(
            "Stable ID,Final Decision\nmdb-1,true\n"
        )
        self.assertEqual(rows[0]["final_decision"], "true")

    def test_skips_rows_without_an_id(self):
        rows = catalog_reports.parse_csv_report("stable_id\nmdb-561\n\n  \n")
        self.assertEqual(len(rows), 1)

    def test_handles_an_empty_file(self):
        self.assertEqual(catalog_reports.parse_csv_report(""), [])


class TestParsePlainReport(TestCase):
    def test_reads_one_id_per_line_and_skips_comments(self):
        rows = catalog_reports.parse_plain_report(
            "# feeds to flag\nmdb-561\n\n  mdb-1260  \n"
        )
        self.assertEqual([row["stable_id"] for row in rows], ["mdb-561", "mdb-1260"])


class TestParseReport(TestCase):
    def write(self, directory, name, text, encoding="utf-8"):
        path = os.path.join(directory, name)
        with open(path, "w", encoding=encoding) as fp:
            fp.write(text)
        return path

    def test_strips_a_byte_order_mark(self):
        # The query exports carry a BOM. Left in place it glues itself to the first
        # column heading, which hides the id column and yields no rows at all.
        with TemporaryDirectory() as directory:
            path = self.write(
                directory,
                "report.csv",
                "stable_id,final_decision\nmdb-1067,true\n",
                encoding="utf-8-sig",
            )
            rows = catalog_reports.parse_report(path)
        self.assertEqual(rows, [{"stable_id": "mdb-1067", "final_decision": "true"}])

    def test_dispatches_on_the_extension(self):
        with TemporaryDirectory() as directory:
            html = self.write(directory, "report.html", HTML_REPORT_WITHOUT_TH)
            plain = self.write(directory, "report.txt", "mdb-1067\n")
            self.assertEqual(
                catalog_reports.parse_report(html)[0]["final_decision"], "true"
            )
            self.assertEqual(
                catalog_reports.parse_report(plain)[0]["stable_id"], "mdb-1067"
            )

    def test_merges_reports_keeping_the_first_mention(self):
        with TemporaryDirectory() as directory:
            first = self.write(
                directory, "first.csv", "stable_id,final_decision\nmdb-561,true\n"
            )
            second = self.write(directory, "second.txt", "mdb-561\nmdb-1260\n")
            rows, total = catalog_reports.parse_reports([first, second])

        self.assertEqual(total, 3)
        by_id = {row["stable_id"]: row for row in rows}
        self.assertEqual(sorted(by_id), ["mdb-1260", "mdb-561"])
        self.assertEqual(by_id["mdb-561"]["final_decision"], "true")


class TestPlaceField(TestCase):
    def source(self):
        return {
            "mdb_source_id": 1,
            "provider": "Somewhere Transit",
            "status": "active",
            "urls": {},
        }

    def test_inserts_after_the_named_key(self):
        placed = catalog_reports.place_field(
            self.source(), "is_official", "True", after="provider"
        )
        self.assertEqual(
            list(placed),
            ["mdb_source_id", "provider", "is_official", "status", "urls"],
        )

    def test_appends_when_the_named_key_is_absent(self):
        placed = catalog_reports.place_field(
            self.source(), "is_official", "True", after="redirect"
        )
        self.assertEqual(list(placed)[-1], "is_official")

    def test_appends_when_no_key_is_named(self):
        placed = catalog_reports.place_field(
            self.source(), "is_producer_url_unstable", "True"
        )
        self.assertEqual(list(placed)[-1], "is_producer_url_unstable")

    def test_leaves_an_existing_field_where_it_is(self):
        source = self.source()
        source["is_official"] = "False"
        placed = catalog_reports.place_field(
            source, "is_official", "True", after="provider"
        )
        self.assertEqual(placed["is_official"], "True")
        self.assertEqual(list(placed), list(self.source()) + ["is_official"])


class TestWriteSource(TestCase):
    SOURCE = {
        "mdb_source_id": 561,
        "provider": "LISERCO",
        "urls": {"direct_download": "https://example.org/gtfs.zip"},
    }

    def roundtrip(self, ends_with_newline):
        with TemporaryDirectory() as directory:
            path = os.path.join(directory, "source.json")
            with open(path, "w") as fp:
                json.dump(self.SOURCE, fp, indent=4, ensure_ascii=False)
                if ends_with_newline:
                    fp.write("\n")

            catalog_reports.set_source_field(
                path, dict(self.SOURCE), "is_official", "True", after="provider"
            )
            with open(path) as fp:
                return fp.read()

    def test_keeps_a_trailing_newline(self):
        self.assertTrue(self.roundtrip(ends_with_newline=True).endswith("}\n"))

    def test_keeps_the_absence_of_a_trailing_newline(self):
        written = self.roundtrip(ends_with_newline=False)
        self.assertTrue(written.endswith("}"))
        self.assertFalse(written.endswith("\n"))

    def test_writes_four_space_indent_like_to_json(self):
        self.assertIn('\n    "provider": "LISERCO",', self.roundtrip(True))

    def test_writes_the_field_in_position(self):
        written = json.loads(self.roundtrip(True))
        self.assertEqual(list(written)[2], "is_official")
        self.assertEqual(written["is_official"], "True")
