# DataConnect Python Library v1.0.0

The DataConnect Python library provides a Python client for connecting to Medidata DataConnect and retrieving relevant data programmatically.
To use this library, you must have a valid iMedidata account and access to required building blocks in the Medidata Platform. For details, see the Medidata [Knowledge Hub](https://learn.medidata.com/en-US/bundle/data-connect/page/developer_center.html).

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication and Connectivity](#authentication-and-connectivity)
- [Functions](#functions)
	- [connect()](#connect)
	- [get_studies()](#get_studies)
	- [get_datasets()](#get_datasets)
	- [get_dataset_versions()](#get_dataset_versions)
	- [fetch_data()](#fetch_data)
	- [close()](#close)
- [Errors](#errors)
- [Reporting known issues](#reporting-known-issues)
- [Backend](#backend)
- [Licensing](#licensing)

## Installation

To install, follow the [Installation Guide](https://github.com/mdsol/dataconnect-library-python/blob/main/guides/dataconnect_setup.md).

## Quick Start

For end-to-end examples, see the [Usage Guide](https://github.com/mdsol/dataconnect-library-python/blob/main/guides/dataconnect_quickstart.md).

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
