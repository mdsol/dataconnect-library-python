from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class StudyEnvironment:
    uuid: UUID
    name: str


@dataclass(frozen=True)
class Study:
    uuid: UUID
    name: str
    environments: list[StudyEnvironment] = field(default_factory=list)
