from wikibaseintegrator import wbi_core
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_core import (
    CorePropIntegrityException,
    ManualInterventionReqException,
)
import os
import argparse
import json

###############################################################################
# This script verifies if a submitted source is using a stable URL already
# present on the Mobility Database.
# Made for Python 3.9. Requires the modules listed in requirements.txt.
###############################################################################

# Mobility Database constants
SPARQL_BIGDATA_URL = "http://mobilitydatabase.org:8989/bigdata/sparql"
API_URL = "http://mobilitydatabase.org/w/api.php"
SVC_URL = "http://wikibase.svc"
STABLE_URL = "stable_url"
SOURCE_NAME = "source_name"
STABLE_URL_PROPERTY = "P13"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to verify source URL. Python 3.9.")
    parser.add_argument(
        "-f",
        "--file-path",
        action="store",
        help="Path to the source file to read.",
    )
    args = parser.parse_args()

    # Load Wikibase Integrator config
    wbi_config["MEDIAWIKI_API_URL"] = API_URL
    wbi_config["SPARQL_ENDPOINT_URL"] = SPARQL_BIGDATA_URL
    wbi_config["WIKIBASE_URL"] = SVC_URL

    with open(args.file_path, "r") as f:
        source_json = json.load(f)

    stable_url = source_json[STABLE_URL]
    source_name = source_json[SOURCE_NAME]

    try:
        source_stable_url = wbi_core.Url(value=stable_url, prop_nr=STABLE_URL_PROPERTY)
    except ValueError as ve:
        print(f"url {stable_url} for source name {source_name} raised {ve}")
        raise ve

    core_props_data = [source_stable_url]

    # An existing source entity is considered the same as the one processed
    # if and only if their stable URLs are matching
    # so the core properties threshold is 100%
    core_props_threshold = 1.0

    try:
        source_entity = wbi_core.ItemEngine(
            data=core_props_data,
            core_props={
                os.environ[STABLE_URL_PROPERTY],
            },
            core_prop_match_thresh=core_props_threshold,
        )
    except ManualInterventionReqException as mi:
        print(
            f"ManualInterventionReqException : a core property value exists for multiple source entities."
        )
        raise mi
    except CorePropIntegrityException as cp:
        print(
            f"CorePropIntegrityException: a source entity exists with 1 of the core props value."
        )
        raise cp
    except Exception as e:
        print(f"Stable url : {stable_url} as core property raised {e}")
        raise e

    # If the source entity retrieved as already an item_id (entity id) value,
    # then we raise an exception because a source already exists with the stable URL
    if source_entity.item_id != "":
        raise Exception(f"{source_entity.item_id} already exist with stable URL {stable_url}")
