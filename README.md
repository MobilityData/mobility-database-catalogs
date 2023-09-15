# The Mobility Database Catalogs

[![Integration tests](https://github.com/MobilityData/mobility-catalogs/actions/workflows/integration_tests.yml/badge.svg?branch=issue%2F343%2Fcatalogs-prototype)](https://github.com/MobilityData/mobility-catalogs/actions/workflows/integration_tests.yml) [![Unit tests](https://github.com/MobilityData/mobility-catalogs/actions/workflows/unit_tests.yml/badge.svg?branch=issue%2F343%2Fcatalogs-prototype)](https://github.com/MobilityData/mobility-catalogs/actions/workflows/unit_tests.yml) [![Export catalogs to CSV](https://github.com/MobilityData/mobility-catalogs/actions/workflows/export_to_csv.yml/badge.svg?branch=issue%2F343%2Fcatalogs-prototype)](https://github.com/MobilityData/mobility-catalogs/actions/workflows/export_to_csv.yml) [![Join the MobilityData chat](https://badgen.net/badge/slack/%20/green?icon=slack)](https://share.mobilitydata.org/slack)

The Mobility Database Catalogs is a list of open mobility data feeds from across the world. [You can learn more about the Mobility Database here](https://database.mobilitydata.org/).

To search feeds easily, you can download [the CSV spreadsheet](https://bit.ly/catalogs-csv). If you want to filter for specific types of feeds, [you can learn how to here](#get-and-filter-feeds).


## Table of Contents

* [Browsing and Consuming The Spreadsheet](#browsing-and-consuming-the-spreadsheet)
* [How Often is the Database Updated?](#how-often-is-the-database-updated)
* [The Architecture](#the-architecture)
* [GTFS Schedule Schema](#gtfs-schedule-schema)
* [GTFS Realtime Schema](#gtfs-realtime-schema)
* [Installation](#installation)
* [Get and Filter Feeds](#get-and-filter-feeds)
* [Integration Tests](#integration-tests)
* [License](#license)
* [Contributing](#contributing)

## Browsing and Consuming The Spreadsheet

If you're only interested in browsing the feeds or pulling all the latest URLs, [download the CSV](https://bit.ly/catalogs-csv). You can cross reference IDs from the Mobility Database, TransitFeeds and Transitland with [this ID map spreadsheet](https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/edit?resourcekey#gid=1787149399).

If you are consuming the spreadsheet, we recommend downloading a new version every time you use it, since the `latest.url` is occasionally updated to match any changes made to the provider and subdivision name within the feed file.

## How Often is the Database Updated?

Updating the CSV is a community effort. Contributors either create a PR here directly or they submit an update through [the form](https://database.mobilitydata.org/add-a-feed), which MobilityData then adds as a PR within approximately a week of submission. You can look at [the PR history](https://github.com/MobilityData/mobility-database-catalogs/pulls?q=is%3Apr+is%3Aclosed) to see how frequently there are updates, and we usually do updates 1-3 times a month.

## The Architecture

### Catalogs

Contains the feeds of the Mobility Database Catalogs. Every single feed is represented by a JSON file. The feeds can be aggregated by criteria using our `tools.operations` functions.

### Tools

Contains the tools to search, add and update the feeds. The `tools.operations` module contains the project operations (get, add and update). The `tools.helpers` module contains helper functions that support the `tools.operations` module. The `tools.constants` module contains the project constants.

### Schemas

Contains the JSON schemas used to validate the feeds in the integration tests.

## GTFS Schedule Schema

|Field Name|Type|Presence|Definition|  
|-|-|-|-|
| mdb_source_id |  Unique ID | System generated | Unique numerical identifier for the feed.      |
| data_type     | Enum| Required| The data format that the feed uses: `gtfs`.|
| features      | Array of Enums | Optional | An array of features which can be any of: <ul><li>`fares-v2`</li><li>`fares-v1`</li><li>`flex-v1`</li><li>`flex-v2`</li><li>`pathways`</li></ul>|  
| status        | Enum | Optional | Describes status of the feed. Should be one of: <ul><li>`active`: Feed should be used in public trip planners.</li><li>`deprecated`: Feed is explicitly deprecated and should not be used in public trip planners.</li><li>`inactive`: Feed hasn't been recently updated and should be used at risk of providing outdated information.</li><li>`development`: Feed is being used for development purposes and should not be used in public trip planners.</li></ul>Feed is assumed to be `active` if status is not explicitly provided.|  
|location| Object | Required |Contains  <ul><li>Text that describes the feed's location in the `country_code`, `subdivision_name`, and `municipality` fields.</li><li>Latitude, longitude, date and time that describes the feed's bounding box in the `bounding_box` subobject. </li></ul>|
| - country_code       | Text |Required                  | ISO 3166-1 alpha-2 code designating the country where the feed service is located. For a list of valid codes [see here](https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes).                                                    |
| - subdivision_name  | Text |Optional              | ISO 3166-2 subdivision name designating the subdivision (e.g province, state, region) where the feed service is located. For a list of valid names [see here](https://unece.org/trade/uncefact/unlocode-country-subdivisions-iso-3166-2).|  
| - municipality  | Text |Optional              | Primary municipality in which the feed service is located.|  
| - bounding_box  | Object|System generated             | Bounding box of the feed  when it was first added to the catalog. Contains `minimum_latitude`, `maximum_latitude`, `minimum_longitude`, `maximum_longitude` and `extracted_on` fields. If the bounding box information displays as "null", you can check any potential feed errors with [the GTFS validator](https://github.com/MobilityData/gtfs-validator).   |  
| --minimum_latitude    | Latitude | System generated                    | The minimum latitude for the feed's bounding box.  
| --maximum_latitude    | Latitude | System generated                    | The maximum latitude for the feed's bounding box.  
| --minimum_longitude    | Longitude | System generated                    | The minimum longitude for the feed's bounding box.  
| --maximum_longitude    | Longitude | System generated                    | The maximum longitude for the feed's bounding box.  
| --extracted_on   | Date and Time | System generated                    | The date and timestamp the bounding box was extracted on in UTC.  
| provider     | Text | Required                   | A commonly used name for the transit provider included in the feed.  
| name        |  Text |Optional              | An optional description of the feed, e.g to specify if the feed is an aggregate of multiple providers, or which network is represented by the feed. |
|urls| Object | Required | Contains URLs associated with the feed in the `direct_download_url`, `latest`, and `license` fields.
|- direct_download |URL|Optional     | URL that automatically opens the feed.
|- authentication_type |Enum|Optional | The **authentication_type** field defines the type of authentication required to access the URL. Valid values for this field are: <ul> <li>**0** or **(empty)** - No authentication required.</li><li>**1** - The authentication requires an API key, which should be passed as value of the parameter `api_key_parameter_name` in the URL. Please visit URL in `authentication_info_url` for more information. </li><li>**2** - The authentication requires an HTTP header, which should be passed as the value of the header `api_key_parameter_name` in the HTTP request. </li></ul> When not provided, the authentication type is assumed to be **0**.|
|- authentication_info_url | URL| Conditionally required | If authentication is required, the **authentication_info_url** field contains a URL to a human-readable page describing how the authentication should be performed and how credentials can be created. This field is required for `authentication_type=1` and `authentication_type=2`. |
|- api_key_parameter_name |Text|Conditionally required | The **api_key_parameter_name** field defines the name of the parameter to pass in the URL to provide the API key. This field is required for `authentication_type=1` and `authentication_type=2`.   |
| - latest | URL | System generated | A stable URL for the latest dataset of a feed.
|- license |URL| Optional     | The license information for the direct download URL.  

## GTFS Realtime Schema

|Field Name|Type|Presence|Definition|  
|-|-|-|-|
| mdb_source_id |  Unique ID | System generated | Unique numerical identifier.      |
| data_type     | Enum| Required| The data format that the feed uses: `gtfs-rt`.                                                                                                |
|entity_type|Array of Enums|Required|The type of realtime entity: `vp`, `tu`, or `sa` which represent vehicle positions, trip updates, and service alerts.
| provider     | Text | Required                   | A commonly used name for the transit provider included in the feed.  
| name        |  Text |Optional              | An optional description of the feed, e.g to specify if the feed is an aggregate of multiple providers
|note|Text| Optional|A note to clarify complex use cases for consumers, for example when several static feeds are associated with a realtime feed.  |  
| features      | Array of Enums | Optional | An array of features which can be any of: <ul><li>`occupancy`</li></ul> |  
| status        | Enum | Optional |  Describes status of the feed. Should be one of: <ul><li>`active`: Feed should be used in public trip planners.</li><li>`deprecated`: Feed is explicitly deprecated and should not be used in public trip planners.</li><li>`inactive`: Feed hasn't been recently updated and should be used at risk of providing outdated information.</li><li>`development`: Feed is being used for development purposes and should not be used in public trip planners.</li></ul>Feed is assumed to be `active` if status is not explicitly provided.|  |  
| static_reference |  Array of Integers |Optional              | A list of the static feeds that the real time feed is associated with, represented by their MDB source IDs. |  
|urls| Object | Required | Contains URLs associated with the feed in the `direct_download_url` and `license_url` fields, and the authentication info for `direct_download_url` in the `authentication_type`, `authentication_info_url` and `api_key_parameter_name` fields.
|- direct_download_url |URL|Required     | URL that responds with an encoded [GTFS Realtime protocol buffer message](https://github.com/google/transit/tree/master/gtfs-realtime/spec/en#data-format).                                                                                                
|- authentication_type |Enum|Optional | The **authentication_type** field defines the type of authentication required to access the URL. Valid values for this field are: <ul> <li>**0** or **(empty)** - No authentication required.</li><li>**1** - The authentication requires an API key, which should be passed as value of the parameter `api_key_parameter_name` in the URL. Please visit URL in `authentication_info_url` for more information. </li><li>**2** - The authentication requires an HTTP header, which should be passed as the value of the header `api_key_parameter_name` in the HTTP request. </li></li>**3**: Ad-hoc authentication required, visit URL in `authentication_info_url` for more information.</li></ul> When not provided, the authentication type is assumed to be **0**.|
|- authentication_info_url | URL| Conditionally required | If authentication is required, the **authentication_info_url** field contains a URL to a human-readable page describing how the authentication should be performed and how credentials can be created. This field is required for `authentication_type=1` or greater. |
|- api_key_parameter_name |Text|Conditionally required | The **api_key_parameter_name** field defines the name of the parameter to pass in the URL to provide the API key. This field is required for `authentication_type=1` and `authentication_type=2`.   |  
|- license_url  |URL| Optional     | The license information for  `direct_download_url`.

In [the CSV](https://bit.ly/catalogs-csv), realtime feeds include the location metadata of their static reference when provided.

## Installation

### Requirements

#### MacOs

To use and run this project properly, you must install all its requirements. Make sure Python 3.9+ and Pip are installed:

```sh
$ python3 --version
$ pip --version
```

If not, install them with:

```sh
$ brew install python3.9
$ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$ sudo python get-pip.py
```

Make sure both GDAL and RTree (Libspatialindex) libraries are installed on your computer, which are required for one of the project dependencies, the [GTFS Kit Library](https://pypi.org/project/gtfs-kit/):

```sh
$ brew install GDAL
$ brew install spatialindex
```

It is recommended to set up a virtual environment before installing the requirements. To set up and activate a Python 3.9 virtual environment, enter the following commands:

```sh
$ python3.9 -m venv env
$ source env/bin/activate
```

Once your virtual environment is activated, enter the following command to install the project requirements:

```sh
(env) $ pip install -r requirements.txt
```

To deactivate your virtual environment, enter the following command:

```sh
(env) $ deactivate
```

If you are working with IntelliJ or PyCharm, it is possible to use this virtual environment within the IDE. To do so, follow the instructions to create a virtual environment [here](https://www.jetbrains.com/help/idea/creating-virtual-environment.html).

### Repository

To use it, clone the project on your local machine using HTTP with the following commands:

```sh
$ git clone https://github.com/MobilityData/mobility-database-catalogs.git
$ cd mobility-database-catalogs
```

## Get and Filter Feeds

### Setup

Follow the steps described in the [Installation](#installation) section.

### Run it

To use the Mobility Database Catalogs, go to the cloned project root, open the Python interpreter and import the project operations:

```sh
$ cd mobility-catalogs
$ python
>>> from tools.operations import *
```

To get the feeds:

```python
>>> get_sources()
```

To get the feeds by subdivision name, where `$SUBDIVISION_NAME` is a ISO 3166-2 subdivision name:

```python
>>> get_sources_by_subdivision_name(subdivision_name=$SUBDIVISION_NAME)
```

To get the feeds by country code, where `$COUNTRY_CODE` is a ISO 3166-1 alpha-2 code:

```python
>>> get_sources_by_country_code(country_code=$COUNTRY_CODE)

```

To get the feeds by bounding box, where `$MINIMUM_LATITUDE` `$MAXIMUM_LATITUDE` `$MINIMUM_LONGITUDE` and `$MAXIMUM_LONGITUDE` are expressed as floats:

```python
>>> get_sources_by_bounding_box(
        minimum_latitude=$MINIMUM_LATITUDE,
        maximum_latitude=$MAXIMUM_LATITUDE,
        minimum_longitude=$MINIMUM_LONGITUDE,
        maximum_longitude=$MAXIMUM_LONGITUDE
    )
```

To get the feeds by feature, `$FEATURE` is expressed as a string and must be one of:

* `fares-v2`  
* `fares-v1`  
* `flex-v1`  
* `flex-v2`  
* `pathways`  
* `occupancy`  

```python
>>> get_sources_by_feature(
        feature=$FEATURE,
    )
```

To get the feeds by status, `$STATUS` is expressed as a string and one of:

* `active`  
* `deprecated`  
* `inactive`  
* `development`  

```python
>>> get_sources_by_status(
        feature=$STATUS,
    )
```
## Integration Tests

In order to avoid invalid feeds in the Mobility Database Catalogs, any modification made in the repository, addition or update, must pass the integration tests before being merged into the project. The integration tests are listed in the [Test Integration](/tests/test_integration.py) module.

## License

Code licensed under the [Apache 2.0 License](http://www.apache.org/licenses/LICENSE-2.0).

All of the Mobility Database catalog's metadata is made available under [Creative Commons CC0 (CC0)](https://creativecommons.org/publicdomain/zero/1.0/legalcode). Individual transit feeds are subject to the terms & conditions of their own respective data provider. If you are a transit provider and there is a feed that should not be included in the repository, please contact emma@mobilitydata.org and we'll remove it as soon as possible.

## Contributing

We welcome contributions to the project! You can add and update feeds or contribute code. Please check out our [Contribution guidelines](/CONTRIBUTING.md) for details. Any PRs or [form contributions](https://database.mobilitydata.org/add-a-feed) will be responded to within a week of submission.
