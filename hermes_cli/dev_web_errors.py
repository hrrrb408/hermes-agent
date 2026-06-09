"""Dev Web API error definitions and handler.

Defines business error codes and a FastAPI exception handler that
produces the unified error envelope. Importing this module has no
side effects.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from hermes_cli.dev_web_schemas import (
    ErrorBody,
    ErrorResponse,
    ResponseMeta,
    sanitize_request_id,
    _utc_now_iso,
)

# ── Business error codes ──

BAD_REQUEST = "BAD_REQUEST"
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
VALIDATION_ERROR = "VALIDATION_ERROR"
UNSAFE_ENVIRONMENT = "UNSAFE_ENVIRONMENT"
DEV_API_CONFIGURATION_ERROR = "DEV_API_CONFIGURATION_ERROR"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
SESSION_STORE_UNAVAILABLE = "SESSION_STORE_UNAVAILABLE"
MEMORY_UNAVAILABLE = "MEMORY_UNAVAILABLE"
MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
INVALID_MEMORY_ID = "INVALID_MEMORY_ID"
INVALID_PARAMETER = "INVALID_PARAMETER"
CONTEXT_PREVIEW_ERROR = "CONTEXT_PREVIEW_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"
REVIEW_QUEUE_UNAVAILABLE = "REVIEW_QUEUE_UNAVAILABLE"
REVIEW_NOT_FOUND = "REVIEW_NOT_FOUND"
INVALID_REVIEW_ID = "INVALID_REVIEW_ID"
INVALID_REVIEW_QUERY = "INVALID_REVIEW_QUERY"
REVIEW_STORE_ERROR = "REVIEW_STORE_ERROR"
REVIEW_DRY_RUN_UNAVAILABLE = "REVIEW_DRY_RUN_UNAVAILABLE"
REVIEW_NOT_PENDING = "REVIEW_NOT_PENDING"
REVIEW_APPROVAL_BLOCKED = "REVIEW_APPROVAL_BLOCKED"
REVIEW_REJECTION_BLOCKED = "REVIEW_REJECTION_BLOCKED"
REVIEW_EXECUTE_DISABLED = "REVIEW_EXECUTE_DISABLED"
REVIEW_PRECONDITION_FAILED = "REVIEW_PRECONDITION_FAILED"
INVALID_CONFIRMATION = "INVALID_CONFIRMATION"
MISSING_DRY_RUN = "MISSING_DRY_RUN"
INVALID_ACKNOWLEDGED_EFFECTS = "INVALID_ACKNOWLEDGED_EFFECTS"
REVIEW_EXECUTE_ERROR = "REVIEW_EXECUTE_ERROR"
MEMORY_DRY_RUN_UNAVAILABLE = "MEMORY_DRY_RUN_UNAVAILABLE"
INVALID_MEMORY_DRY_RUN_REQUEST = "INVALID_MEMORY_DRY_RUN_REQUEST"
MEMORY_WRITE_BLOCKED = "MEMORY_WRITE_BLOCKED"
MEMORY_UPDATE_BLOCKED = "MEMORY_UPDATE_BLOCKED"
MEMORY_ARCHIVE_BLOCKED = "MEMORY_ARCHIVE_BLOCKED"
MEMORY_P0_PROTECTED = "MEMORY_P0_PROTECTED"
MEMORY_PERMANENT_PROTECTED = "MEMORY_PERMANENT_PROTECTED"
MEMORY_DUPLICATE_BLOCKED = "MEMORY_DUPLICATE_BLOCKED"
MEMORY_ALREADY_ARCHIVED = "MEMORY_ALREADY_ARCHIVED"
MEMORY_CATEGORY_NOT_FOUND = "MEMORY_CATEGORY_NOT_FOUND"
MEMORY_STORE_ERROR = "MEMORY_STORE_ERROR"
AGENT_PREVIEW_UNAVAILABLE = "AGENT_PREVIEW_UNAVAILABLE"
INVALID_AGENT_PREVIEW_REQUEST = "INVALID_AGENT_PREVIEW_REQUEST"
INVALID_SESSION_ID = "INVALID_SESSION_ID"
INVALID_MODEL_OVERRIDE = "INVALID_MODEL_OVERRIDE"
INVALID_TEMPERATURE = "INVALID_TEMPERATURE"
INVALID_MAX_OUTPUT_TOKENS = "INVALID_MAX_OUTPUT_TOKENS"
AGENT_HISTORY_UNAVAILABLE = "AGENT_HISTORY_UNAVAILABLE"
AGENT_MEMORY_CONTEXT_UNAVAILABLE = "AGENT_MEMORY_CONTEXT_UNAVAILABLE"
AGENT_CONFIG_UNAVAILABLE = "AGENT_CONFIG_UNAVAILABLE"
AGENT_PROMPT_ASSEMBLY_ERROR = "AGENT_PROMPT_ASSEMBLY_ERROR"

# ── Forbidden strings that must never appear in error responses ──
_FORBIDDEN_IN_MESSAGE = (
    "traceback",
    "file \"/",
    "users/huangruibang",
    ".hermes",
    "state.db",
    "api_key",
    "token",
    "secret",
    "cookie",
    "sql",
    "exception",
)


def _is_message_safe(message: str) -> bool:
    """Check that an error message does not leak sensitive info."""
    lower = message.lower()
    return not any(forbidden in lower for forbidden in _FORBIDDEN_IN_MESSAGE)


def _safe_error_message(default: str = "An error occurred.") -> str:
    """Return a generic safe error message."""
    return default


def make_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: str | None = None,
    request_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Build a standardised error response dict and HTTP status code.

    Returns ``(body_dict, status_code)`` ready for ``JSONResponse``.
    """
    safe_message = message if _is_message_safe(message) else _safe_error_message()
    rid = sanitize_request_id(request_id)
    timestamp = _utc_now_iso()
    body = {
        "error": {
            "code": code,
            "message": safe_message,
            "details": details,
        },
        "requestId": rid,
        "timestamp": timestamp,
    }
    return body, status_code


def register_error_handlers(app: FastAPI) -> None:
    """Register unified error handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code_map = {
            400: BAD_REQUEST,
            404: RESOURCE_NOT_FOUND,
            405: METHOD_NOT_ALLOWED,
            422: VALIDATION_ERROR,
            503: SERVICE_UNAVAILABLE,
        }
        rid = getattr(request.state, "request_id", None) or sanitize_request_id(None)
        body, status = make_error_response(
            status_code=exc.status_code,
            code=code_map.get(exc.status_code, str(exc.status_code)),
            message=str(exc.detail) if exc.detail else _safe_error_message(),
            request_id=rid,
        )
        return JSONResponse(content=body, status_code=status)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or sanitize_request_id(None)
        body, status = make_error_response(
            status_code=500,
            code=INTERNAL_ERROR,
            message="An internal error occurred.",
            request_id=rid,
        )
        return JSONResponse(content=body, status_code=status)


# Avoid name collision with the type annotation import.
from typing import Any  # noqa: E402
