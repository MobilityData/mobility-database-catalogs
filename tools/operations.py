import os
import tools.helpers as helpers
from tools.constants import (
    STATIC,
    PATH_FROM_ROOT,
    STATIC_CATALOG_PATH_FROM_ROOT,
    GTFS_CATALOG_PATH_FROM_ROOT,
    BOUNDING_BOX,
    MINIMUM_LATITUDE,
    MAXIMUM_LATITUDE,
    MINIMUM_LONGITUDE,
    MAXIMUM_LONGITUDE,
    URLS,
    LATEST_DATASET,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

STATIC_MAP = {PATH_FROM_ROOT: STATIC_CATALOG_PATH_FROM_ROOT}

GTFS_MAP = {PATH_FROM_ROOT: GTFS_CATALOG_PATH_FROM_ROOT}


def add_source(
    name, location, country_code, auto_discovery_url, license_url, source_type=STATIC
):
    """Add a new source to the Mobility Catalogs."""
    raise NotImplementedError


def update_source(
    mdb_source_id,
    name=None,
    location=None,
    country_code=None,
    discovery_url=None,
    license_url=None,
    source_type=STATIC,
):
    """Update a source in the Mobility Catalogs."""
    raise NotImplementedError


def get_sources(source_type=STATIC):
    """Get the sources of the Mobility Catalogs."""
    catalog_root = os.path.join(
        PROJECT_ROOT, globals()[f"{source_type.upper()}_MAP"][PATH_FROM_ROOT]
    )
    return helpers.aggregate(catalog_root)


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
        if helpers.is_overlapping_bounding_box(
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


def get_latest_datasets(source_type=STATIC):
    """Get latest datasets of the Mobility Catalogs."""
    return [
        source[URLS][LATEST_DATASET] for source in get_sources(source_type=source_type)
    ]
