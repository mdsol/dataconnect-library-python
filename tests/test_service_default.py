# from __future__ import annotations

# import pytest

# from dataconnect.exceptions import ValidationError
# from dataconnect.service.default import DefaultDataConnectService
# from dataconnect.transport.models import DataRef, ResourceInfo, ResourceQuery


# class StubTransport:
#     def __init__(self, resources: list[ResourceInfo]) -> None:
#         self.resources = resources
#         self.last_request: ResourceQuery | None = None

#     def list_resources(self, request: ResourceQuery) -> list[ResourceInfo]:
#         self.last_request = request
#         return self.resources

#     def close(self) -> None:
#         return None


# def _study_resource(name: str = "Study A") -> ResourceInfo:
#     payload = (f'{{"uuid":"12345678-1234-1234-1234-123456789abc","name":"{name}","environments":[]}}').encode()

#     return ResourceInfo(
#         descriptor=b"",
#         endpoints=[DataRef(ticket=payload)],
#         total_records=1,
#         schema_bytes=b"",
#     )


# def test_get_studies_without_search_name_uses_empty_request_body() -> None:
#     transport = StubTransport(resources=[_study_resource()])
#     service = DefaultDataConnectService(transport)

#     studies = service.get_studies()

#     assert len(studies) == 1
#     assert studies[0].name == "Study A"
#     assert transport.last_request is not None
#     assert transport.last_request.action == "studies.list"
#     assert transport.last_request.body == ""


# def test_get_studies_with_search_name_sets_request_body() -> None:
#     transport = StubTransport(resources=[_study_resource("Cardio Study")])
#     service = DefaultDataConnectService(transport)

#     studies = service.get_studies(search_study_name="Cardio")

#     assert len(studies) == 1
#     assert studies[0].name == "Cardio Study"
#     assert transport.last_request is not None
#     assert transport.last_request.body == '{"search_study_name":"Cardio"}'


# def test_get_studies_rejects_non_string_search_name() -> None:
#     transport = StubTransport(resources=[])
#     service = DefaultDataConnectService(transport)

#     with pytest.raises(ValidationError, match="search_study_name must be a string"):
#         service.get_studies(search_study_name=123)  # type: ignore[arg-type]

#     assert transport.last_request is None


# def test_get_studies_accepts_none_search_name() -> None:
#     transport = StubTransport(resources=[_study_resource()])
#     service = DefaultDataConnectService(transport)

#     studies = service.get_studies(search_study_name=None)

#     assert len(studies) == 1
#     assert transport.last_request is not None
#     assert transport.last_request.body == ""
