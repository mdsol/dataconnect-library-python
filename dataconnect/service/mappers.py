"""Resource → domain model mappers.

Each function takes a transport-layer ``ResourceInfo`` and returns a public
domain model.  All wire-format knowledge (JSON encoding, field names, byte
decoding) is isolated here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

import pandas as pd
import pyarrow as pa

from dataconnect.exceptions import NotFoundError
from dataconnect.models import (
    Dataset,
    DatasetVersion,
    DryPublishResult,
    PublishResult,
    ResultChecks,
    ResultMetadata,
    ResultMetrics,
    Study,
    StudyEnvironment,
)
from dataconnect.transport.models import (
    DataTable,
    DryPublishResponse,
    PublishEnvelope,
    PublishResponse,
    ResourceInfo,
)

_ResultT = TypeVar("_ResultT", DryPublishResult, PublishResult)


def resource_to_study(resource: ResourceInfo) -> Study:
    """Parse a transport-layer ``ResourceInfo`` into a ``Study`` domain object."""

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError(
            error_code="SDK_ERROR",
            message="Invalid resource: missing endpoints or ticket",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return Study(
        uuid=UUID(data["uuid"]),
        name=data["name"],
        environments=[StudyEnvironment(uuid=UUID(e["uuid"]), name=e["name"]) for e in data.get("environments", [])],
    )


def resource_to_dataset_version(resource: ResourceInfo) -> DatasetVersion:
    """Parse a transport-layer ``ResourceInfo`` into a ``DatasetVersion`` domain object."""

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError(
            error_code="SDK_ERROR",
            message="Invalid resource: missing endpoints or ticket",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return DatasetVersion(
        study_uuid=UUID(data["study_uuid"]),
        study_environment_uuid=UUID(data["study_env_uuid"]),
        dataset_uuid=UUID(data["dataset_uuid"]),
        dataset_name=data["dataset_name"],
        dataset_version=data["dataset_version"],
    )


def resource_to_fetched_data(table: DataTable) -> pd.DataFrame:
    """Convert a transport-layer ``DataTable`` into a ``pandas.DataFrame``."""

    ipc_buffer = pa.BufferReader(table.ipc_bytes)
    with pa.ipc.open_stream(ipc_buffer) as reader:
        arrow_table = reader.read_all()

    # Clear schema metadata so types_mapper reliably maps Arrow types to ArrowDtype
    # (embedded pandas metadata can override types_mapper, causing object dtypes).
    arrow_table = arrow_table.replace_schema_metadata(None)

    return arrow_table.to_pandas(types_mapper=pd.ArrowDtype)


def resource_to_dataset(resource: ResourceInfo) -> Dataset:
    """Parse a transport-layer ``ResourceInfo`` into a ``Dataset`` domain object."""

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError(
            error_code="SDK_ERROR",
            message="Invalid resource: missing endpoints or ticket",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return Dataset(
        dataset_uuid=data.get("dataset_uuid", ""),
        study_uuid=data.get("study_uuid", ""),
        study_env_uuid=data.get("study_env_uuid", ""),
        dataset_name=data.get("dataset_name", ""),
        dataset_short_name=data.get("dataset_short_name"),
        type=data.get("type"),
        source=data.get("source"),
        activation_status=data.get("activation_status"),
        dataset_status=data.get("dataset_status"),
        collection=data.get("collection"),
        last_updated=data.get("last_updated"),
        version=data.get("version"),
        other_versions=data.get("other_versions"),
    )


def _envelope_to_domain(envelope: PublishEnvelope, result_cls: type[_ResultT]) -> _ResultT:  # noqa: UP047
    """Copy a transport envelope onto its domain equivalent, section by section."""
    return result_cls(
        success=envelope.success,
        metadata=ResultMetadata(
            dataset_name=envelope.metadata.dataset_name,
            dataset_version=envelope.metadata.dataset_version,
            column_count=envelope.metadata.column_count,
            dataset_uuid=envelope.metadata.dataset_uuid,
        ),
        metrics=ResultMetrics(
            total_valid_rows=envelope.metrics.total_valid_rows,
            total_invalid_rows=envelope.metrics.total_invalid_rows,
            total_duplicate_rows=envelope.metrics.total_duplicate_rows,
        ),
        checks=ResultChecks(
            schema_is_valid=envelope.checks.schema_is_valid,
            config_is_valid=envelope.checks.config_is_valid,
            date_formats_are_valid=envelope.checks.date_formats_are_valid,
            dataset_is_valid=envelope.checks.dataset_is_valid,
            invalid_datetime_formats=envelope.checks.invalid_datetime_formats,
        ),
        errors=envelope.errors,
        invalid_records=envelope.invalid_records,
    )


def dry_publish_response_to_domain(result: DryPublishResponse | None) -> DryPublishResult:
    """Map a transport-layer dry-publish envelope to a ``DryPublishResult``.

    Args:
        result: The transport-layer result returned by
            :meth:`Transport.dry_publish_dataset`.  Pass ``None`` to obtain a
            default :class:`DryPublishResult` with ``success=False``.

    Returns:
        A :class:`DryPublishResult` suitable for returning to the caller.
    """
    if result is None:
        return DryPublishResult(success=False)

    return _envelope_to_domain(result, DryPublishResult)


def publish_response_to_domain(result: PublishResponse | None) -> PublishResult:
    """Map a transport-layer publish envelope to a ``PublishResult``.

    Args:
        result: The transport-layer result returned by
            :meth:`Transport.publish_dataset`. Pass ``None`` to obtain a
            default :class:`PublishResult` with ``success=False``.

    Returns:
        A :class:`PublishResult` suitable for returning to the caller.
    """
    if result is None:
        return PublishResult(success=False)

    return _envelope_to_domain(result, PublishResult)
