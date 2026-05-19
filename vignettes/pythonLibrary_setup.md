# Data Connect Python Library - Setup

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
