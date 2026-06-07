"""Dev Web API shared response schemas.

Pydantic models for the unified JSON response envelope used by all
Dev Web API endpoints. Importing this module has no side effects.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_request_id() -> str:
    """Generate a new random request ID (UUID4)."""
    return uuid.uuid4().hex


def sanitize_request_id(raw: str | None) -> str:
    """Validate and sanitise a client-provided request ID.

    Returns the original value if it is safe, or a new UUID4 otherwise.
    Rejects values that are too long, contain newlines, or have control
    characters — mitigating header-injection risks.
    """
    if not raw:
        return generate_request_id()
    if len(raw) > 64:
        return generate_request_id()
    if any(ch in raw for ch in ("\n", "\r", "\x00")):
        return generate_request_id()
    return raw


# ── Meta ──

class ResponseMeta(BaseModel):
    """Common metadata included in every API response."""

    request_id: str = Field(alias="requestId")
    timestamp: str

    model_config = {"populate_by_name": True}


# ── Error ──

class ErrorBody(BaseModel):
    """Structured error details."""

    code: str
    message: str
    details: str | None = None


class ErrorResponse(BaseModel):
    """Unified error response envelope."""

    error: ErrorBody
    meta: ResponseMeta


# ── Status ──

class IsolationStatus(BaseModel):
    """Environment isolation check results."""

    passed: bool
    uses_development_home: bool = Field(alias="usesDevelopmentHome")
    production_home_untouched: bool = Field(alias="productionHomeUntouched")

    model_config = {"populate_by_name": True}


class ServiceAvailability(BaseModel):
    """Availability status of a single service."""

    available: bool
    read_only: bool = Field(default=True, alias="readOnly")
    phase: str | None = None

    model_config = {"populate_by_name": True}


class ServicesStatus(BaseModel):
    """Status of all Dev API services."""

    api: ServiceAvailability
    sessions: ServiceAvailability
    memory: ServiceAvailability
    agent: ServiceAvailability
    files: ServiceAvailability


class BindInfo(BaseModel):
    """Network binding information."""

    host: str
    port: int


class StatusData(BaseModel):
    """Response data for GET /status."""

    environment: str
    api_version: str = Field(alias="apiVersion")
    status: str
    read_only: bool = Field(default=True, alias="readOnly")
    bind: BindInfo
    isolation: IsolationStatus
    services: ServicesStatus

    model_config = {"populate_by_name": True}


class StatusResponse(BaseModel):
    """Response envelope for GET /status."""

    data: StatusData
    meta: ResponseMeta


# ── Files ──

class FilesStatusData(BaseModel):
    """Response data for GET /files/status."""

    available: bool
    read_only: bool = Field(default=True, alias="readOnly")
    browse_enabled: bool = Field(default=False, alias="browseEnabled")
    upload_enabled: bool = Field(default=False, alias="uploadEnabled")
    download_enabled: bool = Field(default=False, alias="downloadEnabled")
    delete_enabled: bool = Field(default=False, alias="deleteEnabled")
    reason: str

    model_config = {"populate_by_name": True}


class FilesStatusResponse(BaseModel):
    """Response envelope for GET /files/status."""

    data: FilesStatusData
    meta: ResponseMeta


# ── Sessions ──


class SessionListItem(BaseModel):
    """A single session in the list response."""

    id: str
    title: str | None = None
    source: str
    model: str | None = None
    message_count: int = Field(alias="messageCount")
    tool_call_count: int = Field(default=0, alias="toolCallCount")
    archived: bool
    started_at: str = Field(alias="startedAt")
    ended_at: str | None = Field(default=None, alias="endedAt")
    last_active_at: str | None = Field(default=None, alias="lastActiveAt")
    preview: str | None = None

    model_config = {"populate_by_name": True}


class SessionPage(BaseModel):
    """Pagination metadata for session list."""

    offset: int = 0
    limit: int
    total: int
    has_more: bool = Field(alias="hasMore")

    model_config = {"populate_by_name": True}


class SessionListData(BaseModel):
    """Response data for GET /sessions."""

    items: list[SessionListItem]
    page: SessionPage


class SessionListResponse(BaseModel):
    """Response envelope for GET /sessions."""

    data: SessionListData
    meta: ResponseMeta


class SessionDetail(BaseModel):
    """Full session detail."""

    id: str
    title: str | None = None
    source: str
    model: str | None = None
    message_count: int = Field(alias="messageCount")
    tool_call_count: int = Field(default=0, alias="toolCallCount")
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    archived: bool
    started_at: str = Field(alias="startedAt")
    ended_at: str | None = Field(default=None, alias="endedAt")
    last_active_at: str | None = Field(default=None, alias="lastActiveAt")
    end_reason: str | None = Field(default=None, alias="endReason")

    model_config = {"populate_by_name": True}


class SessionDetailResponse(BaseModel):
    """Response envelope for GET /sessions/{sessionId}."""

    data: SessionDetail
    meta: ResponseMeta
