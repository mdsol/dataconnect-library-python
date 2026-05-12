from __future__ import annotations

import json
from uuid import UUID

import pandas as pd
import pyarrow as pa
import pytest

from dataconnect.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
    NotFoundError,
    QueryError,
    ServerError,
    ValidationError,
)
from dataconnect.models import DatasetVersion
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.transport.errors import (
    TransportAuthenticationError,
    TransportAuthorizationError,
    TransportConnectionError,
    TransportIOError,
    TransportNotFoundError,
    TransportStatusError,
)
from dataconnect.transport.models import DataRef, DataTable, ResourceInfo, ResourceQuery


class _FakeTransport:
    def __init__(
        self,
        resources: list[ResourceInfo] | None = None,
        error: Exception | None = None,
        data_table: DataTable | None = None,
        do_get_error: Exception | None = None,
    ) -> None:
        self._resources = resources or []
        self._error = error
        self._data_table = data_table
        self._do_get_error = do_get_error
        self.last_request: ResourceQuery | None = None
        self.last_do_get_request: ResourceQuery | None = None

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        self.last_request = request
        if self._error is not None:
            raise self._error
        return self._resources

    def do_get(self, request: ResourceQuery) -> DataTable:
        self.last_do_get_request = request
        if self._do_get_error is not None:
            raise self._do_get_error
        assert self._data_table is not None, "_FakeTransport: no data_table configured"
        return self._data_table

    def close(self) -> None:
        return None


def _make_ipc_table(data: dict[str, list[object]]) -> DataTable:
    """Serialise a dict of columns to an Arrow IPC stream wrapped in DataTable."""
    arrow_table = pa.table(data)
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, arrow_table.schema)
    writer.write_table(arrow_table)
    writer.close()
    ipc_bytes = sink.getvalue().to_pybytes()
    schema_bytes = arrow_table.schema.serialize().to_pybytes()
    return DataTable(schema_bytes=schema_bytes, ipc_bytes=ipc_bytes)


def _resource_with_ticket_json(payload: dict[str, object]) -> ResourceInfo:
    return ResourceInfo(
        descriptor=b"",
        endpoints=[DataRef(ticket=json.dumps(payload).encode("utf-8"))],
        total_records=1,
        schema_bytes=b"",
    )


def test_get_dataset_versions_returns_mapped_models_and_builds_request() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    payload = {
        "study_uuid": "64a98a9b-1512-44c8-92af-e4cab0183670",
        "study_env_uuid": "4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
        "dataset_uuid": str(dataset_uuid),
        "dataset_name": "labs",
        "dataset_version": "1",
    }
    transport = _FakeTransport(resources=[_resource_with_ticket_json(payload)])
    service = DefaultDataConnectService(transport)

    result = service.get_dataset_versions(dataset_uuid)

    assert result == [
        DatasetVersion(
            study_uuid=UUID("64a98a9b-1512-44c8-92af-e4cab0183670"),
            study_environment_uuid=UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a"),
            dataset_uuid=dataset_uuid,
            dataset_name="labs",
            dataset_version="1",
        )
    ]
    assert transport.last_request is not None
    assert transport.last_request.action == "dataset_versions.list"
    assert json.loads(transport.last_request.body) == {"dataset_uuid": str(dataset_uuid)}


def test_get_dataset_versions_translates_transport_errors() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(error=TransportConnectionError("cannot connect"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ConnectionError, match="cannot connect"):
        service.get_dataset_versions(dataset_uuid)


def test_get_dataset_versions_raises_validation_error_on_bad_payload() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    bad_payload = {
        "study_uuid": "64a98a9b-1512-44c8-92af-e4cab0183670",
        "study_env_uuid": "4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
        "dataset_uuid": str(dataset_uuid),
        "dataset_name": "labs",
        # dataset_version intentionally omitted to trigger mapper validation failure.
    }
    transport = _FakeTransport(resources=[_resource_with_ticket_json(bad_payload)])
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError, match="Unexpected dataset versions response format"):
        service.get_dataset_versions(dataset_uuid)


def test_manual_resource_query_body_can_be_used_directly() -> None:
    """Assert that constructing a ResourceQuery with a JSON body string works as expected.

    This mirrors the alternative to `append_body` where the caller provides a
    JSON-encoded `body` explicitly (using json.dumps to guarantee valid JSON).
    """
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")

    # Build the compact JSON string the same way append_body would

    body_str = json.dumps({"dataset_uuid": str(dataset_uuid)}, separators=(",", ":"))

    rq = ResourceQuery(action="dataset_versions.list", body=body_str)

    assert json.loads(rq.body) == {"dataset_uuid": str(dataset_uuid)}
    # compact representation (no spaces)
    assert rq.body == body_str


def test_get_dataset_versions_raises_validation_error_on_invalid_uuid_input() -> None:
    """Passing a non-UUID to the service should raise ValidationError."""
    transport = _FakeTransport(resources=[])
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as excinfo:
        service.get_dataset_versions("not-a-uuid")

    # Ensure our validation code path is exercised
    assert "dataset_uuid must be a valid UUID" in str(excinfo.value)


def test_get_dataset_versions_raises_validation_error_on_empty_input() -> None:
    """Passing an empty string to the service should raise ValidationError."""
    transport = _FakeTransport(resources=[])
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as excinfo:
        service.get_dataset_versions("")

    # Ensure our validation code path is exercised
    assert "dataset_uuid must be a valid UUID" in str(excinfo.value)


def test_get_dataset_versions_raises_validation_error_on_zero_input() -> None:
    """Passing an empty string to the service should raise ValidationError."""
    transport = _FakeTransport(resources=[])
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError) as excinfo:
        service.get_dataset_versions(UUID(int=0))

    # Ensure our validation code path is exercised
    assert "dataset_uuid must not be empty" in str(excinfo.value)


# ---------------------------------------------------------------------------
# fetch_data tests
# ---------------------------------------------------------------------------


def test_fetch_data_returns_dataframe_with_correct_values() -> None:
    """Happy path: fetched IPC bytes are mapped to a DataFrame matching the source data."""
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    source = {"subject_id": ["S001", "S002"], "age": [30, 45]}
    transport = _FakeTransport(data_table=_make_ipc_table(source))
    service = DefaultDataConnectService(transport)

    result = service.fetch_data(dataset_uuid)

    assert isinstance(result, pd.DataFrame)
    assert result["subject_id"].tolist() == source["subject_id"]
    assert result["age"].tolist() == source["age"]


def test_fetch_data_builds_correct_request() -> None:
    """The request sent to the transport must carry the right action, dataset_uuid, and limit."""
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    service.fetch_data(dataset_uuid, first_n_rows=10)

    assert transport.last_do_get_request is not None
    assert transport.last_do_get_request.action == "data.fetch_ticket"
    body = json.loads(transport.last_do_get_request.body)
    assert body["dataset_uuid"] == str(dataset_uuid)
    assert body["limit"] == 10


def test_fetch_data_no_limit_sends_none_in_body() -> None:
    """When first_n_rows is omitted, limit must be None in the request body."""
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    service.fetch_data(dataset_uuid)

    body = json.loads(transport.last_do_get_request.body)  # type: ignore[union-attr]
    assert body["limit"] is None


def test_fetch_data_returns_empty_dataframe_for_empty_table() -> None:
    """An IPC stream with no rows should produce an empty DataFrame."""
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"col": pa.array([], type=pa.int32())}))
    service = DefaultDataConnectService(transport)

    result = service.fetch_data(dataset_uuid)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    assert "col" in result.columns


def test_fetch_data_raises_value_error_on_zero_first_n_rows() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValueError, match="first_n_rows must be a positive integer"):
        service.fetch_data(dataset_uuid, first_n_rows=0)


def test_fetch_data_raises_value_error_on_negative_first_n_rows() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValueError, match="first_n_rows must be a positive integer"):
        service.fetch_data(dataset_uuid, first_n_rows=-5)


def test_fetch_data_raises_value_error_on_non_int_first_n_rows() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValueError, match="first_n_rows must be a positive integer"):
        service.fetch_data(dataset_uuid, first_n_rows="abc")  # type: ignore[arg-type]


def test_fetch_data_raises_value_error_on_none_uuid() -> None:
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises((ValueError, TypeError)):
        service.fetch_data(None)  # type: ignore[arg-type]


def test_fetch_data_raises_value_error_on_empty_uuid() -> None:
    transport = _FakeTransport(data_table=_make_ipc_table({"x": [1]}))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValueError, match="must not be an empty UUID"):
        service.fetch_data(UUID(int=0))


# Transport-error translation tests


def test_fetch_data_translates_connection_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(do_get_error=TransportConnectionError("timeout"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ConnectionError, match="timeout"):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_authentication_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(do_get_error=TransportAuthenticationError("bad token"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(AuthenticationError, match="bad token"):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_authorization_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(do_get_error=TransportAuthorizationError("forbidden"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(AuthorizationError, match="forbidden"):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_not_found_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(do_get_error=TransportNotFoundError("dataset not found"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(NotFoundError, match="dataset not found"):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_io_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(do_get_error=TransportIOError("stream broken"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(QueryError, match="stream broken"):
        service.fetch_data(dataset_uuid)


def test_fetch_data_translates_status_error() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(do_get_error=TransportStatusError("internal", status_code=13))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ServerError, match="internal"):
        service.fetch_data(dataset_uuid)
