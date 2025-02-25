import json
import os
import datetime
import gtfs_kit
import requests
from requests.exceptions import RequestException, HTTPError
import pandas as pd
from pandas.errors import ParserError
from unidecode import unidecode
import uuid
from tools.constants import (
    STOP_LAT,
    STOP_LON,
    MDB_ARCHIVES_LATEST_URL_TEMPLATE,
    MDB_SOURCE_FILENAME,
    ZIP,
    FALLBACK_HEADERS,

)
from urllib.parse import urlparse

#########################
# I/O FUNCTIONS
#########################


def to_json(path, obj):
    """
    Saves a JSON object to the file with the given path.

    Args:
        path (str): The path to the file where the JSON object will be saved.
        obj (dict): The JSON compatible object to save.

    Returns:
        None
    """
    with open(path, "w") as fp:
        json.dump(obj, fp, indent=4, ensure_ascii=False)


def from_json(path):
    """
    Loads a JSON object from the file at the given path.

    Args:
        path (str): The path to the file from which the JSON object will be loaded.

    Returns:
        dict: The loaded JSON object.
    """
    with open(path, "r") as fp:
        entity = json.load(fp)
    return entity


def to_csv(path, catalog, columns):
    """
    Save a catalog to a CSV file.

    This function normalizes a catalog, optionally filters it by specified columns,
    and saves it to a CSV file at the given path.

    Args:
        path (str): The path to the file where the CSV will be saved.
        catalog (list): The catalog to save, which is a list of dictionaries.
        columns (list, optional): The list of columns to include in the CSV. Defaults to None.

    Returns:
        None
    """
    catalog = pd.json_normalize(catalog)
    if columns is not None:
        catalog = catalog[columns]
    catalog.to_csv(path, sep=",", index=False)


def download_dataset(url, authentication_type, api_key_parameter_name=None, api_key_parameter_value=None):
    """
    Downloads a dataset from the given URL using specified authentication mechanisms.
    The method performs a request to the URL with API key passed as either a query
    parameter or a header, based on the chosen authentication type. If the download
    fails with certain 403 errors, a fallback request with alternative headers is attempted.
    It writes the dataset contents to a temporary file and returns the file path.

    :param url: The dataset's source URL.
    :type url: str
    :param authentication_type: The type of authentication mechanism to use (e.g.,
        1 for parameter-based, 2 for header-based).
    :type authentication_type: int
    :param api_key_parameter_name: The name of the API key parameter/header. It is
        optional if the dataset is publicly accessible or no authentication is
        required.
    :type api_key_parameter_name: str, optional
    :param api_key_parameter_value: The value of the API key to authenticate the
        request. It is optional if no authentication is required.
    :type api_key_parameter_value: str, optional
    :return: The file path where the downloaded dataset is temporarily stored.
    :type return: str
    :raises RequestException: If all attempts to download the dataset fail.
    """

    def make_request(url, params=None, headers=None):
        try:
            response = requests.get(url, params=params, headers=headers, allow_redirects=True)
            response.raise_for_status()
            return response.content
        except HTTPError as e:
            return None if e.response.status_code == 403 else RequestException(
                f"HTTP error {e} when accessing {url}. A fallback attempt with alternative headers will be made.")
        except RequestException as e:
            raise RequestException(f"Request failed: {e}")

    file_path = os.path.join(os.getcwd(), str(uuid.uuid4()))

    params = {api_key_parameter_name: api_key_parameter_value} if authentication_type == 1 else None
    headers = {api_key_parameter_name: api_key_parameter_value} if authentication_type == 2 else None

    zip_file = make_request(url, params, headers) or (
        make_request(url, params, {**FALLBACK_HEADERS, **(headers or {}),
                                   "Referer": f"{urlparse(url).scheme}://{urlparse(url).netloc}/",
                                   "Host": urlparse(url).netloc})
                     )

    if zip_file is None:
        raise RequestException(f"FAILURE! Retry attempts failed for {url}.")

    with open(file_path, "wb") as f:
        f.write(zip_file)

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
    """
    Verifies if two boxes are overlapping in two dimensions.

    This function checks if two geographical bounding boxes overlap based on their latitude and longitude coordinates.

    Args:
        source_minimum_latitude (float): The minimum latitude coordinate of the source box.
        source_maximum_latitude (float): The maximum latitude coordinate of the source box.
        source_minimum_longitude (float): The minimum longitude coordinate of the source box.
        source_maximum_longitude (float): The maximum longitude coordinate of the source box.
        filter_minimum_latitude (float): The minimum latitude coordinate of the filter box.
        filter_maximum_latitude (float): The maximum latitude coordinate of the filter box.
        filter_minimum_longitude (float): The minimum longitude coordinate of the filter box.
        filter_maximum_longitude (float): The maximum longitude coordinate of the filter box.

    Returns:
        bool: True if the two boxes are overlapping, False otherwise.
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
    """
    Verifies if two edges are overlapping in one dimension.

    This function checks if two edges, defined by their minimum and maximum coordinates,
    overlap in a single dimension.

    Args:
        source_minimum (float): The minimum coordinate of the source edge.
        source_maximum (float): The maximum coordinate of the source edge.
        filter_minimum (float): The minimum coordinate of the filter edge.
        filter_maximum (float): The maximum coordinate of the filter edge.

    Returns:
        bool: True if the two edges are overlapping, False otherwise.
              Returns False if one or more coordinates are None.
    """
    return (
        source_maximum > filter_minimum and filter_maximum > source_minimum
        if None not in [source_minimum, source_maximum, filter_minimum, filter_maximum]
        else False
    )


def is_readable(file_path, load_func):
    """
    Verifies if a given source dataset is readable.

    This function checks if a dataset located at a specified file path can be successfully read
    using the provided load function. If an exception occurs during the reading process, it raises
    an exception with a detailed error message.

    Args:
        file_path (str): The file path to the source dataset.
        load_func (callable): The load function to use for reading the dataset.

    Returns:
        bool: True if the dataset is readable.

    Raises:
        Exception: If an error occurs while reading the dataset.
    """
    try:
        load_func(file_path)
    except Exception as e:
        raise Exception(
            f"Exception '{e}' occurred while reading the dataset. "
            f"The dataset must be a valid dataset.\n"
            f"Please contact emma@mobilitydata.org for assistance.\n"
        )
    return True


#########################
# CREATION FUNCTIONS
#########################


def create_latest_url(
    country_code, subdivision_name, provider, data_type, mdb_source_id
):
    """
    Creates the latest URL for an MDB Source.

    This function generates the latest URL for an MDB (Mobility Database) source based on the provided
    parameters. The URL is constructed using a template and includes a filename created from the given
    attributes of the source.

    Args:
        country_code (str): The country code of the entity.
        subdivision_name (str): The subdivision name of the entity.
        provider (str): The name of the entity.
        data_type (str): The data type of the entity.
        mdb_source_id (str): The MDB Source ID.

    Returns:
        str: The latest URL for the MDB source.
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
    """
    Creates the filename for an MDB Source.

    This function generates a filename for an MDB (Mobility Database) source based on the provided
    parameters. The filename is constructed using a template and includes normalized values for
    country code, subdivision name, and provider, along with the data type, MDB source ID, and file extension.

    Args:
        country_code (str): The country code of the entity.
        subdivision_name (str): The subdivision name of the entity.
        provider (str): The name of the entity.
        data_type (str): The data type of the entity.
        mdb_source_id (str): The MDB Source ID.
        extension (str): The extension of the file.

    Returns:
        str: The filename for the MDB source.
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
    """
    Normalizes a string to create a standardized format suitable for filenames.

    This function processes a given string by performing the following steps:
    1. Splits the string at commas and takes the first part.
    2. Converts the string to lowercase and retains only alphanumeric characters,
       spaces, and hyphens.
    3. Replaces spaces with hyphens.
    4. Converts the string to ASCII, removing any non-ASCII characters.

    Args:
        string (str): The input string to normalize.

    Returns:
        str: The normalized string.
    """
    string = string.split(",")[0]
    string = "-".join(
        ("".join(s for s in string.lower() if s.isalnum() or s in [" ", "-"])).split()
    )
    string = unidecode(string, "utf-8")
    return unidecode(string)


def get_iso_time():
    """
    Gets the current UTC time in ISO 8601 format.

    This function retrieves the current time in UTC, removes the microseconds for
    consistency, and formats it according to the ISO 8601 standard.

    Returns:
        str: The current UTC time in ISO 8601 format.
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


def load_gtfs(file_path):
    """
    Loads a GTFS Schedule dataset from the given file path.

    This function reads a GTFS (General Transit Feed Specification) dataset using the GTFS Kit library.
    It handles potential exceptions during the reading process and provides informative error messages.

    Args:
        file_path (str): The file path to the GTFS Schedule dataset.

    Returns:
        gtfs_kit.Feed: The GTFS dataset representation provided by GTFS Kit.

    Raises:
        TypeError: If a TypeError occurs while reading the dataset, indicating that the dataset must be a valid GTFS zip file or URL.
        ParserError: If a ParserError occurs while parsing the dataset, indicating that the dataset must be a valid GTFS zip file or URL.
    """
    try:
        dataset = gtfs_kit.read_feed(file_path, dist_units="km")
    except TypeError as te:
        raise TypeError(
            f"TypeError exception '{te}' occurred while reading the GTFS dataset with the GTFS kit library."
            f"The dataset must be a valid GTFS zip file or URL.\n"
        )
    except ParserError as pe:
        raise ParserError(
            f"ParserError exception {pe} found while parsing the GTFS dataset with the GTFS kit library."
            f"The dataset must be a valid GTFS zip file or URL.\n"
        )
    return dataset


def extract_gtfs_bounding_box(file_path):
    """
    Extracts the bounding box of a GTFS source using the `stops` file from the GTFS dataset.

    This function loads a GTFS dataset and computes the geographical bounding box (minimum and maximum latitudes and longitudes)
    based on the stops in the dataset.

    Args:
        file_path (str): The file path to the GTFS dataset.

    Returns:
        tuple: The coordinates of the bounding box as floats (minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude).

    Notes:
        If the stops file or required columns are missing, or if the columns contain no data, the bounding box coordinates will be None.
    """
    dataset = load_gtfs(file_path)
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
