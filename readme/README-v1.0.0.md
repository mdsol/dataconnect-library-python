# Dataconnect Python Library v1.0.0

The Dataconnect Python library provides a Python client for connecting to Medidata Dataconnect and retrieving relevant data programmatically.
To use this library, you must have a valid iMedidata account and access to required building blocks in the Medidata Platform. For details, see the Medidata [Knowledge Hub](https://learn.medidata.com/en-US/bundle/data-connect/page/developer_center.html).

## Table of Contents

- [Environment Setup and Requirements](#environment-setup-and-requirements)
	- [System Requirements](#system-requirements)
	- [Authentication and Connectivity](#authentication-and-connectivity)
- [Installation](#installation)
	- [Option 1: Install from source (recommended for this repository)](#option-1-install-from-source-recommended-for-this-repository)
	- [Option 2: Install using Poetry](#option-2-install-using-poetry)
- [Quick Start](#quick-start)
- [Functions](#functions)
	- [connect()](#connect)
	- [get_studies()](#get_studies)
	- [get_datasets()](#get_datasets)
	- [get_dataset_versions()](#get_dataset_versions)
	- [fetch_data()](#fetch_data)
	- [close()](#close)
- [Error Handling](#error-handling)
- [Data Models](#data-models)

## Environment Setup and Requirements

### System Requirements

| Requirement       | Version / Notes          |
|-------------------|--------------------------|
| Python            | 3.13                     |
| Operating systems | macOS, Linux, Windows    |
| Core dependencies | pyarrow 19.x, pandas 2.x |

### Authentication and Connectivity

* **Retrieving data:** You must have a user token to establish a connection between your Python environment and Medidata Data Connect. You can generate this token through Data Connect’s Developer Center. For details, see [here](https://learn.medidata.com/en-US/bundle/data-connect/page/developer_center.html). Medidata recommends that you save the token in a separate file and input it into the below initiation function.

* **Publish data:** You must have a project token to publish a dataset from your Python environment to Medidata Data Connect. You can generate this token through Data Connect > Transformations, by creating a Custom Code project. For details, see [here](https://learn.medidata.com/en-US/bundle/data-connect/page/generate_custom_code_projects.html).

## Installation

# Installation

To install, follow the [Installation Guide](https://github.com/mdsol/dataconnect-library-r/blob/main/vignettes/dataconnect/readme/vignettes/pythonLibrary_usage.md).

## Functions

The main public entry point is `DataconnectClient`.

### connect()

#### Description
Creates a connected client using the default Arrow Flight transport.

#### Usage
`connect(host="enodia-gateway.platform.imedidata.com", port=443, use_tls=True, token="")`

#### Example
```python
from Dataconnect import DataconnectClient

client = DataconnectClient.connect(token="<access-token>")
try:
    studies = client.get_studies()
finally:
    client.close()
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| host | str | Dataconnect host |
| port | int | Server port |
| use_tls | bool | Enable TLS |
| token | str | Authentication token, this is the user authentication token generated from the Developer Center in Medidata Data Connect |

#### Output
- Returns: `DataconnectClient`

#### Data Validation
- Raises `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ServerError`, or `ValidationError` when the server/transport returns an error.

---

### get_studies()

#### Description
Lists studies the authenticated user can access, optionally filtered by full or partial study name.

#### Usage
`get_studies(search_study_name=None)`

#### Example
```python
studies = client.get_studies(search_study_name="<search-study-name>")
for study in studies:
    print(study.uuid, study.name)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| search_study_name | str or None | Optional full or partial study name filter |

#### Output
- Returns: `list[Study]`

#### Data Validation
- Raises `DataconnectError` subclasses for server/transport failures.

---

### get_datasets()

#### Description
Retrieves datasets for a specific study environment and returns paginated results.

#### Usage
`get_datasets(study_environment_uuid, search_dataset_name="", page=1, page_size=50)`

#### Example
```python
from uuid import UUID

response = client.get_datasets(
    study_environment_uuid=UUID("<study-environment-uuid>"),
    search_dataset_name="<search-dataset-name>",
    page=1,
    page_size=25,
)

print(response.total_records)
for dataset in response.items:
    print(dataset.dataset_uuid, dataset.dataset_name)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| study_environment_uuid | UUID | Unique iMedidata study environment identifier. You can find this in iMedidata’s Developer Info details |
| search_dataset_name | str | Full or partial dataset name filter |
| page | int | Page number for paginated results (>=1) |
| page_size | int | Number of results per page (>=1) |

#### Output
- Returns: `PaginatedResponse[Dataset]`

#### Data Validation
- Raises `ValidationError` for invalid UUID/page/page_size.
- Raises other `DataconnectError` subclasses for service failures.

---

### get_dataset_versions()

#### Description
Retrieves all available versions for a dataset, sorted in descending version order.

#### Usage
`get_dataset_versions(dataset_uuid)`

#### Example
```python
from uuid import UUID

versions = client.get_dataset_versions(UUID("<dataset-uuid>"))
for version in versions:
    print(version.dataset_name, version.dataset_version)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| dataset_uuid | UUID | Unique iMedidata dataset identifier. This is available in the output of datasets() and dataset_versions() functions |

#### Output
- Returns: `list[DatasetVersion]`

#### Data Validation
- Raises `ValidationError` for invalid UUID.
- Raises other `DataconnectError` subclasses for service failures.

---

### fetch_data()

#### Description
Fetches dataset rows into a pandas DataFrame.

### Usage
`fetch_data(dataset_uuid, first_n_rows=None)`

#### Example
```python
from uuid import UUID

df = client.fetch_data(UUID("<dataset-uuid>"), first_n_rows=100)
print(df.shape)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| dataset_uuid | UUID | Unique iMedidata dataset identifier. This is available in the output of datasets() and dataset_versions() functions |
| first_n_rows | int or None | Optional positive row limit |

#### Output
- Returns: `pandas.DataFrame`

#### Data Validation
- Raises `ValidationError` for invalid `dataset_uuid` or non-positive `first_n_rows`.
- Raises other `DataconnectError` subclasses for service failures.

### close()

Closes the underlying transport connection.

| Item | Details |
|---|---|
| Description | Releases network resources used by the client |
| Parameters | None |
| Returns | None |
| Error handling | May raise `DataconnectError` subclasses if close fails at transport level |

Example example:

```python
client = DataconnectClient.connect(token="<access-token>")
try:
	pass
finally:
	client.close()
```

## Error Handling

All public errors inherit from `DataconnectError`.

| Exception | Typical meaning |
|---|---|
| AuthenticationError | Invalid or missing credentials/token |
| AuthorizationError | Authenticated but not allowed to access requested resource |
| NotFoundError | Requested study/dataset/resource does not exist |
| ServerError | Unexpected server-side failure |
| ValidationError | Invalid inputs or malformed/invalid response payloads |

Example:

```python
from Dataconnect import (
	AuthenticationError,
	AuthorizationError,
	DataconnectError,
	NotFoundError,
	ValidationError,
)

try:
	studies = client.get_studies()
except AuthenticationError as exc:
	print("Authentication failed:", exc)
except AuthorizationError as exc:
	print("Not authorized:", exc)
except NotFoundError as exc:
	print("Resource not found:", exc)
except ValidationError as exc:
	print("Invalid request:", exc)
except DataconnectError as exc:
	print("Dataconnect request failed:", exc)
```

## Data Models

| Model | Fields |
|---|---|
| StudyEnvironment | `uuid`, `name` |
| Study | `uuid`, `name`, `environments` |
| Dataset | `dataset_uuid`, `study_uuid`, `study_env_uuid`, `dataset_name` |
| DatasetVersion | `study_uuid`, `study_environment_uuid`, `dataset_uuid`, `dataset_name`, `dataset_version` |
| Pagination | `page`, `page_size`, `total_pages` |
| PaginatedResponse[T] | `total_records`, `pagination`, `items` |

