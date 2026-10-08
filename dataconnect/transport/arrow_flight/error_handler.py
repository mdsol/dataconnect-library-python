"""Arrow Flight error parsing and normalization utilities.

Provides functions to extract structured error information from raw Arrow
Flight / gRPC / Arrow Flight Server exception messages and translate them
into transport-layer ``TransportError`` subtypes.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from ..errors import (
    ErrorDetail,
    TransportAuthenticationError,
    TransportAuthorizationError,
    TransportError,
    TransportNotFoundError,
    TransportServerError,
    TransportValidationError,
)


def _extract_json_object(text: str) -> str:
    """Extract the first complete JSON object from *text*, returning it as a string.

    Handles common escaping artifacts found in Arrow Flight error payloads.
    Returns *text* unchanged if no ``{`` brace is found or if braces are
    unbalanced.
    """
    # Unescape excessive backslash-quote sequences and single-quote escapes
    text = text.replace('\\"', '"')
    text = re.sub(r"(?<!\\)\\'", "'", text)

    first_brace = text.find("{")
    if first_brace < 0:
        return text

    brace_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[first_brace:], start=first_brace):
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[first_brace : i + 1]

    return text


_AUTH_DETAIL_MSG = (
    "Ensure you provide the correct user authentication "
    "token. The user token must be valid and generated "
    "from the SDK Key Management page in iMedidata > "
    "Data Connect > Developer Center."
)

_AUTH_HOST_MSG = (
    "Verify that the host URL is correct and that your network "
    "allows outbound connections to the specified host and port."
)

_RATE_LIMIT_DETAIL_MSG = "Wait before making more requests."

_ENODIA_PATTERN = re.compile(
    r"FlightUnauthenticatedError|Flight returned unauthenticated error|Flight returned unavailable error",
    re.IGNORECASE,
)

_SERVER_MSG_RE = re.compile(r"with message:\s*(.+)", re.IGNORECASE)


def _normalize_enodia_error(error_message: str) -> str:
    """Normalize an Enodia authentication error string into ``PREFIX::JSON`` format.

    Detects Arrow Flight unauthenticated error messages produced by the Enodia
    gateway and converts them into a structured ``ERROR_CODE::{...}`` string
    that ``parse_dataconnect_error`` can parse uniformly.

    Returns *error_message* unchanged if it is not an Enodia auth error or if
    normalization fails.
    """
    try:
        if not _ENODIA_PATTERN.search(error_message):
            return error_message

        # Extract server message after "with message: "
        server_msg: str | None = None

        m = _SERVER_MSG_RE.search(error_message)

        if m:
            raw = m.group(1)
            raw = re.sub(r"\. gRPC client debug context:.*$", "", raw)
            raw = re.sub(r"\. Client context:.*$", "", raw)
            server_msg = raw.strip()

        payload_field = "token"

        if server_msg:
            if re.search("authorization header not present", server_msg, re.IGNORECASE):
                error_code = "AUTH_E_001"
                clean_msg = "Authentication token is missing from the request."
                detail_expected = _AUTH_DETAIL_MSG
            elif re.search("not provided or formatted incorrectly", server_msg, re.IGNORECASE):
                error_code = "AUTH_E_002"
                clean_msg = "Authentication token is invalid or malformed."
                detail_expected = _AUTH_DETAIL_MSG
            elif re.search("Invalid API token", server_msg, re.IGNORECASE):
                error_code = "AUTH_E_003"
                clean_msg = "Authentication token is expired or revoked."
                detail_expected = _AUTH_DETAIL_MSG
            elif re.search("rate limit exceeded", server_msg, re.IGNORECASE):
                error_code = "AUTH_E_004"
                clean_msg = "Rate limit exceeded."
                detail_expected = _RATE_LIMIT_DETAIL_MSG
            elif re.search("errors resolving", server_msg, re.IGNORECASE):
                error_code = "AUTH_E_005"
                clean_msg = "Hostname lookup failed."
                detail_expected = _AUTH_HOST_MSG
                payload_field = "host"
            else:
                error_code = "AUTH_E_001"
                clean_msg = "Authentication token is missing from the request."
                detail_expected = _AUTH_DETAIL_MSG
        else:
            error_code = "AUTH_E_001"
            clean_msg = "Authentication token is missing from the request."
            detail_expected = _AUTH_DETAIL_MSG

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "error_code": error_code,
            "message": clean_msg,
            "timestamp": timestamp,
            "details": [{"field": payload_field, "message": None, "expected": detail_expected}],
        }
        json_payload = json.dumps(payload)

        return f"{error_code}::{json_payload}"

    except Exception:
        return error_message


def _decode_payload_candidate(candidate: str) -> dict | None:
    """Parse a ``{...}`` candidate that may be raw JSON or still inside a gRPC-escaped string."""
    decoder = json.JSONDecoder()
    payload: object = None

    try:
        payload, _ = decoder.raw_decode(candidate)
    except json.JSONDecodeError:
        try:
            unescaped = re.sub(r"(?<!\\)\\'", "'", candidate)
            decoded_text, _ = decoder.raw_decode('"' + unescaped + '"')
            payload, _ = decoder.raw_decode(decoded_text)
        except json.JSONDecodeError:
            try:
                payload = json.loads(_extract_json_object(candidate))
            except json.JSONDecodeError:
                return None

    # Nested ``details`` items are not error payloads.
    if isinstance(payload, dict) and "error_code" in payload:
        return payload
    return None


def extract_error_payload(error_message: str) -> dict | None:
    """Find a structured error payload in direct or gRPC-wrapped Flight text."""
    normalized_message = _normalize_enodia_error(error_message)
    messages = (error_message,) if normalized_message == error_message else (error_message, normalized_message)

    for message in messages:
        for delimiter in re.finditer(r"::", message):
            payload_text = message[delimiter.end() :]
            for brace in re.finditer(r"\{", payload_text):
                payload = _decode_payload_candidate(payload_text[brace.start() :])
                if payload is not None:
                    return payload

    return None


_UNKNOWN_ERROR = "Unknown error"


def parse_dataconnect_error(ex: Exception, trace_id: str | None = None) -> TransportError:
    """Parse a raw exception into a typed ``TransportError``.

    Extracts a structured ``PREFIX::JSON`` payload from the exception message,
    maps the ``error_code`` prefix to the appropriate ``TransportError``
    subclass, and returns a fully populated error instance.

    Falls back to a generic ``TransportError`` with code ``SDK_ERROR`` when
    the message cannot be parsed or does not match the expected format.
    """
    try:
        if isinstance(ex, TransportError):
            if ex.trace_id is None:
                ex.trace_id = trace_id
            return ex

        error_message = str(ex)

        error_data = extract_error_payload(error_message)
        if error_data is not None:
            parsed_details: list[ErrorDetail] | None = None
            raw_details = error_data.get("details")
            if isinstance(raw_details, list):
                standard_keys = {"field", "message", "expected"}
                parsed_details = [
                    ErrorDetail(
                        field=item.get("field"),
                        message=item.get("message"),
                        expected=item.get("expected"),
                        extra={k: v for k, v in item.items() if k not in standard_keys},
                    )
                    for item in raw_details
                    if isinstance(item, dict)
                ]

            error_code = error_data.get("error_code", "SDK_ERROR")
            payload_trace_id = error_data.get("trace_id")
            parsed_trace_id = trace_id or (payload_trace_id if isinstance(payload_trace_id, str) else None) or None

            if error_code.startswith("AUTH_"):
                return TransportAuthenticationError(
                    error_code=error_code,
                    message=error_data.get("message") or _UNKNOWN_ERROR,
                    timestamp=error_data.get("timestamp"),
                    details=parsed_details,
                    trace_id=parsed_trace_id,
                )

            if error_code.startswith("AUTHZ_"):
                return TransportAuthorizationError(
                    error_code=error_code,
                    message=error_data.get("message") or _UNKNOWN_ERROR,
                    timestamp=error_data.get("timestamp"),
                    details=parsed_details,
                    trace_id=parsed_trace_id,
                )

            if error_code.startswith("VAL_"):
                return TransportValidationError(
                    error_code=error_code,
                    message=error_data.get("message") or _UNKNOWN_ERROR,
                    timestamp=error_data.get("timestamp"),
                    details=parsed_details,
                    trace_id=parsed_trace_id,
                )

            if error_code.startswith("RES_"):
                return TransportNotFoundError(
                    error_code=error_code,
                    message=error_data.get("message") or _UNKNOWN_ERROR,
                    timestamp=error_data.get("timestamp"),
                    details=parsed_details,
                    trace_id=parsed_trace_id,
                )

            if error_code.startswith("INT_"):
                return TransportServerError(
                    error_code=error_code,
                    message=error_data.get("message") or _UNKNOWN_ERROR,
                    timestamp=error_data.get("timestamp"),
                    details=parsed_details,
                    trace_id=parsed_trace_id,
                )

            return TransportError(
                error_code=error_code,
                message=error_data.get("message") or _UNKNOWN_ERROR,
                timestamp=error_data.get("timestamp"),
                details=parsed_details,
                trace_id=parsed_trace_id,
            )

        return TransportError(error_code="SDK_ERROR", message=error_message, trace_id=trace_id)

    except Exception as ex:
        return TransportError(error_code="SDK_ERROR", message=str(ex), trace_id=trace_id)
