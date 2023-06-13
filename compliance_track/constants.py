from zipfile import ZipFile

import pandas as pd

from compliance_track.validation import has_defined_values, extension_file_has_columns, cross_validate_blocks, \
    current_validator, validate_sub_directory_exists, validate_shape_dist_traveled

FILE = "file"
FIELD = "field"
RULE_TO_COUNT = "rule to count instance"
VALIDATOR = "validator"
RULE_ID = "rule_id"
GC_COPY_PATH = "cebc62a4-ed30-4d1b-9816-53b3376baabc"

BEST_PRACTICES_RULES = pd.DataFrame([
    {
        FILE: "routes.txt",
        FIELD: "route_short_name",
        RULE_TO_COUNT: "route_short_name is !empty AND routes.route_long_name is empty",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        has_defined_values(file_path, extension_file, "route_short_name") and
        has_defined_values(file_path, extension_file, "route_long_name", check_undefined=True)
    },
    {
        FILE: "routes.txt",
        FIELD: "agency_id",
        RULE_TO_COUNT: "agency_id is !empty AND there is only one agency_id in agency.txt",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_field', extension_file, 'agency_id')
    },
    {
        FILE: "agency.txt",
        FIELD: "agency_id",
        RULE_TO_COUNT: "agency_id is !empty AND there is only one agency_id in agency.txt",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_field', extension_file, 'agency_id')
    },
    {
        FILE: "fare_attributes.txt",
        FIELD: "agency_id",
        RULE_TO_COUNT: "agency_id is !empty AND there is only one agency_id in agency.txt",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_field', extension_file, 'agency_id')
    },
    {
        FILE: "feed_info.txt",
        FIELD: "",
        RULE_TO_COUNT: "feed_info.txt is !empty AND there is no translations.txt file",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_file', extension_file, None)
    },
    {
        FILE: "feed_info.txt",
        FIELD: "feed_start_date",
        RULE_TO_COUNT: "field is !empty",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_field', extension_file, 'feed_start_date')
    },
    {
        FILE: "feed_info.txt",
        FIELD: "feed_end_date",
        RULE_TO_COUNT: "field is !empty",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_field', extension_file, 'feed_end_date')
    },
    {
        FILE: "feed_info.txt",
        FIELD: "feed_version",
        RULE_TO_COUNT: "field is !empty",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_recommended_field', extension_file, 'feed_version')
    },
    {
        FILE: "feed_info.txt",
        FIELD: "feed_contact_email",
        RULE_TO_COUNT: "feed_contact_email is !empty AND there is no feed_contact_url",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        has_defined_values(file_path, extension_file, "feed_contact_url", check_undefined=True)
        and has_defined_values(file_path, extension_file, "feed_contact_email")
    },
    {
        FILE: "feed_info.txt",
        FIELD: "feed_contact_url",
        RULE_TO_COUNT: "feed_contact_url is !empty AND there is no feed_contact_email",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        has_defined_values(file_path, extension_file, "feed_contact_email", check_undefined=True)
        and has_defined_values(file_path, extension_file, "feed_contact_url")
    },
    {
        FILE: "stop_times.txt",
        FIELD: "timepoint",
        RULE_TO_COUNT: "column exists",
        VALIDATOR: lambda file_path, report_folder_path, extension_file:
        current_validator(report_folder_path, 'missing_timepoint_column', extension_file, None)
    },
    {
        FILE: "trips.txt",
        FIELD: "block_id",
        RULE_TO_COUNT: "block_id is !empty AND the row with block_id has a trip_id that is included in frequences.txt",
        VALIDATOR: lambda file_path, report_folder_path, extension_file: cross_validate_blocks(file_path)
    }
])

BEST_PRACTICES_RULES[RULE_ID] = [f"rule_{i}" for i in range(1, len(BEST_PRACTICES_RULES) + 1)]


BAD_PRACTICES_RULES = pd.DataFrame([
    {
        FILE: "zip subfolder within feed",
        FIELD: "",
        RULE_TO_COUNT: "zip subfolder exists",
        VALIDATOR: lambda file_path, _, __: validate_sub_directory_exists(file_path)
    },
    {
        FILE: "",
        FIELD: "shape_dist_traveled",
        RULE_TO_COUNT: "stop_times.shape_dist_traveled exceeds maximum shapes.shape_dist_traveled",
        VALIDATOR: lambda file_path, _, __: validate_shape_dist_traveled(file_path)
    },
])
BAD_PRACTICES_RULES[RULE_ID] = [f"rule_{i}" for i in range(1, len(BAD_PRACTICES_RULES) + 1)]
