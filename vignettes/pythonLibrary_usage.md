# DataConnect Python Usage Guide

This guide contains runnable examples for all public `DataConnectClient` functions.

## Prerequisites

- Python 3.13
- Installed package dependencies
- A valid Data Connect user token
- A valid project token

## connect()

```python
from dataconnect import DataConnectClient

client = DataConnectClient.connect(token="<access-token>")
try:
	studies = client.get_studies()
	print(f"Found {len(studies)} studies")
finally:
	client.close()
```

## get_studies()

```python
from dataconnect import DataConnectClient

with DataConnectClient.connect(token="<access-token>") as client:
	studies = client.get_studies(search_study_name="<search-study-name>")
	for study in studies:
		print(study.uuid, study.name)
```

## get_datasets()

```python
from dataconnect import DataConnectClient

with DataConnectClient.connect(token="<access-token>") as client:
	response = client.get_datasets(
		study_environment_uuid="<study-environment-uuid>",
		search_dataset_name="<search-dataset-name>",
		page=1,
		page_size=25,
	)

	print(response.total_records)
	for dataset in response.items:
		print(dataset.dataset_uuid, dataset.dataset_name)
```

## get_dataset_versions()

```python
from uuid import UUID

from dataconnect import DataConnectClient

with DataConnectClient.connect(token="<access-token>") as client:
	versions = client.get_dataset_versions(UUID("<dataset-uuid>"))
	for version in versions:
		print(version.dataset_name, version.dataset_version)
```

## fetch_data()

```python
from uuid import UUID

from dataconnect import DataConnectClient

with DataConnectClient.connect(token="<access-token>") as client:
	df = client.fetch_data(UUID("<dataset-uuid>"), first_n_rows=100)
	print(df.shape)
	print(df.head())
```

## close()

```python
from dataconnect import DataConnectClient

client = DataConnectClient.connect(token="<access-token>")
try:
	pass
finally:
	client.close()
```

## Error Handling Example

```python
from dataconnect import (
	AuthenticationError,
	AuthorizationError,
	DataConnectClient,
	DataConnectError,
	NotFoundError,
	ValidationError,
)

try:
	with DataConnectClient.connect(token="<access-token>") as client:
		studies = client.get_studies()
		print(studies)
except AuthenticationError as exc:
	print("Authentication failed:", exc)
except AuthorizationError as exc:
	print("Not authorized:", exc)
except NotFoundError as exc:
	print("Resource not found:", exc)
except ValidationError as exc:
	print("Invalid request:", exc)
except DataConnectError as exc:
	print("DataConnect request failed:", exc)
```
