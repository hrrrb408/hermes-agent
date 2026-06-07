"""Hermes Dev Web API — independent read-only FastAPI application.

This module provides the ``create_dev_web_api_app()`` factory and the
Phase 0C-04 endpoints:

- ``GET /api/dev/v1/status``
- ``GET /api/dev/v1/files/status``
- ``GET /api/dev/v1/sessions``
- ``GET /api/dev/v1/sessions/{sessionId}``
- ``GET /api/dev/v1/sessions/{sessionId}/messages``

Importing this module has **no side effects**: no server is started, no
files are read, no database connections are opened.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_errors import (
    register_error_handlers,
    SESSION_NOT_FOUND,
    SESSION_STORE_UNAVAILABLE,
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
            {"name": "Files", "description": "File browsing status"},
        ],
    )

    app.state.dev_api_config = config

    # Build session service if hermes_home is configured
    session_service: DevSessionQueryService | None = None
    message_service: DevMessageQueryService | None = None
    if config.hermes_home is not None:
        state_db_path = config.hermes_home / "state.db"
        session_service = DevSessionQueryService(state_db_path)
        message_service = DevMessageQueryService(state_db_path)
    app.state.session_service = session_service
    app.state.message_service = message_service

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
    _register_routes(app, config, session_service)

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
) -> None:
    """Register Phase 0C-04 routes."""

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
                    "memory": {"available": False, "readOnly": True, "phase": "0C-05"},
                    "agent": {"available": False, "readOnly": True, "phase": "0C-05"},
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
