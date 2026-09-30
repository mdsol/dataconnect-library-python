"""Tests for trace metadata decoding in the concrete Arrow Flight transport."""

from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest

from dataconnect.service.error_handler import translate_error
from dataconnect.transport.arrow_flight.error_handler import parse_dataconnect_error
from dataconnect.transport.arrow_flight.transport import ArrowFlightTransport
from dataconnect.transport.models import DatasetTicket, ResourceQuery


def _make_transport() -> ArrowFlightTransport:
    with patch.object(ArrowFlightTransport, "_get_client", return_value=MagicMock()):
        return ArrowFlightTransport(host="localhost", port=5005, use_tls=False)


def _make_flight_info(app_metadata: bytes | None) -> MagicMock:
    info = MagicMock()
    info.app_metadata = app_metadata
    info.descriptor = None
    info.endpoints = []
    info.schema = pa.schema([])
    info.total_records = 0
    return info


def test_list_resources_reads_trace_id_from_app_metadata() -> None:
    transport = _make_transport()
    transport._client.list_flights.return_value = [_make_flight_info(b'{"trace_id":"trace-list-1"}')]

    result = transport.list_resources(ResourceQuery(action="studies.list"))

    assert transport.trace_id == "trace-list-1"
    assert len(result) == 1


@pytest.mark.parametrize("app_metadata", [None, b"", b"{}", b"not-json", b"\xff"])
def test_list_resources_returns_no_trace_id_for_missing_or_malformed_metadata(app_metadata: bytes | None) -> None:
    transport = _make_transport()
    transport._client.list_flights.return_value = [_make_flight_info(app_metadata)]

    transport._begin_call()
    result = transport.list_resources(ResourceQuery(action="studies.list"))

    assert transport.trace_id is None
    assert isinstance(result, list)


def test_get_ticket_reads_trace_id_from_schema_metadata() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())], metadata={b"trace_id": b"trace-get-1"})
    reader.read_chunk.side_effect = StopIteration
    transport._client.do_get.return_value = reader

    result = transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert transport.trace_id == "trace-get-1"
    assert isinstance(result.schema_bytes, bytes)
    assert isinstance(result.ipc_bytes, bytes)


def test_get_ticket_returns_no_trace_id_when_schema_metadata_is_absent() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())])
    reader.read_chunk.side_effect = StopIteration
    transport._client.do_get.return_value = reader

    result = transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert transport.trace_id is None
    assert isinstance(result.schema_bytes, bytes)


def test_client_middleware_captures_response_trace_header_and_clears_previous_value() -> None:
    transport = _make_transport()
    transport._trace_id = "previous-trace"

    middleware = transport._trace_middleware.start_call(None)

    assert transport.trace_id is None
    middleware.received_headers({"x-dataconnect-trace-id": ["current-trace"]})
    assert transport.trace_id == "current-trace"


def test_client_middleware_reads_trace_id_from_structured_pre_handler_error() -> None:
    transport = _make_transport()
    middleware = transport._trace_middleware.start_call(None)

    middleware.call_completed(
        RuntimeError('AUTH_001::{"error_code":"AUTH_001","trace_id":"structured-trace"}. Detail: Unauthenticated')
    )

    assert transport.trace_id == "structured-trace"


def test_structured_error_trace_id_is_preserved_and_printed() -> None:
    exception = RuntimeError(
        'RES_002::{"error_code":"RES_002","message":"Dataset lookup failed",'
        '"details":[{"field":"dataset_uuid",'
        '"expected":"Review and provide the correct dataset_uuid that is associated with a valid Study Environment."}],'
        '"trace_id":"structured-error-trace"}'
    )

    transport_error = parse_dataconnect_error(exception)
    public_error = translate_error(transport_error)

    assert transport_error.trace_id == "structured-error-trace"
    assert public_error.trace_id == "structured-error-trace"
    assert str(public_error).endswith(
        "    Expected: Review and provide the correct dataset_uuid that is associated with a valid Study Environment.\n"
        "    Trace ID: structured-error-trace"
    )
