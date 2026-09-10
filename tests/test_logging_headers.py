"""Unit tests for ArrowFlightTransport request headers injection."""

from __future__ import annotations

import importlib.metadata
from unittest.mock import MagicMock, patch

import pytest

from dataconnect.client import DataConnectClient

# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


@patch("pyarrow.flight.FlightClient")
def test_connect_injects_all_required_logging_headers(mock_flight_client: MagicMock) -> None:
    test_uuid = "enodia-user-uuid-12345"
    test_token = "some-bearer-token"
    mocked_sdk_version = "v1.2.3-test"

    with patch("dataconnect.transport.arrow_flight.transport.version", return_value=mocked_sdk_version):
        client = DataConnectClient.connect(
            host="localhost",
            port=8888,
            use_tls=False,
            token=test_token,
            user_uuid=test_uuid,
        )

    transport = client._service._transport
    headers_dict = dict(transport._call_headers)

    # AC-02 & AC-03: SDK Version & SDK Type consistency combined for Server Middleware
    assert b"x-client-dataconnect" in headers_dict
    assert headers_dict[b"x-client-dataconnect"] == b"Python_SDK;v1.2.3-test;"

    # Check that existing auth token logic is preserved
    assert b"authorization" in headers_dict
    assert headers_dict[b"authorization"] == f"Bearer {test_token}".encode()


@pytest.mark.parametrize("simulated_version", ["0.5.0", "2.0.0-alpha"])
@patch("pyarrow.flight.FlightClient")
def test_sdk_type_remains_python_across_different_sdk_versions(
    mock_flight_client: MagicMock, simulated_version: str
) -> None:
    with patch("dataconnect.transport.arrow_flight.transport.version", return_value=simulated_version):
        client = DataConnectClient.connect(
            host="localhost",
            port=8888,
            use_tls=False,
            user_uuid="dummy-uuid",
        )

    transport = client._service._transport
    headers_dict = dict(transport._call_headers)

    expected_client_info = f"Python_SDK;{simulated_version};".encode()
    assert headers_dict[b"x-client-dataconnect"] == expected_client_info


@patch("pyarrow.flight.FlightClient")
def test_sdk_version_falls_back_on_package_not_found_error(mock_flight_client: MagicMock) -> None:
    """AC-02: Checks if the version falls back to 0.1.0 when package metadata is missing.."""
    with patch(
        "dataconnect.transport.arrow_flight.transport.version", side_effect=importlib.metadata.PackageNotFoundError
    ):
        client = DataConnectClient.connect(
            host="localhost",
            port=8888,
            use_tls=False,
            user_uuid="dummy-uuid",
        )

    transport = client._service._transport
    headers_dict = dict(transport._call_headers)

    assert b"x-client-dataconnect" in headers_dict
    assert headers_dict[b"x-client-dataconnect"] == b"Python_SDK;0.1.0;"
