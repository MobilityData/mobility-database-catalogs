import json
from zipfile import ZipFile

import pandas as pd

from update_gtfs_schedule_sources import has_extension_file


def extension_file_has_columns(file_path, extension_file_name, columns):
    zip_file = ZipFile(file_path)
    if has_extension_file(zip_file, extension_file_name):
        dataframe = pd.read_csv(zip_file.open(extension_file_name), low_memory=False)
        columns = [columns] if isinstance(columns, str) else columns
        columns_existence = all([column in dataframe.columns for column in columns])
        return columns_existence, dataframe

    return False, None


def has_defined_values(file_path, extension_file_name, column, check_undefined=False):
    has_column, dataframe = extension_file_has_columns(file_path, extension_file_name, column)
    if has_column:
        return dataframe[column].isna().all() if check_undefined else dataframe[column].notna().all()
    return False


def cross_validate_blocks(file_path):
    has_ids_in_trips, trips_dataframe = extension_file_has_columns(file_path, "trips.txt", ["block_id", "trip_id"])
    has_id_in_frequencies, frequencies_dataframe = extension_file_has_columns(file_path, "frequencies.txt", "trip_id")
    if not (has_ids_in_trips and has_id_in_frequencies):
        return False
    return trips_dataframe.trip_id.isin(frequencies_dataframe.trip_id).all()


def current_validator(report_path, validator_name, filename, field_name):
    try:
        with open(report_path, mode='r') as file:
            report_results = json.load(file)
    except FileNotFoundError:
        return False
    report_results = pd.DataFrame(report_results['notices'])

    if 'code' not in report_results or not (report_results.code == validator_name).any():
        return True

    report_results = pd.DataFrame(
        list(report_results[report_results.code == validator_name].sampleNotices)[0])

    if field_name is None:
        return filename is None or not (report_results.filename == filename).any()

    if 'fieldName' not in report_results or 'filename' not in report_results:
        return False

    return not ((report_results.fieldName == field_name).any() and (report_results.filename == filename).any())


def validate_sub_directory_exists(file_path):
    return any([name.endswith('/') for name in ZipFile(file_path).namelist()])


def validate_shape_dist_traveled(file_path):
    # read stop_times.txt and extract shape_dist_traveled
    has_stop_times, stop_times_df = extension_file_has_columns(file_path, 'stop_times.txt', 'shape_dist_traveled')
    has_shapes, shapes_df = extension_file_has_columns(file_path, 'shapes.txt', 'shape_dist_traveled')
    if not (has_shapes and has_stop_times):
        return False
    try:
        return stop_times_df.shape_dist_traveled.max() > shapes_df.shape_dist_traveled.max()
    except TypeError:
        # in the case where all values in the column are empty
        return False
