from unittest import TestCase, skip
from unittest.mock import patch
from mobilitydb.tools.operations import (
    ALL,
    add_gtfs_realtime_source,
    update_gtfs_realtime_source,
    add_gtfs_schedule_source,
    update_gtfs_schedule_source,
    get_sources,
    get_sources_by_bounding_box,
    get_sources_by_subdivision_name,
    get_sources_by_country_code,
    get_latest_datasets,
    CATALOGS,
)


class TestOperations(TestCase):
    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    def test_add_gtfs_realtime_source(self, mock_catalog):
        test_provider = "test_provider"
        test_name = "test_name"
        test_static_reference = "test_static_reference"
        test_vehicle_positions_url = "test_vehicle_positions_url"
        test_trip_updates_url = "test_trip_updates_url"
        test_service_alerts_url = "test_service_alerts_url"
        under_test = add_gtfs_realtime_source(
            provider=test_provider,
            name=test_name,
            static_reference=test_static_reference,
            vehicle_positions_url=test_vehicle_positions_url,
            trip_updates_url=test_trip_updates_url,
            service_alerts_url=test_service_alerts_url,
        )
        self.assertEqual(under_test, mock_catalog())
        self.assertEqual(mock_catalog.call_count, 2)
        self.assertEqual(mock_catalog().add.call_count, 1)

    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    def test_update_gtfs_realtime_source(self, mock_catalog):
        test_mdb_source_id = "test_mdb_source_id"
        test_provider = "test_provider"
        test_name = "test_name"
        test_static_reference = "test_static_reference"
        test_vehicle_positions_url = "test_vehicle_positions_url"
        test_trip_updates_url = "test_trip_updates_url"
        test_service_alerts_url = "test_service_alerts_url"
        under_test = update_gtfs_realtime_source(
            mdb_source_id=test_mdb_source_id,
            provider=test_provider,
            name=test_name,
            static_reference=test_static_reference,
            vehicle_positions_url=test_vehicle_positions_url,
            trip_updates_url=test_trip_updates_url,
            service_alerts_url=test_service_alerts_url,
        )
        self.assertEqual(under_test, mock_catalog())
        self.assertEqual(mock_catalog.call_count, 2)
        self.assertEqual(mock_catalog().update.call_count, 1)

    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_add_gtfs_schedule_source(self, mock_catalog):
        test_provider = "test_provider"
        test_name = "test_name"
        test_country_code = "test_country_code"
        test_subdivision_name = "test_subdivision_name"
        test_municipality = "test_municipality"
        test_direct_download_url = "test_direct_download_url"
        test_license_url = "test_license_url"
        under_test = add_gtfs_schedule_source(
            provider=test_provider,
            name=test_name,
            country_code=test_country_code,
            subdivision_name=test_subdivision_name,
            municipality=test_municipality,
            direct_download_url=test_direct_download_url,
            license_url=test_license_url,
        )
        self.assertEqual(under_test, mock_catalog())
        self.assertEqual(mock_catalog.call_count, 2)
        self.assertEqual(mock_catalog().add.call_count, 1)

    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_update_gtfs_schedule_source(self, mock_catalog):
        test_mdb_source_id = "test_mdb_source_id"
        test_provider = "test_provider"
        test_name = "test_name"
        test_country_code = "test_country_code"
        test_subdivision_name = "test_subdivision_name"
        test_municipality = "test_municipality"
        test_direct_download_url = "test_direct_download_url"
        test_license_url = "test_license_url"
        under_test = update_gtfs_schedule_source(
            mdb_source_id=test_mdb_source_id,
            provider=test_provider,
            name=test_name,
            country_code=test_country_code,
            subdivision_name=test_subdivision_name,
            municipality=test_municipality,
            direct_download_url=test_direct_download_url,
            license_url=test_license_url,
        )
        self.assertEqual(under_test, mock_catalog())
        self.assertEqual(mock_catalog.call_count, 2)
        self.assertEqual(mock_catalog().update.call_count, 1)

    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_get_sources(self, mock_schedule_catalog, mock_realtime_catalog):
        under_test = get_sources(data_type=ALL)
        self.assertEqual(mock_schedule_catalog.call_count, 1)
        self.assertEqual(mock_schedule_catalog().get_sources.call_count, 1)
        self.assertEqual(mock_realtime_catalog.call_count, 1)
        self.assertEqual(mock_realtime_catalog().get_sources.call_count, 1)

    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_get_sources_by_bounding_box(
        self, mock_schedule_catalog, mock_realtime_catalog
    ):
        test_min_lat = "test_min_lat"
        test_max_lat = "test_max_lat"
        test_min_lon = "test_min_lon"
        test_max_lon = "test_max_lon"
        under_test = get_sources_by_bounding_box(
            minimum_latitude=test_min_lat,
            maximum_latitude=test_max_lat,
            minimum_longitude=test_min_lon,
            maximum_longitude=test_max_lon,
            data_type=ALL,
        )
        self.assertEqual(mock_schedule_catalog.call_count, 1)
        self.assertEqual(
            mock_schedule_catalog().get_sources_by_bounding_box.call_count, 1
        )
        self.assertEqual(mock_realtime_catalog.call_count, 1)
        self.assertEqual(
            mock_realtime_catalog().get_sources_by_bounding_box.call_count, 1
        )

    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_get_sources_by_subdivision_name(
        self, mock_schedule_catalog, mock_realtime_catalog
    ):
        test_subdivision_name = "test_subdivision_name"
        under_test = get_sources_by_subdivision_name(
            subdivision_name=test_subdivision_name, data_type=ALL
        )
        self.assertEqual(mock_schedule_catalog.call_count, 1)
        self.assertEqual(
            mock_schedule_catalog().get_sources_by_subdivision_name.call_count, 1
        )
        self.assertEqual(mock_realtime_catalog.call_count, 1)
        self.assertEqual(
            mock_realtime_catalog().get_sources_by_subdivision_name.call_count, 1
        )

    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_get_sources_by_country_code(
        self, mock_schedule_catalog, mock_realtime_catalog
    ):
        test_country_code = "test_country_code"
        under_test = get_sources_by_country_code(
            country_code=test_country_code, data_type=ALL
        )
        self.assertEqual(mock_schedule_catalog.call_count, 1)
        self.assertEqual(
            mock_schedule_catalog().get_sources_by_country_code.call_count, 1
        )
        self.assertEqual(mock_realtime_catalog.call_count, 1)
        self.assertEqual(
            mock_realtime_catalog().get_sources_by_country_code.call_count, 1
        )

    @patch("tools.operations.GtfsRealtimeSourcesCatalog", autospec=True)
    @patch("tools.operations.GtfsScheduleSourcesCatalog", autospec=True)
    def test_get_latest_datasets(self, mock_schedule_catalog, mock_realtime_catalog):
        under_test = get_latest_datasets(data_type=ALL)
        self.assertEqual(mock_schedule_catalog.call_count, 1)
        self.assertEqual(mock_schedule_catalog().get_latest_datasets.call_count, 1)
        self.assertEqual(mock_realtime_catalog.call_count, 1)
        self.assertEqual(mock_realtime_catalog().get_latest_datasets.call_count, 1)
