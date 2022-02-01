import os
from jsonschema import validate
from tools.helpers import from_json
from tools.operations import get_sources
from tools.constants import GTFS, GTFS_SCHEDULES_SOURCE_SCHEMA_PATH_FROM_ROOT

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def test_catalogs_static_gtfs_json_schema():
    static_source_schema_path = os.path.join(
        PROJECT_ROOT, GTFS_SCHEDULES_SOURCE_SCHEMA_PATH_FROM_ROOT
    )
    schema = from_json(static_source_schema_path)
    for source in get_sources(data_type=GTFS):
        validate(instance=source, schema=schema)
