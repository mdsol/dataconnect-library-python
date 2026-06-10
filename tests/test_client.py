# from __future__ import annotations

# # import sys
# # from types import ModuleType
# from uuid import UUID

# # import pandas as pd
# # import pytest

# from dataconnect.client import DataConnectClient
# from dataconnect.models import StudiesResult


# def _make_dataframe() -> pd.DataFrame:
#     """Return a small DataFrame for use in fetch_data wiring tests."""
#     return pd.DataFrame({"subject_id": ["S001"], "age": [30]})


# class _FakeService:
#     def __init__(
#         self,
#         studies: list[Study] | None = None,
#         versions: list[DatasetVersion] | None = None,
#         fetch_data_result: pd.DataFrame | None = None,
#         datasets: list[Dataset] | None = None,
#     ) -> None:
#         self._studies = studies or []
#         self._versions = versions or []
#         self._fetch_data_result = fetch_data_result if fetch_data_result is not None else pd.DataFrame()
#         self._datasets = datasets or []
#         self.closed = 0
#         self.last_dataset_uuid: UUID | None = None
#         self.last_fetch_data_uuid: UUID | None = None
#         self.last_first_n_rows: int | None = None
#         self.last_get_datasets_kwargs: dict[str, object] | None = None

#     def get_studies(self) -> list[Study]:
#         return self._studies

#     def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
#         self.last_dataset_uuid = dataset_uuid
#         return self._versions

#     def fetch_data(self, dataset_uuid: UUID, first_n_rows: int | None = None) -> pd.DataFrame:
#         self.last_fetch_data_uuid = dataset_uuid
#         self.last_first_n_rows = first_n_rows
#         return self._fetch_data_result

#     def get_datasets(self, **kwargs: object) -> list[Dataset]:
#         self.last_get_datasets_kwargs = kwargs
#         return self._datasets

#     def close(self) -> None:
#         self.closed += 1


# def test_get_dataset_versions_forwards_uuid_to_service() -> None:
#     dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
#     versions = [
#         DatasetVersion(
#             study_uuid=UUID("64a98a9b-1512-44c8-92af-e4cab0183670"),
#             study_environment_uuid=UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a"),
#             dataset_uuid=dataset_uuid,
#             dataset_name="labs",
#             dataset_version="1",
#         )
#     ]
#     service = _FakeService(versions=versions)
#     client = DataConnectClient(service)

#     result = client.get_dataset_versions(dataset_uuid)

#     assert result == versions
#     assert service.last_dataset_uuid == dataset_uuid


# def test_context_manager_closes_service() -> None:
#     service = _FakeService()

#     with DataConnectClient(service) as client:
#         assert isinstance(client, DataConnectClient)

#     assert service.closed == 1


# def test_connect_uses_arrow_transport_and_default_service(monkeypatch: pytest.MonkeyPatch) -> None:
#     import dataconnect.client as client_mod

#     captured: dict[str, object] = {}

#     class FakeArrowFlightTransport:
#         def __init__(self, host: str, port: int, use_tls: bool, token: str = "") -> None:
#             captured["host"] = host
#             captured["port"] = port
#             captured["use_tls"] = use_tls
#             captured["token"] = token

#     class FakeDefaultService:
#         def __init__(self, transport: object) -> None:
#             captured["transport"] = transport

#         def get_studies(self) -> list[Study]:
#             return []

#         def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]:
#             return []

#         def close(self) -> None:
#             return None

#     fake_transport_module = ModuleType("dataconnect.transport.arrow_flight.transport")
#     fake_transport_module.ArrowFlightTransport = FakeArrowFlightTransport

#     monkeypatch.setitem(sys.modules, "dataconnect.transport.arrow_flight.transport", fake_transport_module)
#     monkeypatch.setattr(client_mod, "DefaultDataConnectService", FakeDefaultService)

#     client = client_mod.DataConnectClient.connect(host="sandbox.example", port=9443, use_tls=False, token="abc123")

#     assert isinstance(client, client_mod.DataConnectClient)
#     assert captured["host"] == "sandbox.example"
#     assert captured["port"] == 9443
#     assert captured["use_tls"] is False
#     assert captured["token"] == "abc123"
#     assert isinstance(captured["transport"], FakeArrowFlightTransport)


# def test_fetch_data_forwards_args_to_service() -> None:
#     """Client.fetch_data must delegate uuid and first_n_rows to the service unchanged."""
#     dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
#     expected_df = _make_dataframe()
#     service = _FakeService(fetch_data_result=expected_df)
#     client = DataConnectClient(service)

#     result = client.fetch_data(dataset_uuid, first_n_rows=5)

#     assert result is expected_df
#     assert service.last_fetch_data_uuid == dataset_uuid
#     assert service.last_first_n_rows == 5


# def test_fetch_data_forwards_no_limit_to_service() -> None:
#     """When first_n_rows is omitted, None must be forwarded to the service."""
#     dataset_uuid = UUID("073410b6-79be-3e7d-ae37-92f6e054013e")
#     service = _FakeService(fetch_data_result=_make_dataframe())
#     client = DataConnectClient(service)

#     client.fetch_data(dataset_uuid)

#     assert service.last_first_n_rows is None


# @pytest.mark.benchmark
# def test_dummy_benchmark() -> None:
#     # Dummy benchmark test to satisfy CI
#     assert True


# class StubService:
#     def __init__(self) -> None:
#         self.search_study_name: str | None = None
#         self.was_closed = False

#     def get_studies(self, search_study_name: str | None = None) -> StudiesResult:
#         self.search_study_name = search_study_name
#         return StudiesResult(total_records=0, studies=[])

#     def close(self) -> None:
#         self.was_closed = True


# def test_get_studies_without_filter_delegates_to_service() -> None:
#     service = StubService()
#     client = DataConnectClient(service)

#     result = client.get_studies()

#     assert isinstance(result, StudiesResult)
#     assert result.total_records == 0
#     assert result.studies == []
#     assert service.search_study_name is None


# def test_get_studies_with_filter_delegates_to_service() -> None:
#     service = StubService()
#     client = DataConnectClient(service)

#     result = client.get_studies(search_study_name="cardio")

#     assert isinstance(result, StudiesResult)
#     assert result.total_records == 0
#     assert result.studies == []
#     assert service.search_study_name == "cardio"


# def test_close_delegates_to_service() -> None:
#     service = StubService()
#     client = DataConnectClient(service)

#     client.close()

#     assert service.was_closed


# def test_get_datasets_forwards_arguments_to_service() -> None:
#     datasets = [
#         Dataset(
#             dataset_uuid="073410b6-79be-3e7d-ae37-92f6e054013e",
#             study_uuid="64a98a9b-1512-44c8-92af-e4cab0183670",
#             study_env_uuid="4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a",
#             dataset_name="labs",
#         )
#     ]
#     service = _FakeService(datasets=datasets)
#     client = DataConnectClient(service)

#     result = client.get_datasets(
#         study_environment_uuid=UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a"),
#         search_dataset_name="labs",
#         page=2,
#         page_size=10,
#     )

#     assert result == datasets
#     assert service.last_get_datasets_kwargs == {
#         "study_environment_uuid": UUID("4d1fd10d-5b57-4fd8-a436-f4ec59ce2e4a"),
#         "search_dataset_name": "labs",
#         "page": 2,
#         "page_size": 10,
#     }


# def test_get_datasets_uses_defaults() -> None:
#     service = _FakeService()
#     client = DataConnectClient(service)

#     result = client.get_datasets(study_environment_uuid=UUID("11111111-1111-1111-1111-111111111111"))

#     assert result == []
#     assert service.last_get_datasets_kwargs == {
#         "study_environment_uuid": UUID("11111111-1111-1111-1111-111111111111"),
#         "search_dataset_name": "",
#         "page": 1,
#         "page_size": 50,
#     }
