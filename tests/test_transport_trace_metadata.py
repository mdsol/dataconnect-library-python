"""Tests for trace metadata decoding in the concrete Arrow Flight transport."""

import json
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.flight as flight
import pytest

from dataconnect.service.error_handler import translate_error
from dataconnect.transport.arrow_flight.error_handler import extract_error_payload, parse_dataconnect_error
from dataconnect.transport.arrow_flight.transport import ArrowFlightTransport
from dataconnect.transport.errors import TransportAuthenticationError, TransportError
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


def test_list_resources_keeps_trace_id_when_stream_is_interrupted() -> None:
    transport = _make_transport()

    def interrupted_stream() -> object:
        yield _make_flight_info(b'{"trace_id":"trace-list-partial"}')
        raise RuntimeError("stream interrupted")

    transport._client.list_flights.return_value = interrupted_stream()

    with pytest.raises(TransportError) as error:
        transport.list_resources(ResourceQuery(action="studies.list"))

    assert error.value.trace_id == "trace-list-partial"
    assert transport.trace_id == "trace-list-partial"


def test_get_ticket_keeps_schema_trace_id_when_chunk_read_is_interrupted() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())], metadata={b"trace_id": b"trace-get-partial"})
    reader.read_chunk.side_effect = flight.FlightError("stream interrupted")
    transport._client.do_get.return_value = reader

    with pytest.raises(TransportError) as error:
        transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert error.value.trace_id == "trace-get-partial"
    assert transport.trace_id == "trace-get-partial"


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


def test_get_ticket_ignores_malformed_trace_id_metadata() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())], metadata={b"trace_id": b"\xff"})
    reader.read_chunk.side_effect = StopIteration
    transport._client.do_get.return_value = reader

    result = transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert isinstance(result.schema_bytes, bytes)
    assert transport.trace_id is None


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


def test_enodia_normalization_preserves_trace_id_from_structured_error() -> None:
    exception = RuntimeError('FlightUnauthenticatedError: AUTH_001::{"error_code":"AUTH_001","trace_id":"auth-trace"}')

    transport_error = parse_dataconnect_error(exception)

    assert transport_error.error_code == "AUTH_001"
    assert transport_error.trace_id == "auth-trace"


def test_get_ticket_preserves_typed_error_through_nested_conversion() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())])
    reader.read_chunk.side_effect = flight.FlightError('AUTH_001::{"error_code":"AUTH_001","trace_id":"nested-trace"}')
    transport._client.do_get.return_value = reader

    with pytest.raises(TransportAuthenticationError) as error:
        transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert error.value.error_code == "AUTH_001"
    assert error.value.trace_id == "nested-trace"


def test_transport_attaches_header_trace_id_to_unstructured_error() -> None:
    transport = _make_transport()

    def fail_after_header(*_args: object, **_kwargs: object) -> None:
        middleware = transport._trace_middleware.start_call(None)
        middleware.received_headers({"x-dataconnect-trace-id": ["header-trace"]})
        raise RuntimeError("Something went wrong")

    transport._client.do_get.side_effect = fail_after_header

    with pytest.raises(TransportError) as error:
        transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert error.value.trace_id == "header-trace"


def test_header_trace_id_takes_precedence_over_payload_trace_id() -> None:
    exception = RuntimeError('AUTH_001::{"error_code":"AUTH_001","trace_id":"payload-trace"}')

    transport_error = parse_dataconnect_error(exception, trace_id="header-trace")

    assert transport_error.trace_id == "header-trace"


def test_pre_request_error_does_not_carry_previous_trace_id() -> None:
    transport = _make_transport()
    transport._trace_id = "stale-trace"

    transport._client.do_get.side_effect = RuntimeError("connection failed")

    with pytest.raises(TransportError) as error:
        transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert error.value.trace_id is None


@pytest.mark.parametrize(
    "message",
    [
        "Required input parameters are missing or invalid",
        'Required input "config" is invalid',
    ],
)
def test_client_middleware_and_error_parser_read_trace_from_escaped_ipv6_error(message: str) -> None:
    trace_id = "trace-583f90d5250b271c72802814d94f47ad"
    payload = json.dumps(
        {
            "error_code": "VAL_007",
            "message": message,
            "timestamp": "2026-10-05T10:19:22.422365+00:00",
            "details": [
                {
                    "field": "config",
                    "message": "Config validation failed in dry publish.",
                    "expected": "Ensure the dataset name, key columns, and source datasets are valid.",
                }
            ],
            "trace_id": trace_id,
        }
    )
    escaped_payload = json.dumps(payload)[1:-1]
    exception = RuntimeError(
        "UNKNOWN:Error received from peer ipv6:%5B::1%5D:5007 "
        '{created_time:"2026-10-05T10:19:22.4546385+00:00", grpc_status:2, '
        f'grpc_message:"VAL_007::{escaped_payload}"}}. Detail: Failed'
    )
    transport = _make_transport()
    middleware = transport._trace_middleware.start_call(None)

    middleware.call_completed(exception)
    transport_error = parse_dataconnect_error(exception)
    public_error = translate_error(transport_error)

    assert transport.trace_id == trace_id
    assert transport_error.error_code == "VAL_007"
    assert transport_error.message == message
    assert transport_error.trace_id == trace_id
    assert transport_error.details is not None
    assert transport_error.details[0].field == "config"
    assert transport_error.details[0].message == "Config validation failed in dry publish."
    assert public_error.trace_id == trace_id


def test_error_parser_rejects_trace_only_nested_detail_as_payload() -> None:
    message = 'VAL_007::{"details":[{"trace_id":"nested-trace"}]}'

    assert extract_error_payload(message) is None


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
