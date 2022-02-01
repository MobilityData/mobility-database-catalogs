# DATA TYPES
GTFS = "gtfs"

# GTFS CONSTANTS
STOP_LAT = "stop_lat"
STOP_LON = "stop_lon"

# IDS TEMPLATE
MDB_SOURCE_ID_TEMPLATE = "mdb-src-{data_type}-{name}-{country_code}"

# ARCHIVES TEMPLATE
MDB_ARCHIVES_LATEST_URL_TEMPLATE = "https://storage.googleapis.com/storage/v1/b/archives_latest/o/{mdb_source_id}.{extension}?alt=media"

# CATALOG ROOTS
GTFS_CATALOG_PATH_FROM_ROOT = "catalogs/gtfs/schedules"

# SCHEMAS FILES
GTFS_SCHEDULES_SOURCE_SCHEMA_PATH_FROM_ROOT = (
    "schemas/gtfs_schedules_source_schema.json"
)

# STATIC_SCHEMA
MDB_SOURCE_ID = "mdb_source_id"
NAME = "name"
LOCATION = "location"
COUNTRY_CODE = "country_code"
BOUNDING_BOX = "bounding_box"
MINIMUM_LATITUDE = "minimum_latitude"
MAXIMUM_LATITUDE = "maximum_latitude"
MINIMUM_LONGITUDE = "minimum_longitude"
MAXIMUM_LONGITUDE = "maximum_longitude"
EXTRACTED_ON = "extracted_on"
DATA_TYPE = "data_type"
URLS = "urls"
AUTO_DISCOVERY = "auto_discovery"
LICENSE = "license"
LATEST = "latest"

# OTHER
PATH_FROM_ROOT = "path_from_root"
LOAD_FUNC = "load_func"
EXTENSION = "extension"
ZIP = "zip"
JSON = "json"
