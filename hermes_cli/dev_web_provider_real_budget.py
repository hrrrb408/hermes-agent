"""Phase 3B Real Provider Cost / Rate-limit / Budget Policy (Frozen).

Treats real-provider spend as a **first-class safety boundary**. Every request
is counted, every response is metered, a cost estimate is computed **before**
the call, and a hard daily budget cap blocks further spend once reached. Caps
are config-driven, bounded, and audited.

Counters live in the dev ``HERMES_HOME`` only (atomic, append-style rewrite),
are gitignored, and are never committed. They never carry an API key, token, or
secret. A corrupted counter file fails **closed** (the request is blocked)
until the operator resets it through an explicit dev-only action — never
automatically and never silently.

Phase: 3B — Real Provider Read-only Controlled Integration
Status: cost / rate-limit / budget policy implemented
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED = "blocked_provider_rate_limit_exceeded"
BLOCKED_PROVIDER_BUDGET_EXCEEDED = "blocked_provider_budget_exceeded"

_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_COUNTERS_DIR_RELATIVE = "gateway/dev/provider"
_COUNTERS_FILENAME = "usage-counters.json"

# Conservative price table (cents per 1K tokens). These are safe, rounded,
# slightly-conservative estimates — never an exact billing figure. Unknown
# models are blocked by the model allowlist before they reach here.
_MODEL_PRICE_CENTS_PER_1K: dict[str, tuple[float, float]] = {
    # (prompt per 1K, completion per 1K) in cents
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "glm-4-flash": (0.0, 0.0),
    "glm-4": (0.50, 0.50),
}
_DEFAULT_PRICE_CENTS_PER_1K: tuple[float, float] = (1.0, 4.0)


@dataclass
class ProviderUsageCounters:
    """Append-only counters for a single accounting window.

    ``window_minute`` and ``window_day`` are the UTC minute / day stamps the
    counters belong to; a read against a different stamp means the window reset.
    """

    window_minute: str
    window_day: str
    requests_this_minute: int = 0
    requests_today: int = 0
    tokens_today: int = 0
    cents_today: int = 0  # integer cents (conservative, rounded up)
    last_updated: str = ""

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "windowMinute": self.window_minute,
            "windowDay": self.window_day,
            "requestsThisMinute": self.requests_this_minute,
            "requestsToday": self.requests_today,
            "tokensToday": self.tokens_today,
            "centsToday": self.cents_today,
            "lastUpdated": self.last_updated,
        }


# ---------------------------------------------------------------------------
# 1. Cost estimate (before the call)
# ---------------------------------------------------------------------------


def estimate_cost_cents(
    *, model: str, prompt_tokens: int, completion_tokens: int,
) -> dict[str, Any]:
    """Compute a bounded, conservative cost estimate (integer cents).

    Rounded UP so the budget cap errs toward caution. Never a precise billing
    figure that could leak the spend pattern of a secret session.
    """
    price = _MODEL_PRICE_CENTS_PER_1K.get(model, _DEFAULT_PRICE_CENTS_PER_1K)
    import math

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
# 2. Counter file I/O (atomic, fail-closed)
# ---------------------------------------------------------------------------


def _window_stamps(now_iso: str) -> tuple[str, str]:
    """Derive (minute stamp, day stamp) from an ISO timestamp."""
    # Use the date/time portion only (never the env var value of anything).
    minute = now_iso[:16] if len(now_iso) >= 16 else now_iso  # YYYY-MM-DDTHH:MM
    day = now_iso[:10] if len(now_iso) >= 10 else now_iso  # YYYY-MM-DD
    return minute, day


def _resolve_counters_path(hermes_home: str | None) -> tuple[Path, str | None]:
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

    counters_path = home / _COUNTERS_DIR_RELATIVE / _COUNTERS_FILENAME
    try:
        counters_path.resolve().relative_to(home)
    except ValueError:
        return Path(), "OUTSIDE_HERMES_HOME"
    if str(counters_path.resolve()).endswith("state.db"):
        return Path(), "STATE_DB"
    return counters_path, None


def read_usage_counters(
    *, hermes_home: str | None, now_iso: str,
) -> ProviderUsageCounters | None:
    """Read the counters for the current window.

    Returns fresh zero counters if the file is missing. Returns ``None`` if the
    file is corrupt or outside the dev home — the caller MUST fail closed
    (block the request).
    """
    minute, day = _window_stamps(now_iso)
    path, err = _resolve_counters_path(hermes_home)
    if err is not None:
        return None
    if not path.exists():
        return ProviderUsageCounters(window_minute=minute, window_day=day)

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return None  # corruption → fail closed

    if not isinstance(data, dict):
        return None

    def _get_int(key: str) -> int | None:
        val = data.get(key)
        if isinstance(val, bool) or not isinstance(val, int):
            return None
        return val

    fields = {
        "requests_this_minute": _get_int("requestsThisMinute"),
        "requests_today": _get_int("requestsToday"),
        "tokens_today": _get_int("tokensToday"),
        "cents_today": _get_int("centsToday"),
    }
    if any(v is None for v in fields.values()):
        return None  # malformed → fail closed

    stored_day = data.get("windowDay")
    stored_minute = data.get("windowMinute")
    # Window reset: if the stored window no longer matches, zero the counters
    # for the expired axis (never back-date / pre-date).
    same_minute = isinstance(stored_minute, str) and stored_minute == minute
    same_day = isinstance(stored_day, str) and stored_day == day
    counters = ProviderUsageCounters(
        window_minute=minute,
        window_day=day,
        requests_this_minute=fields["requests_this_minute"] if same_minute else 0,  # type: ignore[assignment]
        requests_today=fields["requests_today"] if same_day else 0,  # type: ignore[assignment]
        tokens_today=fields["tokens_today"] if same_day else 0,  # type: ignore[assignment]
        cents_today=fields["cents_today"] if same_day else 0,  # type: ignore[assignment]
        last_updated=str(data.get("lastUpdated", "")),
    )
    return counters


def _write_counters_atomic(path: Path, counters: ProviderUsageCounters) -> bool:
    """Atomic rewrite (temp + rename). Best-effort; failure → False."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(counters.to_safe_dict(), ensure_ascii=False)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".usage-counters.", suffix=".tmp",
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


def meter_usage(
    *, hermes_home: str | None, now_iso: str,
    prompt_tokens: int, completion_tokens: int, cost_cents: int,
) -> bool:
    """Atomically meter a completed call into the counters. Returns success.

    On any I/O / corruption failure returns ``False`` — the caller must NOT
    treat a failed meter as success (the request already happened, but the
    counters reflect the pre-call state, which is the conservative direction).
    """
    counters = read_usage_counters(hermes_home=hermes_home, now_iso=now_iso)
    if counters is None:
        return False
    path, err = _resolve_counters_path(hermes_home)
    if err is not None:
        return False
    counters.requests_this_minute += 1
    counters.requests_today += 1
    counters.tokens_today += max(0, int(prompt_tokens)) + max(0, int(completion_tokens))
    counters.cents_today += max(0, int(cost_cents))
    counters.last_updated = now_iso
    return _write_counters_atomic(path, counters)


def record_request_attempt(*, hermes_home: str | None, now_iso: str) -> bool:
    """Count a request ATTEMPT (before the call) for the rate-limit window.

    Used so a burst of concurrent attempts cannot slip past the per-minute cap.
    """
    counters = read_usage_counters(hermes_home=hermes_home, now_iso=now_iso)
    if counters is None:
        return False
    path, err = _resolve_counters_path(hermes_home)
    if err is not None:
        return False
    counters.requests_this_minute += 1
    counters.requests_today += 1
    counters.last_updated = now_iso
    return _write_counters_atomic(path, counters)


# ---------------------------------------------------------------------------
# 3. Rate / budget evaluation (before the call)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RateBudgetDecision:
    allowed: bool
    blocked_reason: str | None
    counters: ProviderUsageCounters | None
    cost_estimate: Mapping[str, Any] | None = field(default=None)


def evaluate_rate_and_budget(
    *,
    config,
    now_iso: str,
    hermes_home: str | None,
    estimated_prompt_tokens: int,
    estimated_completion_tokens: int,
) -> RateBudgetDecision:
    """Evaluate every rate-limit + budget cap BEFORE any network call.

    Caps are defensive: when a counter cannot be read/written safely, the
    request is blocked (fail-closed), never allowed.
    """
    counters = read_usage_counters(hermes_home=hermes_home, now_iso=now_iso)
    if counters is None:
        # Corruption / outside home → fail closed.
        return RateBudgetDecision(
            allowed=False, blocked_reason=BLOCKED_PROVIDER_BUDGET_EXCEEDED,
            counters=None, cost_estimate=None,
        )

    cost = estimate_cost_cents(
        model=config.model,
        prompt_tokens=estimated_prompt_tokens,
        completion_tokens=estimated_completion_tokens,
    )

    if counters.requests_this_minute >= config.per_minute_request_cap:
        return RateBudgetDecision(
            allowed=False, blocked_reason=BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED,
            counters=counters, cost_estimate=cost,
        )
    if counters.requests_today >= config.daily_request_cap:
        return RateBudgetDecision(
            allowed=False, blocked_reason=BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED,
            counters=counters, cost_estimate=cost,
        )
    if counters.tokens_today + estimated_prompt_tokens + estimated_completion_tokens > config.daily_token_cap:
        return RateBudgetDecision(
            allowed=False, blocked_reason=BLOCKED_PROVIDER_BUDGET_EXCEEDED,
            counters=counters, cost_estimate=cost,
        )
    if counters.cents_today + int(cost["estimateCents"]) > config.daily_budget_cents:
        return RateBudgetDecision(
            allowed=False, blocked_reason=BLOCKED_PROVIDER_BUDGET_EXCEEDED,
            counters=counters, cost_estimate=cost,
        )

    return RateBudgetDecision(
        allowed=True, blocked_reason=None, counters=counters, cost_estimate=cost,
    )


def usage_badge(*, config, counters: ProviderUsageCounters | None) -> dict[str, Any]:
    """Safe, value-free budget badge for the UI.

    Shows caps + remaining (rounded, conservative) + model name only — never an
    API key, header, raw response, or precise spend that could leak a pattern.
    """
    if counters is None:
        return {
            "available": False,
            "modelName": config.model if config.model_allowed else "",
            "dailyBudgetCents": config.daily_budget_cents,
        }
    remaining_cents = max(0, config.daily_budget_cents - counters.cents_today)
    return {
        "available": True,
        "modelName": config.model if config.model_allowed else "",
        "dailyBudgetCents": config.daily_budget_cents,
        "remainingCents": remaining_cents,
        "requestsToday": counters.requests_today,
        "dailyRequestCap": config.daily_request_cap,
        "remainingRequests": max(0, config.daily_request_cap - counters.requests_today),
        "perMinuteRequestCap": config.per_minute_request_cap,
        "windowDay": counters.window_day,
        "redactionApplied": True,
    }


__all__ = [
    "ProviderUsageCounters",
    "RateBudgetDecision",
    "BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED",
    "BLOCKED_PROVIDER_BUDGET_EXCEEDED",
    "estimate_cost_cents",
    "read_usage_counters",
    "meter_usage",
    "record_request_attempt",
    "evaluate_rate_and_budget",
    "usage_badge",
]
