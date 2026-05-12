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
from dataconnect.models import DatasetVersion, PaginatedResponse, Pagination, Study, StudyEnvironment

__all__ = [
    # Client
    "DataConnectClient",
    # Domain models
    "Study",
    "StudyEnvironment",
    "DatasetVersion",
    "PaginatedResponse",
    "Pagination",
    # Exceptions — catch these in user application code
    "DataConnectError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ServerError",
    "ValidationError",
]
