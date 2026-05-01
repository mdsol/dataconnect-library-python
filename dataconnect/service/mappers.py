"""Resource → domain model mappers.

Each function takes a transport-layer ``ResourceInfo`` and returns a public
domain model.  All wire-format knowledge (JSON encoding, field names, byte
decoding) is isolated here.
"""

from __future__ import annotations

import json
from uuid import UUID

from dataconnect.exceptions import NotFoundError
from dataconnect.models import Dataset, DatasetVersion, Study, StudyEnvironment
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


def resource_to_dataset_version(resource: ResourceInfo) -> DatasetVersion:
    """Parse a transport-layer ``ResourceInfo`` into a ``DatasetVersion`` domain object."""

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError("Invalid resource: missing endpoints or ticket")

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return DatasetVersion(
        study_uuid=UUID(data["study_uuid"]),
        study_environment_uuid=UUID(data["study_env_uuid"]),
        dataset_uuid=UUID(data["dataset_uuid"]),
        dataset_name=data["dataset_name"],
        dataset_version=data["dataset_version"],
    )


def resource_to_dataset(resource: ResourceInfo) -> Dataset:
    """Parse a transport-layer ``ResourceInfo`` into a ``Dataset`` domain object."""

    if not resource or not resource.endpoints or not resource.endpoints[0].ticket:
        raise NotFoundError("Invalid resource: missing endpoints or ticket")

    data = json.loads(resource.endpoints[0].ticket.decode("utf-8"))

    return Dataset(
        dataset_uuid=data.get("dataset_uuid", ""),
        study_uuid=data.get("study_uuid", ""),
        study_env_uuid=data.get("study_env_uuid", ""),
        dataset_name=data.get("dataset_name", ""),
    )
