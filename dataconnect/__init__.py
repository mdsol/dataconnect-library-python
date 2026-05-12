"""dataconnect — Python SDK for the Medidata DataConnect service."""

from __future__ import annotations

from dataconnect.client import DataConnectClient
from dataconnect.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DataConnectError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from dataconnect.models import DatasetVersion, Study, StudyEnvironment

__all__ = [
    # Client
    "DataConnectClient",
    # Domain models
    "Study",
    "StudyEnvironment",
    "DatasetVersion",
    # Exceptions — catch these in user application code
    "DataConnectError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ServerError",
    "ValidationError",
]
