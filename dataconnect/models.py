from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, Self, TypeVar
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


class DatasetFrame:
    """Lazy dataset reference; fetching requires the originating client to remain open."""

    __slots__ = ("_dataset_uuid", "_fetch_data")

    def __init__(self, dataset_uuid: str, fetch_data: Callable[[UUID, int | None], pd.DataFrame]) -> None:
        self._dataset_uuid = dataset_uuid
        self._fetch_data = fetch_data

    def head(self, count: int = 6) -> pd.DataFrame:
        """Fetch the first count rows, matching R's default of six rows."""
        return self._fetch_data(UUID(self._dataset_uuid), count)

    def collect(self) -> pd.DataFrame:
        """Fetch the complete dataset without retaining a previous head limit."""
        return self._fetch_data(UUID(self._dataset_uuid), None)

    def __repr__(self) -> str:
        return f"DatasetFrame(dataset_uuid={self._dataset_uuid!r})"

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        """Keep this opaque reference intact when copying metadata with asdict()."""
        return self


@dataclass(frozen=True)
class Dataset:
    """A dataset belonging to a study environment."""

    dataset_uuid: str
    study_uuid: str
    study_env_uuid: str
    dataset_name: str
    dataset_short_name: str | None = None
    type: str | None = None
    source: str | None = None
    activation_status: str | None = None
    dataset_status: str | None = None
    collection: list[str] | None = field(default=None, hash=False)
    last_updated: str | None = None
    version: str | None = None
    other_versions: list[dict[str, str]] | None = field(default=None, hash=False)
    frame: DatasetFrame | None = field(default=None, repr=False, compare=False)


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


@dataclass(frozen=True)
class ResultMetadata:
    """Identity of the dataset a publish or dry-publish call acted on."""

    dataset_name: str | None = None
    dataset_version: int | None = None
    column_count: int | None = None
    dataset_uuid: str | None = None


@dataclass(frozen=True)
class ResultMetrics:
    """Row counts reported by the server."""

    total_valid_rows: int = 0
    total_invalid_rows: int = 0
    total_duplicate_rows: int = 0


@dataclass(frozen=True)
class ResultChecks:
    """Validation outcomes reported by the server."""

    schema_is_valid: bool = False
    config_is_valid: bool = False
    date_formats_are_valid: bool = False
    dataset_is_valid: bool = False
    invalid_datetime_formats: dict[str, str] = field(default_factory=dict)


@dataclass
class _PublishEnvelopeResult:
    """Canonical result shape shared by publish and dry publish."""

    success: bool
    metadata: ResultMetadata = field(default_factory=ResultMetadata)
    metrics: ResultMetrics = field(default_factory=ResultMetrics)
    checks: ResultChecks = field(default_factory=ResultChecks)
    errors: list[str] = field(default_factory=list)
    invalid_records: pd.DataFrame | None = None

    # Flat accessors below are deprecated views onto the envelope, kept so
    # existing notebooks keep working. Prefer metadata/metrics/checks.

    @property
    def status(self) -> bool:
        return self.success

    @property
    def dataset_name(self) -> str | None:
        return self.metadata.dataset_name

    @property
    def dataset_version(self) -> int | None:
        return self.metadata.dataset_version

    @property
    def dataset_uuid(self) -> str | None:
        return self.metadata.dataset_uuid

    @property
    def no_of_columns(self) -> int | None:
        return self.metadata.column_count

    @property
    def valid_record_count(self) -> int:
        return self.metrics.total_valid_rows

    @property
    def invalid_record_count(self) -> int:
        return self.metrics.total_invalid_rows

    @property
    def duplicate_record_count(self) -> int:
        return self.metrics.total_duplicate_rows

    @property
    def is_schema_valid(self) -> bool:
        return self.checks.schema_is_valid

    @property
    def is_config_valid(self) -> bool:
        return self.checks.config_is_valid

    @property
    def is_dataset_valid(self) -> bool:
        return self.checks.dataset_is_valid

    @property
    def invalid_datetime_formats(self) -> dict[str, str]:
        return self.checks.invalid_datetime_formats


@dataclass
class DryPublishResult(_PublishEnvelopeResult):
    """Result of a dry publish operation, including validation status and details."""


@dataclass
class PublishResult(_PublishEnvelopeResult):
    """Result of a publish operation, including status and details."""


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
