import json
import os
import gtfs_kit
from requests.exceptions import MissingSchema
from pandas.errors import ParserError
from constants import (
    STOP_LAT,
    STOP_LON,
    MDB_SOURCE_ID_TEMPLATE,
    MDB_ARCHIVES_LATEST_URL_TEMPLATE,
)


def aggregate(catalog_root):
    """Aggregate the sources of a catalog.
    :param catalog_root: The path to the root of the catalog folder.
    :return: The sources of the catalog.
    """
    catalog = []
    for path, sub_dirs, files in os.walk(catalog_root):
        for file in files:
            with open(os.path.join(path, file)) as fp:
                catalog.append(json.load(fp))
    return catalog


def to_json(path, entity):
    with open(path, "w") as fp:
        json.dump(entity, fp)


def from_json(path):
    with open(path, "r") as fp:
        entity = json.load(fp)
    return entity


def to_csv(path, catalog):
    raise NotImplementedError


def are_overlapping_boxes(
    source_minimum_latitude,
    source_maximum_latitude,
    source_minimum_longitude,
    source_maximum_longitude,
    filter_minimum_latitude,
    filter_maximum_latitude,
    filter_minimum_longitude,
    filter_maximum_longitude,
):
    """Verify if two boxes are overlapping in two dimension.
    :param source_minimum_latitude: The minimum latitude coordinate of the source box.
    :param source_maximum_latitude: The maximum latitude coordinate of the source box.
    :param source_minimum_longitude: The minimum longitude coordinate of the source box.
    :param source_maximum_longitude: The maximum longitude coordinate of the source box.
    :param filter_minimum_latitude: The minimum latitude coordinate of the filter box.
    :param filter_maximum_latitude: The maximum latitude coordinate of the filter box.
    :param filter_minimum_longitude: The minimum longitude coordinate of the filter box.
    :param filter_maximum_longitude: The maximum longitude coordinate of the filter box.
    :return: True if the two boxes are overlapping, False otherwise.
    """
    return are_overlapping_edges(
        source_minimum_latitude,
        source_maximum_latitude,
        filter_minimum_latitude,
        filter_maximum_latitude,
    ) and are_overlapping_edges(
        source_minimum_longitude,
        source_maximum_longitude,
        filter_minimum_longitude,
        filter_maximum_longitude,
    )


def are_overlapping_edges(
    source_minimum, source_maximum, filter_minimum, filter_maximum
):
    """Verify if two edges are overlapping in one dimension.
    :param source_minimum: The minimum coordinate of the source edge.
    :param source_maximum: The maximum coordinate of the source edge.
    :param filter_minimum: The minimum coordinate of the filter edge.
    :param filter_maximum: The maximum coordinate of the filter edge.
    :return: True is the two edges are overlapping, False otherwise.
    Returns False if one or more coordinates are None.
    """
    return (
        source_maximum >= filter_minimum and filter_maximum >= source_minimum
        if None not in [source_minimum, source_maximum, filter_minimum, filter_maximum]
        else False
    )


def is_readable(url, load_func):
    """Verify if a given source URL is readable, ie. a valid dataset can be downloaded from it.
    :param url: The URL where to download the source dataset.
    :param load_func: The load function to use.
    :return: True if readable, raise an exception if a problem occurs.
    """
    try:
        globals()[load_func](url)
    except (TypeError, MissingSchema, ParserError) as e:
        raise (
            f"Exception '{e}' occurred while reading the GTFS dataset with the GTFS kit library."
            f"The dataset downloaded with the auto-discovery URL must be a valid GTFS zip file.\n"
            f"Please contact emma@mobilitydata.org for assistance.\n"
        )
    return True


def identify_source(name, country_code, data_type):
    """Identity a MDB source with a MDB ID.
    :param name: The name of the entity.
    :param data_type: The data type of the entity.
    :param country_code: The country code of the entity.
    :return: The MDB Source ID.
    """
    return MDB_SOURCE_ID_TEMPLATE.format(
        name=name, data_type=data_type, country_code=country_code
    )


def create_latest_url(mdb_source_id, extension):
    """Create the latest url for a MDB Source.
    :param mdb_source_id: The MDB Source ID.
    :param extension: The dataset extension.
    :return: The latest url.
    """
    return MDB_ARCHIVES_LATEST_URL_TEMPLATE.format(
        mdb_source_id=mdb_source_id, extension=extension
    )


#########################
# GTFS SPECIFIC FUNCTIONS
#########################


def load_gtfs(url):
    """Load a GTFS dataset from the passed URL.
    :param url: The URL where to download the GTFS dataset.
    :return: The GTFS dataset representation given by GTFS Kit.
    """
    return gtfs_kit.read_feed(url, dist_units="km")


def extract_gtfs_bounding_box(url):
    """Extract a GTFS source bounding box using the `stops` file from the GTFS dataset.
    :param url: The URL where to download the GTFS dataset.
    :return: The coordinates of the bounding box as floats.
    """
    dataset = load_gtfs(url)
    stops_required_columns = {STOP_LAT, STOP_LON}
    stops_are_present = dataset.stops is not None and stops_required_columns.issubset(
        dataset.stops.columns
    )

    minimum_latitude = dataset.stops[STOP_LAT].min() if stops_are_present else None
    maximum_latitude = dataset.stops[STOP_LAT].max() if stops_are_present else None
    minimum_longitude = dataset.stops[STOP_LON].min() if stops_are_present else None
    maximum_longitude = dataset.stops[STOP_LON].max() if stops_are_present else None

    return minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
