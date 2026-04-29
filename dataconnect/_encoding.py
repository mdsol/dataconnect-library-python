"""Encoding utilities for DataConnect."""

from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> bytes:
    """Serialize *obj* to JSON (bytes)."""
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def loads(data: bytes) -> Any:
    """Deserialize JSON from *data* (bytes)."""
    return json.loads(data.decode("utf-8"))
