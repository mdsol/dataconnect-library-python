"""Default service implementation — domain logic, encoding, and error translation."""

from __future__ import annotations

from uuid import UUID

import pandas as pd

from dataconnect.models import Dataset, DatasetVersion, PaginatedResponse, Pagination, StudiesResult
from dataconnect.service.base import DataConnectService
from dataconnect.service.error_handler import translate_error
from dataconnect.service.mappers import (
    resource_to_dataset,
    resource_to_dataset_version,
    resource_to_fetched_data,
    resource_to_study,
)
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import TransportError
from dataconnect.transport.models import DatasetTicket, ResourceQuery

# Server action identifiers
_ACTION_LIST_STUDIES = "studies.list"
_ACTION_LIST_DATASETS = "datasets.list"
_ACTION_LIST_DATASET_VERSIONS = "dataset_versions.list"


class DefaultDataConnectService(DataConnectService):
    """Concrete service injected with an abstract ``Transport``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    # DataConnectService

    def get_studies(self, search_study_name: str | None = None) -> StudiesResult:
        """List studies the authenticated user can access.

        Args:
            search_study_name: Optional full or partial study name filter.

        Returns:
            A :class:`StudiesResult` containing:
            - ``total_records``: total number of studies accessible to the authenticated user.
            - ``studies``: list of :class:`Study` objects matching the criteria.
        """

        request = ResourceQuery(action=_ACTION_LIST_STUDIES)
        request = request.append_body({"search_study_name": search_study_name})

        try:
            resources = self._transport.list_resources(request)
            total_records = resources[0].total_records if resources else 0
            studies = [resource_to_study(r) for r in resources]
            return StudiesResult(total_records=total_records, studies=studies)
        except Exception as ex:
            raise translate_error(ex) from ex

    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
        """List available versions for a dataset.

        Args:
            dataset_uuid: UUID of the dataset whose versions are requested.

        Returns:
            A list of :class:`DatasetVersion` objects for the given dataset.

        Raises:
            ValidationError: If *dataset_uuid* is not a valid UUID (upstream).
        """

        request = ResourceQuery(action=_ACTION_LIST_DATASET_VERSIONS).append_body({"dataset_uuid": str(dataset_uuid)})

        try:
            resources = self._transport.list_resources(request)

            # Return Sorted dataset versions in descending order (newest first) based on the dataset_version field.
            return sorted(
                (resource_to_dataset_version(r) for r in resources),
                key=lambda dv: dv.dataset_version,
                reverse=True,
            )
        except Exception as ex:
            raise translate_error(ex) from ex

    def fetch_data(self, dataset_uuid: UUID, first_n_rows: int | None = None) -> pd.DataFrame:
        """Fetch data for a dataset"""

        ticket = DatasetTicket(
            dataset_uuid=str(dataset_uuid),
            limit=first_n_rows,
        )

        try:
            table = self._transport.get_ticket(ticket)
            return resource_to_fetched_data(table)
        except TransportError as ex:
            raise translate_error(ex) from ex

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

        request = ResourceQuery(action=_ACTION_LIST_DATASETS).append_body(
            {
                "study_environment_uuid": str(study_environment_uuid),
                "search_dataset_name": search_dataset_name,
                "page": page,
                "page_size": page_size,
            }
        )

        try:
            resources = self._transport.list_resources(request)
            items = [resource_to_dataset(r) for r in resources]
            total_records = resources[0].total_records if resources else 0
            total_pages = (total_records + page_size - 1) // page_size if page_size > 0 else 0
            return PaginatedResponse(
                total_records=total_records,
                pagination=Pagination(page=page, page_size=page_size, total_pages=total_pages),
                items=items,
            )
        except TransportError as ex:
            raise translate_error(ex) from ex

    def close(self) -> None:
        """Close the underlying transport connection."""

        try:
            self._transport.close()
        except TransportError as ex:
            raise translate_error(ex) from ex
