"""Unit tests for DefaultDataConnectService.fetch_data."""

from __future__ import annotations

from uuid import UUID

import pandas as pd
import pyarrow as pa
import pytest

from dataconnect.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.transport.errors import (
    TransportAuthenticationError,
    TransportAuthorizationError,
    TransportNotFoundError,
    TransportServerError,
)
from dataconnect.transport.models import DatasetTicket, DataTable, ResourceInfo, ResourceQuery

# ---------------------------------------------------------------------------
# Fake transport
# ---------------------------------------------------------------------------


class _FakeTransport:
    """Minimal Transport stub for unit tests."""

    def __init__(
        self,
        data_table: DataTable | None = None,
        get_ticket_error: Exception | None = None,
    ) -> None:
        self._data_table = data_table
        self._get_ticket_error = get_ticket_error
        self.last_ticket: DatasetTicket | None = None

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        return []

    def get_ticket(self, ticket: DatasetTicket) -> DataTable:
        self.last_ticket = ticket
        if self._get_ticket_error is not None:
            raise self._get_ticket_error
        assert self._data_table is not None
        return self._data_table

    def close(self) -> None:
        return None


def _make_ipc_table(data: dict) -> DataTable:
    arrow_table = pa.table(data)
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, arrow_table.schema)
    writer.write_table(arrow_table)
    writer.close()
    return DataTable(
        schema_bytes=arrow_table.schema.serialize().to_pybytes(),
        ipc_bytes=sink.getvalue().to_pybytes(),
    )


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


def test_fetch_data_returns_dataframe_with_correct_values() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    source = {"subject_id": ["S001", "S002"], "age": [30, 45]}
    transport = _FakeTransport(data_table=_make_ipc_table(source))
    service = DefaultDataConnectService(transport)

    result = service.fetch_data(dataset_uuid)

    assert isinstance(result, pd.DataFrame)
    assert result["subject_id"].tolist() == source["subject_id"]
    assert result["age"].tolist() == source["age"]


def test_fetch_data_builds_correct_ticket() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    service.fetch_data(dataset_uuid, first_n_rows=10)

    assert transport.last_ticket is not None
    assert transport.last_ticket.dataset_uuid == str(dataset_uuid)
    assert transport.last_ticket.limit == 10


def test_fetch_data_no_limit_sends_none_in_ticket() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    service.fetch_data(dataset_uuid)

    assert transport.last_ticket is not None
    assert transport.last_ticket.limit is None


def test_fetch_data_returns_empty_dataframe_for_empty_table() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"col": pa.array([], type=pa.int32())}))
    service = DefaultDataConnectService(transport)

    result = service.fetch_data(dataset_uuid)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    assert "col" in result.columns


# ---------------------------------------------------------------------------
# Validation — dataset_uuid
# ---------------------------------------------------------------------------


def test_fetch_data_raises_validation_error_on_none_uuid() -> None:
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as exc_info:
        service.fetch_data(None)  # type: ignore[arg-type]

    assert exc_info.value.error_code == "VAL_C_DATASET_UUID"


def test_fetch_data_raises_validation_error_on_zero_uuid() -> None:
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as exc_info:
        service.fetch_data(UUID(int=0))

    assert exc_info.value.error_code == "VAL_C_DATASET_UUID"


def test_fetch_data_raises_validation_error_on_string_uuid() -> None:
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as exc_info:
        service.fetch_data("073410b6-79be-3e7d-ae37-92f6e054013e")  # type: ignore[arg-type]

    assert exc_info.value.error_code == "VAL_C_DATASET_UUID"


# ---------------------------------------------------------------------------
# Validation — first_n_rows
# ---------------------------------------------------------------------------


def test_fetch_data_raises_validation_error_on_zero_first_n_rows() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as exc_info:
        service.fetch_data(dataset_uuid, first_n_rows=0)

    assert exc_info.value.error_code == "VAL_C_FIRST_N_ROWS"
    assert exc_info.value.details is not None
    assert exc_info.value.details[0].field == "first_n_rows"


def test_fetch_data_raises_validation_error_on_negative_first_n_rows() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as exc_info:
        service.fetch_data(dataset_uuid, first_n_rows=-5)

    assert exc_info.value.error_code == "VAL_C_FIRST_N_ROWS"


def test_fetch_data_raises_validation_error_on_non_int_first_n_rows() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as exc_info:
        service.fetch_data(dataset_uuid, first_n_rows="abc")  # type: ignore[arg-type]

    assert exc_info.value.error_code == "VAL_C_FIRST_N_ROWS"


# ---------------------------------------------------------------------------
# Transport-error translation
# ---------------------------------------------------------------------------


def test_fetch_data_translates_authentication_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(
        get_ticket_error=TransportAuthenticationError(error_code="AUTH_E_001", message="bad token")
    )
    service = DefaultDataConnectService(transport)

    with pytest.raises(AuthenticationError):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_authorization_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(
        get_ticket_error=TransportAuthorizationError(error_code="AUTHZ_001", message="forbidden")
    )
    service = DefaultDataConnectService(transport)

    with pytest.raises(AuthorizationError):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_not_found_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(
        get_ticket_error=TransportNotFoundError(error_code="RES_001", message="dataset not found")
    )
    service = DefaultDataConnectService(transport)

    with pytest.raises(NotFoundError):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_server_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(
        get_ticket_error=TransportServerError(error_code="INT_001", message="internal error")
    )
    service = DefaultDataConnectService(transport)

    with pytest.raises(ServerError):
        service.fetch_data(dataset_uuid)
