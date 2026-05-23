"""Unit tests for the dry-publish feature.

Covers:
- ``_normalize_arrow_type``          (transport helper)
- ``dry_publish_response_to_domain``           (service mapper)
- ``DefaultDataConnectService.dry_publish``  (service layer)
- ``ArrowFlightTransport.dry_publish_dataset`` (transport layer)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import UUID

import pandas as pd
import pyarrow as pa
import pytest

from dataconnect.exceptions import ValidationError
from dataconnect.models import DryPublishResult
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.service.mappers import dry_publish_response_to_domain
from dataconnect.transport.arrow_flight.transport import (
    ArrowFlightTransport,
    _normalize_arrow_type,
)
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import TransportValidationError
from dataconnect.transport.models import (
    DatasetTicket,
    DataTable,
    DryPublishResponse,
    PublishRequest,
    ResourceInfo,
    ResourceQuery,
)

# ---------------------------------------------------------------------------
# Helpers shared across test suites
# ---------------------------------------------------------------------------


def _make_dry_publish_response(**overrides: object) -> DryPublishResponse:
    """Return a fully-populated ``DryPublishResponse`` with sensible defaults."""
    defaults: dict = dict(
        status=True,
        is_schema_valid=True,
        is_config_valid=True,
        dataset_valid=True,
        errors=[],
        invalid_datetime_formats={},
        dataset_name="demo_dataset",
        dataset_version=1,
        no_of_columns=5,
        valid_record_count=10,
        duplicate_record_count=0,
        invalid_record_count=0,
        invalid_records=None,
    )
    return DryPublishResponse(**{**defaults, **overrides})


def _make_json_buf(d: dict) -> pa.Buffer:
    return pa.py_buffer(json.dumps(d).encode("utf-8"))


def _make_ipc_buf(df: pd.DataFrame) -> pa.Buffer:
    table = pa.Table.from_pandas(df)
    sink = pa.BufferOutputStream()
    w = pa.ipc.new_stream(sink, table.schema)
    w.write_table(table)
    w.close()
    return pa.py_buffer(sink.getvalue().to_pybytes())


# ---------------------------------------------------------------------------
# _normalize_arrow_type
# ---------------------------------------------------------------------------


class TestNormalizeArrowType:
    """``_normalize_arrow_type`` must downcast the three widened types and leave
    everything else unchanged."""

    def test_large_utf8_becomes_utf8(self) -> None:
        assert _normalize_arrow_type(pa.large_utf8()) == pa.utf8()

    def test_large_binary_becomes_binary(self) -> None:
        assert _normalize_arrow_type(pa.large_binary()) == pa.binary()

    def test_large_list_of_large_string_becomes_list_of_string(self) -> None:
        result = _normalize_arrow_type(pa.large_list(pa.large_utf8()))
        assert result == pa.list_(pa.utf8())

    def test_large_list_recursive_normalization_with_large_binary(self) -> None:
        result = _normalize_arrow_type(pa.large_list(pa.large_binary()))
        assert result == pa.list_(pa.binary())

    def test_regular_utf8_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.utf8()) == pa.utf8()

    def test_regular_binary_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.binary()) == pa.binary()

    def test_regular_list_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.list_(pa.utf8())) == pa.list_(pa.utf8())

    def test_int64_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.int64()) == pa.int64()

    def test_float64_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.float64()) == pa.float64()

    def test_timestamp_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.timestamp("us")) == pa.timestamp("us")

    def test_bool_passes_through(self) -> None:
        assert _normalize_arrow_type(pa.bool_()) == pa.bool_()


# ---------------------------------------------------------------------------
# dry_publish_response_to_domain
# ---------------------------------------------------------------------------


class TestDryPublishResponseToDomain:
    """Every field of ``DryPublishResponse`` must land on the correct attribute
    of ``DryPublishResult``, including the ``dataset_valid`` rename."""

    def test_status_true_is_mapped(self) -> None:
        assert dry_publish_response_to_domain(_make_dry_publish_response(status=True)).status is True

    def test_status_false_is_mapped(self) -> None:
        assert dry_publish_response_to_domain(_make_dry_publish_response(status=False)).status is False

    def test_is_schema_valid_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(is_schema_valid=False))
        assert result.is_schema_valid is False

    def test_is_config_valid_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(is_config_valid=False))
        assert result.is_config_valid is False

    def test_dataset_valid_renamed_to_is_dataset_valid(self) -> None:
        # Transport field name:  dataset_valid
        # Domain field name:     is_dataset_valid
        result = dry_publish_response_to_domain(_make_dry_publish_response(dataset_valid=False))
        assert result.is_dataset_valid is False

    def test_errors_list_mapped(self) -> None:
        errors = ["Missing column X", "Type mismatch on Y"]
        result = dry_publish_response_to_domain(_make_dry_publish_response(errors=errors))
        assert result.errors == errors

    def test_empty_errors_list_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(errors=[]))
        assert result.errors == []

    def test_invalid_datetime_formats_mapped(self) -> None:
        fmt = {"visit_date": "yyyy-MM-dd"}
        result = dry_publish_response_to_domain(_make_dry_publish_response(invalid_datetime_formats=fmt))
        assert result.invalid_datetime_formats == fmt

    def test_dataset_name_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(dataset_name="my_ds"))
        assert result.dataset_name == "my_ds"

    def test_dataset_version_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(dataset_version=42))
        assert result.dataset_version == 42

    def test_no_of_columns_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(no_of_columns=7))
        assert result.no_of_columns == 7

    def test_valid_record_count_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(valid_record_count=100))
        assert result.valid_record_count == 100

    def test_duplicate_record_count_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(duplicate_record_count=3))
        assert result.duplicate_record_count == 3

    def test_invalid_record_count_mapped(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(invalid_record_count=2))
        assert result.invalid_record_count == 2

    def test_invalid_records_none_preserved(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response(invalid_records=None))
        assert result.invalid_records is None

    def test_invalid_records_dataframe_preserved(self) -> None:
        df = pd.DataFrame({"col": [1, 2, 3]})
        result = dry_publish_response_to_domain(_make_dry_publish_response(invalid_records=df))
        assert result.invalid_records is df

    def test_returns_dry_publish_result_instance(self) -> None:
        result = dry_publish_response_to_domain(_make_dry_publish_response())
        assert isinstance(result, DryPublishResult)


# ---------------------------------------------------------------------------
# DefaultDataConnectService.dry_publish
# ---------------------------------------------------------------------------


class _StubTransport(Transport):
    """Minimal stub that satisfies the Transport ABC for dry-publish tests."""

    def __init__(
        self,
        dry_publish_return: DryPublishResponse | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._return = dry_publish_return
        self._raise = raise_error
        self.last_request: PublishRequest | None = None

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        return []

    def get_ticket(self, ticket: DatasetTicket) -> DataTable:
        raise NotImplementedError

    def dry_publish_dataset(self, request: PublishRequest) -> DryPublishResponse:
        self.last_request = request
        if self._raise is not None:
            raise self._raise
        return self._return  # type: ignore[return-value]

    def close(self) -> None:
        pass


def _make_service(
    dry_publish_return: DryPublishResponse | None = None,
    raise_error: Exception | None = None,
) -> tuple[DefaultDataConnectService, _StubTransport]:
    transport = _StubTransport(dry_publish_return=dry_publish_return, raise_error=raise_error)
    return DefaultDataConnectService(transport), transport


def _default_dry_publish_args() -> dict:
    return dict(
        project_token="tok_abc123",
        dataset_name="my_dataset",
        key_columns=["site_id"],
        source_datasets=[UUID("0158ea12-4004-3817-899b-2de6becbc0f9")],
        data=pd.DataFrame({"site_id": ["S1"], "value": [1]}),
    )


class TestDryPublishService:
    """``DefaultDataConnectService.dry_publish`` must build the correct request,
    delegate to the transport, map the response, and translate errors."""

    def test_returns_dry_publish_result_instance(self) -> None:
        service, _ = _make_service(dry_publish_return=_make_dry_publish_response())
        result = service.dry_publish(**_default_dry_publish_args())
        assert isinstance(result, DryPublishResult)

    def test_successful_status_is_propagated(self) -> None:
        service, _ = _make_service(dry_publish_return=_make_dry_publish_response(status=True))
        assert service.dry_publish(**_default_dry_publish_args()).status is True

    # --- input_config JSON content ---

    def test_input_config_sets_is_dry_publish_true(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        service.dry_publish(**_default_dry_publish_args())
        assert transport.last_request is not None
        config = json.loads(transport.last_request.input_config)
        assert config["is_dry_publish"] is True

    def test_input_config_contains_project_token(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        service.dry_publish(**_default_dry_publish_args())
        assert transport.last_request is not None
        assert json.loads(transport.last_request.input_config)["project_token"] == "tok_abc123"

    def test_input_config_contains_dataset_name(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        service.dry_publish(**_default_dry_publish_args())
        assert transport.last_request is not None
        assert json.loads(transport.last_request.input_config)["dataset_name"] == "my_dataset"

    def test_input_config_contains_key_columns(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        service.dry_publish(**_default_dry_publish_args())
        assert transport.last_request is not None
        assert json.loads(transport.last_request.input_config)["key_columns"] == ["site_id"]

    def test_input_config_source_datasets_serialized_as_strings(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        service.dry_publish(**_default_dry_publish_args())
        assert transport.last_request is not None
        config = json.loads(transport.last_request.input_config)
        assert config["source_datasets"] == ["0158ea12-4004-3817-899b-2de6becbc0f9"]

    def test_datetime_formats_defaults_to_empty_dict(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        service.dry_publish(**_default_dry_publish_args())  # no datetime_formats kwarg
        assert transport.last_request is not None
        assert json.loads(transport.last_request.input_config)["datetime_formats"] == {}

    def test_datetime_formats_passed_through_when_provided(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        args = _default_dry_publish_args()
        args["datetime_formats"] = {"visit_date": "yyyy-MM-dd"}
        service.dry_publish(**args)
        assert transport.last_request is not None
        assert json.loads(transport.last_request.input_config)["datetime_formats"] == {"visit_date": "yyyy-MM-dd"}

    def test_data_dataframe_passed_to_transport(self) -> None:
        service, transport = _make_service(dry_publish_return=_make_dry_publish_response())
        df = pd.DataFrame({"a": [1, 2, 3]})
        args = _default_dry_publish_args()
        args["data"] = df
        service.dry_publish(**args)
        assert transport.last_request is not None
        assert transport.last_request.data is df

    # --- falsy / None result ---

    def test_none_transport_result_returns_status_false(self) -> None:
        service, _ = _make_service(dry_publish_return=None)
        result = service.dry_publish(**_default_dry_publish_args())
        assert isinstance(result, DryPublishResult)
        assert result.status is False

    # --- error translation ---

    def test_transport_validation_error_is_translated_to_service_error(self) -> None:
        err = TransportValidationError(
            error_code="VAL_001",
            message="schema mismatch",
            timestamp="2024-01-01T00:00:00Z",
        )
        service, _ = _make_service(raise_error=err)
        with pytest.raises(ValidationError):
            service.dry_publish(**_default_dry_publish_args())


# ---------------------------------------------------------------------------
# ArrowFlightTransport.dry_publish_dataset
# ---------------------------------------------------------------------------


def _make_flight_transport() -> ArrowFlightTransport:
    """Create an ``ArrowFlightTransport`` with a mocked ``FlightClient``."""
    with patch.object(ArrowFlightTransport, "_get_client", return_value=MagicMock()):
        return ArrowFlightTransport(host="localhost", port=5005, use_tls=False)


def _wire_do_put(
    transport: ArrowFlightTransport,
    json_resp: dict,
    invalid_records_df: pd.DataFrame | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Configure ``transport._client.do_put`` to return controlled writer/reader mocks."""
    json_buf = _make_json_buf(json_resp)
    ipc_buf = _make_ipc_buf(invalid_records_df) if invalid_records_df is not None else None

    reader_mock = MagicMock()
    reader_mock.read.side_effect = [json_buf, ipc_buf]
    writer_mock = MagicMock()
    transport._client.do_put.return_value = (writer_mock, reader_mock)
    return writer_mock, reader_mock


# A minimal valid JSON response the server would return.
_VALID_JSON_RESP: dict = {
    "status": True,
    "is_schema_valid": True,
    "is_config_valid": True,
    "dataset_valid": True,
    "errors": [],
    "invalid_datetime_formats": {},
    "dataset_name": "ds",
    "dataset_version": 1,
    "no_of_columns": 1,
    "valid_record_count": 1,
    "duplicate_record_count": 0,
    "invalid_record_count": 0,
}


class TestDryPublishDatasetTransport:
    """``ArrowFlightTransport.dry_publish_dataset`` must normalise the Arrow schema,
    manage the writer lifecycle correctly, and build ``DryPublishResponse`` from
    the server's two-phase metadata response."""

    # --- schema normalisation ---

    def test_large_string_columns_cast_to_string_before_send(self) -> None:
        transport = _make_flight_transport()
        _wire_do_put(transport, _VALID_JSON_RESP)

        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        transport.dry_publish_dataset(PublishRequest(input_config="{}", data=df))

        sent_schema = transport._client.do_put.call_args[0][1]
        assert sent_schema.field("name").type == pa.utf8(), "large_string should have been normalised to string"

    def test_integer_and_float_columns_not_affected_by_normalisation(self) -> None:
        transport = _make_flight_transport()
        _wire_do_put(transport, _VALID_JSON_RESP)

        df = pd.DataFrame({"count": [1, 2], "score": [1.1, 2.2]})
        transport.dry_publish_dataset(PublishRequest(input_config="{}", data=df))

        sent_schema = transport._client.do_put.call_args[0][1]
        assert pa.types.is_integer(sent_schema.field("count").type)
        assert pa.types.is_floating(sent_schema.field("score").type)

    # --- writer lifecycle ---

    def test_done_writing_is_called_once_on_success(self) -> None:
        transport = _make_flight_transport()
        writer_mock, _ = _wire_do_put(transport, _VALID_JSON_RESP)

        transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        writer_mock.done_writing.assert_called_once()

    def test_close_is_called_once_on_success(self) -> None:
        transport = _make_flight_transport()
        writer_mock, _ = _wire_do_put(transport, _VALID_JSON_RESP)

        transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        writer_mock.close.assert_called_once()

    def test_done_writing_precedes_close(self) -> None:
        transport = _make_flight_transport()
        writer_mock, _ = _wire_do_put(transport, _VALID_JSON_RESP)

        transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        method_names = [str(c) for c in writer_mock.method_calls]
        done_idx = next(i for i, n in enumerate(method_names) if "done_writing" in n)
        close_idx = next(i for i, n in enumerate(method_names) if "close" in n)
        assert done_idx < close_idx, "done_writing() must be called before close()"

    def test_close_called_even_when_write_batch_raises(self) -> None:
        transport = _make_flight_transport()
        writer_mock = MagicMock()
        writer_mock.write_batch.side_effect = RuntimeError("network error")
        reader_mock = MagicMock()
        transport._client.do_put.return_value = (writer_mock, reader_mock)

        from dataconnect.transport.errors import TransportError

        with pytest.raises(TransportError):
            transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))

        writer_mock.close.assert_called_once()

    def test_done_writing_not_called_when_write_batch_raises(self) -> None:
        transport = _make_flight_transport()
        writer_mock = MagicMock()
        writer_mock.write_batch.side_effect = RuntimeError("network error")
        transport._client.do_put.return_value = (writer_mock, MagicMock())

        from dataconnect.transport.errors import TransportError

        with pytest.raises(TransportError):
            transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))

        writer_mock.done_writing.assert_not_called()

    # --- response parsing ---

    def test_returns_dry_publish_response_instance(self) -> None:
        transport = _make_flight_transport()
        _wire_do_put(transport, _VALID_JSON_RESP)

        result = transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        assert isinstance(result, DryPublishResponse)

    def test_status_parsed_from_json(self) -> None:
        transport = _make_flight_transport()
        _wire_do_put(transport, {**_VALID_JSON_RESP, "status": False})

        result = transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        assert result.status is False

    def test_errors_list_parsed_from_json(self) -> None:
        transport = _make_flight_transport()
        _wire_do_put(transport, {**_VALID_JSON_RESP, "errors": ["err1", "err2"]})

        result = transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        assert result.errors == ["err1", "err2"]

    def test_none_ipc_buf_yields_no_invalid_records(self) -> None:
        transport = _make_flight_transport()
        # Second reader.read() returns None — server sent no invalid-records table
        json_buf = _make_json_buf(_VALID_JSON_RESP)
        reader_mock = MagicMock()
        reader_mock.read.side_effect = [json_buf, None]
        writer_mock = MagicMock()
        transport._client.do_put.return_value = (writer_mock, reader_mock)

        result = transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        assert result.invalid_records is None

    def test_ipc_buf_is_decoded_to_dataframe(self) -> None:
        transport = _make_flight_transport()
        invalid_df = pd.DataFrame({"row_id": [10, 20], "reason": ["bad type", "null value"]})
        _wire_do_put(transport, _VALID_JSON_RESP, invalid_records_df=invalid_df)

        result = transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"x": [1]})))
        assert result.invalid_records is not None
        assert list(result.invalid_records.columns) == ["row_id", "reason"]
        assert len(result.invalid_records) == 2
