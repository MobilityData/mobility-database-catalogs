import os
from jsonschema import validate
from tools.helpers import from_json
from tools.operations import get_sources
from tools.constants import (
    GTFS,
    GTFS_SCHEDULE_SOURCE_SCHEMA_PATH_FROM_ROOT,
    MDB_SOURCE_ID,
    URLS,
    DIRECT_DOWNLOAD,
    ALL,
    GTFS_RT,
    GTFS_REALTIME_SOURCE_SCHEMA_PATH_FROM_ROOT,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# Allow list of stable_ids that are intentionally missing from the catalogs.
ALLOWED_MISSING_STABLE_IDS = {3504, 3505}


def test_catalogs_sources_gtfs_schedule_json_schema():
    source_schema_path = os.path.join(
        PROJECT_ROOT, GTFS_SCHEDULE_SOURCE_SCHEMA_PATH_FROM_ROOT
    )
    schema = from_json(source_schema_path)
    for source in get_sources(data_type=GTFS).values():
        validate(instance=source, schema=schema)


def test_catalogs_sources_gtfs_schedule_source_ids_uniqueness():
    source_ids = [
        source[MDB_SOURCE_ID] for source in get_sources(data_type=GTFS).values()
    ]
    assert len(set(source_ids)) == len(source_ids)


def test_catalogs_sources_gtfs_realtime_json_schema():
    source_schema_path = os.path.join(
        PROJECT_ROOT, GTFS_REALTIME_SOURCE_SCHEMA_PATH_FROM_ROOT
    )
    schema = from_json(source_schema_path)
    for source in get_sources(data_type=GTFS_RT).values():
        validate(instance=source, schema=schema)


def test_catalogs_sources_gtfs_realtime_source_ids_uniqueness():
    source_ids = [
        source[MDB_SOURCE_ID] for source in get_sources(data_type=GTFS_RT).values()
    ]
    assert len(set(source_ids)) == len(source_ids)


def test_catalogs_gtfs_source_ids_are_incremental():
    source_ids = [
        source[MDB_SOURCE_ID] for source in get_sources(data_type=ALL).values()
    ]
    expected_ids = set(range(1, max(source_ids) + 1)) - ALLOWED_MISSING_STABLE_IDS
    missing_ids = sorted(expected_ids - set(source_ids))
    assert not missing_ids, (
        f"Source IDs missing from the sequence: {missing_ids}. "
        f"Add them to ALLOWED_MISSING_STABLE_IDS if intentional."
    )


def test_catalogs_sources_gtfs_schedule_direct_download_urls_uniqueness():
    direct_download_urls = [
        source[URLS][DIRECT_DOWNLOAD] for source in get_sources(data_type=GTFS).values()
    ]
    assert len(set(direct_download_urls)) == len(direct_download_urls)
