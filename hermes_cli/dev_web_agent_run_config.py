"""Dev Web API Agent Run Configuration.

Kill switch, concurrency limits, rate limits, timeouts, and event buffer
settings for Phase 1F Agent Dev-Only Run / SSE.

This module contains ONLY pure computation and configuration. It does NOT
initialize providers, create threads, or perform any I/O.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ── Kill switch ──

_ENV_VAR = "HERMES_AGENT_RUN_ENABLED"
_ENABLE_VALUES = frozenset({"true", "1", "yes", "on"})
_DISABLE_VALUES = frozenset({"false", "0", "no", "off", ""})


def is_agent_run_enabled() -> bool:
    """Check if Agent Run capability is enabled via kill switch.

    Environment variable: HERMES_AGENT_RUN_ENABLED

    Default: DISABLED (unset or empty = disabled).
    Fail-closed: any value not in the explicit enable list is treated as disabled.

    Returns:
        True only if the env var is set to an explicit enable value.
    """
    raw = os.environ.get(_ENV_VAR, "").strip().lower()
    return raw in _ENABLE_VALUES


# ── Environment guard ──

ALLOWED_SOURCE_ROOT = Path("/Users/huangruibang/Code/hermes-agent-dev").resolve()
ALLOWED_HERMES_HOME = Path("/Users/huangruibang/Code/hermes-home-dev").resolve()
_PRODUCTION_HERMES_HOME = Path("/Users/huangruibang/.hermes")


def enforce_agent_run_dev_environment(
    hermes_home: Path,
    source_root: Path,
) -> None:
    """Verify the environment is safe for Agent Run operations.

    Must be called BEFORE any provider initialization, thread creation,
    session writes, or audit writes.

    Raises RuntimeError if:
    - Source root does not match the expected dev source root
    - HERMES_HOME does not match the expected dev home
    - HERMES_HOME resolves to the production home
    - HERMES_HOME is inside the production home
    """
    resolved_home = hermes_home.resolve()
    resolved_root = source_root.resolve()

    if resolved_root != ALLOWED_SOURCE_ROOT:
        raise RuntimeError(
            f"Agent Run: source root must be {ALLOWED_SOURCE_ROOT}, "
            f"got {resolved_root}"
        )

    if resolved_home != ALLOWED_HERMES_HOME:
        raise RuntimeError(
            f"Agent Run: HERMES_HOME must be {ALLOWED_HERMES_HOME}, "
            f"got {resolved_home}"
        )

    # Symlink / production check
    try:
        prod_resolved = _PRODUCTION_HERMES_HOME.resolve()
    except Exception:
        prod_resolved = _PRODUCTION_HERMES_HOME

    if resolved_home == prod_resolved:
        raise RuntimeError(
            "Agent Run: production home is not allowed."
        )

    try:
        resolved_home.relative_to(prod_resolved)
    except ValueError:
        pass  # Not inside production — good
    else:
        raise RuntimeError(
            "Agent Run: HERMES_HOME inside production home is not allowed."
        )


# ── Run configuration (frozen) ──


@dataclass(frozen=True)
class AgentRunConfig:
    """Immutable configuration for Agent Run behavior.

    All values are frozen at import / construction time.
    """

    # Concurrency
    global_max_active_runs: int = 1
    per_session_max_active_runs: int = 1

    # Timeouts (seconds)
    overall_run_timeout: float = 120.0
    provider_timeout_max: float = 90.0
    cancel_wait_timeout: float = 10.0

    # Retry
    max_retries: int = 2

    # Rate limits
    rate_limit_per_minute: int = 3
    rate_limit_per_hour: int = 20

    # Event buffer
    event_buffer_max_events: int = 500
    event_buffer_max_bytes: int = 1024 * 1024  # 1 MiB

    # Retention
    completed_run_ttl_seconds: float = 600.0  # 10 minutes

    # Heartbeat
    heartbeat_interval_seconds: float = 15.0

    # Disconnect grace
    disconnect_grace_seconds: float = 15.0

    # Output limits
    max_output_tokens: int = 4096

    # Temperature range
    temperature_min: float = 0.0
    temperature_max: float = 2.0

    # Message limits
    max_message_length: int = 4000

    # Preview receipt TTL
    preview_receipt_ttl_seconds: float = 300.0  # 5 minutes


# Module-level singleton
AGENT_RUN_CONFIG = AgentRunConfig()
