# DataConnect Python Library v1.0.0

The DataConnect Python library provides a Python client for connecting to Medidata DataConnect and retrieving relevant data programmatically.
To use this library, you must have a valid iMedidata account and access to required building blocks in the Medidata Platform. For details, see the Medidata [Knowledge Hub](https://learn.medidata.com/en-US/bundle/data-connect/page/developer_center.html).

## Table of Contents

- [DataConnect Python Library v1.0.0](#dataconnect-python-library-v100)
  - [Table of Contents](#table-of-contents)
  - [Setup and Usage](#setup-and-usage)
    - [Authentication and Connectivity](#authentication-and-connectivity)
  - [Functions](#functions)
    - [connect()](#connect)
      - [Description](#description)
      - [Usage](#usage)
      - [Arguments](#arguments)
      - [Output](#output)
    - [get\_studies()](#get_studies)
      - [Description](#description-1)
      - [Usage](#usage-1)
      - [Arguments](#arguments-1)
      - [Output](#output-1)
    - [get\_datasets()](#get_datasets)
      - [Description](#description-2)
      - [Usage](#usage-2)
      - [Arguments](#arguments-2)
      - [Output](#output-2)
    - [get\_dataset\_versions()](#get_dataset_versions)
      - [Description](#description-3)
      - [Usage](#usage-3)
      - [Arguments](#arguments-3)
      - [Output](#output-3)
    - [fetch\_data()](#fetch_data)
      - [Description](#description-4)
      - [Usage](#usage-4)
      - [Arguments](#arguments-4)
      - [Output](#output-4)
    - [dry\_publish()](#dry_publish)
      - [Description](#description-5)
      - [Usage](#usage-5)
      - [Arguments](#arguments-5)
      - [Output](#output-5)
      - [Data Validations](#data-validations)
    - [publish()](#publish)
      - [Description](#description-6)
      - [Usage](#usage-6)
      - [Arguments](#arguments-6)
      - [Output](#output-6)
      - [Data Validations](#data-validations-1)
    - [Data Validation Failures](#data-validation-failures)
    - [get\_datetime\_formats()](#get_datetime_formats)
      - [Description](#description-7)
      - [Usage](#usage-7)
      - [Arguments](#arguments-7)
      - [Output](#output-7)
    - [close()](#close)
      - [Description](#description-8)
      - [Usage](#usage-8)
      - [Arguments](#arguments-8)
      - [Output](#output-8)
  - [Errors](#errors)
- [Reporting known issues](#reporting-known-issues)
- [Backend](#backend)
- [Licensing](#licensing)

## Setup and Usage

* For instructions on how to install and use this library, follow the [Usage Notebook](../guides/dataconnect_usage.ipynb).
* For an example of how to transform data, go [here](../guides/transform_example.md).

### Authentication and Connectivity

* **Retrieving data:** You must have a user token to establish a connection between your Python environment and Medidata Data Connect. You can generate this token through Data Connect’s Developer Center. For details, visit the [knowledge hub](https://learn.medidata.com/en-US/bundle/data-connect/page/developer_center.html). Medidata recommends that you save the token in a local file and input it into the below initiation function.

* **Publish data:** You must have a project token to publish a dataset from your Python environment to Medidata Data Connect. You can generate this token through Data Connect > Transformations, by creating a Custom Code project. For details, visit the [knowledge hub](https://learn.medidata.com/en-US/bundle/data-connect/page/generate_custom_code_projects.html).

## Functions

The main public entry point is `DataconnectClient`.

### connect()

#### Description
Creates a connected client.

#### Usage
`connect(token="")`

#### Arguments
| Argument | Type | Description |
|---|---|---|
| host | str | Server host. Default host="enodia-gateway.platform.imedidata.com" |
| port | int | Server port. Default port="443" |
| use_tls | bool | Denotes whether to use TLS. Default use_tls = True |
| token | str | Authentication token, this is the user authentication token generated from the Developer Center in Medidata Data Connect |

#### Output
DataconnectClient object. This enables you to interact with Medidata Data Connect data in Python environment.

---

### get_studies()

#### Description
Retrieves a list of studies where the user has permission to manage custom code projects. Use the optional study name search parameter to filter results.

#### Usage
`get_studies(search_study_name=None)`

#### Arguments
| Argument | Type | Description |
|---|---|---|
| search_study_name | str or None | Optional. The approximate name of the study |

#### Output
Returns a list containing `total_records` (total studies available) and a `studies` array. Each study includes `name`, `uuid`, and an environments array. Each environment includes `name` and `uuid`.

---

### get_datasets()

#### Description
Retrieves datasets for a specific study environment and returns paginated results.

#### Usage
`get_datasets(study_environment_uuid, search_dataset_name="", page=1, page_size=50)`

#### Arguments
| Argument | Type | Description |
|---|---|---|
| study_environment_uuid | UUID | Unique iMedidata study environment identifier. You can find this in iMedidata’s Developer Info details |
| search_dataset_name | str | Optional. The approximate name of the dataset |
| page | int | Optional. Page number for paginated results. Default: 1 |
| page_size | int | Optional. Number of results per page. Default: 50 |

#### Output
Returns a list containing `total_records` (total datasets available across all pages), `pagination` and `datasets` array.

---

### get_dataset_versions()

#### Description
Retrieves all available versions for a dataset.

#### Usage
`get_dataset_versions(dataset_uuid)`

#### Arguments
| Argument | Type | Description |
|---|---|---|
| dataset_uuid | UUID | Unique iMedidata dataset identifier. This is available in the output of datasets() function |

#### Output
Returns all available versions of the dataset.

---

### fetch_data()

#### Description
Fetches dataset rows into a pandas DataFrame.

#### Usage
`fetch_data(dataset_uuid, first_n_rows=None)`

#### Arguments
| Argument | Type | Description |
|---|---|---|
| dataset_uuid | UUID | Unique iMedidata dataset identifier. This is available in the output of datasets() and dataset_versions() functions |
| first_n_rows | int or None | Optional positive row limit |

#### Output
Returns data from a specific dataset.

---

### dry_publish()

#### Description
Check if the publish results meet validation requirements.

#### Usage

```python
dry_publish(project_token, dataset_name, key_columns, source_datasets, data, datetime_formats = None)
```

#### Arguments

| Argument             | Description |
|:---------------------| :---------- |
| **project_token**    | You can generate this from the Data Connect > Transformations > Custom Code project type. |
| **dataset_name**     | Data Connect expects the dataset name to be unique within the study |
| **key_columns**      | List of columns that form the composite key that identifies each unique record in the data to be validated. Key columns must not contain null/missing values (for example, `None`) in any row. |
| **source_datasets**  | List of source dataset unique identifiers (UUIDs) to be used to create the data being validated |
| **data**             | Data frame that needs to be validated |
| **datetime_formats** | Optional. The expected format for date or datetime fields in the data frame. This is used to validate that the date or datetime fields in the data frame are in the correct format before publishing to Data Connect. This should be `None` when none of the fields in the data frame are expected to be in date or datetime type.|

#### Output

Returns the result of publishing validations as a list containing clean, server-side data-quality metrics:
* **`valid_record_count`**: Number of clean records matching platform requirements (always ≥ 0).
* **`duplicate_record_count`**: Gross duplicate records identified across the payload composite keys.
* **`invalid_record_count`**: Number of records containing validation errors or missing required keys.
* **`invalid_records`**: A data frame containing the rows that failed validation.

#### Data Validations

| Validations             | Description                                                                                                                                                                                                                                                                                                    |
|:---------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Invalid Input**    | Required argument is missing                                                                                                                                                                                                                                                                                   |
| **project_token**     | 1. Project Token is valid and generated from the Data Connect > Transformations > Custom Code project type.<br>2. More than one dataset cannot be published into a project<br>3. Only the project owner can publish datasets into a project. |
| **dataset_name**     | 1. Maximum length of 15 characters and must only contain alphanumeric characters and underscores<br> 2.  This is the new name of the resulting dataset created by the user                                                                                                                                                                                                            |
| **key_columns** | 1. Key columns are valid column names from the data frame being published <br>2. Key columns must not contain null/missing values (for example, `None`) in any row<br> 3. Maps directly to the server-side metrics payload: `valid_record_count`, `duplicate_record_count`, and `invalid_record_count` without double-penalizing overlapping row states.                |
| **source_datasets**  | 1. Source Dataset is a valid dataset UUID <br>2. Source Dataset is from the same study environment.                                                                                                                                                                                                            |
| **data**             | Invalid column name '{column.name}', it must only contain alphanumeric characters and underscores, with a maximum length of 20 characters.                                                                                                                                                                     |
| **datetime_formats** | 1. Date or Date time format is not from the acceptable list of formats <br> 2. Date/Datetime format cannot be provided for a field that is not parsed as a Date/DateTime field in data frame.      |


### publish()

#### Description

Publish dataset to Data Connect.


#### Usage

```python
publish(project_token, dataset_name, key_columns, source_datasets, data, datetime_formats = None)
```

#### Arguments

| Argument             | Description |
|:---------------------| :---------- |
| **project_token**    | You can generate this from the Data Connect > Transformations > Custom Code project type |
| **dataset_name**     | This is the new name of the resulting dataset being created by the user. Data Connect expects the dataset name to be unique within the study |
| **key_columns**      | List of columns that form the composite key that identifies each unique record. Rows with null/missing values (for example, `None`) are flagged as invalid. Key fields are mandatory, they cannot be omitted.|
| **source_datasets**  | List of source dataset UUIDs within the study environment where the dataset is published and used to create the data that is being published |
| **data**             | Data frame which needs to be published |
| **datetime_formats** | Optional. The expected format for datetime fields in the data frame. This is used to validate that datetime fields in the data frame are in the correct format before publishing to Data Connect. This should be `None` when none of the fields in the data frame are expected to be in date or datetime type.|


#### Output

Returns the status of publish as a list containing the final backend execution results:
* **`valid_record_count`**: Total structural records written successfully to the destination table.
* **`duplicate_record_count`**: Gross row duplication counters.
* **`invalid_record_count`**: Total failure rows excluded during the network stream.
* **`invalid_records`**: A data frame containing the rows that failed validation.


#### Data Validations

| Validations             | Description                                                                                                                                                                                                                                                                                                    |
|:---------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Invalid Input**    | Required argument is missing                                                                                                                                                                                                                                                                                   |
| **project_token**     | 1. Project Token is valid and generated from the Data Connect > Transformations > Custom Code project type. <br>2. More than one dataset cannot be published into a project<br>3. Only the project owner can publish datasets into a project. |
| **dataset_name**     | 1. Maximum length of 15 characters and must only contain alphanumeric characters and underscores<br> 2. This is the new name of the resulting dataset created by the user                                                                                                                                                                                                                  |
| **key_columns**      | 1. Key columns are valid column names from the data frame being published <br>2. Key columns must not contain null/missing values (for example, `None`) in any row<br> 3. Maps directly to the server-side metrics payload: `valid_record_count`, `duplicate_record_count`, and `invalid_record_count` without double-penalizing overlapping row states.                                                 |
| **source_datasets**  | 1. Source Dataset is a valid dataset UUID <br>2. Source Dataset is from the same study environment.                                                                                                                                                                                                            |
| **data**             | Invalid column name '{column.name}', it must only contain alphanumeric characters and underscores, with a maximum length of 20 characters.                                                                                                                                                                     |
| **datetime_formats** | 1. Date or Date time format is not from the acceptable list of formats <br> 2. Date/Datetime format cannot be provided for a field that is not parsed as a Date/DateTime field in data frame.                                                                                                                  |

### Data Validation Failures
- When validation fails, the SDK returns the original data frame with an appended `error` column.
- Each invalid record appears once per error type (a row with multiple errors produces multiple result rows).
- Supported error names: `NULL_KEY` (null/empty value in key column), `INVALID_VALUE` (invalid value in key column).
- A summary is printed to the console for immediate visibility.
- The full invalid records table is accessible programmatically from the error object.



### get_datetime_formats()

#### Description
Returns the list of date/datetime format patterns accepted by Data Connect when publishing data. Use this to discover valid values for the `datetime_formats` argument of [`dry_publish()`](#dry_publish) and [`publish()`](#publish).

#### Usage

```python
get_datetime_formats(project_token, format_type="all")
```

#### Arguments

| Argument          | Type | Description |
|:------------------|:-----|:------------|
| **project_token** | str  | You can generate this from the Data Connect > Transformations > Custom Code project type. |
| **format_type**   | str  | Optional. Filters the returned formats. One of `"all"` (default), `"date"`, or `"datetime"`. |

#### Output

Returns a `DatetimeFormatsResult` object exposing the following methods:

| Method          | Returns               | Description |
|:----------------|:----------------------|:------------|
| `all()`         | `list[DatetimeFormat]`| Every supported format, each tagged with its `type` (`"date"` or `"datetime"`). |
| `dates()`       | `list[str]`           | Format strings classified as date-only. |
| `datetimes()`   | `list[str]`           | Format strings classified as datetime. |

Each `DatetimeFormat` item has two fields:

| Field    | Type | Description |
|:---------|:-----|:------------|
| `format` | str  | The format pattern (for example, `"yyyy-MM-dd"`). |
| `type`   | str  | Either `"date"` or `"datetime"`. |

Example:

```python
with DataConnectClient.connect(token=user_token) as dc:
    result = dc.get_datetime_formats(project_token=project_token)
    for fmt in result.all():
        print(f"{fmt.format}  [{fmt.type}]")

    date_only = result.dates()
    datetime_only = result.datetimes()
```

When `format_type="date"` or `format_type="datetime"` is supplied, the server returns only formats of that kind; `all()` will contain just those entries and the matching accessor (`dates()` / `datetimes()`) will mirror them.


### close()

#### Description
Closes the underlying transport connection.

#### Usage
`close()`

#### Arguments
None

#### Output
None

## Errors
The library raises exceptions for many reasons, such as invalid parameters, authentication errors, and validation failures. We have introduced error codes for each category of errors to be handled programmatically.

| Error Code | Type | Scenario|
| :--- | :--- |:---|
| AUTHZ_001	| Authorization	| Authorization service check failed |
| VAL_002	| Validation - Page Number | Page number is not a positive integer
| VAL_003	| Validation - Page Size | Page size is out of range [1, 100]
| VAL_004	| Validation - Study Parameter | Invalid study uuid
| VAL_005	| Validation - Study Environment Parameter | Missing or invalid study environment uuid
| VAL_006	| Validation - Dataset Parameter | Invalid dataset uuid
| VAL_007	| Validation - Configuration Error | Required input parameters are missing or invalid in configuration
| VAL_008	| Validation - Project Token | Invalid project token
| VAL_009	| Validation - Unsupported Data Type | Unsupported data types.
| VAL_010	| Validation - Unsupported Data Type | Unsupported datetime formats.
| VAL_011	| Validation - Pagination	| Pagination is out of range
| VAL_012	| Validation - Concurrency | Project actively being published
| VAL_013	| Validation - Formatting Error | Data validation failed. One or more records contain formatting errors.
| RES_002	| Resource Exceptions - Study Environment | No authorized Study Environments found for the authenticated user
| RES_003	| Resource Exceptions - Invalid parameter | Incorrect UUID combination.
| RES_004	| Resource Exceptions - Invalid parameter | Incorrect UUID combination.
| RES_005	| Resource Exceptions - Study Group |  Study Group not found for the Dataset's Study Environment.
| RES_006	| Resource Exceptions - Study |	Study Group not found for the Dataset's Study Environment.
| RES_007	| Resource Exceptions - Client Division | 	Client Division not found for the Dataset's Study Environment.
| RES_008	| Resource Exceptions - Custom Code Project | Transformation Project is not found.
| INT_001	| Internal Application Exception | Something went wrong on our end.

# Reporting known issues

If you believe you have found an issue, please contact Medidata Support by submitting a ticket to Medidata Support. All issue reports should include a minimal reproducible example to ensure our team can diagnose the issue.

Additionally, all known issues are available [here](https://learn.medidata.com/en-US/bundle/current-issues/page/current_known_issues_for_data_connect.html).

# Backend

This library uses the Arrow open source library and the Iceberg open table format to enable data interoperability across platforms.

* [Apache arrow](https://arrow.apache.org/docs/r/): This library uses Arrow’s highly efficient format [pyarrow](https://arrow.apache.org/cookbook/py/flight.html) to transfer massive datasets over the network, allowing users to access & interact with remote datasets.

* [Apache Iceberg](https://iceberg.apache.org/): This is the open table format underlying Medidata Data Connect's structured data management to support high-performance and reliable data analytics and storage.

# Licensing

BY DOWNLOADING THIS FILE (“DOWNLOAD”) YOU AGREE TO THE FOLLOWING TERMS:
MEDIDATA SOLUTIONS, INC. AND ITS AFFILIATES (COLLECTIVELY “MEDIDATA”) GRANT A FREE OF CHARGE, NON-EXCLUSIVE AND NON-TRANSFERABLE RIGHT TO USE THE DOWNLOAD. USE OF THIS DOWNLOAD IS PERMITTED FOR INTERNAL BUSINESS PURPOSES ONLY.

THIS DOWNLOAD IS MADE AVAILABLE ON AN "AS IS" BASIS WITHOUT WARRANTY OF ANY KIND, WHETHER EXPRESS OR IMPLIED, ORAL OR WRITTEN, INCLUDING, WITHOUT LIMITATION, ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE OR NON-INFRINGEMENT.

MEDIDATA SHALL HAVE NO LIABILITY FOR DIRECT, INDIRECT, INCIDENTAL, CONSEQUENTIAL OR PUNITIVE DAMAGES, INCLUDING, WITHOUT LIMITATION, CLAIMS FOR LOST PROFITS, BUSINESS INTERRUPTION AND LOSS OF DATA THAT IN ANY WAY RELATE TO THIS DOWNLOAD, WHETHER OR NOT MEDIDATA HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES AND NOTWITHSTANDING THE FAILURE OF THE ESSENTIAL PURPOSE OF ANY REMEDY.

YOUR USE OF THIS DOWNLOAD SHALL BE AT YOUR SOLE RISK. NO SUPPORT OF ANY KIND OF THE DOWNLOAD IS PROVIDED BY MEDIDATA.
