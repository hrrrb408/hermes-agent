"""Phase 3B-Live-Enablement — Live Provider Budget / Rate-limit Policy (Frozen).

Every live request is cost-bounded, rate-bounded, token-bounded, and
time-bounded. The first live slice caps at **one** request, **≤ 1000** total
tokens (**≤ 200** output), **≤ 5** cents, **0** retries, **60 s** runtime.
Counters are atomic and fail-closed: if a counter cannot be read or written,
the request is blocked.

Counters live under the dev ``HERMES_HOME`` only (atomic JSON rewrite),
never under ``~/.hermes``, never touch ``state.db``, never carry a key, and
are never committed. A corrupted counter file fails **closed** (the request
is blocked) until the operator resets it through an explicit dev-only action.

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live budget / rate-limit policy implemented
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# 1. Frozen first-live caps
# ---------------------------------------------------------------------------

MAX_REQUESTS = 1
MAX_TOTAL_TOKENS = 1000
MAX_INPUT_TOKENS = 800
MAX_OUTPUT_TOKENS = 200
MAX_BUDGET_CENTS = 5
MAX_RUNTIME_SECONDS = 60
MAX_RETRIES = 0  # no retry for the first live test
RATE_LIMIT_WINDOW_SECONDS = 60

# Conservative price table (cents per 1K tokens) for the cost estimate. These
# are safe, rounded, slightly-conservative estimates — never an exact billing
# figure. Unknown models are blocked by the model allowlist before they reach.
_MODEL_PRICE_CENTS_PER_1K: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}
_DEFAULT_PRICE_CENTS_PER_1K: tuple[float, float] = (1.0, 4.0)

_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_STORE_DIR_RELATIVE = "gateway/dev/provider-live-budget"
_STORE_FILENAME = "counters.json"

# ---------------------------------------------------------------------------
# 2. Frozen blocked-reason catalogue (budget layer)
# ---------------------------------------------------------------------------

BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED = "blocked_live_provider_budget_not_configured"
BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED = "blocked_live_provider_budget_exceeded"
BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED = "blocked_live_provider_request_cap_exceeded"
BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED = "blocked_live_provider_token_cap_exceeded"
BLOCKED_LIVE_PROVIDER_RETRY_NOT_ALLOWED = "blocked_live_provider_retry_not_allowed"
BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE = "blocked_live_provider_counter_unavailable"


@dataclass(frozen=True, slots=True)
class LiveBudgetCaps:
    """The frozen first-live caps."""

    max_requests: int = MAX_REQUESTS
    max_total_tokens: int = MAX_TOTAL_TOKENS
    max_input_tokens: int = MAX_INPUT_TOKENS
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    max_budget_cents: int = MAX_BUDGET_CENTS
    max_runtime_seconds: int = MAX_RUNTIME_SECONDS
    max_retries: int = MAX_RETRIES
    rate_limit_window_seconds: int = RATE_LIMIT_WINDOW_SECONDS

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "maxRequests": self.max_requests,
            "maxTotalTokens": self.max_total_tokens,
            "maxInputTokens": self.max_input_tokens,
            "maxOutputTokens": self.max_output_tokens,
            "maxBudgetCents": self.max_budget_cents,
            "maxRuntimeSeconds": self.max_runtime_seconds,
            "maxRetries": self.max_retries,
            "rateLimitWindow": self.rate_limit_window_seconds,
            "failClosedOnCounterError": True,
            "redactionApplied": True,
        }


@dataclass
class LiveBudgetCounters:
    """Live-window counters (atomic, fail-closed)."""

    window_minute: str
    requests_this_window: int = 0
    tokens_this_window: int = 0
    cents_this_window: int = 0
    last_updated: str = ""

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "windowMinute": self.window_minute,
            "requestsThisWindow": self.requests_this_window,
            "tokensThisWindow": self.tokens_this_window,
            "centsThisWindow": self.cents_this_window,
            "lastUpdated": self.last_updated,
        }


@dataclass(frozen=True, slots=True)
class LiveBudgetDecision:
    allowed: bool
    blocked_reason: str | None
    counters: LiveBudgetCounters | None
    cost_estimate: Mapping[str, Any] | None = field(default=None)
    spent_estimate: int = 0
    remaining_estimate: int = 0


# ---------------------------------------------------------------------------
# 3. Cost estimate (before the call; derived from token counts only)
# ---------------------------------------------------------------------------


def estimate_live_cost_cents(
    *, model: str, prompt_tokens: int, completion_tokens: int,
) -> dict[str, Any]:
    """Compute a bounded, conservative cost estimate (integer cents, rounded up)."""
    price = _MODEL_PRICE_CENTS_PER_1K.get(model, _DEFAULT_PRICE_CENTS_PER_1K)
    prompt = max(0, int(prompt_tokens))
    completion = max(0, int(completion_tokens))
    raw = (prompt * price[0] + completion * price[1]) / 1000.0
    cents = int(math.ceil(raw))
    return {
        "model": model,
        "promptTokens": prompt,
        "completionTokens": completion,
        "estimateCents": cents,
        "roundedUp": True,
    }


# ---------------------------------------------------------------------------
# 4. Counter file I/O (atomic, fail-closed)
# ---------------------------------------------------------------------------


def _window_minute(now_iso: str) -> str:
    return now_iso[:16] if len(now_iso) >= 16 else now_iso


def _resolve_store_path(hermes_home: str | None) -> tuple[Path, str | None]:
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), "HERMES_HOME_MISSING"
        home = Path(home_str).resolve()
    prod = Path(_PRODUCTION_HERMES_HOME).resolve()
    if home == prod:
        return Path(), "PRODUCTION_HOME"
    store_path = home / _STORE_DIR_RELATIVE / _STORE_FILENAME
    try:
        store_path.resolve().relative_to(home)
    except ValueError:
        return Path(), "OUTSIDE_HERMES_HOME"
    if str(store_path.resolve()).endswith("state.db"):
        return Path(), "STATE_DB"
    return store_path, None


def read_live_counters(
    *, hermes_home: str | None, now_iso: str,
) -> LiveBudgetCounters | None:
    """Read the live counters for the current window.

    Fresh zero counters if the file is missing. ``None`` if corrupt / outside
    home → the caller MUST fail closed.
    """
    minute = _window_minute(now_iso)
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return None
    if not path.exists():
        return LiveBudgetCounters(window_minute=minute)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None

    def _get_int(key: str) -> int | None:
        val = data.get(key)
        if isinstance(val, bool) or not isinstance(val, int):
            return None
        return val

    fields = {
        "requests_this_window": _get_int("requestsThisWindow"),
        "tokens_this_window": _get_int("tokensThisWindow"),
        "cents_this_window": _get_int("centsThisWindow"),
    }
    if any(v is None for v in fields.values()):
        return None
    stored_minute = data.get("windowMinute")
    same = isinstance(stored_minute, str) and stored_minute == minute
    return LiveBudgetCounters(
        window_minute=minute,
        requests_this_window=fields["requests_this_window"] if same else 0,  # type: ignore[assignment]
        tokens_this_window=fields["tokens_this_window"] if same else 0,  # type: ignore[assignment]
        cents_this_window=fields["cents_this_window"] if same else 0,  # type: ignore[assignment]
        last_updated=str(data.get("lastUpdated", "")),
    )


def _write_counters_atomic(path: Path, counters: LiveBudgetCounters) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(counters.to_safe_dict(), ensure_ascii=False)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".live-counters.", suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_name, path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            return False
        return True
    except OSError:
        return False


def record_live_attempt(*, hermes_home: str | None, now_iso: str) -> bool:
    """Count a request ATTEMPT (before the call) for the rate window."""
    counters = read_live_counters(hermes_home=hermes_home, now_iso=now_iso)
    if counters is None:
        return False
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return False
    counters.requests_this_window += 1
    counters.last_updated = now_iso
    return _write_counters_atomic(path, counters)


def meter_live_usage(
    *,
    hermes_home: str | None,
    now_iso: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_cents: int,
) -> bool:
    """Meter a completed live call into the counters (atomic). Returns success."""
    counters = read_live_counters(hermes_home=hermes_home, now_iso=now_iso)
    if counters is None:
        return False
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return False
    counters.tokens_this_window += max(0, int(prompt_tokens)) + max(0, int(completion_tokens))
    counters.cents_this_window += max(0, int(cost_cents))
    counters.last_updated = now_iso
    return _write_counters_atomic(path, counters)


def reset_live_counters(*, hermes_home: str | None, now_iso: str) -> bool:
    """Reset the live counters (disable / rollback procedure). Dev-only."""
    counters = LiveBudgetCounters(window_minute=_window_minute(now_iso))
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return False
    return _write_counters_atomic(path, counters)


# ---------------------------------------------------------------------------
# 5. Rate / budget evaluation (before the call)
# ---------------------------------------------------------------------------


def evaluate_live_budget(
    *,
    caps: LiveBudgetCaps | None,
    model: str,
    hermes_home: str | None,
    now_iso: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
) -> LiveBudgetDecision:
    """Evaluate every live cap BEFORE any network call. Fail-closed.

    A missing cap set, a corrupt counter, an exceeded request / token / budget
    cap, or a non-zero retry all fail closed with a precise reason.
    """
    if caps is None:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED,
            counters=None,
        )
    if caps.max_retries != MAX_RETRIES:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_RETRY_NOT_ALLOWED,
            counters=None,
        )

    counters = read_live_counters(hermes_home=hermes_home, now_iso=now_iso)
    if counters is None:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE,
            counters=None,
        )

    cost = estimate_live_cost_cents(
        model=model,
        prompt_tokens=estimated_input_tokens,
        completion_tokens=estimated_output_tokens,
    )
    est_total = max(0, int(estimated_input_tokens)) + max(0, int(estimated_output_tokens))

    if counters.requests_this_window >= caps.max_requests:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED,
            counters=counters,
            cost_estimate=cost,
        )
    if est_total > caps.max_total_tokens:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED,
            counters=counters,
            cost_estimate=cost,
        )
    if max(0, int(estimated_output_tokens)) > caps.max_output_tokens:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED,
            counters=counters,
            cost_estimate=cost,
        )
    if counters.tokens_this_window + est_total > caps.max_total_tokens:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED,
            counters=counters,
            cost_estimate=cost,
        )
    if counters.cents_this_window + int(cost["estimateCents"]) > caps.max_budget_cents:
        return LiveBudgetDecision(
            allowed=False,
            blocked_reason=BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED,
            counters=counters,
            cost_estimate=cost,
        )

    return LiveBudgetDecision(
        allowed=True,
        blocked_reason=None,
        counters=counters,
        cost_estimate=cost,
        spent_estimate=counters.cents_this_window,
        remaining_estimate=max(0, caps.max_budget_cents - counters.cents_this_window),
    )


def live_budget_badge(
    *, caps: LiveBudgetCaps, counters: LiveBudgetCounters | None,
) -> dict[str, Any]:
    """Safe, value-free budget badge for the UI."""
    if counters is None:
        return {
            "available": False,
            **caps.to_safe_dict(),
        }
    return {
        "available": True,
        **caps.to_safe_dict(),
        "requestsUsed": counters.requests_this_window,
        "tokensUsed": counters.tokens_this_window,
        "centsUsed": counters.cents_this_window,
        "remainingCents": max(0, caps.max_budget_cents - counters.cents_this_window),
        "remainingRequests": max(0, caps.max_requests - counters.requests_this_window),
        "windowMinute": counters.window_minute,
    }


__all__ = [
    "MAX_REQUESTS",
    "MAX_TOTAL_TOKENS",
    "MAX_INPUT_TOKENS",
    "MAX_OUTPUT_TOKENS",
    "MAX_BUDGET_CENTS",
    "MAX_RUNTIME_SECONDS",
    "MAX_RETRIES",
    "RATE_LIMIT_WINDOW_SECONDS",
    "LiveBudgetCaps",
    "LiveBudgetCounters",
    "LiveBudgetDecision",
    "BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED",
    "BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED",
    "BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED",
    "BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED",
    "BLOCKED_LIVE_PROVIDER_RETRY_NOT_ALLOWED",
    "BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE",
    "estimate_live_cost_cents",
    "read_live_counters",
    "record_live_attempt",
    "meter_live_usage",
    "reset_live_counters",
    "evaluate_live_budget",
    "live_budget_badge",
]
