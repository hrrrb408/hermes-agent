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


# ── Messages ──


class TextContent(BaseModel):
    """Text message content."""

    type: str = "text"
    text: str
    truncated: bool | None = None


class EmptyContent(BaseModel):
    """Empty message content."""

    type: str = "empty"


class UnsupportedContent(BaseModel):
    """Unsupported message content placeholder."""

    type: str = "unsupported"


class ToolCallFunction(BaseModel):
    """Function call within a tool call."""

    name: str
    arguments: str


class ToolCallItem(BaseModel):
    """A single tool call in an assistant message."""

    id: str
    type: str = "function"
    function: ToolCallFunction


class MessageItem(BaseModel):
    """A single message in the messages response."""

    id: int
    role: str
    content: dict[str, Any]
    timestamp: str | None = None
    token_count: int | None = Field(default=None, alias="tokenCount")
    finish_reason: str | None = Field(default=None, alias="finishReason")
    tool_calls: list[ToolCallItem] | None = Field(default=None, alias="toolCalls")
    tool_call_id: str | None = Field(default=None, alias="toolCallId")
    tool_name: str | None = Field(default=None, alias="toolName")

    model_config = {"populate_by_name": True}


class MessagePage(BaseModel):
    """Pagination metadata for message list."""

    offset: int = 0
    limit: int
    total: int
    has_more: bool = Field(alias="hasMore")
    messages_before: int | None = Field(default=None, alias="messagesBefore")
    messages_after: int | None = Field(default=None, alias="messagesAfter")

    model_config = {"populate_by_name": True}


class MessageListData(BaseModel):
    """Response data for GET /sessions/{sessionId}/messages."""

    items: list[MessageItem]
    page: MessagePage


class MessageListResponse(BaseModel):
    """Response envelope for GET /sessions/{sessionId}/messages."""

    data: MessageListData
    meta: ResponseMeta


# ── Review Execute (Phase 1C) ──


class ReviewExecuteRequest(BaseModel):
    """Request body for POST /reviews/{reviewId}/approve/execute."""

    confirmation_text: str = Field(alias="confirmationText")
    expected_action: str = Field(alias="expectedAction")
    review_updated_at: str = Field(alias="reviewUpdatedAt")
    dry_run_previewed: bool = Field(alias="dryRunPreviewed")
    acknowledged_effects: list[str] = Field(
        alias="acknowledgedEffects", default_factory=list,
    )

    model_config = {"populate_by_name": True}


class ReviewRejectExecuteRequest(BaseModel):
    """Request body for POST /reviews/{reviewId}/reject/execute."""

    confirmation_text: str = Field(alias="confirmationText")
    expected_action: str = Field(alias="expectedAction")
    review_updated_at: str = Field(alias="reviewUpdatedAt")
    dry_run_previewed: bool = Field(alias="dryRunPreviewed")
    acknowledged_effects: list[str] = Field(
        alias="acknowledgedEffects", default_factory=list,
    )
    reason: str | None = Field(default=None, max_length=500)

    model_config = {"populate_by_name": True}


class ReviewExecuteTarget(BaseModel):
    """Target information in execute response."""

    memory_id: str | None = Field(default=None, alias="memoryId")
    category: str = ""
    operation: str = ""

    model_config = {"populate_by_name": True}


class ReviewExecuteAudit(BaseModel):
    """Audit information in execute response."""

    actor: str = "dev-webui"
    timestamp: str = ""
    dev_only: bool = Field(default=True, alias="devOnly")

    model_config = {"populate_by_name": True}


class ReviewExecuteResult(BaseModel):
    """Response data for POST /reviews/{reviewId}/approve|reject/execute."""

    review_id: str = Field(alias="reviewId")
    executed: bool = True
    action: str = ""
    status_before: str = Field(alias="statusBefore", default="")
    status_after: str = Field(alias="statusAfter", default="")
    memory_changed: bool = Field(default=False, alias="memoryChanged")
    review_changed: bool = Field(default=False, alias="reviewChanged")
    event_appended: bool = Field(default=False, alias="eventAppended")
    target: ReviewExecuteTarget = Field(default_factory=ReviewExecuteTarget)
    audit: ReviewExecuteAudit = Field(default_factory=ReviewExecuteAudit)
    warnings: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
