"""Default service implementation — domain logic, encoding, and error translation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from dataconnect.exceptions import ValidationError
from dataconnect.models import Dataset, DatasetVersion, Study
from dataconnect.service.base import DataConnectService
from dataconnect.service.error_handler import translate_error
from dataconnect.service.mappers import resource_to_dataset, resource_to_dataset_version, resource_to_study
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import TransportError
from dataconnect.transport.models import ResourceQuery

# Server action identifiers
_ACTION_LIST_STUDIES = "studies.list"
_ACTION_LIST_DATASETS = "datasets.list"
_ACTION_LIST_DATASET_VERSIONS = "dataset_versions.list"


class DefaultDataConnectService(DataConnectService):
    """Concrete service injected with an abstract ``Transport``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    # DataConnectService

    def get_studies(self, search_study_name: str | None = None) -> list[Study]:
        """List studies the authenticated user can access.

        Args:
            search_study_name: Optional full or partial study name filter.

        Returns:
            A list of :class:`Study` objects matching the criteria.
        """
        # validate_search_study_name(search_study_name)

        request = ResourceQuery(action=_ACTION_LIST_STUDIES)
        if search_study_name and search_study_name.strip() != "":
            request = request.append_body({"search_study_name": search_study_name})

        try:
            resources = self._transport.list_resources(request)
            return [resource_to_study(r) for r in resources]
        except Exception as ex:
            raise translate_error(ex) from ex

    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
        """List available versions for a dataset.

        Args:
            dataset_uuid: UUID of the dataset whose versions are requested.

        Returns:
            A list of :class:`DatasetVersion` objects for the given dataset.

        Raises:
            ValidationError: If *dataset_uuid* is not a valid, non-zero UUID.
        """
        # Input validation: ensure callers pass a UUID
        if not isinstance(dataset_uuid, UUID):
            raise ValidationError(
                error_code="VAL_C_DATASET_UUID",
                message="dataset_uuid must be a valid UUID",
                timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        if dataset_uuid.int == 0:
            raise ValidationError(
                error_code="VAL_C_DATASET_UUID",
                message="dataset_uuid must not be empty",
                timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        request = ResourceQuery(action=_ACTION_LIST_DATASET_VERSIONS).append_body({"dataset_uuid": str(dataset_uuid)})

        try:
            resources = self._transport.list_resources(request)
            return [resource_to_dataset_version(r) for r in resources]
        except Exception as ex:
            raise translate_error(ex) from ex

    def get_datasets(
        self,
        study_environment_uuid: UUID,
        search_dataset_name: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> list[Dataset]:
        """List datasets for a study environment.

        Args:
            study_environment_uuid: UUID of the study environment (required).
            search_dataset_name: Full or partial dataset name filter.
            page: Page number for paginated results.
            page_size: Number of results per page.

        Returns:
            A list of :class:`Dataset` items matching the criteria.
        """
        if not isinstance(study_environment_uuid, UUID):
            raise ValidationError(
                error_code="VAL_C_STUDY_ENV_UUID",
                message="study_environment_uuid must be a valid UUID.",
                timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        if study_environment_uuid.int == 0:
            raise ValidationError(
                error_code="VAL_C_STUDY_ENV_UUID",
                message="study_environment_uuid must not be empty.",
                timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

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
            return [resource_to_dataset(r) for r in resources]
        except TransportError as ex:
            raise translate_error(ex) from ex

    def close(self) -> None:
        """Close the underlying transport connection."""

        try:
            self._transport.close()
        except TransportError as ex:
            raise translate_error(ex) from ex
