## How to contribute to the catalogs
All contributions to this project are welcome. If you want to add or updates sources and don't want to use GitHub, [you can use the form here](https://database.mobilitydata.org/add-a-feed) and the MobilityData team will add it.

If you want to use GitHub:

To propose changes, we encourage contributors to:
1. [Fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo) this project on GitHub
2. Create a new branch, and
3. Propose their changes by opening a [new pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests). We encourage contributors to format pull request titles following the [Conventional Commit Specification](https://www.conventionalcommits.org/en/v1.0.0/#examples).

## Having problems?
Have you encountered an error? A critical step in troubleshooting is being able to reproduce the problem. You can [create a bug ticket](https://github.com/MobilityData/mobility-database-catalogs/issues/new?assignees=maximearmstrong&labels=&template=bug_report.md&title=%5BBUG%5D) with reproduction steps and we will review it.

## Contributing data

Note that adding or updating sources manually is possible, although not recommended as it increases the risk of introducing incorrect or invalid information into your branch and pull request. [Using the operations makes sure your JSON files are valid](#contribute-data).

Note that your contribution must pass all of our tests, as implemented in the CI workflows of this project repository, to be merged into the main branch. To pass our tests, make sure that your contribution conforms to the appropriate JSON schema and that the ID and direct download URL values contributed for a source are not already in the Mobility Database Catalogs.  

### Data contribution flow

To contribute data to the Mobility Database catalogs, please follow these steps:
1. [Check our sources](https://github.com/MobilityData/mobility-database-catalogs#browsing-and-consuming-the-spreadsheet) to see if any of them match the one you want to add or update.
1. Clone our repository on your local machine using the HTTPS protocol `git clone https://github.com/MobilityData/mobility-database-catalogs.git`.
2. Create a new branch for your contribution `git checkout -b $YOUR_NEW_BRANCH`. Note that you can list the existing branches with `git branch -a` to make sure your branch name is not already used.
3. Set up the Python environment following the instructions in our README.md.
4. Contribute data.
5. Test your contribution.
6. Add your contribution files to the git staging area with `git add $YOUR_FILES` where `$YOUR_FILES` is a list of files or the directory where your modifications are.
7. Commit your contribution including a message explaining your contribution with `git commit -m "$YOUR_COMMIT_MESSAGE"`.
8. Push your contribution to your branch on the origin repository with `git push origin $YOUR_NEW_BRANCH`
9. Go to the repository pull requests [page](https://github.com/MobilityData/mobility-database-catalogs/pulls) and open a **draft** pull request with your branch. If you are adding a GTFS **Schedule** source, your pull request **must** include the string "[SOURCES]" at the end of its title. Eg. "feat: Add Montreal GTFS Source [SOURCES]".
10. Modify your contribution as many times as needed following steps 4 to 8.
11. When your contribution is ready, convert your pull request from draft to ready for review and request a review from a team member at Mobility Data. Not that if you need to modify your contribution after this step, you will be asked to convert your pull request back to draft.
12. Once your pull request is converted to ready for review and that all the checks have passed, we will approve and merge it.

#### Add a GTFS Schedule source
The easiest way to add a GTFS Schedule source is to use the operation `tools.operations.add_gtfs_schedule_source` through the Python interpreter or in your scripts. This operation makes sure the information provided is correct and will pass our tests. Provide the information about your source in the operation function to add your source.

**If your GTFS Schedule source requires API authentication, please use the [form](https://database.mobilitydata.org/update-a-data-source)** instead of the PR process so we can generate our own API credentials for the source. Sources with `authentication_type=1` or `authentication_type=2` can't be added from forks, but those with `authentication_type=0` can.

```python
>>> add_gtfs_schedule_source(
        provider=$YOUR_SOURCE_PROVIDER_NAME,
        country_code=$YOUR_SOURCE_COUNTRY_CODE,
        direct_download_url=$YOUR_SOURCE_DIRECT_DOWNLOAD_URL,
        authentication_type=$OPTIONAL_AUTHENTICATION_TYPE,
        authentication_info_url=$CONDITIONALLY_REQUIRED_AUTHENTICATION_INFO_URL,
        api_key_parameter_name=$CONDITIONALLY_REQUIRED_API_KEY_PARAMETER_NAME,
        api_key_parameter_value=$NOT_STORED_API_KEY_PARAMETER_VALUE,
        subdivision_name=$OPTIONAL_SUBDIVISION_NAME,
        municipality=$OPTIONAL_MUNICIPALITY,
        license_url=$OPTIONAL_LICENSE_URL,
        name=$OPTIONAL_SOURCE_NAME,
        features=[$OPTIONAL_FEATURE_ARRAY],
        status=$OPTIONAL_STATUS
    )
```

#### Add a GTFS Realtime source
The easiest way to add a GTFS Realtime source is to use the operation `tools.operations.add_gtfs_realtime_source` through the Python interpreter or in your scripts. Provide the information about your source in the operation function to add your source.

```python
>>> add_gtfs_realtime_source(
        entity_type=[$YOUR_SOURCE_ARRAY_OF_ENTITY_TYPES],
        provider=$YOUR_SOURCE_PROVIDER_NAME,
        direct_download_url=$YOUR_SOURCE_DIRECT_DOWNLOAD_URL,
        authentication_type=$YOUR_SOURCE_AUTHENTICATION_TYPE,
        authentication_info_url=$CONDITIONALLY_REQUIRED_AUTHENTICATION_INFO_URL,
        api_key_parameter_name=$CONDITIONALLY_REQUIRED_API_KEY_PARAMETER_NAME,
        license_url=$OPTIONAL_LICENSE_URL,
        name=$OPTIONAL_SOURCE_NAME,
        static_reference=[$OPTIONAL_ARRAY_OF_STATIC_REFERENCE_NUMERICAL_IDS],
        note=$OPTIONAL_SOURCE_NOTE,
    )
```

#### Update a GTFS Schedule source
The easiest way to update a GTFS Schedule source is to use the operation `tools.operations.update_gtfs_schedule_source` through the Python interpreter or in your scripts.

The default value for every parameter is `None`. Note that once a parameter value is added, it cannot be set to `None` again.

`mdb_source_id` and `data_type` cannot be updated. All other parameters can.

**If your GTFS Schedule source requires API authentication, please use the [form](https://database.mobilitydata.org/update-a-data-source)** instead of the PR process to update the source. Sources with `authentication_type=1` or `authentication_type=2` can't be updated from forks, but those with `authentication_type=0` can.

```python
>>> update_gtfs_schedule_source(
        mdb_source_id=$YOUR_SOURCE_NUMERICAL_ID,
        provider=$OPTIONAL_SOURCE_PROVIDER_NAME,
        name=$OPTIONAL_SOURCE_NAME,
        country_code=$OPTIONAL_SOURCE_COUNTRY_CODE,
        subdivision_name=$OPTIONAL_SOURCE_SUBDIVISION_NAME,
        municipality=$OPTIONAL_SOURCE_MUNICIPALITY,
        direct_download_url=$OPTIONAL_SOURCE_DIRECT_DOWNLOAD_URL,
        authentication_type=$OPTIONAL_AUTHENTICATION_TYPE,
        authentication_info_url=$CONDITIONALLY_REQUIRED_AUTHENTICATION_INFO_URL,
        api_key_parameter_name=$CONDITIONALLY_REQUIRED_API_KEY_PARAMETER_NAME,
        api_key_parameter_value=$NOT_STORED_API_KEY_PARAMETER_VALUE,
        license_url=$OPTIONAL_LICENSE_URL,
        features=[$OPTIONAL_FEATURE_ARRAY],
        status=$OPTIONAL_STATUS
    )
```

#### Update a GTFS Realtime source
The easiest way to update a GTFS Realtime source is to use the operation `tools.operations.update_gtfs_realtime_source` through the Python interpreter or in your scripts.

The default value for every parameter is `None`. Note that once a parameter value is added, it cannot be set to `None` again.

`mdb_source_id` and `data_type` cannot be updated. All other parameters can.

```python
>>> update_gtfs_realtime_source(
        mdb_source_id=$YOUR_SOURCE_NUMERICAL_ID,
        entity_type=[$YOUR_SOURCE_ARRAY_OF_ENTITY_TYPES],
        provider=$YOUR_SOURCE_PROVIDER_NAME,
        direct_download_url=$YOUR_SOURCE_DIRECT_DOWNLOAD_URL,
        authentication_type=$YOUR_SOURCE_AUTHENTICATION_TYPE,
        authentication_info_url=$CONDITIONALLY_REQUIRED_AUTHENTICATION_INFO_URL,
        api_key_parameter_name=$CONDITIONALLY_REQUIRED_API_KEY_PARAMETER_NAME,
        license_url=$OPTIONAL_LICENSE_URL,
        name=$OPTIONAL_SOURCE_NAME,
        static_reference=[$OPTIONAL_ARRAY_OF_STATIC_REFERENCE_NUMERICAL_IDS],
        note=$OPTIONAL_SOURCE_NOTE,
    )
```

### Update a source file name
You need to
1. Manually search for the JSON file you want in your fork. For example, finding `ca-ontario-toronto-transit-commission-gtfs-732.json` in the `schedule` folder.
2. Modify the file name. For example, updating the file name to `ca-ontario-ttc-gtfs-732.json`.
3. Modify the `latest.url` to match the new file name. For example, changing `https://storage.googleapis.com/storage/v1/b/mdb-latest/o/ca-ontario-toronto-transit-commission-gtfs-732.zip?alt=media` to `https://storage.googleapis.com/storage/v1/b/mdb-latest/o/ca-ontario-toronto-ttc-gtfs-732.zip?alt=media`.

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
5. Contribute the unit tests for every function or operation you added after [running tests locally](#how-to-run-tests-locally).

## Coding style
"Sticking to a single consistent and documented coding style for this project is important to ensure that code reviewers dedicate their attention to the functionality of the validation, as opposed to disagreements about the coding style (and avoid [bike-shedding](https://en.wikipedia.org/wiki/Law_of_triviality))."

This project uses [the Black code formatter](https://github.com/psf/black), which is compliant with [PEP8](https://www.python.org/dev/peps/pep-0008/), the style guide for Python code. A [pre-commit](https://pre-commit.com/) hook file is provided with the repo so it is easy to apply Black before each commit. A CI workflow is testing the code pushed in a pull request to make sure it is PEP8 compliant.

## How to run tests locally
This project includes unit and integration tests in order to:
1. Verify the implementation behaves as expected in tests as well as on real data
2. Make sure any new code does not break existing code

Run the following command at the root of the project to run Python tests:
`$ pytest`
