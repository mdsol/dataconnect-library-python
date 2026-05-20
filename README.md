# dataconnect-library-python

Python SDK for the [Medidata DataConnect](https://github.com/mdsol/dataconnect-library-r) service.

---

## Transport note

The DataConnect service uses **Apache Arrow Flight** (gRPC binary protocol), and **not** a plain REST/HTTP API.  `pyarrow.flight` is the primary transport
dependency.

---

## Installation

```bash
pip install dataconnect          # core (pyarrow)
pip install dataconnect[pandas]  # + pandas for .to_pandas() on results
```

Requires **Python ≥ 3.13**.

---

## Quick start

```python
from uuid import UUID

from dataconnect import DataConnectClient


with DataConnectClient.connect(
    host="dataconnect.example.com",
    port=443,
    token="your-bearer-token",
) as client:

    result = client.get_studies(search_study_name="ACME")
    print(result.total)    # total number of studies accessible to the user
    print(result.studies)  # list of Study objects

    pagination = client.get_datasets(study_environment_uuid=UUID("cec9f2a7-07ba-4fa8-bfcf-34fbc5d56793"))
    datasets = pagination.items

```
## Development

```bash
pip install -e ".[dev]"
pytest
```
