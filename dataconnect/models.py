from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Study:
    id: str
    name: str


@dataclass(frozen=True)
class StudyEnvironment:
    """Environment variables for a study."""


@dataclass(frozen=True)
class Dataset:
    id: str
    study_id: str
    name: str


@dataclass(frozen=True)
class DatasetVersion:
    id: str
    dataset_id: str
    name: str
