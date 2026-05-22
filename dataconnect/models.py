from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar
from uuid import UUID

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
