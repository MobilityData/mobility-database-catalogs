from unittest import TestCase, skip
from unittest.mock import patch, Mock
from mobility_catalogs.tools.helpers import *
import pandas as pd


class TestVerificationFunctions(TestCase):
    def setUp(self):
        self.test_url = "some_url"

    def test_are_overlapping_crossing_edges(self):
        test_source_minimum = 45.000000
        test_source_maximum = 46.000000
        test_filter_minimum = 45.500000
        test_filter_maximum = 46.500000

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertTrue(under_test)

    def test_are_overlapping_included_edges(self):
        test_source_minimum = 45.000000
        test_source_maximum = 46.000000
        test_filter_minimum = 45.250000
        test_filter_maximum = 45.750000

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertTrue(under_test)

        test_source_minimum = 45.250000
        test_source_maximum = 45.750000
        test_filter_minimum = 45.000000
        test_filter_maximum = 46.000000

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertTrue(under_test)

    def test_are_not_overlapping_touching_edges(self):
        test_source_minimum = 45.000000
        test_source_maximum = 45.500000
        test_filter_minimum = 45.500000
        test_filter_maximum = 46.000000

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertFalse(under_test)

        test_source_minimum = 45.500000
        test_source_maximum = 46.000000
        test_filter_minimum = 45.000000
        test_filter_maximum = 45.500000

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertFalse(under_test)

    def test_are_not_overlapping_edges(self):
        test_source_minimum = 44.000000
        test_source_maximum = 45.000000
        test_filter_minimum = 46.000000
        test_filter_maximum = 47.500000

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertFalse(under_test)

    def test_are_not_overlapping_none_edges(self):
        test_source_minimum = None
        test_source_maximum = None
        test_filter_minimum = None
        test_filter_maximum = None

        under_test = are_overlapping_edges(
            source_minimum=test_source_minimum,
            source_maximum=test_source_maximum,
            filter_minimum=test_filter_minimum,
            filter_maximum=test_filter_maximum,
        )
        self.assertFalse(under_test)

    @patch("mobility_catalogs.tools.helpers.are_overlapping_edges")
    def test_are_overlapping_boxes(self, mock_edges):
        test_source_minimum_latitude = Mock()
        test_source_maximum_latitude = Mock()
        test_source_minimum_longitude = Mock()
        test_source_maximum_longitude = Mock()
        test_filter_minimum_latitude = Mock()
        test_filter_maximum_latitude = Mock()
        test_filter_minimum_longitude = Mock()
        test_filter_maximum_longitude = Mock()

        mock_edges.side_effect = [True, True]
        under_test = are_overlapping_boxes(
            source_minimum_latitude=test_source_minimum_latitude,
            source_maximum_latitude=test_source_maximum_latitude,
            source_minimum_longitude=test_source_minimum_longitude,
            source_maximum_longitude=test_source_maximum_longitude,
            filter_minimum_latitude=test_filter_minimum_latitude,
            filter_maximum_latitude=test_filter_maximum_latitude,
            filter_minimum_longitude=test_filter_minimum_longitude,
            filter_maximum_longitude=test_filter_maximum_longitude,
        )
        self.assertTrue(under_test)

        mock_edges.side_effect = [True, False]
        under_test = are_overlapping_boxes(
            source_minimum_latitude=test_source_minimum_latitude,
            source_maximum_latitude=test_source_maximum_latitude,
            source_minimum_longitude=test_source_minimum_longitude,
            source_maximum_longitude=test_source_maximum_longitude,
            filter_minimum_latitude=test_filter_minimum_latitude,
            filter_maximum_latitude=test_filter_maximum_latitude,
            filter_minimum_longitude=test_filter_minimum_longitude,
            filter_maximum_longitude=test_filter_maximum_longitude,
        )
        self.assertFalse(under_test)

        mock_edges.side_effect = [False, True]
        under_test = are_overlapping_boxes(
            source_minimum_latitude=test_source_minimum_latitude,
            source_maximum_latitude=test_source_maximum_latitude,
            source_minimum_longitude=test_source_minimum_longitude,
            source_maximum_longitude=test_source_maximum_longitude,
            filter_minimum_latitude=test_filter_minimum_latitude,
            filter_maximum_latitude=test_filter_maximum_latitude,
            filter_minimum_longitude=test_filter_minimum_longitude,
            filter_maximum_longitude=test_filter_maximum_longitude,
        )
        self.assertFalse(under_test)

        mock_edges.side_effect = [False, False]
        under_test = are_overlapping_boxes(
            source_minimum_latitude=test_source_minimum_latitude,
            source_maximum_latitude=test_source_maximum_latitude,
            source_minimum_longitude=test_source_minimum_longitude,
            source_maximum_longitude=test_source_maximum_longitude,
            filter_minimum_latitude=test_filter_minimum_latitude,
            filter_maximum_latitude=test_filter_maximum_latitude,
            filter_minimum_longitude=test_filter_minimum_longitude,
            filter_maximum_longitude=test_filter_maximum_longitude,
        )
        self.assertFalse(under_test)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_is_not_readable(self, mock_load_func):
        mock_load_func.side_effect = Mock(side_effect=TypeError())
        self.assertRaises(
            Exception, is_readable, url=self.test_url, load_func=mock_load_func
        )

        mock_load_func.side_effect = Mock(side_effect=MissingSchema())
        self.assertRaises(
            Exception, is_readable, url=self.test_url, load_func=mock_load_func
        )

        mock_load_func.side_effect = Mock(side_effect=ParserError())
        self.assertRaises(
            Exception, is_readable, url=self.test_url, load_func=mock_load_func
        )

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_is_readable(self, mock_load_func):
        mock_load_func.side_effect = "some_dataset"
        under_test = is_readable(url=self.test_url, load_func=mock_load_func)
        self.assertTrue(under_test)


class TestCreationFunctions(TestCase):
    def test_identify_source(self):
        test_name = "Some Name"
        test_country_code = "CA"
        test_data_type = "gtfs"
        test_mdb_source_id = "mdb-src-gtfs-some-name-ca"
        under_test = identify_source(
            name=test_name, country_code=test_country_code, data_type=test_data_type
        )
        self.assertEqual(under_test, test_mdb_source_id)

    def test_create_latest_url(self):
        test_mdb_source_id = "mdb-src-gtfs-some-name-ca"
        test_extension = "zip"
        test_latest_url = "https://storage.googleapis.com/storage/v1/b/archives_latest/o/mdb-src-gtfs-some-name-ca.zip?alt=media"
        under_test = create_latest_url(
            mdb_source_id=test_mdb_source_id, extension=test_extension
        )
        self.assertEqual(under_test, test_latest_url)


class TestGtfsSpecificFunctions(TestCase):
    def setUp(self):
        self.test_url = "some_url"

    @patch("mobility_catalogs.tools.helpers.gtfs_kit.read_feed")
    def test_not_loading_gtfs(self, mock_gtfs_kit):
        mock_gtfs_kit.side_effect = Mock(side_effect=TypeError())
        self.assertRaises(
            TypeError,
            load_gtfs,
            url=self.test_url,
        )

        mock_gtfs_kit.side_effect = Mock(side_effect=MissingSchema())
        self.assertRaises(
            MissingSchema,
            load_gtfs,
            url=self.test_url,
        )

        mock_gtfs_kit.side_effect = Mock(side_effect=ParserError())
        self.assertRaises(
            ParserError,
            load_gtfs,
            url=self.test_url,
        )

    @patch("mobility_catalogs.tools.helpers.gtfs_kit.read_feed")
    def test_loading_gtfs(self, mock_gtfs_kit):
        test_dataset = "some_gtfs_dataset"
        mock_gtfs_kit.return_value = test_dataset
        under_test = load_gtfs(url=self.test_url)
        self.assertEqual(under_test, test_dataset)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_none_stops(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = None
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(url=self.test_url)
        self.assertEqual(under_test, test_bounding_box)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_empty_dataframe(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame()
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(url=self.test_url)
        self.assertEqual(under_test, test_bounding_box)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_missing_columns(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame({"some_column": []})
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(url=self.test_url)
        self.assertEqual(under_test, test_bounding_box)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_empty_columns(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame({STOP_LAT: [], STOP_LON: []})
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(url=self.test_url)
        self.assertEqual(under_test, test_bounding_box)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_nan_values(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame({STOP_LAT: [pd.NA], STOP_LON: [pd.NA]})
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(url=self.test_url)
        self.assertEqual(under_test, test_bounding_box)

    @patch("mobility_catalogs.tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_stops_present(self, mock_load_gtfs):
        test_bounding_box = (44.00000, 45.000000, -110.000000, -109.000000)

        test_stops = pd.DataFrame(
            {
                STOP_LAT: [44.000000, 45.000000, pd.NA],
                STOP_LON: [-110.000000, -109.000000, pd.NA],
            }
        )
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(url=self.test_url)
        self.assertEqual(under_test, test_bounding_box)


class TestInOutFunctions(TestCase):
    def setUp(self):
        self.test_path = "some_path"
        self.test_obj = {"some_key": "some_value"}

    @patch("mobility_catalogs.tools.helpers.open")
    @patch("mobility_catalogs.tools.helpers.json.dump")
    def test_to_json(self, mock_json, mock_open):
        under_test = to_json(path=self.test_path, obj=self.test_obj)
        self.assertIsNone(under_test)
        mock_open.assert_called_once()
        mock_json.assert_called_once()

    @patch("mobility_catalogs.tools.helpers.open")
    @patch("mobility_catalogs.tools.helpers.json.load")
    def test_from_json(self, mock_json, mock_open):
        mock_json.return_value = self.test_obj
        under_test = from_json(path=self.test_path)
        self.assertEqual(under_test, self.test_obj)
        mock_open.assert_called_once()
        mock_json.assert_called_once()

    @patch("mobility_catalogs.tools.helpers.os.walk")
    @patch("mobility_catalogs.tools.helpers.os.path.join")
    @patch("mobility_catalogs.tools.helpers.open")
    @patch("mobility_catalogs.tools.helpers.json.load")
    def test_aggregate(self, mock_json, mock_open, mock_path, mock_walk):
        mock_walk.return_value = [
            ("/catalogs", ("static",), ()),
            ("/catalogs/static", ("gtfs",), ()),
            ("/catalogs/static/gtfs", (), ("some_source.json", "another_source.json")),
        ]
        mock_json.return_value = self.test_obj
        under_test = aggregate(catalog_root=self.test_path)
        self.assertEqual(under_test, [self.test_obj, self.test_obj])
        self.assertEqual(mock_walk.call_count, 1)
        self.assertEqual(mock_path.call_count, 2)
        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(mock_json.call_count, 2)

    @skip
    def test_to_csv(self):
        raise NotImplementedError
