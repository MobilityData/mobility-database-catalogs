from unittest import TestCase
from unittest.mock import patch
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
