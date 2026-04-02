"""Abstract transport interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

import pyarrow as pa


class FlightTransport(ABC):
    """Minimal abstract transport interface for DataConnect Flight operations."""

    @abstractmethod
    def do_action(self, action: str, body: bytes = b"") -> bytes:
        """Invoke a Flight action and return a response."""

    @abstractmethod
    def do_get(self, ticket: bytes) -> RecordBatchStream:
        """Open a DoGet stream for ticket."""

    @abstractmethod
    def do_put(
        self,
        command: bytes,
        table: pa.Table,
    ) -> bytes | None:
        """Upload a table via DoPut with a command descriptor."""

    @abstractmethod
    def close(self) -> None:
        """Close the transport connection."""


class RecordBatchStream(ABC):
    """Minimal abstract stream interface for Flight record batches."""

    @abstractmethod
    def read_all(self) -> pa.Table:
        """Read all record batches into a single PyArrow Table."""

    @abstractmethod
    def __iter__(self) -> Iterator[pa.RecordBatch]:
        """Iterate over record batches."""
