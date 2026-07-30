"""Transport-layer DTOs — technology-agnostic contract."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ResourceQuery:
    """An outbound request to query available resources."""

    action: str
    body: str = field(default="")

    def append_body(self, extra: dict[str, Any]) -> ResourceQuery:
        """Return a new ResourceQuery with extra fields merged into the JSON body."""

        body_dict = json.loads(self.body) if self.body else {}
        merged_body = {**body_dict, **extra}

        return ResourceQuery(action=self.action, body=json.dumps(merged_body, separators=(",", ":")))


@dataclass(frozen=True)
class DataRef:
    """An opaque server-side reference to a data stream."""

    ticket: bytes


@dataclass(frozen=True)
class DatasetTicket:
    """A data ticket for a specific dataset, containing all information needed to fetch the data."""

    dataset_uuid: str
    limit: int | None = None
    study_env_uuid: str | None = None
    dataset_name: str | None = None
    dataset_version: str | None = None


@dataclass(frozen=True)
class ResourceInfo:
    """Technology-agnostic representation of a single resource."""

    descriptor: bytes
    endpoints: list[DataRef]
    total_records: int
    schema_bytes: bytes


@dataclass(frozen=True)
class DataTable:
    """Technology-agnostic representation of a fetched data result.

    ``schema_bytes`` holds the Arrow IPC-serialized schema.
    ``ipc_bytes`` holds the full Arrow IPC stream (schema + all batches).
    """

    schema_bytes: bytes
    ipc_bytes: bytes


@dataclass(frozen=True)
class DatetimeFormatsRequest:
    """An outbound request to fetch the supported datetime formats.

    Attributes:
        project_token: Base64-encoded project token used by the server to
            authorize the request.
        format_type: Filter applied server-side. One of ``"all"``, ``"date"``,
            or ``"datetime"``.
    """

    project_token: str
    format_type: str = "all"


@dataclass(frozen=True)
class PublishRequest:
    """A publish request containing the input configuration and the dataset to be published.

    Attributes:
        input_config: JSON-encoded server configuration string, including
            ``is_dry_publish`` flag.
        data: The dataset to send to the server.
    """

    input_config: str
    """JSON-encoded server configuration string, including ``is_dry_publish`` flag."""

    data: pd.DataFrame
    """The dataset to send to the server."""


@dataclass(frozen=True)
class ResponseMetadata:
    """Identity of the dataset the server acted on."""

    dataset_name: str | None = None
    dataset_version: int | None = None
    column_count: int | None = None
    dataset_uuid: str | None = None
    dataset_batch_number: int | None = None


@dataclass(frozen=True)
class ResponseMetrics:
    """Row counts reported by the server."""

    total_valid_rows: int = 0
    total_invalid_rows: int = 0
    total_duplicate_rows: int = 0


@dataclass(frozen=True)
class ResponseChecks:
    """Validation outcomes reported by the server."""

    schema_is_valid: bool = False
    config_is_valid: bool = False
    date_formats_are_valid: bool = False
    dataset_is_valid: bool = False
    invalid_datetime_formats: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PublishEnvelope:
    """Transport-layer response shared by publish and dry-publish calls.

    Mirrors the canonical envelope the Arrow Flight server emits on both
    ``do_put`` and ``do_action``.
    """

    success: bool = False
    metadata: ResponseMetadata = field(default_factory=ResponseMetadata)
    metrics: ResponseMetrics = field(default_factory=ResponseMetrics)
    checks: ResponseChecks = field(default_factory=ResponseChecks)
    errors: list[str] = field(default_factory=list)
    invalid_records: pd.DataFrame | None = None
    """Populated from the Arrow IPC channel, not from the JSON payload."""

    @classmethod
    def from_json(cls, payload: dict, invalid_records: pd.DataFrame | None = None) -> PublishEnvelope:
        """Build an envelope from the server's decoded JSON response.

        Missing sections fall back to defaults so an older or partial server
        response degrades to "nothing validated" rather than raising.
        """
        metadata = payload.get("metadata") or {}
        metrics = payload.get("metrics") or {}
        checks = payload.get("checks") or {}

        return cls(
            success=payload.get("success", False),
            metadata=ResponseMetadata(
                dataset_name=metadata.get("dataset_name"),
                dataset_version=metadata.get("dataset_version"),
                column_count=metadata.get("column_count"),
                dataset_uuid=metadata.get("dataset_uuid"),
                dataset_batch_number=metadata.get("dataset_batch_number"),
            ),
            metrics=ResponseMetrics(
                total_valid_rows=metrics.get("total_valid_rows") or 0,
                total_invalid_rows=metrics.get("total_invalid_rows") or 0,
                total_duplicate_rows=metrics.get("total_duplicate_rows") or 0,
            ),
            checks=ResponseChecks(
                schema_is_valid=checks.get("schema_is_valid", False),
                config_is_valid=checks.get("config_is_valid", False),
                date_formats_are_valid=checks.get("date_formats_are_valid", False),
                dataset_is_valid=checks.get("dataset_is_valid", False),
                invalid_datetime_formats=checks.get("invalid_datetime_formats") or {},
            ),
            errors=payload.get("errors") or [],
            invalid_records=invalid_records,
        )


# Publish and dry-publish share one wire contract; the names are kept so call
# sites still read as the operation they perform.
DryPublishResponse = PublishEnvelope
PublishResponse = PublishEnvelope
