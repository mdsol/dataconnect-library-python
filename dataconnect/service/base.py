"""Abstract service interface for DataConnect."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dataconnect.models import Study


class DataConnectService(ABC):
    """Abstract service interface — defines all operations available to the client."""

    @abstractmethod
    def get_studies(self) -> list[Study]: ...

    @abstractmethod
    def close(self) -> None: ...
