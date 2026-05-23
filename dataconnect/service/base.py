"""Abstract service interface for DataConnect."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

import pandas as pd

from dataconnect.models import Dataset, DatasetVersion, DryPublishResult, PaginatedResponse, StudiesResult


class DataConnectService(ABC):
    """Abstract service interface — defines all operations available to the client."""

    @abstractmethod
    def get_studies(self, search_study_name: str | None = None) -> StudiesResult: ...

    @abstractmethod
    def get_datasets(
        self,
        study_environment_uuid: UUID,
        search_dataset_name: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[Dataset]: ...

    @abstractmethod
    def get_dataset_versions(self, dataset_uuid: UUID) -> list[DatasetVersion]: ...

    @abstractmethod
    def fetch_data(
        self,
        dataset_uuid: UUID,
        first_n_rows: int | None = None,
    ) -> pd.DataFrame: ...

    @abstractmethod
    def dry_publish(
        self,
        project_token: str,
        dataset_name: str,
        key_columns: list[str],
        source_datasets: list[UUID],
        data: pd.DataFrame,
        datetime_formats: dict[str, str] | None = None,
    ) -> DryPublishResult: ...

    @abstractmethod
    def close(self) -> None: ...
