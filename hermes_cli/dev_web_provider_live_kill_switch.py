"""Phase 3B-Live-Enablement — Live Provider Kill Switch (Frozen).

A live provider session must be killable instantly and must return the boundary
to its disabled-by-default state. The kill switch is **inactive by default**;
when active it blocks all live requests, blocks the secret read, blocks the
network call, writes a redacted audit entry, and requires a **fresh** approval
to re-enable (clearing the kill switch is not itself an approval).

The store lives under the dev ``HERMES_HOME`` only (atomic JSON), never under
``~/.hermes``, never touches ``state.db``, never carries a key, and is never
committed.

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live kill switch implemented (inactive by default)
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 1. Frozen constants
# ---------------------------------------------------------------------------

_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_STORE_DIR_RELATIVE = "gateway/dev/provider-live-kill-switch"
_STORE_FILENAME = "kill-switch.json"

BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE = "blocked_live_provider_kill_switch_active"

# Frozen kill-switch trigger reasons. The kill switch fires on ANY of these.
KILL_SWITCH_TRIGGER_MANUAL = "manual_operator_trigger"
KILL_SWITCH_TRIGGER_BUDGET_EXCEEDED = "budget_exceeded"
KILL_SWITCH_TRIGGER_RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
KILL_SWITCH_TRIGGER_SECRET_DETECTED = "secret_detected"
KILL_SWITCH_TRIGGER_RESPONSE_TOO_LARGE = "response_too_large"
KILL_SWITCH_TRIGGER_MALFORMED_RESPONSE = "malformed_unsafe_response"
KILL_SWITCH_TRIGGER_OFF_ALLOWLIST_REDIRECT = "off_allowlist_redirect"
KILL_SWITCH_TRIGGER_ROUTE_GOVERNANCE_DRIFT = "route_governance_drift"
KILL_SWITCH_TRIGGER_PRODUCTION_GATEWAY_PID_DRIFT = "production_gateway_pid_drift"
KILL_SWITCH_TRIGGER_AUDIT_WRITE_FAILURE = "audit_write_failure"
KILL_SWITCH_TRIGGER_UNEXPECTED_TOOL_CALL = "unexpected_provider_tool_call"
KILL_SWITCH_TRIGGER_PROVIDER_WRITE_SUGGESTION = "provider_write_autonomous_suggestion"
KILL_SWITCH_TRIGGER_SMOKE_FAILURE = "smoke_failure"
KILL_SWITCH_TRIGGER_MANUAL_ABORT = "manual_abort"

KILL_SWITCH_TRIGGERS: frozenset[str] = frozenset(
    {
        KILL_SWITCH_TRIGGER_MANUAL,
        KILL_SWITCH_TRIGGER_BUDGET_EXCEEDED,
        KILL_SWITCH_TRIGGER_RATE_LIMIT_EXCEEDED,
        KILL_SWITCH_TRIGGER_SECRET_DETECTED,
        KILL_SWITCH_TRIGGER_RESPONSE_TOO_LARGE,
        KILL_SWITCH_TRIGGER_MALFORMED_RESPONSE,
        KILL_SWITCH_TRIGGER_OFF_ALLOWLIST_REDIRECT,
        KILL_SWITCH_TRIGGER_ROUTE_GOVERNANCE_DRIFT,
        KILL_SWITCH_TRIGGER_PRODUCTION_GATEWAY_PID_DRIFT,
        KILL_SWITCH_TRIGGER_AUDIT_WRITE_FAILURE,
        KILL_SWITCH_TRIGGER_UNEXPECTED_TOOL_CALL,
        KILL_SWITCH_TRIGGER_PROVIDER_WRITE_SUGGESTION,
        KILL_SWITCH_TRIGGER_SMOKE_FAILURE,
        KILL_SWITCH_TRIGGER_MANUAL_ABORT,
    }
)


@dataclass(frozen=True, slots=True)
class KillSwitchState:
    """The kill switch state (value-free)."""

    active: bool
    triggered_by: str  # a KILL_SWITCH_TRIGGER_* reason, or "" when inactive
    triggered_at: str  # ISO timestamp, or "" when inactive

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "triggeredBy": self.triggered_by,
            "triggeredAt": self.triggered_at,
            "redactionApplied": True,
        }


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


def _write_atomic(path: Path, state: KillSwitchState) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(state.to_safe_dict(), ensure_ascii=False)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".kill-switch.", suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
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


def read_kill_switch(*, hermes_home: str | None) -> KillSwitchState:
    """Read the kill switch state. Defaults to inactive (fail OPEN on read).

    A corrupt / missing store means the switch is inactive (the live path is
    still gated by the approval + budget + network + secret layers). Triggering
    uses a separate fail-closed write.
    """
    path, err = _resolve_store_path(hermes_home)
    if err is not None or not path.exists():
        return KillSwitchState(active=False, triggered_by="", triggered_at="")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return KillSwitchState(active=False, triggered_by="", triggered_at="")
    if not isinstance(data, dict):
        return KillSwitchState(active=False, triggered_by="", triggered_at="")
    active = bool(data.get("active", False))
    triggered_by = str(data.get("triggeredBy", ""))
    if active and triggered_by not in KILL_SWITCH_TRIGGERS:
        triggered_by = KILL_SWITCH_TRIGGER_MANUAL
    triggered_at = str(data.get("triggeredAt", ""))
    if not active:
        triggered_by = ""
        triggered_at = ""
    return KillSwitchState(
        active=active, triggered_by=triggered_by, triggered_at=triggered_at,
    )


def trigger_kill_switch(
    *, hermes_home: str | None, reason: str, now_iso: str,
) -> bool:
    """Arm the kill switch. Returns whether the write succeeded.

    An unknown reason is normalized to ``manual_operator_trigger``.
    """
    normalized = reason if reason in KILL_SWITCH_TRIGGERS else KILL_SWITCH_TRIGGER_MANUAL
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return False
    return _write_atomic(
        path, KillSwitchState(active=True, triggered_by=normalized, triggered_at=now_iso),
    )


def clear_kill_switch(*, hermes_home: str | None) -> bool:
    """Disarm the kill switch (disable / rollback procedure).

    Clearing the switch is **not** an approval: re-enabling a live request still
    requires a fresh human approval.
    """
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return False
    return _write_atomic(
        path, KillSwitchState(active=False, triggered_by="", triggered_at=""),
    )


def is_kill_switch_active(*, hermes_home: str | None) -> bool:
    return read_kill_switch(hermes_home=hermes_home).active


__all__ = [
    "BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE",
    "KILL_SWITCH_TRIGGERS",
    "KILL_SWITCH_TRIGGER_MANUAL",
    "KILL_SWITCH_TRIGGER_BUDGET_EXCEEDED",
    "KILL_SWITCH_TRIGGER_RATE_LIMIT_EXCEEDED",
    "KILL_SWITCH_TRIGGER_SECRET_DETECTED",
    "KILL_SWITCH_TRIGGER_RESPONSE_TOO_LARGE",
    "KILL_SWITCH_TRIGGER_MALFORMED_RESPONSE",
    "KILL_SWITCH_TRIGGER_OFF_ALLOWLIST_REDIRECT",
    "KILL_SWITCH_TRIGGER_ROUTE_GOVERNANCE_DRIFT",
    "KILL_SWITCH_TRIGGER_PRODUCTION_GATEWAY_PID_DRIFT",
    "KILL_SWITCH_TRIGGER_AUDIT_WRITE_FAILURE",
    "KILL_SWITCH_TRIGGER_UNEXPECTED_TOOL_CALL",
    "KILL_SWITCH_TRIGGER_PROVIDER_WRITE_SUGGESTION",
    "KILL_SWITCH_TRIGGER_SMOKE_FAILURE",
    "KILL_SWITCH_TRIGGER_MANUAL_ABORT",
    "KillSwitchState",
    "read_kill_switch",
    "trigger_kill_switch",
    "clear_kill_switch",
    "is_kill_switch_active",
]
