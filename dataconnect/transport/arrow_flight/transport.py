"""Arrow Flight implementation of the Transport interface.

This is the ONLY file in the SDK that imports ``pyarrow.flight``.
All pyarrow Flight exceptions are caught here and translated into
technology-agnostic ``TransportError`` subtypes before propagating up.
"""

from __future__ import annotations

import base64
import json
import platform
import subprocess
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.flight as flight

from dataconnect.transport.arrow_flight.error_handler import parse_dataconnect_error
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import TransportValidationError
from dataconnect.transport.models import DataRef, DataTable, DatasetTicket, ResourceInfo, ResourceQuery


def _to_resource_info(info: flight.FlightInfo) -> ResourceInfo:
    """Convert a pyarrow ``FlightInfo`` to a technology-agnostic ``ResourceInfo``."""

    descriptor_bytes = info.descriptor.command if info.descriptor else b""
    endpoints = [DataRef(ticket=e.ticket.ticket) for e in info.endpoints]
    schema_bytes = info.schema.serialize().to_pybytes()

    return ResourceInfo(
        descriptor=descriptor_bytes,
        endpoints=endpoints,
        schema_bytes=schema_bytes,
        total_records=info.total_records,
    )


def _to_bytes(table: pa.Table) -> DataTable:
    """Serialize a ``pa.Table`` to a technology-agnostic ``DataTable``.

    Each record batch is serialized individually as Arrow IPC bytes.
    The schema is serialized separately so it can be recovered without
    the data batches.
    """
    schema_bytes = table.schema.serialize().to_pybytes()

    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, table.schema)
    for batch in table.to_batches():
        writer.write_batch(batch)
    writer.close()
    ipc_bytes = sink.getvalue().to_pybytes()

    return DataTable(schema_bytes=schema_bytes, ipc_bytes=ipc_bytes)


# Maps service-layer action names to the flight_type value the Arrow Flight server expects.
_ACTION_FLIGHT_TYPE: dict[str, str] = {
    "studies.list": "STUDIES",
    "datasets.list": "DATASETS",
    "dataset_versions.list": "VERSIONS",
    "data.fetch_ticket": "DATA_FETCH_TICKET",
}


class ArrowFlightTransport(Transport):
    """Flight transport implementation using pyarrow (default implementation)."""

    def __init__(
        self,
        host: str,
        port: int,
        use_tls: bool,
        token: str = "",
    ) -> None:
        """Create a new Arrow Flight transport.

        Args:
            host: Hostname or IP address of the Arrow Flight server.
            port: Port number to connect to.
            use_tls: Whether to use TLS (``grpc+tls``) for the connection.
            token: Optional Bearer token appended to every request header.
        """
        self._call_headers: list[tuple[bytes, bytes]] = []

        scheme = "grpc+tls" if use_tls else "grpc"
        uri = f"{scheme}://{host}:{port}"

        try:
            self._client = self._get_client(uri, use_tls)
        except Exception as exc:
            raise parse_dataconnect_error(exc) from exc

        if token:
            self._call_headers.append((b"authorization", f"Bearer {token}".encode()))

    def _get_client(self, uri: str, use_tls: bool) -> flight.FlightClient:
        """Construct a :class:`flight.FlightClient` for the given URI.

        On Windows with TLS enabled, system root certificates are read from
        the Windows certificate store (``Cert:\\LocalMachine\\Root``) via
        PowerShell and passed as ``tls_root_certs`` to work around pyarrow's
        lack of native Windows certificate store support.
        """
        is_windows = platform.system() == "Windows"

        if use_tls and is_windows:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-Command",
                    (
                        "Get-ChildItem -Path Cert:\\LocalMachine\\Root | "
                        "ForEach-Object { [System.Convert]::ToBase64String($_.RawData) }"
                    ),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            pem_parts = []
            for b64 in result.stdout.splitlines():
                b64 = b64.strip()
                if not b64:
                    continue
                base64.b64decode(b64, validate=True)
                lines = ["-----BEGIN CERTIFICATE-----"]
                lines += [b64[i : i + 64] for i in range(0, len(b64), 64)]
                lines.append("-----END CERTIFICATE-----")
                pem_parts.append("\n".join(lines))

            pem_certs = "\n".join(pem_parts).encode("utf-8")
            client = flight.FlightClient(uri, tls_root_certs=pem_certs)
        else:
            client = flight.FlightClient(uri)

        return client

    def _options(self) -> flight.FlightCallOptions:
        """Return call options containing the configured request headers."""
        return flight.FlightCallOptions(headers=self._call_headers)

    # Transport

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        """Translate the action name to Arrow Flight criteria and return resource records."""

        flight_type = _ACTION_FLIGHT_TYPE.get(request.action)

        if flight_type is None:
            raise TransportValidationError(
                error_code="VAL_001",
                message=f"Unsupported action: {request.action}",
                timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        body = json.loads(request.body) if request.body else {}
        criteria = json.dumps({**body, "flight_type": flight_type}, separators=(",", ":")).encode("utf-8")

        try:
            raw_flights = self._client.list_flights(criteria, self._options())
            return [_to_resource_info(f) for f in raw_flights]

        except Exception as ex:
            raise parse_dataconnect_error(ex) from ex

    def get_ticket(self, ticket: DatasetTicket) -> DataTable:
        """Call FlightClient.do_get and read all chunks into a single pa.Table."""

        ticket_bytes = json.dumps(ticket.__dict__, separators=(",", ":")).encode("utf-8")
        ticket = flight.Ticket(ticket_bytes)

        try:
            table = self._client.do_get(ticket, self._options())
            batches: list[pa.RecordBatch] = []
            while True:
                try:
                    chunk, _metadata = table.read_chunk()
                    batches.append(chunk)
                except StopIteration:
                    break
                except flight.FlightError as ex:
                    raise parse_dataconnect_error(ex) from ex

            return _to_bytes(pa.Table.from_batches(batches, schema=table.schema))

        except Exception as ex:
            raise parse_dataconnect_error(ex) from ex

    def close(self) -> None:
        self._client.close()
