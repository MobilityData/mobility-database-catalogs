import json
import os


def aggregate(catalog_root):
    catalog = []
    for path, sub_dirs, files in os.walk(catalog_root):
        for file in files:
            with open(os.path.join(path, file)) as fp:
                catalog.append(json.load(fp))
    return catalog


def is_overlapping_bounding_box(
    source_minimum_latitude,
    source_maximum_latitude,
    source_minimum_longitude,
    source_maximum_longitude,
    filter_minimum_latitude,
    filter_maximum_latitude,
    filter_minimum_longitude,
    filter_maximum_longitude,
):
    return is_overlapping_bounding_edge(
        source_minimum_latitude,
        source_maximum_latitude,
        filter_minimum_latitude,
        filter_maximum_latitude,
    ) and is_overlapping_bounding_edge(
        source_minimum_longitude,
        source_maximum_longitude,
        filter_minimum_longitude,
        filter_maximum_longitude,
    )


def is_overlapping_bounding_edge(
    source_minimum, source_maximum, filter_minimum, filter_maximum
):
    return (
        source_maximum >= filter_minimum and filter_maximum >= source_minimum
        if source_minimum is not None and source_maximum is not None
        else False
    )
