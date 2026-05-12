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

import pyarrow.flight as flight

from dataconnect.transport.base import Transport
from dataconnect.transport.errors import (
    TransportAuthenticationError,
    TransportAuthorizationError,
    TransportConnectionError,
    TransportStatusError,
)
from dataconnect.transport.models import DataRef, ResourceInfo, ResourceQuery


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


# Maps service-layer action names to the flight_type value the Arrow Flight server expects.
_ACTION_FLIGHT_TYPE: dict[str, str] = {
    "studies.list": "STUDIES",
    "datasets.list": "DATASETS",
    "dataset_versions.list": "VERSIONS",
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
        self._call_headers: list[tuple[bytes, bytes]] = []

        scheme = "grpc+tls" if use_tls else "grpc"
        uri = f"{scheme}://{host}:{port}"

        try:
            self._client = self._get_client(uri, use_tls)
        except Exception as exc:
            raise TransportConnectionError(f"Failed to create FlightClient: {exc}") from exc

        if token:
            self._call_headers.append((b"authorization", f"Bearer {token}".encode()))

    def _get_client(self, uri: str, use_tls: bool) -> flight.FlightClient:
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
        return flight.FlightCallOptions(headers=self._call_headers)

    # Transport

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        """Translate the action name to Arrow Flight criteria and return resource records."""

        flight_type = _ACTION_FLIGHT_TYPE.get(request.action)

        if flight_type is None:
            raise TransportStatusError(
                f"Unknown action: {request.action!r}", status_code=3, grpc_status="INVALID_ARGUMENT"
            )

        body = json.loads(request.body) if request.body else {}
        criteria = json.dumps({**body, "flight_type": flight_type}, separators=(",", ":")).encode("utf-8")

        try:
            raw_flights = self._client.list_flights(criteria, self._options())
            return [_to_resource_info(f) for f in raw_flights]

        except flight.FlightUnauthenticatedError as ex:
            raise TransportAuthenticationError(str(ex)) from ex
        except flight.FlightUnauthorizedError as ex:
            raise TransportAuthorizationError(str(ex)) from ex
        except flight.FlightUnavailableError as ex:
            raise TransportConnectionError(str(ex)) from ex
        except flight.FlightInternalError as ex:
            raise TransportStatusError(str(ex), status_code=13, grpc_status="INTERNAL") from ex
        except flight.FlightError as ex:
            raise TransportConnectionError(str(ex)) from ex
        except Exception as ex:
            raise TransportConnectionError(f"Unexpected error during list_resources: {ex}") from ex

    def close(self) -> None:
        self._client.close()
