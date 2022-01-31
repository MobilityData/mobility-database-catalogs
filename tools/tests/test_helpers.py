from unittest import TestCase
from unittest.mock import patch, Mock
from tools.helpers import *


class TestVerificationFunctions(TestCase):
    def test_are_overlapping_edges(self):
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

    @patch("tools.helpers.are_overlapping_edges")
    def test_are_overlapping_boxes(self, mock_edges):
        test_source_minimum_latitude = 0.000000
        test_source_maximum_latitude = 0.000000
        test_source_minimum_longitude = 0.000000
        test_source_maximum_longitude = 0.000000
        test_filter_minimum_latitude = 0.000000
        test_filter_maximum_latitude = 0.000000
        test_filter_minimum_longitude = 0.000000
        test_filter_maximum_longitude = 0.000000

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

    @patch("tools.helpers.load_gtfs")
    def test_is_readable(self, mock_load_func):
        test_url = "test_url"

        mock_load_func.side_effect = Mock(side_effect=TypeError())
        self.assertRaises(
            Exception, is_readable, url=test_url, load_func=mock_load_func
        )

        mock_load_func.side_effect = Mock(side_effect=MissingSchema())
        self.assertRaises(
            Exception, is_readable, url=test_url, load_func=mock_load_func
        )

        mock_load_func.side_effect = Mock(side_effect=ParserError())
        self.assertRaises(
            Exception, is_readable, url=test_url, load_func=mock_load_func
        )

        mock_load_func.side_effect = "some_dataset"
        under_test = is_readable(url=test_url, load_func=mock_load_func)
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
    @patch("tools.helpers.gtfs_kit.read_feed")
    def test_load_gtfs(self, mock_gtfs_kit):
        test_url = "test_url"
        test_dataset = "some_gtfs_dataset"

        mock_gtfs_kit.return_value = test_dataset
        under_test = load_gtfs(url=test_url)
        self.assertEqual(under_test, test_dataset)

        mock_gtfs_kit.side_effect = Mock(side_effect=TypeError())
        self.assertRaises(
            TypeError,
            load_gtfs,
            url=test_url,
        )

        mock_gtfs_kit.side_effect = Mock(side_effect=MissingSchema())
        self.assertRaises(
            MissingSchema,
            load_gtfs,
            url=test_url,
        )

        mock_gtfs_kit.side_effect = Mock(side_effect=ParserError())
        self.assertRaises(
            ParserError,
            load_gtfs,
            url=test_url,
        )
