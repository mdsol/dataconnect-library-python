"""Tests for trace metadata decoding in the concrete Arrow Flight transport."""

from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest

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

    assert result.trace_id == "trace-list-1"
    assert len(result.resources) == 1


@pytest.mark.parametrize("app_metadata", [None, b"", b"{}", b"not-json", b"\xff"])
def test_list_resources_returns_no_trace_id_for_missing_or_malformed_metadata(app_metadata: bytes | None) -> None:
    transport = _make_transport()
    transport._client.list_flights.return_value = [_make_flight_info(app_metadata)]

    result = transport.list_resources(ResourceQuery(action="studies.list"))

    assert result.trace_id is None


def test_get_ticket_reads_trace_id_from_schema_metadata() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())], metadata={b"trace_id": b"trace-get-1"})
    reader.read_chunk.side_effect = StopIteration
    transport._client.do_get.return_value = reader

    result = transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert result.trace_id == "trace-get-1"


def test_get_ticket_returns_no_trace_id_when_schema_metadata_is_absent() -> None:
    transport = _make_transport()
    reader = MagicMock()
    reader.schema = pa.schema([("id", pa.int64())])
    reader.read_chunk.side_effect = StopIteration
    transport._client.do_get.return_value = reader

    result = transport.get_ticket(DatasetTicket(dataset_uuid="dataset-1"))

    assert result.trace_id is None
