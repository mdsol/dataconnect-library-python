"""Public API for the DataConnect client library.

``DataConnectClient`` is a thin façade over ``DataConnectService``.
The ``connect()`` class method is the composition root — the only place in
the SDK where concrete implementation types are wired together.
"""

from __future__ import annotations

from types import TracebackType
from uuid import UUID

import pandas as pd

from dataconnect.models import (
    Dataset,
    DatasetVersion,
    DatetimeFormatsResult,
    DryPublishResult,
    PaginatedResponse,
    PublishResult,
    StudiesResult,
)
from dataconnect.service import DataConnectService, DefaultDataConnectService

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
        user_uuid: str = "",
    ) -> DataConnectClient:

        # Import is deferred so pyarrow.flight is only loaded when this factory
        # is called — callers injecting a custom transport are unaffected.
        from dataconnect.transport.arrow_flight.transport import ArrowFlightTransport

        transport = ArrowFlightTransport(host=host, port=port, use_tls=use_tls, token=token, user_uuid=user_uuid)

        return cls(DefaultDataConnectService(transport))

    # Public API

    def get_studies(self, search_study_name: str | None = None) -> StudiesResult:
        """List the studies the client is authorized to access."""
        return self._service.get_studies(search_study_name=search_study_name)

    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
        """List the dataset versions the client is authorized to access."""
        return self._service.get_dataset_versions(dataset_uuid)

    def fetch_data(
        self,
        dataset_uuid: UUID,
        first_n_rows: int | None = None,
    ) -> pd.DataFrame:
        """Fetch data frames for a given dataset UUID."""
        return self._service.fetch_data(dataset_uuid, first_n_rows)

    def get_datasets(
        self,
        study_environment_uuid: UUID,
        search_dataset_name: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[Dataset]:
        """List datasets for a study environment.

        Args:
            study_environment_uuid: UUID of the study environment (required).
            search_dataset_name: Full or partial dataset name filter.
            page: Page number for paginated results.
            page_size: Number of results per page.

        Returns:
            A :class:`PaginatedResponse` of :class:`Dataset` items matching the criteria.
        """
        return self._service.get_datasets(
            study_environment_uuid=study_environment_uuid,
            search_dataset_name=search_dataset_name,
            page=page,
            page_size=page_size,
        )

    def dry_publish(
        self,
        project_token: str,
        dataset_name: str,
        key_columns: list[str],
        source_datasets: list[UUID],
        data: pd.DataFrame,
        datetime_formats: dict[str, str] | None = None,
    ) -> DryPublishResult:
        """Validate a dataset against the server without persisting any changes.

        Delegates directly to :meth:`DataConnectService.dry_publish`.

        Args:
            project_token: Base64-encoded project token identifying the target
                study, study environment, and project.
            dataset_name: Name of the dataset to validate.
            key_columns: Column names that form the unique key for the dataset.
            source_datasets: UUIDs of the source datasets the published dataset
                is derived from.
            data: The dataset to validate as a ``pd.DataFrame``.
            datetime_formats: Optional mapping of column name → datetime format
                string (e.g. ``{"visit_date": "yyyy-MM-dd"}``).

        Returns:
            A :class:`DryPublishResult` containing the server's validation
            outcome, including per-field validity flags, error messages, and
            an optional ``invalid_records`` DataFrame.
        """
        return self._service.dry_publish(
            project_token=project_token,
            dataset_name=dataset_name,
            key_columns=key_columns,
            source_datasets=source_datasets,
            data=data,
            datetime_formats=datetime_formats,
        )

    def publish(
        self,
        project_token: str,
        dataset_name: str,
        key_columns: list[str],
        source_datasets: list[UUID],
        data: pd.DataFrame,
        datetime_formats: dict[str, str] | None = None,
    ) -> PublishResult:
        """Publish a dataset to the server.

        Delegates directly to :meth:`DataConnectService.publish`.

        Args:
            project_token: Base64-encoded project token identifying the target
                study, study environment, and project.
            dataset_name: Name of the dataset to publish.
            key_columns: Column names that form the unique key for the dataset.
            source_datasets: UUIDs of the source datasets the published dataset
                is derived from.
            data: The dataset to publish as a ``pd.DataFrame``.
            datetime_formats: Optional mapping of column name → datetime format
                string (e.g. ``{"visit_date": "yyyy-MM-dd"}``).

        Returns:
            A :class:`PublishResult` containing the server's publish outcome,
            including dataset UUID, version, and record counts.
        """
        return self._service.publish(
            project_token=project_token,
            dataset_name=dataset_name,
            key_columns=key_columns,
            source_datasets=source_datasets,
            data=data,
            datetime_formats=datetime_formats,
        )

    def get_datetime_formats(
        self,
        project_token: str,
        format_type: str = "all",
    ) -> DatetimeFormatsResult:
        """Return the supported datetime formats filtered by ``format_type``.

        Delegates directly to :meth:`DataConnectService.get_datetime_formats`.

        Args:
            project_token: Base64-encoded project token identifying the target
                study, study environment, and project.
            format_type: Server-side filter to apply.  One of ``"all"``
                (default), ``"date"``, or ``"datetime"``.

        Returns:
            A :class:`DatetimeFormatsResult` exposing the classified list via
            :meth:`~DatetimeFormatsResult.all` and the type-filtered views via
            :meth:`~DatetimeFormatsResult.dates` and
            :meth:`~DatetimeFormatsResult.datetimes`.
        """
        return self._service.get_datetime_formats(
            project_token=project_token,
            format_type=format_type,
        )

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
