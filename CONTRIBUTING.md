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
To contribute data to the mobility catalogs, it is suggested that you follow the steps below.

Note that adding or updating sources manually is possible, although not recommended as it increases the risk of introducing incorrect or invalid information into your branch and pull request.

Note that your contribution must pass all of our tests, as implemented in the CI workflows of this project repository, to be merged into the main branch. To pass our tests, make sure that your contribution conforms to the appropriate JSON schema and that the ID and auto-discovery URL values contributed for a source are unique across the Mobility Database Catalogs.

### Prepare to contribute data
Check our sources to see if any of them match the one you want to add or update.

If yes, please go to Update a source.
Otherwise, please go to Add a source.

### Contribute data

#### Add a source
The easiest way to add a source is to use the operation `tools.operations.add_source` through the Python interpreter or in your scripts. Provide the information about your source in the operation function to add your source.

Note that if different than the default value `tools.constants.GTFS`, the data type must be taken from the `data_type` field enum values, which can be discovered in the appropriate JSON schema.
```
>>> add_source(
        name="Your Source Name",
        location="Your Source Location",
        country_code="Your Source Country Code",
        auto_discovery_url="https://your.source.stable.discovery.url",
        license_url="https://your.source.license.url",
        data_type=GTFS
    )
```

#### Update a source
The easiest way to update a source is to use the operation `tools.operations.update_source` through the Python interpreter or in your scripts.

Note that only the parameters for which the provided value will differ from the default value `None` will be updated. Only the following parameters can be updated: name, location, country code, license url and auto-discovery url.

Note that if different than the default value `tools.constants.GTFS`, the data type must be taken from the `data_type` field enum values, which can be discovered in the appropriate JSON schema.

```
>>> update_source(
        mdb_source_id="mdb-src-gtfs-your-source-id",
        name=None,
        location=None,
        country_code=None,
        auto_discovery_url=None,
        license_url=None,
        data_type=GTFS
    )
```

## Contributing operations
To contribute operations to the mobility catalogs, it is suggested that you follow the steps below.

### Prepare to contribute operation
1. Check our operations under `tools.operations` to see if the operation you want to add is not already implemented.
2. Check our helpers under `tools.helpers` to see if there are functions that might be useful for your contribution.
3. Check our constants under `tools.constants` to see if there are constants that might be useful for your contribution.

### Contribute operation
1. Contribute the operation under `tools.operations`. Note that the code added in `tools.operations` should only implement the business logic of the operation (filter, attribute assignment, etc.). Any functions to create, verify, extract data/metadata or import/export data must be implemented in `tools.helpers` and called by the operation in `tools.operations`.
2. Contribute the helpers needed for your operation under `tools.helpers`.
3. Contribute the constants needed for your operation under `tools.constants`.
4. Contribute the unit tests for every function or operation you added.

### Coding style
"Sticking to a single consistent and documented coding style for this project is important to ensure that code reviewers dedicate their attention to the functionality of the validation, as opposed to disagreements about the coding style (and avoid [bike-shedding](https://en.wikipedia.org/wiki/Law_of_triviality))."

This project uses [the Black code formatter](https://github.com/psf/black), which is compliant with [PEP8](https://www.python.org/dev/peps/pep-0008/), the style guide for Python code. A [pre-commit](https://pre-commit.com/) hook file is provided with the repo so it is easy to apply Black before each commit. A CI workflow is testing the code pushed in a pull request to make sure it is PEP8 compliant.

### How to run tests locally
This project includes unit and integration tests in order to:
1. Verify the implementation behaves as expected in tests as well as on real data
2. Make sure any new code does not break existing code

Run the following command at the root of the project to run Python tests:
`$ pytest`
