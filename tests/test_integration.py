import os
from collections import Counter, defaultdict
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


def get_duplicates(values):
    return sorted(value for value, count in Counter(values).items() if count > 1)


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
    duplicate_ids = get_duplicates(source_ids)
    assert not duplicate_ids, f"Duplicate GTFS Schedule source IDs: {duplicate_ids}"


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
    duplicate_ids = get_duplicates(source_ids)
    assert not duplicate_ids, f"Duplicate GTFS Realtime source IDs: {duplicate_ids}"


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
    source_ids_by_url = defaultdict(list)
    for source in get_sources(data_type=GTFS).values():
        source_ids_by_url[source[URLS][DIRECT_DOWNLOAD]].append(source[MDB_SOURCE_ID])
    duplicates = {
        url: sorted(source_ids)
        for url, source_ids in source_ids_by_url.items()
        if len(source_ids) > 1
    }
    assert not duplicates, (
        f"Source IDs sharing a direct download URL: {sorted(duplicates.values())}"
    )
