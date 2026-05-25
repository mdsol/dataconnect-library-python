"""Abstract Transport interface — technology-agnostic.

No pyarrow imports here.

Layer 3 deals only with transport-level DTOs defined in ``transport/models.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dataconnect.transport.models import (
    DatasetTicket,
    DataTable,
    DryPublishResponse,
    PublishRequest,
    PublishResponse,
    ResourceInfo,
    ResourceQuery,
)


class Transport(ABC):
    """Minimal abstract transport for DataConnect operations."""

    @abstractmethod
    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        """List available data resources matching the given query.

        The transport does not interpret the action name or body — that is the
        service layer's responsibility.
        """

    @abstractmethod
    def get_ticket(self, ticket: DatasetTicket) -> DataTable:
        """Fetch the full dataset described by ``ticket``.

        All record batches from the stream are read and returned as a single
        ``DataTable`` containing the complete result set.
        """

    @abstractmethod
    def dry_publish_dataset(self, publish_request: PublishRequest) -> DryPublishResponse:
        """Dry publish a dataset described by ``publish_request``.

        All record batches from the stream are read and returned as a single
        ``DryPublishResponse`` containing the complete result set.
        """

    @abstractmethod
    def publish_dataset(self, publish_request: PublishRequest) -> PublishResponse:
        """Publish a dataset described by ``publish_request``.

        All record batches from the stream are read and returned as a single
        ``PublishResponse`` containing the complete result set.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the transport connection."""
