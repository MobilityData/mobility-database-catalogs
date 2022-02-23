import json
import os
import datetime
import gtfs_kit
from requests.exceptions import MissingSchema
import pandas as pd
from pandas.errors import ParserError
from tools.constants import (
    STOP_LAT,
    STOP_LON,
    MDB_ARCHIVES_LATEST_URL_TEMPLATE,
    MDB_SOURCE_FILENAME,
    ZIP,
)


#########################
# I/O FUNCTIONS
#########################


def aggregate(catalog_root):
    """Aggregates the sources of a catalog.
    :param catalog_root: The path to the root of the catalog folder.
    :return: The sources of the catalog.
    """
    catalog = []
    for path, sub_dirs, files in os.walk(catalog_root):
        for file in files:
            with open(os.path.join(path, file)) as fp:
                catalog.append(json.load(fp))
    return catalog


def to_json(path, obj):
    """Saves a JSON object to the file with the given path.
    :param path: The path to the file.
    :param obj: The JSON compatible object to save.
    """
    with open(path, "w") as fp:
        json.dump(obj, fp, indent=4)


def from_json(path):
    """Loads a JSON object from the file at the given path.
    :param path: The path to the file.
    :return: The JSON object.
    """
    with open(path, "r") as fp:
        entity = json.load(fp)
    return entity


def to_csv(path, catalog, columns):
    catalog = pd.json_normalize(catalog)
    if columns is not None:
        catalog = catalog[columns]
    catalog.to_csv(path, sep=",", index=False)


def find_file(catalog_root, mdb_id):
    file_path = None
    for path, sub_dirs, files in os.walk(catalog_root):
        for file in files:
            # Split the filename string under the format
            # "filename-prefix-mdb-id.extension" to extract the mdb_id
            if file.split(".")[0].split("-")[-1] == str(mdb_id):
                file_path = os.path.join(path, file)
                break
    return file_path


#########################
# VERIFICATION FUNCTIONS
#########################


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
    """Verifies if two boxes are overlapping in two dimension.
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
    """Verifies if two edges are overlapping in one dimension.
    :param source_minimum: The minimum coordinate of the source edge.
    :param source_maximum: The maximum coordinate of the source edge.
    :param filter_minimum: The minimum coordinate of the filter edge.
    :param filter_maximum: The maximum coordinate of the filter edge.
    :return: True is the two edges are overlapping, False otherwise.
    Returns False if one or more coordinates are None.
    """
    return (
        source_maximum > filter_minimum and filter_maximum > source_minimum
        if None not in [source_minimum, source_maximum, filter_minimum, filter_maximum]
        else False
    )


def is_readable(url, load_func):
    """Verifies if a given source URL is readable, ie. a valid dataset can be downloaded from it.
    :param url: The URL where to download the source dataset.
    :param load_func: The load function to use.
    :return: True if readable, raise an exception if a problem occurs.
    """
    try:
        load_func(url)
    except Exception as e:
        raise (
            f"Exception '{e}' occurred while reading the dataset. "
            f"The dataset downloaded with the auto-discovery URL must be a valid dataset.\n"
            f"Please contact emma@mobilitydata.org for assistance.\n"
        )
    return True


#########################
# CREATION FUNCTIONS
#########################


def identify(catalog_root):
    """Identities a MDB entity with a MDB ID.
    The MDB Entity ID is a numeric identifier, which is assigned incrementally.
    :return: The MDB Entity ID.
    """
    return sum(len(files) for path, sub_dirs, files in os.walk(catalog_root)) + 1


def create_latest_url(
    country_code, subdivision_name, provider, data_type, mdb_source_id
):
    """Creates the latest url for a MDB Source.
    :param provider: The name of the entity.
    :param subdivision_name: The subdivision name of the entity.
    :param country_code: The country code of the entity.
    :param data_type: The data type of the entity.
    :param mdb_source_id: The MDB Source ID.
    :return: The latest url.
    """
    return MDB_ARCHIVES_LATEST_URL_TEMPLATE.format(
        filename=create_filename(
            country_code=country_code,
            subdivision_name=subdivision_name,
            provider=provider,
            data_type=data_type,
            mdb_source_id=mdb_source_id,
            extension=ZIP,
        )
    )


def create_filename(
    country_code, subdivision_name, provider, data_type, mdb_source_id, extension
):
    """Creates the latest url for a MDB Source.
    :param provider: The name of the entity.
    :param subdivision_name: The subdivision name of the entity.
    :param country_code: The country code of the entity.
    :param data_type: The data type of the entity.
    :param mdb_source_id: The MDB Source ID.
    :param extension: The extension of the file.
    :return: The filename.
    """
    return MDB_SOURCE_FILENAME.format(
        country_code=normalize(country_code),
        subdivision_name=normalize(subdivision_name),
        provider=normalize(provider),
        data_type=data_type,
        mdb_source_id=mdb_source_id,
        extension=extension,
    )


def normalize(string):
    return "-".join(
        ("".join(s for s in string.lower() if s.isalnum() or s == " ")).split()
    )


def get_iso_time():
    """Get the current UTC time in ISO 8601 format.
    :return: The current UTC time in ISO 8601 format.
    """
    return (
        datetime.datetime.utcnow()
        .replace(tzinfo=datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


#########################
# GTFS SPECIFIC FUNCTIONS
#########################


def load_gtfs(url):
    """Loads a GTFS dataset from the passed URL.
    :param url: The URL where to download the GTFS dataset.
    :return: The GTFS dataset representation given by GTFS Kit.
    """
    try:
        dataset = gtfs_kit.read_feed(url, dist_units="km")
    except TypeError as te:
        raise TypeError(
            f"TypeError exception '{te}' occurred while reading the GTFS dataset with the GTFS kit library."
            f"The dataset must be a valid GTFS zip file or URL.\n"
        )
    except MissingSchema as ms:
        raise MissingSchema(
            f"MissingSchema exception '{ms}' occurred while opening the GTFS dataset with the GTFS kit library."
            f"The dataset must be a valid GTFS zip file or URL.\n"
        )
    except ParserError as pe:
        raise ParserError(
            f"ParserError exception {pe} found while parsing the GTFS dataset with the GTFS kit library."
            f"The dataset must be a valid GTFS zip file or URL.\n"
        )
    return dataset


def extract_gtfs_bounding_box(url):
    """Extracts a GTFS source bounding box using the `stops` file from the GTFS dataset.
    :param url: The URL where to download the GTFS dataset.
    :return: The coordinates of the bounding box as floats.
    """
    dataset = load_gtfs(url)
    stops = dataset.stops

    stops_required_columns = {STOP_LAT, STOP_LON}
    stops_are_present = (
        stops is not None
        and stops_required_columns.issubset(stops.columns)
        and not (stops[STOP_LAT].dropna().empty or stops[STOP_LON].dropna().empty)
    )

    minimum_latitude = stops[STOP_LAT].dropna().min() if stops_are_present else None
    maximum_latitude = stops[STOP_LAT].dropna().max() if stops_are_present else None
    minimum_longitude = stops[STOP_LON].dropna().min() if stops_are_present else None
    maximum_longitude = stops[STOP_LON].dropna().max() if stops_are_present else None

    return minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
