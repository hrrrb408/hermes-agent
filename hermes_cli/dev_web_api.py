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
    if config.hermes_home is not None:
        state_db_path = config.hermes_home / "state.db"
        session_service = DevSessionQueryService(state_db_path)
        message_service = DevMessageQueryService(state_db_path)
        memory_service = DevMemoryQueryService(config.hermes_home)
        agent_service = DevAgentStatusService(config.hermes_home)
        review_service = DevReviewQueryService(config.hermes_home)
        writer_service = DevMemoryWriterDryRunService(config.hermes_home)
        preview_service = DevAgentPreviewService(config.hermes_home)
    app.state.session_service = session_service
    app.state.message_service = message_service
    app.state.memory_service = memory_service
    app.state.agent_service = agent_service
    app.state.review_service = review_service
    app.state.writer_service = writer_service
    app.state.preview_service = preview_service

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
    _register_routes(app, config, session_service, memory_service, agent_service, review_service, writer_service, preview_service)

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


def _register_routes(
    app: FastAPI,
    config: DevWebApiConfig,
    session_service: DevSessionQueryService | None,
    memory_service: DevMemoryQueryService | None,
    agent_service: DevAgentStatusService | None,
    review_service: DevReviewQueryService | None,
    writer_service: DevMemoryWriterDryRunService | None,
    preview_service: DevAgentPreviewService | None,
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
