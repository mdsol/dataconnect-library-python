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
class DryPublishResponse:
    """Transport-layer response from a dry-publish call.

    Carries the server's validation outcome for all rows and schema checks
    without any data being persisted.
    """

    status: bool
    is_schema_valid: bool
    is_config_valid: bool
    dataset_valid: bool
    errors: list[str]
    invalid_datetime_formats: dict[str, str]
    dataset_name: str
    dataset_version: int
    no_of_columns: int
    valid_record_count: int
    duplicate_record_count: int
    invalid_record_count: int = 0
    invalid_records: pd.DataFrame | None = None


@dataclass(frozen=True)
class PublishResponse:
    """Transport-layer response from a live publish call.

    Carries the server's outcome after persisting the submitted dataset,
    including the assigned dataset UUID and version number.
    """

    status: bool
    dataset_name: str | None = None
    dataset_uuid: str | None = None
    dataset_version: int | None = None
    dataset_batch_number: int | None = None
    valid_record_count: int | None = None
    duplicate_record_count: int | None = None
    invalid_record_count: int | None = None
    invalid_records: pd.DataFrame | None = None
