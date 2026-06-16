"""Phase 3B Real Provider Config Model for the Hermes Dev WebUI.

A bounded, env-driven config model for the **real** provider round-trip boundary.
Real provider stays **disabled by default**. This module only *reads* the
configuration surface (and the API-key **presence**); it never prints, logs,
audits, persists, or returns an API-key value.

Mode semantics (mirrors Phase 2B):
  - ``disabled``: no provider at all (default).
  - ``fake``: deterministic offline adapter (Phase 2B) — unchanged.
  - ``real``: the gated real round-trip. Reachable only when EVERY enablement
    condition holds (see ``evaluate_real_provider_gating``). Otherwise blocked.

Config surface (read only; never the key value):
  - ``HERMES_PROVIDER_MODE``           = disabled|fake|real
  - ``HERMES_PROVIDER_API_ENABLED``    = 0|1
  - ``HERMES_PROVIDER_NAME``           = openai_compatible|anthropic_compatible|...
  - ``HERMES_PROVIDER_BASE_URL``       = <allowlisted host; never logged raw>
  - ``HERMES_PROVIDER_MODEL``          = <safe string>
  - ``HERMES_PROVIDER_TIMEOUT_SECONDS``= <bounded number>
  - ``HERMES_PROVIDER_MAX_RETRIES``    = <bounded number>
  - ``HERMES_PROVIDER_DAILY_BUDGET_CENTS`` = <bounded number>

Architecture constraints (mirrors the rest of the chain):
  - stdlib only (no third-party imports)
  - never reads ~/.hermes, never touches production state.db
  - never exposes an API-key value — only ``env_present`` / ``env_missing``
  - deterministic, JSON-serializable output

Phase: 3B — Real Provider Read-only Controlled Integration
Status: config model implemented (real provider disabled by default)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

PROVIDER_MODE_DISABLED = "disabled"
PROVIDER_MODE_FAKE = "fake"
PROVIDER_MODE_REAL = "real"

_VALID_PROVIDER_MODES: frozenset[str] = frozenset(
    {PROVIDER_MODE_DISABLED, PROVIDER_MODE_FAKE, PROVIDER_MODE_REAL}
)

# Adapter names supported by the generic boundary. Phase 3B ships the first
# concrete impl (OpenAI-compatible); the others are recognised names reserved
# for future slices and resolve to ``blocked_provider_name_not_supported``.
PROVIDER_NAME_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_NAME_ANTHROPIC_COMPATIBLE = "anthropic_compatible"
PROVIDER_NAME_ZAI_COMPATIBLE = "zai_compatible"
PROVIDER_NAME_OPENROUTER_COMPATIBLE = "openrouter_compatible"

_KNOWN_PROVIDER_NAMES: frozenset[str] = frozenset(
    {
        PROVIDER_NAME_OPENAI_COMPATIBLE,
        PROVIDER_NAME_ANTHROPIC_COMPATIBLE,
        PROVIDER_NAME_ZAI_COMPATIBLE,
        PROVIDER_NAME_OPENROUTER_COMPATIBLE,
    }
)
# Names with a concrete Phase 3B adapter implementation.
_IMPLEMENTED_PROVIDER_NAMES: frozenset[str] = frozenset(
    {PROVIDER_NAME_OPENAI_COMPATIBLE}
)

# Bounded, clamped numeric config ranges. These are HARD ceilings; a value
# outside the range is clamped, never rejected silently as a crash.
_MIN_TIMEOUT_SECONDS = 1
_MAX_TIMEOUT_SECONDS = 60
_DEFAULT_TIMEOUT_SECONDS = 20

_MIN_MAX_RETRIES = 0
_MAX_MAX_RETRIES = 4
_DEFAULT_MAX_RETRIES = 2

_MIN_DAILY_BUDGET_CENTS = 0
_MAX_DAILY_BUDGET_CENTS = 500  # $5.00 hard ceiling for the dev workbench
_DEFAULT_DAILY_BUDGET_CENTS = 100

_MIN_MAX_TOKENS = 1
_MAX_MAX_TOKENS = 4096
_DEFAULT_MAX_TOKENS = 1024

# Per-request + rate-limit caps (frozen by the cost / rate-limit policy).
_DEFAULT_PER_MINUTE_REQUEST_CAP = 20
_DEFAULT_DAILY_REQUEST_CAP = 200
_DEFAULT_DAILY_TOKEN_CAP = 500_000

# Production boundary (read-only observation only — never signals).
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Accepted provider API key env vars (read ONLY for presence; never the value).
_PROVIDER_KEY_ENVS: tuple[str, ...] = (
    "HERMES_PROVIDER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "ZAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
)

# Base-URL allowlist (hosts only). Phase 3B allows the de-facto OpenAI-compatible
# endpoints. Anything else → ``blocked_provider_base_url_not_allowed``. The
# allowlist is matched on the URL *host* (scheme must be https); the full
# secret-bearing URL is never logged.
_ALLOWED_BASE_URL_HOSTS: frozenset[str] = frozenset(
    {
        "api.openai.com",
        "api.z.ai",
        "open.bigmodel.cn",
    }
)

# Model allowlist (safe model id strings). Unknown model → blocked.
_ALLOWED_MODELS: frozenset[str] = frozenset(
    {
        "gpt-4o-mini",
        "gpt-4o",
        "glm-4-flash",
        "glm-4",
    }
)


# ---------------------------------------------------------------------------
# 2. Env reading helpers (value-free for secrets)
# ---------------------------------------------------------------------------


def _env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name, default)
    if not isinstance(value, str):
        return default
    return value.strip()


def _env_int(name: str, default: int, lo: int, hi: int) -> int:
    raw = _env_str(name, "")
    if not raw:
        return default
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, parsed))


def _normalize_mode(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _VALID_PROVIDER_MODES:
            return lowered
    return PROVIDER_MODE_DISABLED


def _normalize_provider_name(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _KNOWN_PROVIDER_NAMES:
            return lowered
    return PROVIDER_NAME_OPENAI_COMPATIBLE


def _is_dev_home() -> bool:
    """True only when HERMES_HOME resolves to the dev home, not ~/.hermes."""
    home_str = os.environ.get("HERMES_HOME", "")
    if not home_str:
        return False
    try:
        home = Path(home_str).resolve()
    except (OSError, ValueError):
        return False
    try:
        prod = Path(_PRODUCTION_HERMES_HOME).resolve()
    except (OSError, ValueError):
        prod = Path(_PRODUCTION_HERMES_HOME)
    return home != prod


def _api_key_source_detail() -> str:
    """Return ``env_present`` / ``env_missing`` — never the value."""
    for env_name in _PROVIDER_KEY_ENVS:
        value = os.environ.get(env_name, "")
        if isinstance(value, str) and value.strip():
            return "env_present"
    return "env_missing"


def _api_key_present() -> bool:
    return _api_key_source_detail() == "env_present"


def _base_url_host_allowed(base_url: str) -> tuple[bool, str]:
    """Return (allowed, host) for a base URL. https-only; host allowlist."""
    if not isinstance(base_url, str) or not base_url.strip():
        return False, ""
    url = base_url.strip()
    if not url.lower().startswith("https://"):
        return False, ""
    rest = url[len("https://"):]
    # Strip path / query / userinfo. The host is up to the first '/', '?', '#'.
    host = rest
    for sep in ("/", "?", "#"):
        idx = host.find(sep)
        if idx >= 0:
            host = host[:idx]
    # Strip any userinfo prefix (host is after the last '@'); we only keep the
    # host portion, never the userinfo (which could carry a secret).
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    host = host.lower().strip()
    if not host:
        return False, ""
    # Drop an explicit :port for the allowlist comparison.
    host_no_port = host.split(":", 1)[0]
    return host_no_port in _ALLOWED_BASE_URL_HOSTS, host_no_port


# ---------------------------------------------------------------------------
# 3. Config dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRealConfig:
    """The bounded, env-driven real-provider config (value-free for secrets).

    ``base_url`` and ``model`` are carried because they are non-secret config
    strings; the API-key value is NEVER carried — only ``api_key_source_detail``.
    """

    provider_mode: str
    api_enabled: bool
    provider_name: str
    base_url: str
    model: str
    timeout_seconds: int
    max_retries: int
    daily_budget_cents: int
    max_tokens: int
    per_minute_request_cap: int
    daily_request_cap: int
    daily_token_cap: int
    api_key_source_detail: str  # env_present | env_missing — never the value
    base_url_allowed: bool
    base_url_host: str  # host only, never secret-bearing query
    model_allowed: bool
    name_implemented: bool
    is_dev_home: bool

    def to_safe_dict(self) -> dict[str, Any]:
        """JSON-safe dict. Never includes an API-key value, token, or secret.

        The base URL is reduced to the allowlisted HOST only (never the full
        secret-bearing URL with any path query). The API key is reduced to the
        value-free ``env_present`` / ``env_missing`` marker.
        """
        return {
            "providerMode": self.provider_mode,
            "apiEnabled": self.api_enabled,
            "providerName": self.provider_name,
            "providerNameImplemented": self.name_implemented,
            "baseUrlHost": self.base_url_host if self.base_url_allowed else "",
            "baseUrlAllowed": self.base_url_allowed,
            "model": self.model if self.model_allowed else "",
            "modelAllowed": self.model_allowed,
            "timeoutSeconds": self.timeout_seconds,
            "maxRetries": self.max_retries,
            "dailyBudgetCents": self.daily_budget_cents,
            "maxTokens": self.max_tokens,
            "perMinuteRequestCap": self.per_minute_request_cap,
            "dailyRequestCap": self.daily_request_cap,
            "dailyTokenCap": self.daily_token_cap,
            "apiKeySource": "env",
            "apiKeyPresent": self.api_key_source_detail == "env_present",
            "apiKeySourceDetail": self.api_key_source_detail,
            "isDevHome": self.is_dev_home,
            "redactionApplied": True,
        }


def load_provider_real_config() -> ProviderRealConfig:
    """Load + clamp the bounded real-provider config from the environment.

    Real provider is **disabled by default**: ``HERMES_PROVIDER_API_ENABLED``
    defaults to off and ``HERMES_PROVIDER_MODE`` defaults to ``disabled``.
    """
    mode = _normalize_mode(_env_str("HERMES_PROVIDER_MODE", PROVIDER_MODE_DISABLED))
    api_enabled = _env_str("HERMES_PROVIDER_API_ENABLED", "0") == "1"
    name = _normalize_provider_name(_env_str("HERMES_PROVIDER_NAME", PROVIDER_NAME_OPENAI_COMPATIBLE))
    base_url = _env_str("HERMES_PROVIDER_BASE_URL", "")
    model = _env_str("HERMES_PROVIDER_MODEL", "")

    timeout_seconds = _env_int(
        "HERMES_PROVIDER_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS,
        _MIN_TIMEOUT_SECONDS, _MAX_TIMEOUT_SECONDS,
    )
    max_retries = _env_int(
        "HERMES_PROVIDER_MAX_RETRIES", _DEFAULT_MAX_RETRIES,
        _MIN_MAX_RETRIES, _MAX_MAX_RETRIES,
    )
    daily_budget_cents = _env_int(
        "HERMES_PROVIDER_DAILY_BUDGET_CENTS", _DEFAULT_DAILY_BUDGET_CENTS,
        _MIN_DAILY_BUDGET_CENTS, _MAX_DAILY_BUDGET_CENTS,
    )
    max_tokens = _env_int(
        "HERMES_PROVIDER_MAX_TOKENS", _DEFAULT_MAX_TOKENS,
        _MIN_MAX_TOKENS, _MAX_MAX_TOKENS,
    )

    base_url_allowed, base_url_host = _base_url_host_allowed(base_url)
    model_allowed = model in _ALLOWED_MODELS
    name_implemented = name in _IMPLEMENTED_PROVIDER_NAMES

    return ProviderRealConfig(
        provider_mode=mode,
        api_enabled=api_enabled,
        provider_name=name,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        daily_budget_cents=daily_budget_cents,
        max_tokens=max_tokens,
        per_minute_request_cap=_DEFAULT_PER_MINUTE_REQUEST_CAP,
        daily_request_cap=_DEFAULT_DAILY_REQUEST_CAP,
        daily_token_cap=_DEFAULT_DAILY_TOKEN_CAP,
        api_key_source_detail=_api_key_source_detail(),
        base_url_allowed=base_url_allowed,
        base_url_host=base_url_host,
        model_allowed=model_allowed,
        name_implemented=name_implemented,
        is_dev_home=_is_dev_home(),
    )


__all__ = [
    "ProviderRealConfig",
    "load_provider_real_config",
    "PROVIDER_MODE_DISABLED",
    "PROVIDER_MODE_FAKE",
    "PROVIDER_MODE_REAL",
    "PROVIDER_NAME_OPENAI_COMPATIBLE",
    "PROVIDER_NAME_ANTHROPIC_COMPATIBLE",
    "PROVIDER_NAME_ZAI_COMPATIBLE",
    "PROVIDER_NAME_OPENROUTER_COMPATIBLE",
    "_KNOWN_PROVIDER_NAMES",
    "_IMPLEMENTED_PROVIDER_NAMES",
    "_ALLOWED_BASE_URL_HOSTS",
    "_ALLOWED_MODELS",
    "_PRODUCTION_HERMES_HOME",
    "_PROVIDER_KEY_ENVS",
]
