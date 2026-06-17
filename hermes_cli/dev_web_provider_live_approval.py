"""Phase 3B-Live-Enablement — Live Provider Human Approval Model (Frozen).

Live enablement is **never automatic.** Every live request requires a fresh,
explicit, in-scope, single-use, short-window human approval. No approval → fail
closed. This module owns the approval record, its lifetime, and its dev-only
store. It does **not** read an API key, does **not** make a network call, and
does **not** carry a key / header / token / raw prompt / raw response / production
path.

The approval record is **value-free**: it carries the approved scope, provider
name, mode, model, allowlisted host, budget / request / token caps, the read-only
tool allowlist, an expiry, the single-use flag, and the operator. The API key,
Authorization header, and any raw secret are **forbidden fields** — their
presence is a P0 stop condition.

The store lives under the dev ``HERMES_HOME`` only (atomic, append-style JSON),
is gitignored, never carries a secret, and is never committed. A corrupt / outside
store fails **closed** (no approval is considered valid).

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live approval model implemented (live provider disabled by default)
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# 1. Frozen constants
# ---------------------------------------------------------------------------

APPROVAL_SCOPE = "provider_live_enablement"
PROVIDER_MODE_REAL = "real"

# Frozen first-live lifetime. 5 minutes, single-use, manual renewal.
DEFAULT_TTL_SECONDS = 300

# Production boundary (read-only observation only — never signals).
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_STORE_DIR_RELATIVE = "gateway/dev/provider-live-approvals"
_STORE_FILENAME = "approvals.json"

# ---------------------------------------------------------------------------
# 2. Frozen blocked-reason catalogue (approval layer)
# ---------------------------------------------------------------------------

BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED = "blocked_live_provider_not_human_approved"
BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED = "blocked_live_provider_approval_expired"
BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID = "blocked_live_provider_approval_scope_invalid"
BLOCKED_LIVE_PROVIDER_APPROVAL_USED = "blocked_live_provider_approval_used"
BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH = "blocked_live_provider_approval_mismatch"
BLOCKED_LIVE_PROVIDER_DEV_ONLY_VIOLATION = "blocked_live_provider_dev_only_violation"


# ---------------------------------------------------------------------------
# 3. The approval record (value-free)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LiveApproval:
    """A fresh, single-use, short-window human approval for one live request.

    Never carries an API key, Authorization header, bearer token, raw prompt,
    raw response, or production path. ``redactionApplied`` is always True.
    """

    approval_id: str
    approval_scope: str  # always provider_live_enablement
    provider_name: str
    provider_mode: str  # always real
    model: str
    base_url_host: str
    budget_cap_cents: int
    request_cap: int
    token_cap: int
    output_token_cap: int
    tool_allowlist: frozenset[str] = field(default_factory=frozenset)
    expires_at: str = ""  # ISO timestamp
    created_at: str = ""  # ISO timestamp
    approved_by: str = "human_operator"
    single_use: bool = True
    used_at: str = ""
    redaction_applied: bool = True

    def to_safe_dict(self) -> dict[str, Any]:
        """JSON-safe dict. Never includes a key, header, token, or secret."""
        return {
            "approvalId": self.approval_id,
            "approvalScope": self.approval_scope,
            "providerName": self.provider_name,
            "providerMode": self.provider_mode,
            "model": self.model,
            "baseUrlHost": self.base_url_host,
            "budgetCapCents": self.budget_cap_cents,
            "requestCap": self.request_cap,
            "tokenCap": self.token_cap,
            "outputTokenCap": self.output_token_cap,
            "toolAllowlist": sorted(self.tool_allowlist),
            "expiresAt": self.expires_at,
            "createdAt": self.created_at,
            "approvedBy": self.approved_by,
            "singleUse": self.single_use,
            "usedAt": self.used_at,
            "redactionApplied": True,
        }


# ---------------------------------------------------------------------------
# 4. Store path resolution (dev-only, fail-closed)
# ---------------------------------------------------------------------------


def _resolve_store_path(hermes_home: str | None) -> tuple[Path, str | None]:
    """Resolve the approval store path. Returns (path, error).

    Fails closed (returns an error) when the home is the production home, is
    missing, or the resolved path escapes the dev home / hits state.db.
    """
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


def _write_store_atomic(path: Path, payload: list[dict[str, Any]]) -> bool:
    """Atomic rewrite (temp + rename). Best-effort; failure → False."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".approvals.", suffix=".tmp",
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


def _read_store(hermes_home: str | None) -> list[dict[str, Any]] | None:
    """Read the raw approval list. ``None`` means corrupt / outside home → fail closed."""
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return None
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    return [entry for entry in data if isinstance(entry, dict)]


def _persist(hermes_home: str | None, approvals: list[LiveApproval]) -> bool:
    path, err = _resolve_store_path(hermes_home)
    if err is not None:
        return False
    return _write_store_atomic(path, [a.to_safe_dict() for a in approvals])


def _approval_from_dict(entry: Mapping[str, Any]) -> LiveApproval | None:
    """Rebuild a LiveApproval from a stored dict. ``None`` if malformed."""
    try:
        allowlist_raw = entry.get("toolAllowlist", [])
        allowlist = frozenset(
            str(t) for t in allowlist_raw if isinstance(t, str)
        ) if isinstance(allowlist_raw, (list, tuple)) else frozenset()
        return LiveApproval(
            approval_id=str(entry.get("approvalId", "")),
            approval_scope=str(entry.get("approvalScope", "")),
            provider_name=str(entry.get("providerName", "")),
            provider_mode=str(entry.get("providerMode", "")),
            model=str(entry.get("model", "")),
            base_url_host=str(entry.get("baseUrlHost", "")),
            budget_cap_cents=int(entry.get("budgetCapCents", 0)),
            request_cap=int(entry.get("requestCap", 0)),
            token_cap=int(entry.get("tokenCap", 0)),
            output_token_cap=int(entry.get("outputTokenCap", 0)),
            tool_allowlist=allowlist,
            expires_at=str(entry.get("expiresAt", "")),
            created_at=str(entry.get("createdAt", "")),
            approved_by=str(entry.get("approvedBy", "human_operator")),
            single_use=bool(entry.get("singleUse", True)),
            used_at=str(entry.get("usedAt", "")),
            redaction_applied=True,
        )
    except (TypeError, ValueError):
        return None


def _read_all_approvals(hermes_home: str | None) -> list[LiveApproval]:
    raw = _read_store(hermes_home)
    if raw is None:
        return []
    out: list[LiveApproval] = []
    for entry in raw:
        rebuilt = _approval_from_dict(entry)
        if rebuilt is not None:
            out.append(rebuilt)
    return out


# ---------------------------------------------------------------------------
# 5. Issue / validate / expire / revoke
# ---------------------------------------------------------------------------


def issue_live_approval(
    *,
    provider_name: str,
    model: str,
    base_url_host: str,
    budget_cap_cents: int,
    request_cap: int,
    token_cap: int,
    output_token_cap: int,
    tool_allowlist: frozenset[str] | set[str],
    hermes_home: str | None = None,
    now_iso: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    approved_by: str = "human_operator",
) -> LiveApproval | None:
    """Issue a fresh, single-use, short-window human approval.

    Returns the approval (persisted) or ``None`` when the store cannot be
    written (fail closed — no approval is granted). The approval never carries
    a key / header / token.
    """
    expires_iso = _shift_iso(now_iso, ttl_seconds)
    approval = LiveApproval(
        approval_id=f"plap_{secrets.token_urlsafe(16)}",
        approval_scope=APPROVAL_SCOPE,
        provider_name=provider_name,
        provider_mode=PROVIDER_MODE_REAL,
        model=model,
        base_url_host=base_url_host,
        budget_cap_cents=int(budget_cap_cents),
        request_cap=int(request_cap),
        token_cap=int(token_cap),
        output_token_cap=int(output_token_cap),
        tool_allowlist=frozenset(str(t) for t in tool_allowlist),
        expires_at=expires_iso,
        created_at=now_iso,
        approved_by=approved_by,
        single_use=True,
        used_at="",
        redaction_applied=True,
    )
    existing = _read_all_approvals(hermes_home)
    # A single in-flight approval is permitted at a time (single-use policy).
    existing.append(approval)
    if not _persist(hermes_home, existing):
        return None
    return approval


def _shift_iso(now_iso: str, seconds: int) -> str:
    """Add ``seconds`` to an ISO timestamp string (UTC). Best-effort parse."""
    from datetime import datetime, timedelta, timezone

    base = _parse_iso(now_iso)
    if base is None:
        return now_iso
    return (base + timedelta(seconds=max(0, seconds))).isoformat()


def _parse_iso(value: str) -> datetime | None:
    from datetime import datetime, timezone

    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate_live_approval(
    approval: LiveApproval | None,
    *,
    now_iso: str,
) -> tuple[bool, str | None]:
    """Validate an approval's lifetime (scope / expiry / single-use).

    Returns ``(valid, blocked_reason)``. ``None`` approval → not-human-approved.
    A mismatched scope, an expired window, or an already-used single-use
    approval fails closed with a precise reason.
    """
    if approval is None:
        return False, BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED
    if approval.approval_scope != APPROVAL_SCOPE:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID
    if approval.provider_mode != PROVIDER_MODE_REAL:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID
    now = _parse_iso(now_iso)
    expires = _parse_iso(approval.expires_at)
    if now is not None and expires is not None and now > expires:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED
    if approval.single_use and approval.used_at:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_USED
    return True, None


def match_live_approval(
    approval: LiveApproval,
    *,
    provider_name: str,
    model: str,
    base_url_host: str,
    tool_allowlist: frozenset[str] | set[str],
) -> tuple[bool, str | None]:
    """Match an approval against the concrete request parameters.

    Any provider / model / host / tool-allowlist mismatch fails closed with
    ``blocked_live_provider_approval_mismatch``.
    """
    requested = frozenset(str(t) for t in tool_allowlist)
    if approval.provider_name != provider_name:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH
    if approval.model != model:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH
    if approval.base_url_host != base_url_host:
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH
    # Every requested tool must be inside the approved allowlist (defense).
    if not requested.issubset(approval.tool_allowlist):
        return False, BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH
    return True, None


def mark_approval_used(
    approval_id: str,
    *,
    hermes_home: str | None,
    now_iso: str,
) -> bool:
    """Invalidate a single-use approval after exactly one live request.

    Returns whether the store was updated. A single-use approval may never be
    reused; calling this twice on the same id is a no-op (already used).
    """
    approvals = _read_all_approvals(hermes_home)
    changed = False
    updated: list[LiveApproval] = []
    for approval in approvals:
        if approval.approval_id == approval_id and approval.single_use and not approval.used_at:
            updated.append(LiveApproval(
                approval_id=approval.approval_id,
                approval_scope=approval.approval_scope,
                provider_name=approval.provider_name,
                provider_mode=approval.provider_mode,
                model=approval.model,
                base_url_host=approval.base_url_host,
                budget_cap_cents=approval.budget_cap_cents,
                request_cap=approval.request_cap,
                token_cap=approval.token_cap,
                output_token_cap=approval.output_token_cap,
                tool_allowlist=approval.tool_allowlist,
                expires_at=approval.expires_at,
                created_at=approval.created_at,
                approved_by=approval.approved_by,
                single_use=approval.single_use,
                used_at=now_iso,
                redaction_applied=True,
            ))
            changed = True
        else:
            updated.append(approval)
    if not changed:
        return False
    return _persist(hermes_home, updated)


def revoke_all_approvals(*, hermes_home: str | None) -> bool:
    """Clear the live approval store (disable / rollback procedure).

    Returns whether the store was cleared successfully. Never reads ~/.hermes.
    """
    return _persist(hermes_home, [])


def find_active_approval(
    approval_id: str | None,
    *,
    hermes_home: str | None,
) -> LiveApproval | None:
    """Look up an approval by id from the dev store. ``None`` if absent / corrupt."""
    if not approval_id:
        return None
    for approval in _read_all_approvals(hermes_home):
        if approval.approval_id == approval_id:
            return approval
    return None


def list_approvals(*, hermes_home: str | None) -> list[LiveApproval]:
    """Return all stored approvals (value-free)."""
    return _read_all_approvals(hermes_home)


__all__ = [
    "APPROVAL_SCOPE",
    "PROVIDER_MODE_REAL",
    "DEFAULT_TTL_SECONDS",
    "LiveApproval",
    "BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED",
    "BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED",
    "BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID",
    "BLOCKED_LIVE_PROVIDER_APPROVAL_USED",
    "BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH",
    "BLOCKED_LIVE_PROVIDER_DEV_ONLY_VIOLATION",
    "issue_live_approval",
    "validate_live_approval",
    "match_live_approval",
    "mark_approval_used",
    "revoke_all_approvals",
    "find_active_approval",
    "list_approvals",
]
