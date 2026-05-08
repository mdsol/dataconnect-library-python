"""Resource → domain model mappers.

Each function takes a transport-layer ``ResourceInfo`` and returns a public
domain model.  All wire-format knowledge (JSON encoding, field names, byte
decoding) is isolated here.
"""

from __future__ import annotations

import json
from uuid import UUID

import pandas as pd
import pyarrow as pa

from dataconnect.exceptions import NotFoundError
from dataconnect.models import Study, StudyEnvironment
from dataconnect.transport.models import ResourceInfo


def resource_to_study(resource: ResourceInfo) -> Study:
    """Parse a transport-layer ``ResourceInfo`` into a ``Study`` domain object."""

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError("Invalid resource: missing endpoints or ticket")

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return Study(
        uuid=UUID(data["uuid"]),
        name=data["name"],
        environments=[StudyEnvironment(uuid=UUID(e["uuid"]), name=e["name"]) for e in data.get("environments", [])],
    )


def resource_to_fetched_data(resource: ResourceInfo) -> pd.DataFrame:
    """Parse a transport-layer ``ResourceInfo`` into pandas DataFrame.

    The ticket bytes are expected to contain an Arrow IPC stream.  They are
    read via ``pyarrow.ipc.open_stream`` and converted to a ``pd.DataFrame``.
    """

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError("Invalid resource: missing endpoints or ticket")

    ticket_bytes = resource.endpoints[0].ticket
    buf = pa.BufferReader(ticket_bytes)
    reader = pa.ipc.open_stream(buf)
    return reader.read_all().to_pandas()
