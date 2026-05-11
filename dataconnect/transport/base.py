"""Abstract Transport interface — technology-agnostic.

No pyarrow imports here.

Layer 3 deals only with transport-level DTOs defined in ``transport/models.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dataconnect.transport.models import ResourceInfo, ResourceQuery, DataTable


class Transport(ABC):
    """Minimal abstract transport for DataConnect operations."""

    @abstractmethod
    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        """List available data resources matching the given query.

        The transport does not interpret the action name or body — that is the
        service layer's responsibility.
        """

    @abstractmethod
    def do_get(self, request: ResourceQuery) -> DataTable:
        """Retrieve data for a single endpoint ticket.

        Reads all chunks from the server stream and returns a single
        ``DataTable`` containing the complete result set.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the transport connection."""
