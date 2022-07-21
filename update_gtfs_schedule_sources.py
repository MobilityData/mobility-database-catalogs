import os
from datetime import datetime, timedelta
import pandas as pd
from zipfile import ZipFile
from tools.operations import get_latest_datasets, update_gtfs_schedule_source, GTFS
from tools.helpers import download_dataset
from tools.constants import (
    PATHWAYS_TXT,
    FARES_ATTRIBUTES_TXT,
    FARES_PRODUCTS_TXT,
    LOCATION_GROUPS_TXT,
    LOCATIONS_GEOJSON,
    BOOKINGS_RULES_TXT,
    AREAS_TXT,
    STOP_TIMES_TXT,
    CALENDAR_TXT,
    START_SERVICE_AREA_ID,
    START_SERVICE_AREA_RADIUS,
    END_DATE,
    GTFS_DATE_FORMAT,
    SIX_MONTHS_IN_WEEKS,
    PATHWAYS,
    FARES_V1,
    FARES_V2,
    FLEX_V1,
    FLEX_V2,
    INACTIVE,
)


def has_at_least_2_rows(zip_file, extension_file_name):
    return has_at_least_n_rows(zip_file, extension_file_name, 2)


def has_at_least_4_rows(zip_file, extension_file_name):
    has_at_least_n_rows(zip_file, extension_file_name, 4)


def has_at_least_n_rows(zip_file, extension_file_name, n_rows):
    return (
        sum(1 for _ in zip_file.open(extension_file_name)) >= n_rows
        if has_extension_file(
            zip_file=zip_file, extension_file_name=extension_file_name
        )
        else False
    )


def has_defined_values(zip_file, extension_file_name, columns):
    result = False
    if has_extension_file(zip_file=zip_file, extension_file_name=extension_file_name):
        dataframe = pd.read_csv(zip_file.open(extension_file_name))
        result = any(
            [
                dataframe[column].notna().any()
                for column in columns
                if column in dataframe
            ]
        )
    return result


def has_recent_service_date(zip_file):
    result = False
    if has_extension_file(zip_file=zip_file, extension_file_name=CALENDAR_TXT):
        dataframe = pd.read_csv(zip_file.open(CALENDAR_TXT))
        if END_DATE in dataframe:
            dataframe = dataframe.loc[dataframe[END_DATE].notna()]
            dataframe[END_DATE] = pd.to_datetime(
                dataframe[END_DATE], format=GTFS_DATE_FORMAT, errors="coerce"
            )
            result = (
                dataframe[END_DATE]
                .loc[
                    dataframe[END_DATE]
                    > (datetime.now() - timedelta(weeks=SIX_MONTHS_IN_WEEKS))
                ]
                .any()
            )
    return result


def has_extension_file(zip_file, extension_file_name):
    return extension_file_name in zip_file.namelist()


if __name__ == "__main__":
    latest_datasets = get_latest_datasets(GTFS)

    for mdb_source_id, latest_url in latest_datasets.items():
        dataset_path = download_dataset(latest_url)
        dataset_zip = ZipFile(dataset_path)

        dataset_features = []
        if has_at_least_2_rows(zip_file=dataset_zip, extension_file_name=PATHWAYS_TXT):
            dataset_features.append(PATHWAYS)
        if has_at_least_2_rows(
            zip_file=dataset_zip, extension_file_name=FARES_ATTRIBUTES_TXT
        ):
            dataset_features.append(FARES_V1)
        if has_at_least_2_rows(
            zip_file=dataset_zip, extension_file_name=FARES_PRODUCTS_TXT
        ):
            dataset_features.append(FARES_V2)
        if has_extension_file(
            zip_file=dataset_zip, extension_file_name=AREAS_TXT
        ) and has_defined_values(
            zip_file=dataset_zip,
            extension_file_name=STOP_TIMES_TXT,
            columns=[START_SERVICE_AREA_ID, START_SERVICE_AREA_RADIUS],
        ):
            dataset_features.append(FLEX_V1)
        if (
            has_at_least_2_rows(
                zip_file=dataset_zip, extension_file_name=LOCATION_GROUPS_TXT
            )
            or has_at_least_2_rows(
                zip_file=dataset_zip, extension_file_name=LOCATIONS_GEOJSON
            )
            or has_at_least_4_rows(
                zip_file=dataset_zip, extension_file_name=BOOKINGS_RULES_TXT
            )
        ):
            dataset_features.append(FLEX_V2)
        # If no feature is found, we assign None so we don't update the source features.
        if len(dataset_features) == 0:
            dataset_features = None

        dataset_status = None
        if not has_recent_service_date(zip_file=dataset_zip):
            dataset_status = INACTIVE

        # Delete the downloaded dataset because we don't need it anymore
        os.remove(dataset_path)

        # Update the source
        update_gtfs_schedule_source(
            mdb_source_id=mdb_source_id,
            features=dataset_features,
            status=dataset_status,
        )
