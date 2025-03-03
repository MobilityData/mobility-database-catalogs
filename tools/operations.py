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
    IS_OFFICIAL
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
    is_official=None,
):
    """
    Add a new GTFS Realtime source to the Mobility Catalogs.

    This function creates a new GTFS Realtime source entity with the provided details and adds it
    to the GTFS Realtime Sources Catalog.

    Args:
        entity_type (str): The type of the entity.
        provider (str): The provider of the GTFS Realtime source.
        direct_download_url (str): The direct download URL for the GTFS Realtime data.
        authentication_type (str, optional): The type of authentication required. Defaults to None.
        authentication_info_url (str, optional): The URL for authentication information. Defaults to None.
        api_key_parameter_name (str, optional): The name of the API key parameter. Defaults to None.
        license_url (str, optional): The URL for the license. Defaults to None.
        name (str, optional): The name of the GTFS Realtime source. Defaults to None.
        static_reference (str, optional): A static reference related to the source. Defaults to None.
        note (str, optional): Additional notes regarding the source. Defaults to None.
        status (str, optional): The status of the GTFS Realtime source. Defaults to None.
        features (list, optional): A list of features of the GTFS Realtime source. Defaults to None.
        is_official (str, optional): Flag indicating if the source comes from the agency itself or not. Defaults to None.
    
    Returns:
        GtfsRealtimeSourcesCatalog: The catalog with the newly added GTFS Realtime source.
    """
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
        IS_OFFICIAL: is_official
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
    is_official = None,
):
    """
    Update an existing GTFS Realtime source in the Mobility Catalogs.

    This function updates an existing GTFS Realtime source entity with the provided details in the
    GTFS Realtime Sources Catalog.

    Args:
        mdb_source_id (str): The MDB source ID of the GTFS Realtime source to update.
        entity_type (str, optional): The type of the entity. Defaults to None.
        provider (str, optional): The provider of the GTFS Realtime source. Defaults to None.
        direct_download_url (str, optional): The direct download URL for the GTFS Realtime data. Defaults to None.
        authentication_type (str, optional): The type of authentication required. Defaults to None.
        authentication_info_url (str, optional): The URL for authentication information. Defaults to None.
        api_key_parameter_name (str, optional): The name of the API key parameter. Defaults to None.
        license_url (str, optional): The URL for the license. Defaults to None.
        name (str, optional): The name of the GTFS Realtime source. Defaults to None.
        static_reference (str, optional): A static reference related to the source. Defaults to None.
        note (str, optional): Additional notes regarding the source. Defaults to None.
        status (str, optional): The status of the GTFS Realtime source. Defaults to None.
        features (list, optional): A list of features of the GTFS Realtime source. Defaults to None.
        is_official (str, optional): Flag indicating if the source comes from the agency itself or not. Defaults to None.
        
    Returns:
        GtfsRealtimeSourcesCatalog: The catalog with the updated GTFS Realtime source.
    """
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
        IS_OFFICIAL: is_official,
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
    is_official=None,
):
    """
    Add a new GTFS Schedule source to the Mobility Catalogs.

    This function creates a new GTFS Schedule source entity with the provided details and adds it
    to the GTFS Schedule Sources Catalog.

    Args:
        provider (str): The provider of the GTFS Schedule source.
        country_code (str): The country code of the GTFS Schedule source.
        direct_download_url (str): The direct download URL for the GTFS Schedule data.
        authentication_type (str, optional): The type of authentication required. Defaults to None.
        authentication_info_url (str, optional): The URL for authentication information. Defaults to None.
        api_key_parameter_name (str, optional): The name of the API key parameter. Defaults to None.
        api_key_parameter_value (str, optional): The value of the API key parameter. Defaults to None.
        subdivision_name (str, optional): The subdivision name for the source. Defaults to None.
        municipality (str, optional): The municipality for the source. Defaults to None.
        license_url (str, optional): The URL for the license. Defaults to None.
        name (str, optional): The name of the GTFS Schedule source. Defaults to None.
        status (str, optional): The status of the GTFS Schedule source. Defaults to None.
        features (list, optional): A list of features of the GTFS Schedule source. Defaults to None.
        feed_contact_email (str, optional): The contact email for the feed. Defaults to None.
        redirects (list, optional): A list of redirect information for the source. Each redirect should be a dict with 'id' (str) and 'comment' (str). Defaults to None.
        is_official (str, optional): Flag indicating if the source comes from the agency itself or not. Defaults to None.
    Returns:
        GtfsScheduleSourcesCatalog: The catalog with the newly added GTFS Schedule source.
    """
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
        IS_OFFICIAL: is_official,
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
    is_official=None,
):
    """
    Update a GTFS Schedule source in the Mobility Catalogs.

    This function updates an existing GTFS Schedule source entity with the provided details in the
    GTFS Schedule Sources Catalog.

    Args:
        mdb_source_id (str): The MDB source ID of the GTFS Schedule source to update.
        provider (str, optional): The provider of the GTFS Schedule source. Defaults to None.
        name (str, optional): The name of the GTFS Schedule source. Defaults to None.
        country_code (str, optional): The country code of the GTFS Schedule source. Defaults to None.
        subdivision_name (str, optional): The subdivision name for the source. Defaults to None.
        municipality (str, optional): The municipality for the source. Defaults to None.
        direct_download_url (str, optional): The direct download URL for the GTFS Schedule data. Defaults to None.
        authentication_type (str, optional): The type of authentication required. Defaults to None.
        authentication_info_url (str, optional): The URL for authentication information. Defaults to None.
        api_key_parameter_name (str, optional): The name of the API key parameter. Defaults to None.
        api_key_parameter_value (str, optional): The value of the API key parameter. Defaults to None.
        license_url (str, optional): The URL for the license. Defaults to None.
        status (str, optional): The status of the GTFS Schedule source. Defaults to None.
        features (list, optional): A list of features of the GTFS Schedule source. Defaults to None.
        feed_contact_email (str, optional): The contact email for the feed. Defaults to None.
        redirects (list, optional): A list of redirect information for the source. Each redirect should be a dict with 'id' (str) and 'comment' (str). Defaults to None.
        is_official (str, optional): Flag indicating if the source comes from the agency itself or not. Defaults to None.
    Returns:
        GtfsScheduleSourcesCatalog: The catalog with the updated GTFS Schedule source.
    """
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
        IS_OFFICIAL: is_official,
    }
    catalog.update(**data)
    return catalog


def get_sources(data_type=ALL):
    """
    Get the sources of the Mobility Catalogs.

    This function retrieves sources from the specified data type in the Mobility Catalogs.

    Args:
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL. 
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources from the specified catalog.
    """
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
    """
    Get the sources included in the geographical bounding box.

    This function retrieves sources from the specified data type in the Mobility Catalogs
    that are within the given geographical bounding box.

    Args:
        minimum_latitude (float): The minimum latitude of the bounding box.
        maximum_latitude (float): The maximum latitude of the bounding box.
        minimum_longitude (float): The minimum longitude of the bounding box.
        maximum_longitude (float): The maximum longitude of the bounding box.
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources within the specified bounding box from the specified catalog.
    """
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
    """
    Get the sources located at the given subdivision name.

    This function retrieves sources from the specified data type in the Mobility Catalogs
    that are located within the given subdivision name.

    Args:
        subdivision_name (str): The name of the subdivision to retrieve sources for.
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources within the specified subdivision from the specified catalog.
    """
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
    """
    Get the sources located at the given country code.

    This function retrieves sources from the specified data type in the Mobility Catalogs
    that are located within the given country code.

    Args:
        country_code (str): The country code to retrieve sources for.
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources within the specified country from the specified catalog.
    """
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
    """
    Get latest datasets of the Mobility Catalogs.

    This function retrieves the latest datasets from the specified data type in the Mobility Catalogs.

    Args:
        data_type (str, optional): The type of data to retrieve datasets for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted latest datasets from the specified catalog.
    """
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(globals()[f"{catalog_cls}"]().get_latest_datasets())
    return dict(sorted(sources.items()))


def get_sources_by_status(
    status,
    data_type=ALL,
):
    """
    Get the sources with the given status.

    This function retrieves sources from the specified data type in the Mobility Catalogs
    that have the given status.

    Args:
        status (str): The status to filter sources by.
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources with the specified status from the specified catalog.
    """
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
    """
    Get the sources with the given feature.

    This function retrieves sources from the specified data type in the Mobility Catalogs
    that have the given feature.

    Args:
        feature (str): The feature to filter sources by.
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources with the specified feature from the specified catalog.
    """
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_feature(feature=feature)
        )
    return dict(sorted(sources.items()))

def get_sources_by_is_official(
    is_official,
    data_type=ALL,
):
    """
    Get the sources with the given is_offical flag.

    This function retrieves sources from the specified data type in the Mobility Catalogs
    that have the given is_official flag.

    Args:
        is_official (str): The feature to filter sources by.
        data_type (str, optional): The type of data to retrieve sources for. Defaults to ALL.
            Possible values are 'ALL', 'GTFS', 'GTFS-RT', etc.

    Returns:
        dict: A dictionary of sorted sources with the specified is_official flag from the specified catalog.
    """
    source_type_map = globals()[f"{data_type.upper().replace('-', '_')}_MAP"]
    sources = {}
    for catalog_cls in source_type_map[CATALOGS]:
        sources.update(
            globals()[f"{catalog_cls}"]().get_sources_by_is_official(is_official=is_official)
        )
    return dict(sorted(sources.items()))