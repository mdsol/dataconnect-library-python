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
- [Features](#features)
- [Public API Reference](#public-api-reference)
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

- You need a valid Dataconnect access token.
- Default connection settings used by the client:
  - Host: `enodia-gateway.platform.imedidata.com`
  - Port: `443`
  - TLS: enabled

## Installation

Choose one of the following approaches.

### Option 1: Install from source (recommended for this repository)

```bash
git clone <repository-url>
cd Dataconnect-library-python
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Option 2: Install using Poetry

```bash
git clone <repository-url>
cd Dataconnect-library-python
poetry install
poetry shell
```

## Quick Start

```python
from uuid import UUID

from Dataconnect import DataconnectClient

with DataconnectClient.connect(token="your-bearer-token") as client:
	studies = client.get_studies()
	print(f"Found {len(studies)} studies")

	if studies and studies[0].environments:
    study_environment_uuid = studies[0].environments[0].uuid
    datasets_data = client.get_datasets(study_environment_uuid=study_environment_uuid, page=1, page_size=10)
    print(f"Found {datasets_data.total_records} datasets")

    if datasets_data.items:
      dataset_uuid = UUID(datasets_data.items[0].dataset_uuid)
      df = client.fetch_data(dataset_uuid, first_n_rows=100)
      print(df.head())
```

## Features

- Connect to Dataconnect with secure Arrow Flight transport.
- Get studies available to the authenticated user.
- Get datasets for a study environment with pagination and name filtering.
- Get versions for a dataset.
- Fetch dataset records as a pandas DataFrame.

## Public API Reference

The main public entry point is `Dataconnect.DataconnectClient`.

### `DataconnectClient.connect(host="enodia-gateway.platform.imedidata.com", port=443, use_tls=True, token="")`

#### Description
Creates a connected client using the default Arrow Flight transport.

#### Usage
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
| `host` | `str` | Dataconnect host. |
| `port` | `int` | Server port. |
| `use_tls` | `bool` | Enable TLS. |
| `token` | `str` | Bearer token for authorization. |

#### Output
- Returns: `DataconnectClient`

#### Data Validation
- Raises `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ServerError`, or `ValidationError` when the server/transport returns an error.

---

### `get_studies(search_study_name=None)`

#### Description
Lists studies the authenticated user can access, optionally filtered by full or partial study name.

#### Usage
```python
studies = client.get_studies(search_study_name="<search-study-name>")
for study in studies:
    print(study.uuid, study.name)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| `search_study_name` | `str | None` | Optional full or partial study name filter. |

#### Output
- Returns: `list[Study]`

#### Data Validation
- Raises `DataconnectError` subclasses for server/transport failures.

---

### `get_datasets(study_environment_uuid, search_dataset_name="", page=1, page_size=50)`

#### Description
Retrieves datasets for a specific study environment and returns paginated results.

#### Usage
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
| `study_environment_uuid` | `UUID` | Required study environment UUID. |
| `search_dataset_name` | `str` | Full or partial dataset name filter. |
| `page` | `int` | Page number for paginated results (>=1). |
| `page_size` | `int` | Number of results per page (>=1). |

#### Output
- Returns: `PaginatedResponse[Dataset]`

#### Data Validation
- Raises `ValidationError` for invalid UUID/page/page_size.
- Raises other `DataconnectError` subclasses for service failures.

---

### `get_dataset_versions(dataset_uuid)`

#### Description
Retrieves all available versions for a dataset, sorted in descending version order.

#### Usage
```python
from uuid import UUID

versions = client.get_dataset_versions(UUID("<dataset-uuid>"))
for version in versions:
    print(version.dataset_name, version.dataset_version)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| `dataset_uuid` | `UUID` | Required dataset UUID. |

#### Output
- Returns: `list[DatasetVersion]`

#### Data Validation
- Raises `ValidationError` for invalid UUID.
- Raises other `DataconnectError` subclasses for service failures.

---

### `fetch_data(dataset_uuid, first_n_rows=None)`

#### Description
Fetches dataset rows into a pandas DataFrame.

#### Usage
```python
from uuid import UUID

df = client.fetch_data(UUID("<dataset-uuid>"), first_n_rows=100)
print(df.shape)
```

#### Arguments
| Argument | Type | Description |
|---|---|---|
| `dataset_uuid` | `UUID` | Required dataset UUID. |
| `first_n_rows` | `int | None` | Optional positive row limit. |

#### Output
- Returns: `pandas.DataFrame`

#### Data Validation
- Raises `ValidationError` for invalid `dataset_uuid` or non-positive `first_n_rows`.
- Raises other `DataconnectError` subclasses for service failures.

### `close()`

Closes the underlying transport connection.

| Item | Details |
|---|---|
| Description | Releases network resources used by the client. |
| Parameters | None |
| Returns | None |
| Error handling | May raise `DataconnectError` subclasses if close fails at transport level. |

Usage example:

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
| `AuthenticationError` | Invalid or missing credentials/token. |
| `AuthorizationError` | Authenticated but not allowed to access requested resource. |
| `NotFoundError` | Requested study/dataset/resource does not exist. |
| `ServerError` | Unexpected server-side failure. |
| `ValidationError` | Invalid inputs or malformed/invalid response payloads. |

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
| `StudyEnvironment` | `uuid`, `name` |
| `Study` | `uuid`, `name`, `environments` |
| `Dataset` | `dataset_uuid`, `study_uuid`, `study_env_uuid`, `dataset_name` |
| `DatasetVersion` | `study_uuid`, `study_environment_uuid`, `dataset_uuid`, `dataset_name`, `dataset_version` |
| `Pagination` | `page`, `page_size`, `total_pages` |
| `PaginatedResponse[T]` | `total_records`, `pagination`, `items` |

