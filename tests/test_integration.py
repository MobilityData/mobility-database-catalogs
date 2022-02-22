import os
from jsonschema import validate
from tools.helpers import from_json
from tools.operations import get_sources
from tools.constants import (
    GTFS,
    GTFS_SCHEDULES_SOURCE_SCHEMA_PATH_FROM_ROOT,
    MDB_SOURCE_ID,
    URLS,
    AUTO_DISCOVERY,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def test_catalogs_static_gtfs_json_schema():
    static_source_schema_path = os.path.join(
        PROJECT_ROOT, GTFS_SCHEDULES_SOURCE_SCHEMA_PATH_FROM_ROOT
    )
    schema = from_json(static_source_schema_path)
    for source in get_sources(data_type=GTFS):
        validate(instance=source, schema=schema)


def test_catalogs_static_gtfs_source_ids_uniqueness():
    source_ids = [source[MDB_SOURCE_ID] for source in get_sources(data_type=GTFS)]
    assert len(set(source_ids)) == len(source_ids)


def test_catalogs_static_gtfs_source_ids_are_incremental():
    source_ids = [source[MDB_SOURCE_ID] for source in get_sources(data_type=GTFS)]
    assert sorted(source_ids) == list(range(1, len(source_ids) + 1))


def test_catalogs_static_gtfs_auto_discovery_urls_uniqueness():
    auto_discovery_urls = [
        source[URLS][AUTO_DISCOVERY] for source in get_sources(data_type=GTFS)
    ]
    assert len(set(auto_discovery_urls)) == len(auto_discovery_urls)
