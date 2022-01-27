import os
from tools.helpers import (
    aggregate,
    is_readable,
    identify_source,
    extract_gtfs_bounding_box,
    are_overlapping_boxes,
    load_gtfs,
    create_latest_url,
    to_json,
    from_json,
)
from tools.constants import (
    STATIC,
    GTFS,
    PATH_FROM_ROOT,
    LOAD_FUNC,
    STATIC_CATALOG_PATH_FROM_ROOT,
    GTFS_CATALOG_PATH_FROM_ROOT,
    EXTENSION,
    ZIP,
    JSON,
    MDB_SOURCE_ID,
    NAME,
    LOCATION,
    COUNTRY_CODE,
    BOUNDING_BOX,
    MINIMUM_LATITUDE,
    MAXIMUM_LATITUDE,
    MINIMUM_LONGITUDE,
    MAXIMUM_LONGITUDE,
    DATA_TYPE,
    URLS,
    AUTO_DISCOVERY,
    LICENSE,
    LATEST,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

STATIC_MAP = {PATH_FROM_ROOT: STATIC_CATALOG_PATH_FROM_ROOT}

GTFS_MAP = {
    PATH_FROM_ROOT: GTFS_CATALOG_PATH_FROM_ROOT,
    LOAD_FUNC: load_gtfs.__name__,
    EXTENSION: ZIP,
}


def add_source(
    name, location, country_code, auto_discovery_url, license_url, data_type=GTFS
):
    """Add a new source to the Mobility Catalogs."""
    data_type_map = globals()[f"{data_type.upper()}_MAP"]
    if is_readable(url=auto_discovery_url, load_func=data_type_map[LOAD_FUNC]):
        mdb_source_id = identify_source(
            name=name, country_code=country_code, data_type=data_type
        )
        (
            minimum_latitude,
            maximum_latitude,
            minimum_longitude,
            maximum_longitude,
        ) = extract_gtfs_bounding_box(url=auto_discovery_url)
        latest_url = create_latest_url(
            mdb_source_id=mdb_source_id, extension=data_type_map[EXTENSION]
        )

        source = {
            MDB_SOURCE_ID: mdb_source_id,
            NAME: name,
            LOCATION: location,
            COUNTRY_CODE: country_code,
            BOUNDING_BOX: {
                MINIMUM_LATITUDE: minimum_latitude,
                MAXIMUM_LATITUDE: maximum_latitude,
                MINIMUM_LONGITUDE: minimum_longitude,
                MAXIMUM_LONGITUDE: maximum_longitude,
            },
            DATA_TYPE: data_type,
            URLS: {
                AUTO_DISCOVERY: auto_discovery_url,
                LICENSE: license_url,
                LATEST: latest_url,
            },
        }
        to_json(
            path=os.path.join(
                PROJECT_ROOT, data_type_map[PATH_FROM_ROOT], f"{mdb_source_id}.{JSON}"
            ),
            obj=source,
        )
        return source


def update_source(
    mdb_source_id,
    name=None,
    location=None,
    country_code=None,
    auto_discovery_url=None,
    license_url=None,
    data_type=GTFS,
):
    """Update a source in the Mobility Catalogs."""
    data_type_map = globals()[f"{data_type.upper()}_MAP"]
    source_path = os.path.join(
        PROJECT_ROOT, data_type_map[PATH_FROM_ROOT], f"{mdb_source_id}.{JSON}"
    )
    source = from_json(path=source_path)

    if auto_discovery_url is not None and is_readable(
        url=auto_discovery_url, load_func=data_type_map[LOAD_FUNC]
    ):
        source[URLS][AUTO_DISCOVERY] = auto_discovery_url
        (
            source[BOUNDING_BOX][MINIMUM_LATITUDE],
            source[BOUNDING_BOX][MAXIMUM_LATITUDE],
            source[BOUNDING_BOX][MINIMUM_LONGITUDE],
            source[BOUNDING_BOX][MAXIMUM_LONGITUDE],
        ) = extract_gtfs_bounding_box(url=auto_discovery_url)
    if name is not None:
        source[NAME] = name
    if location is not None:
        source[LOCATION] = location
    if country_code is not None:
        source[COUNTRY_CODE] = country_code
    if license_url is not None:
        source[URLS][LICENSE] = license_url

    to_json(path=source_path, obj=source)
    return source


def get_sources(source_type=STATIC):
    """Get the sources of the Mobility Catalogs."""
    source_type_map = globals()[f"{source_type.upper()}_MAP"]
    catalog_root = os.path.join(PROJECT_ROOT, source_type_map[PATH_FROM_ROOT])
    return aggregate(catalog_root)


def get_sources_by_bounding_box(
    minimum_latitude,
    maximum_latitude,
    minimum_longitude,
    maximum_longitude,
    source_type=STATIC,
):
    """Get the sources included in the geographical bounding box."""
    return [
        source
        for source in get_sources(source_type=source_type)
        if are_overlapping_boxes(
            source_minimum_latitude=source[BOUNDING_BOX][MINIMUM_LATITUDE],
            source_maximum_latitude=source[BOUNDING_BOX][MAXIMUM_LATITUDE],
            source_minimum_longitude=source[BOUNDING_BOX][MINIMUM_LONGITUDE],
            source_maximum_longitude=source[BOUNDING_BOX][MAXIMUM_LONGITUDE],
            filter_minimum_latitude=minimum_latitude,
            filter_maximum_latitude=maximum_latitude,
            filter_minimum_longitude=minimum_longitude,
            filter_maximum_longitude=maximum_longitude,
        )
    ]


def get_sources_by_location(
    location,
    source_type=STATIC,
):
    """Get the sources located at the given location."""
    return [
        source
        for source in get_sources(source_type=source_type)
        if source[LOCATION] == location
    ]


def get_sources_by_country_code(
    country_code,
    source_type=STATIC,
):
    """Get the sources located at the given location."""
    return [
        source
        for source in get_sources(source_type=source_type)
        if source[COUNTRY_CODE] == country_code
    ]


def get_latest_datasets(source_type=STATIC):
    """Get latest datasets of the Mobility Catalogs."""
    return [source[URLS][LATEST] for source in get_sources(source_type=source_type)]
