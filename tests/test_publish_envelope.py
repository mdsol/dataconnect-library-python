"""Tests for the canonical publish/dry-publish envelope on the client side.

The fixtures in ``_arrow_envelopes.py`` are captured verbatim from the Arrow
Flight server (MCC-1533427), so these tests fail if the SDK drifts from what
the server actually emits.

Covers:
- ``ResultMetadata`` / ``ResultMetrics`` / ``ResultChecks`` (domain models)
- backward-compatible flat accessors on the public results
- ``ArrowFlightTransport`` parsing of the nested envelope
- ``dry_publish_response_to_domain`` / ``publish_response_to_domain``
"""

from __future__ import annotations

import json
from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pandas as pd
import pyarrow as pa
import pytest

from dataconnect.models import DryPublishResult, PublishResult
from dataconnect.service.mappers import dry_publish_response_to_domain, publish_response_to_domain
from dataconnect.transport.arrow_flight.transport import ArrowFlightTransport
from dataconnect.transport.models import PublishRequest
from tests._arrow_envelopes import FAILED_DRY_PUBLISH_ENVELOPE, PASSED_DRY_PUBLISH_ENVELOPE, PUBLISH_ENVELOPE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flight_transport() -> ArrowFlightTransport:
    with patch.object(ArrowFlightTransport, "_get_client", return_value=MagicMock()):
        return ArrowFlightTransport(host="localhost", port=5005, use_tls=False)


def _make_ipc_buf(df: pd.DataFrame) -> pa.Buffer:
    table = pa.Table.from_pandas(df)
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, table.schema)
    writer.write_table(table)
    writer.close()
    return pa.py_buffer(sink.getvalue().to_pybytes())


def _wire_do_put(
    transport: ArrowFlightTransport,
    envelope: dict,
    invalid_records_df: pd.DataFrame | None = None,
) -> None:
    json_buf = pa.py_buffer(json.dumps(envelope).encode("utf-8"))
    ipc_buf = _make_ipc_buf(invalid_records_df) if invalid_records_df is not None else None

    reader_mock = MagicMock()
    reader_mock.read.side_effect = [json_buf, ipc_buf]
    transport._client.do_put.return_value = (MagicMock(), reader_mock)


def _dry_publish_over_wire(envelope: dict, invalid_records_df: pd.DataFrame | None = None) -> DryPublishResult:
    """Drive the full client stack: server bytes -> transport -> domain."""
    transport = _make_flight_transport()
    _wire_do_put(transport, envelope, invalid_records_df)
    response = transport.dry_publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"a": [1]})))
    return dry_publish_response_to_domain(response)


def _publish_over_wire(envelope: dict, invalid_records_df: pd.DataFrame | None = None) -> PublishResult:
    transport = _make_flight_transport()
    _wire_do_put(transport, envelope, invalid_records_df)
    response = transport.publish_dataset(PublishRequest(input_config="{}", data=pd.DataFrame({"a": [1]})))
    return publish_response_to_domain(response)


# ---------------------------------------------------------------------------
# Domain model shape
# ---------------------------------------------------------------------------


class TestEnvelopeShapeOnDomainModels:
    """Both public results expose the canonical envelope sections."""

    @pytest.mark.parametrize("result_cls", [DryPublishResult, PublishResult])
    def test_exposes_canonical_sections(self, result_cls: type) -> None:
        result = result_cls(success=True)

        assert result.success is True
        assert result.metadata is not None
        assert result.metrics is not None
        assert result.checks is not None
        assert result.errors == []
        assert result.invalid_records is None

    @pytest.mark.parametrize("result_cls", [DryPublishResult, PublishResult])
    def test_metrics_default_to_zero(self, result_cls: type) -> None:
        metrics = result_cls(success=False).metrics

        assert metrics.total_valid_rows == 0
        assert metrics.total_invalid_rows == 0
        assert metrics.total_duplicate_rows == 0

    @pytest.mark.parametrize("result_cls", [DryPublishResult, PublishResult])
    def test_checks_default_to_false(self, result_cls: type) -> None:
        checks = result_cls(success=False).checks

        assert checks.schema_is_valid is False
        assert checks.config_is_valid is False
        assert checks.date_formats_are_valid is False
        assert checks.dataset_is_valid is False
        assert checks.invalid_datetime_formats == {}


# ---------------------------------------------------------------------------
# Backward compatibility — the notebooks must keep working
# ---------------------------------------------------------------------------


class TestFlatAccessorsStillWork:
    """Existing notebooks read flat attributes; they must survive the reshape."""

    def test_dry_publish_flat_accessors(self) -> None:
        result = _dry_publish_over_wire(FAILED_DRY_PUBLISH_ENVELOPE)

        assert result.status is False
        assert result.is_schema_valid is True
        assert result.is_config_valid is True
        assert result.is_dataset_valid is True
        assert result.dataset_name == "PP_0726_1"
        assert result.dataset_version == 0
        assert result.no_of_columns == 13
        assert result.valid_record_count == 36042
        assert result.invalid_record_count == 4
        assert result.duplicate_record_count == 2
        assert result.invalid_datetime_formats == {"lbdat_int": "yyyy-MM-dd"}

    def test_publish_flat_accessors(self) -> None:
        result = _publish_over_wire(PUBLISH_ENVELOPE)

        assert result.status is True
        assert result.dataset_name == "PP_0726_1"
        assert result.dataset_uuid == "6f5a4e1c-0000-4a2b-9d3e-2f1c8b7a6d55"
        assert result.dataset_version == 1
        assert result.dataset_batch_number == 1
        assert result.valid_record_count == 36042
        assert result.invalid_record_count == 0
        assert result.duplicate_record_count == 0

    @pytest.mark.parametrize(
        ("flat_attr", "nested_path"),
        [
            ("status", ("success",)),
            ("dataset_name", ("metadata", "dataset_name")),
            ("dataset_version", ("metadata", "dataset_version")),
            ("no_of_columns", ("metadata", "column_count")),
            ("valid_record_count", ("metrics", "total_valid_rows")),
            ("invalid_record_count", ("metrics", "total_invalid_rows")),
            ("duplicate_record_count", ("metrics", "total_duplicate_rows")),
            ("is_schema_valid", ("checks", "schema_is_valid")),
            ("is_config_valid", ("checks", "config_is_valid")),
            ("is_dataset_valid", ("checks", "dataset_is_valid")),
        ],
    )
    def test_flat_accessor_is_a_view_onto_the_envelope(self, flat_attr: str, nested_path: tuple[str, ...]) -> None:
        """No duplicated state: each flat name reads through to one envelope field."""
        result = _dry_publish_over_wire(FAILED_DRY_PUBLISH_ENVELOPE)

        nested_value = result
        for part in nested_path:
            nested_value = getattr(nested_value, part)

        assert getattr(result, flat_attr) == nested_value


# ---------------------------------------------------------------------------
# Transport parsing against real server output
# ---------------------------------------------------------------------------


class TestTransportParsesArrowEnvelope:
    """The SDK must read exactly what the Arrow Flight server emits."""

    def test_failed_dry_publish(self) -> None:
        result = _dry_publish_over_wire(FAILED_DRY_PUBLISH_ENVELOPE)

        assert result.success is False
        assert result.checks.date_formats_are_valid is False
        assert result.checks.invalid_datetime_formats == {"lbdat_int": "yyyy-MM-dd"}
        assert result.errors == ["Missing datetime formats for date/timestamp columns: lbdat_int"]

    def test_passed_dry_publish(self) -> None:
        result = _dry_publish_over_wire(PASSED_DRY_PUBLISH_ENVELOPE)

        assert result.success is True
        assert result.errors == []
        assert result.metrics.total_valid_rows == 36042
        assert result.metadata.column_count == 13

    def test_publish(self) -> None:
        result = _publish_over_wire(PUBLISH_ENVELOPE)

        assert result.success is True
        assert result.metadata.dataset_uuid == "6f5a4e1c-0000-4a2b-9d3e-2f1c8b7a6d55"
        assert result.metadata.dataset_batch_number == 1
        assert result.checks.schema_is_valid is True

    def test_dry_publish_and_publish_read_the_same_sections(self) -> None:
        """One envelope, one parser: both operations populate the same structure."""
        dry = _dry_publish_over_wire(PASSED_DRY_PUBLISH_ENVELOPE)
        live = _publish_over_wire(PUBLISH_ENVELOPE)

        for section in ("metadata", "metrics", "checks"):
            assert vars(getattr(dry, section)).keys() == vars(getattr(live, section)).keys()


# ---------------------------------------------------------------------------
# invalid_records arrives on the Arrow IPC channel, not in the JSON
# ---------------------------------------------------------------------------


class TestInvalidRecordsMaterialisation:
    def test_ipc_rows_land_on_invalid_records(self) -> None:
        rows = pd.DataFrame({"row_index": [0, 1], "error_type": ["invalid_datetime_format"] * 2})

        result = _dry_publish_over_wire(FAILED_DRY_PUBLISH_ENVELOPE, invalid_records_df=rows)

        assert result.invalid_records is not None
        assert len(result.invalid_records) == 2
        assert list(result.invalid_records["error_type"]) == ["invalid_datetime_format"] * 2

    def test_empty_json_placeholder_is_not_used_as_the_value(self) -> None:
        """The server sends invalid_records: [] in JSON; rows come over IPC."""
        assert FAILED_DRY_PUBLISH_ENVELOPE["invalid_records"] == []

        result = _dry_publish_over_wire(FAILED_DRY_PUBLISH_ENVELOPE)

        assert result.invalid_records is None

    def test_publish_ipc_rows_land_on_invalid_records(self) -> None:
        rows = pd.DataFrame({"row_index": [7]})

        result = _publish_over_wire(PUBLISH_ENVELOPE, invalid_records_df=rows)

        assert result.invalid_records is not None
        assert len(result.invalid_records) == 1


# ---------------------------------------------------------------------------
# Missing / partial payloads must not explode
# ---------------------------------------------------------------------------


class TestDefensiveParsing:
    def test_empty_envelope_yields_defaults(self) -> None:
        result = _dry_publish_over_wire({})

        assert result.success is False
        assert result.metrics.total_valid_rows == 0
        assert result.checks.schema_is_valid is False
        assert result.metadata.dataset_name is None

    def test_missing_sections_yield_defaults(self) -> None:
        result = _publish_over_wire({"success": True})

        assert result.success is True
        assert result.metadata.dataset_uuid is None
        assert result.metrics.total_duplicate_rows == 0

    def test_none_transport_response_maps_to_failure(self) -> None:
        assert dry_publish_response_to_domain(None).success is False
        assert publish_response_to_domain(None).success is False


class TestBatchNumberIsHiddenFromOutput:
    @pytest.mark.parametrize(
        ("envelope", "over_wire"),
        [
            (FAILED_DRY_PUBLISH_ENVELOPE, _dry_publish_over_wire),
            (PASSED_DRY_PUBLISH_ENVELOPE, _dry_publish_over_wire),
            (PUBLISH_ENVELOPE, _publish_over_wire),
        ],
        ids=["dry_publish_failure", "dry_publish_success", "publish"],
    )
    def test_batch_number_absent_from_printed_output(
        self, envelope: dict, over_wire: Callable[[dict], DryPublishResult | PublishResult]
    ) -> None:
        result = over_wire(envelope)

        assert "dataset_batch_number" not in repr(result)
        assert "dataset_batch_number" not in repr(result.metadata)

    def test_publish_batch_number_is_still_readable(self) -> None:
        result = _publish_over_wire(PUBLISH_ENVELOPE)

        assert result.metadata.dataset_batch_number == 1
        assert result.dataset_batch_number == 1

    def test_other_metadata_still_printed(self) -> None:
        printed = repr(_publish_over_wire(PUBLISH_ENVELOPE).metadata)

        for field_name in ("dataset_name", "dataset_version", "column_count", "dataset_uuid"):
            assert field_name in printed
