from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar
from uuid import UUID

import pandas as pd

T = TypeVar("T")


@dataclass(frozen=True)
class StudyEnvironment:
    uuid: UUID
    name: str


@dataclass(frozen=True)
class Study:
    uuid: UUID
    name: str
    environments: list[StudyEnvironment] = field(default_factory=list)


@dataclass(frozen=True)
class StudiesResult:
    total_records: int
    studies: list[Study]


@dataclass(frozen=True)
class DatasetVersion:
    study_uuid: UUID
    study_environment_uuid: UUID
    dataset_uuid: UUID
    dataset_name: str
    dataset_version: str


@dataclass(frozen=True)
class Dataset:
    """A dataset belonging to a study environment."""

    dataset_uuid: str
    study_uuid: str
    study_env_uuid: str
    dataset_name: str


@dataclass(frozen=True)
class Pagination:
    """Server-side pagination metadata."""

    page: int
    page_size: int
    total_pages: int


@dataclass
class PaginatedResponse(Generic[T]):  # noqa: UP046
    """A paginated collection returned by list endpoints."""

    total_records: int
    pagination: Pagination
    items: list[T]


@dataclass
class DryPublishResult:
    """Result of a dry publish operation, including validation status and details."""

    status: bool
    is_schema_valid: bool | None = None
    is_config_valid: bool | None = None
    is_dataset_valid: bool | None = None
    errors: list[str] = field(default_factory=list)
    invalid_datetime_formats: dict[str, str] = field(default_factory=dict)
    dataset_name: str | None = None
    dataset_version: int | None = None
    no_of_columns: int | None = None
    valid_record_count: int | None = None
    duplicate_record_count: int | None = None
    invalid_record_count: int | None = None
    invalid_records: pd.DataFrame | None = None


@dataclass
class PublishResult:
    """Result of a publish operation, including status and details."""

    status: bool
    dataset_name: str | None = None
    dataset_uuid: str | None = None
    dataset_version: int | None = None
    dataset_batch_number: int | None = None
    valid_record_count: int | None = None
    duplicate_record_count: int | None = None
    invalid_record_count: int | None = None
    invalid_records: pd.DataFrame | None = None


@dataclass(frozen=True)
class DatetimeFormat:
    """A single supported datetime format string with its classification."""

    format: str
    """The format string as returned by the server (e.g. ``"yyyy-MM-dd"``)."""

    type: str
    """Either ``"date"`` (date-only) or ``"datetime"`` (date with time component)."""


@dataclass
class DatetimeFormatsResult:
    """Result of a :meth:`DataConnectClient.get_datetime_formats` call.

    Holds the full list of supported datetime formats returned by the server
    and provides convenience accessors for the common views.

    Examples:
        >>> result = client.get_datetime_formats(project_token="...")
        >>> for fmt in result.all():
        ...     print(fmt.format, fmt.type)
        >>> only_dates = result.dates()           # list[str]
        >>> only_datetimes = result.datetimes()   # list[str]
    """

    formats: list[DatetimeFormat] = field(default_factory=list)
    """The full list of supported formats, in the order returned by the server."""

    def all(self) -> list[DatetimeFormat]:
        """Return every supported format with its type classification."""
        return list(self.formats)

    def dates(self) -> list[str]:
        """Return only the date-style format strings (no time component)."""
        return [f.format for f in self.formats if f.type == "date"]

    def datetimes(self) -> list[str]:
        """Return only the datetime-style format strings (with a time component)."""
        return [f.format for f in self.formats if f.type == "datetime"]
