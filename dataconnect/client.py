"""Public API for the DataConnect client library."""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any

import pyarrow as pa

from dataconnect import _encoding
from dataconnect.auth import BearerTokenAuth
from dataconnect.framework.pyarrow_transport import PyArrowFlightTransport
from dataconnect.framework.transport import FlightTransport
from dataconnect.models import Dataset, Study

# Flight actions / commands
_ACTION_LIST_STUDIES = "studies.list"
_ACTION_LIST_DATASETS = "datasets.list"
_ACTION_LIST_DATASET_VERSIONS = "dataset_versions.list"
_ACTION_FETCH_TICKET = "data.fetch_ticket"
_CMD_PUBLISH = "publish"
_CMD_DRY_PUBLISH = "dry_publish"

_DEFAULT_HOST = "enodia-gateway.platform.imedidata.com"
_DEFAULT_PORT = 443


class DataConnectClient:
    """Client for interacting with DataConnect services."""

    def __init__(self, transport: FlightTransport) -> None:
        """Initialize the DataConnect client with a specified transport."""
        self._transport = transport

    @classmethod
    def connect(
        cls,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        use_tls: bool = True,
        token: str = "",
    ) -> DataConnectClient:
        """Open connection to a Flight server."""
        location = f"grpc+tls://{host}:{port}"
        transport = PyArrowFlightTransport(
            location=location,
            credentials=BearerTokenAuth(token),
        )
        return cls(transport)

    def studies(self) -> list[Study]:
        """List the studies the client is authorized to access."""
        rows = self._action_json(_ACTION_LIST_STUDIES, None)
        return [Study(**r) for r in rows]

    def datasets(self, study_uuid: str) -> list[Dataset]:
        """List the datasets available for a given study."""
        body = {"study_uuid": study_uuid}
        rows = self._action_json(_ACTION_LIST_DATASETS, {"study_uuid": body})
        return [Dataset(**r) for r in rows]

    def fetch_data(self, dataset_uuid: str) -> pa.Table:
        """Fetch the data for a given dataset as a PyArrow Table."""
        body = {"dataset_uuid": dataset_uuid}
        results = self._transport.do_action(_ACTION_FETCH_TICKET, _encoding.dumps(body))
        if not results:
            raise RuntimeError("Server returned no data for the fetch_data action.")
        return self._transport.do_get(results).read_all()

    # Lifecycle
    def close(self) -> None:
        """Close the underlying transport connection."""
        self._transport.close()

    def __enter__(self) -> DataConnectClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._transport.close()

    # Helpers
    def _action_json(self, action: str, body: dict[str, Any] | None) -> Any:
        """Execute a Flight action and return the result as JSON."""
        results = self._transport.do_action(action, _encoding.dumps(body or {}))
        if not results:
            return []
        return json.loads(results.decode("utf-8"))
