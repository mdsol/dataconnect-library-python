"""Public API for the DataConnect client library.

``DataConnectClient`` is a thin façade over ``DataConnectService``.
The ``connect()`` class method is the composition root — the only place in
the SDK where concrete implementation types are wired together.
"""

from __future__ import annotations

from types import TracebackType

from dataconnect.models import Study
from dataconnect.service import DataConnectService, DefaultDataConnectService

from uuid import UUID

import pandas as pd

_DEFAULT_HOST = "enodia-gateway.platform.imedidata.com"
_DEFAULT_PORT = 443


class DataConnectClient:
    """Client for interacting with DataConnect services."""

    def __init__(self, service: DataConnectService) -> None:
        """Initialize the client with an injected service implementation."""
        self._service = service

    @classmethod
    def connect(
        cls,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        use_tls: bool = True,
        token: str = "",
    ) -> DataConnectClient:

        # Import is deferred so pyarrow.flight is only loaded when this factory
        # is called — callers injecting a custom transport are unaffected.
        from dataconnect.transport.arrow_flight.transport import ArrowFlightTransport

        transport = ArrowFlightTransport(host=host, port=port, use_tls=use_tls, token=token)

        return cls(DefaultDataConnectService(transport))

    # Public API

    def get_studies(self) -> list[Study]:
        """List the studies the client is authorized to access."""
        return self._service.get_studies()
    
    def fetch_data(
        self,
        dataset_uuid: UUID,
        first_n_rows: int | None = None,
    ) -> pd.DataFrame:
        """Fetch data frames for a given dataset UUID."""
        return self._service.fetch_data(dataset_uuid, first_n_rows)

    # Lifecycle

    def close(self) -> None:
        """Close the underlying connection."""
        self._service.close()

    def __enter__(self) -> DataConnectClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._service.close()
