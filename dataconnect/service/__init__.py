"""Service layer — public symbols re-exported for import convenience."""

from dataconnect.service.base import DataConnectService
from dataconnect.service.default import DefaultDataConnectService

__all__ = [
    "DataConnectService",
    "DefaultDataConnectService",
]
