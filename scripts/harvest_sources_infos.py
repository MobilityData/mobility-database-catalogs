import argparse
import json
import requests
import re
from os import path

###############################################################################
# This script harvests the sources infos for the sources listed in a catalog.
# Made for Python 3.9. Requires the modules listed in requirements.txt.
###############################################################################

# API constants
API_URL = "http://mobilitydatabase.org/w/api.php?"
ACTION = "action"
STABLE_URL_PROPERTY = "P13"
CLAIMS = "claims"
ENTITIES = "entities"
IDS = "ids"
SOURCE_PROPERTY = "P5"
WBGETENTITIES = "wbgetentities"
FORMAT = "format"
JSON = "json"
MAINSNAK = "mainsnak"
DATAVALUE = "datavalue"
VALUE = "value"
ID = "id"
LABELS = "labels"
EN = "en"
SOURCE_NAME = "source_name"
STABLE_URL = "stable_url"
BACKUP_STABLE_URL = "backup_stable_url"
DATATYPE = "datatype"

# Catalog constants
GTFS_CATALOG_ID = "Q6"

# Other
NON_ALPHANUM_CHAR_REGEX = "[^a-zA-Z0-9]+"
GTFS_NAME_SUFFIX = "'s GTFS Schedule source"


def save_content_to_file(content, data_path, filename):
    file_path = path.join(data_path, filename)
    with open(file_path, "w") as f:
        json.dump(content, f)


def save_sources_infos(source_infos, data_path):
    filename_prefix = source_infos[SOURCE_NAME]
    filename_prefix = filename_prefix.replace(GTFS_NAME_SUFFIX, "")
    filename_prefix = re.sub(
        NON_ALPHANUM_CHAR_REGEX, "_", filename_prefix
    ).lower()

    filename_suffix = source_infos[STABLE_URL]
    for string in ["https://", "http://", "www."]:
        filename_suffix = filename_suffix.replace(string, "")
    filename_suffix = filename_suffix.replace("/", ".")

    filename = f"{filename_prefix}-{filename_suffix}"
    filename += ".json"

    save_content_to_file(source_infos, data_path, filename)


def get_entity_data(entity_id):
    query = {ACTION: WBGETENTITIES, IDS: entity_id, FORMAT: JSON}
    response = requests.get(API_URL, params=query)
    response_json = response.json()
    return response_json[ENTITIES][entity_id]


def harvest_sources_infos(catalog_data, data_path):
    sources_infos = []

    sources = catalog_data[CLAIMS][SOURCE_PROPERTY]
    for source in sources:
        source_id = source[MAINSNAK][DATAVALUE][VALUE][ID]
        source_data = get_entity_data(source_id)
        source_infos = {}
        source_infos[SOURCE_NAME] = source_data[LABELS][EN][VALUE]
        source_infos[STABLE_URL] = source_data[CLAIMS][STABLE_URL_PROPERTY][0][MAINSNAK][DATAVALUE][VALUE]
        if len(source_data[CLAIMS][STABLE_URL_PROPERTY]) > 1:
            source_infos[BACKUP_STABLE_URL] = source_data[CLAIMS][STABLE_URL_PROPERTY][1][MAINSNAK][DATAVALUE][VALUE]
        source_infos[DATATYPE] = "GTFS"
        save_sources_infos(source_infos, data_path)
        sources_infos.append(source_infos)

    return sources_infos


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to harvest sources infos. Python 3.9.")
    parser.add_argument(
        "-d",
        "--data-path",
        action="store",
        default="./data/",
        help="Data path.",
    )
    args = parser.parse_args()

    catalog_id = GTFS_CATALOG_ID
    catalog_data = get_entity_data(catalog_id)
    sources_infos = harvest_sources_infos(catalog_data, args.data_path)
