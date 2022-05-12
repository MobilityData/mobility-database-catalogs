# The Mobility Database Catalogs

[![Integration tests](https://github.com/MobilityData/mobility-catalogs/actions/workflows/integration_tests.yml/badge.svg?branch=issue%2F343%2Fcatalogs-prototype)](https://github.com/MobilityData/mobility-catalogs/actions/workflows/integration_tests.yml) [![Unit tests](https://github.com/MobilityData/mobility-catalogs/actions/workflows/unit_tests.yml/badge.svg?branch=issue%2F343%2Fcatalogs-prototype)](https://github.com/MobilityData/mobility-catalogs/actions/workflows/unit_tests.yml) [![Export catalogs to CSV](https://github.com/MobilityData/mobility-catalogs/actions/workflows/export_to_csv.yml/badge.svg?branch=issue%2F343%2Fcatalogs-prototype)](https://github.com/MobilityData/mobility-catalogs/actions/workflows/export_to_csv.yml) [![Join the MobilityData chat](https://badgen.net/badge/slack/%20/green?icon=slack)](https://bit.ly/mobilitydata-slack)

The Mobility Database Catalogs is a project that provides a list of open mobility data sources from across the world, and the code to filter and manipulate them. [You can learn more about the Mobility Database here](https://database.mobilitydata.org/).

If you're only interested in browsing the sources, [download the CSV](https://storage.googleapis.com/storage/v1/b/mdb-csv/o/sources.csv?alt=media). You can cross reference IDs from the Mobility Database, TransitFeeds and Transitland with [this ID map spreadsheet](https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/edit?resourcekey#gid=1787149399).

[You can view our release plan for V1 here](https://github.com/MobilityData/mobility-database-catalogs/issues/30).

## Table of Contents

* [The Core Parts](#the-core-parts)
* [GTFS Schedule Data Structure](#gtfs-schedule-data-structure)
* [GTFS Realtime Data Structure](#gtfs-realtime-data-structure)
* [Installation](#installation)
* [Using the Mobility Database Catalogs](#using-the-mobility-database-catalogs)
* [Integration Tests](#integration-tests)
* [License](#license)
* [Contributing](#contributing)

## The Core Parts

### Catalogs

Contains the sources of the Mobility Database Catalogs. Every single source is represented by a JSON file. The sources can be aggregated by criteria using our `tools.operations` functions.

### Tools

Contains the tools to search, add and update the sources. The `tools.operations` module contains the project operations (get, add and update). The `tools.helpers` module contains helper functions that support the `tools.operations` module. The `tools.constants` module contains the project constants.

### Schemas

Contains the JSON schemas used to validate the sources in the integration tests.

## GTFS Schedule Data Structure

|     Field Name     |  Required from users  |                                                                              Definition                                                                             |
|:------------------:|:---------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------:
| MDB Source ID      | No - system generated | Unique numerical identifier.      |   |   |
| Data Type          | Yes                   | The data format that the source uses: GTFS.                                                                                                            |   |   |
| Country Code       | Yes                   | ISO 3166-1 alpha-2 code designating the country where the system is located. For a list of valid codes [see here](https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes).                                                    |   |   |
| Subdivision name   | Optional              | ISO 3166-2 subdivision name designating the subdivision (e.g province, state, region) where the system is located. For a list of valid names [see here](https://unece.org/trade/uncefact/unlocode-country-subdivisions-iso-3166-2).              |   |   |
| Municipality       | Optional              | Primary municipality in which the transit system is located.                                                                                                        |   |   |
| Provider           | Yes                   | Commonly used name of the transit provider.                                                                |   |   |
| Name               | Optional              | An optional description of the data source, e.g to specify if the data source is an aggregate of multiple providers, or which network is represented by the source. |   |   |
| Direct download URL | Yes                  | URL that automatically opens the source.                                                                                                                            |   |   |
| Latest dataset URL | No - system generated | A stable URL for the latest dataset of a source.                                                                                                                    |   |   |
| License URL        | Optional              | The transit provider’s license information.                                                                                                                         |   |   |
| Bounding box       | No - system generated | This is the bounding box of the data source when it was first added to the catalog. It includes the date and timestamp the bounding box was extracted on in UTC. If the bounding box information displays as "null", you can check any potential source errors with [the GTFS validator](https://github.com/MobilityData/gtfs-validator).     |   |   |

## GTFS Realtime Data Structure

This is still under discussion. [Please comment to share your thoughts](https://github.com/MobilityData/mobility-database-catalogs/issues/36). [You can view what is currently drafted in the working document](https://docs.google.com/document/d/1Mlz3AXHItInitsOEAKKi8hZV9d3t3gpFbyIZGm67ESU/edit#heading=h.i8ficnh0oxru).

## Installation

### Requirements

#### MacOs

To use and run this project properly, you must install all its requirements. Make sure Python 3.9+ and Pip are installed:
```
$ python3 --version
$ pip --version
```

If not, install them with:
```
$ brew install python3.9
$ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$ sudo python get-pip.py
```

Make sure both GDAL and RTree (Libspatialindex) libraries are installed on your computer, which are required for one of the project dependencies, the [GTFS Kit Library](https://pypi.org/project/gtfs-kit/):
```
$ brew install GDAL
$ brew install spatialindex
```

It is recommended to set up a virtual environment before installing the requirements. To set up and activate a Python 3.9 virtual environment, enter the following commands:
```
$ python3.9 -m venv env
$ source env/bin/activate
```

Once your virtual environment is activated, enter the following command to install the project requirements:
```
(env) $ pip install -r requirements.txt
```

To deactivate your virtual environment, enter the following command:
```
(env) $ deactivate
```

If you are working with IntelliJ or PyCharm, it is possible to use this virtual environment within the IDE. To do so, follow the instructions to create a virtual environment [here](https://www.jetbrains.com/help/idea/creating-virtual-environment.html).

### Repository

To use it, clone the project on your local machine using HTTP with the following commands:
```
$ git clone https://github.com/MobilityData/mobility-database-catalogs.git
$ cd mobility-database-catalogs
```

## Using the Mobility Database Catalogs

### Setup
Follow the steps described in the [Installation](#installation) section.

### Run it
To use the Mobility Database Catalogs, go to the cloned project root, open the Python interpreter and import the project operations:
```
$ cd mobility-catalogs
$ python
>>> from tools.operations import *
```

To get the sources:
```
>>> get_sources()
```

To get the sources by subdivision name, where `$SUBDIVISION_NAME` is a ISO 3166-2 subdivision name:
```
>>> get_sources_by_subdivision_name(subdivision_name=$SUBDIVISION_NAME)
```

To get the sources by country code, where `$COUNTRY_CODE` is a ISO 3166-1 alpha-2 code:
```
>>> get_sources_by_country_code(country_code=$COUNTRY_CODE)

```

To get the sources by bounding box, where `$MINIMUM_LATITUDE` `$MAXIMUM_LATITUDE` `$MINIMUM_LONGITUDE` and `$MAXIMUM_LONGITUDE` are expressed as floats:
```
>>> get_sources_by_bounding_box(
        minimum_latitude=$MINIMUM_LATITUDE,
        maximum_latitude=$MAXIMUM_LATITUDE,
        minimum_longitude=$MINIMUM_LONGITUDE,
        maximum_longitude=$MAXIMUM_LONGITUDE
    )
```


To add a new GTFS Schedule source:
```
>>> add_gtfs_schedule_source(
        provider=$YOUR_SOURCE_PROVIDER_NAME,
        country_code=$YOUR_SOURCE_COUNTRY_CODE,
        direct_download_url=$YOUR_SOURCE_DIRECT_DOWNLOAD_URL,
        subdivision_name=$OPTIONAL_SUBDIVISION_NAME,
        municipality=$OPTIONAL_MUNICIPALITY,
        license_url=$OPTIONAL_LICENSE_URL,
        name=$OPTIONAL_SOURCE_NAME
    )
```

To add a new GTFS Realtime source:
```
>>> add_gtfs_realtime_source(
        provider=$YOUR_SOURCE_PROVIDER_NAME,
        static_reference=$OPTIONAL_STATIC_REFERENCE_NUMERICAL_ID,
        vehicle_positions_url=$OPTIONAL_VEHICLE_POSITIONS_URL,
        trip_updates_url=$OPTIONAL_TRIP_UPDATES_URL,
        service_alerts_url=$OPTIONAL_SERVICE_ALERTS_URL,
        name=$OPTIONAL_SOURCE_NAME
    )
```

To update a GTFS Schedule source:
```
>>> update_gtfs_schedule_source(
        mdb_source_id=$YOUR_SOURCE_NUMERICAL_ID,
        provider=$OPTIONAL_SOURCE_PROVIDER_NAME,
        name=$OPTIONAL_SOURCE_NAME,
        country_code=$OPTIONAL_SOURCE_COUNTRY_CODE,
        subdivision_name=$OPTIONAL_SOURCE_SUBDIVISION_NAME,
        municipality=$OPTIONAL_SOURCE_MUNICIPALITY,
        direct_download_url=$OPTIONAL_SOURCE_DIRECT_DOWNLOAD_URL,
        license_url=$OPTIONAL_LICENSE_URL
    )
```

To update a GTFS Realtime source:

```
>>> update_gtfs_realtime_source(
        mdb_source_id=$YOUR_SOURCE_NUMERICAL_ID,
        provider=$OPTIONAL_SOURCE_PROVIDER_NAME,
        static_reference=$OPTIONAL_STATIC_REFERENCE_NUMERICAL_ID,
        vehicle_positions_url=$OPTIONAL_VEHICLE_POSITIONS_URL,
        trip_updates_url=$OPTIONAL_TRIP_UPDATES_URL,
        service_alerts_url=$OPTIONAL_SERVICE_ALERTS_URL,
        name=$OPTIONAL_SOURCE_NAME
    )
```


## Integration Tests

In order to avoid invalid sources in the Mobility Database Catalogs, any modification made in the repository, addition or update, must pass the integration tests before being merged into the project. The integration tests are listed in the [Test Integration](/tests/test_integration.py) module

## License

Code licensed under the [Apache 2.0 License](http://www.apache.org/licenses/LICENSE-2.0).

All of the Mobility Database catalog's metadata is made available under [Creative Commons CC0 (CC0)](https://creativecommons.org/publicdomain/zero/1.0/legalcode). Individual transit data sources are subject to the terms & conditions of their own respective data provider. If you are a transit provider and there is a data source that should not be included in the repository, please contact emma@mobilitydata.org and we'll remove it as soon as possible.

## Contributing

We welcome contributions to the project! Please check out our [Contribution guidelines](/CONTRIBUTING.md) for details.
