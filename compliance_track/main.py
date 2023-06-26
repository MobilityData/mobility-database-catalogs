import os

import numpy as np
import pandas as pd
from requests import RequestException

from compliance_track.constants import BEST_PRACTICES_RULES, GC_COPY_PATH, BAD_PRACTICES_RULES, VALIDATOR
from compliance_track.validation import download_latest_dataset
from tools.constants import GTFS
from tools.operations import get_sources

pd.options.mode.chained_assignment = None


def validate_practices(practices, results):
    for index, best_practice in practices.iterrows():
        results.loc[results.mdb_id == mdb_id, best_practice.rule_id] = \
            best_practice.validator(dataset_path, report_folder_path, best_practice.file)


def init_results_container(practices):
    results = pd.DataFrame(columns=["mdb_id"] + list(practices.rule_id))
    results.mdb_id = list(dataset.keys())
    results[practices.rule_id] = False
    return results


def write_results(file_writer, practices, results, prefix):
    practices.drop(columns=[VALIDATOR]).to_excel(file_writer, sheet_name=f'{prefix} Rules', index=False)
    results.to_excel(file_writer, sheet_name=f'{prefix} Results', index=False)
    pd.DataFrame(results.count()).T.to_excel(file_writer, sheet_name=f'{prefix} Count', index=False)


def format_results(practices, results):
    final_results = pd.DataFrame(columns=practices.rule_id)
    for rule in practices.rule_id:
        mdb_ids = list(results[results[rule]].mdb_id)
        if len(mdb_ids) == 0:
            continue
        if len(mdb_ids) > len(final_results):
            final_results = final_results.reindex(index=range(len(mdb_ids)))
        else:
            mdb_ids += [np.nan for _ in range(len(final_results) - len(mdb_ids))]
        final_results[rule] = mdb_ids
    return final_results


if __name__ == '__main__':
    # retrieve report folders available
    if not os.path.exists(GC_COPY_PATH):
        print('Please import report data using gsutil as described in README.md. Make sure the data is included in the'
              ' root of mobility-database-catalogs.')
        exit(1)
    report_results_folders = os.listdir(GC_COPY_PATH)
    report_results_folders = [f'{GC_COPY_PATH}/{folder_name}/report-output-4.1.0/report.json'
                              for folder_name in report_results_folders]

    # retrieve data
    dataset = get_sources(GTFS)

    best_practice_results = init_results_container(BEST_PRACTICES_RULES)
    bad_practice_results = init_results_container(BAD_PRACTICES_RULES)

    for data in dataset.values():
        mdb_id = data['mdb_source_id']

        report_folder_path = [folder_name for folder_name in report_results_folders
                              if len(folder_name.split('/')) > 1 and folder_name.split('/')[1].endswith(f'-{mdb_id}')]
        if len(report_folder_path) != 1:
            continue

        report_folder_path = report_folder_path[0]

        # retrieve data
        try:
            dataset_path = download_latest_dataset(data)
        except RequestException as e:
            continue

        # validate compliance
        validate_practices(BEST_PRACTICES_RULES, best_practice_results)
        validate_practices(BAD_PRACTICES_RULES, bad_practice_results)

        # clean up
        os.remove(dataset_path)
        print(mdb_id)

    # formatting and saving the results
    final_results_best_practices = format_results(BEST_PRACTICES_RULES, best_practice_results)
    final_results_bad_practices = format_results(BAD_PRACTICES_RULES, bad_practice_results)

    # write results
    with pd.ExcelWriter('output.xlsx', engine='xlsxwriter') as writer:
        write_results(writer, BEST_PRACTICES_RULES, final_results_best_practices, 'Best Practices')
        write_results(writer, BAD_PRACTICES_RULES, final_results_bad_practices, 'Practice Review')
    print('Completed. Check output.xlsx file.')
