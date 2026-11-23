"""Publish envelopes captured verbatim from the Arrow Flight server.

Source: data_connect_arrow_integration, ``app/tests/test_publish_envelope_contract.py``
(MCC-1533427).  Regenerate rather than hand-edit if the server contract changes,
so the SDK is always tested against bytes the server really produces.
"""

from __future__ import annotations

FAILED_DRY_PUBLISH_ENVELOPE: dict = {
    "success": False,
    "metadata": {
        "dataset_name": "PP_0726_1",
        "dataset_version": 0,
        "column_count": 13,
        "dataset_uuid": None,
        "dataset_batch_number": None,
    },
    "metrics": {
        "total_valid_rows": 36042,
        "total_invalid_rows": 4,
        "total_duplicate_rows": 2,
    },
    "checks": {
        "schema_is_valid": True,
        "config_is_valid": True,
        "date_formats_are_valid": False,
        "dataset_is_valid": True,
        "invalid_datetime_formats": {"lbdat_int": "yyyy-MM-dd"},
    },
    "errors": ["Missing datetime formats for date/timestamp columns: lbdat_int"],
    "invalid_records": [],
}

PASSED_DRY_PUBLISH_ENVELOPE: dict = {
    "success": True,
    "metadata": {
        "dataset_name": "PP_0726_1",
        "dataset_version": 1,
        "column_count": 13,
        "dataset_uuid": None,
        "dataset_batch_number": None,
    },
    "metrics": {
        "total_valid_rows": 36042,
        "total_invalid_rows": 0,
        "total_duplicate_rows": 0,
    },
    "checks": {
        "schema_is_valid": True,
        "config_is_valid": True,
        "date_formats_are_valid": True,
        "dataset_is_valid": True,
        "invalid_datetime_formats": {},
    },
    "errors": [],
    "invalid_records": [],
}

PUBLISH_ENVELOPE: dict = {
    "success": True,
    "metadata": {
        "dataset_name": "PP_0726_1",
        "dataset_version": 1,
        "column_count": 13,
        "dataset_uuid": "6f5a4e1c-0000-4a2b-9d3e-2f1c8b7a6d55",
        "dataset_batch_number": 1,
    },
    "metrics": {
        "total_valid_rows": 36042,
        "total_invalid_rows": 0,
        "total_duplicate_rows": 0,
    },
    "checks": {
        "schema_is_valid": True,
        "config_is_valid": True,
        "date_formats_are_valid": True,
        "dataset_is_valid": True,
        "invalid_datetime_formats": {},
    },
    "errors": [],
    "invalid_records": [],
}
