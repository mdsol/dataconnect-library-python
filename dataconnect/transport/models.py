"""Transport-layer DTOs — technology-agnostic contract."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


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
class ResourceInfo:
    """Technology-agnostic representation of a single resource."""

    descriptor: bytes
    endpoints: list[DataRef]
    total_records: int
    schema_bytes: bytes

