"""Service-layer error translation utilities.

Provides a single function to map transport-layer ``TransportError`` subtypes
into the corresponding public ``DataConnectError`` subtypes that callers catch.
"""

from __future__ import annotations

from dataconnect.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DataConnectError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from dataconnect.exceptions import (
    ErrorDetail as DataConnectErrorDetail,
)
from dataconnect.transport.errors import (
    TransportAuthenticationError,
    TransportAuthorizationError,
    TransportError,
    TransportNotFoundError,
    TransportServerError,
    TransportValidationError,
)


def translate_error(ex: Exception) -> DataConnectError:
    """Map a transport-layer exception to the appropriate public ``DataConnectError`` subtype."""

    if not isinstance(ex, TransportError):
        return DataConnectError(error_code="SDK_ERROR", message=str(ex))

    error_details = [
        DataConnectErrorDetail(field=detail.field, message=detail.message, expected=detail.expected, extra=detail.extra)
        for detail in ex.details or []
    ]

    if isinstance(ex, TransportAuthenticationError):
        return AuthenticationError(
            error_code=ex.error_code, message=ex.message, timestamp=ex.timestamp, details=error_details
        )

    if isinstance(ex, TransportAuthorizationError):
        return AuthorizationError(
            error_code=ex.error_code, message=ex.message, timestamp=ex.timestamp, details=error_details
        )

    if isinstance(ex, TransportValidationError):
        return ValidationError(
            error_code=ex.error_code, message=ex.message, timestamp=ex.timestamp, details=error_details
        )

    if isinstance(ex, TransportNotFoundError):
        return NotFoundError(
            error_code=ex.error_code, message=ex.message, timestamp=ex.timestamp, details=error_details
        )

    if isinstance(ex, TransportServerError):
        return ServerError(error_code=ex.error_code, message=ex.message, timestamp=ex.timestamp, details=error_details)

    # Non-specific transport error
    return DataConnectError(error_code=ex.error_code, message=ex.message, timestamp=ex.timestamp, details=error_details)
