import os
from tools.helpers import (
    is_readable,
    extract_gtfs_bounding_box,
    to_json,
    from_json,
    get_iso_time,
    find_file,
)
from tools.constants import (
    GTFS,
    GTFS_RT,
    LOAD_FUNC,
    SOURCE_CATALOG_PATH_FROM_ROOT,
    NAME,
    PROVIDER,
    LOCATION,
    COUNTRY_CODE,
    SUBDIVISION_NAME,
    MUNICIPALITY,
    BOUNDING_BOX,
    MINIMUM_LATITUDE,
    MAXIMUM_LATITUDE,
    MINIMUM_LONGITUDE,
    MAXIMUM_LONGITUDE,
    EXTRACTED_ON,
    URLS,
    AUTO_DISCOVERY,
    LICENSE,
    STATIC_REFERENCE,
    REALTIME_VEHICLE_POSITIONS,
    REALTIME_TRIP_UPDATES,
    REALTIME_ALERTS,
    CATALOGS,
    ALL,
)
from tools.representations import GtfsScheduleSourcesCatalog, GtfsRealtimeSourcesCatalog

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

GTFS_MAP = {CATALOGS: [GtfsScheduleSourcesCatalog]}

GTFS_RT_MAP = {CATALOGS: [GtfsRealtimeSourcesCatalog]}

ALL_MAP = {CATALOGS: [GtfsScheduleSourcesCatalog, GtfsRealtimeSourcesCatalog]}


def add_gtfs_realtime_source(
    provider,
    static_reference=None,
    vehicle_positions_url=None,
    trip_updates_url=None,
    service_alerts_url=None,
    name=None,
):
    """Add a new GTFS Rsource to the Mobility Catalogs."""
    catalog = GtfsRealtimeSourcesCatalog()
    data = {
        PROVIDER: provider,
        STATIC_REFERENCE: static_reference,
        REALTIME_VEHICLE_POSITIONS: vehicle_positions_url,
        REALTIME_TRIP_UPDATES: trip_updates_url,
        REALTIME_ALERTS: service_alerts_url,
        NAME: name,
    }
    catalog.add(**data)
    return catalog


def add_gtfs_schedule_source(
    provider,
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
        PROVIDER: provider,
        COUNTRY_CODE: country_code,
        SUBDIVISION_NAME: subdivision_name,
        MUNICIPALITY: municipality,
        AUTO_DISCOVERY: auto_discovery_url,
        LICENSE: license_url,
        NAME: name,
    }
    catalog.add(**data)
    return catalog


def update_source(
    mdb_source_id,
    provider=None,
    name=None,
    country_code=None,
    subdivision_name=None,
    municipality=None,
    auto_discovery_url=None,
    license_url=None,
    data_type=GTFS,
):
    """Update a source in the Mobility Catalogs."""
    data_type_map = globals()[f"{data_type.upper()}_MAP"]
    source_path = find_file(
        catalog_root=os.path.join(PROJECT_ROOT, SOURCE_CATALOG_PATH_FROM_ROOT),
        mdb_id=mdb_source_id,
    )
    source = from_json(path=source_path)

    if auto_discovery_url is not None and is_readable(
        url=auto_discovery_url, load_func=data_type_map[LOAD_FUNC]
    ):
        source[URLS][AUTO_DISCOVERY] = auto_discovery_url
        (
            source[LOCATION][BOUNDING_BOX][MINIMUM_LATITUDE],
            source[LOCATION][BOUNDING_BOX][MAXIMUM_LATITUDE],
            source[LOCATION][BOUNDING_BOX][MINIMUM_LONGITUDE],
            source[LOCATION][BOUNDING_BOX][MAXIMUM_LONGITUDE],
        ) = extract_gtfs_bounding_box(url=auto_discovery_url)
        source[BOUNDING_BOX][EXTRACTED_ON] = get_iso_time()
    if provider is not None:
        source[PROVIDER] = provider
    if name is not None:
        source[NAME] = name
    if country_code is not None:
        source[LOCATION][COUNTRY_CODE] = country_code
    if subdivision_name is not None:
        source[LOCATION][SUBDIVISION_NAME] = SUBDIVISION_NAME
    if municipality is not None:
        source[LOCATION][MUNICIPALITY] = municipality
    if license_url is not None:
        source[URLS][LICENSE] = license_url

    to_json(path=source_path, obj=source)
    return source


def get_sources(data_type=ALL):
    """Get the sources of the Mobility Catalogs."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        catalog = catalog_cls()
        sources.update(catalog.get_sources())
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
        catalog = catalog_cls()
        sources.update(
            catalog.get_sources_by_bounding_box(
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
        catalog = catalog_cls()
        sources.update(
            catalog.get_sources_by_subdivision_name(subdivision_name=subdivision_name)
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
        catalog = catalog_cls()
        sources.update(catalog.get_sources_by_country_code(country_code=country_code))
    return dict(sorted(sources.items()))


def get_latest_datasets(data_type=ALL):
    """Get latest datasets of the Mobility Catalogs."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        catalog = catalog_cls()
        sources.update(catalog.get_latest_datasets())
    return dict(sorted(sources.items()))
