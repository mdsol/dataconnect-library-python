"""Input validation helpers for service-layer operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from dataconnect.exceptions import ErrorDetail, ValidationError


def validate_search_study_name(search_study_name: str | None) -> None:
    """Validate optional study-name filter used by ``get_studies``."""

    if not search_study_name:
        return

    if not isinstance(search_study_name, str):
        raise ValidationError("search_study_name must be a string")


def validate_uuid(
    value: object,
    *,
    field_name: str,
    error_code: str,
    message: str | None = None,
    details: list[ErrorDetail] | None = None,
) -> None:
    """Ensure *value* is a non-zero UUID.

    Raises:
        ValidationError: If *value* is not a UUID instance or is the nil UUID.
    """
    if not isinstance(value, UUID):
        raise ValidationError(
            error_code=error_code,
            message=message or f"{field_name} must be a valid UUID.",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            details=details,
        )

    if value.int == 0:
        raise ValidationError(
            error_code=error_code,
            message=message or f"{field_name} must not be empty.",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            details=details,
        )


def validate_positive_int(
    value: object,
    *,
    field_name: str,
    error_code: str,
    message: str | None = None,
    details: list[ErrorDetail] | None = None,
) -> None:
    """Ensure *value* is an integer >= 1.

    Raises:
        ValidationError: If *value* is not an int or is less than 1.
    """
    if not isinstance(value, int) or value < 1:
        raise ValidationError(
            error_code=error_code,
            message=message or f"{field_name} must be a positive integer.",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            details=details,
        )
