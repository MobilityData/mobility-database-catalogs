from unittest import TestCase
from unittest.mock import patch, MagicMock
from copy import deepcopy
from tools.representations import (
    Catalog,
    SourcesCatalog,
    GtfsScheduleSourcesCatalog,
    GtfsRealtimeSourcesCatalog,
    GtfsScheduleSource,
    GtfsRealtimeSource,
    FILENAME,
    ENTITY_CLS,
    ROOT,
    PATH,
    MDB_SOURCE_ID,
    DATA_TYPE,
    PROVIDER,
    NAME,
    COUNTRY_CODE,
    SUBDIVISION_NAME,
    MUNICIPALITY,
    MINIMUM_LATITUDE,
    MAXIMUM_LATITUDE,
    MINIMUM_LONGITUDE,
    MAXIMUM_LONGITUDE,
    EXTRACTED_ON,
    DIRECT_DOWNLOAD,
    LATEST,
    LICENSE,
    URLS,
    LOCATION,
    BOUNDING_BOX,
    STATIC_REFERENCE,
    AUTHENTICATION_TYPE,
    AUTHENTICATION_INFO,
    API_KEY_PARAMETER_NAME,
    ENTITY_TYPE,
    NOTE,
    FEATURES,
    STATUS,
    json,
)


class TestCatalog(TestCase):
    def setUp(self):
        self.test_path = "some_path"
        self.test_filename = "some-source.json"
        self.test_another_filename = "another-source.json"
        self.test_key = "some_key"
        self.test_value = "some_value"
        self.test_another_value = "another_value"
        self.test_obj = {self.test_key: self.test_value}
        self.test_another_obj = {self.test_key: self.test_another_value}

    @patch("tools.representations.os.walk")
    def test_identify(self, mock_walk):
        mock_walk.return_value = [
            ("/catalogs", ("sources",), ()),
            ("/catalogs/sources", ("gtfs",), ()),
            ("/catalogs/sources/gtfs", ("schedule",), ()),
            (
                "/catalogs/sources/gtfs/schedule",
                (),
                (self.test_filename, self.test_another_filename),
            ),
        ]
        under_test = Catalog.identify(catalog_root=self.test_path)
        self.assertEqual(under_test, 3)
        self.assertEqual(mock_walk.call_count, 1)

    @patch("tools.representations.os.walk")
    @patch("tools.representations.os.path.join")
    @patch("tools.representations.open")
    @patch("tools.representations.json.load")
    def test_aggregate(self, mock_json, mock_open, mock_path, mock_walk):
        mock_walk.return_value = [
            ("/catalogs", ("sources",), ()),
            ("/catalogs/sources", ("gtfs",), ()),
            ("/catalogs/sources/gtfs", ("schedule",), ()),
            (
                "/catalogs/sources/gtfs/schedule",
                (),
                (self.test_filename, self.test_another_filename),
            ),
        ]
        mock_json.side_effect = [self.test_obj, self.test_another_obj]
        under_test = Catalog.aggregate(
            catalog_path=self.test_path, id_key=self.test_key, entity_cls=dict
        )
        self.assertEqual(
            under_test,
            {
                self.test_value: {
                    FILENAME: self.test_filename,
                    self.test_key: self.test_value,
                },
                self.test_another_value: {
                    FILENAME: self.test_another_filename,
                    self.test_key: self.test_another_value,
                },
            },
        )
        self.assertEqual(mock_walk.call_count, 1)
        self.assertEqual(mock_path.call_count, 2)
        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(mock_json.call_count, 2)


class TestSourcesCatalog(TestCase):
    def setUp(self):
        self.test_source_key = 0
        self.test_another_source_key = 1
        self.test_json = {"some_json_key": "some_json_value"}
        self.test_nonexistent_key = "some_nonexistent_key"
        self.test_source = MagicMock()
        self.test_source.as_json.return_value = self.test_json
        self.test_another_source = MagicMock()
        self.test_another_source.as_json.return_value = self.test_json
        self.test_root = "some/root"
        self.test_path = "to/some/catalog"
        self.test_catalog = {
            self.test_source_key: self.test_source,
            self.test_another_source_key: self.test_another_source,
        }
        self.test_entity_cls = MagicMock()
        self.test_kwargs = {
            ENTITY_CLS: self.test_entity_cls,
            ROOT: self.test_root,
            PATH: self.test_path,
        }

    @patch("tools.representations.Catalog.aggregate")
    def test_get_source(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        instance = SourcesCatalog(**self.test_kwargs)
        under_test = instance.get_source(self.test_source_key)
        self.assertEqual(under_test, self.test_source)
        under_test = instance.get_source(self.test_another_source_key)
        self.assertEqual(under_test, self.test_another_source)
        under_test = instance.get_source(self.test_nonexistent_key)
        self.assertIsNone(under_test)

    @patch("tools.representations.Catalog.aggregate")
    def test_get_sources(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        instance = SourcesCatalog(**self.test_kwargs)
        under_test = instance.get_sources()
        self.assertEqual(
            under_test,
            {
                self.test_source_key: self.test_json,
                self.test_another_source_key: self.test_json,
            },
        )

    @patch("tools.representations.Catalog.aggregate")
    def test_get_sources_by_bounding_box(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        self.test_source.is_overlapping_bounding_box.return_value = True
        self.test_another_source.is_overlapping_bounding_box.return_value = False
        instance = SourcesCatalog(**self.test_kwargs)
        test_minimum_latitude = 43.00000
        test_maximum_latitude = 43.20000
        test_minimum_longitude = -81.50000
        test_maximum_longitude = -81.30000
        under_test = instance.get_sources_by_bounding_box(
            minimum_latitude=test_minimum_latitude,
            maximum_latitude=test_maximum_latitude,
            minimum_longitude=test_minimum_longitude,
            maximum_longitude=test_maximum_longitude,
        )
        self.assertEqual(under_test, {self.test_source_key: self.test_json})

    @patch("tools.representations.Catalog.aggregate")
    def test_get_sources_by_subdivision_name(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        self.test_source.has_subdivision_name.return_value = True
        self.test_another_source.has_subdivision_name.return_value = False
        instance = SourcesCatalog(**self.test_kwargs)
        test_subdivision_name = "Ontario"
        under_test = instance.get_sources_by_subdivision_name(
            subdivision_name=test_subdivision_name
        )
        self.assertEqual(under_test, {self.test_source_key: self.test_json})

    @patch("tools.representations.Catalog.aggregate")
    def test_get_sources_by_country_code(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        self.test_source.has_country_code.return_value = True
        self.test_another_source.has_country_code.return_value = False
        instance = SourcesCatalog(**self.test_kwargs)
        test_country_code = "CA"
        under_test = instance.get_sources_by_country_code(
            country_code=test_country_code
        )
        self.assertEqual(under_test, {self.test_source_key: self.test_json})

    @patch("tools.representations.Catalog.aggregate")
    def test_get_latest_dataset(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        self.test_source.has_latest_dataset.return_value = True
        self.test_another_source.has_latest_dataset.return_value = False
        test_latest_url = "some_latest_url"
        self.test_source.latest_url = test_latest_url
        instance = SourcesCatalog(**self.test_kwargs)
        under_test = instance.get_latest_datasets()
        self.assertEqual(under_test, {self.test_source_key: test_latest_url})

    @patch("tools.representations.Catalog.aggregate")
    def test_get_sources_by_feature(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        self.test_source.has_feature.return_value = True
        self.test_another_source.has_feature.return_value = False
        instance = SourcesCatalog(**self.test_kwargs)
        test_feature = "flex-v2"
        under_test = instance.get_sources_by_feature(feature=test_feature)
        self.assertEqual(under_test, {self.test_source_key: self.test_json})

    @patch("tools.representations.Catalog.aggregate")
    def test_get_sources_by_status(self, mock_aggregate):
        mock_aggregate.return_value = self.test_catalog
        self.test_source.has_status.return_value = True
        self.test_another_source.has_status.return_value = False
        instance = SourcesCatalog(**self.test_kwargs)
        test_status = "active"
        under_test = instance.get_sources_by_status(status=test_status)
        self.assertEqual(under_test, {self.test_source_key: self.test_json})

    @patch("tools.representations.SourcesCatalog.save")
    @patch("tools.representations.isinstance")
    @patch("tools.representations.Catalog.identify")
    @patch("tools.representations.Catalog.aggregate")
    def test_add(self, mock_aggregate, mock_identify, mock_isinstance, mock_save):
        test_new_id = 3
        test_catalog = self.test_catalog
        test_catalog.update({test_new_id: self.test_source})
        mock_aggregate.return_value = self.test_catalog
        mock_identify.return_value = test_new_id
        self.test_entity_cls.build.return_value = self.test_source
        mock_isinstance.return_value = True
        instance = SourcesCatalog(**self.test_kwargs)
        under_test = instance.add(**self.test_kwargs)
        self.assertEqual(under_test, test_catalog)
        mock_isinstance.assert_called_once()
        mock_save.assert_called_once()

    @patch("tools.representations.SourcesCatalog.save")
    @patch("tools.representations.SourcesCatalog.get_source")
    @patch("tools.representations.Catalog.aggregate")
    def test_update(self, mock_aggregate, mock_source, mock_save):
        mock_aggregate.return_value = self.test_catalog
        mock_source.return_value = self.test_source
        self.test_source.update.return_value = self.test_source
        instance = SourcesCatalog(**self.test_kwargs)
        under_test = instance.update(
            mdb_source_id=self.test_source_key, **self.test_kwargs
        )
        self.assertEqual(under_test, self.test_catalog)
        mock_source.assert_called_once()
        mock_save.assert_called_once()

    @patch("tools.representations.to_json")
    @patch("tools.representations.Catalog.aggregate")
    def test_save(self, mock_aggregate, mock_func):
        mock_aggregate.return_value = self.test_catalog
        mock_func.return_value = None
        instance = SourcesCatalog(**self.test_kwargs)
        under_test = instance.save(self.test_source)
        self.assertIsNone(under_test)
        mock_func.assert_called_once()


class TestGtfsScheduleSourcesCatalog(TestCase):
    def test_singleton(self):
        test_singleton = GtfsScheduleSourcesCatalog()
        under_test = GtfsScheduleSourcesCatalog()
        self.assertTrue(under_test is test_singleton)


class TestGtfsRealtimeSourcesCatalog(TestCase):
    def test_singleton(self):
        test_singleton = GtfsRealtimeSourcesCatalog()
        under_test = GtfsRealtimeSourcesCatalog()
        self.assertTrue(under_test is test_singleton)


class TestGtfsScheduleSource(TestCase):
    def setUp(self):
        self.test_mdb_source_id = "some_numerical_id"
        self.test_data_type = "some_data_type"
        self.test_provider = "some_provider_with_accents_éàç"
        self.test_name = "some_name"
        self.test_feature = "some_feature"
        self.test_features = [self.test_feature]
        self.test_status = "some_status"
        self.test_filename = "some_filename"
        self.test_country_code = "some_country_code"
        self.test_subdivision_name = "some_subdivision_name"
        self.test_municipality = "some_municipality"
        self.test_min_lat = "some_min_lat"
        self.test_max_lat = "some_max_lat"
        self.test_min_lon = "some_min_lon"
        self.test_max_lon = "some_max_lon"
        self.test_extracted_on = "some_extraction_time"
        self.test_direct_download_url = "some_direct_download_url"
        self.test_latest_url = "some_latest_url"
        self.test_license_url = "some_license_url"
        self.test_kwargs = {
            MDB_SOURCE_ID: self.test_mdb_source_id,
            DATA_TYPE: self.test_data_type,
            PROVIDER: self.test_provider,
            NAME: self.test_name,
            FILENAME: self.test_filename,
            COUNTRY_CODE: self.test_country_code,
            SUBDIVISION_NAME: self.test_subdivision_name,
            MUNICIPALITY: self.test_municipality,
            MINIMUM_LATITUDE: self.test_min_lat,
            MAXIMUM_LATITUDE: self.test_max_lat,
            MINIMUM_LONGITUDE: self.test_min_lon,
            MAXIMUM_LONGITUDE: self.test_max_lon,
            EXTRACTED_ON: self.test_extracted_on,
            DIRECT_DOWNLOAD: self.test_direct_download_url,
            LATEST: self.test_latest_url,
            LICENSE: self.test_license_url,
            FEATURES: self.test_features,
            STATUS: self.test_status,
        }
        self.test_schema = {
            MDB_SOURCE_ID: self.test_mdb_source_id,
            DATA_TYPE: self.test_data_type,
            PROVIDER: self.test_provider,
            NAME: self.test_name,
            FEATURES: self.test_features,
            STATUS: self.test_status,
            LOCATION: {
                COUNTRY_CODE: self.test_country_code,
                SUBDIVISION_NAME: self.test_subdivision_name,
                MUNICIPALITY: self.test_municipality,
                BOUNDING_BOX: {
                    MINIMUM_LATITUDE: self.test_min_lat,
                    MAXIMUM_LATITUDE: self.test_max_lat,
                    MINIMUM_LONGITUDE: self.test_min_lon,
                    MAXIMUM_LONGITUDE: self.test_max_lon,
                    EXTRACTED_ON: self.test_extracted_on,
                },
            },
            URLS: {
                DIRECT_DOWNLOAD: self.test_direct_download_url,
                LATEST: self.test_latest_url,
                LICENSE: self.test_license_url,
            },
        }

    @patch("tools.representations.GtfsScheduleSource.schematize")
    def test_str(self, mock_schema):
        # Intentionally not patching json.dumps to test the actual behavior
        mock_schema.return_value = self.test_schema
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.__str__()
        self.assertEqual(under_test, json.dumps(self.test_schema, ensure_ascii=False))

    @patch("tools.representations.GtfsScheduleSource.__str__")
    def test_repr(self, mock_str):
        test_repr = f"GtfsScheduleSource({str(self.test_schema)})"
        mock_str.return_value = str(self.test_schema)
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.__repr__()
        self.assertEqual(under_test, test_repr)

    def test_has_subdivision_name(self):
        test_subdivision_name = self.test_subdivision_name
        test_another_subdivision_name = "some_another_subdivision_name"
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_subdivision_name(
            subdivision_name=test_subdivision_name
        )
        self.assertTrue(under_test)
        under_test = instance.has_subdivision_name(
            subdivision_name=test_another_subdivision_name
        )
        self.assertFalse(under_test)

    def test_has_country_code(self):
        test_country_code = self.test_country_code
        test_another_country_code = "some_another_country_code"
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_country_code(country_code=test_country_code)
        self.assertTrue(under_test)
        under_test = instance.has_country_code(country_code=test_another_country_code)
        self.assertFalse(under_test)

    @patch("tools.representations.are_overlapping_boxes")
    def test_is_overlapping_bounding_box(self, mock_overlapping_func):
        test_minimum_latitude = 43.00000
        test_maximum_latitude = 43.20000
        test_minimum_longitude = -81.50000
        test_maximum_longitude = -81.30000
        mock_overlapping_func.side_effect = [True, False]
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.is_overlapping_bounding_box(
            minimum_latitude=test_minimum_latitude,
            maximum_latitude=test_maximum_latitude,
            minimum_longitude=test_minimum_longitude,
            maximum_longitude=test_maximum_longitude,
        )
        self.assertTrue(under_test)
        under_test = instance.is_overlapping_bounding_box(
            minimum_latitude=test_minimum_latitude,
            maximum_latitude=test_maximum_latitude,
            minimum_longitude=test_minimum_longitude,
            maximum_longitude=test_maximum_longitude,
        )
        self.assertFalse(under_test)

    def test_has_latest_dataset(self):
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_latest_dataset()
        self.assertTrue(under_test)
        instance.latest_url = None
        under_test = instance.has_latest_dataset()
        self.assertFalse(under_test)

    def test_has_feature(self):
        test_feature = self.test_feature
        test_another_feature = ["some_other_feature"]
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_feature(feature=test_feature)
        self.assertTrue(under_test)
        under_test = instance.has_feature(feature=test_another_feature)
        self.assertFalse(under_test)

    def test_has_status(self):
        test_status = self.test_status
        test_another_status = "some_other_status"
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_status(status=test_status)
        self.assertTrue(under_test)
        under_test = instance.has_status(status=test_another_status)
        self.assertFalse(under_test)

    @patch("tools.representations.get_iso_time")
    @patch("tools.representations.extract_gtfs_bounding_box")
    @patch("tools.representations.is_readable")
    def test_update(self, mock_read_func, mock_bounding_box, mock_time):
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.update(**{})
        self.assertEqual(under_test.direct_download_url, self.test_direct_download_url)
        self.assertEqual(under_test.bbox_min_lat, self.test_min_lat)
        self.assertEqual(under_test.bbox_max_lat, self.test_max_lat)
        self.assertEqual(under_test.bbox_min_lon, self.test_min_lon)
        self.assertEqual(under_test.bbox_max_lon, self.test_max_lon)
        self.assertEqual(under_test.bbox_extracted_on, self.test_extracted_on)
        self.assertEqual(under_test.provider, self.test_provider)
        self.assertEqual(under_test.name, self.test_name)
        self.assertEqual(under_test.country_code, self.test_country_code)
        self.assertEqual(under_test.subdivision_name, self.test_subdivision_name)
        self.assertEqual(under_test.municipality, self.test_municipality)
        self.assertEqual(under_test.license_url, self.test_license_url)
        test_direct_download_url = "another_direct_download_url"
        test_min_lat = "another_min_lat"
        test_max_lat = "another_max_lat"
        test_min_lon = "another_min_lon"
        test_max_lon = "another_max_lon"
        test_extracted_on = "another_extraction_time"
        test_provider = "another_provider"
        test_name = "another_name"
        test_country_code = "another_country_code"
        test_subdivision_name = "another_subdivision_name"
        test_municipality = "another_municipality"
        test_license_url = "another_license_url"
        mock_read_func.return_value = True
        mock_bounding_box.return_value = (
            test_min_lat,
            test_max_lat,
            test_min_lon,
            test_max_lon,
        )
        mock_time.return_value = test_extracted_on
        under_test = instance.update(
            **{
                PROVIDER: test_provider,
                NAME: test_name,
                DIRECT_DOWNLOAD: test_direct_download_url,
                COUNTRY_CODE: test_country_code,
                SUBDIVISION_NAME: test_subdivision_name,
                MUNICIPALITY: test_municipality,
                LICENSE: test_license_url,
            }
        )
        self.assertEqual(under_test.direct_download_url, test_direct_download_url)
        self.assertEqual(under_test.bbox_min_lat, test_min_lat)
        self.assertEqual(under_test.bbox_max_lat, test_max_lat)
        self.assertEqual(under_test.bbox_min_lon, test_min_lon)
        self.assertEqual(under_test.bbox_max_lon, test_max_lon)
        self.assertEqual(under_test.bbox_extracted_on, test_extracted_on)
        self.assertEqual(under_test.provider, test_provider)
        self.assertEqual(under_test.name, test_name)
        self.assertEqual(under_test.country_code, test_country_code)
        self.assertEqual(under_test.subdivision_name, test_subdivision_name)
        self.assertEqual(under_test.municipality, test_municipality)
        self.assertEqual(under_test.license_url, test_license_url)

    @patch("tools.representations.GtfsScheduleSource.schematize")
    @patch("tools.representations.create_latest_url")
    @patch("tools.representations.create_filename")
    @patch("tools.representations.get_iso_time")
    @patch("tools.representations.extract_gtfs_bounding_box")
    @patch("tools.representations.is_readable")
    def test_build(
        self,
        mock_read_func,
        mock_bounding_box,
        mock_time,
        mock_filename,
        mock_latest_url,
        mock_schema,
    ):
        mock_read_func.return_value = False
        under_test = GtfsScheduleSource.build(**self.test_kwargs)
        self.assertIsNone(under_test)

        mock_read_func.return_value = True
        mock_bounding_box.return_value = (
            "some_min_lat",
            "some_max_lat",
            "some_min_lon",
            "some_max_lon",
        )
        mock_time.return_value = "some_time"
        mock_filename.return_value = "some_filename"
        mock_latest_url.return_value = "some_latest_url"
        mock_schema.return_value = deepcopy(self.test_schema)
        del self.test_kwargs[DATA_TYPE]
        del self.test_kwargs[MINIMUM_LATITUDE]
        del self.test_kwargs[MAXIMUM_LATITUDE]
        del self.test_kwargs[MINIMUM_LONGITUDE]
        del self.test_kwargs[MAXIMUM_LONGITUDE]
        del self.test_kwargs[EXTRACTED_ON]
        del self.test_kwargs[LATEST]
        under_test = GtfsScheduleSource.build(**self.test_kwargs)
        self.assertIsNotNone(under_test)

        del self.test_kwargs[NAME]
        del self.test_kwargs[LICENSE]
        del self.test_kwargs[SUBDIVISION_NAME]
        del self.test_kwargs[MUNICIPALITY]
        del self.test_schema[NAME]
        del self.test_schema[URLS][LICENSE]
        del self.test_schema[LOCATION][SUBDIVISION_NAME]
        del self.test_schema[LOCATION][MUNICIPALITY]
        mock_schema.return_value = deepcopy(self.test_schema)
        under_test = GtfsScheduleSource.build(**self.test_kwargs)
        self.assertIsNotNone(under_test)

    def test_schematize(self):
        under_test = GtfsScheduleSource.schematize(**self.test_kwargs)
        self.assertDictEqual(under_test, self.test_schema)

        del self.test_kwargs[NAME]
        del self.test_kwargs[LICENSE]
        del self.test_kwargs[SUBDIVISION_NAME]
        del self.test_kwargs[MUNICIPALITY]
        del self.test_schema[NAME]
        del self.test_schema[URLS][LICENSE]
        del self.test_schema[LOCATION][SUBDIVISION_NAME]
        del self.test_schema[LOCATION][MUNICIPALITY]
        under_test = GtfsScheduleSource.schematize(**self.test_kwargs)
        self.assertDictEqual(under_test, self.test_schema)

    @patch("tools.representations.GtfsScheduleSource.__str__")
    @patch("tools.representations.json.loads")
    def test_as_json(self, mock_json, mock_str):
        test_json = {"some_json_key": "some_json_value"}
        mock_json.return_value = test_json
        instance = GtfsScheduleSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.as_json()
        self.assertEqual(under_test, test_json)
        mock_json.assert_called_once()
        mock_str.assert_called_once()


class TestGtfsRealtimeSource(TestCase):
    def setUp(self):
        self.test_mdb_source_id = "some_numerical_id"
        self.test_data_type = "some_data_type"
        self.test_entity_type = ["some_entity_type", "some_other_entity_type"]
        self.test_provider = "some_provider_with_accents_éàç"
        self.test_name = "some_name"
        self.test_filename = "some_filename"
        self.test_static_reference = ["some_source_id", "another_source_id"]
        self.test_note = "some_note"
        self.test_direct_download_url = "some_direct_download_url"
        self.test_authentication_type = "some_authentication_type"
        self.test_authentication_info_url = "some_authentication_info_url"
        self.test_api_key_parameter_name = "some_api_key_parameter_name"
        self.test_license_url = "some_license_url"
        self.test_feature = "some_feature"
        self.test_features = [self.test_feature]
        self.test_status = "some_status"
        self.test_kwargs = {
            MDB_SOURCE_ID: self.test_mdb_source_id,
            DATA_TYPE: self.test_data_type,
            ENTITY_TYPE: self.test_entity_type,
            PROVIDER: self.test_provider,
            NAME: self.test_name,
            FILENAME: self.test_filename,
            STATIC_REFERENCE: self.test_static_reference,
            NOTE: self.test_note,
            DIRECT_DOWNLOAD: self.test_direct_download_url,
            AUTHENTICATION_TYPE: self.test_authentication_type,
            AUTHENTICATION_INFO: self.test_authentication_info_url,
            API_KEY_PARAMETER_NAME: self.test_api_key_parameter_name,
            LICENSE: self.test_license_url,
            FEATURES: self.test_features,
            STATUS: self.test_status,
        }
        self.test_schema = {
            MDB_SOURCE_ID: self.test_mdb_source_id,
            DATA_TYPE: self.test_data_type,
            ENTITY_TYPE: self.test_entity_type,
            PROVIDER: self.test_provider,
            NAME: self.test_name,
            STATIC_REFERENCE: self.test_static_reference,
            NOTE: self.test_note,
            STATUS: self.test_status,
            FEATURES: self.test_features,
            URLS: {
                DIRECT_DOWNLOAD: self.test_direct_download_url,
                AUTHENTICATION_TYPE: self.test_authentication_type,
                AUTHENTICATION_INFO: self.test_authentication_info_url,
                API_KEY_PARAMETER_NAME: self.test_api_key_parameter_name,
                LICENSE: self.test_license_url,
            },
        }

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.schematize")
    def test_str(self, mock_schema, mock_static_catalog):
        # Intentionally not patching json.dumps to test the actual behavior
        mock_schema.return_value = self.test_schema
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.__str__()
        self.assertEqual(under_test, json.dumps(self.test_schema, ensure_ascii=False))

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.__str__")
    def test_repr(self, mock_str, mock_static_catalog):
        test_repr = f"GtfsRealtimeSource({str(self.test_schema)})"
        mock_str.return_value = str(self.test_schema)
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.__repr__()
        self.assertEqual(under_test, test_repr)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.get_static_sources")
    def test_has_subdivision_name(self, mock_static_sources, mock_static_catalog):
        test_subdivision_name = "some_subdivision_name"
        test_another_subdivision_name = "another_subdivision_name"
        test_missing_subdivision_name = "missing_subdivision_name"
        test_static_source = MagicMock()
        test_static_source.subdivision_name = test_subdivision_name
        test_another_static_source = MagicMock()
        test_another_static_source.subdivision_name = test_another_subdivision_name
        mock_static_sources.return_value = [
            test_static_source,
            test_another_static_source,
        ]
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_subdivision_name(
            subdivision_name=test_subdivision_name
        )
        self.assertTrue(under_test)
        under_test = instance.has_subdivision_name(
            subdivision_name=test_another_subdivision_name
        )
        self.assertTrue(under_test)
        under_test = instance.has_subdivision_name(
            subdivision_name=test_missing_subdivision_name
        )
        self.assertFalse(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.get_static_sources")
    def test_has_country_code(self, mock_static_sources, mock_static_catalog):
        test_country_code = "some_country_code"
        test_another_country_code = "another_country_code"
        test_missing_country_code = "missing_country_code"
        test_static_source = MagicMock()
        test_static_source.country_code = test_country_code
        test_another_static_source = MagicMock()
        test_another_static_source.country_code = test_another_country_code
        mock_static_sources.return_value = [
            test_static_source,
            test_another_static_source,
        ]
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_country_code(country_code=test_country_code)
        self.assertTrue(under_test)
        under_test = instance.has_country_code(country_code=test_another_country_code)
        self.assertTrue(under_test)
        under_test = instance.has_country_code(country_code=test_missing_country_code)
        self.assertFalse(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.get_static_sources")
    @patch("tools.representations.are_overlapping_boxes")
    def test_is_overlapping_bounding_box(
        self, mock_overlapping_func, mock_static_sources, mock_static_catalog
    ):
        test_minimum_latitude = 43.00000
        test_maximum_latitude = 43.20000
        test_minimum_longitude = -81.50000
        test_maximum_longitude = -81.30000
        mock_overlapping_func.side_effect = [True, False, False, False]
        test_static_source = MagicMock()
        test_another_static_source = MagicMock()
        mock_static_sources.return_value = [
            test_static_source,
            test_another_static_source,
        ]
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.is_overlapping_bounding_box(
            minimum_latitude=test_minimum_latitude,
            maximum_latitude=test_maximum_latitude,
            minimum_longitude=test_minimum_longitude,
            maximum_longitude=test_maximum_longitude,
        )
        self.assertTrue(under_test)
        under_test = instance.is_overlapping_bounding_box(
            minimum_latitude=test_minimum_latitude,
            maximum_latitude=test_maximum_latitude,
            minimum_longitude=test_minimum_longitude,
            maximum_longitude=test_maximum_longitude,
        )
        self.assertFalse(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    def test_has_latest_dataset(self, mock_static_catalog):
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_latest_dataset()
        self.assertFalse(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    def test_has_feature(self, mock_static_catalog):
        test_feature = self.test_feature
        test_another_feature = "some_other_feature"
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_feature(feature=test_feature)
        self.assertTrue(under_test)
        under_test = instance.has_feature(feature=test_another_feature)
        self.assertFalse(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    def test_has_status(self, mock_static_catalog):
        test_status = self.test_status
        test_another_status = "some_other_status"
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.has_status(status=test_status)
        self.assertTrue(under_test)
        under_test = instance.has_status(status=test_another_status)
        self.assertFalse(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    def test_update(self, mock_static_catalog):
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.update(**{})
        self.assertEqual(under_test.entity_type, self.test_entity_type)
        self.assertEqual(under_test.provider, self.test_provider)
        self.assertEqual(under_test.name, self.test_name)
        self.assertEqual(under_test.static_reference, self.test_static_reference)
        self.assertEqual(under_test.note, self.test_note)
        self.assertEqual(under_test.direct_download_url, self.test_direct_download_url)
        self.assertEqual(under_test.authentication_type, self.test_authentication_type)
        self.assertEqual(
            under_test.authentication_info_url, self.test_authentication_info_url
        )
        self.assertEqual(
            under_test.api_key_parameter_name, self.test_api_key_parameter_name
        )
        self.assertEqual(under_test.license_url, self.test_license_url)
        test_entity_type = ["another_entity_type"]
        test_provider = "another_provider"
        test_name = "another_name"
        test_static_reference = ["another_static_reference"]
        test_note = "another_note"
        test_direct_download_url = "another_direct_download_url"
        test_authentication_type = "another_authentication_type"
        test_authentication_info_url = "another_authentication_info_url"
        test_api_key_parameter_name = "another_api_key_parameter_name"
        test_license_url = "another_license_url"
        under_test = instance.update(
            **{
                ENTITY_TYPE: test_entity_type,
                PROVIDER: test_provider,
                NAME: test_name,
                STATIC_REFERENCE: test_static_reference,
                NOTE: test_note,
                DIRECT_DOWNLOAD: test_direct_download_url,
                AUTHENTICATION_TYPE: test_authentication_type,
                AUTHENTICATION_INFO: test_authentication_info_url,
                API_KEY_PARAMETER_NAME: test_api_key_parameter_name,
                LICENSE: test_license_url,
            }
        )
        self.assertEqual(under_test.entity_type, test_entity_type)
        self.assertEqual(under_test.provider, test_provider)
        self.assertEqual(under_test.name, test_name)
        self.assertEqual(under_test.static_reference, test_static_reference)
        self.assertEqual(under_test.note, test_note)
        self.assertEqual(under_test.direct_download_url, test_direct_download_url)
        self.assertEqual(under_test.authentication_type, test_authentication_type)
        self.assertEqual(
            under_test.authentication_info_url, test_authentication_info_url
        )
        self.assertEqual(under_test.api_key_parameter_name, test_api_key_parameter_name)
        self.assertEqual(under_test.license_url, test_license_url)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.schematize")
    @patch("tools.representations.create_filename")
    @patch("tools.representations.GtfsRealtimeSource.get_static_sources")
    def test_build(
        self, mock_static_sources, mock_filename, mock_schema, mock_static_catalog
    ):
        test_country_code = "some_country_code"
        test_subdivision_name = "some_subdivision_name"
        test_static_source = MagicMock()
        test_static_source.country_code = test_country_code
        test_static_source.subdivision_name = test_subdivision_name
        mock_static_sources.return_value = [test_static_source]

        mock_filename.return_value = "some_filename"
        mock_schema.return_value = self.test_schema
        del self.test_kwargs[DATA_TYPE]
        under_test = GtfsRealtimeSource.build(**self.test_kwargs)
        self.assertIsNotNone(under_test)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    def test_schematize(self, mock_static_catalog):
        under_test = GtfsRealtimeSource.schematize(**self.test_kwargs)
        self.assertDictEqual(under_test, self.test_schema)

        del self.test_kwargs[NAME]
        del self.test_kwargs[NOTE]
        del self.test_kwargs[STATIC_REFERENCE]
        del self.test_kwargs[AUTHENTICATION_INFO]
        del self.test_kwargs[API_KEY_PARAMETER_NAME]
        del self.test_kwargs[LICENSE]
        del self.test_schema[NAME]
        del self.test_schema[NOTE]
        del self.test_schema[STATIC_REFERENCE]
        del self.test_schema[URLS][AUTHENTICATION_INFO]
        del self.test_schema[URLS][API_KEY_PARAMETER_NAME]
        del self.test_schema[URLS][LICENSE]
        under_test = GtfsRealtimeSource.schematize(**self.test_kwargs)
        self.assertDictEqual(under_test, self.test_schema)

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    def test_get_static_sources(self, mock_static_catalog):
        test_static_source = "some_static_source"
        test_another_static_source = "another_static_source"
        mock_static_catalog.get_source.side_effect = [
            test_static_source,
            test_another_static_source,
        ]
        under_test = GtfsRealtimeSource.get_static_sources(self.test_static_reference)
        self.assertEqual(under_test, [test_static_source, test_another_static_source])

        test_empty_static_reference = None
        under_test = GtfsRealtimeSource.get_static_sources(test_empty_static_reference)
        self.assertEqual(under_test, [])

    @patch("tools.representations.GtfsRealtimeSource.static_catalog")
    @patch("tools.representations.GtfsRealtimeSource.__str__")
    @patch("tools.representations.json.loads")
    def test_as_json(self, mock_json, mock_str, mock_static_catalog):
        test_json = {"some_json_key": "some_json_value"}
        mock_json.return_value = test_json
        instance = GtfsRealtimeSource(filename=self.test_filename, **self.test_schema)
        under_test = instance.as_json()
        self.assertEqual(under_test, test_json)
        mock_json.assert_called_once()
        mock_str.assert_called_once()
