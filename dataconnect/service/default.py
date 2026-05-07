"""Default service implementation — domain logic, encoding, and error translation."""

from __future__ import annotations

from uuid import UUID

from dataconnect.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
    DataConnectError,
    NotFoundError,
    QueryError,
    ServerError,
    ValidationError,
)
from dataconnect.models import DatasetVersion, Study
from dataconnect.service.base import DataConnectService
from dataconnect.service.mappers import resource_to_dataset_version, resource_to_study
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import (
    TransportAuthenticationError,
    TransportAuthorizationError,
    TransportConnectionError,
    TransportError,
    TransportIOError,
    TransportNotFoundError,
    TransportStatusError,
)
from dataconnect.transport.models import ResourceQuery

# Server action identifiers
_ACTION_LIST_STUDIES = "studies.list"
_ACTION_LIST_DATASET_VERSIONS = "dataset_versions.list"


def _translate_error(ex: TransportError) -> DataConnectError:
    """Map a ``TransportError`` to the appropriate public ``DataConnectError``."""

    if isinstance(ex, TransportAuthenticationError):
        return AuthenticationError(str(ex))
    if isinstance(ex, TransportAuthorizationError):
        return AuthorizationError(str(ex))
    if isinstance(ex, TransportNotFoundError):
        return NotFoundError(str(ex))
    if isinstance(ex, TransportStatusError):
        return ServerError(str(ex), status_code=ex.status_code)
    if isinstance(ex, TransportConnectionError):
        return ConnectionError(str(ex))
    if isinstance(ex, TransportIOError):
        return QueryError(str(ex))

    return ServerError(str(ex))


class DefaultDataConnectService(DataConnectService):
    """Concrete service injected with an abstract ``Transport``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    # DataConnectService

    def get_studies(self) -> list[Study]:

        request = ResourceQuery(action=_ACTION_LIST_STUDIES)

        try:
            resources = self._transport.list_resources(request)
        except TransportError as ex:
            raise _translate_error(ex) from ex

        try:
            return [resource_to_study(r) for r in resources]
        except (IndexError, KeyError, TypeError, ValueError) as ex:
            raise ValidationError(f"Unexpected studies response format: {ex}") from ex

    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
        request = ResourceQuery(action=_ACTION_LIST_DATASET_VERSIONS).append_body({"dataset_uuid": str(dataset_uuid)})

        try:
            resources = self._transport.list_resources(request)
        except TransportError as ex:
            raise _translate_error(ex) from ex

        try:
            return [resource_to_dataset_version(r) for r in resources]
        except (IndexError, KeyError, TypeError, ValueError) as ex:
            raise ValidationError(f"Unexpected dataset versions response format: {ex}") from ex

    def close(self) -> None:

        try:
            self._transport.close()
        except TransportError as ex:
            raise ConnectionError(str(ex)) from ex
