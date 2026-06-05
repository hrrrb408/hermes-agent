"""Runtime integration for hierarchical memory context.

This module is read-only. It loads relevant layered memories for the current
user message and formats an API-call-time prompt block. It does not modify
MEMORY.md, indexes, records, events, snapshots, or session transcripts.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RuntimeMemoryContext:
    enabled: bool
    context: str
    selected_categories: list[str]
    loaded_memories: list[dict[str, str]]
    skipped: list[str]
    error: str = ""

    @property
    def chars(self) -> int:
        return len(self.context)


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_bool(name: str) -> bool | None:
    if name not in os.environ:
        return None
    return _as_bool(os.environ.get(name), True)


def _as_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return parsed if parsed > 0 else default


def _runtime_memory_config(config: dict | None) -> dict[str, Any]:
    config = config or {}
    memory_cfg = config.get("memory", {}) if isinstance(config, dict) else {}
    if not isinstance(memory_cfg, dict):
        memory_cfg = {}
    loader_cfg = memory_cfg.get("context_loader", {})
    if not isinstance(loader_cfg, dict):
        loader_cfg = {}

    memory_enabled = _as_bool(memory_cfg.get("enabled"), True)
    if memory_cfg.get("memory_enabled") is False:
        memory_enabled = False
    context_enabled = _as_bool(loader_cfg.get("enabled"), True)

    env_memory_enabled = _env_bool("HERMES_MEMORY_ENABLED")
    if env_memory_enabled is not None:
        memory_enabled = env_memory_enabled
    env_context_enabled = _env_bool("HERMES_MEMORY_CONTEXT_ENABLED")
    if env_context_enabled is not None:
        context_enabled = env_context_enabled

    return {
        "memory_enabled": memory_enabled,
        "context_enabled": context_enabled,
        "max_categories": _as_int(loader_cfg.get("max_categories"), 3),
        "max_memories": _as_int(loader_cfg.get("max_memories"), 5),
        "max_record_chars": _as_int(loader_cfg.get("max_record_chars"), 3000),
        "include_archived": _as_bool(loader_cfg.get("include_archived"), False),
        "log_loaded_memories": _as_bool(loader_cfg.get("log_loaded_memories"), True),
    }


def _format_runtime_memory_context(result) -> str:
    if not result.loaded_memories:
        return ""

    parts = ["[Relevant Long-term Memories]"]
    for entry in result.loaded_memories:
        item = entry.item
        fields = item.fields
        parts.extend(
            [
                "",
                f"[{item.memory_id}] {item.title}",
                f"category: {item.category}",
                f"importance: {fields.get('importance', '')}",
                f"ttl: {fields.get('ttl', '')}",
                f"status: {fields.get('status', '')}",
                f"updated_at: {fields.get('updated_at', '')}",
                f"summary: {fields.get('summary', '')}",
                "",
                entry.record_text,
            ]
        )
    return "\n".join(parts).strip()


def _short_skipped_memory_note(note: str) -> str:
    memory_id = ""
    status = ""
    for part in str(note).replace(":", " ").split():
        if part.startswith("MEM-"):
            memory_id = part
        elif part.startswith("status="):
            status = part.split("=", 1)[1]
    if memory_id and status:
        return f"{memory_id}(status={status})"
    if memory_id:
        return memory_id
    return str(note)[:80]


def _log_runtime_memory_summary(
    memory_context: RuntimeMemoryContext,
    *,
    gateway_log: bool = False,
) -> None:
    selected = ", ".join(memory_context.selected_categories) or "none"
    loaded = ", ".join(
        (
            f"{item.get('memory_id', '')}"
            f"(category={item.get('category', '')}, status={item.get('status', '')})"
        ).strip()
        for item in memory_context.loaded_memories
    ) or "none"
    skipped = ", ".join(_short_skipped_memory_note(note) for note in memory_context.skipped) or "none"
    if memory_context.error:
        message = f"Runtime memory injection failed: {memory_context.error[:160]}"
    elif not memory_context.enabled:
        message = "Runtime memory injection: disabled"
    else:
        message = (
            "Runtime memory injection: enabled; "
            f"Selected categories: {selected}; "
            f"Loaded memories: {loaded}; "
            f"Skipped memories: {skipped}; "
            f"Memory context chars: {memory_context.chars}"
        )
    logger.info(message)
    if gateway_log:
        logging.getLogger("gateway.runtime_memory").info(message)


def load_runtime_memory_context(
    user_message: str,
    config: dict | None = None,
) -> RuntimeMemoryContext:
    cfg = _runtime_memory_config(config)
    if not cfg["memory_enabled"] or not cfg["context_enabled"]:
        memory_context = RuntimeMemoryContext(
            enabled=False,
            context="",
            selected_categories=[],
            loaded_memories=[],
            skipped=[],
        )
        _log_runtime_memory_summary(
            memory_context,
            gateway_log=_as_bool(os.getenv("HERMES_DEV_GATEWAY_MEMORY_LOGS"), False),
        )
        return memory_context

    try:
        from hermes_cli.memory_router import load_memory_context

        result = load_memory_context(
            query=user_message,
            max_categories=cfg["max_categories"],
            max_memories=cfg["max_memories"],
            max_record_chars=cfg["max_record_chars"],
            include_archived=cfg["include_archived"],
        )
        context = _format_runtime_memory_context(result)
        selected = [entry.category.name for entry in result.selected_categories]
        loaded = [
            {
                "memory_id": entry.item.memory_id,
                "title": entry.item.title,
                "category": entry.item.category,
                "status": entry.item.fields.get("status", ""),
            }
            for entry in result.loaded_memories
        ]
        memory_context = RuntimeMemoryContext(
            enabled=True,
            context=context,
            selected_categories=selected,
            loaded_memories=loaded,
            skipped=result.skipped,
        )
        if cfg["log_loaded_memories"]:
            _log_runtime_memory_summary(
                memory_context,
                gateway_log=_as_bool(os.getenv("HERMES_DEV_GATEWAY_MEMORY_LOGS"), False),
            )
        return memory_context
    except Exception as exc:
        memory_context = RuntimeMemoryContext(
            enabled=False,
            context="",
            selected_categories=[],
            loaded_memories=[],
            skipped=[],
            error=str(exc),
        )
        _log_runtime_memory_summary(
            memory_context,
            gateway_log=_as_bool(os.getenv("HERMES_DEV_GATEWAY_MEMORY_LOGS"), False),
        )
        return memory_context


def build_runtime_prompt_preview(
    user_message: str,
    config: dict | None = None,
    *,
    system_prompt: str = "<System Prompt ...>",
) -> tuple[RuntimeMemoryContext, str]:
    memory_context = load_runtime_memory_context(user_message, config)
    parts = [system_prompt]
    if memory_context.context:
        parts.append(memory_context.context)
    parts.append("[Current User Message]\n\n" + user_message)
    return memory_context, "\n\n".join(part for part in parts if part)
