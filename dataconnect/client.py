"""Public API for the DataConnect client library."""

from __future__ import annotations

import json
import warnings
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

    def fetch_data(
        self,
        dataset_uuid: str,
        study_uuid: str | None = None,
        study_environment_uuid: str | None = None,
        first_n_rows: int | None = None,
    ) -> pd.DataFrame:
        """Fetch data of a single dataset as a pandas DataFrame.

        Streams Arrow record batches over Flight and assembles them into a
        single pandas DataFrame, preserving clinical data types
        (dates, decimals, etc.).

        Parameters
        ----------
        dataset_uuid:
            UUID of the target dataset (required).
        study_uuid:
            Deprecated. The Study context is resolved automatically; this
            argument is ignored and emitting it triggers a
            ``DeprecationWarning``.
        study_environment_uuid:
            Deprecated. The Study Environment context is resolved
            automatically; this argument is ignored and emitting it triggers
            a ``DeprecationWarning``.
        first_n_rows:
            Optional row limit. When provided, only the first
            ``first_n_rows`` rows of the dataset are returned. When omitted
            (``None``), the full dataset is returned.

        Returns
        -------
        pandas.DataFrame
            The dataset materialized as a pandas DataFrame.
        """
        if study_uuid is not None and str(study_uuid).strip() != "":
            warnings.warn(
                "You only need to provide dataset_uuid; the Study context is "
                "now resolved automatically.",
                DeprecationWarning,
                stacklevel=2,
            )
        if study_environment_uuid is not None and str(study_environment_uuid).strip() != "":
            warnings.warn(
                "You only need to provide dataset_uuid; the Study Environment "
                "context is now optional, and will be resolved automatically.",
                DeprecationWarning,
                stacklevel=2,
            )

        if first_n_rows is not None and first_n_rows <= 0:
            raise ValueError("first_n_rows must be a positive integer when provided.")

        return _get_dataset(
            transport=self._transport,
            study_uuid=study_uuid,
            study_environment_uuid=study_environment_uuid,
            dataset_uuid=dataset_uuid,
            limit=first_n_rows,
        )

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


def _get_dataset(
    transport: FlightTransport,
    study_uuid: str | None,
    study_environment_uuid: str | None,
    dataset_uuid: str,
    limit: int | None,
) -> pd.DataFrame:
    """Fetch a single dataset over Arrow Flight as a pandas DataFrame.

    Mirrors the R implementation in ``R/datasets.R::.get_dataset`` /
    ``.get_dataset_raw``: builds a JSON Flight ticket and streams record
    batches into a single :class:`pandas.DataFrame`.
    """
    if not dataset_uuid or not str(dataset_uuid).strip():
        raise ValueError("dataset_uuid must be provided.")

    ticket_data: dict[str, Any] = {
        "study_uuid": study_uuid,
        "study_env_uuid": study_environment_uuid,
        "dataset_uuid": dataset_uuid,
        "dataset_name": "",
        "limit": limit,
    }

    ticket = _encoding.dumps(ticket_data)
    stream = transport.do_get(ticket)

    # Stream batches directly into a single Arrow Table to minimize memory
    # overhead for large datasets, then convert to pandas in one pass so that
    # clinical data types (dates, decimals, etc.) are preserved.
    batches: list[pa.RecordBatch] = []
    schema: pa.Schema | None = None
    for batch in stream:
        if schema is None:
            schema = batch.schema
        batches.append(batch)

    if not batches:
        return pd.DataFrame()

    table = pa.Table.from_batches(batches, schema=schema)
    return table.to_pandas()
