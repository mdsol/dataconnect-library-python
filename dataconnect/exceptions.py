"""Public exceptions for DataConnect.

Hierarchy
---------
DataConnectError
├── AuthenticationError    — authentication failure from server
├── AuthorizationError     — authorization failure from server
├── NotFoundError          — requested resource does not exist
├── ServerError            — unexpected server-side error
└── ValidationError        — server response was malformed or unexpected
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
class DataConnectError(Exception):
    error_code: str
    message: str
    timestamp: str | None = None
    details: list[ErrorDetail] | None = None

    def __str__(self) -> str:
        lines = [
            f"Error Code: [{self.error_code}]",
            f"Message: {self.message}",
        ]

        if self.timestamp is not None:
            lines.append(f"Timestamp: {self.timestamp}")

        if self.details:
            lines.append("Details:")
            for detail in self.details:
                lines.append(str(detail))

        return "\n".join(lines)


class AuthenticationError(DataConnectError):
    """Authentication failure."""


class AuthorizationError(DataConnectError):
    """Authorization failure."""


class NotFoundError(DataConnectError):
    """The requested resource (study, dataset, etc.) was not found."""


class ServerError(DataConnectError):
    """Unexpected server-side error."""


class ValidationError(DataConnectError):
    """Server returned data in an unexpected or invalid format."""
