"""Abstract service interface for DataConnect."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from dataconnect.models import DatasetVersion, Study


class DataConnectService(ABC):
    """Abstract service interface — defines all operations available to the client."""

    @abstractmethod
    def get_studies(self, search_study_name: str | None = None) -> list[Study]: ...

    @abstractmethod
    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]: ...

    @abstractmethod
    def close(self) -> None: ...
