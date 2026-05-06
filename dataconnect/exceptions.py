"""Public exceptions for DataConnect.

Hierarchy
---------
DataConnectError
├── ConnectionError        — unable to reach server
├── AuthenticationError    — authentication failure from server
├── AuthorizationError     — authorization failure from server
├── NotFoundError          — requested resource does not exist
├── QueryError             — server rejected query / stream read failure
├── ServerError            — unexpected server-side error
└── ValidationError        — server response was malformed or unexpected
"""

from __future__ import annotations


class DataConnectError(Exception):
    """Base exception for all DataConnect client errors."""


class ConnectionError(DataConnectError):
    """Unable to establish or maintain a connection to the server."""


class AuthenticationError(DataConnectError):
    """Authentication failure."""


class AuthorizationError(DataConnectError):
    """Authorization failure."""


class NotFoundError(DataConnectError):
    """The requested resource (study, dataset, etc.) was not found."""


class QueryError(DataConnectError):
    """The server rejected the query or a data-stream read failed."""


class ServerError(DataConnectError):
    """Unexpected server-side error."""

    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


class ValidationError(DataConnectError):
    """Server returned data in an unexpected or invalid format."""
