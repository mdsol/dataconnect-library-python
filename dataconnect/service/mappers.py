"""Resource → domain model mappers.

Each function takes a transport-layer ``ResourceInfo`` and returns a public
domain model.  All wire-format knowledge (JSON encoding, field names, byte
decoding) is isolated here.
"""

from __future__ import annotations

import json
from uuid import UUID

from dataconnect.models import Study, StudyEnvironment
from dataconnect.transport.models import ResourceInfo


def resource_to_study(resource: ResourceInfo) -> Study:
    """Parse a transport-layer ``ResourceInfo`` into a ``Study`` domain object."""

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return Study(
        uuid=UUID(data["uuid"]),
        name=data["name"],
        environments=[StudyEnvironment(uuid=UUID(e["uuid"]), name=e["name"]) for e in data.get("environments", [])],
    )
