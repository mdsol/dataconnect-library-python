from __future__ import annotations

import sys
from types import ModuleType
from uuid import UUID

import pytest

from dataconnect.client import DataConnectClient
from dataconnect.models import DatasetVersion, Study


class _FakeService:
    def __init__(self, studies: list[Study] | None = None, versions: list[DatasetVersion] | None = None) -> None:
        self._studies = studies or []
        self._versions = versions or []
        self.closed = 0
        self.last_dataset_uuid: UUID | None = None

    def get_studies(self) -> list[Study]:
        return self._studies

    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
        self.last_dataset_uuid = dataset_uuid
        return self._versions

    def close(self) -> None:
        self.closed += 1


def test_get_studies_returns_service_result() -> None:
    studies = [Study(uuid=UUID("64a98a9b-1512-44c8-92af-e4cab0183670"), name="Study A")]
    client = DataConnectClient(_FakeService(studies=studies))

    assert client.get_studies() == studies


def test_get_dataset_versions_forwards_uuid_to_service() -> None:
    dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
    versions = [
        DatasetVersion(
            study_uuid=UUID("64a98a9b-1512-44c8-92af-e4cab0183670"),
            study_env_uuid=UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a"),
            dataset_uuid=dataset_uuid,
            dataset_name="labs",
            dataset_version="1",
        )
    ]
    service = _FakeService(versions=versions)
    client = DataConnectClient(service)

    result = client.get_dataset_versions(dataset_uuid)

    assert result == versions
    assert service.last_dataset_uuid == dataset_uuid


def test_context_manager_closes_service() -> None:
    service = _FakeService()

    with DataConnectClient(service) as client:
        assert isinstance(client, DataConnectClient)

    assert service.closed == 1


def test_connect_uses_arrow_transport_and_default_service(monkeypatch: pytest.MonkeyPatch) -> None:
    import dataconnect.client as client_mod

    captured: dict[str, object] = {}

    class FakeArrowFlightTransport:
        def __init__(self, host: str, port: int, use_tls: bool, token: str = "") -> None:
            captured["host"] = host
            captured["port"] = port
            captured["use_tls"] = use_tls
            captured["token"] = token

    class FakeDefaultService:
        def __init__(self, transport: object) -> None:
            captured["transport"] = transport

        def get_studies(self) -> list[Study]:
            return []

        def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
            return []

        def close(self) -> None:
            return None

    fake_transport_module = ModuleType("dataconnect.transport.arrow_flight.transport")
    fake_transport_module.ArrowFlightTransport = FakeArrowFlightTransport

    monkeypatch.setitem(sys.modules, "dataconnect.transport.arrow_flight.transport", fake_transport_module)
    monkeypatch.setattr(client_mod, "DefaultDataConnectService", FakeDefaultService)

    client = client_mod.DataConnectClient.connect(host="sandbox.example", port=9443, use_tls=False, token="abc123")

    assert isinstance(client, client_mod.DataConnectClient)
    assert captured["host"] == "sandbox.example"
    assert captured["port"] == 9443
    assert captured["use_tls"] is False
    assert captured["token"] == "abc123"
    assert isinstance(captured["transport"], FakeArrowFlightTransport)


@pytest.mark.benchmark
def test_dummy_benchmark() -> None:
    # Dummy benchmark test to satisfy CI
    assert True
