import json
from zipfile import ZipFile

import pandas as pd

from tools.constants import AUTHENTICATION_TYPE, API_KEY_PARAMETER_NAME, API_KEY_PARAMETER_VALUE
from tools.helpers import download_dataset
from update_gtfs_schedule_sources import has_extension_file


def download_latest_dataset(data):
    urls = data['urls']
    latest_url = urls['latest']

    # retrieving auth data
    authentication_type, api_key_parameter_name, api_key_parameter_value = None, None, None
    if AUTHENTICATION_TYPE in urls:
        authentication_type = urls[AUTHENTICATION_TYPE]
    if API_KEY_PARAMETER_NAME in urls:
        api_key_parameter_name = urls[API_KEY_PARAMETER_NAME]
    if API_KEY_PARAMETER_VALUE in urls:
        api_key_parameter_value = urls[API_KEY_PARAMETER_VALUE]

    # retrieve data
    return download_dataset(latest_url, authentication_type, api_key_parameter_name,
                            api_key_parameter_value)


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


def get_sub_directories(file_path):
    return [name for name in ZipFile(file_path).namelist() if name.endswith('/')]


def validate_sub_directory_exists(file_path):
    return len(get_sub_directories(file_path)) > 0


def get_exceeded_shape_dist(file_path):
    try:
        # retrieve dataframes
        _, trips_df = extension_file_has_columns(file_path, 'trips.txt', 'shape_id')
        has_stop_times, stop_times_df = extension_file_has_columns(file_path, 'stop_times.txt', 'shape_dist_traveled')
        has_shapes, shapes_df = extension_file_has_columns(file_path, 'shapes.txt', 'shape_dist_traveled')
        if not (has_shapes and has_stop_times):
            return None

        # merge data on shape_id and trip_id
        stop_times_trips_merge = pd.merge(
            trips_df[['trip_id', 'shape_id']],
            stop_times_df[['trip_id', 'shape_dist_traveled']],
            on='trip_id',
            how='inner'
        )[['trip_id', 'shape_id', 'shape_dist_traveled']] \
            .groupby(['trip_id', 'shape_id'])['shape_dist_traveled'].max().reset_index() \
            .rename(columns={'shape_dist_traveled': 'max_stop_times'})
        merged_df = pd.merge(
            stop_times_trips_merge,
            shapes_df[['shape_id', 'shape_dist_traveled']].groupby(['shape_id']).max().reset_index(),
            on='shape_id',
            how='inner'
        )[['trip_id', 'shape_id', 'max_stop_times', 'shape_dist_traveled']] \
            .rename(columns={'shape_dist_traveled': 'max_shapes'})

        # add column with relative difference
        results = merged_df[merged_df.max_stop_times > merged_df.max_shapes]
        results['relative_diff'] = (results.max_stop_times - results.max_shapes) / results.max_shapes
        return results
    except Exception:
        return None


def validate_shape_dist_traveled(file_path):
    try:
        return len(get_exceeded_shape_dist(file_path)) > 0
    except Exception:
        return False
