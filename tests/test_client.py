from __future__ import annotations

from dataconnect.client import DataConnectClient
from dataconnect.models import Study


class StubService:
    def __init__(self) -> None:
        self.search_study_name: str | None = None
        self.was_closed = False

    def get_studies(self, search_study_name: str | None = None) -> list[Study]:
        self.search_study_name = search_study_name
        return []

    def close(self) -> None:
        self.was_closed = True


def test_get_studies_without_filter_delegates_to_service() -> None:
    service = StubService()
    client = DataConnectClient(service)

    studies = client.get_studies()

    assert studies == []
    assert service.search_study_name is None


def test_get_studies_with_filter_delegates_to_service() -> None:
    service = StubService()
    client = DataConnectClient(service)

    studies = client.get_studies(search_study_name="cardio")

    assert studies == []
    assert service.search_study_name == "cardio"


def test_close_delegates_to_service() -> None:
    service = StubService()
    client = DataConnectClient(service)

    client.close()

    assert service.was_closed
