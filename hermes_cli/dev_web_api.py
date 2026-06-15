"""Hermes Dev Web API — independent read-only FastAPI application.

This module provides the ``create_dev_web_api_app()`` factory and the
Phase 1A endpoints:

- ``GET /api/dev/v1/status``
- ``GET /api/dev/v1/files/status``
- ``GET /api/dev/v1/sessions``
- ``GET /api/dev/v1/sessions/{sessionId}``
- ``GET /api/dev/v1/sessions/{sessionId}/messages``
- ``GET /api/dev/v1/memory/status``
- ``GET /api/dev/v1/memory/categories``
- ``GET /api/dev/v1/memory/items``
- ``GET /api/dev/v1/memory/items/{memoryId}``
- ``POST /api/dev/v1/context/preview``
- ``GET /api/dev/v1/agent/status``
- ``GET /api/dev/v1/reviews/status``
- ``GET /api/dev/v1/reviews``
- ``GET /api/dev/v1/reviews/{reviewId}``

Importing this module has **no side effects**: no server is started, no
files are read, no database connections are opened.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from pathlib import Path

from fastapi import Body, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from typing import Any

from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_errors import (
    register_error_handlers,
    SESSION_NOT_FOUND,
    SESSION_STORE_UNAVAILABLE,
    MEMORY_UNAVAILABLE,
    MEMORY_NOT_FOUND,
    INVALID_MEMORY_ID,
    INVALID_PARAMETER,
    CONTEXT_PREVIEW_ERROR,
    REVIEW_QUEUE_UNAVAILABLE,
    REVIEW_NOT_FOUND,
    INVALID_REVIEW_ID,
    INVALID_REVIEW_QUERY,
    REVIEW_STORE_ERROR,
    REVIEW_DRY_RUN_UNAVAILABLE,
    REVIEW_NOT_PENDING,
    REVIEW_APPROVAL_BLOCKED,
    REVIEW_EXECUTE_DISABLED,
    REVIEW_PRECONDITION_FAILED,
    INVALID_CONFIRMATION,
    MISSING_DRY_RUN,
    INVALID_ACKNOWLEDGED_EFFECTS,
    REVIEW_EXECUTE_ERROR,
    UNSAFE_ENVIRONMENT,
    REVIEW_REJECTION_BLOCKED,
    MEMORY_DRY_RUN_UNAVAILABLE,
    INVALID_MEMORY_DRY_RUN_REQUEST,
    MEMORY_WRITE_BLOCKED,
    MEMORY_UPDATE_BLOCKED,
    MEMORY_ARCHIVE_BLOCKED,
    MEMORY_P0_PROTECTED,
    MEMORY_PERMANENT_PROTECTED,
    MEMORY_DUPLICATE_BLOCKED,
    MEMORY_ALREADY_ARCHIVED,
    MEMORY_CATEGORY_NOT_FOUND,
    MEMORY_STORE_ERROR,
    INTERNAL_ERROR,
    AGENT_PREVIEW_UNAVAILABLE,
    INVALID_AGENT_PREVIEW_REQUEST,
    INVALID_SESSION_ID,
    INVALID_MODEL_OVERRIDE,
    INVALID_TEMPERATURE,
    INVALID_MAX_OUTPUT_TOKENS,
    AGENT_HISTORY_UNAVAILABLE,
    AGENT_MEMORY_CONTEXT_UNAVAILABLE,
    AGENT_CONFIG_UNAVAILABLE,
    AGENT_PROMPT_ASSEMBLY_ERROR,
    AGENT_RUN_DISABLED,
    INVALID_AGENT_RUN_REQUEST,
    AGENT_SESSION_BUSY,
    AGENT_RUN_CAPACITY_REACHED,
    AGENT_RUN_NOT_FOUND,
    AGENT_RATE_LIMITED,
    AGENT_RUN_FAILED,
)
from hermes_cli.dev_web_middleware import RequestIdMiddleware
from hermes_cli.dev_web_schemas import _utc_now_iso
from hermes_cli.dev_web_session_service import (
    DevSessionQueryService,
    SessionNotFoundError,
    SessionStoreUnavailableError,
)
from hermes_cli.dev_web_message_service import (
    DevMessageQueryService,
    MessageSessionNotFoundError,
    MessageStoreUnavailableError,
)
from hermes_cli.dev_web_memory_service import (
    DevMemoryQueryService,
    MemoryUnavailableError,
    MemoryNotFoundError,
    InvalidMemoryIdError,
)
from hermes_cli.dev_web_agent_service import (
    DevAgentStatusService,
)
from hermes_cli.dev_web_review_service import (
    DevReviewQueryService,
    ReviewQueueUnavailableError,
    ReviewNotFoundError,
    InvalidReviewIdError,
    InvalidReviewQueryError,
    ReviewNotPendingError,
    ReviewExecuteDisabledError,
    ReviewPreconditionFailedError,
    InvalidConfirmationError,
    MissingDryRunError,
    InvalidAcknowledgedEffectsError,
    ReviewApprovalBlockedError,
    UnsafeEnvironmentError,
)
from hermes_cli.dev_web_memory_writer_service import (
    DevMemoryWriterDryRunService,
    MemoryWriterDryRunUnavailableError,
    MemoryWriterTargetNotFoundError,
    MemoryWriterInvalidIdError,
    MemoryWriterInvalidRequestError,
)
from hermes_cli.dev_web_agent_preview_service import (
    DevAgentPreviewService,
    AgentPreviewError,
    AgentConfigUnavailableError,
    AgentHistoryUnavailableError,
    AgentMemoryContextUnavailableError,
    AgentPromptAssemblyError,
    InvalidSessionIdError,
    InvalidModelOverrideError,
    InvalidTemperatureError,
    InvalidMaxOutputTokensError,
    InvalidRequestError,
    _validate_session_id,
    _MAX_MESSAGE_LENGTH,
    _MAX_HISTORY_LIMIT,
    _MAX_MEMORY_QUERY_LENGTH,
    _MAX_CATEGORIES,
    _MAX_MEMORIES,
)
from hermes_cli.dev_web_tool_policy_service import (
    DevToolPolicyQueryService,
    validate_catalog_query,
    ToolPolicyQueryError,
    InvalidToolPolicyQueryError,
    InvalidToolRiskError,
    InvalidToolCapabilityError,
    InvalidToolPolicyStatusError,
    InvalidToolSortError,
    ToolPolicyDataInvalidError,
    _DANGEROUS_PARAM_NAMES,
    _MAX_QUERY_LENGTH,
    _MAX_PAGE_SIZE,
)
from hermes_cli.dev_web_tool_schema_preview_service import (
    list_schema_previews as _list_schema_previews,
    get_schema_preview as _get_schema_preview,
)
from hermes_cli.dev_web_tool_dry_run import (
    dry_run_tool_policy as _dry_run_tool_policy,
    STATIC_ALLOWLIST as _DRY_RUN_STATIC_ALLOWLIST,
)
from hermes_cli.dev_web_tool_dry_run_audit import (
    build_dry_run_audit_event as _build_dry_run_audit_event,
    write_dry_run_audit_event as _write_dry_run_audit_event,
)
from hermes_cli.dev_web_tool_execute_confirmation import (
    issue_confirmation_token as _issue_confirmation_token,
)
from hermes_cli.dev_web_tool_execute import (
    evaluate_tool_execute_request as _evaluate_tool_execute_request,
    compute_execute_policy_summary as _compute_execute_policy_summary,
)
from hermes_cli.dev_web_tool_audit_read import (
    read_audit_events as _read_audit_events,
    audit_read_result_to_safe_dict as _audit_read_result_to_safe_dict,
    VALID_AUDIT_KINDS as _VALID_AUDIT_KINDS,
)
from hermes_cli.dev_web_audit_query import (
    build_audit_query as _build_audit_query,
    query_audit_events as _query_audit_events,
    audit_query_result_to_safe_dict as _audit_query_result_to_safe_dict,
    decode_audit_cursor as _decode_audit_cursor,
)
from hermes_cli.dev_web_write_plan import (
    build_write_preview as _build_write_preview,
    build_provider_write_preview as _build_provider_write_preview,
)
from hermes_cli.dev_web_write_handlers import (
    dispatch_write_tool as _dispatch_write_tool,
    dispatch_rollback_tool as _dispatch_rollback_tool,
)
from hermes_cli.dev_web_write_tool_registry import (
    is_phase_2c_write_tool as _is_phase_2c_write_tool,
    PHASE_2C_WRITE_TOOL_IDS as _PHASE_2C_WRITE_TOOL_IDS,
)
from hermes_cli.dev_web_write_rollback import (
    build_rollback_execution_preview as _build_rollback_execution_preview,
)
from hermes_cli.dev_web_write_rollback_store import (
    is_valid_rollback_id as _is_valid_rollback_id,
    list_rollback_manifests as _list_rollback_manifests,
)


# ── Query parameter enums ──


class OrderOption(str, Enum):
    """Sort order for session list."""

    recent = "recent"
    created = "created"


class ArchivedOption(str, Enum):
    """Archive filter for session list."""

    exclude = "exclude"
    include = "include"
    only = "only"


class ReviewStatusOption(str, Enum):
    """Status filter for review list."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"
    all = "all"


class ReviewDecisionOption(str, Enum):
    """Decision filter for review list."""

    WRITE = "WRITE"
    UPDATE = "UPDATE"
    REVIEW = "REVIEW"
    SKIP = "SKIP"
    SKIP_DUPLICATE = "SKIP_DUPLICATE"
    UNDECIDED = "UNDECIDED"
    all = "all"


class ReviewOrderOption(str, Enum):
    """Sort order for review list."""

    created_desc = "created_desc"
    updated_desc = "updated_desc"


# ── App factory ──


def create_dev_web_api_app(
    config: DevWebApiConfig | None = None,
) -> FastAPI:
    """Create and return the Dev Web API FastAPI application.

    This function is safe to call in tests — it does not start a server,
    read files, or open databases.
    """
    if config is None:
        config = DevWebApiConfig(hermes_home=None)

    app = FastAPI(
        title="Hermes Dev Web API",
        version="1",
        docs_url="/docs",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "System", "description": "System status and health"},
            {"name": "Sessions", "description": "Session list and detail"},
            {"name": "Messages", "description": "Session messages"},
            {"name": "Memory", "description": "Memory system read-only access"},
            {"name": "Context", "description": "Memory context preview"},
            {"name": "Agent", "description": "Agent configuration status"},
            {"name": "Files", "description": "File browsing status"},
            {"name": "Reviews", "description": "Review queue read-only access"},
            {"name": "Tools", "description": "Tool policy and catalog read-only access"},
        ],
    )

    app.state.dev_api_config = config

    # Build services if hermes_home is configured
    session_service: DevSessionQueryService | None = None
    message_service: DevMessageQueryService | None = None
    memory_service: DevMemoryQueryService | None = None
    agent_service: DevAgentStatusService | None = None
    review_service: DevReviewQueryService | None = None
    writer_service: DevMemoryWriterDryRunService | None = None
    preview_service: DevAgentPreviewService | None = None
    tool_policy_service: DevToolPolicyQueryService | None = None
    if config.hermes_home is not None:
        state_db_path = config.hermes_home / "state.db"
        session_service = DevSessionQueryService(state_db_path)
        message_service = DevMessageQueryService(state_db_path)
        memory_service = DevMemoryQueryService(config.hermes_home)
        agent_service = DevAgentStatusService(config.hermes_home)
        review_service = DevReviewQueryService(config.hermes_home)
        writer_service = DevMemoryWriterDryRunService(config.hermes_home)
        preview_service = DevAgentPreviewService(config.hermes_home)
    # Tool Policy service is stateless — no hermes_home dependency
    tool_policy_service = DevToolPolicyQueryService()
    app.state.session_service = session_service
    app.state.message_service = message_service
    app.state.memory_service = memory_service
    app.state.agent_service = agent_service
    app.state.review_service = review_service
    app.state.writer_service = writer_service
    app.state.preview_service = preview_service
    app.state.tool_policy_service = tool_policy_service

    # ── Middleware (order matters: outermost first) ──
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ── Error handlers ──
    register_error_handlers(app)

    # ── Routes ──
    _register_routes(app, config, session_service, memory_service, agent_service, review_service, writer_service, preview_service, tool_policy_service)
    _register_tool_execute_routes(app, config)

    # ── Phase 1G-04-30: Tool Audit Events Read-Only (one GET route) ──
    _register_tool_audit_read_routes(app, config)

    return app


def _make_error_json(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    """Build a standardised JSON error response."""
    from hermes_cli.dev_web_errors import make_error_response

    body, status = make_error_response(
        status_code=status_code,
        code=code,
        message=message,
        request_id=request_id,
    )
    return JSONResponse(content=body, status_code=status)


def _is_store_audit_query(
    *,
    cursor: str | None,
    order: str | None,
    event_type: str | None,
    tool_id: str | None,
    status: str | None,
    source: str | None,
    provider_mode: str | None,
    read_only: bool | None,
    write_required: bool | None,
    from_created_at: str | None,
    to_created_at: str | None,
    search: str | None,
    include_summary: bool | None,
) -> bool:
    """Return True when the request should use the Phase 2D durable store path.

    Store mode is engaged by any new filter param, an opaque (non-integer)
    cursor, order=asc, or an explicit includeSummary toggle. Legacy requests
    (auditKind + integer offset cursor + canonicalName only) stay on the
    legacy reader for backward compatibility.
    """
    if cursor is not None and not cursor.isdigit():
        return True
    if order == "asc":
        return True
    for value in (
        event_type, tool_id, status, source, provider_mode,
        from_created_at, to_created_at, search,
    ):
        if value is not None:
            return True
    if read_only is not None or write_required is not None:
        return True
    if include_summary is not None:
        return True
    return False


# Error codes for the durable-store audit path.
_AUDIT_STORE_INVALID_CURSOR = "TOOL_AUDIT_EVENTS_INVALID_CURSOR"
_AUDIT_STORE_INVALID_QUERY = "TOOL_AUDIT_EVENTS_INVALID_QUERY"
_AUDIT_STORE_LIMIT_TOO_LARGE = "TOOL_AUDIT_EVENTS_INVALID_LIMIT"


def _audit_store_error_json(result: Any, request_id: str) -> JSONResponse:
    """Map a durable-store audit query failure to a safe HTTP error envelope."""
    code = getattr(result, "error_code", None) or ""
    message = getattr(result, "error_message", None) or "Audit query failed."
    if code == "blocked_audit_cursor_invalid":
        return _make_error_json(
            status_code=400, code=_AUDIT_STORE_INVALID_CURSOR,
            message=message, request_id=request_id,
        )
    if code == "blocked_audit_cursor_query_mismatch":
        return _make_error_json(
            status_code=400, code=_AUDIT_STORE_INVALID_CURSOR,
            message=message, request_id=request_id,
        )
    if code == "blocked_audit_limit_too_large":
        return _make_error_json(
            status_code=400, code=_AUDIT_STORE_LIMIT_TOO_LARGE,
            message=message, request_id=request_id,
        )
    if code in (
        "audit_store_hermes_home_missing", "audit_store_root_forbidden",
    ):
        return _make_error_json(
            status_code=503, code="TOOL_AUDIT_EVENTS_UNAVAILABLE",
            message="Audit store is unavailable.", request_id=request_id,
        )
    return _make_error_json(
        status_code=400, code=_AUDIT_STORE_INVALID_QUERY,
        message=message, request_id=request_id,
    )


def _register_routes(
    app: FastAPI,
    config: DevWebApiConfig,
    session_service: DevSessionQueryService | None,
    memory_service: DevMemoryQueryService | None,
    agent_service: DevAgentStatusService | None,
    review_service: DevReviewQueryService | None,
    writer_service: DevMemoryWriterDryRunService | None,
    preview_service: DevAgentPreviewService | None,
    tool_policy_service: DevToolPolicyQueryService | None,
) -> None:
    """Register Phase 1A routes."""

    prefix = config.api_prefix

    # ── GET /status ──

    @app.get(
        f"{prefix}/status",
        tags=["System"],
        summary="System status and environment verification",
    )
    async def get_status(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()
        hermes_home = config.hermes_home
        has_dev_home = hermes_home is not None

        # Check real session availability
        sessions_available = (
            session_service.is_available()
            if session_service is not None
            else False
        )

        # Check real memory availability
        memory_available = (
            memory_service.is_available()
            if memory_service is not None
            else False
        )

        return {
            "data": {
                "environment": "development",
                "apiVersion": "v1",
                "status": "ok",
                "readOnly": True,
                "bind": {"host": config.host, "port": config.port},
                "isolation": {
                    "passed": has_dev_home,
                    "usesDevelopmentHome": has_dev_home,
                    "productionHomeUntouched": True,
                },
                "services": {
                    "api": {"available": True, "readOnly": True},
                    "sessions": {
                        "available": sessions_available,
                        "readOnly": True,
                    },
                    "memory": {
                        "available": memory_available,
                        "readOnly": True,
                    },
                    "agent": {
                        "available": agent_service is not None,
                        "readOnly": True,
                    },
                    "files": {"available": False, "readOnly": True},
                },
            },
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /files/status ──

    @app.get(
        f"{prefix}/files/status",
        tags=["Files"],
        summary="File browsing availability",
    )
    async def get_files_status(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        return {
            "data": {
                "available": False,
                "readOnly": True,
                "browseEnabled": False,
                "uploadEnabled": False,
                "downloadEnabled": False,
                "deleteEnabled": False,
                "reason": "Files integration is not available in Phase 0C.",
            },
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /sessions ──

    @app.get(
        f"{prefix}/sessions",
        tags=["Sessions"],
        summary="List sessions with pagination",
    )
    def list_sessions(
        request: Request,
        limit: int = Query(default=30, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        query: str | None = Query(
            default=None,
            max_length=500,
            description="Search session titles and session identifiers. "
            "Message contents are not searched in Phase 0C-03.",
        ),
        source: str | None = Query(default=None),
        order: OrderOption = Query(default=OrderOption.recent),
        archived: ArchivedOption = Query(default=ArchivedOption.exclude),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if session_service is None:
            return _make_error_json(
                status_code=503,
                code=SESSION_STORE_UNAVAILABLE,
                message="Session storage is unavailable.",
                request_id=rid,
            )

        try:
            result = session_service.list_sessions(
                query=query,
                offset=offset,
                limit=limit,
                order=order.value,
                source=source,
                archived=archived.value,
            )
        except SessionStoreUnavailableError:
            return _make_error_json(
                status_code=503,
                code=SESSION_STORE_UNAVAILABLE,
                message="Session storage is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /sessions/{sessionId} ──

    @app.get(
        f"{prefix}/sessions/{{sessionId}}",
        tags=["Sessions"],
        summary="Get session detail",
    )
    def get_session_detail(
        request: Request,
        sessionId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate session ID
        validation_error = DevSessionQueryService.validate_session_id(
            sessionId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code="INVALID_PARAMETER",
                message=validation_error,
                request_id=rid,
            )

        if session_service is None:
            return _make_error_json(
                status_code=503,
                code=SESSION_STORE_UNAVAILABLE,
                message="Session storage is unavailable.",
                request_id=rid,
            )

        try:
            result = session_service.get_session(sessionId)
        except SessionNotFoundError:
            return _make_error_json(
                status_code=404,
                code=SESSION_NOT_FOUND,
                message="Session was not found.",
                request_id=rid,
            )
        except SessionStoreUnavailableError:
            return _make_error_json(
                status_code=503,
                code=SESSION_STORE_UNAVAILABLE,
                message="Session storage is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /sessions/{sessionId}/messages ──

    message_service = app.state.message_service

    @app.get(
        f"{prefix}/sessions/{{sessionId}}/messages",
        tags=["Messages"],
        summary="Get messages for a session",
    )
    def get_session_messages(
        request: Request,
        sessionId: str,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        before: int | None = Query(default=None),
        after: int | None = Query(default=None),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate session ID
        validation_error = DevSessionQueryService.validate_session_id(
            sessionId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code="INVALID_PARAMETER",
                message=validation_error,
                request_id=rid,
            )

        if message_service is None:
            return _make_error_json(
                status_code=503,
                code=SESSION_STORE_UNAVAILABLE,
                message="Message storage is unavailable.",
                request_id=rid,
            )

        try:
            result = message_service.get_messages(
                sessionId,
                limit=limit,
                offset=offset,
                before=before,
                after=after,
            )
        except MessageSessionNotFoundError:
            return _make_error_json(
                status_code=404,
                code=SESSION_NOT_FOUND,
                message="Session was not found.",
                request_id=rid,
            )
        except MessageStoreUnavailableError:
            return _make_error_json(
                status_code=503,
                code=SESSION_STORE_UNAVAILABLE,
                message="Message storage is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /memory/status ──

    @app.get(
        f"{prefix}/memory/status",
        tags=["Memory"],
        summary="Memory system status",
    )
    def get_memory_status(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        if memory_service is None:
            return {
                "data": {
                    "available": False,
                    "readOnly": True,
                    "rootCategories": {"total": 0, "active": 0, "archived": 0},
                    "memories": {"total": 0, "active": 0, "archived": 0},
                    "capabilities": {
                        "contextLoader": False,
                        "runtimeInjection": False,
                        "writer": False,
                        "reviewQueue": False,
                    },
                    "exposedCapabilities": {
                        "read": False,
                        "write": False,
                        "review": False,
                    },
                },
                "meta": {"requestId": rid, "timestamp": ts},
            }

        result = memory_service.get_status()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /memory/categories ──

    @app.get(
        f"{prefix}/memory/categories",
        tags=["Memory"],
        summary="List memory categories",
    )
    def list_memory_categories(
        request: Request,
        includeArchived: bool = Query(
            default=False,
            alias="includeArchived",
            description="Include archived categories.",
        ),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if memory_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        try:
            items = memory_service.list_categories(
                include_archived=includeArchived,
            )
        except MemoryUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": {
                "items": items,
                "total": len(items),
            },
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /memory/items ──

    @app.get(
        f"{prefix}/memory/items",
        tags=["Memory"],
        summary="List memory items",
    )
    def list_memory_items(
        request: Request,
        category: str | None = Query(default=None, max_length=64),
        query: str | None = Query(default=None, max_length=200),
        includeArchived: bool = Query(
            default=False,
            alias="includeArchived",
        ),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if memory_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        try:
            result = memory_service.list_items(
                category=category,
                query=query,
                include_archived=includeArchived,
                limit=limit,
                offset=offset,
            )
        except MemoryUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /memory/items/{memoryId} ──

    @app.get(
        f"{prefix}/memory/items/{{memoryId}}",
        tags=["Memory"],
        summary="Get memory item detail",
    )
    def get_memory_item(
        request: Request,
        memoryId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate memory ID
        validation_error = DevMemoryQueryService.validate_memory_id(memoryId)
        if validation_error:
            return _make_error_json(
                status_code=400,
                code=INVALID_MEMORY_ID,
                message=validation_error,
                request_id=rid,
            )

        if memory_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        try:
            result = memory_service.get_item(memoryId)
        except MemoryNotFoundError:
            return _make_error_json(
                status_code=404,
                code=MEMORY_NOT_FOUND,
                message="Memory item was not found.",
                request_id=rid,
            )
        except MemoryUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── POST /context/preview ──

    @app.post(
        f"{prefix}/context/preview",
        tags=["Context"],
        summary="Preview memory context for a query",
    )
    async def preview_context(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Parse request body
        try:
            body = await request.json()
        except Exception:
            return _make_error_json(
                status_code=400,
                code=INVALID_PARAMETER,
                message="Request body must be valid JSON.",
                request_id=rid,
            )

        query = body.get("query", "")
        if not isinstance(query, str):
            return _make_error_json(
                status_code=400,
                code=INVALID_PARAMETER,
                message="Query must be a string.",
                request_id=rid,
            )
        query = query.strip()
        if not query:
            return _make_error_json(
                status_code=400,
                code=INVALID_PARAMETER,
                message="Query is required.",
                request_id=rid,
            )
        if len(query) > 1000:
            return _make_error_json(
                status_code=400,
                code=INVALID_PARAMETER,
                message="Query is too long (max 1000 characters).",
                request_id=rid,
            )

        # Extract options with safe bounds
        options = body.get("options", {})
        if not isinstance(options, dict):
            options = {}

        max_categories = options.get("maxCategories", 3)
        if not isinstance(max_categories, int) or max_categories < 1:
            max_categories = 3
        max_categories = min(max_categories, 10)

        max_memories = options.get("maxMemories", 5)
        if not isinstance(max_memories, int) or max_memories < 1:
            max_memories = 5
        max_memories = min(max_memories, 20)

        max_record_chars = options.get("maxRecordChars", 3000)
        if not isinstance(max_record_chars, int) or max_record_chars < 1:
            max_record_chars = 3000
        max_record_chars = min(max_record_chars, 10000)

        include_archived = options.get("includeArchived", False)
        if not isinstance(include_archived, bool):
            include_archived = False

        show_scores = options.get("showScores", True)
        if not isinstance(show_scores, bool):
            show_scores = True

        if memory_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        try:
            result = memory_service.preview_context(
                query,
                max_categories=max_categories,
                max_memories=max_memories,
                max_record_chars=max_record_chars,
                include_archived=include_archived,
                show_scores=show_scores,
            )
        except MemoryUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_UNAVAILABLE,
                message="Memory system is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /agent/status ──

    @app.get(
        f"{prefix}/agent/status",
        tags=["Agent"],
        summary="Agent configuration status",
    )
    def get_agent_status(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        if agent_service is None:
            return {
                "data": {
                    "available": False,
                    "readOnly": True,
                    "runtime": {
                        "entry": "conversation_loop",
                        "messageSendEnabled": False,
                        "streamingEnabled": False,
                        "toolExecutionEnabled": False,
                    },
                    "model": {
                        "configured": False,
                        "provider": "",
                        "name": "",
                    },
                    "memory": {
                        "enabled": False,
                        "contextLoaderEnabled": False,
                        "autoWriteEnabled": False,
                        "reviewQueueEnabled": False,
                    },
                },
                "meta": {"requestId": rid, "timestamp": ts},
            }

        result = agent_service.get_status()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /reviews/status ──

    @app.get(
        f"{prefix}/reviews/status",
        tags=["Reviews"],
        summary="Review queue status",
    )
    def get_review_status(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        if review_service is None:
            return {
                "data": {
                    "available": False,
                    "readOnly": True,
                    "queueEnabled": False,
                    "writeEnabled": False,
                    "approveEnabled": False,
                    "rejectEnabled": False,
                    "enqueueEnabled": False,
                    "counts": {
                        "pending": 0,
                        "approved": 0,
                        "rejected": 0,
                        "failed": 0,
                        "total": 0,
                    },
                    "storage": {
                        "available": False,
                        "redactedPath": "",
                    },
                },
                "meta": {"requestId": rid, "timestamp": ts},
            }

        result = review_service.get_status()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /reviews ──

    @app.get(
        f"{prefix}/reviews",
        tags=["Reviews"],
        summary="List review queue items",
    )
    def list_reviews(
        request: Request,
        status: ReviewStatusOption | None = Query(
            default=None,
            description="Filter by review status.",
        ),
        decision: ReviewDecisionOption | None = Query(
            default=None,
            description="Filter by original decision.",
        ),
        category: str | None = Query(
            default=None,
            max_length=64,
            description="Filter by memory category.",
        ),
        query: str | None = Query(
            default=None,
            max_length=200,
            description="Search review titles and summaries.",
        ),
        limit: int = Query(default=30, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        order: ReviewOrderOption = Query(default=ReviewOrderOption.updated_desc),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if review_service is None:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )

        try:
            result = review_service.list_reviews(
                status=status.value if status else None,
                decision=decision.value if decision else None,
                category=category,
                query=query,
                limit=limit,
                offset=offset,
                order=order.value,
            )
        except ReviewQueueUnavailableError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )
        except InvalidReviewQueryError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_REVIEW_QUERY,
                message=str(exc),
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /reviews/{reviewId} ──

    @app.get(
        f"{prefix}/reviews/{{reviewId}}",
        tags=["Reviews"],
        summary="Get review item detail",
    )
    def get_review_detail(
        request: Request,
        reviewId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate review ID
        validation_error = DevReviewQueryService.validate_review_id(
            reviewId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code=INVALID_REVIEW_ID,
                message=validation_error,
                request_id=rid,
            )

        if review_service is None:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )

        try:
            result = review_service.get_review_detail(reviewId)
        except ReviewNotFoundError:
            return _make_error_json(
                status_code=404,
                code=REVIEW_NOT_FOUND,
                message="Review item was not found.",
                request_id=rid,
            )
        except ReviewQueueUnavailableError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── POST /reviews/{reviewId}/approve/dry-run ──

    @app.post(
        f"{prefix}/reviews/{{reviewId}}/approve/dry-run",
        tags=["Reviews"],
        summary="Preview approve action (dry-run, no side effects)",
    )
    def approve_dry_run(
        request: Request,
        reviewId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate review ID
        validation_error = DevReviewQueryService.validate_review_id(
            reviewId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code=INVALID_REVIEW_ID,
                message=validation_error,
                request_id=rid,
            )

        if review_service is None:
            return _make_error_json(
                status_code=503,
                code=REVIEW_DRY_RUN_UNAVAILABLE,
                message="Review dry-run is unavailable.",
                request_id=rid,
            )

        try:
            result = review_service.dry_run_approve(
                reviewId,
                include_diff=True,
            )
        except ReviewNotFoundError:
            return _make_error_json(
                status_code=404,
                code=REVIEW_NOT_FOUND,
                message="Review item was not found.",
                request_id=rid,
            )
        except ReviewQueueUnavailableError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_DRY_RUN_UNAVAILABLE,
                message="Review dry-run is unavailable.",
                request_id=rid,
            )
        except ReviewNotPendingError as exc:
            return _make_error_json(
                status_code=409,
                code=REVIEW_NOT_PENDING,
                message=str(exc),
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── POST /reviews/{reviewId}/reject/dry-run ──

    @app.post(
        f"{prefix}/reviews/{{reviewId}}/reject/dry-run",
        tags=["Reviews"],
        summary="Preview reject action (dry-run, no side effects)",
    )
    def reject_dry_run(
        request: Request,
        reviewId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate review ID
        validation_error = DevReviewQueryService.validate_review_id(
            reviewId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code=INVALID_REVIEW_ID,
                message=validation_error,
                request_id=rid,
            )

        if review_service is None:
            return _make_error_json(
                status_code=503,
                code=REVIEW_DRY_RUN_UNAVAILABLE,
                message="Review dry-run is unavailable.",
                request_id=rid,
            )

        try:
            result = review_service.dry_run_reject(
                reviewId,
                reason=None,
                include_diff=True,
            )
        except ReviewNotFoundError:
            return _make_error_json(
                status_code=404,
                code=REVIEW_NOT_FOUND,
                message="Review item was not found.",
                request_id=rid,
            )
        except ReviewQueueUnavailableError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_DRY_RUN_UNAVAILABLE,
                message="Review dry-run is unavailable.",
                request_id=rid,
            )
        except ReviewNotPendingError as exc:
            return _make_error_json(
                status_code=409,
                code=REVIEW_NOT_PENDING,
                message=str(exc),
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── POST /reviews/{reviewId}/approve/execute ──

    @app.post(
        f"{prefix}/reviews/{{reviewId}}/approve/execute",
        tags=["Reviews"],
        summary="Execute approve action (dev-only, requires confirmation)",
    )
    def approve_execute(
        request: Request,
        reviewId: str,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate review ID
        validation_error = DevReviewQueryService.validate_review_id(
            reviewId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code=INVALID_REVIEW_ID,
                message=validation_error,
                request_id=rid,
            )

        if review_service is None:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )

        confirmation_text = body.get("confirmationText", "")
        expected_action = body.get("expectedAction", "")
        review_updated_at = body.get("reviewUpdatedAt", "")
        dry_run_previewed = body.get("dryRunPreviewed", False)
        acknowledged_effects = body.get("acknowledgedEffects", [])

        # Validate required fields
        if not confirmation_text:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message="confirmationText is required.",
                request_id=rid,
            )
        if not review_updated_at:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message="reviewUpdatedAt is required.",
                request_id=rid,
            )

        try:
            result = review_service.execute_approve(
                reviewId,
                confirmation_text=confirmation_text,
                expected_action=expected_action,
                review_updated_at=review_updated_at,
                dry_run_previewed=dry_run_previewed,
                acknowledged_effects=acknowledged_effects,
            )
        except ReviewExecuteDisabledError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_EXECUTE_DISABLED,
                message=(
                    "Review execute is disabled. "
                    "Enable with HERMES_REVIEW_EXECUTE_ENABLED=true."
                ),
                # kill_switch_disabled
                request_id=rid,
            )
        except UnsafeEnvironmentError:
            return _make_error_json(
                status_code=503,
                code=UNSAFE_ENVIRONMENT,
                message="Execute is not allowed in this environment.",
                request_id=rid,
            )
        except ReviewNotFoundError:
            return _make_error_json(
                status_code=404,
                code=REVIEW_NOT_FOUND,
                message="Review item was not found.",
                request_id=rid,
            )
        except ReviewNotPendingError as exc:
            return _make_error_json(
                status_code=409,
                code=REVIEW_NOT_PENDING,
                message=str(exc),
                request_id=rid,
            )
        except ReviewPreconditionFailedError:
            return _make_error_json(
                status_code=409,
                code=REVIEW_PRECONDITION_FAILED,
                message=(
                    "Review item was modified since dry-run preview. "
                    "Please re-run dry-run."
                ),
                # updated_at mismatch
                request_id=rid,
            )
        except InvalidConfirmationError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message=str(exc),
                request_id=rid,
            )
        except MissingDryRunError as exc:
            return _make_error_json(
                status_code=400,
                code=MISSING_DRY_RUN,
                message=str(exc),
                request_id=rid,
            )
        except InvalidAcknowledgedEffectsError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_ACKNOWLEDGED_EFFECTS,
                message=str(exc),
                request_id=rid,
            )
        except ReviewApprovalBlockedError as exc:
            return _make_error_json(
                status_code=409,
                code=REVIEW_APPROVAL_BLOCKED,
                message=str(exc),
                request_id=rid,
            )
        except ReviewQueueUnavailableError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=REVIEW_EXECUTE_ERROR,
                message="An unexpected error occurred during execute.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── POST /reviews/{reviewId}/reject/execute ──

    @app.post(
        f"{prefix}/reviews/{{reviewId}}/reject/execute",
        tags=["Reviews"],
        summary="Execute reject action (dev-only, requires confirmation)",
    )
    def reject_execute(
        request: Request,
        reviewId: str,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        # Validate review ID
        validation_error = DevReviewQueryService.validate_review_id(
            reviewId
        )
        if validation_error:
            return _make_error_json(
                status_code=400,
                code=INVALID_REVIEW_ID,
                message=validation_error,
                request_id=rid,
            )

        if review_service is None:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )

        confirmation_text = body.get("confirmationText", "")
        expected_action = body.get("expectedAction", "")
        review_updated_at = body.get("reviewUpdatedAt", "")
        dry_run_previewed = body.get("dryRunPreviewed", False)
        acknowledged_effects = body.get("acknowledgedEffects", [])
        reason = body.get("reason")

        # Validate required fields
        if not confirmation_text:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message="confirmationText is required.",
                request_id=rid,
            )
        if not review_updated_at:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message="reviewUpdatedAt is required.",
                request_id=rid,
            )

        try:
            result = review_service.execute_reject(
                reviewId,
                confirmation_text=confirmation_text,
                expected_action=expected_action,
                review_updated_at=review_updated_at,
                dry_run_previewed=dry_run_previewed,
                acknowledged_effects=acknowledged_effects,
                reason=reason,
            )
        except ReviewExecuteDisabledError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_EXECUTE_DISABLED,
                message=(
                    "Review execute is disabled. "
                    "Enable with HERMES_REVIEW_EXECUTE_ENABLED=true."
                ),
                # kill_switch_disabled
                request_id=rid,
            )
        except UnsafeEnvironmentError:
            return _make_error_json(
                status_code=503,
                code=UNSAFE_ENVIRONMENT,
                message="Execute is not allowed in this environment.",
                request_id=rid,
            )
        except ReviewNotFoundError:
            return _make_error_json(
                status_code=404,
                code=REVIEW_NOT_FOUND,
                message="Review item was not found.",
                request_id=rid,
            )
        except ReviewNotPendingError as exc:
            return _make_error_json(
                status_code=409,
                code=REVIEW_NOT_PENDING,
                message=str(exc),
                request_id=rid,
            )
        except ReviewPreconditionFailedError:
            return _make_error_json(
                status_code=409,
                code=REVIEW_PRECONDITION_FAILED,
                message=(
                    "Review item was modified since dry-run preview. "
                    "Please re-run dry-run."
                ),
                # updated_at mismatch
                request_id=rid,
            )
        except InvalidConfirmationError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message=str(exc),
                request_id=rid,
            )
        except MissingDryRunError as exc:
            return _make_error_json(
                status_code=400,
                code=MISSING_DRY_RUN,
                message=str(exc),
                request_id=rid,
            )
        except InvalidAcknowledgedEffectsError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_ACKNOWLEDGED_EFFECTS,
                message=str(exc),
                request_id=rid,
            )
        except ReviewQueueUnavailableError:
            return _make_error_json(
                status_code=503,
                code=REVIEW_QUEUE_UNAVAILABLE,
                message="Review queue is unavailable.",
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=REVIEW_EXECUTE_ERROR,
                message="An unexpected error occurred during execute.",
                request_id=rid,
            )


        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── Phase 1D: Memory Writer Dry-Run ──
    _register_writer_routes(app, config, writer_service)

    # ── Phase 1E: Agent Prompt Preview & Run Dry-Run ──
    _register_preview_routes(app, config, preview_service)

    # ── Phase 1F: Agent Run (Dev-Only, SSE) ──
    _register_agent_run_routes(app, config)

    # ── Phase 1G: Tool Policy Read-Only ──
    _register_tool_policy_routes(app, config, tool_policy_service)

    # ── Phase 1G-03: Tool Schema Preview Read-Only ──
    _register_schema_preview_routes(app, config)

    # ── Phase 1G-04: Tool Dry-Run Read-Only ──
    _register_tool_dry_run_routes(app, config)


def _register_writer_routes(
    app: FastAPI,
    config: DevWebApiConfig,
    writer_service: DevMemoryWriterDryRunService | None,
) -> None:
    """Register Phase 1D Memory Writer dry-run routes."""

    prefix = config.api_prefix

    # ── POST /memory/write/dry-run ──

    @app.post(
        f"{prefix}/memory/write/dry-run",
        tags=["Memory"],
        summary="Preview WRITE operation (dry-run, no side effects)",
    )
    def memory_write_dry_run(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if writer_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_DRY_RUN_UNAVAILABLE,
                message="Memory writer dry-run is unavailable.",
                request_id=rid,
            )

        query = body.get("query", "")
        candidate = body.get("candidate", {})
        options = body.get("options")

        try:
            result = writer_service.dry_run_write(
                query=query,
                candidate=candidate,
                options=options,
            )
        except MemoryWriterDryRunUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_DRY_RUN_UNAVAILABLE,
                message="Memory writer dry-run is unavailable.",
                request_id=rid,
            )
        except MemoryWriterInvalidRequestError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MEMORY_DRY_RUN_REQUEST,
                message=str(exc),
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=INTERNAL_ERROR,
                message="An unexpected error occurred during dry-run.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        result["meta"] = {"requestId": rid, "timestamp": ts}
        return result

    # ── POST /memory/items/{memoryId}/update/dry-run ──

    @app.post(
        f"{prefix}/memory/items/{{memoryId}}/update/dry-run",
        tags=["Memory"],
        summary="Preview UPDATE operation (dry-run, no side effects)",
    )
    def memory_update_dry_run(
        request: Request,
        memoryId: str,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if writer_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_DRY_RUN_UNAVAILABLE,
                message="Memory writer dry-run is unavailable.",
                request_id=rid,
            )

        candidate = body.get("candidate", {})
        options = body.get("options")

        try:
            result = writer_service.dry_run_update(
                memoryId,
                candidate=candidate,
                options=options,
            )
        except MemoryWriterDryRunUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_DRY_RUN_UNAVAILABLE,
                message="Memory writer dry-run is unavailable.",
                request_id=rid,
            )
        except MemoryWriterInvalidIdError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MEMORY_ID,
                message=str(exc),
                request_id=rid,
            )
        except MemoryWriterTargetNotFoundError:
            return _make_error_json(
                status_code=404,
                code=MEMORY_NOT_FOUND,
                message="Memory item was not found.",
                request_id=rid,
            )
        except MemoryWriterInvalidRequestError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MEMORY_DRY_RUN_REQUEST,
                message=str(exc),
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=INTERNAL_ERROR,
                message="An unexpected error occurred during dry-run.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        result["meta"] = {"requestId": rid, "timestamp": ts}
        return result

    # ── POST /memory/items/{memoryId}/archive/dry-run ──

    @app.post(
        f"{prefix}/memory/items/{{memoryId}}/archive/dry-run",
        tags=["Memory"],
        summary="Preview ARCHIVE operation (dry-run, no side effects)",
    )
    def memory_archive_dry_run(
        request: Request,
        memoryId: str,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if writer_service is None:
            return _make_error_json(
                status_code=503,
                code=MEMORY_DRY_RUN_UNAVAILABLE,
                message="Memory writer dry-run is unavailable.",
                request_id=rid,
            )

        reason = body.get("reason")
        options = body.get("options")

        try:
            result = writer_service.dry_run_archive(
                memoryId,
                reason=reason,
                options=options,
            )
        except MemoryWriterDryRunUnavailableError:
            return _make_error_json(
                status_code=503,
                code=MEMORY_DRY_RUN_UNAVAILABLE,
                message="Memory writer dry-run is unavailable.",
                request_id=rid,
            )
        except MemoryWriterInvalidIdError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MEMORY_ID,
                message=str(exc),
                request_id=rid,
            )
        except MemoryWriterTargetNotFoundError:
            return _make_error_json(
                status_code=404,
                code=MEMORY_NOT_FOUND,
                message="Memory item was not found.",
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=INTERNAL_ERROR,
                message="An unexpected error occurred during dry-run.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        result["meta"] = {"requestId": rid, "timestamp": ts}
        return result


# ── Forbidden request fields ──

_FORBIDDEN_REQUEST_FIELDS = frozenset({
    "apiKey", "api_key", "baseUrl", "base_url",
    "authorization", "headers", "proxy",
    "systemPrompt", "developerPrompt",
    "tools", "toolSchema", "execute", "run",
    "stream", "force", "persist", "saveSession",
    "writeMemory", "autoMemory",
})


def _check_forbidden_fields(body: dict, rid: str) -> JSONResponse | None:
    """Check for forbidden fields in the request body. Returns error or None."""
    for field in _FORBIDDEN_REQUEST_FIELDS:
        if field in body:
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message=f"Field '{field}' is not allowed.",
                request_id=rid,
            )
    # Check nested options/overrides for forbidden fields
    for section_key in ("options", "overrides"):
        section = body.get(section_key)
        if isinstance(section, dict):
            for field in _FORBIDDEN_REQUEST_FIELDS:
                if field in section:
                    return _make_error_json(
                        status_code=400,
                        code=INVALID_AGENT_PREVIEW_REQUEST,
                        message=f"Field '{field}' is not allowed in {section_key}.",
                        request_id=rid,
                    )
    return None


def _register_preview_routes(
    app: FastAPI,
    config: DevWebApiConfig,
    preview_service: DevAgentPreviewService | None,
) -> None:
    """Register Phase 1E Agent Prompt Preview & Run Dry-Run routes."""

    prefix = config.api_prefix

    # ── POST /agent/prompt/preview ──

    @app.post(
        f"{prefix}/agent/prompt/preview",
        tags=["Agent"],
        summary="Preview agent prompt assembly (dry-run, no side effects)",
    )
    def agent_prompt_preview(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if preview_service is None:
            return _make_error_json(
                status_code=503,
                code=AGENT_PREVIEW_UNAVAILABLE,
                message="Agent preview is unavailable.",
                request_id=rid,
            )

        # Check for forbidden fields
        forbidden = _check_forbidden_fields(body, rid)
        if forbidden is not None:
            return forbidden

        # Validate message
        message = body.get("message", "")
        if not isinstance(message, str):
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message="message must be a string.",
                request_id=rid,
            )
        message = message.strip()
        if not message:
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message="message is required and must not be empty.",
                request_id=rid,
            )
        if len(message) > _MAX_MESSAGE_LENGTH:
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message=f"message is too long (max {_MAX_MESSAGE_LENGTH} characters).",
                request_id=rid,
            )

        # Validate session ID if provided
        session_id = body.get("sessionId")
        if session_id is not None:
            if not isinstance(session_id, str):
                return _make_error_json(
                    status_code=400,
                    code=INVALID_SESSION_ID,
                    message="sessionId must be a string.",
                    request_id=rid,
                )
            session_id = session_id.strip()
            validation_error = _validate_session_id(session_id)
            if validation_error:
                return _make_error_json(
                    status_code=400,
                    code=INVALID_SESSION_ID,
                    message=validation_error,
                    request_id=rid,
                )

        # Extract options with safe bounds
        options = body.get("options", {})
        if not isinstance(options, dict):
            options = {}

        include_history = options.get("includeHistory", True)
        if not isinstance(include_history, bool):
            include_history = True

        history_limit = options.get("historyLimit", 20)
        if not isinstance(history_limit, int) or history_limit < 0:
            history_limit = 20
        history_limit = min(history_limit, _MAX_HISTORY_LIMIT)

        include_memory_context = options.get("includeMemoryContext", True)
        if not isinstance(include_memory_context, bool):
            include_memory_context = True

        memory_query = options.get("memoryQuery", "")
        if not isinstance(memory_query, str):
            memory_query = ""
        memory_query = memory_query.strip()
        if len(memory_query) > _MAX_MEMORY_QUERY_LENGTH:
            memory_query = memory_query[:_MAX_MEMORY_QUERY_LENGTH]

        max_categories = options.get("maxCategories", 5)
        if not isinstance(max_categories, int) or max_categories < 0:
            max_categories = 5
        max_categories = min(max_categories, _MAX_CATEGORIES)

        max_memories = options.get("maxMemories", 10)
        if not isinstance(max_memories, int) or max_memories < 0:
            max_memories = 10
        max_memories = min(max_memories, _MAX_MEMORIES)

        include_system_preview = options.get("includeSystemPreview", False)
        if not isinstance(include_system_preview, bool):
            include_system_preview = False

        include_tool_metadata = options.get("includeToolMetadata", True)
        if not isinstance(include_tool_metadata, bool):
            include_tool_metadata = True

        # Extract overrides
        overrides = body.get("overrides", {})
        if not isinstance(overrides, dict):
            overrides = {}

        model_override = overrides.get("model")
        if model_override is not None and not isinstance(model_override, str):
            return _make_error_json(
                status_code=400,
                code=INVALID_MODEL_OVERRIDE,
                message="model override must be a string.",
                request_id=rid,
            )

        temperature_override = overrides.get("temperature")
        if temperature_override is not None:
            try:
                temperature_override = float(temperature_override)
            except (ValueError, TypeError):
                return _make_error_json(
                    status_code=400,
                    code=INVALID_TEMPERATURE,
                    message="temperature must be a number.",
                    request_id=rid,
                )

        max_tokens_override = overrides.get("maxOutputTokens")
        if max_tokens_override is not None:
            try:
                max_tokens_override = int(max_tokens_override)
            except (ValueError, TypeError):
                return _make_error_json(
                    status_code=400,
                    code=INVALID_MAX_OUTPUT_TOKENS,
                    message="maxOutputTokens must be an integer.",
                    request_id=rid,
                )

        try:
            result = preview_service.preview_prompt(
                message=message,
                session_id=session_id or None,
                include_history=include_history,
                history_limit=history_limit,
                include_memory_context=include_memory_context,
                memory_query=memory_query,
                max_categories=max_categories,
                max_memories=max_memories,
                include_system_preview=include_system_preview,
                include_tool_metadata=include_tool_metadata,
                model_override=model_override or None,
                temperature_override=temperature_override,
                max_tokens_override=max_tokens_override,
            )
        except AgentConfigUnavailableError:
            return _make_error_json(
                status_code=503,
                code=AGENT_CONFIG_UNAVAILABLE,
                message="Agent configuration is unavailable.",
                request_id=rid,
            )
        except InvalidSessionIdError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_SESSION_ID,
                message=str(exc),
                request_id=rid,
            )
        except InvalidModelOverrideError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MODEL_OVERRIDE,
                message=str(exc),
                request_id=rid,
            )
        except InvalidTemperatureError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_TEMPERATURE,
                message=str(exc),
                request_id=rid,
            )
        except InvalidMaxOutputTokensError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MAX_OUTPUT_TOKENS,
                message=str(exc),
                request_id=rid,
            )
        except AgentPromptAssemblyError:
            return _make_error_json(
                status_code=500,
                code=AGENT_PROMPT_ASSEMBLY_ERROR,
                message="Prompt assembly failed.",
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=INTERNAL_ERROR,
                message="An unexpected error occurred during preview.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── POST /agent/run/dry-run ──

    @app.post(
        f"{prefix}/agent/run/dry-run",
        tags=["Agent"],
        summary="Preview agent run capabilities (dry-run, no side effects)",
    )
    def agent_run_dry_run(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if preview_service is None:
            return _make_error_json(
                status_code=503,
                code=AGENT_PREVIEW_UNAVAILABLE,
                message="Agent preview is unavailable.",
                request_id=rid,
            )

        # Check for forbidden fields
        forbidden = _check_forbidden_fields(body, rid)
        if forbidden is not None:
            return forbidden

        # Validate message
        message = body.get("message", "")
        if not isinstance(message, str):
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message="message must be a string.",
                request_id=rid,
            )
        message = message.strip()
        if not message:
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message="message is required and must not be empty.",
                request_id=rid,
            )
        if len(message) > _MAX_MESSAGE_LENGTH:
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_PREVIEW_REQUEST,
                message=f"message is too long (max {_MAX_MESSAGE_LENGTH} characters).",
                request_id=rid,
            )

        # Validate session ID if provided
        session_id = body.get("sessionId")
        if session_id is not None:
            if not isinstance(session_id, str):
                return _make_error_json(
                    status_code=400,
                    code=INVALID_SESSION_ID,
                    message="sessionId must be a string.",
                    request_id=rid,
                )
            session_id = session_id.strip()
            validation_error = _validate_session_id(session_id)
            if validation_error:
                return _make_error_json(
                    status_code=400,
                    code=INVALID_SESSION_ID,
                    message=validation_error,
                    request_id=rid,
                )

        # Extract options
        options = body.get("options", {})
        if not isinstance(options, dict):
            options = {}

        include_history = options.get("includeHistory", True)
        if not isinstance(include_history, bool):
            include_history = True

        history_limit = options.get("historyLimit", 20)
        if not isinstance(history_limit, int) or history_limit < 0:
            history_limit = 20
        history_limit = min(history_limit, _MAX_HISTORY_LIMIT)

        include_memory_context = options.get("includeMemoryContext", True)
        if not isinstance(include_memory_context, bool):
            include_memory_context = True

        memory_query = options.get("memoryQuery", "")
        if not isinstance(memory_query, str):
            memory_query = ""
        memory_query = memory_query.strip()
        if len(memory_query) > _MAX_MEMORY_QUERY_LENGTH:
            memory_query = memory_query[:_MAX_MEMORY_QUERY_LENGTH]

        tools_requested = options.get("toolsRequested", False)
        if not isinstance(tools_requested, bool):
            tools_requested = False

        stream_requested = options.get("streamRequested", False)
        if not isinstance(stream_requested, bool):
            stream_requested = False

        auto_memory_requested = options.get("autoMemoryRequested", False)
        if not isinstance(auto_memory_requested, bool):
            auto_memory_requested = False

        # Extract overrides
        overrides = body.get("overrides", {})
        if not isinstance(overrides, dict):
            overrides = {}

        model_override = overrides.get("model")
        if model_override is not None and not isinstance(model_override, str):
            return _make_error_json(
                status_code=400,
                code=INVALID_MODEL_OVERRIDE,
                message="model override must be a string.",
                request_id=rid,
            )

        temperature_override = overrides.get("temperature")
        if temperature_override is not None:
            try:
                temperature_override = float(temperature_override)
            except (ValueError, TypeError):
                return _make_error_json(
                    status_code=400,
                    code=INVALID_TEMPERATURE,
                    message="temperature must be a number.",
                    request_id=rid,
                )

        max_tokens_override = overrides.get("maxOutputTokens")
        if max_tokens_override is not None:
            try:
                max_tokens_override = int(max_tokens_override)
            except (ValueError, TypeError):
                return _make_error_json(
                    status_code=400,
                    code=INVALID_MAX_OUTPUT_TOKENS,
                    message="maxOutputTokens must be an integer.",
                    request_id=rid,
                )

        try:
            result = preview_service.dry_run_agent(
                message=message,
                session_id=session_id or None,
                include_history=include_history,
                history_limit=history_limit,
                include_memory_context=include_memory_context,
                memory_query=memory_query,
                tools_requested=tools_requested,
                stream_requested=stream_requested,
                auto_memory_requested=auto_memory_requested,
                model_override=model_override or None,
                temperature_override=temperature_override,
                max_tokens_override=max_tokens_override,
            )
        except AgentConfigUnavailableError:
            return _make_error_json(
                status_code=503,
                code=AGENT_CONFIG_UNAVAILABLE,
                message="Agent configuration is unavailable.",
                request_id=rid,
            )
        except InvalidSessionIdError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_SESSION_ID,
                message=str(exc),
                request_id=rid,
            )
        except InvalidModelOverrideError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MODEL_OVERRIDE,
                message=str(exc),
                request_id=rid,
            )
        except InvalidTemperatureError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_TEMPERATURE,
                message=str(exc),
                request_id=rid,
            )
        except InvalidMaxOutputTokensError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_MAX_OUTPUT_TOKENS,
                message=str(exc),
                request_id=rid,
            )
        except AgentPromptAssemblyError:
            return _make_error_json(
                status_code=500,
                code=AGENT_PROMPT_ASSEMBLY_ERROR,
                message="Prompt assembly failed.",
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=INTERNAL_ERROR,
                message="An unexpected error occurred during dry-run.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result,
            "meta": {"requestId": rid, "timestamp": ts},
        }


def _register_agent_run_routes(
    app: FastAPI,
    config: DevWebApiConfig,
) -> None:
    """Register Phase 1F Agent Run routes (dev-only, SSE streaming).

    Routes:
        POST   /api/dev/v1/agent/runs                     Create Run
        GET    /api/dev/v1/agent/runs/{runId}             Run Status
        GET    /api/dev/v1/agent/runs/{runId}/events      SSE Stream
        POST   /api/dev/v1/agent/runs/{runId}/cancel      Cancel Run
    """

    prefix = config.api_prefix

    # ── POST /agent/runs ──

    @app.post(
        f"{prefix}/agent/runs",
        tags=["Agent"],
        summary="Create agent run (dev-only, no tools, streaming only)",
        status_code=202,
    )
    async def create_agent_run(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", "")

        if config.hermes_home is None:
            return _make_error_json(
                status_code=503,
                code=AGENT_RUN_DISABLED,
                message="Agent Run is unavailable (no HERMES_HOME).",
                request_id=rid,
            )

        from hermes_cli.dev_web_agent_run_service import (
            AgentRunService,
            AgentRunDisabledError,
            InvalidRequestError as RunInvalidRequestError,
            InvalidConfirmError,
            MissingDryRunError as RunMissingDryRunError,
            InvalidEffectsError,
            SessionNotFoundError as RunSessionNotFoundError,
            SessionBusyError as RunSessionBusyError,
            CapacityError,
            RateLimitedError,
            AgentRunError,
        )

        service = AgentRunService(
            hermes_home=config.hermes_home,
            source_root=Path(__file__).resolve().parents[1],
        )

        try:
            result = service.create_run(body, rid)
        except AgentRunDisabledError:
            return _make_error_json(
                status_code=503,
                code=AGENT_RUN_DISABLED,
                message=(
                    "Agent Run is disabled. "
                    "Enable with HERMES_AGENT_RUN_ENABLED=true."
                ),
                request_id=rid,
            )
        except InvalidConfirmError:
            return _make_error_json(
                status_code=400,
                code=INVALID_CONFIRMATION,
                message="confirmationText must be 'RUN'.",
                request_id=rid,
            )
        except RunMissingDryRunError:
            return _make_error_json(
                status_code=400,
                code=MISSING_DRY_RUN,
                message="dryRunPreviewed must be true.",
                request_id=rid,
            )
        except InvalidEffectsError:
            return _make_error_json(
                status_code=400,
                code=INVALID_ACKNOWLEDGED_EFFECTS,
                message="acknowledgedEffects must be exactly ['CALL_LLM', 'WRITE_SESSION'].",
                request_id=rid,
            )
        except RunInvalidRequestError as exc:
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_RUN_REQUEST,
                message=str(exc),
                request_id=rid,
            )
        except RunSessionNotFoundError:
            return _make_error_json(
                status_code=404,
                code=SESSION_NOT_FOUND,
                message="Session was not found.",
                request_id=rid,
            )
        except RunSessionBusyError:
            return _make_error_json(
                status_code=409,
                code=AGENT_SESSION_BUSY,
                message="Session already has an active run.",
                request_id=rid,
            )
        except CapacityError:
            return _make_error_json(
                status_code=409,
                code=AGENT_RUN_CAPACITY_REACHED,
                message="Global active run limit reached.",
                request_id=rid,
            )
        except RateLimitedError as exc:
            resp = _make_error_json(
                status_code=429,
                code=AGENT_RATE_LIMITED,
                message=str(exc),
                request_id=rid,
            )
            if exc.retry_after:
                resp.headers["Retry-After"] = str(int(exc.retry_after))
            return resp
        except AgentRunError:
            return _make_error_json(
                status_code=500,
                code=AGENT_RUN_FAILED,
                message="Agent run failed to start.",
                request_id=rid,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=INTERNAL_ERROR,
                message="An unexpected error occurred.",
                request_id=rid,
            )

        return JSONResponse(content=result, status_code=202)

    # ── GET /agent/runs/{runId} ──

    @app.get(
        f"{prefix}/agent/runs/{{runId}}",
        tags=["Agent"],
        summary="Get agent run status",
    )
    def get_agent_run_status(
        request: Request,
        runId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        from hermes_cli.dev_web_agent_run_service import (
            AgentRunService,
            AgentRunDisabledError,
            RunNotFoundError as RunRunNotFoundError,
        )
        from hermes_cli.dev_web_agent_run_models import validate_run_id

        if not validate_run_id(runId):
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_RUN_REQUEST,
                message="Invalid run ID format.",
                request_id=rid,
            )

        if config.hermes_home is None:
            return _make_error_json(
                status_code=503,
                code=AGENT_RUN_DISABLED,
                message="Agent Run is unavailable.",
                request_id=rid,
            )

        service = AgentRunService(
            hermes_home=config.hermes_home,
            source_root=Path(__file__).resolve().parents[1],
        )

        try:
            return service.get_run_status(runId, rid)
        except AgentRunDisabledError:
            return _make_error_json(
                status_code=503,
                code=AGENT_RUN_DISABLED,
                message="Agent Run is disabled.",
                request_id=rid,
            )
        except RunRunNotFoundError:
            return _make_error_json(
                status_code=404,
                code=AGENT_RUN_NOT_FOUND,
                message="Run not found.",
                request_id=rid,
            )

    # ── GET /agent/runs/{runId}/events ──

    @app.get(
        f"{prefix}/agent/runs/{{runId}}/events",
        tags=["Agent"],
        summary="SSE stream for agent run events",
    )
    async def stream_agent_run_events(
        request: Request,
        runId: str,
    ):
        from starlette.responses import StreamingResponse
        from hermes_cli.dev_web_agent_run_models import validate_run_id
        from hermes_cli.dev_web_agent_run_registry import get_run_registry
        from hermes_cli.dev_web_agent_run_sse import (
            stream_run_events,
            SSE_HEADERS,
        )

        rid = getattr(request.state, "request_id", "")

        if not validate_run_id(runId):
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_RUN_REQUEST,
                message="Invalid run ID format.",
                request_id=rid,
            )

        registry = get_run_registry()
        if registry.try_get_run(runId) is None:
            return _make_error_json(
                status_code=404,
                code=AGENT_RUN_NOT_FOUND,
                message="Run not found.",
                request_id=rid,
            )

        # Parse Last-Event-ID header
        last_event_id = None
        lei_header = request.headers.get("Last-Event-ID")
        if lei_header:
            try:
                last_event_id = int(lei_header)
            except ValueError:
                return _make_error_json(
                    status_code=400,
                    code=INVALID_AGENT_RUN_REQUEST,
                    message="Invalid Last-Event-ID header.",
                    request_id=rid,
                )

        # Create disconnect event
        disconnect_event = asyncio.Event()

        async def event_generator():
            try:
                async for event_text in stream_run_events(
                    runId, registry, last_event_id, disconnect_event,
                ):
                    yield event_text
            except Exception:
                yield ""

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    # ── POST /agent/runs/{runId}/cancel ──

    @app.post(
        f"{prefix}/agent/runs/{{runId}}/cancel",
        tags=["Agent"],
        summary="Cancel agent run (idempotent)",
    )
    async def cancel_agent_run(
        request: Request,
        runId: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        from hermes_cli.dev_web_agent_run_service import (
            AgentRunService,
            AgentRunDisabledError,
            RunNotFoundError as RunRunNotFoundError,
        )
        from hermes_cli.dev_web_agent_run_models import validate_run_id

        if not validate_run_id(runId):
            return _make_error_json(
                status_code=400,
                code=INVALID_AGENT_RUN_REQUEST,
                message="Invalid run ID format.",
                request_id=rid,
            )

        if config.hermes_home is None:
            return _make_error_json(
                status_code=503,
                code=AGENT_RUN_DISABLED,
                message="Agent Run is unavailable.",
                request_id=rid,
            )

        service = AgentRunService(
            hermes_home=config.hermes_home,
            source_root=Path(__file__).resolve().parents[1],
        )

        try:
            return service.cancel_run(runId, rid)
        except AgentRunDisabledError:
            return _make_error_json(
                status_code=503,
                code=AGENT_RUN_DISABLED,
                message="Agent Run is disabled.",
                request_id=rid,
            )
        except RunRunNotFoundError:
            return _make_error_json(
                status_code=404,
                code=AGENT_RUN_NOT_FOUND,
                message="Run not found.",
                request_id=rid,
            )


# ── Phase 1G: Tool Policy Read-Only Routes ──


def _tool_dto_to_camel(obj: Any) -> Any:
    """Recursively convert a frozen dataclass DTO to a camelCase dict.

    Only whitelisted DTO fields are included. This function handles:
    - Nested dataclasses (recursive conversion)
    - Tuples/lists → list
    - Dicts → dict with camelCase keys
    - Primitives → as-is
    """
    import dataclasses

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for field in dataclasses.fields(obj):
            camel_key = _snake_to_camel(field.name)
            result[camel_key] = _tool_dto_to_camel(getattr(obj, field.name))
        return result
    if isinstance(obj, tuple):
        return [_tool_dto_to_camel(item) for item in obj]
    if isinstance(obj, list):
        return [_tool_dto_to_camel(item) for item in obj]
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _tool_dto_to_camel(v) for k, v in obj.items()}
    return obj


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def _register_tool_policy_routes(
    app: FastAPI,
    config: DevWebApiConfig,
    tool_policy_service: DevToolPolicyQueryService | None,
) -> None:
    """Register Phase 1G Tool Policy read-only routes."""
    prefix = config.api_prefix

    # ── GET /tools/policy ──

    @app.get(
        f"{prefix}/tools/policy",
        tags=["Tools"],
        summary="Tool policy status overview",
    )
    def get_tool_policy_status(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        if tool_policy_service is None:
            return _make_error_json(
                status_code=503,
                code="TOOL_POLICY_UNAVAILABLE",
                message="Tool policy service is unavailable.",
                request_id=rid,
            )

        try:
            dto = tool_policy_service.get_policy_status()
        except ToolPolicyDataInvalidError as exc:
            return _make_error_json(
                status_code=500,
                code="TOOL_POLICY_DATA_INVALID",
                message=exc.message,
                request_id=rid,
            )

        return {
            "data": _tool_dto_to_camel(dto),
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /tools/catalog ──

    @app.get(
        f"{prefix}/tools/catalog",
        tags=["Tools"],
        summary="Filtered, paginated tool catalog",
    )
    def list_tool_catalog(
        request: Request,
        q: str | None = Query(
            default=None,
            max_length=_MAX_QUERY_LENGTH,
            description="Search tool names and rationales.",
        ),
        risk: str | None = Query(
            default=None,
            description="Filter by risk level.",
        ),
        capability: str | None = Query(
            default=None,
            description="Filter by capability.",
        ),
        policyStatus: str | None = Query(
            default=None,
            alias="policyStatus",
            description="Filter by policy status.",
        ),
        page: int = Query(
            default=1,
            ge=1,
            description="Page number (1-based).",
        ),
        pageSize: int = Query(
            default=25,
            ge=1,
            le=_MAX_PAGE_SIZE,
            alias="pageSize",
            description="Items per page.",
        ),
        sort: str = Query(
            default="nameAsc",
            description="Sort order.",
        ),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        if tool_policy_service is None:
            return _make_error_json(
                status_code=503,
                code="TOOL_POLICY_UNAVAILABLE",
                message="Tool policy service is unavailable.",
                request_id=rid,
            )

        # Check for dangerous query parameters
        raw_params = dict(request.query_params)
        for param_name in raw_params:
            if param_name.lower() in _DANGEROUS_PARAM_NAMES:
                return _make_error_json(
                    status_code=400,
                    code="INVALID_TOOL_POLICY_QUERY",
                    message=f"Dangerous query parameter rejected: {param_name}",
                    request_id=rid,
                )

        try:
            query = validate_catalog_query(
                q=q,
                risk=risk,
                capability=capability,
                policy_status=policyStatus,
                page=page,
                page_size=pageSize,
                sort=sort,
            )
        except InvalidToolPolicyQueryError as exc:
            return _make_error_json(
                status_code=400,
                code="INVALID_TOOL_POLICY_QUERY",
                message=exc.message,
                request_id=rid,
            )
        except InvalidToolRiskError as exc:
            return _make_error_json(
                status_code=400,
                code="INVALID_TOOL_RISK",
                message=exc.message,
                request_id=rid,
            )
        except InvalidToolCapabilityError as exc:
            return _make_error_json(
                status_code=400,
                code="INVALID_TOOL_CAPABILITY",
                message=exc.message,
                request_id=rid,
            )
        except InvalidToolPolicyStatusError as exc:
            return _make_error_json(
                status_code=400,
                code="INVALID_TOOL_POLICY_STATUS",
                message=exc.message,
                request_id=rid,
            )
        except InvalidToolSortError as exc:
            return _make_error_json(
                status_code=400,
                code="INVALID_TOOL_SORT",
                message=exc.message,
                request_id=rid,
            )

        try:
            dto = tool_policy_service.list_tool_catalog(query)
        except ToolPolicyDataInvalidError as exc:
            return _make_error_json(
                status_code=500,
                code="TOOL_POLICY_DATA_INVALID",
                message=exc.message,
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": _tool_dto_to_camel(dto),
            "meta": {"requestId": rid, "timestamp": ts},
        }


# ── Phase 1G-03: Tool Schema Preview Read-Only Routes ──


def _register_schema_preview_routes(
    app: FastAPI,
    config: DevWebApiConfig,
) -> None:
    """Register Phase 1G-03 Tool Schema Preview read-only routes.

    Two GET-only routes that expose safe, redacted schema previews for all
    71 tools in the policy inventory. No POST/PATCH/PUT/DELETE, no tool
    execution, no provider schema sending, no handler invocation.
    """
    prefix = config.api_prefix

    # ── GET /tools/schemas ──

    @app.get(
        f"{prefix}/tools/schemas",
        tags=["Tools"],
        summary="Schema preview catalog for all tools",
        description="Returns safe, redacted schema previews for all 71 tools "
        "in the policy inventory. No handler, callable, source path, or "
        "secret is exposed. All data is read-only and derived from the "
        "static policy module and optional schema source.",
    )
    def list_tool_schema_previews(request: Request) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        catalog = _list_schema_previews()

        return {
            "data": catalog.to_safe_dict(),
            "meta": {"requestId": rid, "timestamp": ts},
        }

    # ── GET /tools/schemas/{canonicalName} ──

    @app.get(
        f"{prefix}/tools/schemas/{{canonicalName}}",
        tags=["Tools"],
        summary="Schema preview for a single tool",
        description="Returns the safe, redacted schema preview for a single "
        "tool by its exact canonical name. No fuzzy matching, no case "
        "folding. Returns 404 for tools not in the policy inventory.",
    )
    def get_tool_schema_preview(
        request: Request,
        canonicalName: str,
    ) -> dict:
        rid = getattr(request.state, "request_id", "")

        result = _get_schema_preview(canonicalName)

        if not result.found:
            return _make_error_json(
                status_code=404,
                code="TOOL_SCHEMA_PREVIEW_NOT_FOUND",
                message=f"Tool schema preview not found for '{canonicalName}'.",
                request_id=rid,
            )

        ts = _utc_now_iso()
        return {
            "data": result.to_safe_dict(),
            "meta": {"requestId": rid, "timestamp": ts},
        }


# ── Phase 1G-04: Tool Dry-Run Read-Only Routes ──


def _register_tool_dry_run_routes(
    app: FastAPI,
    config: DevWebApiConfig,
) -> None:
    """Register Phase 1G-04 Tool Dry-Run read-only route.

    One POST route that exposes the existing pure dry-run policy engine
    as a local-only, non-mutating decision endpoint.

    Phase 1G-04-07: Internal audit writer integration.
    After computing the dry-run policy decision, a dev-only local JSONL
    audit event is written. auditWritten in the response reflects whether
    the audit event was successfully written, not tool execution.

    Guarantees:
      - No tool handler called
      - No tool dispatch
      - No provider schema sent
      - No provider API called
      - Audit write failure does not enable execution
      - No runtime mutation
      - No STATIC_ALLOWLIST mutation
    """
    prefix = config.api_prefix

    # ── Error codes ──

    _TOOL_DRY_RUN_INVALID_REQUEST = "TOOL_DRY_RUN_INVALID_REQUEST"
    _TOOL_DRY_RUN_INVALID_CANONICAL_NAME = "TOOL_DRY_RUN_INVALID_CANONICAL_NAME"
    _TOOL_DRY_RUN_INVALID_ARGUMENTS = "TOOL_DRY_RUN_INVALID_ARGUMENTS"
    _TOOL_DRY_RUN_POLICY_UNAVAILABLE = "TOOL_DRY_RUN_POLICY_UNAVAILABLE"
    _TOOL_DRY_RUN_INTERNAL_ERROR = "TOOL_DRY_RUN_INTERNAL_ERROR"

    # Validation limits
    _MAX_CANONICAL_NAME_LENGTH = 256
    _MAX_SOURCE_CONTEXT_LENGTH = 512
    _MAX_UI_ORIGIN_LENGTH = 256
    _MAX_REQUEST_ID_LENGTH = 128

    # ── Phase 2C: write preview branch (same /tools/dry-run path, no new route) ──

    _WRITE_INVALID_TOOL = "WRITE_INVALID_TOOL"
    _WRITE_INVALID_ARGUMENTS = "WRITE_INVALID_ARGUMENTS"
    _WRITE_INTERNAL_ERROR = "WRITE_INTERNAL_ERROR"

    def _handle_write_preview(
        body: dict[str, Any],
        rid: str,
        ts: str,
    ) -> dict:
        """Handle a Phase 2C write-preview (dry-run) on the dry-run path.

        Reuses ``POST /tools/dry-run`` with ``body.mode='write_preview'`` —
        no new route is added. The preview NEVER writes a file.
        """
        tool_id = body.get("toolId")
        if not isinstance(tool_id, str) or not tool_id.strip():
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="toolId is required for write_preview mode.",
                request_id=rid,
            )
        tool_id = tool_id.strip()
        if not _is_phase_2c_write_tool(tool_id):
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="toolId is not a Phase 2C write tool.",
                request_id=rid,
            )
        arguments = body.get("arguments")
        if arguments is not None and not isinstance(arguments, dict):
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_ARGUMENTS,
                message="arguments must be a JSON object or null.",
                request_id=rid,
            )
        hermes_home_override = (
            str(config.hermes_home) if config.hermes_home is not None else None
        )
        try:
            preview = _build_write_preview(
                tool_id, arguments, hermes_home=hermes_home_override
            )
        except Exception:
            return _make_error_json(
                status_code=500, code=_WRITE_INTERNAL_ERROR,
                message="An unexpected error occurred during write preview.",
                request_id=rid,
            )
        preview["mode"] = "write_preview"
        return {"data": preview, "meta": {"requestId": rid, "timestamp": ts}}

    def _handle_rollback_preview(
        body: dict[str, Any],
        rid: str,
        ts: str,
    ) -> dict:
        """Phase 2C-H1 rollback preview (dry-run) on the dry-run path.

        Reuses ``POST /tools/dry-run`` with ``body.mode='rollback_preview'`` —
        no new route. Loads the stored manifest, checks the current sandbox
        state, and returns the preview + a rollback-scoped confirmation token.
        NEVER mutates the filesystem.
        """
        rollback_id = body.get("rollbackId")
        if not isinstance(rollback_id, str) or not rollback_id.strip():
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="rollbackId is required for rollback_preview mode.",
                request_id=rid,
            )
        rollback_id = rollback_id.strip()
        if not _is_valid_rollback_id(rollback_id):
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="rollbackId is not a valid rollback manifest id.",
                request_id=rid,
            )
        hermes_home_override = (
            str(config.hermes_home) if config.hermes_home is not None else None
        )
        try:
            preview = _build_rollback_execution_preview(
                rollback_id, hermes_home=hermes_home_override
            )
        except Exception:
            return _make_error_json(
                status_code=500, code=_WRITE_INTERNAL_ERROR,
                message="An unexpected error occurred during rollback preview.",
                request_id=rid,
            )
        preview["mode"] = "rollback_preview"
        # Optionally surface the known rollback manifest ids so the UI can list
        # them without a new route.
        if body.get("includeManifestList"):
            preview["manifestList"] = _list_rollback_manifests(
                limit=50, hermes_home=hermes_home_override
            )
        return {"data": preview, "meta": {"requestId": rid, "timestamp": ts}}

    # ── POST /tools/dry-run ──

    @app.post(
        f"{prefix}/tools/dry-run",
        tags=["Tools"],
        summary="Evaluate dry-run policy for a proposed tool call",
        description="Returns a policy decision (would_allow, would_block, would_redact, "
        "requires_review) without executing the tool. No tool handler is called, "
        "no provider schema is sent. A dev-only audit record is written when the "
        "audit write succeeds (auditWritten=true does not imply tool execution).",
    )
    def tool_dry_run(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        # Phase 2C: write-preview branch (same path, no new route).
        mode = body.get("mode")
        if mode == "write_preview":
            return _handle_write_preview(body, rid, ts)

        # Phase 2C-H1: rollback-preview branch (same path, no new route).
        if mode == "rollback_preview":
            return _handle_rollback_preview(body, rid, ts)

        # Step 1: Record start time for duration measurement
        import time
        start_time = time.monotonic()

        # Step 2: Validate canonicalName
        canonical_name = body.get("canonicalName")
        if canonical_name is None:
            return _make_error_json(
                status_code=400,
                code=_TOOL_DRY_RUN_INVALID_CANONICAL_NAME,
                message="canonicalName is required.",
                request_id=rid,
            )
        if not isinstance(canonical_name, str):
            return _make_error_json(
                status_code=400,
                code=_TOOL_DRY_RUN_INVALID_CANONICAL_NAME,
                message="canonicalName must be a string.",
                request_id=rid,
            )
        canonical_name = canonical_name.strip()
        if not canonical_name:
            return _make_error_json(
                status_code=400,
                code=_TOOL_DRY_RUN_INVALID_CANONICAL_NAME,
                message="canonicalName must not be empty.",
                request_id=rid,
            )
        if len(canonical_name) > _MAX_CANONICAL_NAME_LENGTH:
            return _make_error_json(
                status_code=400,
                code=_TOOL_DRY_RUN_INVALID_CANONICAL_NAME,
                message=f"canonicalName exceeds maximum length ({_MAX_CANONICAL_NAME_LENGTH}).",
                request_id=rid,
            )

        # Step 4: Validate argumentsPreview (optional, must be object if present)
        arguments_preview = body.get("argumentsPreview")
        if arguments_preview is not None:
            if not isinstance(arguments_preview, dict):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_ARGUMENTS,
                    message="argumentsPreview must be a JSON object or null.",
                    request_id=rid,
                )

        # Step 5: Validate optional string fields
        source_context = body.get("sourceContext")
        if source_context is not None:
            if not isinstance(source_context, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message="sourceContext must be a string or null.",
                    request_id=rid,
                )
            if len(source_context) > _MAX_SOURCE_CONTEXT_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message=f"sourceContext exceeds maximum length ({_MAX_SOURCE_CONTEXT_LENGTH}).",
                    request_id=rid,
                )

        ui_origin = body.get("uiOrigin")
        if ui_origin is not None:
            if not isinstance(ui_origin, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message="uiOrigin must be a string or null.",
                    request_id=rid,
                )
            if len(ui_origin) > _MAX_UI_ORIGIN_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message=f"uiOrigin exceeds maximum length ({_MAX_UI_ORIGIN_LENGTH}).",
                    request_id=rid,
                )

        request_id_field = body.get("requestId")
        if request_id_field is not None:
            if not isinstance(request_id_field, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message="requestId must be a string or null.",
                    request_id=rid,
                )
            if len(request_id_field) > _MAX_REQUEST_ID_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message=f"requestId exceeds maximum length ({_MAX_REQUEST_ID_LENGTH}).",
                    request_id=rid,
                )

        # Step 5a: Validate issueConfirmationToken (optional boolean)
        issue_confirmation_token_flag = body.get("issueConfirmationToken")
        if issue_confirmation_token_flag is not None:
            if not isinstance(issue_confirmation_token_flag, bool):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_DRY_RUN_INVALID_REQUEST,
                    message="issueConfirmationToken must be a boolean or null.",
                    request_id=rid,
                )

        # Step 6: Call the pure dry-run policy engine
        try:
            result = _dry_run_tool_policy(
                canonical_name,
                arguments_preview,
                source_context=source_context,
                ui_origin=ui_origin,
            )
        except Exception as exc:
            # Defensive: policy inventory load failure
            exc_name = type(exc).__name__
            if "import" in exc_name.lower() or "module" in exc_name.lower():
                return _make_error_json(
                    status_code=503,
                    code=_TOOL_DRY_RUN_POLICY_UNAVAILABLE,
                    message="Dry-run policy is unavailable.",
                    request_id=rid,
                )
            return _make_error_json(
                status_code=500,
                code=_TOOL_DRY_RUN_INTERNAL_ERROR,
                message="An unexpected error occurred during dry-run evaluation.",
                request_id=rid,
            )

        # Step 7: Compute duration
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Step 7a + 8: Build audit event, then compute dryRunDecisionDigest
        # bound to the REAL audit eventId / timestamp / expiry.
        #
        # Phase 1G-04-30: the digest must be computed with the same
        # audit_event_id / created_at / expires_at that the execute gate
        # recomputes from the historical audit lookup (eventId, timestamp,
        # timestamp+TTL). Computing it with audit_event_id=None here made the
        # dry-run response/token digest diverge from the execute-derived
        # digest, blocking the controlled execution chain with
        # blocked_digest_mismatch. Build the event first, extract its real
        # eventId/timestamp, compute the digest consistently, patch the
        # event, then write.
        dry_run_decision_digest = None
        digest_algorithm = None
        digest_package_version = None
        canonicalization_version = None
        audit_written = False
        audit_error_reason = None
        try:
            event = _build_dry_run_audit_event(
                dry_run_result=result,
                source_context=source_context,
                ui_origin=ui_origin,
                request_id=request_id_field or rid,
                duration_ms=duration_ms,
                result_status="ok",
                dry_run_decision_digest=None,  # patched below
                digest_algorithm=None,
                digest_package_version=None,
                canonicalization_version=None,
            )
            try:
                from hermes_cli.dev_web_tool_execute_digest import (
                    build_dry_run_decision_digest_package,
                    DIGEST_ALGORITHM as _DIGEST_ALGO,
                    DIGEST_PACKAGE_VERSION as _DIGEST_PKG_VER,
                    CANONICALIZATION_VERSION as _CANON_VER,
                )
                from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST
                from hermes_cli.dev_web_tool_execute_preflight import (
                    _DRY_RUN_TTL_SECONDS as _DRY_RUN_TTL,
                )
                from datetime import datetime as _dt, timezone as _tz, timedelta as _td

                real_event_id = event.get("eventId")
                created_at = event.get("timestamp")
                expires_at = None
                if isinstance(created_at, str) and created_at:
                    try:
                        expires_at = (
                            _dt.fromisoformat(created_at)
                            + _td(seconds=_DRY_RUN_TTL)
                        ).isoformat()
                    except ValueError:
                        expires_at = None

                digest_pkg_result = build_dry_run_decision_digest_package(
                    dry_run_request_id=request_id_field or rid,
                    canonical_name=result.canonical_name,
                    risk_tier=result.risk_tier,
                    policy_decision=result.decision,
                    allowlisted=result.canonical_name in STATIC_ALLOWLIST,
                    audit_written=True,  # Will be true after audit write
                    audit_event_id=real_event_id,
                    arguments=arguments_preview if isinstance(arguments_preview, dict) else None,
                    created_at=created_at,
                    expires_at=expires_at,
                )
                if digest_pkg_result.success:
                    dry_run_decision_digest = digest_pkg_result.digest
                    digest_algorithm = _DIGEST_ALGO
                    digest_package_version = _DIGEST_PKG_VER
                    canonicalization_version = _CANON_VER
            except Exception:
                # Digest computation failure does not affect dry-run response
                pass

            # Patch the event with the consistently-computed digest fields
            event["dryRunDecisionDigest"] = dry_run_decision_digest
            event["digestAlgorithm"] = digest_algorithm
            event["digestPackageVersion"] = digest_package_version
            event["canonicalizationVersion"] = canonicalization_version

            audit_result = _write_dry_run_audit_event(
                event,
                hermes_home=(
                    config.hermes_home
                    if config.hermes_home is not None
                    else None
                ),
            )
            audit_written = audit_result.written
            if not audit_written and audit_result.error_code:
                audit_error_reason = audit_result.error_code
        except Exception:
            # Audit write failure must not enable execution
            audit_written = False

        # Step 9: Build response with audit status
        response_data = result.to_safe_dict()
        response_data["auditWritten"] = audit_written

        # Step 9b: Include digest fields in response (Phase 1G-04-22)
        response_data["dryRunDecisionDigest"] = dry_run_decision_digest
        response_data["digestAlgorithm"] = digest_algorithm
        response_data["digestPackageVersion"] = digest_package_version
        response_data["canonicalizationVersion"] = canonicalization_version

        # If audit write failed, add a safe policy note
        if not audit_written and audit_error_reason:
            notes = list(response_data.get("policyNotes", []))
            notes.append(
                "Audit write failed; dry-run decision returned without execution."
            )
            response_data["policyNotes"] = notes
            reasons = list(response_data.get("reasonCodes", []))
            reasons.append("AUDIT_WRITE_FAILED")
            response_data["reasonCodes"] = reasons

        # Step 9a: Issue confirmation token if requested and eligible
        if (
            issue_confirmation_token_flag is True
            and result.decision == "would_allow"
            and audit_written
            and result.canonical_name in _DRY_RUN_STATIC_ALLOWLIST
        ):
            try:
                from hermes_cli.dev_web_tool_execute_preflight import (
                    DryRunHistoricalLookupResult,
                )
                # Build a minimal dry-run record for token issuance
                dry_run_record_for_token = DryRunHistoricalLookupResult(
                    found=True,
                    error_code=None,
                    dry_run_request_id=request_id_field or rid,
                    canonical_name=result.canonical_name,
                    decision=result.decision,
                    risk_tier=result.risk_tier,
                    policy_version=None,
                    arguments_digest=None,
                    dry_run_decision_digest=None,
                    audit_written=True,
                    audit_event_id=audit_result.event_id if audit_result.written else None,
                    created_at=_utc_now_iso(),
                    expires_at=None,
                    lookup_source=None,
                    redaction_status="applied" if result.forbidden_fields else "none",
                )
                token_result = _issue_confirmation_token(
                    hermes_home=(
                        config.hermes_home
                        if config.hermes_home is not None
                        else None
                    ),
                    dry_run_record=dry_run_record_for_token,
                    canonical_name=result.canonical_name,
                    risk_tier=result.risk_tier,
                    policy_version=None,
                    dry_run_request_id=request_id_field or rid,
                    dry_run_decision_digest=dry_run_decision_digest,
                    audit_event_id=audit_result.event_id if audit_result.written else None,
                    arguments_digest=None,
                    redaction_version=None,
                )
                if token_result.issued and token_result.raw_token is not None:
                    response_data["confirmationToken"] = token_result.raw_token
                    response_data["confirmationTokenId"] = token_result.token_id
                    response_data["confirmationTokenExpiresAt"] = token_result.expires_at
            except Exception:
                # Token issuance failure does not affect dry-run response
                pass

        # Step 10: Return safe response envelope
        return {
            "data": response_data,
            "meta": {"requestId": rid, "timestamp": ts},
        }


def _register_tool_execute_routes(
    app: FastAPI,
    config: DevWebApiConfig,
) -> None:
    """Register Phase 1G-04-11 tool execute gate skeleton routes.

    Safety guarantees:
      - Blocked-by-default: all requests return blocked
      - No tool handler called
      - No tool dispatch
      - No provider schema sent
      - No provider API called
      - No STATIC_ALLOWLIST mutation
      - No audit file write (skeleton only)
      - No runtime mutation
    """
    prefix = config.api_prefix

    # ── Error codes ──

    _TOOL_EXECUTE_INVALID_REQUEST = "TOOL_EXECUTE_INVALID_REQUEST"
    _TOOL_EXECUTE_INVALID_CANONICAL_NAME = "TOOL_EXECUTE_INVALID_CANONICAL_NAME"
    _TOOL_EXECUTE_INVALID_ARGUMENTS = "TOOL_EXECUTE_INVALID_ARGUMENTS"
    _TOOL_EXECUTE_INVALID_FIELD = "TOOL_EXECUTE_INVALID_FIELD"
    _TOOL_EXECUTE_INTERNAL_ERROR = "TOOL_EXECUTE_INTERNAL_ERROR"

    # Validation limits
    _MAX_CANONICAL_NAME_LENGTH = 256
    _MAX_DRY_RUN_REQUEST_ID_LENGTH = 256
    _MAX_DRY_RUN_DIGEST_LENGTH = 256
    _MAX_CONFIRMATION_TOKEN_LENGTH = 512
    _MAX_REQUEST_ID_LENGTH = 128
    _MAX_SOURCE_CONTEXT_LENGTH = 256
    _MAX_UI_ORIGIN_LENGTH = 256
    _MAX_CLIENT_CREATED_AT_LENGTH = 64

    # ── Phase 2B: Provider round-trip helper (reuses this route, no new path) ──

    _PROVIDER_INVALID_REQUEST = "PROVIDER_INVALID_REQUEST"
    _PROVIDER_INVALID_MODE = "PROVIDER_INVALID_MODE"
    _PROVIDER_INVALID_MESSAGE = "PROVIDER_INVALID_MESSAGE"
    _PROVIDER_INVALID_ALLOWED_TOOLS = "PROVIDER_INVALID_ALLOWED_TOOLS"
    _PROVIDER_INTERNAL_ERROR = "PROVIDER_INTERNAL_ERROR"
    _PROVIDER_VALID_MODES = ("disabled", "fake", "real")
    _MAX_PROVIDER_MESSAGE_LENGTH = 4000
    _MAX_ALLOWED_TOOLS = 32
    _MAX_ALLOWED_TOOL_NAME_LENGTH = 128

    def _handle_provider_roundtrip(
        request: Request,
        body: dict[str, Any],
        rid: str,
        ts: str,
    ) -> dict:
        """Handle a Phase 2B provider round-trip request on the execute route.

        Reuses the existing ``POST /tools/execute`` path (no new route). The
        provider round-trip is fake-by-default; real mode is blocked unless
        fully enabled. Provider-requested tool calls flow through the existing
        controlled execution chain.
        """
        from hermes_cli.dev_web_provider_roundtrip import run_provider_tool_roundtrip

        # providerMode (default disabled)
        provider_mode = body.get("providerMode", "disabled")
        if not isinstance(provider_mode, str):
            return _make_error_json(
                status_code=400,
                code=_PROVIDER_INVALID_MODE,
                message="providerMode must be a string (disabled, fake, or real).",
                request_id=rid,
            )
        provider_mode = provider_mode.strip().lower()
        if provider_mode not in _PROVIDER_VALID_MODES:
            return _make_error_json(
                status_code=400,
                code=_PROVIDER_INVALID_MODE,
                message="providerMode must be one of: disabled, fake, real.",
                request_id=rid,
            )

        # message
        message = body.get("message")
        if message is None:
            return _make_error_json(
                status_code=400,
                code=_PROVIDER_INVALID_MESSAGE,
                message="message is required for provider round-trip mode.",
                request_id=rid,
            )
        if not isinstance(message, str):
            return _make_error_json(
                status_code=400,
                code=_PROVIDER_INVALID_MESSAGE,
                message="message must be a string.",
                request_id=rid,
            )
        message = message.strip()
        if not message:
            return _make_error_json(
                status_code=400,
                code=_PROVIDER_INVALID_MESSAGE,
                message="message must not be empty.",
                request_id=rid,
            )
        if len(message) > _MAX_PROVIDER_MESSAGE_LENGTH:
            return _make_error_json(
                status_code=400,
                code=_PROVIDER_INVALID_MESSAGE,
                message=f"message exceeds maximum length ({_MAX_PROVIDER_MESSAGE_LENGTH}).",
                request_id=rid,
            )

        # allowedToolIds (optional list of strings)
        allowed_tool_ids_raw = body.get("allowedToolIds")
        selected: frozenset[str] | None = None
        if allowed_tool_ids_raw is not None:
            if not isinstance(allowed_tool_ids_raw, list):
                return _make_error_json(
                    status_code=400,
                    code=_PROVIDER_INVALID_ALLOWED_TOOLS,
                    message="allowedToolIds must be an array of strings or null.",
                    request_id=rid,
                )
            if len(allowed_tool_ids_raw) > _MAX_ALLOWED_TOOLS:
                return _make_error_json(
                    status_code=400,
                    code=_PROVIDER_INVALID_ALLOWED_TOOLS,
                    message=f"allowedToolIds exceeds maximum length ({_MAX_ALLOWED_TOOLS}).",
                    request_id=rid,
                )
            cleaned: set[str] = set()
            for item in allowed_tool_ids_raw:
                if not isinstance(item, str):
                    return _make_error_json(
                        status_code=400,
                        code=_PROVIDER_INVALID_ALLOWED_TOOLS,
                        message="allowedToolIds entries must be strings.",
                        request_id=rid,
                    )
                item = item.strip()
                if not item or len(item) > _MAX_ALLOWED_TOOL_NAME_LENGTH:
                    return _make_error_json(
                        status_code=400,
                        code=_PROVIDER_INVALID_ALLOWED_TOOLS,
                        message="allowedToolIds entries must be non-empty bounded strings.",
                        request_id=rid,
                    )
                cleaned.add(item)
            selected = frozenset(cleaned) if cleaned else None

        hermes_home_override = (
            str(config.hermes_home) if config.hermes_home is not None else None
        )

        # Phase 2C: if the provider request targets Phase 2C write tools or runs
        # in preview-only write mode, generate a write PREVIEW only — never
        # auto-execute. Reuses the same /tools/execute path (no new route).
        provider_write_mode = body.get("providerWriteMode")
        write_tool_ids = [t for t in (selected or ()) if _is_phase_2c_write_tool(t)]
        if provider_write_mode == "preview_only" or write_tool_ids:
            target_write_tool = write_tool_ids[0] if write_tool_ids else "dev_sandbox_file_write"
            try:
                wp_preview = _build_provider_write_preview(
                    message,
                    target_write_tool,
                    hermes_home=hermes_home_override,
                    provider_mode=provider_mode,
                )
            except Exception:
                return _make_error_json(
                    status_code=500, code=_PROVIDER_INTERNAL_ERROR,
                    message="An unexpected error occurred during provider write preview.",
                    request_id=rid,
                )
            data: dict[str, Any] = {
                "status": "blocked",
                "mode": "provider_roundtrip",
                "providerMode": provider_mode,
                "providerRequestId": wp_preview.get("writePlanId"),
                "providerResponseId": None,
                "providerSchemaSent": True,
                "providerApiCalled": provider_mode == "fake",
                "externalNetworkCalled": False,
                "readOnlyOnly": False,
                "toolWriteDisabled": True,
                "writePreviewGenerated": True,
                "writeExecuted": False,
                "requiresUserConfirmation": True,
                "toolCalls": [
                    {
                        "id": "ptc_write_preview",
                        "name": target_write_tool,
                        "arguments": {"targetPath": wp_preview.get("targetRelativePath")},
                        "status": "blocked",
                        "blockedReason": wp_preview.get("blockedReason"),
                    }
                ],
                "toolResults": [],
                "finalAnswer": (
                    "Provider write preview generated. Auto-execution denied; "
                    "user confirmation required."
                ),
                "providerAuditIds": [],
                "blockedReason": wp_preview.get("blockedReason"),
                "schemaSummary": {
                    "schemaVersion": 1,
                    "bundleVersion": 1,
                    "toolCount": 1,
                    "toolIds": [target_write_tool],
                    "readOnlyOnly": False,
                    "writeToolCount": 1,
                    "providerRecursiveToolCount": 0,
                },
                "writePreview": wp_preview,
            }
            data["requestId"] = rid
            return {"data": data, "meta": {"requestId": rid, "timestamp": ts}}

        try:
            result = run_provider_tool_roundtrip(
                user_message=message,
                provider_mode=provider_mode,
                selected_tool_ids=selected,
                context={"uiOrigin": "dev-webui"},
                hermes_home=hermes_home_override,
            )
        except Exception:
            return _make_error_json(
                status_code=500,
                code=_PROVIDER_INTERNAL_ERROR,
                message="An unexpected error occurred during provider round-trip.",
                request_id=rid,
            )

        data = result.to_safe_dict()
        data["requestId"] = rid
        return {"data": data, "meta": {"requestId": rid, "timestamp": ts}}

    # ── Phase 2C: write execute branch (same /tools/execute path, no new route) ──

    def _handle_write_execute(
        body: dict[str, Any],
        rid: str,
        ts: str,
    ) -> dict:
        """Handle a Phase 2C controlled write on the execute path.

        Reuses ``POST /tools/execute`` with ``body.mode='write'`` — no new
        route is added. This route is classified as a Tool execution route,
        NOT a Tool write route (it is the existing execution path).
        """
        tool_id = body.get("toolId")
        if not isinstance(tool_id, str) or not tool_id.strip():
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="toolId is required for write mode.",
                request_id=rid,
            )
        tool_id = tool_id.strip()
        if not _is_phase_2c_write_tool(tool_id):
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="toolId is not a Phase 2C write tool.",
                request_id=rid,
            )
        arguments = body.get("arguments")
        if arguments is not None and not isinstance(arguments, dict):
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_ARGUMENTS,
                message="arguments must be a JSON object or null.",
                request_id=rid,
            )
        context = {
            "writePlanId": body.get("writePlanId") if isinstance(body.get("writePlanId"), str) else None,
            "confirmationToken": body.get("confirmationToken") if isinstance(body.get("confirmationToken"), str) else None,
            "argumentDigest": body.get("argumentDigest") if isinstance(body.get("argumentDigest"), str) else None,
            "uiOrigin": body.get("uiOrigin") if isinstance(body.get("uiOrigin"), str) else None,
            "sourceContext": body.get("sourceContext") if isinstance(body.get("sourceContext"), str) else None,
        }
        hermes_home_override = (
            str(config.hermes_home) if config.hermes_home is not None else None
        )
        try:
            result = _dispatch_write_tool(
                tool_id, arguments, context=context, hermes_home=hermes_home_override
            )
        except Exception:
            return _make_error_json(
                status_code=500, code=_WRITE_INTERNAL_ERROR,
                message="An unexpected error occurred during write execution.",
                request_id=rid,
            )
        data = result.to_safe_dict()
        data["mode"] = "write"
        return {"data": data, "meta": {"requestId": rid, "timestamp": ts}}

    def _handle_rollback_execute(
        body: dict[str, Any],
        rid: str,
        ts: str,
    ) -> dict:
        """Phase 2C-H1 controlled rollback on the execute path.

        Reuses ``POST /tools/execute`` with ``body.mode='rollback'`` — no new
        route. Requires a rollbackId, a rollback-scoped confirmation token, and
        an argument digest. This route remains a Tool execution route, NOT a
        Tool write route.
        """
        rollback_id = body.get("rollbackId")
        if not isinstance(rollback_id, str) or not rollback_id.strip():
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="rollbackId is required for rollback mode.",
                request_id=rid,
            )
        rollback_id = rollback_id.strip()
        if not _is_valid_rollback_id(rollback_id):
            return _make_error_json(
                status_code=400, code=_WRITE_INVALID_TOOL,
                message="rollbackId is not a valid rollback manifest id.",
                request_id=rid,
            )
        context = {
            "confirmationToken": body.get("confirmationToken") if isinstance(body.get("confirmationToken"), str) else None,
            "argumentDigest": body.get("argumentDigest") if isinstance(body.get("argumentDigest"), str) else None,
            "uiOrigin": body.get("uiOrigin") if isinstance(body.get("uiOrigin"), str) else None,
            "sourceContext": body.get("sourceContext") if isinstance(body.get("sourceContext"), str) else None,
        }
        hermes_home_override = (
            str(config.hermes_home) if config.hermes_home is not None else None
        )
        try:
            result = _dispatch_rollback_tool(
                rollback_id, context=context, hermes_home=hermes_home_override
            )
        except Exception:
            return _make_error_json(
                status_code=500, code=_WRITE_INTERNAL_ERROR,
                message="An unexpected error occurred during rollback execution.",
                request_id=rid,
            )
        data = result.to_safe_dict()
        data["mode"] = "rollback"
        return {"data": data, "meta": {"requestId": rid, "timestamp": ts}}

    # ── POST /tools/execute ──

    @app.post(
        f"{prefix}/tools/execute",
        tags=["Tools"],
        summary="Execute gate + provider round-trip",
        description="Evaluates a tool execution request through the gate stack, or — "
        "when body.mode='provider_roundtrip' — runs the Phase 2B controlled Provider "
        "Schema/API round-trip on the same path (no new route). For the default "
        "canonical-name path: blocked-by-default unless the full controlled chain "
        "admits the tool. For provider_roundtrip: fake mode is deterministic and "
        "offline; real mode is blocked unless explicitly enabled. "
        "This route is classified as a Tool execution route, not a Tool write route.",
    )
    def tool_execute(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        # Phase 2B: provider round-trip branch (same path, no new route).
        mode = body.get("mode")
        if mode == "provider_roundtrip":
            return _handle_provider_roundtrip(request, body, rid, ts)

        # Phase 2C: controlled write branch (same path, no new route).
        if mode == "write":
            return _handle_write_execute(body, rid, ts)

        # Phase 2C-H1: controlled rollback branch (same path, no new route).
        if mode == "rollback":
            return _handle_rollback_execute(body, rid, ts)

        # Step 1: Validate canonicalName
        canonical_name = body.get("canonicalName")
        if canonical_name is None:
            return _make_error_json(
                status_code=400,
                code=_TOOL_EXECUTE_INVALID_CANONICAL_NAME,
                message="canonicalName is required.",
                request_id=rid,
            )
        if not isinstance(canonical_name, str):
            return _make_error_json(
                status_code=400,
                code=_TOOL_EXECUTE_INVALID_CANONICAL_NAME,
                message="canonicalName must be a string.",
                request_id=rid,
            )
        canonical_name = canonical_name.strip()
        if not canonical_name:
            return _make_error_json(
                status_code=400,
                code=_TOOL_EXECUTE_INVALID_CANONICAL_NAME,
                message="canonicalName must not be empty.",
                request_id=rid,
            )
        if len(canonical_name) > _MAX_CANONICAL_NAME_LENGTH:
            return _make_error_json(
                status_code=400,
                code=_TOOL_EXECUTE_INVALID_CANONICAL_NAME,
                message=f"canonicalName exceeds maximum length ({_MAX_CANONICAL_NAME_LENGTH}).",
                request_id=rid,
            )

        # Step 2: Validate argumentsPreview (optional, must be object if present)
        arguments_preview = body.get("argumentsPreview")
        if arguments_preview is not None:
            if not isinstance(arguments_preview, dict):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_ARGUMENTS,
                    message="argumentsPreview must be a JSON object or null.",
                    request_id=rid,
                )

        # Step 3: Validate optional string fields
        dry_run_request_id = body.get("dryRunRequestId")
        if dry_run_request_id is not None:
            if not isinstance(dry_run_request_id, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="dryRunRequestId must be a string or null.",
                    request_id=rid,
                )
            if len(dry_run_request_id) > _MAX_DRY_RUN_REQUEST_ID_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"dryRunRequestId exceeds maximum length ({_MAX_DRY_RUN_REQUEST_ID_LENGTH}).",
                    request_id=rid,
                )

        dry_run_decision_digest = body.get("dryRunDecisionDigest")
        if dry_run_decision_digest is not None:
            if not isinstance(dry_run_decision_digest, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="dryRunDecisionDigest must be a string or null.",
                    request_id=rid,
                )
            if len(dry_run_decision_digest) > _MAX_DRY_RUN_DIGEST_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"dryRunDecisionDigest exceeds maximum length ({_MAX_DRY_RUN_DIGEST_LENGTH}).",
                    request_id=rid,
                )

        confirmation_token = body.get("confirmationToken")
        if confirmation_token is not None:
            if not isinstance(confirmation_token, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="confirmationToken must be a string or null.",
                    request_id=rid,
                )
            if len(confirmation_token) > _MAX_CONFIRMATION_TOKEN_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"confirmationToken exceeds maximum length ({_MAX_CONFIRMATION_TOKEN_LENGTH}).",
                    request_id=rid,
                )

        request_id_field = body.get("requestId")
        if request_id_field is not None:
            if not isinstance(request_id_field, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="requestId must be a string or null.",
                    request_id=rid,
                )
            if len(request_id_field) > _MAX_REQUEST_ID_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"requestId exceeds maximum length ({_MAX_REQUEST_ID_LENGTH}).",
                    request_id=rid,
                )

        source_context = body.get("sourceContext")
        if source_context is not None:
            if not isinstance(source_context, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="sourceContext must be a string or null.",
                    request_id=rid,
                )
            if len(source_context) > _MAX_SOURCE_CONTEXT_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"sourceContext exceeds maximum length ({_MAX_SOURCE_CONTEXT_LENGTH}).",
                    request_id=rid,
                )

        ui_origin = body.get("uiOrigin")
        if ui_origin is not None:
            if not isinstance(ui_origin, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="uiOrigin must be a string or null.",
                    request_id=rid,
                )
            if len(ui_origin) > _MAX_UI_ORIGIN_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"uiOrigin exceeds maximum length ({_MAX_UI_ORIGIN_LENGTH}).",
                    request_id=rid,
                )

        client_created_at = body.get("clientCreatedAt")
        if client_created_at is not None:
            if not isinstance(client_created_at, str):
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message="clientCreatedAt must be a string or null.",
                    request_id=rid,
                )
            if len(client_created_at) > _MAX_CLIENT_CREATED_AT_LENGTH:
                return _make_error_json(
                    status_code=400,
                    code=_TOOL_EXECUTE_INVALID_FIELD,
                    message=f"clientCreatedAt exceeds maximum length ({_MAX_CLIENT_CREATED_AT_LENGTH}).",
                    request_id=rid,
                )

        # Step 4: Call the pure execute gate evaluator
        try:
            result = _evaluate_tool_execute_request(
                canonical_name,
                arguments_preview,
                dry_run_request_id=dry_run_request_id,
                dry_run_decision_digest=dry_run_decision_digest,
                confirmation_token=confirmation_token,
                request_id=request_id_field,
                source_context=source_context,
                ui_origin=ui_origin,
                client_created_at=client_created_at,
                hermes_home=(
                    str(config.hermes_home)
                    if config.hermes_home is not None
                    else None
                ),
            )
        except Exception as exc:
            return _make_error_json(
                status_code=500,
                code=_TOOL_EXECUTE_INTERNAL_ERROR,
                message="An unexpected error occurred during execute gate evaluation.",
                request_id=rid,
            )

        # Step 5: Return safe response envelope
        return {
            "data": result.to_safe_dict(),
            "meta": {"requestId": rid, "timestamp": ts},
        }


# ── Phase 1G-04-30: Tool Audit Events Read-Only Route ──


def _register_tool_audit_read_routes(
    app: FastAPI,
    config: DevWebApiConfig,
) -> None:
    """Register the Phase 1G-04-30 read-only audit events route.

    One GET-only route that exposes safe, redacted audit events from the
    dev-only JSONL stores. No POST/PUT/PATCH/DELETE, no tool write, no
    execution, no provider schema sending, no handler invocation.

    Guarantees:
      - Read-only (GET only)
      - Dev HERMES_HOME only; production ``~/.hermes`` blocked
      - Missing file returns empty items (not 500)
      - Malformed JSONL lines skipped safely (never leaked)
      - Path traversal / production path rejected
      - No raw token, full tokenHash, raw arguments, or secrets exposed
    """
    prefix = config.api_prefix

    _AUDIT_EVENTS_INVALID_KIND = "TOOL_AUDIT_EVENTS_INVALID_KIND"
    _AUDIT_EVENTS_INVALID_LIMIT = "TOOL_AUDIT_EVENTS_INVALID_LIMIT"
    _AUDIT_EVENTS_INVALID_CURSOR = "TOOL_AUDIT_EVENTS_INVALID_CURSOR"
    _AUDIT_EVENTS_INVALID_CANONICAL_NAME = "TOOL_AUDIT_EVENTS_INVALID_CANONICAL_NAME"
    _AUDIT_EVENTS_PATH_FORBIDDEN = "TOOL_AUDIT_EVENTS_PATH_FORBIDDEN"
    _AUDIT_EVENTS_UNAVAILABLE = "TOOL_AUDIT_EVENTS_UNAVAILABLE"
    _AUDIT_EVENTS_INVALID_QUERY = "TOOL_AUDIT_EVENTS_INVALID_QUERY"

    @app.get(
        f"{prefix}/tools/audit-events",
        tags=["Tools"],
        summary="Read-only tool audit events (dry-run / pre-execution / post-execution)",
        description="Returns safe, redacted audit events from the dev-only "
        "audit stores. Only GET is allowed. No raw confirmation token, "
        "full token hash, raw arguments, secrets, callable objects, function "
        "reprs, or provider payloads are ever exposed. A missing audit file "
        "returns an empty item list. Phase 2D adds optional cursor pagination, "
        "filters (eventType / toolId / status / auditKind / source / "
        "providerMode / readOnly / writeRequired), time range, safe search, "
        "and store/index status — all served from the same route. Legacy "
        "offset pagination remains supported for backward compatibility.",
    )
    def list_tool_audit_events(
        request: Request,
        auditKind: str = Query(
            ...,
            description="Audit kind: dry_run | pre_execution | post_execution "
            "| write (legacy), or provider | rollback | confirmation "
            "(Phase 2D durable store).",
        ),
        limit: int = Query(
            default=50,
            ge=1,
            le=100,
            description="Maximum items to return (1..100).",
        ),
        cursor: str | None = Query(
            default=None,
            max_length=512,
            description="Opaque cursor from a previous nextCursor. Legacy "
            "integer-offset cursors are still accepted.",
        ),
        canonicalName: str | None = Query(
            default=None,
            max_length=256,
            description="Optional exact canonicalName filter (legacy mode).",
        ),
        order: str | None = Query(
            default=None,
            description="Phase 2D: result order — 'desc' (default, newest "
            "first) or 'asc'. Selecting 'asc' engages the durable store path.",
        ),
        eventType: str | None = Query(
            default=None, max_length=128,
            description="Phase 2D: filter by eventType (durable store path).",
        ),
        toolId: str | None = Query(
            default=None, max_length=128,
            description="Phase 2D: filter by toolId.",
        ),
        status: str | None = Query(
            default=None, max_length=64,
            description="Phase 2D: filter by status.",
        ),
        source: str | None = Query(
            default=None, max_length=64,
            description="Phase 2D: filter by event source.",
        ),
        providerMode: str | None = Query(
            default=None, max_length=32,
            description="Phase 2D: filter by providerMode.",
        ),
        readOnly: bool | None = Query(
            default=None,
            description="Phase 2D: filter by readOnly flag.",
        ),
        writeRequired: bool | None = Query(
            default=None,
            description="Phase 2D: filter by writeRequired flag.",
        ),
        fromCreatedAt: str | None = Query(
            default=None, max_length=40,
            description="Phase 2D: inclusive lower bound on createdAt (ISO-8601).",
        ),
        toCreatedAt: str | None = Query(
            default=None, max_length=40,
            description="Phase 2D: inclusive upper bound on createdAt (ISO-8601).",
        ),
        search: str | None = Query(
            default=None, max_length=128,
            description="Phase 2D: safe substring search over summary/metadata.",
        ),
        includeSummary: bool | None = Query(
            default=None,
            description="Phase 2D: include sanitized summary/safeMetadata "
            "(default true).",
        ),
    ) -> dict:
        rid = getattr(request.state, "request_id", "")
        ts = _utc_now_iso()

        # Guard: dev HERMES_HOME must be configured
        if config.hermes_home is None:
            return _make_error_json(
                status_code=503,
                code=_AUDIT_EVENTS_UNAVAILABLE,
                message="Audit events are unavailable (no HERMES_HOME).",
                request_id=rid,
            )

        # Detect Phase 2D durable-store mode: any new filter param, an opaque
        # (non-integer) cursor, or order=asc selects the store query engine.
        store_mode = _is_store_audit_query(
            cursor=cursor,
            order=order,
            event_type=eventType,
            tool_id=toolId,
            status=status,
            source=source,
            provider_mode=providerMode,
            read_only=readOnly,
            write_required=writeRequired,
            from_created_at=fromCreatedAt,
            to_created_at=toCreatedAt,
            search=search,
            include_summary=includeSummary,
        )

        if store_mode:
            q = _build_audit_query(
                limit=limit,
                cursor=cursor,
                order=order or "desc",
                event_type=eventType,
                tool_id=toolId,
                status=status,
                audit_kind=auditKind,
                source=source,
                provider_mode=providerMode,
                read_only=readOnly,
                write_required=writeRequired,
                from_created_at=fromCreatedAt,
                to_created_at=toCreatedAt,
                search=search,
                include_summary=True if includeSummary is None else includeSummary,
            )
            result = _query_audit_events(q, hermes_home=str(config.hermes_home))
            if not result.success:
                return _audit_store_error_json(result, rid)
            payload = _audit_query_result_to_safe_dict(result)
            return {
                "data": payload,
                "meta": {"requestId": rid, "timestamp": ts},
            }

        # Legacy mode: validate auditKind against the legacy set.
        if auditKind not in _VALID_AUDIT_KINDS:
            return _make_error_json(
                status_code=400,
                code=_AUDIT_EVENTS_INVALID_KIND,
                message=(
                    "auditKind must be one of: dry_run, pre_execution, "
                    "post_execution, write."
                ),
                request_id=rid,
            )

        result = _read_audit_events(
            audit_kind=auditKind,
            limit=limit,
            cursor=cursor,
            canonical_name=canonicalName,
            hermes_home=str(config.hermes_home),
        )

        # Map reader error codes to safe HTTP error envelopes
        if not result.success:
            if result.error_code == "audit_read_hermes_home_missing":
                return _make_error_json(
                    status_code=503,
                    code=_AUDIT_EVENTS_UNAVAILABLE,
                    message="Audit events are unavailable (no HERMES_HOME).",
                    request_id=rid,
                )
            if result.error_code == "audit_read_path_forbidden":
                return _make_error_json(
                    status_code=403,
                    code=_AUDIT_EVENTS_PATH_FORBIDDEN,
                    message="Audit path is outside the dev environment.",
                    request_id=rid,
                )
            if result.error_code == "audit_read_kind_invalid":
                return _make_error_json(
                    status_code=400,
                    code=_AUDIT_EVENTS_INVALID_KIND,
                    message="Invalid auditKind.",
                    request_id=rid,
                )
            if result.error_code == "audit_read_limit_invalid":
                return _make_error_json(
                    status_code=400,
                    code=_AUDIT_EVENTS_INVALID_LIMIT,
                    message="limit must be a positive integer.",
                    request_id=rid,
                )
            if result.error_code == "audit_read_cursor_invalid":
                return _make_error_json(
                    status_code=400,
                    code=_AUDIT_EVENTS_INVALID_CURSOR,
                    message="cursor must encode a non-negative integer offset.",
                    request_id=rid,
                )
            # canonicalName validation fell through to kind_invalid bucket
            return _make_error_json(
                status_code=400,
                code=_AUDIT_EVENTS_INVALID_CANONICAL_NAME,
                message="canonicalName must be a string within length limits.",
                request_id=rid,
            )

        return {
            "data": _audit_read_result_to_safe_dict(result),
            "meta": {"requestId": rid, "timestamp": ts},
        }
