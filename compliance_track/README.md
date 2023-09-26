# Best practices and bad practices tracking

This is a Python script to track usage of best practices and bad practices in the Mobility Database feeds.

## Table of Contents

* [Installation](#installation)
* [Run the Script](#run-the-script)

## Installation
### Gcloud installation
Install the `gcloud CLI` following the instructions in the [official documentation](https://cloud.google.com/sdk/docs/install) and authenticate yourself.

Once it's completed, make sure you can access the [mobilitydata-gtfs-validation-results bucket](https://console.cloud.google.com/storage/browser/mobilitydata-gtfs-validation-results;tab=objects?forceOnBucketsSortingFiltering=true&project=md-poc-playground&supportedpurview=project&prefix=&forceOnObjectsSortingFiltering=false).

### Python environment
Create a Python virtual environment as described [here](https://github.com/MobilityData/mobility-database-catalogs/blob/main/README.md#installation).
Once the described installation steps are successfully completed you should install `xlsxwriter`:
```sh
$ pip install xlsxwriter
```

### Retrieve reports from the Google Cloud bucket
After activating the virtual environment and being in the root directory of the mobility-database-catalog repository, run the following commands:
```sh
$ pip install gsutil
$ gsutil -m cp -r "gs://mobilitydata-gtfs-validation-results/reports/2023-06-06T02:45/cebc62a4-ed30-4d1b-9816-53b3376baabc" .
```

## Run the script
Simply run:
```sh
$ python3 -m compliance_track.main 
```
To produce the report containing details about practices under discussion run:
```sh
$ python3 -m compliance_track.details
```
