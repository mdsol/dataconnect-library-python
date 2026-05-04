"""Public API for the DataConnect client library."""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any

import pandas as pd
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

    def fetch_data(self, dataset_uuid: str, first_n_rows: int | None = None) -> pd.DataFrame:
        """Fetch data for a dataset and return a pandas DataFrame.

        Data is transferred using Arrow Flight DoGet and converted to pandas in
        streaming batches to reduce peak memory overhead.
        """
        if not dataset_uuid or not dataset_uuid.strip():
            raise ValueError("dataset_uuid must be a non-empty string.")

        if first_n_rows is not None:
            if isinstance(first_n_rows, bool) or not isinstance(first_n_rows, int):
                raise TypeError("first_n_rows must be an integer when provided.")
            if first_n_rows < 0:
                raise ValueError("first_n_rows must be >= 0 when provided.")

        ticket_payload: dict[str, Any] = {
            "study_uuid": None,
            "study_env_uuid": None,
            "dataset_uuid": dataset_uuid,
            "dataset_name": "",
        }

        if first_n_rows is not None:
            ticket_payload["limit"] = int(first_n_rows)

        stream = self._transport.do_get(_encoding.dumps(ticket_payload))
        return self._stream_to_pandas(stream, first_n_rows)

    def _stream_to_pandas(
        self,
        stream: pa.RecordBatchReader | Any,
        first_n_rows: int | None,
    ) -> pd.DataFrame:
        """Convert a record-batch stream into a pandas DataFrame."""
        if first_n_rows == 0:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        remaining = first_n_rows

        for batch in stream:
            current_batch = batch
            if remaining is not None:
                if remaining <= 0:
                    break
                if batch.num_rows > remaining:
                    current_batch = batch.slice(0, remaining)

            frames.append(
                current_batch.to_pandas(
                    types_mapper=pd.ArrowDtype,
                    date_as_object=False,
                    timestamp_as_object=False,
                )
            )

            if remaining is not None:
                remaining -= current_batch.num_rows

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True, copy=False)

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
