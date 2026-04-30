"""Default Flight transport implementation using pyarrow."""

from __future__ import annotations

from collections.abc import Iterator

import pyarrow as pa
from pyarrow import flight

from dataconnect.exceptions import AuthenticationError, DataConnectError, QueryError
from dataconnect.auth import BearerTokenAuth, Credentials
from dataconnect.framework.transport import FlightTransport, RecordBatchStream


class PyArrowFlightTransport(FlightTransport):
    """Flight transport implementation using pyarrow."""

    def __init__(
        self,
        location: str,
        *,
        credentials: Credentials | None = None,
        tls_root_certs: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        try:
            self._client = flight.FlightClient(
                location,
                tls_root_certs=tls_root_certs,
            )
        except Exception as exc:
            raise ConnectionError(f"Failed to connect to {location}: {exc}") from exc

        self._call_headers: list[tuple[bytes, bytes]] = [
            (k.lower().encode("ascii"), v.encode("utf-8")) for k, v in (headers or {}).items()
        ]

        if credentials is not None:
            self._apply_credentials(credentials)

    # Auth
    def _apply_credentials(self, credentials: Credentials) -> None:
        try:
            if isinstance(credentials, BearerTokenAuth):
                self._call_headers.append((b"authorization", f"Bearer {credentials.token}".encode()))
            else:
                raise DataConnectError(f"Unsupported credentials type: {type(credentials)}")
        except flight.FlightUnauthenticatedError as exc:
            raise AuthenticationError(f"Authentication failed: {exc}") from exc
        except flight.FlightError as exc:
            raise ConnectionError(str(exc)) from exc

    def __options(self) -> flight.FlightCallOptions:
        return flight.FlightCallOptions(headers=self._call_headers)

    # FlightTransport
    def do_get(self, ticket: bytes) -> RecordBatchStream:
        try:
            reader = self._client.do_get(flight.Ticket(ticket), self.__options())
        except flight.FlightUnauthenticatedError as exc:
            raise AuthenticationError(f"Authentication failed: {exc}") from exc
        except flight.FlightError as exc:
            raise QueryError(str(exc)) from exc
        return _PyArrowRecordBatchStream(reader)

    def do_put(self, command: bytes, table: pa.Table) -> bytes | None:
        """Upload a table via DoPut with a command descriptor."""
        return b""

    def do_action(self, action: str, body: bytes = b"") -> bytes:
        """Invoke a Flight action and return a response."""
        return b""

    def close(self) -> None:
        self._client.close()


class _PyArrowRecordBatchStream(RecordBatchStream):
    """Adapter for pyarrow RecordBatchReader to implement RecordBatchStream."""

    def __init__(self, reader: flight.FlightStreamReader) -> None:
        self._reader = reader

    def read_all(self) -> pa.Table:
        """Read all record batches into a single PyArrow Table."""
        try:
            return self._reader.read_all()
        except flight.FlightError as exc:
            raise QueryError(str(exc)) from exc

    def __iter__(self) -> Iterator[pa.RecordBatch]:
        try:
            while True:
                chunk = self._reader.read_chunk()
                yield chunk.data
        except StopIteration:
            return
        except flight.FlightError as exc:
            raise QueryError(str(exc)) from exc
