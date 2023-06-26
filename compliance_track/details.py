import os

import pandas as pd
from requests import RequestException

from compliance_track.validation import download_latest_dataset, get_sub_directories, get_exceeded_shape_dist
from tools.constants import GTFS
from tools.operations import get_sources

pd.options.mode.chained_assignment = None

# script to get details for rules under review
if __name__ == '__main__':
    # retrieve data
    dataset = get_sources(GTFS)
    rule_1_results = pd.DataFrame({
        'mdb_id': [],
        'sub_folders_titles': []
    })
    rule_2_results = pd.DataFrame({
        'mdb_id': [],
        'trip_id': [],
        'shape_id': [],
        'max_stop_times': [],
        'max_shapes': [],
        'relative_diff': [],
    })

    for data in dataset.values():
        mdb_id = data['mdb_source_id']
        try:
            dataset_path = download_latest_dataset(data)
        except RequestException:
            continue

        # get results for subfolders
        sub_folders_names = get_sub_directories(dataset_path)
        if len(sub_folders_names) > 0:
            sub_folders_names = ", ".join(sub_folders_names)
            rule_1_results = rule_1_results.append(pd.Series([mdb_id, sub_folders_names], index=rule_1_results.columns), ignore_index=True)

        # get results for exceeded max distance
        exceeded_max_dist = get_exceeded_shape_dist(dataset_path)
        if exceeded_max_dist is not None and len(exceeded_max_dist) > 0:
            exceeded_max_dist['mdb_id'] = mdb_id
            rule_2_results = pd.concat([rule_2_results, exceeded_max_dist], axis=0)

        # clean up
        os.remove(dataset_path)
        print(mdb_id)
    with pd.ExcelWriter('details.xlsx', engine='xlsxwriter') as writer:
        rule_1_results.to_excel(writer, sheet_name=f'Subfolders Details', index=False)
        rule_2_results.to_excel(writer, sheet_name=f'Max Dist Details', index=False)
    print('Completed. Check details.xlsx file.')
