"""Authentication and authorization utilities for DataConnect."""

from __future__ import annotations

from dataclasses import dataclass


class Credentials:
    """Marker base class for all credentials types."""


@dataclass(frozen=True)
class BearerTokenAuth(Credentials):
    """Bearer token authentication credentials (OAuth access token)."""

    token: str
