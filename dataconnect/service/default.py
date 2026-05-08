"""Default service implementation — domain logic, encoding, and error translation."""

from __future__ import annotations

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
from dataconnect.models import Study
from dataconnect.service.base import DataConnectService
from dataconnect.service.mappers import resource_to_study
from dataconnect.service.validators import validate_search_study_name
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

    def get_studies(self, search_study_name: str | None = None) -> list[Study]:

        validate_search_study_name(search_study_name)

        request = ResourceQuery(action=_ACTION_LIST_STUDIES)
        if search_study_name is not None:
            request = request.append_body({"search_study_name": search_study_name})

        try:
            resources = self._transport.list_resources(request)
        except TransportError as ex:
            raise _translate_error(ex) from ex

        try:
            return [resource_to_study(r) for r in resources]
        except (IndexError, KeyError, TypeError, ValueError) as ex:
            raise ValidationError(f"Unexpected studies response format: {ex}") from ex

    def close(self) -> None:

        try:
            self._transport.close()
        except TransportError as ex:
            raise ConnectionError(str(ex)) from ex
