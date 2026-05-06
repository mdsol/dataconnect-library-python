from dataconnect import DataConnectClientfrom dataconnect import DataConnectClient

# dataconnect-library-python

Python SDK for the [Medidata DataConnect](https://github.com/mdsol/dataconnect-library-r) service.

---

## Transport note

The DataConnect service uses **Apache Arrow Flight** (gRPC binary protocol),
**not** a plain REST/HTTP API.  `pyarrow.flight` is the primary transport
dependency.

---

## Installation

```bash
pip install dataconnect          # core (pyarrow + pydantic + httpx)
pip install dataconnect[pandas]  # + pandas for .to_pandas() on results
```

Requires **Python ≥ 3.13**.

---

## Quick start

```python
import pyarrow as pa
from dataconnect import DataConnectClient


with DataConnectClient.connect(
    host="dataconnect.example.com",
    port=443,
    token="your-bearer-token",
) as client:

    studies = client.get_studies(search_study_name="ACME")
```
## Development

```bash
pip install -e ".[dev]"
pytest
```
