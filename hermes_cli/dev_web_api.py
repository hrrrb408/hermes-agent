"""Hermes Dev Web API — independent read-only FastAPI application.

This module provides the ``create_dev_web_api_app()`` factory and the
two Phase 0C-02 endpoints:

- ``GET /api/dev/v1/status``
- ``GET /api/dev/v1/files/status``

Importing this module has **no side effects**: no server is started, no
files are read, no database connections are opened.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_errors import register_error_handlers
from hermes_cli.dev_web_middleware import RequestIdMiddleware
from hermes_cli.dev_web_schemas import _utc_now_iso


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
            {"name": "Files", "description": "File browsing status"},
        ],
    )

    app.state.dev_api_config = config

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
    _register_routes(app, config)

    return app


def _register_routes(app: FastAPI, config: DevWebApiConfig) -> None:
    """Register Phase 0C-02 routes."""

    prefix = config.api_prefix

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
                    "sessions": {"available": False, "readOnly": True, "phase": "0C-03"},
                    "memory": {"available": False, "readOnly": True, "phase": "0C-05"},
                    "agent": {"available": False, "readOnly": True, "phase": "0C-05"},
                    "files": {"available": False, "readOnly": True},
                },
            },
            "meta": {"requestId": rid, "timestamp": ts},
        }

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
