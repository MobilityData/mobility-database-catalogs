# DATA TYPES
GTFS = "gtfs"
GTFS_RT = "gtfs-rt"

# GTFS CONSTANTS
STOP_LAT = "stop_lat"
STOP_LON = "stop_lon"
START_SERVICE_AREA_ID = "start_service_area_id"
START_SERVICE_AREA_RADIUS = "start_service_area_radius"
START_DATE = "start_date"
END_DATE = "end_date"
DATE = "date"
GTFS_DATE_FORMAT = "%Y%m%d"
PATHWAYS_TXT = "pathways.txt"
FARES_ATTRIBUTES_TXT = "fares_attributes.txt"
FARES_PRODUCTS_TXT = "fares_products.txt"
LOCATION_GROUPS_TXT = "location_groups.txt"
LOCATIONS_GEOJSON = "locations.geojson"
BOOKINGS_RULES_TXT = "bookings_rules.txt"
AREAS_TXT = "areas.txt"
STOP_TIMES_TXT = "stop_times.txt"
CALENDAR_TXT = "calendar.txt"

# FILENAME TEMPLATE
MDB_SOURCE_FILENAME = "{country_code}-{subdivision_name}-{provider}-{data_type}-{mdb_source_id}.{extension}"

# ARCHIVES TEMPLATE
MDB_ARCHIVES_LATEST_URL_TEMPLATE = (
    "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/{filename}?alt=media"
)

# CATALOG CONSTANTS
ROOT = "root"
PATH = "path"
ENTITY_CLS = "entity_cls"
ID_KEY = "id_key"
UNKNOWN = "unknown"
FILENAME = "filename"
CATALOGS = "catalogs"
ALL = "all"

# CATALOG ROOTS
SOURCE_CATALOG_PATH_FROM_ROOT = "catalogs/sources"
GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/schedule"
GTFS_REALTIME_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/realtime"
GTFS_SCHEDULE_CATALOG_PATH = "gtfs/schedule"
GTFS_REALTIME_CATALOG_PATH = "gtfs/realtime"

# SCHEMAS FILES
GTFS_SCHEDULE_SOURCE_SCHEMA_PATH_FROM_ROOT = "schemas/gtfs_schedule_source_schema.json"
GTFS_REALTIME_SOURCE_SCHEMA_PATH_FROM_ROOT = "schemas/gtfs_realtime_source_schema.json"

# GTFS SCHEDULE & REALTIME CONSTANTS
MDB_SOURCE_ID = "mdb_source_id"
DATA_TYPE = "data_type"
PROVIDER = "provider"
NAME = "name"
LOCATION = "location"
COUNTRY_CODE = "country_code"
SUBDIVISION_NAME = "subdivision_name"
MUNICIPALITY = "municipality"
BOUNDING_BOX = "bounding_box"
STATUS = "status"
ACTIVE = "active"
DEPRECATED = "deprecated"
INACTIVE = "inactive"
DEVELOPMENT = "development"
FEATURES = "features"
FARES_V2 = "fares-v2"
FARES_V1 = "fares-v1"
FLEX_V2 = "flex-v2"
FLEX_V1 = "flex-v1"
PATHWAYS = "pathways"
OCCUPANCY = "occupancy"
MINIMUM_LATITUDE = "minimum_latitude"
MAXIMUM_LATITUDE = "maximum_latitude"
MINIMUM_LONGITUDE = "minimum_longitude"
MAXIMUM_LONGITUDE = "maximum_longitude"
EXTRACTED_ON = "extracted_on"
EXTRACTED_FILESIZE= "extracted_filesize"
EXTRACTED_CALENDAR_START = "extracted_calendar_start"
EXTRACTED_CALENDAR_END = "extracted_calendar_end"
URLS = "urls"
DIRECT_DOWNLOAD = "direct_download"
LICENSE = "license"
LATEST = "latest"
STATIC_REFERENCE = "static_reference"
AUTHENTICATION_TYPE = "authentication_type"
AUTHENTICATION_INFO = "authentication_info"
API_KEY_PARAMETER_NAME = "api_key_parameter_name"
API_KEY_PARAMETER_VALUE = "api_key_parameter_value"
NOTE = "note"
ENTITY_TYPE = "entity_type"
FEED_CONTACT_EMAIL = "feed_contact_email"
REDIRECTS = "redirect"
REDIRECT_ID = "id"
REDIRECT_COMMENT = "comment"
IS_OFFICIAL = "is_official"

# TIME CONSTANTS
SIX_MONTHS_IN_WEEKS = 26

# OTHER
PATH_FROM_ROOT = "path_from_root"
LOAD_FUNC = "load_func"
ZIP = "zip"
JSON = "json"

#browser header
FALLBACK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/132.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,image/apng,*/*;q=0.8,"
                      "application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "application/zip",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
}
