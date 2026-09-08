import importlib.util
import os
from unittest import TestCase

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "mark_official_feeds.py")

# The script is standalone by design, so that it can run without the GDAL dependencies
# that tools.helpers pulls in. Load it by path rather than turning scripts/ into a
# package. It puts its own directory on sys.path to find catalog_reports.
spec = importlib.util.spec_from_file_location("mark_official_feeds", SCRIPT_PATH)
mark_official_feeds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mark_official_feeds)

read_decision = mark_official_feeds.read_decision


class TestReadDecision(TestCase):
    def test_maps_true_to_the_string_true(self):
        # The field is a string enum in the schema, not a JSON boolean.
        self.assertEqual(read_decision({"final_decision": "true"}), ("true", "True"))

    def test_maps_false_to_the_string_false(self):
        self.assertEqual(read_decision({"final_decision": "false"}), ("false", "False"))

    def test_ignores_case_and_surrounding_space(self):
        for raw in ("TRUE", " True ", "tRuE"):
            with self.subTest(raw=raw):
                self.assertEqual(read_decision({"final_decision": raw})[1], "True")

    def test_accepts_the_is_official_column_the_script_writes(self):
        self.assertEqual(read_decision({"is_official": "False"})[1], "False")

    def test_prefers_final_decision_over_is_official(self):
        row = {"final_decision": "true", "is_official": "False"}
        self.assertEqual(read_decision(row)[1], "True")

    def test_reports_a_verdict_it_does_not_understand(self):
        raw, value = read_decision({"final_decision": "maybe"})
        self.assertEqual(raw, "maybe")
        self.assertIsNone(value)

    def test_reports_a_missing_verdict(self):
        for row in ({}, {"final_decision": ""}, {"final_decision": "   "}):
            with self.subTest(row=row):
                self.assertEqual(read_decision(row), ("", None))


class TestParseArgs(TestCase):
    def test_requires_a_report(self):
        with self.assertRaises(SystemExit):
            mark_official_feeds.parse_args([])

    def test_defaults_to_a_dry_run_over_the_whole_catalog(self):
        args = mark_official_feeds.parse_args(["report.csv"])
        self.assertEqual(args.reports, ["report.csv"])
        self.assertFalse(args.apply)
        self.assertEqual(args.data_type, "all")
