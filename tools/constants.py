# DATA TYPES
GTFS = "gtfs"

# GTFS CONSTANTS
STOP_LAT = "stop_lat"
STOP_LON = "stop_lon"

# FILENAME TEMPLATE
MDB_SOURCE_FILENAME = "{country_code}-{subdivision_name}-{provider}-{data_type}-{mdb_source_id}.{extension}"

# ARCHIVES TEMPLATE
MDB_ARCHIVES_LATEST_URL_TEMPLATE = (
    "https://storage.googleapis.com/storage/v1/b/archives_latest/o/{filename}?alt=media"
)

# CATALOG ROOTS
SOURCE_CATALOG_PATH_FROM_ROOT = "catalogs/sources"
GTFS_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/schedules"

# SCHEMAS FILES
GTFS_SCHEDULES_SOURCE_SCHEMA_PATH_FROM_ROOT = (
    "schemas/gtfs_schedules_source_schema.json"
)

# STATIC_SCHEMA
MDB_SOURCE_ID = "mdb_source_id"
DATA_TYPE = "data_type"
PROVIDER = "provider"
NAME = "name"
LOCATION = "location"
COUNTRY_CODE = "country_code"
SUBDIVISION_NAME = "subdivision_name"
MUNICIPALITY = "municipality"
BOUNDING_BOX = "bounding_box"
MINIMUM_LATITUDE = "minimum_latitude"
MAXIMUM_LATITUDE = "maximum_latitude"
MINIMUM_LONGITUDE = "minimum_longitude"
MAXIMUM_LONGITUDE = "maximum_longitude"
EXTRACTED_ON = "extracted_on"
URLS = "urls"
AUTO_DISCOVERY = "auto_discovery"
LICENSE = "license"
LATEST = "latest"

# OTHER
PATH_FROM_ROOT = "path_from_root"
LOAD_FUNC = "load_func"
ZIP = "zip"
JSON = "json"
