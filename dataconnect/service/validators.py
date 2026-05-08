"""Input validation helpers for service-layer operations."""

from __future__ import annotations

from dataconnect.exceptions import ValidationError


def validate_search_study_name(search_study_name: str | None) -> None:
    """Validate optional study-name filter used by ``get_studies``."""

    if not search_study_name:
        return

    if not isinstance(search_study_name, str):
        raise ValidationError("search_study_name must be a string")
