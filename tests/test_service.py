from __future__ import annotations

import json
from uuid import UUID

import pytest

from dataconnect.exceptions import ConnectionError, ValidationError
from dataconnect.models import DatasetVersion
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.transport.errors import TransportConnectionError
from dataconnect.transport.models import DataRef, ResourceInfo, ResourceQuery


class _FakeTransport:
    def __init__(
        self,
        resources: list[ResourceInfo] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._resources = resources or []
        self._error = error
        self.last_request: ResourceQuery | None = None

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        self.last_request = request
        if self._error is not None:
            raise self._error
        return self._resources

    def close(self) -> None:
        return None


def _resource_with_ticket_json(payload: dict[str, object]) -> ResourceInfo:
    return ResourceInfo(
        descriptor=b"",
        endpoints=[DataRef(ticket=json.dumps(payload).encode("utf-8"))],
        total_records=1,
        schema_bytes=b"",
    )


def test_get_dataset_versions_returns_mapped_models_and_builds_request() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    payload = {
        "study_uuid": "64a98a9b-1512-44c8-92af-e4cab0183670",
        "study_env_uuid": "4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
        "dataset_uuid": str(dataset_uuid),
        "dataset_name": "labs",
        "dataset_version": "1",
    }
    transport = _FakeTransport(resources=[_resource_with_ticket_json(payload)])
    service = DefaultDataConnectService(transport)

    result = service.get_dataset_versions(dataset_uuid)

    assert result == [
        DatasetVersion(
            study_uuid=UUID("64a98a9b-1512-44c8-92af-e4cab0183670"),
            study_environment_uuid=UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a"),
            dataset_uuid=dataset_uuid,
            dataset_name="labs",
            dataset_version="1",
        )
    ]
    assert transport.last_request is not None
    assert transport.last_request.action == "dataset_versions.list"
    assert json.loads(transport.last_request.body) == {"dataset_uuid": str(dataset_uuid)}


def test_get_dataset_versions_translates_transport_errors() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    transport = _FakeTransport(error=TransportConnectionError("cannot connect"))
    service = DefaultDataConnectService(transport)

    with pytest.raises(ConnectionError, match="cannot connect"):
        service.get_dataset_versions(dataset_uuid)


def test_get_dataset_versions_raises_validation_error_on_bad_payload() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    bad_payload = {
        "study_uuid": "64a98a9b-1512-44c8-92af-e4cab0183670",
        "study_env_uuid": "4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
        "dataset_uuid": str(dataset_uuid),
        "dataset_name": "labs",
        # dataset_version intentionally omitted to trigger mapper validation failure.
    }
    transport = _FakeTransport(resources=[_resource_with_ticket_json(bad_payload)])
    service = DefaultDataConnectService(transport)

    with pytest.raises(ValidationError, match="Unexpected dataset versions response format"):
        service.get_dataset_versions(dataset_uuid)


def test_manual_resource_query_body_can_be_used_directly() -> None:
    """Assert that constructing a ResourceQuery with a JSON body string works as expected.

    This mirrors the alternative to `append_body` where the caller provides a
    JSON-encoded `body` explicitly (using json.dumps to guarantee valid JSON).
    """
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")

    # Build the compact JSON string the same way append_body would

    body_str = json.dumps({"dataset_uuid": str(dataset_uuid)}, separators=(",", ":"))

    rq = ResourceQuery(action="dataset_versions.list", body=body_str)

    assert json.loads(rq.body) == {"dataset_uuid": str(dataset_uuid)}
    # compact representation (no spaces)
    assert rq.body == body_str
