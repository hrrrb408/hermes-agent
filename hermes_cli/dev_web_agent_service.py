"""Dev Web API agent status service.

Read-only service that reports safe agent configuration status.
No agent execution, no LLM calls, no tool execution.

Importing this module has no side effects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_cli.config import load_config_readonly


# ── Custom exceptions ──


class AgentStatusError(Exception):
    """Raised when agent status cannot be determined."""


# ── Sensitive fields that must never be exposed ──

_SENSITIVE_KEYS = frozenset({
    "api_key",
    "api_key_env_vars",
    "base_url",
    "secret",
    "token",
    "credential",
    "credential_pool_strategies",
    "password",
    "cookie",
})

# Safe provider names for display
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
    "auto": "Auto",
}


def _safe_provider_name(provider: str) -> str:
    """Get a safe display name for a provider."""
    if not provider:
        return ""
    lower = provider.lower().strip()
    return _SAFE_PROVIDER_MAP.get(lower, provider.split("/")[-1])


def _safe_model_name(model: str) -> str:
    """Get a safe display name for a model (strip path-like segments)."""
    if not model:
        return ""
    # Only keep the last segment if it contains /
    return model.split("/")[-1] if "/" in model else model


# ── Agent status service ──


class DevAgentStatusService:
    """Read-only agent status service for the Dev Web API.

    Reports safe configuration status without exposing secrets,
    API keys, base URLs, or full configuration dumps.
    """

    def __init__(self, hermes_home: Path) -> None:
        self._home = hermes_home

    def get_status(self) -> dict[str, Any]:
        """Get safe agent configuration status.

        Returns a DTO dict with safe runtime, model, and memory info.
        Never returns API keys, base URLs, or full config.
        """
        try:
            config = load_config_readonly()
        except Exception:
            return {
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
            }

        # Extract safe model info
        # config["model"] can be a string or a dict with provider routing
        raw_model = config.get("model", "")
        if isinstance(raw_model, str):
            model_name = raw_model
        elif isinstance(raw_model, dict):
            # Try to extract a safe default model name
            model_name = str(raw_model.get("default", ""))
            if not model_name:
                model_name = ""
        else:
            model_name = ""

        provider = ""
        providers = config.get("providers", {})
        if isinstance(providers, dict):
            for _prov_name, prov_config in providers.items():
                if isinstance(prov_config, dict):
                    provider = _prov_name
                    break

        # Extract safe memory info
        memory_config = config.get("memory", {})
        context_loader = memory_config.get("context_loader", {})

        return {
            "available": True,
            "readOnly": True,
            "runtime": {
                "entry": "conversation_loop",
                "messageSendEnabled": False,
                "streamingEnabled": False,
                "toolExecutionEnabled": False,
            },
            "model": {
                "configured": bool(model_name),
                "provider": _safe_provider_name(provider),
                "name": _safe_model_name(model_name),
            },
            "memory": {
                "enabled": bool(memory_config.get("enabled", True)),
                "contextLoaderEnabled": bool(
                    context_loader.get("enabled", True)
                ),
                "autoWriteEnabled": False,
                "reviewQueueEnabled": False,
            },
        }
