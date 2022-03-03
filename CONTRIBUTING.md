## How to contribute to the catalogs
All contributions to this project are welcome. To propose changes, we encourage contributors to:
1. [Fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo) this project on GitHub
2. Create a new branch, and
3. Propose their changes by opening a [new pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests).

## Issue and PR templates
We encourage contributors to format pull request titles following the Conventional Commit Specification.

## Having problems?
Have you encountered an error? A critical step in troubleshooting is being able to reproduce the problem. You can [create a bug ticket](https://github.com/MobilityData/mobility-database-catalogs/issues/new?assignees=maximearmstrong&labels=&template=bug_report.md&title=%5BBUG%5D) with reproduction steps and we will review it.

## Contributing data
To contribute data to the mobility database catalogs, it is suggested that you follow the steps below.

Note that adding or updating sources manually is possible, although not recommended as it increases the risk of introducing incorrect or invalid information into your branch and pull request.

Note that your contribution must pass all of our tests, as implemented in the CI workflows of this project repository, to be merged into the main branch. To pass our tests, make sure that your contribution conforms to the appropriate JSON schema and that the ID and auto-discovery URL values contributed for a source are unique across the Mobility Database Catalogs.

### Prepare to contribute data
Check our sources to see if any of them match the one you want to add or update.

If yes, please go to Update a source.
Otherwise, please go to Add a source.

### Contribute data

#### Add a GTFS Schedule source
The easiest way to add a GTFS Schedule source is to use the operation `tools.operations.add_gtfs_schedule_source` through the Python interpreter or in your scripts. Provide the information about your source in the operation function to add your source.

```
>>> add_gtfs_schedule_source(
        provider=$YOUR_SOURCE_PROVIDER_NAME,
        country_code=$YOUR_SOURCE_COUNTRY_CODE,
        subdivision_name=$YOUR_SOURCE_SUBDIVISION_NAME,
        municipality=$YOUR_SOURCE_MUNICIPALITY,
        auto_discovery_url=$YOUR_SOURCE_STABLE_DISCOVERY_URL,
        license_url=$OPTIONAL_LICENSE_URL,
        name=$OPTIONAL_SOURCE_NAME
    )
```

#### Add a GTFS Realtime source
The easiest way to add a GTFS Realtime source is to use the operation `tools.operations.add_gtfs_realtime_source` through the Python interpreter or in your scripts. Provide the information about your source in the operation function to add your source. Note that even though `vehicle_positions_url`, `trip_updates_url` and `service_alerts_url`, you must provide at least one URL for your source to be valid.

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

#### Update a GTFS Schedule source
The easiest way to update a GTFS Schedule source is to use the operation `tools.operations.update_gtfs_schedule_source` through the Python interpreter or in your scripts.

Note that only the parameters for which the provided value will differ from the default value `None` will be updated. Only the following parameters can be updated: `provider`, `name`, `country_code`, `subdivision_name`, `municipality`, `auto_discovery_url` and `license_url`.

```
>>> update_gtfs_schedule_source(
        mdb_source_id=$YOUR_SOURCE_NUMERICAL_ID,
        provider=$OPTIONAL_SOURCE_PROVIDER_NAME,
        name=$OPTIONAL_SOURCE_NAME,
        country_code=$OPTIONAL_SOURCE_COUNTRY_CODE,
        subdivision_name=$OPTIONAL_SOURCE_SUBDIVISION_NAME,
        municipality=$OPTIONAL_SOURCE_MUNICIPALITY,
        auto_discovery_url=$OPTIONAL_SOURCE_STABLE_DISCOVERY_URL,
        license_url=$OPTIONAL_LICENSE_URL
    )
```

#### Update a GTFS Realtime source
The easiest way to update a GTFS Realtime source is to use the operation `tools.operations.update_gtfs_realtime_source` through the Python interpreter or in your scripts.

Note that only the parameters for which the provided value will differ from the default value `None` will be updated. Only the following parameters can be updated: `provider`, `name`, `static_reference`, `vehicle_positions_url`, `trip_updates_url` and `service_alerts_url`.

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

## Contributing operations
To contribute operations to the mobility database catalogs, it is suggested that you follow the steps below.

### Prepare to contribute operation
1. Check our operations under `tools.operations` to see if the operation you want to add is not already implemented.
2. Check our representations under `tools.representations` to see if there are methods that might be useful for your contribution.
3. Check our helpers under `tools.helpers` to see if there are functions that might be useful for your contribution.
4. Check our constants under `tools.constants` to see if there are constants that might be useful for your contribution.

### Contribute operation
1. Contribute the operation under `tools.operations`. Note that the code added in `tools.operations` should only implement the business logic of the operation (filter, attribute assignment, etc.). Any functions to create, verify, extract data/metadata or import/export data must be implemented in `tools.helpers` and called by the operation in `tools.operations`.
2. Contribute the representations needed for your operation under `tools.representations`.
3. Contribute the helpers needed for your operation under `tools.helpers`.
4. Contribute the constants needed for your operation under `tools.constants`.
5. Contribute the unit tests for every function or operation you added.

## Coding style
"Sticking to a single consistent and documented coding style for this project is important to ensure that code reviewers dedicate their attention to the functionality of the validation, as opposed to disagreements about the coding style (and avoid [bike-shedding](https://en.wikipedia.org/wiki/Law_of_triviality))."

This project uses [the Black code formatter](https://github.com/psf/black), which is compliant with [PEP8](https://www.python.org/dev/peps/pep-0008/), the style guide for Python code. A [pre-commit](https://pre-commit.com/) hook file is provided with the repo so it is easy to apply Black before each commit. A CI workflow is testing the code pushed in a pull request to make sure it is PEP8 compliant.

## How to run tests locally
This project includes unit and integration tests in order to:
1. Verify the implementation behaves as expected in tests as well as on real data
2. Make sure any new code does not break existing code

Run the following command at the root of the project to run Python tests:
`$ pytest`
