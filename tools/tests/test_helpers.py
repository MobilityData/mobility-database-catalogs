from unittest import TestCase, skip
from unittest.mock import patch, Mock

import pandas as pd
import requests
from freezegun import freeze_time
from requests.exceptions import HTTPError

from tools.helpers import (
    are_overlapping_edges,
    are_overlapping_boxes,
    is_readable,
    RequestException,
    ParserError,
    create_latest_url,
    create_filename,
    get_iso_time,
    load_gtfs,
    extract_gtfs_bounding_box,
    extract_gtfs_calendar_range,
    STOP_LAT,
    STOP_LON,
    START_DATE,
    END_DATE,
    DATE,
    to_json,
    from_json,
    normalize,
    download_dataset,
)


class TestVerificationFunctions(TestCase):
    def setUp(self):
        self.test_path = "some_path"

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

    @patch("tools.helpers.are_overlapping_edges")
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

    @patch("tools.helpers.load_gtfs")
    def test_is_not_readable(self, mock_load_func):
        mock_load_func.side_effect = Mock(side_effect=TypeError())
        self.assertRaises(
            Exception, is_readable, file_path=self.test_path, load_func=mock_load_func
        )

        mock_load_func.side_effect = Mock(side_effect=ParserError())
        self.assertRaises(
            Exception, is_readable, file_path=self.test_path, load_func=mock_load_func
        )

    @patch("tools.helpers.load_gtfs")
    def test_is_readable(self, mock_load_func):
        mock_load_func.side_effect = "some_dataset"
        under_test = is_readable(file_path=self.test_path, load_func=mock_load_func)
        self.assertTrue(under_test)


class TestCreationFunctions(TestCase):
    def setUp(self):
        self.test_path = "some_path"

    @patch("tools.helpers.create_filename")
    def test_create_latest_url(self, mock_filename):
        mock_filename.return_value = "ca-some-subdivision-name-some-provider-gtfs-1.zip"
        test_country_code = "CA"
        test_subdivision_name = "Some Subdivision Name"
        test_provider = "Some Provider"
        test_data_type = "gtfs"
        test_mdb_source_id = "1"
        test_latest_url = "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/ca-some-subdivision-name-some-provider-gtfs-1.zip?alt=media"
        under_test = create_latest_url(
            country_code=test_country_code,
            subdivision_name=test_subdivision_name,
            provider=test_provider,
            data_type=test_data_type,
            mdb_source_id=test_mdb_source_id,
        )
        self.assertEqual(under_test, test_latest_url)
        self.assertEqual(mock_filename.call_count, 1)

    def test_create_filename(self):
        test_country_code = "CA"
        test_subdivision_name = "Some Subdivision Name"
        test_provider = "Some Provider"
        test_data_type = "gtfs"
        test_mdb_source_id = "1"
        test_extension = "zip"
        test_filename = "ca-some-subdivision-name-some-provider-gtfs-1.zip"
        under_test = create_filename(
            country_code=test_country_code,
            subdivision_name=test_subdivision_name,
            provider=test_provider,
            data_type=test_data_type,
            mdb_source_id=test_mdb_source_id,
            extension=test_extension,
        )
        self.assertEqual(under_test, test_filename)

    def test_normalize(self):
        test_string = "test"
        under_test = normalize(test_string)
        self.assertEqual(under_test, "test")

        test_string = "Some Test"
        under_test = normalize(test_string)
        self.assertEqual(under_test, "some-test")

        test_string = "Some ~Test &!"
        under_test = normalize(test_string)
        self.assertEqual(under_test, "some-test")

        test_string = "1000 +=+=== Some    ******* ~Test &!"
        under_test = normalize(test_string)
        self.assertEqual(under_test, "1000-some-test")

        test_string = "SOURCE's test..."
        under_test = normalize(test_string)
        self.assertEqual(under_test, "sources-test")

        test_string = "SOURCé-çø-čõå-ćō-cåã."
        under_test = normalize(test_string)
        self.assertEqual(under_test, "source-co-coa-co-caa")

        test_string = "Source provider,, another, , pro"
        under_test = normalize(test_string)
        self.assertEqual(under_test, "source-provider")

    @freeze_time("2022-01-01")
    def test_get_iso_time(self):
        test_time = "2022-01-01T00:00:00+00:00"
        under_test = get_iso_time()
        self.assertEqual(under_test, test_time)


class TestGtfsSpecificFunctions(TestCase):
    def setUp(self):
        self.test_path = "some_path"

    @patch("tools.helpers.gtfs_kit.read_feed")
    def test_not_loading_gtfs(self, mock_gtfs_kit):
        mock_gtfs_kit.side_effect = Mock(side_effect=TypeError())
        self.assertRaises(
            TypeError,
            load_gtfs,
            file_path=self.test_path,
        )

        mock_gtfs_kit.side_effect = Mock(side_effect=ParserError())
        self.assertRaises(
            ParserError,
            load_gtfs,
            file_path=self.test_path,
        )

    @patch("tools.helpers.gtfs_kit.read_feed")
    def test_loading_gtfs(self, mock_gtfs_kit):
        test_dataset = "some_gtfs_dataset"
        mock_gtfs_kit.return_value = test_dataset
        under_test = load_gtfs(file_path=self.test_path)
        self.assertEqual(under_test, test_dataset)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_none_stops(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = None
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(file_path=self.test_path)
        self.assertEqual(under_test, test_bounding_box)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_empty_dataframe(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame()
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(file_path=self.test_path)
        self.assertEqual(under_test, test_bounding_box)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_missing_columns(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame({"some_column": []})
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(file_path=self.test_path)
        self.assertEqual(under_test, test_bounding_box)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_empty_columns(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame({STOP_LAT: [], STOP_LON: []})
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(file_path=self.test_path)
        self.assertEqual(under_test, test_bounding_box)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_nan_values(self, mock_load_gtfs):
        test_bounding_box = (None, None, None, None)
        test_stops = pd.DataFrame({STOP_LAT: [pd.NA], STOP_LON: [pd.NA]})
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(file_path=self.test_path)
        self.assertEqual(under_test, test_bounding_box)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_bounding_box_stops_present(self, mock_load_gtfs):
        test_bounding_box = (44.00000, 45.000000, -110.000000, -109.000000)

        test_stops = pd.DataFrame(
            {
                STOP_LAT: [44.000000, 45.000000, pd.NA],
                STOP_LON: [-110.000000, -109.000000, pd.NA],
            }
        )
        type(mock_load_gtfs.return_value).stops = test_stops
        under_test = extract_gtfs_bounding_box(file_path=self.test_path)
        self.assertEqual(under_test, test_bounding_box)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_calendar_range_no_calendar_or_calendar_dates(self, mock_load_gtfs):
        test_return_min_max = (None, None)
        test_calendar = None
        type(mock_load_gtfs.return_value).calendar = test_calendar
        test_calendar_dates = None
        type(mock_load_gtfs.return_value).calendar_dates = test_calendar_dates
        under_test = extract_gtfs_calendar_range(file_path=self.test_path)
        self.assertEqual(under_test, test_return_min_max)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_calendar_range_invalid_calendar(self, mock_load_gtfs):
        test_return_min_max = (None, None)
        test_calendar = pd.DataFrame(
            {
                # Note: only YYYYMMDD valid per GTFS spec; YYYY-MM-DD & nil values dropped
                START_DATE: ["2024-02-30", pd.NA],
                END_DATE: ["2034-02-01", pd.NA]
            }
        )
        type(mock_load_gtfs.return_value).calendar = test_calendar
        test_calendar_dates = None
        type(mock_load_gtfs.return_value).calendar_dates = test_calendar_dates
        under_test = extract_gtfs_calendar_range(file_path=self.test_path)
        self.assertEqual(under_test, test_return_min_max)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_calendar_range_only_calendar(self, mock_load_gtfs):
        test_return_min_max = ('2010-01-02', '2032-04-09')
        test_calendar = pd.DataFrame(
            {
                # Note: only YYYYMMDD valid per GTFS spec; YYYY-MM-DD & nil values dropped
                START_DATE: ["20100102", "20230702", "20230402", "2024-02-30", pd.NA],
                END_DATE: ["20140104", "20230709", "20320409", "2034-02-01", pd.NA]
            }
        )
        type(mock_load_gtfs.return_value).calendar = test_calendar
        test_calendar_dates = None
        type(mock_load_gtfs.return_value).calendar_dates = test_calendar_dates
        under_test = extract_gtfs_calendar_range(file_path=self.test_path)
        self.assertEqual(under_test, test_return_min_max)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_calendar_range_only_calendar_dates(self, mock_load_gtfs):
        test_return_min_max = ('2021-07-02', '2029-04-02')
        test_calendar = None
        type(mock_load_gtfs.return_value).calendar = test_calendar
        test_calendar_dates = pd.DataFrame(
            {
                # Note: only YYYYMMDD valid per GTFS spec; YYYY-MM-DD & nil values dropped
                DATE: ["20240102", "20210702", "20290402", "2027-02-30", pd.NA],
            }
        )
        type(mock_load_gtfs.return_value).calendar_dates = test_calendar_dates
        under_test = extract_gtfs_calendar_range(file_path=self.test_path)
        self.assertEqual(under_test, test_return_min_max)

    @patch("tools.helpers.load_gtfs")
    def test_extract_gtfs_calendar_range_both_calendar_and_calendar_dates(self, mock_load_gtfs):
        test_return_min_max = ('1999-01-02', '2031-07-02')
        test_calendar = pd.DataFrame(
            {
                # Note: only YYYYMMDD valid per GTFS spec; YYYY-MM-DD & nil values dropped
                START_DATE: ["19990102", "20230702", "20230402", "2024-02-30", pd.NA],
                END_DATE: ["20240104", "20230709", "20230409", "2034-02-01", pd.NA]
            }
        )
        type(mock_load_gtfs.return_value).calendar = test_calendar
        test_calendar_dates = pd.DataFrame(
            {
                # Note: only YYYYMMDD valid per GTFS spec; YYYY-MM-DD & nil values dropped
                DATE: ["20240102", "20310702", "20290402", "2027-02-30", pd.NA],
            }
        )
        type(mock_load_gtfs.return_value).calendar_dates = test_calendar_dates
        under_test = extract_gtfs_calendar_range(file_path=self.test_path)
        self.assertEqual(under_test, test_return_min_max)

class TestInOutFunctions(TestCase):
    def setUp(self):
        self.test_url = "some_url"
        self.test_path = "some_path"
        self.test_obj = {"some_key": "some_value"}

    @patch("tools.helpers.open")
    @patch("tools.helpers.json.dump")
    def test_to_json(self, mock_json, mock_open):
        under_test = to_json(path=self.test_path, obj=self.test_obj)
        self.assertIsNone(under_test)
        mock_open.assert_called_once()
        mock_json.assert_called_once()

    @patch("tools.helpers.open")
    @patch("tools.helpers.json.load")
    def test_from_json(self, mock_json, mock_open):
        mock_json.return_value = self.test_obj
        under_test = from_json(path=self.test_path)
        self.assertEqual(under_test, self.test_obj)
        mock_open.assert_called_once()
        mock_json.assert_called_once()

    @skip
    def test_to_csv(self):
        raise NotImplementedError

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_auth_type_empty(
            self, mock_requests, mock_os, mock_uuid4, mock_open
    ):
        test_authentication_type = None
        test_api_key_parameter_name = None
        test_api_key_parameter_value = None
        mock_os.path.join.return_value = self.test_path
        under_test = download_dataset(
            url=self.test_url,
            authentication_type=test_authentication_type,
            api_key_parameter_name=test_api_key_parameter_name,
            api_key_parameter_value=test_api_key_parameter_value,
        )
        self.assertEqual(under_test, self.test_path)
        self.assertEqual(mock_requests.call_args.kwargs["params"], None)
        self.assertEqual(mock_requests.call_args.kwargs["headers"], None)
        mock_requests.assert_called_once()
        mock_os.path.join.assert_called_once()
        mock_os.getcwd.assert_called_once()
        mock_uuid4.assert_called_once()
        mock_open.assert_called_once()

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_auth_type_0(
            self, mock_requests, mock_os, mock_uuid4, mock_open
    ):
        test_authentication_type = 0
        test_api_key_parameter_name = None
        test_api_key_parameter_value = None
        mock_os.path.join.return_value = self.test_path
        under_test = download_dataset(
            url=self.test_url,
            authentication_type=test_authentication_type,
            api_key_parameter_name=test_api_key_parameter_name,
            api_key_parameter_value=test_api_key_parameter_value,
        )
        self.assertEqual(under_test, self.test_path)
        self.assertEqual(mock_requests.call_args.kwargs["params"], None)
        self.assertEqual(mock_requests.call_args.kwargs["headers"], None)
        mock_requests.assert_called_once()
        mock_os.path.join.assert_called_once()
        mock_os.getcwd.assert_called_once()
        mock_uuid4.assert_called_once()
        mock_open.assert_called_once()

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_auth_type_1(
            self, mock_requests, mock_os, mock_uuid4, mock_open
    ):
        test_authentication_type = 1
        test_api_key_parameter_name = "some_name"
        test_api_key_parameter_value = "some_value"
        mock_os.path.join.return_value = self.test_path
        under_test = download_dataset(
            url=self.test_url,
            authentication_type=test_authentication_type,
            api_key_parameter_name=test_api_key_parameter_name,
            api_key_parameter_value=test_api_key_parameter_value,
        )
        self.assertEqual(under_test, self.test_path)
        self.assertEqual(
            mock_requests.call_args.kwargs["params"],
            {test_api_key_parameter_name: test_api_key_parameter_value},
        )
        self.assertEqual(mock_requests.call_args.kwargs["headers"], None)
        mock_requests.assert_called_once()
        mock_os.path.join.assert_called_once()
        mock_os.getcwd.assert_called_once()
        mock_uuid4.assert_called_once()
        mock_open.assert_called_once()

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_auth_type_2(
            self, mock_requests, mock_os, mock_uuid4, mock_open
    ):
        test_authentication_type = 2
        test_api_key_parameter_name = "some_name"
        test_api_key_parameter_value = "some_value"
        mock_os.path.join.return_value = self.test_path
        under_test = download_dataset(
            url=self.test_url,
            authentication_type=test_authentication_type,
            api_key_parameter_name=test_api_key_parameter_name,
            api_key_parameter_value=test_api_key_parameter_value,
        )
        self.assertEqual(under_test, self.test_path)
        self.assertEqual(mock_requests.call_args.kwargs["params"], None)
        self.assertEqual(
            mock_requests.call_args.kwargs["headers"],
            {test_api_key_parameter_name: test_api_key_parameter_value},
        )
        mock_requests.assert_called_once()
        mock_os.path.join.assert_called_once()
        mock_os.getcwd.assert_called_once()
        mock_uuid4.assert_called_once()
        mock_open.assert_called_once()

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_exception(
            self, mock_requests, mock_os, mock_uuid4, mock_open
    ):
        test_authentication_type = None
        test_api_key_parameter_name = None
        test_api_key_parameter_value = None

        mock_requests.side_effect = Mock(side_effect=RequestException)
        self.assertRaises(
            RequestException,
            download_dataset,
            url=self.test_url,
            authentication_type=test_authentication_type,
            api_key_parameter_name=test_api_key_parameter_name,
            api_key_parameter_value=test_api_key_parameter_value,
        )

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_403_fallback_success(self, mock_requests, mock_os, mock_uuid4, mock_open):
        response_403 = Mock(status_code=403)
        response_403.raise_for_status.side_effect = HTTPError(response=response_403)

        response_200 = Mock(status_code=200, content=b"file_content")

        mock_requests.side_effect = [response_403, response_200]
        mock_os.path.join.return_value = self.test_path

        under_test = download_dataset(url=self.test_url, authentication_type=0, api_key_parameter_name=None,
                                      api_key_parameter_value=None, )

        self.assertEqual(under_test, self.test_path)
        self.assertEqual(mock_requests.call_count, 2)

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_403_fallback_failure(self, mock_requests, mock_os, mock_uuid4, mock_open):
        test_authentication_type = 0
        test_api_key_parameter_name = None
        test_api_key_parameter_value = None

        response_403_1 = Mock(status_code=403)
        response_403_1.raise_for_status.side_effect = HTTPError(response=response_403_1)
        response_403_2 = Mock(status_code=403)
        response_403_2.raise_for_status.side_effect = HTTPError(response=response_403_2)
        response_403_3 = Mock(status_code=403)
        response_403_3.raise_for_status.side_effect = HTTPError(response=response_403_3)

        mock_requests.side_effect = [response_403_1, response_403_2, response_403_3]

        mock_os.path.join.return_value = self.test_path
        self.assertRaises(RequestException, download_dataset, url=self.test_url,
                          authentication_type=test_authentication_type,
                          api_key_parameter_name=test_api_key_parameter_name,
                          api_key_parameter_value=test_api_key_parameter_value)

        self.assertEqual(mock_requests.call_count, 3)
        mock_os.path.join.assert_called_once()
        mock_os.getcwd.assert_called_once()
        mock_uuid4.assert_called_once()
        mock_open.assert_not_called()

    @patch("tools.helpers.open")
    @patch("tools.helpers.uuid.uuid4")
    @patch("tools.helpers.os")
    @patch("tools.helpers.requests.get")
    def test_download_dataset_ssl_error_fallback(self, mock_requests, mock_os, mock_uuid4, mock_open):
        test_authentication_type = 0
        test_api_key_parameter_name = None
        test_api_key_parameter_value = None

        ssl_error = requests.exceptions.SSLError("SSL Certificate Verification Failed")

        response_200 = Mock(status_code=200, content=b"file_content")

        mock_requests.side_effect = [ssl_error, response_200]
        mock_os.path.join.return_value = self.test_path

        under_test = download_dataset(
            url=self.test_url,
            authentication_type=test_authentication_type,
            api_key_parameter_name=test_api_key_parameter_name,
            api_key_parameter_value=test_api_key_parameter_value,
        )

        self.assertEqual(under_test, self.test_path)
        self.assertEqual(mock_requests.call_count, 2)

        self.assertTrue(mock_requests.call_args_list[0].kwargs["verify"])
        self.assertFalse(mock_requests.call_args_list[1].kwargs["verify"])

        mock_os.path.join.assert_called_once()
        mock_os.getcwd.assert_called_once()
        mock_uuid4.assert_called_once()
        mock_open.assert_called_once()
