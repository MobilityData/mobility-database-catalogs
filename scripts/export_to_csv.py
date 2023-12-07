# Read the feeds json files and generate the sources.csv file.
# Normally called from the export_to_csv github action, but can also be called directly with python.
import pandas as pd
import os
import json

CSV_PATH = "./sources.csv"
CSV_COLUMNS = [
    'mdb_source_id',
    'data_type',
    'entity_type',
    'location.country_code',
    'location.subdivision_name',
    'location.municipality',
    'provider',
    'name',
    'note',
    'feed_contact_email',
    'static_reference',
    'urls.direct_download',
    'urls.authentication_type',
    'urls.authentication_info',
    'urls.api_key_parameter_name',
    'urls.latest',
    'urls.license',
    'location.bounding_box.minimum_latitude',
    'location.bounding_box.maximum_latitude',
    'location.bounding_box.minimum_longitude',
    'location.bounding_box.maximum_longitude',
    'location.bounding_box.extracted_on',
    'status',
    'features',
    'redirect.id',
    'redirect.comment'
]

# tools.constants
GTFS = "gtfs"
GTFS_RT = "gtfs-rt"
MDB_SOURCE_ID = "mdb_source_id"
DATA_TYPE = "data_type"
LOCATION = "location"
COUNTRY_CODE = "country_code"
SUBDIVISION_NAME = "subdivision_name"
MUNICIPALITY = "municipality"
STATIC_REFERENCE = "static_reference"
ENTITY_TYPE = "entity_type"
UNKNOWN = "unknown"
URLS_AUTHENTICATION_TYPE = "urls.authentication_type"
FEATURES = "features"
REDIRECTS = "redirect"
REDIRECT_ID = "redirect.id"
REDIRECT_COMMENT = "redirect.comment"
FEED_CONTACT_EMAIL = "feed_contact_email"

# tools.constants.GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT
GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/schedule"

# tools.constants.GTFS_REALTIME_CATALOG_PATH_FROM_ROOT
GTFS_REALTIME_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/realtime"

# tools.operations.get_sources
gtfs_schedule_catalog_path = os.path.join(".", GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT)
gtfs_realtime_catalog_path = os.path.join(".", GTFS_REALTIME_CATALOG_PATH_FROM_ROOT)
catalog = {}
for catalog_path in [gtfs_schedule_catalog_path, gtfs_realtime_catalog_path]:
    for path, sub_dirs, files in os.walk(catalog_path):
        for file in files:
            with open(os.path.join(path, file)) as fp:
                entity_json = json.load(fp)
                entity_id = entity_json[MDB_SOURCE_ID]
                catalog[entity_id] = entity_json
# Complete the GTFS Realtime Sources: location information from their static reference
# and pipe delimited static reference and entity type
for source_id, source in catalog.items():
    if source.get(DATA_TYPE) == GTFS_RT:
        if len(source.get(STATIC_REFERENCE, [])) > 0:
            if catalog.get(source.get(STATIC_REFERENCE)[0], {}).get(LOCATION) is not None:
                source[LOCATION] = catalog.get(source.get(STATIC_REFERENCE)[0], {}).get(LOCATION)
            source[STATIC_REFERENCE] = "|".join([str(ref_id) for ref_id in source.get(STATIC_REFERENCE)])
        else:
            source[LOCATION] = {COUNTRY_CODE: UNKNOWN, SUBDIVISION_NAME: UNKNOWN, MUNICIPALITY: UNKNOWN}
        source[ENTITY_TYPE] = "|".join(source.get(ENTITY_TYPE))
    if len(source.get(FEATURES, [])) > 0:
        source[FEATURES] = "|".join(source.get(FEATURES))

    # For redirects, allow strings or integers
    redirects = source.pop(REDIRECTS, [])
    # Extract ids and comments
    ids = []
    comments = []

    for item in redirects:
        ids.append(str(item["id"]))               # Convert to string since we allow integer ids
        comments.append(item.get("comment", ""))  # Default to an empty string if "comment" is missing

    # Join the ids and comments with '|' as separator
    ids_str = "|".join(ids)
    comments_str = "|".join(comments) if comments else ""
    source[REDIRECT_ID] = ids_str
    source[REDIRECT_COMMENT] = comments_str

    catalog[source_id] = source
# Sort the catalog and convert it to a list
catalog = list(dict(sorted(catalog.items())).values())

# tools.helpers.to_csv
path = CSV_PATH
columns = CSV_COLUMNS
catalog = pd.json_normalize(catalog)
tmp = pd.DataFrame()
for column in columns:
    if column in catalog:
        tmp[column] = catalog[column]
    else:  # None of the input json file has the column. We still want the column in the .csv file.
        tmp[column] = None
catalog = tmp
if URLS_AUTHENTICATION_TYPE in catalog:
    catalog[URLS_AUTHENTICATION_TYPE] = catalog[URLS_AUTHENTICATION_TYPE].astype('Int64')
catalog.to_csv(path, sep=",", index=False)