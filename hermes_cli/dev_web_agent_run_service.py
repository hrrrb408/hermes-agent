"""Dev Web API Agent Run Service.

Orchestrates Agent Run creation, execution, cancellation, and lifecycle.
Manages worker threads, rate limiting, and coordinates between the
Run Registry, Audit Trail, and SSE Bridge.

Safety guarantees:
    - Kill switch checked FIRST (before any I/O)
    - Dev-only environment verified (before any I/O)
    - Session must pre-exist (no auto-create)
    - Tools forcibly disabled (enabled_toolsets=[])
    - Auto memory forcibly disabled (skip_memory=True)
    - Review queue forcibly disabled (config default)
    - Single stream_delta_callback (stream_callback=None)
    - Web API never calls SessionDB.append_message directly
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_cli.dev_web_agent_run_audit import AgentRunAudit, AgentRunAuditError
from hermes_cli.dev_web_agent_run_config import (
    AGENT_RUN_CONFIG,
    enforce_agent_run_dev_environment,
    is_agent_run_enabled,
)
from hermes_cli.dev_web_agent_run_models import (
    RunEventType,
    RunRecord,
    RunStatus,
    RunUsage,
)
from hermes_cli.dev_web_agent_run_registry import (
    AgentRunRegistry,
    CapacityReachedError,
    RunNotFoundError,
    SessionBusyError,
    get_run_registry,
)
from hermes_cli.dev_web_agent_run_sse import SSEBridge

logger = logging.getLogger(__name__)

# ── Validation constants ──

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,200}$")
_MAX_MESSAGE_LENGTH = 4000
_REQUIRED_EFFECTS = frozenset({"CALL_LLM", "WRITE_SESSION"})
_FORBIDDEN_FIELDS = frozenset({
    "apiKey", "api_key", "baseUrl", "base_url", "authorization",
    "headers", "proxy", "systemPrompt", "developerPrompt",
    "toolsSchema", "toolChoice", "workerCount", "threadId",
    "force", "writeMemory", "persistMode",
})

# ── Rate limiter (in-memory) ──


class _RateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, per_minute: int, per_hour: int) -> None:
        self._per_minute = per_minute
        self._per_hour = per_hour
        self._timestamps: List[float] = []
        self._lock = threading.Lock()

    def check(self) -> Optional[float]:
        """Check if request is allowed.

        Returns:
            None if allowed, or retryAfterSeconds if rate limited.
        """
        now = time.monotonic()
        with self._lock:
            # Prune old timestamps
            self._timestamps = [
                t for t in self._timestamps
                if now - t < 3600  # Keep last hour
            ]

            # Check per-minute
            minute_count = sum(
                1 for t in self._timestamps if now - t < 60
            )
            if minute_count >= self._per_minute:
                # Find oldest in current minute window
                minute_ts = [t for t in self._timestamps if now - t < 60]
                if minute_ts:
                    retry_after = 60 - (now - minute_ts[0])
                    return max(1.0, retry_after)

            # Check per-hour
            if len(self._timestamps) >= self._per_hour:
                retry_after = 3600 - (now - self._timestamps[0])
                return max(1.0, retry_after)

            # Record this request
            self._timestamps.append(now)
            return None


# ── Thread pool (singleton) ──

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the singleton thread pool for agent runs."""
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="agent-run",
            )
        return _executor


# ── Main service ──


class AgentRunService:
    """Agent Run Service — orchestrates Run lifecycle.

    Coordinates:
    - Kill switch check
    - Dev-only environment guard
    - Rate limiting
    - Request validation
    - Run Registry operations
    - Audit trail
    - Worker thread dispatch
    - Cancellation
    - Usage normalization
    """

    def __init__(
        self,
        hermes_home: Path,
        source_root: Path,
    ) -> None:
        self._hermes_home = hermes_home
        self._source_root = source_root
        self._config = AGENT_RUN_CONFIG
        self._registry = get_run_registry()
        self._rate_limiter = _RateLimiter(
            per_minute=self._config.rate_limit_per_minute,
            per_hour=self._config.rate_limit_per_hour,
        )
        self._audit = AgentRunAudit(hermes_home / "state.db")

    # ── Create Run ──

    def create_run(self, request_body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Create a new Agent Run.

        Validates request, checks all guards, creates registry entry,
        writes audit, dispatches worker thread.

        Returns:
            API response dict with data/meta envelope.

        Raises:
            Various error conditions with appropriate HTTP status codes.
        """
        # 1. Kill switch
        if not is_agent_run_enabled():
            raise AgentRunDisabledError("Agent Run is disabled. Set HERMES_AGENT_RUN_ENABLED=true to enable.")

        # 2. Dev-only guard
        enforce_agent_run_dev_environment(self._hermes_home, self._source_root)

        # 3. Request validation
        session_id, message, model, provider, overrides = self._validate_request(request_body)

        # 4. Rate limit
        retry_after = self._rate_limiter.check()
        if retry_after is not None:
            raise RateLimitedError(f"Rate limit exceeded. Retry after {retry_after:.0f}s.", retry_after)

        # 5. Session existence check
        self._verify_session_exists(session_id)

        # 6. Create Run in Registry
        try:
            record = self._registry.create_run(
                session_id=session_id,
                request_id=request_id,
                model_name=model,
                provider_name=provider,
            )
        except CapacityReachedError as exc:
            raise CapacityError(str(exc))
        except SessionBusyError as exc:
            raise SessionBusyError(str(exc))

        # 7. Audit: run.created
        try:
            self._audit.record_created(
                run_id=record.run_id,
                session_id=session_id,
                request_id=request_id,
                model=model,
                provider=provider,
            )
        except AgentRunAuditError:
            # Roll back registry entry
            self._registry.fail_run(record.run_id, "AUDIT_ERROR", "Audit creation failed")
            raise AgentRunError("Failed to create audit record. Run not started.")

        # 8. Emit run.created event
        self._registry.append_event(record.run_id, RunEventType.RUN_CREATED, {
            "sessionId": session_id,
            "model": {"name": model, "provider": provider},
        })

        # 9. Dispatch worker
        run_id = record.run_id
        executor = _get_executor()
        loop = asyncio.get_running_loop()
        future = executor.submit(
            self._worker,
            run_id=run_id,
            session_id=session_id,
            message=message,
            model=model,
            provider=provider,
            overrides=overrides,
            loop=loop,
        )
        self._registry.set_future(run_id, future)

        # 10. Return 202 response
        return {
            "data": {
                "runId": record.run_id,
                "sessionId": session_id,
                "status": record.status.value,
                "streamUrl": f"/api/dev/v1/agent/runs/{record.run_id}/events",
                "statusUrl": f"/api/dev/v1/agent/runs/{record.run_id}",
                "cancelUrl": f"/api/dev/v1/agent/runs/{record.run_id}/cancel",
                "model": {"name": model, "provider": provider},
                "capabilities": {
                    "llmCall": True,
                    "streaming": True,
                    "tools": False,
                    "autoMemory": False,
                    "sessionWrite": True,
                    "memoryWrite": False,
                    "reviewQueue": False,
                },
                "safety": {
                    "devOnly": True,
                    "killSwitchEnabled": True,
                    "toolsDisabled": True,
                    "autoMemoryDisabled": True,
                },
            },
            "meta": {
                "requestId": request_id,
                "timestamp": _utc_now_iso(),
            },
        }

    # ── Get Run Status ──

    def get_run_status(self, run_id: str, request_id: str) -> Dict[str, Any]:
        """Get Run status.

        Returns:
            API response dict with whitelisted fields only.
        """
        if not is_agent_run_enabled():
            raise AgentRunDisabledError("Agent Run is disabled.")

        from hermes_cli.dev_web_agent_run_registry import (
            RunNotFoundError as RegistryRunNotFoundError,
        )
        try:
            record = self._registry.get_run(run_id)
        except RegistryRunNotFoundError:
            raise RunNotFoundError(f"Run {run_id} not found.")

        return {
            "data": record.to_status_dict(),
            "meta": {
                "requestId": request_id,
                "timestamp": _utc_now_iso(),
            },
        }

    # ── Cancel Run ──

    def cancel_run(self, run_id: str, request_id: str) -> Dict[str, Any]:
        """Request cancellation of a Run.

        Idempotent:
        - First cancel: transitions to CANCELLING, calls interrupt()
        - Repeated cancel: no-op (already CANCELLING)
        - Terminal cancel: returns alreadyTerminal=true

        Returns:
            API response dict with cancel status.
        """
        if not is_agent_run_enabled():
            raise AgentRunDisabledError("Agent Run is disabled.")

        from hermes_cli.dev_web_agent_run_registry import (
            RunNotFoundError as RegistryRunNotFoundError,
        )
        try:
            record = self._registry.get_run(run_id)
        except RegistryRunNotFoundError:
            raise RunNotFoundError(f"Run {run_id} not found.")

        # Terminal state
        if record.is_terminal():
            return {
                "data": {
                    "runId": run_id,
                    "cancelRequested": record.cancel_requested,
                    "statusBefore": record.status.value,
                    "statusAfter": record.status.value,
                    "alreadyTerminal": True,
                },
                "meta": {"requestId": request_id, "timestamp": _utc_now_iso()},
            }

        # Already cancelling
        if record.status == RunStatus.CANCELLING:
            return {
                "data": {
                    "runId": run_id,
                    "cancelRequested": True,
                    "statusBefore": record.status.value,
                    "statusAfter": RunStatus.CANCELLING.value,
                    "alreadyTerminal": False,
                },
                "meta": {"requestId": request_id, "timestamp": _utc_now_iso()},
            }

        # Active cancel
        status_before = record.status.value
        self._registry.append_event(run_id, RunEventType.RUN_CANCELLING, {})
        updated = self._registry.mark_cancelling(run_id)

        # Call interrupt on agent
        agent_ref = updated.agent_reference
        if agent_ref is not None:
            try:
                agent_ref.interrupt()
            except Exception as exc:
                logger.debug("Agent interrupt failed for run %s: %s", run_id, exc)

        # Wait for worker with timeout
        future = updated.future
        if future is not None:
            try:
                future.result(timeout=self._config.cancel_wait_timeout)
                # Worker finished — transition to CANCELLED
                self._registry.cancel_run_completed(run_id)
                self._registry.append_event(run_id, RunEventType.RUN_CANCELLED, {})
                self._audit.record_cancelled(run_id=run_id)
            except Exception:
                # Timeout — worker still running
                logger.warning(
                    "Cancel timeout for run %s — worker may still be running",
                    run_id
                )
                self._registry.fail_run(
                    run_id,
                    "AGENT_CANCEL_TIMEOUT",
                    "Cancel wait timed out — worker may still be running",
                )
                self._registry.append_event(run_id, RunEventType.RUN_FAILED, {
                    "errorCode": "AGENT_CANCEL_TIMEOUT",
                })
                self._audit.record_failed(
                    run_id=run_id, error_code="AGENT_CANCEL_TIMEOUT"
                )

        return {
            "data": {
                "runId": run_id,
                "cancelRequested": True,
                "statusBefore": status_before,
                "statusAfter": self._registry.get_run(run_id).status.value,
                "alreadyTerminal": False,
            },
            "meta": {"requestId": request_id, "timestamp": _utc_now_iso()},
        }

    # ── Worker ──

    def _worker(
        self,
        *,
        run_id: str,
        session_id: str,
        message: str,
        model: str,
        provider: str,
        overrides: Dict[str, Any],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Worker thread that runs the agent.

        This is the ONLY place where AIAgent is instantiated and
        run_conversation() is called.
        """
        start_time = time.monotonic()
        agent = None

        try:
            # STARTING
            self._registry.transition(run_id, RunStatus.STARTING)
            self._registry.append_event(run_id, RunEventType.RUN_STARTED, {
                "model": model,
            })
            self._audit.record_started(run_id=run_id)

            # Create SSE bridge
            bridge = SSEBridge(run_id, self._registry, loop)

            # Create Agent
            agent = self._create_agent(
                session_id=session_id,
                model=model,
                provider=provider,
                overrides=overrides,
                stream_delta_callback=bridge.stream_delta_callback,
            )
            self._registry.set_agent_reference(run_id, agent)

            # RUNNING
            self._registry.transition(run_id, RunStatus.RUNNING)

            # Execute
            result = agent.run_conversation(
                message,
                stream_callback=None,  # MUST be None — only stream_delta_callback
            )

            # Normalize usage
            usage = self._normalize_usage(result)

            # Check for unexpected tool calls
            if self._has_tool_calls(result):
                raise ToolCallForbiddenError("Provider returned unexpected tool call")

            # Complete
            self._registry.set_usage(run_id, usage)
            self._registry.append_event(run_id, RunEventType.MESSAGE_COMPLETED, {
                "usage": usage.to_api_dict(),
            })
            self._registry.append_event(run_id, RunEventType.USAGE_UPDATED, {
                "usage": usage.to_api_dict(),
            })
            self._registry.complete_run(run_id, usage=usage)
            self._registry.append_event(run_id, RunEventType.RUN_COMPLETED, {})

            # Audit
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._audit.record_completed(
                run_id=run_id,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                duration_ms=duration_ms,
            )

        except ToolCallForbiddenError:
            logger.error("Unexpected tool call in run %s — terminating", run_id)
            self._safe_fail_run(
                run_id, "AGENT_TOOL_CALL_FORBIDDEN",
                "Provider returned unexpected tool call"
            )

        except Exception as exc:
            logger.error("Agent run %s failed: %s", run_id, exc)
            error_code = "AGENT_RUN_FAILED"
            error_msg = "Agent execution error"
            self._safe_fail_run(run_id, error_code, error_msg)

        finally:
            # Ensure terminal event is emitted even on crash
            self._ensure_terminal_event(run_id)
            # Clear agent reference
            if agent is not None:
                try:
                    agent.clear_interrupt()
                except Exception:
                    pass

    # ── Agent creation ──

    def _create_agent(
        self,
        *,
        session_id: str,
        model: str,
        provider: str,
        overrides: Dict[str, Any],
        stream_delta_callback: Any,
    ) -> Any:
        """Create an AIAgent instance for this Run.

        Safety:
        - enabled_toolsets=[] → no tools
        - skip_memory=True → no auto memory
        - stream_delta_callback set, _stream_callback=None
        - session_db from dev home only
        - quiet_mode=True
        """
        from hermes_state import SessionDB

        config = self._load_safe_config()
        api_key = self._load_api_key(config, provider)
        base_url = self._load_base_url(config, provider)

        max_tokens = overrides.get("maxOutputTokens") or self._config.max_output_tokens
        if max_tokens and max_tokens > self._config.max_output_tokens:
            max_tokens = self._config.max_output_tokens

        session_db = SessionDB(
            db_path=self._hermes_home / "state.db",
        )

        # Import AIAgent
        from run_agent import AIAgent

        agent = AIAgent(
            base_url=base_url,
            api_key=api_key,
            provider=provider,
            model=model,
            session_id=session_id,
            session_db=session_db,
            stream_delta_callback=stream_delta_callback,
            enabled_toolsets=[],  # NO TOOLS
            skip_memory=True,  # NO AUTO MEMORY
            quiet_mode=True,
            max_tokens=max_tokens or self._config.max_output_tokens,
            platform="dev-webui",
        )

        return agent

    def _load_safe_config(self) -> Dict[str, Any]:
        """Load read-only config for dev home."""
        from hermes_cli.config import load_config_readonly
        return load_config_readonly(hermes_home=str(self._hermes_home))

    def _load_api_key(self, config: Dict[str, Any], provider: str) -> str:
        """Load API key from environment (not from config)."""
        from hermes_cli.config import load_config_readonly
        # API keys are in .env, loaded as env vars
        key_map = {
            "zai": "ZAI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "glm": "GLM_API_KEY",
            "zhipu": "ZHIPU_API_KEY",
        }
        env_var = key_map.get(provider, f"{provider.upper()}_API_KEY")
        return os.environ.get(env_var, "")

    def _load_base_url(self, config: Dict[str, Any], provider: str) -> str:
        """Load base URL from config (not from env)."""
        providers = config.get("providers", {})
        provider_config = providers.get(provider, {})
        return provider_config.get("base_url", "")

    # ── Validation ──

    def _validate_request(self, body: Dict[str, Any]) -> tuple:
        """Validate the create run request.

        Returns:
            (session_id, message, model, provider, overrides)

        Raises:
            InvalidRequestError on any validation failure.
        """
        # Check forbidden fields
        for field in _FORBIDDEN_FIELDS:
            if field in body:
                raise InvalidRequestError(f"Forbidden field: {field}")

        # Session ID
        session_id = body.get("sessionId", "")
        if not session_id or not isinstance(session_id, str):
            raise InvalidRequestError("sessionId is required")
        if not _SESSION_ID_RE.match(session_id):
            raise InvalidRequestError("Invalid sessionId format")

        # Message
        message = body.get("message", "")
        if not message or not isinstance(message, str):
            raise InvalidRequestError("message is required")
        if len(message) < 1 or len(message) > _MAX_MESSAGE_LENGTH:
            raise InvalidRequestError(f"message must be 1-{_MAX_MESSAGE_LENGTH} characters")

        # Confirmation text
        confirmation = body.get("confirmationText", "")
        if confirmation != "RUN":
            raise InvalidConfirmError("confirmationText must be 'RUN'")

        # Dry-run previewed
        if not body.get("dryRunPreviewed"):
            raise MissingDryRunError("dryRunPreviewed must be true")

        # Acknowledged effects
        effects = body.get("acknowledgedEffects", [])
        if set(effects) != _REQUIRED_EFFECTS:
            raise InvalidEffectsError(
                "acknowledgedEffects must be exactly ['CALL_LLM', 'WRITE_SESSION']"
            )

        # Options
        options = body.get("options", {})
        if options.get("stream") is not True:
            raise InvalidRequestError("stream must be true")
        if options.get("tools") is not False:
            raise InvalidRequestError("tools must be false")
        if options.get("autoMemory") is not False:
            raise InvalidRequestError("autoMemory must be false")

        # Load model/provider from config — with fallback for validation-only contexts
        try:
            config = self._load_safe_config()
        except Exception:
            config = {}
        model_name = config.get("model", "unknown")
        provider_name = config.get("provider", "unknown")

        # Overrides
        overrides = body.get("overrides", {}) or {}
        model_override = overrides.get("model")
        if model_override:
            if not isinstance(model_override, str) or len(model_override) > 100:
                raise InvalidRequestError("Invalid model override")
            model_name = model_override

        temp = overrides.get("temperature")
        if temp is not None:
            if not isinstance(temp, (int, float)) or temp < 0.0 or temp > 2.0:
                raise InvalidRequestError("temperature must be 0.0-2.0")

        max_tokens = overrides.get("maxOutputTokens")
        if max_tokens is not None:
            if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 4096:
                raise InvalidRequestError("maxOutputTokens must be 1-4096")

        return session_id, message, model_name, provider_name, overrides

    def _verify_session_exists(self, session_id: str) -> None:
        """Verify the session exists in dev-home SessionDB."""
        from hermes_state import SessionDB

        db = SessionDB(
            db_path=self._hermes_home / "state.db",
        )
        session = db.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} not found")

    # ── Usage normalization ──

    def _normalize_usage(self, result: Dict[str, Any]) -> RunUsage:
        """Normalize provider usage from run_conversation() result."""
        usage = RunUsage()

        input_tokens = result.get("input_tokens")
        output_tokens = result.get("output_tokens")
        total_tokens = result.get("total_tokens")

        usage.input_tokens = input_tokens if isinstance(input_tokens, int) else None
        usage.output_tokens = output_tokens if isinstance(output_tokens, int) else None
        usage.total_tokens = total_tokens if isinstance(total_tokens, int) else None

        return usage

    def _has_tool_calls(self, result: Dict[str, Any]) -> bool:
        """Check if the result contains any tool calls (forbidden in Phase 1F)."""
        # Check for tool_calls in the messages
        messages = result.get("messages", [])
        for msg in messages:
            if msg.get("tool_calls"):
                return True
        return False

    # ── Error helpers ──

    def _safe_fail_run(self, run_id: str, error_code: str, error_message: str) -> None:
        """Safely transition run to FAILED state."""
        try:
            self._registry.fail_run(run_id, error_code, error_message)
        except Exception:
            pass

    def _ensure_terminal_event(self, run_id: str) -> None:
        """Ensure a terminal event has been emitted."""
        try:
            record = self._registry.get_run(run_id)
            if not record.terminal_event_emitted:
                if record.status == RunStatus.CANCELLED:
                    self._registry.append_event(run_id, RunEventType.RUN_CANCELLED, {})
                elif record.status == RunStatus.COMPLETED:
                    self._registry.append_event(run_id, RunEventType.RUN_COMPLETED, {})
                else:
                    self._registry.append_event(run_id, RunEventType.RUN_FAILED, {
                        "errorCode": record.error_code or "INTERNAL_ERROR",
                    })
        except Exception:
            pass


# ── Error classes ──


class AgentRunDisabledError(Exception):
    """Kill switch is OFF."""


class UnsafeEnvironmentError(Exception):
    """Environment guard failed."""


class InvalidRequestError(Exception):
    """Request validation failed."""


class InvalidConfirmError(Exception):
    """confirmationText != 'RUN'."""


class MissingDryRunError(Exception):
    """dryRunPreviewed != true."""


class InvalidEffectsError(Exception):
    """acknowledgedEffects wrong."""


class SessionNotFoundError(Exception):
    """Session does not exist."""


class SessionBusyError(Exception):
    """Session already has active run."""


class CapacityError(Exception):
    """Global active run limit reached."""


class RateLimitedError(Exception):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: float = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ModelNotAllowedError(Exception):
    """Model not in allowlist."""


class ToolCallForbiddenError(Exception):
    """Provider returned unexpected tool call."""


class AgentRunError(Exception):
    """General agent run error."""


class RunNotFoundError(Exception):
    """Run ID not found."""


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
