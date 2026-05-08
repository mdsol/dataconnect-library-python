"""Abstract service interface for DataConnect."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

import pandas as pd

from dataconnect.models import Study


class DataConnectService(ABC):
    """Abstract service interface — defines all operations available to the client."""

    @abstractmethod
    def get_studies(self) -> list[Study]: ...

    @abstractmethod
    def fetch_data(
        self,
        dataset_uuid: UUID,
        first_n_rows: int | None = None,
    ) -> pd.DataFrame: ...

    @abstractmethod
    def close(self) -> None: ...
