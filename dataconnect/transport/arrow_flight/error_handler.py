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

_RATE_LIMIT_DETAIL_MSG = "Wait before making more requests."

_ENODIA_PATTERN = re.compile(
    r"FlightUnauthenticatedError|Flight returned unauthenticated error",
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
            "details": [{"field": "token", "message": None, "expected": detail_expected}],
        }
        json_payload = json.dumps(payload)

        return f"{error_code}::{json_payload}"

    except Exception:
        return error_message


_UNKNOWN_ERROR = "Unknown error"


def parse_dataconnect_error(ex: Exception) -> TransportError:
    """Parse a raw exception into a typed ``TransportError``.

    Extracts a structured ``PREFIX::JSON`` payload from the exception message,
    maps the ``error_code`` prefix to the appropriate ``TransportError``
    subclass, and returns a fully populated error instance.

    Falls back to a generic ``TransportError`` with code ``SDK_ERROR`` when
    the message cannot be parsed or does not match the expected format.
    """
    try:
        error_message = str(ex)

        # Normalize enodia authentication errors into PREFIX::JSON format
        error_message = _normalize_enodia_error(error_message)

        if "::" in error_message:
            delimiter_pos = error_message.index("::")
            json_part_raw = error_message[delimiter_pos + 2 :]

            if json_part_raw:
                json_part = _extract_json_object(json_part_raw)

                error_data: dict = json.loads(json_part)

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

                if error_code.startswith("AUTH_"):
                    return TransportAuthenticationError(
                        error_code=error_code,
                        message=error_data.get("message") or _UNKNOWN_ERROR,
                        timestamp=error_data.get("timestamp"),
                        details=parsed_details,
                    )

                if error_code.startswith("AUTHZ_"):
                    return TransportAuthorizationError(
                        error_code=error_code,
                        message=error_data.get("message") or _UNKNOWN_ERROR,
                        timestamp=error_data.get("timestamp"),
                        details=parsed_details,
                    )

                if error_code.startswith("VAL_"):
                    return TransportValidationError(
                        error_code=error_code,
                        message=error_data.get("message") or _UNKNOWN_ERROR,
                        timestamp=error_data.get("timestamp"),
                        details=parsed_details,
                    )

                if error_code.startswith("RES_"):
                    return TransportNotFoundError(
                        error_code=error_code,
                        message=error_data.get("message") or _UNKNOWN_ERROR,
                        timestamp=error_data.get("timestamp"),
                        details=parsed_details,
                    )

                if error_code.startswith("INT_"):
                    return TransportServerError(
                        error_code=error_code,
                        message=error_data.get("message") or _UNKNOWN_ERROR,
                        timestamp=error_data.get("timestamp"),
                        details=parsed_details,
                    )

                return TransportError(
                    error_code=error_code,
                    message=error_data.get("message") or _UNKNOWN_ERROR,
                    timestamp=error_data.get("timestamp"),
                    details=parsed_details,
                )

        return TransportError(error_code="SDK_ERROR", message=error_message)

    except Exception as ex:
        return TransportError(error_code="SDK_ERROR", message=str(ex))
