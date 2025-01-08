import os
import json
import hashlib
import numpy as np


# OS constants
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT = "catalogs/sources/gtfs/schedule"
URL_STORAGE_PREFIX = """${{ env.URL_STORAGE_PREFIX }}"""
MATRIX_FILE = "urls_matrix.json"

# File constants
URLS = "urls"
DIRECT_DOWNLOAD = "direct_download"
LATEST = "latest"
AUTHENTICATION_TYPE = "authentication_type"
API_KEY_PARAMETER_NAME = "api_key_parameter_name"

# GitHub constants
MAX_JOB_NUMBER = 256

# Matrix constants
INCLUDE = "include"
DATA = "data"
BASE = "base"
HASH = "hash"

# Report constants
GET_URLS_REPORT = "get_urls_report.txt"

def create_matrix():
    """
    Create a matrix of URLs to be used in the workflow
    """
    print(f"ROOT => {ROOT}")
    files = os.listdir(os.path.join(ROOT, GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT))
    urls = {}
    for file in files:
        base = os.path.splitext(os.path.basename(file))[0]
        with open(os.path.join(ROOT, GTFS_SCHEDULE_CATALOG_PATH_FROM_ROOT, file), "r") as fp:
            file_json = json.load(fp)
            status = file_json.get("status")
            if status == "deprecated" or status == "inactive":
                continue
            direct_download_url = file_json.get(URLS, {}).get(DIRECT_DOWNLOAD)
            latest_url = file_json.get(URLS, {}).get(LATEST)
            authentication_type = file_json.get(URLS, {}).get(AUTHENTICATION_TYPE)
            api_key_parameter_name = file_json.get(URLS, {}).get(API_KEY_PARAMETER_NAME)
            if direct_download_url is None or latest_url is None:
                file_log = (
                    f"{base}: FAILURE! Direct download URL is {direct_download_url} and latest URL is {latest_url}. "
                    f"Both URLS must be defined to update the source latest URL.\n"
                )
            else:
                urls[base] = {
                    DIRECT_DOWNLOAD: direct_download_url,
                    LATEST: latest_url.replace(URL_STORAGE_PREFIX, ""),
                    AUTHENTICATION_TYPE: authentication_type,
                    API_KEY_PARAMETER_NAME: api_key_parameter_name
                }
                file_log = (
                    f"{base}: SUCCESS! Both direct download and latest URLs were fetched.\n"
                )
            with open(GET_URLS_REPORT, "a") as fp:
                fp.write(file_log)

    urls_data = []
    jobs = np.array_split(list(urls.keys()), min(MAX_JOB_NUMBER, len(list(urls.keys()))))
    jobs = [list(job) for job in jobs]
    for job in jobs:
        urls_data_string = ""
        while len(job) > 0:
            file_base = job.pop()
            file_information = {
                BASE: file_base,
                DIRECT_DOWNLOAD: urls[file_base][DIRECT_DOWNLOAD],
                LATEST: urls[file_base][LATEST],
            }
            if urls[file_base][AUTHENTICATION_TYPE]:
                file_information[API_KEY_PARAMETER_NAME] = urls[file_base][API_KEY_PARAMETER_NAME]
            if urls[file_base][API_KEY_PARAMETER_NAME]:
                file_information[API_KEY_PARAMETER_NAME] = urls[file_base][API_KEY_PARAMETER_NAME]
            urls_data_string = urls_data_string + json.dumps(
                file_information, separators=(",", ":")
            )
        job_data = {
            HASH: hashlib.sha1(urls_data_string.encode("utf-8")).hexdigest(),
            DATA: urls_data_string.replace("}{", "} {")
        }
        urls_data.append(job_data)
    matrix_data = {INCLUDE: urls_data}

    filepath = os.path.join(ROOT, MATRIX_FILE)
    print(f"Writing matrix to {filepath}")
    with open(filepath, "w") as fp:
        file_json = json.dump(matrix_data, fp)


if __name__ == "__main__":
    create_matrix()