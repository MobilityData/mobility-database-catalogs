import os
from tools.constants import (
    NAME,
    PROVIDER,
    COUNTRY_CODE,
    SUBDIVISION_NAME,
    MUNICIPALITY,
    FEATURES,
    STATUS,
    DIRECT_DOWNLOAD,
    LICENSE,
    STATIC_REFERENCE,
    AUTHENTICATION_TYPE,
    AUTHENTICATION_INFO,
    API_KEY_PARAMETER_NAME,
    API_KEY_PARAMETER_VALUE,
    NOTE,
    ENTITY_TYPE,
    CATALOGS,
    ALL,
    MDB_SOURCE_ID,
    FEED_CONTACT_EMAIL,
    REDIRECTS,
)
from tools.representations import GtfsScheduleSourcesCatalog, GtfsRealtimeSourcesCatalog

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

GTFS_MAP = {CATALOGS: ["GtfsScheduleSourcesCatalog"]}

GTFS_RT_MAP = {CATALOGS: ["GtfsRealtimeSourcesCatalog"]}

ALL_MAP = {CATALOGS: ["GtfsScheduleSourcesCatalog", "GtfsRealtimeSourcesCatalog"]}


def add_gtfs_realtime_source(
    entity_type,
    provider,
    direct_download_url,
    authentication_type=None,
    authentication_info_url=None,
    api_key_parameter_name=None,
    license_url=None,
    name=None,
    static_reference=None,
    note=None,
    status=None,
    features=None,
):
    """Add a new GTFS Realtime source to the Mobility Catalogs."""
    catalog = GtfsRealtimeSourcesCatalog()
    data = {
        ENTITY_TYPE: entity_type,
        PROVIDER: provider,
        NAME: name,
        STATIC_REFERENCE: static_reference,
        NOTE: note,
        DIRECT_DOWNLOAD: direct_download_url,
        AUTHENTICATION_TYPE: authentication_type,
        AUTHENTICATION_INFO: authentication_info_url,
        API_KEY_PARAMETER_NAME: api_key_parameter_name,
        LICENSE: license_url,
        STATUS: status,
        FEATURES: features,
    }
    catalog.add(**data)
    return catalog


def update_gtfs_realtime_source(
    mdb_source_id,
    entity_type=None,
    provider=None,
    direct_download_url=None,
    authentication_type=None,
    authentication_info_url=None,
    api_key_parameter_name=None,
    license_url=None,
    name=None,
    static_reference=None,
    note=None,
    status=None,
    features=None,
):
    """Update a new GTFS Realtime source to the Mobility Catalogs."""
    catalog = GtfsRealtimeSourcesCatalog()
    data = {
        MDB_SOURCE_ID: mdb_source_id,
        ENTITY_TYPE: entity_type,
        PROVIDER: provider,
        NAME: name,
        STATIC_REFERENCE: static_reference,
        NOTE: note,
        DIRECT_DOWNLOAD: direct_download_url,
        AUTHENTICATION_TYPE: authentication_type,
        AUTHENTICATION_INFO: authentication_info_url,
        API_KEY_PARAMETER_NAME: api_key_parameter_name,
        LICENSE: license_url,
        STATUS: status,
        FEATURES: features,
    }
    catalog.update(**data)
    return catalog


def add_gtfs_schedule_source(
    provider,
    country_code,
    direct_download_url,
    authentication_type=None,
    authentication_info_url=None,
    api_key_parameter_name=None,
    api_key_parameter_value=None,
    subdivision_name=None,
    municipality=None,
    license_url=None,
    name=None,
    status=None,
    features=None,
    feed_contact_email=None,
    redirects=None,
):
    """Add a new GTFS Schedule source to the Mobility Catalogs."""
    catalog = GtfsScheduleSourcesCatalog()
    data = {
        PROVIDER: provider,
        COUNTRY_CODE: country_code,
        SUBDIVISION_NAME: subdivision_name,
        MUNICIPALITY: municipality,
        DIRECT_DOWNLOAD: direct_download_url,
        AUTHENTICATION_TYPE: authentication_type,
        AUTHENTICATION_INFO: authentication_info_url,
        API_KEY_PARAMETER_NAME: api_key_parameter_name,
        API_KEY_PARAMETER_VALUE: api_key_parameter_value,
        LICENSE: license_url,
        NAME: name,
        STATUS: status,
        FEATURES: features,
        FEED_CONTACT_EMAIL: feed_contact_email,
        REDIRECTS: redirects,
    }
    catalog.add(**data)
    return catalog


def update_gtfs_schedule_source(
    mdb_source_id,
    provider=None,
    name=None,
    country_code=None,
    subdivision_name=None,
    municipality=None,
    direct_download_url=None,
    authentication_type=None,
    authentication_info_url=None,
    api_key_parameter_name=None,
    api_key_parameter_value=None,
    license_url=None,
    status=None,
    features=None,
    feed_contact_email=None,
    redirects=None,
):
    """Update a GTFS Schedule source in the Mobility Catalogs."""
    catalog = GtfsScheduleSourcesCatalog()
    data = {
        MDB_SOURCE_ID: mdb_source_id,
        PROVIDER: provider,
        COUNTRY_CODE: country_code,
        SUBDIVISION_NAME: subdivision_name,
        MUNICIPALITY: municipality,
        DIRECT_DOWNLOAD: direct_download_url,
        AUTHENTICATION_TYPE: authentication_type,
        AUTHENTICATION_INFO: authentication_info_url,
        API_KEY_PARAMETER_NAME: api_key_parameter_name,
        API_KEY_PARAMETER_VALUE: api_key_parameter_value,
        LICENSE: license_url,
        NAME: name,
        STATUS: status,
        FEATURES: features,
        FEED_CONTACT_EMAIL: feed_contact_email,
        REDIRECTS: redirects,
    }
    catalog.update(**data)
    return catalog


def get_sources(data_type=ALL):
    """Get the sources of the Mobility Catalogs."""
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
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
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
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
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
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
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
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
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(globals()[f"{catalog_cls}"]().get_latest_datasets())
    return dict(sorted(sources.items()))


def get_sources_by_status(
    status,
    data_type=ALL,
):
    """Get the sources with the given status."""
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_status(status=status)
        )
    return dict(sorted(sources.items()))


def get_sources_by_feature(
    feature,
    data_type=ALL,
):
    """Get the sources with the given feature."""
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_feature(feature=feature)
        )
    return dict(sorted(sources.items()))
