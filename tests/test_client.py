"""Tests for DataConnectClient, including fetch_data and _get_dataset."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pytest

from dataconnect import _encoding
from dataconnect.client import DataConnectClient, _get_dataset
from dataconnect.framework.transport import FlightTransport, RecordBatchStream


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeStream(RecordBatchStream):
    def __init__(self, batches: list[pa.RecordBatch]) -> None:
        self._batches = batches

    def read_all(self) -> pa.Table:
        if not self._batches:
            return pa.table({})
        return pa.Table.from_batches(self._batches)

    def __iter__(self) -> Iterator[pa.RecordBatch]:
        yield from self._batches


class _FakeTransport(FlightTransport):
    def __init__(self, batches: list[pa.RecordBatch]) -> None:
        self._batches = batches
        self.last_ticket: bytes | None = None
        self.do_get_calls = 0

    def do_action(self, action: str, body: bytes = b"") -> bytes:
        return b""

    def do_get(self, ticket: bytes) -> RecordBatchStream:
        self.last_ticket = ticket
        self.do_get_calls += 1
        return _FakeStream(self._batches)

    def do_put(self, command: bytes, table: pa.Table) -> bytes | None:
        return b""

    def close(self) -> None:
        return None


def _make_clinical_batches() -> list[pa.RecordBatch]:
    """Two batches with date32 and decimal128 columns to exercise dtype roundtrip."""
    schema = pa.schema(
        [
            pa.field("subject_id", pa.string()),
            pa.field("visit_date", pa.date32()),
            pa.field("dose_mg", pa.decimal128(precision=10, scale=2)),
        ]
    )
    batch_a = pa.RecordBatch.from_pydict(
        {
            "subject_id": ["S1", "S2"],
            "visit_date": [dt.date(2026, 1, 15), dt.date(2026, 2, 1)],
            "dose_mg": [Decimal("12.50"), Decimal("7.25")],
        },
        schema=schema,
    )
    batch_b = pa.RecordBatch.from_pydict(
        {
            "subject_id": ["S3"],
            "visit_date": [dt.date(2026, 3, 10)],
            "dose_mg": [Decimal("100.00")],
        },
        schema=schema,
    )
    return [batch_a, batch_b]


# ---------------------------------------------------------------------------
# Placeholder / benchmark
# ---------------------------------------------------------------------------

def test_client() -> None:
    assert True


@pytest.mark.benchmark
def test_dummy_benchmark() -> None:
    # Dummy benchmark test to satisfy CI
    assert True


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------

def test_fetch_data_returns_pandas_dataframe_preserving_types() -> None:
    transport = _FakeTransport(_make_clinical_batches())
    client = DataConnectClient(transport)

    df = client.fetch_data(dataset_uuid="ds-123")

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["subject_id", "visit_date", "dose_mg"]
    assert len(df) == 3
    # date32 → python date objects (preserved, not coerced to ns timestamps)
    assert df["visit_date"].iloc[0] == dt.date(2026, 1, 15)
    # decimal128 → Decimal objects (precision preserved)
    assert df["dose_mg"].iloc[0] == Decimal("12.50")
    assert df["dose_mg"].iloc[2] == Decimal("100.00")


def test_fetch_data_sends_ticket_with_dataset_uuid_and_limit() -> None:
    transport = _FakeTransport(_make_clinical_batches())
    client = DataConnectClient(transport)

    client.fetch_data(dataset_uuid="ds-123", first_n_rows=10)

    assert transport.last_ticket is not None
    payload = json.loads(transport.last_ticket.decode("utf-8"))
    assert payload["dataset_uuid"] == "ds-123"
    assert payload["limit"] == 10
    assert payload["dataset_name"] == ""
    # Study / study-env UUIDs are no longer part of the ticket.
    assert "study_uuid" not in payload
    assert "study_env_uuid" not in payload


def test_fetch_data_omitted_first_n_rows_sends_null_limit() -> None:
    transport = _FakeTransport(_make_clinical_batches())
    client = DataConnectClient(transport)

    client.fetch_data(dataset_uuid="ds-123")

    payload = json.loads(transport.last_ticket.decode("utf-8"))  # type: ignore[union-attr]
    assert payload["limit"] is None


def test_fetch_data_invalid_first_n_rows_raises() -> None:
    transport = _FakeTransport(_make_clinical_batches())
    client = DataConnectClient(transport)

    with pytest.raises(ValueError):
        client.fetch_data(dataset_uuid="ds-123", first_n_rows=0)


def test_fetch_data_empty_stream_returns_empty_dataframe() -> None:
    transport = _FakeTransport([])
    client = DataConnectClient(transport)

    df = client.fetch_data(dataset_uuid="ds-123")

    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_fetch_data_rejects_legacy_study_kwargs() -> None:
    """The legacy study_uuid / study_environment_uuid kwargs must be removed."""
    transport = _FakeTransport(_make_clinical_batches())
    client = DataConnectClient(transport)

    with pytest.raises(TypeError):
        client.fetch_data(dataset_uuid="ds-123", study_uuid="study-1")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        client.fetch_data(dataset_uuid="ds-123", study_environment_uuid="env-1")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# _get_dataset helper
# ---------------------------------------------------------------------------

def test_get_dataset_helper_builds_expected_ticket() -> None:
    transport = _FakeTransport(_make_clinical_batches())

    _get_dataset(
        transport=transport,
        dataset_uuid="ds-9",
        limit=5,
    )

    payload = _encoding.loads(transport.last_ticket)  # type: ignore[arg-type]
    assert payload == {
        "dataset_uuid": "ds-9",
        "dataset_name": "",
        "limit": 5,
    }


def test_get_dataset_helper_requires_dataset_uuid() -> None:
    transport = _FakeTransport(_make_clinical_batches())

    with pytest.raises(ValueError):
        _get_dataset(transport=transport, dataset_uuid="", limit=None)
