"""Public exceptions for DataConnect."""

from __future__ import annotations


class DataConnectError(Exception):
    """Base exception for all DataConnect client errors."""


class ConnectionError(DataConnectError):
    """Error connecting to the DataConnect server."""


class AuthenticationError(DataConnectError):
    """Error authenticating with the DataConnect server."""


class QueryError(DataConnectError):
    """Error executing a query."""
