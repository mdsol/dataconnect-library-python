"""Resource → domain model mappers.

Each function takes a transport-layer ``ResourceInfo`` and returns a public
domain model.  All wire-format knowledge (JSON encoding, field names, byte
decoding) is isolated here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

import pandas as pd
import pyarrow as pa

from dataconnect.exceptions import NotFoundError
from dataconnect.models import Dataset, DatasetVersion, DryPublishResult, PublishResult, Study, StudyEnvironment
from dataconnect.transport.models import DataTable, DryPublishResponse, PublishResponse, ResourceInfo


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
        return reader.read_all().to_pandas()


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
    )


def dry_publish_response_to_domain(result: DryPublishResponse | None) -> DryPublishResult:
    """Map a transport-layer ``DryPublishResponse`` to a ``DryPublishResult`` domain object.

    ``DryPublishResponse`` carries flat, typed fields returned by the server after a
    dry-publish call.  The mapping is direct for all shared fields with one
    exception:

    * ``DryPublishResponse.dataset_valid`` → ``DryPublishResult.is_dataset_valid``
      (renamed for naming consistency with the other ``is_*_valid`` fields).

    Args:
        result: The transport-layer result returned by
            :meth:`Transport.dry_publish_dataset`.  Pass ``None`` to obtain a
            default :class:`DryPublishResult` with ``status=False`` and all
            other fields at their zero values.

    Returns:
        A :class:`DryPublishResult` suitable for returning to the caller.
    """
    if result is None:
        return DryPublishResult(status=False)

    return DryPublishResult(
        status=result.status,
        is_schema_valid=result.is_schema_valid,
        is_config_valid=result.is_config_valid,
        is_dataset_valid=result.dataset_valid,
        errors=result.errors,
        invalid_datetime_formats=result.invalid_datetime_formats,
        dataset_name=result.dataset_name,
        dataset_version=result.dataset_version,
        no_of_columns=result.no_of_columns,
        valid_record_count=result.valid_record_count,
        duplicate_record_count=result.duplicate_record_count,
        invalid_record_count=result.invalid_record_count,
        invalid_records=result.invalid_records,
    )


def publish_response_to_domain(result: PublishResponse | None) -> PublishResult:
    """Map a transport-layer ``PublishResponse`` to a ``PublishResult`` domain object.

    ``PublishResponse`` carries flat, typed fields returned by the server after a
    publish call.  The mapping is direct for all shared fields with one
    exception:

    Args:
        result: The transport-layer result returned by
            :meth:`Transport.publish_dataset`.  Pass ``None`` to obtain a
            default :class:`PublishResult` with ``status=False`` and all
            other fields at their zero values.

    Returns:
        A :class:`PublishResult` suitable for returning to the caller.
    """
    if result is None:
        return PublishResult(status=False)

    return PublishResult(
        status=result.status,
        dataset_name=result.dataset_name,
        dataset_uuid=result.dataset_uuid,
        dataset_version=result.dataset_version,
        dataset_batch_number=result.dataset_batch_number,
        valid_record_count=result.valid_record_count,
        duplicate_record_count=result.duplicate_record_count,
        invalid_record_count=result.invalid_record_count,
        invalid_records=result.invalid_records,
    )
