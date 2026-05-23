"""Transport layer — public exports.

Transport errors (``transport/errors.py``) are intentionally NOT re-exported
here. They are internal to the transport layer and must not be caught by
user-facing code.
"""

from dataconnect.transport.base import Transport
from dataconnect.transport.models import (
    DataRef,
    DatasetTicket,
    DataTable,
    DryPublishResponse,
    PublishRequest,
    ResourceInfo,
    ResourceQuery,
)

__all__ = [
    "Transport",
    "ResourceQuery",
    "ResourceInfo",
    "DataRef",
    "DatasetTicket",
    "DataTable",
    "PublishRequest",
    "DryPublishResponse",
]
