"""Dev Web API Agent Preview Service.

Pure-computation preview service for Agent Prompt Preview and Agent Run
Dry-Run operations. This service ONLY reads existing configuration, session
history, and memory data and returns a preview of what *would* be sent to
the LLM. No LLM calls are made, no tools are executed, no sessions are
written, no memory is modified.

Safety guarantees enforced at the service layer:
- Never calls AIAgent.chat(), run_conversation(), _interruptible_api_call,
  registry.dispatch(), handle_function_call(), maybe_auto_write_memory(),
  enqueue_review_item(), SessionDB.append_message(), _persist_session,
  _flush_messages_to_session_db, append_to_transcript, append_event,
  ensure_memory_scaffold, create_memory_item, update_memory_item, or any
  other write function.
- Never constructs a Provider client, API key, or network connection.
- Never instantiates AIAgent or any executable agent.
- All responses have dryRun=True, readOnly=True, sideEffects=False.

IMPORTANT: This service does NOT call build_system_prompt_parts() directly
because that function requires a live agent object. Instead, it assembles
prompt metadata by reading the same source files that the agent would use,
without constructing an executable agent.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from hermes_cli.config import load_config_readonly
from hermes_cli.dev_web_memory_service import redact_local_paths

logger = logging.getLogger(__name__)

# ── Truncation limits ──

_MAX_MESSAGE_LENGTH = 4000
_MAX_SESSION_ID_LENGTH = 200
_MAX_HISTORY_LIMIT = 100
_MAX_MEMORY_QUERY_LENGTH = 1000
_MAX_CATEGORIES = 20
_MAX_MEMORIES = 50
_MAX_SYSTEM_PREVIEW = 500
_MAX_HISTORY_PREVIEW = 300
_MAX_MEMORY_SUMMARY_PREVIEW = 300
_MAX_USER_MESSAGE_PREVIEW = 500
_MAX_CHECK_MESSAGE = 200
_MAX_WARNING = 200
_MAX_BLOCKED_REASON = 200
_MAX_MODEL_NAME = 100
_MAX_PROVIDER_NAME = 50

# ── Secret redaction patterns ──

_SECRET_PATTERNS = [
    (re.compile(r'api_key\s*=\s*\S+', re.IGNORECASE), 'api_key=[secret-redacted]'),
    (re.compile(r'api_key["\']?\s*:\s*["\']?\S+', re.IGNORECASE), 'api_key: [secret-redacted]'),
    (re.compile(r'Authorization\s*:\s*Bearer\s+\S+', re.IGNORECASE), 'Authorization: Bearer [secret-redacted]'),
    (re.compile(r'token\s*=\s*\S+', re.IGNORECASE), 'token=[secret-redacted]'),
    (re.compile(r'secret\s*=\s*\S+', re.IGNORECASE), 'secret=[secret-redacted]'),
    (re.compile(r'cookie\s*=\s*\S+', re.IGNORECASE), 'cookie=[secret-redacted]'),
]

# ── Safe provider name map ──

_SAFE_PROVIDER_MAP = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "deepseek": "DeepSeek",
    "zhipu": "ZhipuAI",
    "moonshot": "Moonshot",
    "qwen": "Qwen",
    "doubao": "Doubao",
    "siliconflow": "SiliconFlow",
    "localai": "LocalAI",
    "ollama": "Ollama",
    "glm": "GLM",
    "zai": "ZAI",
    "auto": "Auto",
}

# ── Section type enum ──

SECTION_SYSTEM_IDENTITY = "SYSTEM_IDENTITY"
SECTION_RUNTIME_INSTRUCTIONS = "RUNTIME_INSTRUCTIONS"
SECTION_SKILLS = "SKILLS"
SECTION_ENVIRONMENT = "ENVIRONMENT"
SECTION_CONTEXT_FILES = "CONTEXT_FILES"
SECTION_MEMORY_CONTEXT = "MEMORY_CONTEXT"
SECTION_HISTORY = "HISTORY"
SECTION_USER_MESSAGE = "USER_MESSAGE"
SECTION_TOOL_METADATA = "TOOL_METADATA"
SECTION_TIMESTAMP = "TIMESTAMP"


# ── Custom exceptions ──


class AgentPreviewError(Exception):
    """Raised when agent preview cannot be computed."""


class AgentConfigUnavailableError(AgentPreviewError):
    """Raised when agent config cannot be read."""


class AgentHistoryUnavailableError(AgentPreviewError):
    """Raised when session history cannot be read."""


class AgentMemoryContextUnavailableError(AgentPreviewError):
    """Raised when memory context cannot be read."""


class AgentPromptAssemblyError(AgentPreviewError):
    """Raised when prompt assembly fails."""


class InvalidSessionIdError(AgentPreviewError):
    """Raised when session ID format is invalid."""


class InvalidModelOverrideError(AgentPreviewError):
    """Raised when model override is not allowed."""


class InvalidTemperatureError(AgentPreviewError):
    """Raised when temperature is out of range."""


class InvalidMaxOutputTokensError(AgentPreviewError):
    """Raised when maxOutputTokens is out of range."""


class InvalidRequestError(AgentPreviewError):
    """Raised when request validation fails."""


# ── Helpers ──


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len with ellipsis indicator."""
    if not text or len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def redact_secrets(text: str) -> str:
    """Redact secret patterns from text."""
    if not text:
        return text
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _safe_provider_name(provider: str) -> str:
    """Get a safe display name for a provider."""
    if not provider:
        return ""
    lower = provider.lower().strip()
    name = _SAFE_PROVIDER_MAP.get(lower, provider.split("/")[-1])
    return _truncate(name, _MAX_PROVIDER_NAME)


def _safe_model_name(model: str) -> str:
    """Get a safe display name for a model."""
    if not model:
        return ""
    name = model.split("/")[-1] if "/" in model else model
    return _truncate(name, _MAX_MODEL_NAME)


def _validate_session_id(session_id: str) -> str | None:
    """Validate session ID format. Returns error message or None."""
    if not session_id:
        return None
    if len(session_id) > _MAX_SESSION_ID_LENGTH:
        return f"Session ID too long (max {_MAX_SESSION_ID_LENGTH} characters)."
    # Reject control characters
    if any(ord(c) < 32 for c in session_id):
        return "Session ID contains control characters."
    return None


def _extract_safe_model_info(config: dict[str, Any]) -> dict[str, Any]:
    """Extract safe model/provider information from config.

    Only returns safe fields: model name, provider display name,
    temperature, max_tokens. Never returns api_key, base_url, etc.
    """
    raw_model = config.get("model", "")
    if isinstance(raw_model, str):
        model_name = raw_model
    elif isinstance(raw_model, dict):
        model_name = str(raw_model.get("default", ""))
        if not model_name:
            model_name = ""
    else:
        model_name = ""

    provider = ""
    providers = config.get("providers", {})
    if isinstance(providers, dict):
        for prov_name in providers:
            provider = prov_name
            break

    temperature = config.get("temperature")
    if temperature is not None:
        try:
            temperature = float(temperature)
            if temperature < 0.0 or temperature > 2.0:
                temperature = None
        except (ValueError, TypeError):
            temperature = None

    max_tokens = config.get("max_tokens")
    if max_tokens is not None:
        try:
            max_tokens = int(max_tokens)
            if max_tokens < 1:
                max_tokens = None
        except (ValueError, TypeError):
            max_tokens = None

    return {
        "name": _safe_model_name(model_name),
        "provider": _safe_provider_name(provider),
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }


def _load_history_readonly(
    session_id: str,
    state_db_path: Path,
    limit: int = 20,
) -> dict[str, Any]:
    """Load session history in read-only mode.

    Returns a dict with history metadata and safe previews.
    Never writes to the database.
    """
    from hermes_state import SessionDB

    if not state_db_path.exists():
        return {
            "exists": False,
            "historyIncluded": False,
            "historyMessageCount": 0,
            "historyTruncated": False,
            "messages": [],
        }

    try:
        db = SessionDB(state_db_path, read_only=True)
    except Exception:
        return {
            "exists": False,
            "historyIncluded": False,
            "historyMessageCount": 0,
            "historyTruncated": False,
            "messages": [],
        }

    try:
        session = db.get_session(session_id)
        if session is None:
            return {
                "exists": False,
                "historyIncluded": False,
                "historyMessageCount": 0,
                "historyTruncated": False,
                "messages": [],
            }

        all_messages = db.get_messages(session_id)
        total = len(all_messages)

        if limit <= 0:
            messages = []
        elif limit >= total:
            messages = all_messages
        else:
            # Take the last N messages
            messages = all_messages[-limit:]

        # Build safe message previews
        safe_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = ""
            if isinstance(msg.get("content"), str):
                content = msg["content"]
            elif isinstance(msg.get("content"), list):
                # Multi-part content — concatenate text parts
                parts = []
                for part in msg["content"]:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                content = " ".join(parts)

            has_tool_calls = bool(msg.get("tool_calls"))

            # Redact and truncate for preview
            safe_content = redact_local_paths(content)
            safe_content = redact_secrets(safe_content)

            safe_messages.append({
                "role": role,
                "characterCount": len(content),
                "preview": _truncate(safe_content, _MAX_HISTORY_PREVIEW),
                "hasToolCalls": has_tool_calls,
            })

        return {
            "exists": True,
            "historyIncluded": True,
            "historyMessageCount": total,
            "historyTruncated": total > limit,
            "messages": safe_messages,
        }
    except Exception:
        return {
            "exists": False,
            "historyIncluded": False,
            "historyMessageCount": 0,
            "historyTruncated": False,
            "messages": [],
        }


def _load_memory_context_readonly(
    hermes_home: Path,
    query: str = "",
    max_categories: int = 5,
    max_memories: int = 10,
) -> dict[str, Any]:
    """Load memory context in read-only mode.

    Returns a dict with memory category/item metadata and safe previews.
    Never writes to memory files or events.
    """
    from hermes_cli.memory_router import (
        active_root_categories,
        parse_index,
        score_category,
        score_memory_item,
    )

    memory_dir = hermes_home / "memory"
    root_file = hermes_home / "MEMORY.md"

    if not root_file.exists() or not memory_dir.exists():
        return {
            "enabled": False,
            "categoryCount": 0,
            "memoryCount": 0,
            "items": [],
            "truncated": False,
        }

    try:
        categories = active_root_categories(home=hermes_home)

        # Score categories if query provided
        scored_cats: list[tuple[str, Any, int]] = []
        if query:
            for cat_name, cat in categories.items():
                score = score_category(cat, query)
                if score > 0:
                    scored_cats.append((cat_name, cat, score))
            scored_cats.sort(key=lambda x: x[2], reverse=True)
            scored_cats = scored_cats[:max_categories]
        else:
            # Return top categories by priority without scoring
            scored_cats = [(name, cat, 0) for name, cat in list(categories.items())[:max_categories]]

        # Collect memory items from scored categories
        all_items = []
        seen_ids: set[str] = set()
        for cat_name, cat, cat_score in scored_cats:
            try:
                cat_items = parse_index(cat_name, home=hermes_home)
            except Exception:
                cat_items = []

            for item in cat_items:
                if item.memory_id in seen_ids:
                    continue
                if item.fields.get("status") != "active":
                    continue
                seen_ids.add(item.memory_id)

                item_score = cat_score
                if query:
                    item_score = score_memory_item(item, query)
                    if item_score <= 0:
                        continue

                summary = item.summary or ""
                safe_summary = redact_local_paths(summary)
                safe_summary = redact_secrets(safe_summary)

                all_items.append({
                    "memoryId": item.memory_id,
                    "title": _truncate(item.title or "", _MAX_MEMORY_SUMMARY_PREVIEW),
                    "category": cat_name,
                    "score": item_score,
                    "summaryPreview": _truncate(safe_summary, _MAX_MEMORY_SUMMARY_PREVIEW),
                })

        # Sort by score descending, limit
        all_items.sort(key=lambda x: x["score"], reverse=True)
        truncated = len(all_items) > max_memories
        all_items = all_items[:max_memories]

        return {
            "enabled": True,
            "categoryCount": len(scored_cats),
            "memoryCount": len(all_items),
            "items": all_items,
            "truncated": truncated,
        }
    except Exception:
        return {
            "enabled": False,
            "categoryCount": 0,
            "memoryCount": 0,
            "items": [],
            "truncated": False,
        }


# ── Preview Service ──


class DevAgentPreviewService:
    """Read-only agent preview service for the Dev Web API.

    Assembles prompt metadata and capability plans without:
    - Constructing an executable Agent
    - Calling any LLM
    - Executing any Tool
    - Writing any Session, Message, Memory, or Review data
    - Registering any Streaming callback

    All inputs use explicit paths — never falls back to ~/.hermes.
    """

    def __init__(self, hermes_home: Path) -> None:
        self._home = hermes_home
        self._state_db_path = hermes_home / "state.db"

    def is_available(self) -> bool:
        """Check if the preview service can operate."""
        return self._home.is_dir()

    def preview_prompt(
        self,
        *,
        message: str,
        session_id: str | None = None,
        include_history: bool = True,
        history_limit: int = 20,
        include_memory_context: bool = True,
        memory_query: str = "",
        max_categories: int = 5,
        max_memories: int = 10,
        include_system_preview: bool = False,
        include_tool_metadata: bool = True,
        model_override: str | None = None,
        temperature_override: float | None = None,
        max_tokens_override: int | None = None,
    ) -> dict[str, Any]:
        """Generate a Prompt Preview response.

        Pure read-only computation. No side effects.
        """
        # 1. Validate inputs
        self._validate_overrides(model_override, temperature_override, max_tokens_override)

        # 2. Read config
        config = self._read_config()
        model_info = _extract_safe_model_info(config)

        # Apply safe overrides
        if model_override:
            model_info["name"] = _safe_model_name(model_override)
        if temperature_override is not None:
            model_info["temperature"] = temperature_override
        if max_tokens_override is not None:
            model_info["maxOutputTokens"] = max_tokens_override

        # 3. Session / History
        session_info: dict[str, Any] = {
            "sessionId": session_id or "",
            "exists": False,
            "historyIncluded": False,
            "historyMessageCount": 0,
            "historyTruncated": False,
        }
        history_messages: list[dict[str, Any]] = []

        if session_id and include_history:
            session_info.update(
                exists=True,
                historyIncluded=True,
            )
            history_result = _load_history_readonly(
                session_id, self._state_db_path, limit=history_limit,
            )
            session_info["exists"] = history_result["exists"]
            session_info["historyIncluded"] = history_result["historyIncluded"]
            session_info["historyMessageCount"] = history_result["historyMessageCount"]
            session_info["historyTruncated"] = history_result["historyTruncated"]
            history_messages = history_result["messages"]
        elif session_id and not include_history:
            session_info["sessionId"] = session_id
            session_info["exists"] = True
            session_info["historyIncluded"] = False

        # 4. Memory context
        memory_context: dict[str, Any] = {
            "enabled": False,
            "categoryCount": 0,
            "memoryCount": 0,
            "items": [],
            "truncated": False,
        }
        if include_memory_context:
            memory_context = _load_memory_context_readonly(
                self._home,
                query=memory_query,
                max_categories=max_categories,
                max_memories=max_memories,
            )

        # 5. Build prompt section metadata
        sections = self._build_section_metadata(
            config,
            session_info,
            history_messages,
            memory_context,
            message,
            include_system_preview,
            include_tool_metadata,
        )

        prompt_metadata = {
            "sectionCount": len(sections),
            "characterCount": sum(s.get("characterCount", 0) for s in sections),
            "truncated": False,
            "sections": sections,
        }

        # 6. Build capabilities (all forced disabled in Phase 1E)
        capabilities = self._build_capabilities(
            tools_requested=False,
            stream_requested=False,
            auto_memory_requested=False,
        )

        # 7. Build checks
        checks = self._build_checks()

        # 8. Build no-effects list
        no_effects = [
            "No language model request was sent.",
            "No session message was written.",
            "No memory file was modified.",
            "No tool was executed.",
            "No review item was created.",
        ]

        # 9. Build safety flags
        safety = {
            "readOnly": True,
            "sideEffects": False,
            "llmCalled": False,
            "toolsExecuted": False,
            "sessionWritten": False,
            "memoryWritten": False,
            "reviewQueued": False,
        }

        # 10. User message preview (redacted)
        safe_message = redact_local_paths(message)
        safe_message = redact_secrets(safe_message)

        # Build the final response
        result: dict[str, Any] = {
            "dryRun": True,
            "operation": "PROMPT_PREVIEW",
            "allowed": True,
            "blockedReason": None,
            "session": session_info,
            "model": model_info,
            "prompt": prompt_metadata,
            "memoryContext": memory_context,
            "capabilities": capabilities,
            "checks": checks,
            "noEffects": no_effects,
            "safety": safety,
            "warnings": [],
            "userMessagePreview": _truncate(safe_message, _MAX_USER_MESSAGE_PREVIEW),
        }

        return result

    def dry_run_agent(
        self,
        *,
        message: str,
        session_id: str | None = None,
        include_history: bool = True,
        history_limit: int = 20,
        include_memory_context: bool = True,
        memory_query: str = "",
        tools_requested: bool = False,
        stream_requested: bool = False,
        auto_memory_requested: bool = False,
        model_override: str | None = None,
        temperature_override: float | None = None,
        max_tokens_override: int | None = None,
    ) -> dict[str, Any]:
        """Generate an Agent Run Dry-Run response.

        Pure read-only computation. Simulates what *would* happen without
        executing anything.
        """
        # 1. Validate inputs
        self._validate_overrides(model_override, temperature_override, max_tokens_override)

        # 2. Read config
        config = self._read_config()
        model_info = _extract_safe_model_info(config)

        # Apply safe overrides
        if model_override:
            model_info["name"] = _safe_model_name(model_override)
        if temperature_override is not None:
            model_info["temperature"] = temperature_override
        if max_tokens_override is not None:
            model_info["maxOutputTokens"] = max_tokens_override

        # 3. Session / History
        session_info: dict[str, Any] = {
            "sessionId": session_id or "",
            "exists": False,
            "historyIncluded": False,
            "historyMessageCount": 0,
            "historyTruncated": False,
        }
        history_messages: list[dict[str, Any]] = []

        if session_id and include_history:
            session_info.update(
                exists=True,
                historyIncluded=True,
            )
            history_result = _load_history_readonly(
                session_id, self._state_db_path, limit=history_limit,
            )
            session_info["exists"] = history_result["exists"]
            session_info["historyIncluded"] = history_result["historyIncluded"]
            session_info["historyMessageCount"] = history_result["historyMessageCount"]
            session_info["historyTruncated"] = history_result["historyTruncated"]
            history_messages = history_result["messages"]
        elif session_id and not include_history:
            session_info["sessionId"] = session_id
            session_info["exists"] = True
            session_info["historyIncluded"] = False

        # 4. Memory context
        memory_context: dict[str, Any] = {
            "enabled": False,
            "categoryCount": 0,
            "memoryCount": 0,
            "items": [],
            "truncated": False,
        }
        if include_memory_context:
            memory_context = _load_memory_context_readonly(
                self._home,
                query=memory_query,
                max_categories=5,
                max_memories=10,
            )

        # 5. Build prompt section metadata
        sections = self._build_section_metadata(
            config,
            session_info,
            history_messages,
            memory_context,
            message,
            include_system_preview=False,
            include_tool_metadata=False,
        )

        prompt_metadata = {
            "sectionCount": len(sections),
            "characterCount": sum(s.get("characterCount", 0) for s in sections),
            "truncated": False,
            "sections": sections,
        }

        # 6. Build capabilities (ALL forced disabled in Phase 1E)
        capabilities = self._build_capabilities(
            tools_requested=tools_requested,
            stream_requested=stream_requested,
            auto_memory_requested=auto_memory_requested,
        )

        # 7. Build checks
        checks = self._build_checks()

        # 8. Build no-effects list
        no_effects = [
            "No language model request was sent.",
            "No session message was written.",
            "No memory file was modified.",
            "No tool was executed.",
            "No review item was created.",
        ]

        # 9. Build safety flags
        safety = {
            "readOnly": True,
            "sideEffects": False,
            "llmCalled": False,
            "toolsExecuted": False,
            "sessionWritten": False,
            "memoryWritten": False,
            "reviewQueued": False,
        }

        # 10. Build warnings about forced-disabled capabilities
        warnings = []
        if tools_requested:
            warnings.append("Tools were requested but forced disabled in Phase 1E preview.")
        if stream_requested:
            warnings.append("Streaming was requested but forced disabled in Phase 1E preview.")
        if auto_memory_requested:
            warnings.append("Auto-memory was requested but forced disabled in Phase 1E preview.")

        result: dict[str, Any] = {
            "dryRun": True,
            "operation": "AGENT_RUN_DRY_RUN",
            "allowed": True,
            "blockedReason": None,
            "session": session_info,
            "model": model_info,
            "prompt": prompt_metadata,
            "memoryContext": memory_context,
            "capabilities": capabilities,
            "checks": checks,
            "noEffects": no_effects,
            "safety": safety,
            "warnings": [_truncate(w, _MAX_WARNING) for w in warnings],
        }

        return result

    # ── Internal helpers ──

    def _read_config(self) -> dict[str, Any]:
        """Read agent config in read-only mode."""
        try:
            return load_config_readonly()
        except Exception as exc:
            raise AgentConfigUnavailableError(
                "Agent configuration is unavailable."
            ) from exc

    def _validate_overrides(
        self,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> None:
        """Validate model/temperature/max_tokens overrides."""
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise InvalidTemperatureError(
                    "Temperature must be a number between 0.0 and 2.0."
                )
            if temperature < 0.0 or temperature > 2.0:
                raise InvalidTemperatureError(
                    "Temperature must be between 0.0 and 2.0."
                )

        if max_tokens is not None:
            if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 32768:
                raise InvalidMaxOutputTokensError(
                    "maxOutputTokens must be between 1 and 32768."
                )

    def _build_section_metadata(
        self,
        config: dict[str, Any],
        session_info: dict[str, Any],
        history_messages: list[dict[str, Any]],
        memory_context: dict[str, Any],
        message: str,
        include_system_preview: bool,
        include_tool_metadata: bool,
    ) -> list[dict[str, Any]]:
        """Build prompt section metadata list.

        Returns metadata about each prompt section without exposing full content.
        Character counts are estimated based on typical assembly.
        """
        sections: list[dict[str, Any]] = []
        warnings: list[str] = []

        # SYSTEM_IDENTITY section
        soul_path = self._home / "SOUL.md"
        soul_chars = 0
        if soul_path.exists():
            try:
                soul_chars = len(soul_path.read_text(encoding="utf-8"))
            except Exception:
                soul_chars = 0
        else:
            # Default identity is ~500 chars
            soul_chars = 500

        system_preview = None
        if include_system_preview and soul_chars > 0:
            try:
                if soul_path.exists():
                    raw_preview = soul_path.read_text(encoding="utf-8")
                else:
                    raw_preview = "Hermes AI Assistant"

                # Redact and truncate
                safe_preview = redact_local_paths(raw_preview)
                safe_preview = redact_secrets(safe_preview)
                system_preview = _truncate(safe_preview, _MAX_SYSTEM_PREVIEW)
            except Exception:
                system_preview = None

        sections.append({
            "type": SECTION_SYSTEM_IDENTITY,
            "included": True,
            "characterCount": soul_chars,
            "messageCount": None,
            "preview": system_preview,
            "redacted": True,
        })

        # RUNTIME_INSTRUCTIONS section
        runtime_chars = 1200  # Estimated tool guidance, enforcement, etc.
        sections.append({
            "type": SECTION_RUNTIME_INSTRUCTIONS,
            "included": True,
            "characterCount": runtime_chars,
            "messageCount": None,
            "preview": None,
            "redacted": True,
        })

        # SKILLS section
        skills_chars = 0
        skills_dir = self._home / "skills"
        if skills_dir.exists():
            # Estimate skills prompt length
            try:
                skill_files = list(skills_dir.rglob("SKILL.md"))
                skills_chars = len(skill_files) * 200  # Rough estimate
            except Exception:
                skills_chars = 0

        sections.append({
            "type": SECTION_SKILLS,
            "included": skills_chars > 0,
            "characterCount": skills_chars,
            "messageCount": None,
            "preview": None,
            "redacted": True,
        })

        # ENVIRONMENT section
        env_chars = 300  # Estimated environment hints
        sections.append({
            "type": SECTION_ENVIRONMENT,
            "included": True,
            "characterCount": env_chars,
            "messageCount": None,
            "preview": None,
            "redacted": True,
        })

        # CONTEXT_FILES section
        context_chars = 0
        # Check for context files in typical locations
        for cf_name in ["AGENTS.md", "CLAUDE.md", ".cursorrules"]:
            for parent in [self._home, Path.cwd()]:
                cf_path = parent / cf_name
                if cf_path.exists():
                    try:
                        context_chars += len(cf_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass

        sections.append({
            "type": SECTION_CONTEXT_FILES,
            "included": context_chars > 0,
            "characterCount": context_chars,
            "messageCount": None,
            "preview": None,
            "redacted": True,
        })

        # MEMORY_CONTEXT section
        memory_chars = 0
        memory_items = memory_context.get("items", [])
        for item in memory_items:
            memory_chars += len(item.get("summaryPreview", "")) + 50  # +50 for formatting
        sections.append({
            "type": SECTION_MEMORY_CONTEXT,
            "included": memory_context.get("enabled", False),
            "characterCount": memory_chars,
            "messageCount": None,
            "preview": None,
            "redacted": True,
        })

        # HISTORY section
        history_chars = sum(m.get("characterCount", 0) for m in history_messages)
        sections.append({
            "type": SECTION_HISTORY,
            "included": session_info.get("historyIncluded", False),
            "characterCount": history_chars,
            "messageCount": session_info.get("historyMessageCount", 0),
            "preview": None,
            "redacted": True,
        })

        # USER_MESSAGE section
        safe_msg = redact_local_paths(message)
        safe_msg = redact_secrets(safe_msg)
        sections.append({
            "type": SECTION_USER_MESSAGE,
            "included": True,
            "characterCount": len(message),
            "messageCount": None,
            "preview": _truncate(safe_msg, _MAX_USER_MESSAGE_PREVIEW),
            "redacted": False,
        })

        # TOOL_METADATA section
        if include_tool_metadata:
            sections.append({
                "type": SECTION_TOOL_METADATA,
                "included": True,
                "characterCount": 0,
                "messageCount": None,
                "preview": None,
                "redacted": True,
            })

        # TIMESTAMP section
        sections.append({
            "type": SECTION_TIMESTAMP,
            "included": True,
            "characterCount": 80,  # Estimated timestamp line
            "messageCount": None,
            "preview": None,
            "redacted": False,
        })

        return sections

    def _build_capabilities(
        self,
        *,
        tools_requested: bool = False,
        stream_requested: bool = False,
        auto_memory_requested: bool = False,
    ) -> dict[str, Any]:
        """Build capability plan for the response.

        Phase 1E: ALL execution capabilities are forced disabled.
        """
        return {
            "llmCallRequested": False,
            "llmCallAvailable": False,
            "llmCallForcedDisabled": True,
            "streamingRequested": stream_requested,
            "streamingAvailable": False,
            "streamingForcedDisabled": True,
            "toolsRequested": tools_requested,
            "toolExecutionAvailable": False,
            "toolExecutionForcedDisabled": True,
            "autoMemoryRequested": auto_memory_requested,
            "memoryWriteAvailable": False,
            "memoryWriteForcedDisabled": True,
            "sessionWriteAvailable": False,
            "reviewQueueAvailable": False,
        }

    def _build_checks(self) -> list[dict[str, Any]]:
        """Build safety check results."""
        return [
            {
                "code": "NO_LLM_CALL",
                "passed": True,
                "message": _truncate("No language model request was sent.", _MAX_CHECK_MESSAGE),
            },
            {
                "code": "NO_TOOL_EXECUTION",
                "passed": True,
                "message": _truncate("No tool was executed.", _MAX_CHECK_MESSAGE),
            },
            {
                "code": "NO_SESSION_WRITE",
                "passed": True,
                "message": _truncate("No session message was written.", _MAX_CHECK_MESSAGE),
            },
            {
                "code": "NO_MEMORY_WRITE",
                "passed": True,
                "message": _truncate("No memory file was modified.", _MAX_CHECK_MESSAGE),
            },
            {
                "code": "NO_REVIEW_QUEUE",
                "passed": True,
                "message": _truncate("No review item was created.", _MAX_CHECK_MESSAGE),
            },
        ]
