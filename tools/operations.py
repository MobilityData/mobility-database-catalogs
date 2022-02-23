import os
from tools.helpers import (
    aggregate,
    is_readable,
    identify,
    extract_gtfs_bounding_box,
    are_overlapping_boxes,
    load_gtfs,
    create_latest_url,
    create_filename,
    to_json,
    from_json,
    get_iso_time,
    find_file,
)
from tools.constants import (
    GTFS,
    PATH_FROM_ROOT,
    LOAD_FUNC,
    SOURCE_CATALOG_PATH_FROM_ROOT,
    GTFS_CATALOG_PATH_FROM_ROOT,
    JSON,
    MDB_SOURCE_ID,
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
    DATA_TYPE,
    URLS,
    AUTO_DISCOVERY,
    LICENSE,
    LATEST,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

GTFS_MAP = {
    PATH_FROM_ROOT: GTFS_CATALOG_PATH_FROM_ROOT,
    LOAD_FUNC: load_gtfs,
}


def add_source(
    provider,
    country_code,
    subdivision_name,
    municipality,
    auto_discovery_url,
    license_url=None,
    name=None,
    data_type=GTFS,
):
    """Add a new source to the Mobility Catalogs."""
    data_type_map = globals()[f"{data_type.upper()}_MAP"]
    if is_readable(url=auto_discovery_url, load_func=data_type_map[LOAD_FUNC]):
        mdb_source_id = identify(
            catalog_root=os.path.join(PROJECT_ROOT, SOURCE_CATALOG_PATH_FROM_ROOT)
        )
        (
            minimum_latitude,
            maximum_latitude,
            minimum_longitude,
            maximum_longitude,
        ) = extract_gtfs_bounding_box(url=auto_discovery_url)
        latest_url = create_latest_url(
            country_code=country_code,
            subdivision_name=subdivision_name,
            provider=provider,
            data_type=data_type,
            mdb_source_id=mdb_source_id,
        )
        extraction_time = get_iso_time()

        source = {
            MDB_SOURCE_ID: mdb_source_id,
            DATA_TYPE: data_type,
            PROVIDER: provider,
            NAME: name,
            LOCATION: {
                COUNTRY_CODE: country_code,
                SUBDIVISION_NAME: subdivision_name,
                MUNICIPALITY: municipality,
                BOUNDING_BOX: {
                    MINIMUM_LATITUDE: minimum_latitude,
                    MAXIMUM_LATITUDE: maximum_latitude,
                    MINIMUM_LONGITUDE: minimum_longitude,
                    MAXIMUM_LONGITUDE: maximum_longitude,
                    EXTRACTED_ON: extraction_time,
                },
            },
            URLS: {
                AUTO_DISCOVERY: auto_discovery_url,
                LICENSE: license_url,
                LATEST: latest_url,
            },
        }

        if name is None:
            del source[NAME]
        if license_url is None:
            del source[URLS][LICENSE]

        to_json(
            path=os.path.join(
                PROJECT_ROOT,
                data_type_map[PATH_FROM_ROOT],
                create_filename(
                    country_code=country_code,
                    subdivision_name=subdivision_name,
                    provider=provider,
                    data_type=data_type,
                    mdb_source_id=mdb_source_id,
                    extension=JSON,
                ),
            ),
            obj=source,
        )
        return source


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


def get_sources(data_type=GTFS):
    """Get the sources of the Mobility Catalogs."""
    source_type_map = globals()[f"{data_type.upper()}_MAP"]
    catalog_root = os.path.join(PROJECT_ROOT, source_type_map[PATH_FROM_ROOT])
    return aggregate(catalog_root)


def get_sources_by_bounding_box(
    minimum_latitude,
    maximum_latitude,
    minimum_longitude,
    maximum_longitude,
    data_type=GTFS,
):
    """Get the sources included in the geographical bounding box."""
    return [
        source
        for source in get_sources(data_type=data_type)
        if are_overlapping_boxes(
            source_minimum_latitude=source[LOCATION][BOUNDING_BOX][MINIMUM_LATITUDE],
            source_maximum_latitude=source[LOCATION][BOUNDING_BOX][MAXIMUM_LATITUDE],
            source_minimum_longitude=source[LOCATION][BOUNDING_BOX][MINIMUM_LONGITUDE],
            source_maximum_longitude=source[LOCATION][BOUNDING_BOX][MAXIMUM_LONGITUDE],
            filter_minimum_latitude=minimum_latitude,
            filter_maximum_latitude=maximum_latitude,
            filter_minimum_longitude=minimum_longitude,
            filter_maximum_longitude=maximum_longitude,
        )
    ]


def get_sources_by_subdivision_name(
    subdivision_name,
    data_type=GTFS,
):
    """Get the sources located at the given subdivision name."""
    return [
        source
        for source in get_sources(data_type=data_type)
        if source[LOCATION][SUBDIVISION_NAME] == subdivision_name
    ]


def get_sources_by_country_code(
    country_code,
    data_type=GTFS,
):
    """Get the sources located at the given country code."""
    return [
        source
        for source in get_sources(data_type=data_type)
        if source[LOCATION][COUNTRY_CODE] == country_code
    ]


def get_latest_datasets(data_type=GTFS):
    """Get latest datasets of the Mobility Catalogs."""
    return [source[URLS][LATEST] for source in get_sources(data_type=data_type)]
