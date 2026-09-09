"""Tests for get_datasets returning PaginatedResponse[Dataset]."""

from __future__ import annotations

import json
from copy import copy, deepcopy
from dataclasses import asdict, fields
from threading import Lock
from uuid import UUID

import pandas as pd
import pyarrow as pa
import pytest

from dataconnect.client import DataConnectClient
from dataconnect.models import Dataset, DatasetVersion, PaginatedResponse, Pagination
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.transport.errors import TransportError
from dataconnect.transport.models import DataRef, DatasetTicket, DataTable, ResourceInfo, ResourceQuery


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


def _dataset_resource(payload: dict[str, object], total_records: int = 1) -> ResourceInfo:
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


_DATASET_UUID = "073410b6-79be-3e7d-ae37-92f6e054013e"
_OTHER_DATASET_UUID = "006e4963-aba4-5d3b-93c4-e01354077219"
_IDENTIFIERS = {
    "dataset_uuid": _DATASET_UUID,
    "study_uuid": "64a98a9b-1512-44c8-92af-e4cab0183670",
    "study_env_uuid": str(_STUDY_ENV_UUID),
    "dataset_name": "LBHEM2",
}
_METADATA = {
    "dataset_short_name": "LB",
    "type": "Derived Dataset",
    "source": "JL_templ_upgrd2",
    "activation_status": "Activated",
    "dataset_status": "Warning",
    "collection": ["clinical", "labs"],
    "last_updated": "2024-06-15 09:30:00",
    "version": "1",
    "other_versions": [{"version": "0", "dataset_uuid": _OTHER_DATASET_UUID}],
}
_EXPECTED_FIELDS = {
    "dataset_uuid",
    "study_uuid",
    "study_env_uuid",
    "dataset_name",
    "dataset_short_name",
    "type",
    "source",
    "activation_status",
    "dataset_status",
    "collection",
    "last_updated",
    "version",
    "other_versions",
    "frame",
}


class _PagedFetchingTransport(_FakeTransport):
    def __init__(self, pages: dict[int, list[dict[str, object]]]) -> None:
        super().__init__()
        self.pages = pages
        self.requests: list[ResourceQuery] = []
        self.tickets: list[DatasetTicket] = []
        self.closed = False
        self.lock = Lock()
        self.fetch_error: TransportError | None = None

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        self.requests.append(request)
        body = json.loads(request.body)
        total_records = sum(len(payloads) for payloads in self.pages.values())
        return [_dataset_resource(payload, total_records) for payload in self.pages[body.get("page", 1)]]

    def get_ticket(self, ticket: DatasetTicket) -> DataTable:
        if self.closed:
            raise TransportError(error_code="CLOSED", message="transport closed")
        if self.fetch_error is not None:
            raise self.fetch_error
        self.tickets.append(ticket)
        table = pa.table({"dataset_uuid": [ticket.dataset_uuid] * 8, "value": list(range(8))})
        if ticket.limit is not None:
            table = table.slice(0, ticket.limit)
        buffer = pa.BufferOutputStream()
        with pa.ipc.new_stream(buffer, table.schema) as writer:
            writer.write_table(table)
        return DataTable(schema_bytes=table.schema.serialize().to_pybytes(), ipc_bytes=buffer.getvalue().to_pybytes())

    def close(self) -> None:
        self.closed = True


def test_complete_metadata_and_frames_survive_independent_pages() -> None:
    pages = {
        1: [{**_IDENTIFIERS, **_METADATA}],
        2: [{**_IDENTIFIERS, **_METADATA, "dataset_uuid": _OTHER_DATASET_UUID, "version": "41, 51"}],
    }
    transport = _PagedFetchingTransport(pages)
    client = DataConnectClient(DefaultDataConnectService(transport))

    for page_number, payloads in pages.items():
        result = client.get_datasets(_STUDY_ENV_UUID, search_dataset_name="LB", page=page_number, page_size=1)
        assert len(transport.requests) == page_number
        assert transport.requests[-1].action == "datasets.list"
        assert json.loads(transport.requests[-1].body) == {
            "study_environment_uuid": str(_STUDY_ENV_UUID),
            "search_dataset_name": "LB",
            "page": page_number,
            "page_size": 1,
        }
        assert result.total_records == 2
        assert result.pagination == Pagination(page=page_number, page_size=1, total_pages=2)
        dataset = result.items[0]
        assert {item.name for item in fields(dataset)} == _EXPECTED_FIELDS
        for name, value in payloads[0].items():
            assert getattr(dataset, name) == value
        assert dataset.frame is not None

    assert transport.tickets == []


@pytest.mark.parametrize("scenario", ["missing", "null", "empty"])
def test_metadata_preserves_missing_null_and_empty_values(scenario: str) -> None:
    metadata = {}
    if scenario == "null":
        metadata = dict.fromkeys(_METADATA)
    elif scenario == "empty":
        metadata = {name: [] if name in {"collection", "other_versions"} else "" for name in _METADATA}
    transport = _FakeTransport([_dataset_resource({**_IDENTIFIERS, **metadata})])

    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]

    for name in _METADATA:
        assert getattr(dataset, name) == metadata.get(name)
    assert dataset.frame is not None


@pytest.mark.parametrize("version", ["3", "v1,v2", "41, 51, 88", "", None])
def test_version_labels_are_preserved_without_coercion(version: str | None) -> None:
    transport = _FakeTransport([_dataset_resource({**_IDENTIFIERS, "version": version})])

    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]

    assert dataset.version == version


def test_frame_fetches_only_on_demand_and_binds_each_dataset() -> None:
    transport = _PagedFetchingTransport(
        {
            1: [
                {**_IDENTIFIERS, **_METADATA},
                {**_IDENTIFIERS, "dataset_uuid": _OTHER_DATASET_UUID},
            ]
        }
    )
    client = DataConnectClient(DefaultDataConnectService(transport))
    first, second = client.get_datasets(_STUDY_ENV_UUID).items
    assert transport.tickets == []
    assert first.frame is not None
    assert second.frame is not None
    assert first.frame is not second.frame

    preview = first.frame.head(3)
    assert isinstance(preview, pd.DataFrame)
    assert preview["value"].tolist() == [0, 1, 2]
    assert preview["dataset_uuid"].tolist() == [_DATASET_UUID] * 3
    assert len(first.frame.head()) == 6
    assert len(first.frame.collect()) == 8
    assert second.frame.head(1)["dataset_uuid"].tolist() == [_OTHER_DATASET_UUID]
    assert transport.tickets == [
        DatasetTicket(dataset_uuid=_DATASET_UUID, limit=3),
        DatasetTicket(dataset_uuid=_DATASET_UUID, limit=6),
        DatasetTicket(dataset_uuid=_DATASET_UUID, limit=None),
        DatasetTicket(dataset_uuid=_OTHER_DATASET_UUID, limit=1),
    ]


def test_frame_copy_and_inspection_do_not_copy_or_fetch_connection() -> None:
    transport = _PagedFetchingTransport({1: [{**_IDENTIFIERS, **_METADATA}]})
    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]
    assert dataset.frame is not None

    encoded = asdict(dataset)
    assert set(encoded) == _EXPECTED_FIELDS
    assert encoded["frame"] is dataset.frame
    assert deepcopy(dataset).frame is dataset.frame
    assert copy(dataset.frame) is dataset.frame
    assert "_fetch_data" not in repr(dataset.frame)
    assert "_PagedFetchingTransport" not in repr(dataset)
    for name, value in _METADATA.items():
        assert encoded[name] == value
    assert transport.tickets == []
    assert len(encoded["frame"].head(1)) == 1


def test_dataset_constructor_and_equality_remain_independent_of_frame() -> None:
    transport = _FakeTransport([_dataset_resource(_IDENTIFIERS)])
    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]
    legacy = Dataset(**_IDENTIFIERS)

    assert legacy.frame is None
    assert dataset == legacy
    assert dataset.frame is not None


def test_frame_uses_existing_fetch_error_translation_and_client_lifetime() -> None:
    transport = _PagedFetchingTransport({1: [_IDENTIFIERS]})
    service = DefaultDataConnectService(transport)
    client = DataConnectClient(service)
    dataset = client.get_datasets(_STUDY_ENV_UUID).items[0]
    assert dataset.frame is not None
    transport.fetch_error = TransportError(error_code="FETCH", message="fetch failed")

    with pytest.raises(Exception) as direct:
        service.fetch_data(UUID(_DATASET_UUID))
    with pytest.raises(type(direct.value), match="fetch failed"):
        dataset.frame.collect()

    transport.fetch_error = None
    client.close()
    with pytest.raises(Exception, match="transport closed"):
        dataset.frame.collect()


def test_r_screenshot_metadata_preserves_empty_collections_and_null_timestamp() -> None:
    payload = {
        **_IDENTIFIERS,
        **_METADATA,
        "dataset_short_name": "",
        "collection": [],
        "last_updated": None,
        "other_versions": [],
    }
    transport = _FakeTransport([_dataset_resource(payload)])
    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]

    assert dataset.dataset_short_name == ""
    assert dataset.collection == []
    assert dataset.last_updated is None
    assert dataset.other_versions == []
    assert dataset.frame is not None


def test_null_dataset_identifier_is_preserved_without_attaching_frame() -> None:
    transport = _FakeTransport([_dataset_resource({**_IDENTIFIERS, "dataset_uuid": None})])
    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]

    assert dataset.dataset_uuid is None
    assert dataset.frame is None


def test_dataset_remains_hashable_with_collection_metadata() -> None:
    transport = _FakeTransport([_dataset_resource({**_IDENTIFIERS, **_METADATA})])
    dataset = DefaultDataConnectService(transport).get_datasets(_STUDY_ENV_UUID).items[0]

    assert hash(dataset) == hash(deepcopy(dataset))
    assert {dataset: "cached metadata"}[deepcopy(dataset)] == "cached metadata"


def test_dataset_version_frames_fetch_only_on_demand_and_bind_each_version() -> None:
    transport = _PagedFetchingTransport(
        {
            1: [
                {**_IDENTIFIERS, "dataset_version": "1", "dataset_uuid": _OTHER_DATASET_UUID},
                {**_IDENTIFIERS, "dataset_version": "2"},
            ]
        }
    )
    client = DataConnectClient(DefaultDataConnectService(transport))

    newest, oldest = client.get_dataset_versions(UUID(_DATASET_UUID))

    assert transport.tickets == []
    assert newest.frame is not None
    assert oldest.frame is not None
    assert newest.frame is not oldest.frame
    assert [newest.dataset_version, oldest.dataset_version] == ["2", "1"]
    assert {field.name for field in fields(newest)} == {
        "study_uuid",
        "study_environment_uuid",
        "dataset_uuid",
        "dataset_name",
        "dataset_version",
        "frame",
    }
    preview = newest.frame.head(3)
    assert isinstance(preview, pd.DataFrame)
    assert preview["value"].tolist() == [0, 1, 2]
    assert preview["dataset_uuid"].tolist() == [_DATASET_UUID] * 3
    assert len(newest.frame.head()) == 6
    assert len(newest.frame.collect()) == 8
    assert oldest.frame.head(1)["dataset_uuid"].tolist() == [_OTHER_DATASET_UUID]
    assert oldest.frame.collect()["dataset_uuid"].tolist() == [_OTHER_DATASET_UUID] * 8
    assert transport.tickets == [
        DatasetTicket(dataset_uuid=_DATASET_UUID, limit=3),
        DatasetTicket(dataset_uuid=_DATASET_UUID, limit=6),
        DatasetTicket(dataset_uuid=_DATASET_UUID, limit=None),
        DatasetTicket(dataset_uuid=_OTHER_DATASET_UUID, limit=1),
        DatasetTicket(dataset_uuid=_OTHER_DATASET_UUID, limit=None),
    ]


@pytest.mark.parametrize("label", ["1", "v1,v2", "41, 51, 88", ""])
def test_dataset_version_frame_preserves_labels_and_metadata_semantics(label: str) -> None:
    transport = _PagedFetchingTransport({1: [{**_IDENTIFIERS, "dataset_version": label}]})
    client = DataConnectClient(DefaultDataConnectService(transport))
    version = client.get_dataset_versions(UUID(_DATASET_UUID))[0]
    legacy = DatasetVersion(UUID(_IDENTIFIERS["study_uuid"]), _STUDY_ENV_UUID, UUID(_DATASET_UUID), "LBHEM2", label)

    assert legacy.frame is None
    assert version.frame is not None
    assert version.dataset_version == label
    assert version == legacy
    assert hash(version) == hash(legacy)
    assert repr(version) == repr(legacy)
    assert asdict(version)["frame"] is version.frame
    assert deepcopy(version).frame is version.frame
    assert copy(version.frame) is version.frame
    assert transport.tickets == []


def test_dataset_version_frame_preserves_fetch_errors_and_client_lifetime() -> None:
    transport = _PagedFetchingTransport({1: [{**_IDENTIFIERS, "dataset_version": "1"}]})
    service = DefaultDataConnectService(transport)
    client = DataConnectClient(service)
    version = client.get_dataset_versions(UUID(_DATASET_UUID))[0]
    assert version.frame is not None
    transport.fetch_error = TransportError(error_code="FETCH", message="fetch failed")

    with pytest.raises(Exception) as direct:
        service.fetch_data(version.dataset_uuid)
    with pytest.raises(type(direct.value), match="fetch failed"):
        version.frame.collect()
    with pytest.raises(type(direct.value), match="fetch failed"):
        version.frame.head()

    transport.fetch_error = None
    client.close()
    with pytest.raises(Exception, match="transport closed"):
        version.frame.collect()


def test_dataset_versions_empty_response_does_not_fetch() -> None:
    transport = _PagedFetchingTransport({1: []})
    client = DataConnectClient(DefaultDataConnectService(transport))

    assert client.get_dataset_versions(UUID(_DATASET_UUID)) == []
    assert transport.tickets == []


def test_dataset_versions_metadata_is_unchanged_before_and_after_listing() -> None:
    older = {**_IDENTIFIERS, "dataset_version": "1", "dataset_uuid": _OTHER_DATASET_UUID}
    newer = {**_IDENTIFIERS, "dataset_version": "2"}
    versions = [_dataset_resource(older), _dataset_resource(newer)]
    transport = _FakeTransport(versions)
    client = DataConnectClient(DefaultDataConnectService(transport))
    expected = [
        {
            "study_uuid": UUID(_IDENTIFIERS["study_uuid"]),
            "study_environment_uuid": _STUDY_ENV_UUID,
            "dataset_uuid": UUID(_DATASET_UUID),
            "dataset_name": "LBHEM2",
            "dataset_version": "2",
        },
        {
            "study_uuid": UUID(_IDENTIFIERS["study_uuid"]),
            "study_environment_uuid": _STUDY_ENV_UUID,
            "dataset_uuid": UUID(_OTHER_DATASET_UUID),
            "dataset_name": "LBHEM2",
            "dataset_version": "1",
        },
    ]

    initial_versions = client.get_dataset_versions(UUID(_DATASET_UUID))
    for item, metadata in zip(initial_versions, expected, strict=True):
        assert item.frame is not None
        assert asdict(item) == {**metadata, "frame": item.frame}
    transport._resources = [_dataset_resource({**_IDENTIFIERS, **_METADATA})]
    assert client.get_datasets(_STUDY_ENV_UUID).items[0].frame is not None
    transport._resources = versions
    subsequent_versions = client.get_dataset_versions(UUID(_DATASET_UUID))
    for item, metadata in zip(subsequent_versions, expected, strict=True):
        assert item.frame is not None
        assert asdict(item) == {**metadata, "frame": item.frame}
    assert subsequent_versions == initial_versions
    assert transport.last_request is not None
    assert transport.last_request.action == "dataset_versions.list"
    assert json.loads(transport.last_request.body) == {"dataset_uuid": _DATASET_UUID}
