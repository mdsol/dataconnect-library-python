"""Tests for get_datasets returning PaginatedResponse[Dataset]."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from dataconnect.exceptions import ValidationError
from dataconnect.models import Dataset, PaginatedResponse, Pagination
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.transport.errors import TransportError
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

    def do_get(self, request: ResourceQuery) -> None:
        pass

    def close(self) -> None:
        return None


def _dataset_resource(payload: dict[str, str], total_records: int = 1) -> ResourceInfo:
    return ResourceInfo(
        descriptor=b"",
        endpoints=[DataRef(ticket=json.dumps(payload).encode("utf-8"))],
        total_records=total_records,
        schema_bytes=b"",
    )


_STUDY_ENV_UUID = UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a")


class TestGetDatasetsReturnsPaginatedResponse:
    """Verify get_datasets returns a PaginatedResponse[Dataset]."""

    def test_returns_paginated_response_with_items(self) -> None:
        payload = {
            "dataset_uuid": "073410b6-79be-3e7d-ae37-92f6e054013e",
            "study_uuid": "64a98a9b-1512-44c8-92af-e4cab0183670",
            "study_env_uuid": "4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
            "dataset_name": "labs",
        }
        transport = _FakeTransport(resources=[_dataset_resource(payload, total_records=3)])
        service = DefaultDataConnectService(transport)

        result = service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID)

        assert isinstance(result, PaginatedResponse)
        assert result.total_records == 3
        assert result.items == [
            Dataset(
                dataset_uuid="073410b6-79be-3e7d-ae37-92f6e054013e",
                study_uuid="64a98a9b-1512-44c8-92af-e4cab0183670",
                study_env_uuid="4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
                dataset_name="labs",
            )
        ]

    def test_pagination_metadata_uses_request_params(self) -> None:
        payload = {
            "dataset_uuid": "aaa",
            "study_uuid": "bbb",
            "study_env_uuid": "ccc",
            "dataset_name": "vitals",
        }
        transport = _FakeTransport(resources=[_dataset_resource(payload, total_records=100)])
        service = DefaultDataConnectService(transport)

        result = service.get_datasets(
            study_environment_uuid=_STUDY_ENV_UUID,
            page=2,
            page_size=25,
        )

        assert result.pagination == Pagination(page=2, page_size=25, total_pages=4)

    def test_total_pages_rounds_up(self) -> None:
        payload = {
            "dataset_uuid": "aaa",
            "study_uuid": "bbb",
            "study_env_uuid": "ccc",
            "dataset_name": "vitals",
        }
        # 51 records / 25 per page = 3 pages (rounds up)
        transport = _FakeTransport(resources=[_dataset_resource(payload, total_records=51)])
        service = DefaultDataConnectService(transport)

        result = service.get_datasets(
            study_environment_uuid=_STUDY_ENV_UUID,
            page=1,
            page_size=25,
        )

        assert result.pagination.total_pages == 3

    def test_empty_resources_returns_zero_totals(self) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        result = service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID)

        assert isinstance(result, PaginatedResponse)
        assert result.total_records == 0
        assert result.items == []
        assert result.pagination == Pagination(page=1, page_size=50, total_pages=0)

    def test_builds_correct_request_body(self) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        service.get_datasets(
            study_environment_uuid=_STUDY_ENV_UUID,
            search_dataset_name="vitals",
            page=3,
            page_size=10,
        )

        assert transport.last_request is not None
        assert transport.last_request.action == "datasets.list"
        body = json.loads(transport.last_request.body)
        assert body == {
            "study_environment_uuid": str(_STUDY_ENV_UUID),
            "search_dataset_name": "vitals",
            "page": 3,
            "page_size": 10,
        }

    def test_raises_validation_error_for_invalid_uuid(self) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        with pytest.raises(ValidationError, match="study_environment_uuid must be a valid UUID"):
            service.get_datasets(study_environment_uuid="not-a-uuid")  # type: ignore[arg-type]

    def test_raises_validation_error_for_zero_uuid(self) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        with pytest.raises(ValidationError, match="study_environment_uuid must not be empty"):
            service.get_datasets(study_environment_uuid=UUID(int=0))

    @pytest.mark.parametrize("page", [0, -1, -100])
    def test_raises_validation_error_for_invalid_page(self, page: int) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        with pytest.raises(ValidationError, match="page must be a positive integer"):
            service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID, page=page)

    def test_raises_validation_error_for_non_int_page(self) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        with pytest.raises(ValidationError, match="page must be a positive integer"):
            service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID, page="2")  # type: ignore[arg-type]

    @pytest.mark.parametrize("page_size", [0, -1, -50])
    def test_raises_validation_error_for_invalid_page_size(self, page_size: int) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        with pytest.raises(ValidationError, match="page_size must be a positive integer"):
            service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID, page_size=page_size)

    def test_raises_validation_error_for_non_int_page_size(self) -> None:
        transport = _FakeTransport(resources=[])
        service = DefaultDataConnectService(transport)

        with pytest.raises(ValidationError, match="page_size must be a positive integer"):
            service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID, page_size="25")  # type: ignore[arg-type]

    def test_translates_transport_errors(self) -> None:
        transport = _FakeTransport(error=TransportError(error_code="CONN", message="cannot connect"))
        service = DefaultDataConnectService(transport)

        with pytest.raises(Exception, match="cannot connect"):
            service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID)

    def test_multiple_items_returned(self) -> None:
        resources = [
            _dataset_resource(
                {"dataset_uuid": "aaa", "study_uuid": "bbb", "study_env_uuid": "ccc", "dataset_name": "labs"},
                total_records=2,
            ),
            _dataset_resource(
                {"dataset_uuid": "ddd", "study_uuid": "eee", "study_env_uuid": "fff", "dataset_name": "vitals"},
                total_records=2,
            ),
        ]
        transport = _FakeTransport(resources=resources)
        service = DefaultDataConnectService(transport)

        result = service.get_datasets(study_environment_uuid=_STUDY_ENV_UUID, page_size=10)

        assert len(result.items) == 2
        assert result.total_records == 2
        assert result.items[0].dataset_name == "labs"
        assert result.items[1].dataset_name == "vitals"
