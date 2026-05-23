"""Arrow Flight implementation of the Transport interface.

This is the ONLY file in the SDK that imports ``pyarrow.flight``.
All pyarrow Flight exceptions are caught here and translated into
technology-agnostic ``TransportError`` subtypes before propagating up.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import platform
import socket
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version

import pyarrow as pa
import pyarrow.flight as flight

from dataconnect.transport.arrow_flight.error_handler import parse_dataconnect_error
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import TransportValidationError
from dataconnect.transport.models import (
    DataRef,
    DatasetTicket,
    DataTable,
    DryPublishResponse,
    PublishRequest,
    PublishResponse,
    ResourceInfo,
    ResourceQuery,
)


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


def _normalize_arrow_type(dtype: pa.DataType) -> pa.DataType:
    """Recursively normalize Arrow types that widen during a pandas round-trip.

    ``pa.Table.from_pandas()`` always infers the "large" variants because pandas
    has no distinction between them:

    * ``large_string``  → ``string``
    * ``large_binary``  → ``binary``
    * ``large_list<T>`` → ``list<T>``  (applied recursively to the value type)
    """
    if dtype == pa.large_utf8():
        return pa.utf8()
    if dtype == pa.large_binary():
        return pa.binary()
    if pa.types.is_large_list(dtype):
        return pa.list_(_normalize_arrow_type(dtype.value_type))
    return dtype


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
        user_uuid: str = "",
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

        if user_uuid:
            self._call_headers.append((b"user-uuid", str(user_uuid).encode("utf-8")))

        try:
            sdk_version = version("dataconnect-library-python")
        except Exception:
            sdk_version = "0.1.0"
        self._call_headers.append((b"python-sdk-version", sdk_version.encode("utf-8")))

        self._call_headers.append((b"sdk-type", b"Python"))

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            client_ip = s.getsockname()[0]
            s.close()
        except Exception:
            client_ip = "127.0.0.1"
        self._call_headers.append((b"client-ip", client_ip.encode("utf-8")))

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

        ticket_bytes = json.dumps(dataclasses.asdict(ticket), separators=(",", ":")).encode("utf-8")
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

    def dry_publish_dataset(self, publish_request: PublishRequest) -> DryPublishResponse:
        """Send a dataset to the server via Arrow Flight ``do_put`` and return the validation result.

        The method serialises the request DataFrame to Arrow IPC, streams it to
        the server batch-by-batch, then reads two metadata responses from the
        server before closing the call:

        1. A JSON buffer containing validation fields (status, error lists, …).
        2. An optional Arrow IPC buffer containing the invalid-records table
           (``None`` when all rows pass validation).

        The ``done_writing()`` / ``close()`` split is intentional:
        * ``done_writing()`` signals end-of-stream without closing the RPC call,
          allowing the metadata reads to complete while the call is still alive.
        * ``writer.close()`` in the ``finally`` block always terminates the call,
          even if writing or reading raises.

        Args:
            request: A :class:`PublishRequest` carrying the encoded server config
                (``input_config``) and the dataset as a ``pd.DataFrame``.

        Returns:
            A :class:`DryPublishResponse` populated from the server's JSON response and,
            when present, the invalid-records Arrow table converted to a
            ``pd.DataFrame``.

        Raises:
            TransportError: Any Arrow Flight or gRPC error is translated by
                :func:`parse_dataconnect_error` before propagating.
        """

        descriptor_bytes = publish_request.input_config.encode("utf-8")
        flight_descriptor = flight.FlightDescriptor.for_path(descriptor_bytes)

        arrow_table = pa.Table.from_pandas(publish_request.data, preserve_index=False)

        # pa.Table.from_pandas() widens string→large_string, binary→large_binary,
        # and list→large_list. Normalize back so the schema matches the server.
        arrow_table = arrow_table.cast(
            pa.schema([f.with_type(_normalize_arrow_type(f.type)) for f in arrow_table.schema])
        )

        try:
            writer, reader = self._client.do_put(flight_descriptor, arrow_table.schema, self._options())

            try:
                for batch in arrow_table.to_batches():
                    writer.write_batch(batch)
                writer.done_writing()  # only signal completion when all batches succeeded

                # Read while the RPC call is still open (before writer.close())
                # The server first writes a JSON result, then the Arrow table as IPC bytes
                _json_buf = reader.read()
                json_result = json.loads(_json_buf.to_pybytes())

                # Read the Arrow table returned by the server upon successful publishing
                metadata_buf = reader.read()
                result_table = pa.ipc.open_stream(pa.BufferReader(metadata_buf)).read_all() if metadata_buf else None
            finally:
                writer.close()  # terminates the RPC call — must happen after all reads

            return DryPublishResponse(
                status=json_result.get("status", False),
                is_schema_valid=json_result.get("is_schema_valid", False),
                is_config_valid=json_result.get("is_config_valid", False),
                dataset_valid=json_result.get("dataset_valid", False),
                errors=json_result.get("errors", []),
                invalid_datetime_formats=json_result.get("invalid_datetime_formats", {}),
                dataset_name=json_result.get("dataset_name", ""),
                dataset_version=json_result.get("dataset_version", 0),
                no_of_columns=json_result.get("no_of_columns", 0),
                valid_record_count=json_result.get("valid_record_count", 0),
                duplicate_record_count=json_result.get("duplicate_record_count", 0),
                invalid_record_count=json_result.get("invalid_record_count", 0),
                invalid_records=result_table.to_pandas() if result_table else None,
            )

        except Exception as ex:
            raise parse_dataconnect_error(ex) from ex

    def publish_dataset(self, publish_request: PublishRequest) -> PublishResponse:
        """Send a dataset to the server via Arrow Flight ``do_put`` and return the publish result.

        Follows the same two-phase metadata protocol as :meth:`dry_publish_dataset`:
        the server first returns a JSON result buffer, then an optional Arrow IPC
        buffer containing any invalid records.

        Args:
            publish_request: A :class:`PublishRequest` carrying the encoded server
                config (``input_config``) and the dataset as a ``pd.DataFrame``.

        Returns:
            A :class:`PublishResponse` populated from the server's JSON response,
            including the assigned dataset UUID, version, and record counts.

        Raises:
            TransportError: Any Arrow Flight or gRPC error is translated by
                :func:`parse_dataconnect_error` before propagating.
        """
        descriptor_bytes = publish_request.input_config.encode("utf-8")
        flight_descriptor = flight.FlightDescriptor.for_path(descriptor_bytes)

        arrow_table = pa.Table.from_pandas(publish_request.data, preserve_index=False)

        # pa.Table.from_pandas() widens string→large_string, binary→large_binary,
        # and list→large_list. Normalize back so the schema matches the server.
        arrow_table = arrow_table.cast(
            pa.schema([f.with_type(_normalize_arrow_type(f.type)) for f in arrow_table.schema])
        )

        try:
            writer, reader = self._client.do_put(flight_descriptor, arrow_table.schema, self._options())

            try:
                for batch in arrow_table.to_batches():
                    writer.write_batch(batch)
                writer.done_writing()  # only signal completion when all batches succeeded

                # Read while the RPC call is still open (before writer.close())
                # The server first writes a JSON result, then the Arrow table as IPC bytes
                _json_buf = reader.read()
                json_result = json.loads(_json_buf.to_pybytes())

                # Read the Arrow table returned by the server upon successful publishing
                metadata_buf = reader.read()
                result_table = pa.ipc.open_stream(pa.BufferReader(metadata_buf)).read_all() if metadata_buf else None
            finally:
                writer.close()  # terminates the RPC call — must happen after all reads

            return PublishResponse(
                status=json_result.get("status", False),
                dataset_name=json_result.get("dataset_name", None),
                dataset_uuid=json_result.get("dataset_uuid", None),
                dataset_version=json_result.get("dataset_version", None),
                dataset_batch_number=json_result.get("dataset_batch_number", None),
                valid_record_count=json_result.get("valid_record_count", None),
                duplicate_record_count=json_result.get("duplicate_record_count", None),
                invalid_record_count=json_result.get("invalid_record_count", None),
                invalid_records=result_table.to_pandas() if result_table else None,
            )

        except Exception as ex:
            raise parse_dataconnect_error(ex) from ex

    def close(self) -> None:
        self._client.close()
