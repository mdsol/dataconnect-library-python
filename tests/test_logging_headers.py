"""Unit tests for ArrowFlightTransport request headers injection."""

from __future__ import annotations

import importlib.metadata
import socket
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

    # AC-01: User UUID
    assert b"user-uuid" in headers_dict
    assert headers_dict[b"user-uuid"] == b"enodia-user-uuid-12345"

    # AC-02 & AC-03: SDK Version & SDK Type consistency
    assert b"python-sdk-version" in headers_dict
    assert headers_dict[b"python-sdk-version"] == b"v1.2.3-test"
    assert b"sdk-type" in headers_dict
    assert headers_dict[b"sdk-type"] == b"Python"

    # AC-04: Client IP Address validation
    assert b"client-ip" in headers_dict
    try:
        socket.inet_aton(headers_dict[b"client-ip"].decode("utf-8"))
        ip_is_valid = True
    except OSError:
        ip_is_valid = False
    assert ip_is_valid

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

    assert headers_dict[b"python-sdk-version"] == simulated_version.encode("utf-8")
    assert headers_dict[b"sdk-type"] == b"Python"


# ---------------------------------------------------------------------------
# Edge cases & Error handling
# ---------------------------------------------------------------------------


@patch("pyarrow.flight.FlightClient")
def test_client_ip_falls_back_to_localhost_on_socket_error(mock_flight_client: MagicMock) -> None:
    """AC-04: Verifică dacă IP-ul face fallback pe 127.0.0.1 când mașina e offline."""
    with (
        patch("socket.socket.connect", side_effect=OSError("No network")),
        patch("dataconnect.transport.arrow_flight.transport.version", return_value="1.0.0"),
    ):
        client = DataConnectClient.connect(
            host="localhost",
            port=8888,
            use_tls=False,
            user_uuid="dummy-uuid",
        )

    transport = client._service._transport
    headers_dict = dict(transport._call_headers)

    assert b"client-ip" in headers_dict
    assert headers_dict[b"client-ip"] == b"127.0.0.1"


@patch("pyarrow.flight.FlightClient")
def test_sdk_version_falls_back_on_package_not_found_error(mock_flight_client: MagicMock) -> None:
    """AC-02: Verifică dacă versiunea face fallback pe 0.1.0 când metadatele pachetului lipsesc."""
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        client = DataConnectClient.connect(
            host="localhost",
            port=8888,
            use_tls=False,
            user_uuid="dummy-uuid",
        )

    transport = client._service._transport
    headers_dict = dict(transport._call_headers)

    assert b"python-sdk-version" in headers_dict
    assert headers_dict[b"python-sdk-version"] == b"0.1.0"
