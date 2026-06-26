"""Unit tests for the ``get_datetime_formats`` feature.

Covers:
- ``DatetimeFormatsResult``                              (domain model helpers)
- ``DefaultDataConnectService.get_datetime_formats``     (service layer)
- ``ArrowFlightTransport.get_datetime_formats``          (transport layer)
- ``DataConnectClient.get_datetime_formats``             (client façade)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from dataconnect.client import DataConnectClient
from dataconnect.exceptions import ValidationError
from dataconnect.models import DatetimeFormat, DatetimeFormatsResult
from dataconnect.service.default import DefaultDataConnectService
from dataconnect.transport.arrow_flight.transport import ArrowFlightTransport
from dataconnect.transport.base import Transport
from dataconnect.transport.errors import TransportValidationError
from dataconnect.transport.models import (
    DatasetTicket,
    DataTable,
    DatetimeFormatsRequest,
    DryPublishResponse,
    PublishRequest,
    PublishResponse,
    ResourceInfo,
    ResourceQuery,
)

# ---------------------------------------------------------------------------
# Shared fixtures / stubs
# ---------------------------------------------------------------------------


_SAMPLE_FORMATS: list[str] = [
    "yyyy-MM-dd",
    "MM/dd/yyyy",
    "yyyy-MM-dd HH:mm:ss",
    "yyyy-MM-dd'T'HH:mm:ssXXX",
]


class _StubTransport(Transport):
    """Minimal stub that satisfies the Transport ABC for get_datetime_formats tests."""

    def __init__(
        self,
        formats: list[str] | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._formats = formats if formats is not None else list(_SAMPLE_FORMATS)
        self._raise = raise_error
        self.last_request: DatetimeFormatsRequest | None = None

    def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
        return []

    def get_ticket(self, ticket: DatasetTicket) -> DataTable:
        raise NotImplementedError

    def dry_publish_dataset(self, publish_request: PublishRequest) -> DryPublishResponse:
        raise NotImplementedError

    def publish_dataset(self, publish_request: PublishRequest) -> PublishResponse:
        raise NotImplementedError

    def get_datetime_formats(self, request: DatetimeFormatsRequest) -> list[str]:
        self.last_request = request
        if self._raise is not None:
            raise self._raise
        return self._formats

    def close(self) -> None:
        pass


def _make_service(
    formats: list[str] | None = None,
    raise_error: Exception | None = None,
) -> tuple[DefaultDataConnectService, _StubTransport]:
    transport = _StubTransport(formats=formats, raise_error=raise_error)
    return DefaultDataConnectService(transport), transport


# ---------------------------------------------------------------------------
# DatetimeFormatsResult — domain model helpers
# ---------------------------------------------------------------------------


class TestDatetimeFormatsResult:
    """``DatetimeFormatsResult.all/dates/datetimes`` must return the correct
    views without mutating the underlying list.
    """

    def _make(self) -> DatetimeFormatsResult:
        return DatetimeFormatsResult(
            formats=[
                DatetimeFormat(format="yyyy-MM-dd", type="date"),
                DatetimeFormat(format="MM/dd/yyyy", type="date"),
                DatetimeFormat(format="yyyy-MM-dd HH:mm:ss", type="datetime"),
                DatetimeFormat(format="yyyy-MM-dd'T'HH:mm:ssXXX", type="datetime"),
            ]
        )

    def test_all_returns_every_format_object(self) -> None:
        result = self._make()
        items = result.all()
        assert len(items) == 4
        assert all(isinstance(item, DatetimeFormat) for item in items)
        assert [item.format for item in items] == [
            "yyyy-MM-dd",
            "MM/dd/yyyy",
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm:ssXXX",
        ]

    def test_all_returns_a_copy_not_the_internal_list(self) -> None:
        result = self._make()
        items = result.all()
        items.pop()
        assert len(result.all()) == 4

    def test_dates_returns_only_date_format_strings(self) -> None:
        result = self._make()
        assert result.dates() == ["yyyy-MM-dd", "MM/dd/yyyy"]

    def test_datetimes_returns_only_datetime_format_strings(self) -> None:
        result = self._make()
        assert result.datetimes() == [
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm:ssXXX",
        ]

    def test_dates_returns_list_of_strings(self) -> None:
        result = self._make()
        assert all(isinstance(fmt, str) for fmt in result.dates())

    def test_datetimes_returns_list_of_strings(self) -> None:
        result = self._make()
        assert all(isinstance(fmt, str) for fmt in result.datetimes())

    def test_empty_result_methods_return_empty_lists(self) -> None:
        result = DatetimeFormatsResult(formats=[])
        assert result.all() == []
        assert result.dates() == []
        assert result.datetimes() == []

    def test_default_formats_is_empty_list_and_not_shared(self) -> None:
        a = DatetimeFormatsResult()
        b = DatetimeFormatsResult()
        a.formats.append(DatetimeFormat(format="yyyy", type="date"))
        assert b.formats == []


# ---------------------------------------------------------------------------
# DefaultDataConnectService.get_datetime_formats
# ---------------------------------------------------------------------------


class TestServiceGetDatetimeFormats:
    """``DefaultDataConnectService.get_datetime_formats`` must validate the
    ``format_type`` filter, forward the request to the transport, and classify
    each returned format.
    """

    def test_returns_datetime_formats_result_instance(self) -> None:
        service, _ = _make_service()
        result = service.get_datetime_formats(project_token="tok")
        assert isinstance(result, DatetimeFormatsResult)

    def test_default_format_type_is_all(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="tok")
        assert transport.last_request is not None
        assert transport.last_request.format_type == "all"

    def test_project_token_forwarded_to_transport(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="abc123", format_type="all")
        assert transport.last_request is not None
        assert transport.last_request.project_token == "abc123"

    def test_format_type_date_forwarded_to_transport(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="tok", format_type="date")
        assert transport.last_request is not None
        assert transport.last_request.format_type == "date"

    def test_format_type_datetime_forwarded_to_transport(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="tok", format_type="datetime")
        assert transport.last_request is not None
        assert transport.last_request.format_type == "datetime"

    def test_format_type_is_normalised_case_insensitively(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="tok", format_type="DATE")
        assert transport.last_request is not None
        assert transport.last_request.format_type == "date"

    def test_format_type_is_normalised_with_whitespace(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="tok", format_type="  Datetime  ")
        assert transport.last_request is not None
        assert transport.last_request.format_type == "datetime"

    def test_empty_string_format_type_is_treated_as_all(self) -> None:
        service, transport = _make_service()
        service.get_datetime_formats(project_token="tok", format_type="")
        assert transport.last_request is not None
        assert transport.last_request.format_type == "all"

    # --- response classification ---

    def test_result_preserves_server_order(self) -> None:
        service, _ = _make_service()
        result = service.get_datetime_formats(project_token="tok")
        assert [f.format for f in result.formats] == _SAMPLE_FORMATS

    def test_date_only_formats_classified_as_date(self) -> None:
        service, _ = _make_service(formats=["yyyy-MM-dd", "MM/dd/yyyy"])
        result = service.get_datetime_formats(project_token="tok", format_type="date")
        assert [f.type for f in result.formats] == ["date", "date"]

    def test_formats_with_time_component_classified_as_datetime(self) -> None:
        service, _ = _make_service(
            formats=["yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ssXXX"],
        )
        result = service.get_datetime_formats(project_token="tok", format_type="datetime")
        assert [f.type for f in result.formats] == ["datetime", "datetime"]

    def test_mixed_classification_when_format_type_is_all(self) -> None:
        service, _ = _make_service()  # uses _SAMPLE_FORMATS
        result = service.get_datetime_formats(project_token="tok", format_type="all")
        assert [f.type for f in result.formats] == [
            "date",
            "date",
            "datetime",
            "datetime",
        ]

    def test_filter_helpers_work_on_service_result(self) -> None:
        service, _ = _make_service()
        result = service.get_datetime_formats(project_token="tok")
        assert result.dates() == ["yyyy-MM-dd", "MM/dd/yyyy"]
        assert result.datetimes() == [
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm:ssXXX",
        ]

    def test_empty_server_response_yields_empty_result(self) -> None:
        service, _ = _make_service(formats=[])
        result = service.get_datetime_formats(project_token="tok")
        assert result.all() == []
        assert result.dates() == []
        assert result.datetimes() == []

    # --- invalid input ---

    @pytest.mark.parametrize("bad_type", ["NA", "invalid", "datetimes", "DATETIMEZ", "1"])
    def test_invalid_format_type_raises_validation_error(self, bad_type: str) -> None:
        service, transport = _make_service()
        with pytest.raises(ValidationError):
            service.get_datetime_formats(project_token="tok", format_type=bad_type)
        # Transport must not be invoked when validation fails up-front.
        assert transport.last_request is None

    # --- error translation ---

    def test_transport_validation_error_is_translated_to_service_error(self) -> None:
        err = TransportValidationError(
            error_code="VAL_008",
            message="invalid project token",
            timestamp="2024-01-01T00:00:00Z",
        )
        service, _ = _make_service(raise_error=err)
        with pytest.raises(ValidationError):
            service.get_datetime_formats(project_token="bad", format_type="all")


# ---------------------------------------------------------------------------
# ArrowFlightTransport.get_datetime_formats
# ---------------------------------------------------------------------------


def _make_flight_transport() -> ArrowFlightTransport:
    """Create an ``ArrowFlightTransport`` with a mocked ``FlightClient``."""
    with patch.object(ArrowFlightTransport, "_get_client", return_value=MagicMock()):
        return ArrowFlightTransport(host="localhost", port=5005, use_tls=False)


def _make_action_result(payload: list[str]) -> MagicMock:
    body = MagicMock()
    body.to_pybytes.return_value = json.dumps(payload).encode("utf-8")
    result = MagicMock()
    result.body = body
    return result


class TestTransportGetDatetimeFormats:
    """``ArrowFlightTransport.get_datetime_formats`` must encode the request as a
    Flight ``Action`` and decode the JSON response.
    """

    def test_action_type_is_get_datetime_formats(self) -> None:
        transport = _make_flight_transport()
        transport._client.do_action.return_value = iter([_make_action_result(_SAMPLE_FORMATS)])

        transport.get_datetime_formats(DatetimeFormatsRequest(project_token="tok", format_type="all"))

        action_arg = transport._client.do_action.call_args[0][0]
        assert action_arg.type == "get_datetime_formats"

    def test_action_body_contains_project_token_and_type(self) -> None:
        transport = _make_flight_transport()
        transport._client.do_action.return_value = iter([_make_action_result(_SAMPLE_FORMATS)])

        transport.get_datetime_formats(DatetimeFormatsRequest(project_token="my_token", format_type="datetime"))

        action_arg = transport._client.do_action.call_args[0][0]
        body = json.loads(action_arg.body.to_pybytes().decode("utf-8"))
        assert body == {"project_token": "my_token", "type": "datetime"}

    def test_returns_decoded_format_list(self) -> None:
        transport = _make_flight_transport()
        transport._client.do_action.return_value = iter([_make_action_result(_SAMPLE_FORMATS)])

        result = transport.get_datetime_formats(DatetimeFormatsRequest(project_token="tok", format_type="all"))

        assert result == _SAMPLE_FORMATS

    def test_empty_result_iterator_returns_empty_list(self) -> None:
        transport = _make_flight_transport()
        transport._client.do_action.return_value = iter([])

        result = transport.get_datetime_formats(DatetimeFormatsRequest(project_token="tok", format_type="all"))

        assert result == []

    def test_underlying_exception_is_translated_to_transport_error(self) -> None:
        from dataconnect.transport.errors import TransportError

        transport = _make_flight_transport()
        transport._client.do_action.side_effect = RuntimeError("boom")

        with pytest.raises(TransportError):
            transport.get_datetime_formats(DatetimeFormatsRequest(project_token="tok", format_type="all"))


# ---------------------------------------------------------------------------
# DataConnectClient.get_datetime_formats (façade)
# ---------------------------------------------------------------------------


class _FakeService:
    """Minimal fake service to verify the client delegates correctly."""

    def __init__(self, return_value: DatetimeFormatsResult | None = None) -> None:
        self._return = return_value or DatetimeFormatsResult(formats=[DatetimeFormat(format="yyyy-MM-dd", type="date")])
        self.calls: list[dict] = []

    def get_datetime_formats(self, **kwargs: object) -> DatetimeFormatsResult:
        self.calls.append(kwargs)
        return self._return

    # Unused service methods — must exist to satisfy the implicit protocol used
    # by DataConnectClient.

    def get_studies(self, **kwargs: object) -> None:  # type: ignore[return]
        pass

    def get_datasets(self, **kwargs: object) -> None:  # type: ignore[return]
        pass

    def get_dataset_versions(self, **kwargs: object) -> None:  # type: ignore[return]
        pass

    def fetch_data(self, **kwargs: object) -> None:  # type: ignore[return]
        pass

    def dry_publish(self, **kwargs: object) -> None:  # type: ignore[return]
        pass

    def publish(self, **kwargs: object) -> None:  # type: ignore[return]
        pass

    def close(self) -> None:
        pass


class TestClientGetDatetimeFormats:
    """``DataConnectClient.get_datetime_formats`` must delegate to the service."""

    def test_returns_datetime_formats_result(self) -> None:
        service = _FakeService()
        client = DataConnectClient(service)  # type: ignore[arg-type]
        result = client.get_datetime_formats(project_token="tok")
        assert isinstance(result, DatetimeFormatsResult)

    def test_default_format_type_is_all(self) -> None:
        service = _FakeService()
        client = DataConnectClient(service)  # type: ignore[arg-type]
        client.get_datetime_formats(project_token="tok")
        assert service.calls == [{"project_token": "tok", "format_type": "all"}]

    def test_format_type_is_forwarded(self) -> None:
        service = _FakeService()
        client = DataConnectClient(service)  # type: ignore[arg-type]
        client.get_datetime_formats(project_token="tok", format_type="datetime")
        assert service.calls == [{"project_token": "tok", "format_type": "datetime"}]

    def test_result_from_service_is_returned_unchanged(self) -> None:
        expected = DatetimeFormatsResult(formats=[DatetimeFormat(format="yyyy-MM-dd HH:mm", type="datetime")])
        service = _FakeService(return_value=expected)
        client = DataConnectClient(service)  # type: ignore[arg-type]
        result = client.get_datetime_formats(project_token="tok", format_type="datetime")
        assert result is expected
