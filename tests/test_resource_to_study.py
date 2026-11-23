from __future__ import annotations

import json
from uuid import UUID

from dataconnect.service.mappers import resource_to_study
from dataconnect.transport.models import DataRef, ResourceInfo


def _resource(payload: dict) -> ResourceInfo:
    return ResourceInfo(
        descriptor=b"",
        endpoints=[DataRef(ticket=json.dumps(payload).encode("utf-8"))],
        total_records=1,
        schema_bytes=b"",
    )


def test_resource_to_study_exposes_environment_oid() -> None:
    resource = _resource(
        {
            "uuid": "12345678-1234-1234-1234-123456789abc",
            "name": "Study A",
            "environments": [{"uuid": "11111111-1111-1111-1111-111111111111", "name": "Production", "oid": "prod"}],
        }
    )

    study = resource_to_study(resource)

    assert study.environments[0].oid == "prod"
    assert study.environments[0].name == "Production"
    assert study.environments[0].uuid == UUID("11111111-1111-1111-1111-111111111111")


def test_resource_to_study_oid_differs_from_name_multiple_environments() -> None:
    resource = _resource(
        {
            "uuid": "12345678-1234-1234-1234-123456789abc",
            "name": "Study A",
            "environments": [
                {"uuid": "11111111-1111-1111-1111-111111111111", "name": "Production", "oid": "prod"},
                {"uuid": "22222222-2222-2222-2222-222222222222", "name": "Custom Env", "oid": "other"},
            ],
        }
    )

    study = resource_to_study(resource)

    # OID must track its own environment, not be derived from name/uuid.
    assert study.environments[0].oid == "prod"
    assert study.environments[1].oid == "other"
    assert study.environments[1].name == "Custom Env"


def test_resource_to_study_missing_oid_defaults_to_none() -> None:
    """Older/partial server payloads without 'oid' must not break parsing."""
    resource = _resource(
        {
            "uuid": "12345678-1234-1234-1234-123456789abc",
            "name": "Study A",
            "environments": [{"uuid": "11111111-1111-1111-1111-111111111111", "name": "Production"}],
        }
    )

    study = resource_to_study(resource)

    assert study.environments[0].oid is None
