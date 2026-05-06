"""Internal transport-layer exceptions.

These are NEVER re-exported publicly.

The service layer catches them and translates them into
public ``DataConnectError`` subtypes.
"""

from __future__ import annotations


class TransportError(Exception):
    """Base class for all transport-layer errors."""


class TransportConnectionError(TransportError):
    """Raised when a connection to the server cannot be established."""


class TransportAuthenticationError(TransportError):
    """Raised on authentication failures."""

class TransportAuthorizationError(TransportError):
    """Raised on authorization failures."""

class TransportStatusError(TransportError):
    """Raised when the server returns an explicit error status."""

    def __init__(self, message: str, status_code: int, grpc_status: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.grpc_status = grpc_status


class TransportNotFoundError(TransportStatusError):
    """Raised when the server returns not-found response."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=5, grpc_status="NOT_FOUND")


class TransportIOError(TransportError):
    """Raised when reading from or writing to a data stream fails."""
