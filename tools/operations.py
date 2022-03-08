import os
from tools.constants import (
    GTFS,
    GTFS_RT,
    NAME,
    AGENCY,
    COUNTRY_CODE,
    SUBDIVISION_NAME,
    MUNICIPALITY,
    AUTO_DISCOVERY,
    LICENSE,
    STATIC_REFERENCE,
    REALTIME_VEHICLE_POSITIONS,
    REALTIME_TRIP_UPDATES,
    REALTIME_ALERTS,
    CATALOGS,
    ALL,
    MDB_SOURCE_ID,
)
from tools.representations import GtfsScheduleSourcesCatalog, GtfsRealtimeSourcesCatalog

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

GTFS_MAP = {CATALOGS: ["GtfsScheduleSourcesCatalog"]}

GTFS_RT_MAP = {CATALOGS: ["GtfsRealtimeSourcesCatalog"]}

ALL_MAP = {CATALOGS: ["GtfsScheduleSourcesCatalog", "GtfsRealtimeSourcesCatalog"]}


def add_gtfs_realtime_source(
    agency,
    static_reference=None,
    vehicle_positions_url=None,
    trip_updates_url=None,
    service_alerts_url=None,
    name=None,
):
    """Add a new GTFS Realtime source to the Mobility Catalogs."""
    catalog = GtfsRealtimeSourcesCatalog()
    data = {
        AGENCY: agency,
        STATIC_REFERENCE: static_reference,
        REALTIME_VEHICLE_POSITIONS: vehicle_positions_url,
        REALTIME_TRIP_UPDATES: trip_updates_url,
        REALTIME_ALERTS: service_alerts_url,
        NAME: name,
    }
    catalog.add(**data)
    return catalog


def update_gtfs_realtime_source(
    mdb_source_id,
    agency=None,
    static_reference=None,
    vehicle_positions_url=None,
    trip_updates_url=None,
    service_alerts_url=None,
    name=None,
):
    """Update a new GTFS Realtime source to the Mobility Catalogs."""
    catalog = GtfsRealtimeSourcesCatalog()
    data = {
        MDB_SOURCE_ID: mdb_source_id,
        AGENCY: agency,
        STATIC_REFERENCE: static_reference,
        REALTIME_VEHICLE_POSITIONS: vehicle_positions_url,
        REALTIME_TRIP_UPDATES: trip_updates_url,
        REALTIME_ALERTS: service_alerts_url,
        NAME: name,
    }
    catalog.update(**data)
    return catalog


def add_gtfs_schedule_source(
    agency,
    country_code,
    subdivision_name,
    municipality,
    auto_discovery_url,
    license_url=None,
    name=None,
):
    """Add a new GTFS Schedule source to the Mobility Catalogs."""
    catalog = GtfsScheduleSourcesCatalog()
    data = {
        AGENCY: agency,
        COUNTRY_CODE: country_code,
        SUBDIVISION_NAME: subdivision_name,
        MUNICIPALITY: municipality,
        AUTO_DISCOVERY: auto_discovery_url,
        LICENSE: license_url,
        NAME: name,
    }
    catalog.add(**data)
    return catalog


def update_gtfs_schedule_source(
    mdb_source_id,
    agency=None,
    name=None,
    country_code=None,
    subdivision_name=None,
    municipality=None,
    auto_discovery_url=None,
    license_url=None,
):
    """Update a GTFS Schedule source in the Mobility Catalogs."""
    catalog = GtfsScheduleSourcesCatalog()
    data = {
        MDB_SOURCE_ID: mdb_source_id,
        AGENCY: agency,
        COUNTRY_CODE: country_code,
        SUBDIVISION_NAME: subdivision_name,
        MUNICIPALITY: municipality,
        AUTO_DISCOVERY: auto_discovery_url,
        LICENSE: license_url,
        NAME: name,
    }
    catalog.update(**data)
    return catalog


def get_sources(data_type=ALL):
    """Get the sources of the Mobility Catalogs."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(globals()[f"{catalog_cls}"]().get_sources())
    return dict(sorted(sources.items()))


def get_sources_by_bounding_box(
    minimum_latitude,
    maximum_latitude,
    minimum_longitude,
    maximum_longitude,
    data_type=ALL,
):
    """Get the sources included in the geographical bounding box."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_bounding_box(
                minimum_latitude=minimum_latitude,
                maximum_latitude=maximum_latitude,
                minimum_longitude=minimum_longitude,
                maximum_longitude=maximum_longitude,
            )
        )
    return dict(sorted(sources.items()))


def get_sources_by_subdivision_name(
    subdivision_name,
    data_type=ALL,
):
    """Get the sources located at the given subdivision name."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_subdivision_name(
                subdivision_name=subdivision_name
            )
        )
    return dict(sorted(sources.items()))


def get_sources_by_country_code(
    country_code,
    data_type=ALL,
):
    """Get the sources located at the given country code."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_country_code(
                country_code=country_code
            )
        )
    return dict(sorted(sources.items()))


def get_latest_datasets(data_type=ALL):
    """Get latest datasets of the Mobility Catalogs."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(globals()[f"{catalog_cls}"]().get_latest_datasets())
    return dict(sorted(sources.items()))
