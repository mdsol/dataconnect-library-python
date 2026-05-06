"""dataconnect — Python SDK for the Medidata DataConnect service."""

from __future__ import annotations

from dataconnect.client import DataConnectClient
from dataconnect.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
    DataConnectError,
    NotFoundError,
    QueryError,
    ServerError,
    ValidationError,
)
from dataconnect.models import Study, StudyEnvironment

__all__ = [
    # Client
    "DataConnectClient",

    # Domain models
    "Study",
    "StudyEnvironment",

    # Exceptions — catch these in user application code
    "DataConnectError",
    "ConnectionError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "QueryError",
    "ServerError",
    "ValidationError",
]
