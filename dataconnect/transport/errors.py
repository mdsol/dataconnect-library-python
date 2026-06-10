"""Internal transport-layer exceptions.

These are NEVER re-exported publicly.

The service layer catches them and translates them into
public ``DataConnectError`` subtypes.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any


@dataclass
class ErrorDetail:
    field: str | None = None
    message: str | None = None
    expected: str | None = None
    extra: dict[str, Any] = dataclass_field(default_factory=dict)

    def __str__(self) -> str:
        lines = ["\n  Error Detail:"]

        if self.field is not None:
            lines.append(f"    Field: {self.field}")

        if self.message is not None:
            lines.append(f"    Message: {self.message}")

        if self.expected is not None:
            lines.append(f"    Expected: {self.expected}")

        for k, v in self.extra.items():
            lines.append(f"    {k}: {v}")

        return "\n".join(lines)


@dataclass
class TransportError(Exception):
    """Base class for all transport-layer errors."""

    error_code: str
    message: str
    timestamp: str | None = None
    details: list[ErrorDetail] | None = None


class TransportAuthenticationError(TransportError):
    """Raised on authentication failures."""


class TransportAuthorizationError(TransportError):
    """Raised on authorization failures."""


class TransportValidationError(TransportError):
    """Raised on validation failures."""


class TransportNotFoundError(TransportError):
    """Raised when the server returns not-found response."""


class TransportServerError(TransportError):
    """Raised when the server returns an internal error status."""
