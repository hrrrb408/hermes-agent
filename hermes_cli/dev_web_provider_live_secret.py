"""Phase 3B-Live-Enablement — Live Provider Secret Read Policy (Frozen).

A real API key may be read **only** from the environment, and **only** after
every live gate has passed (real mode + api enabled + kill switch inactive +
valid approval + budget valid + host allowlisted). Its value never persists,
never traverses a store, and never appears in audit / logs / exceptions /
responses / UI / tests. This module returns a **value-free** ``SecretState``
only; it never returns, prints, logs, or audits the key value.

``OPENAI_API_KEY`` is the named first-live source. Default tests / smoke do
**not** reach the env read: with no approval / disabled mode / active kill
switch / invalid budget / off-allowlist host, the module short-circuits with
``blocked_before_secret_read`` and never inspects the environment.

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live secret-read policy implemented (default paths never read the key)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# The named first-live API-key environment variable. It is READ ONLY and only
# after every gate passes. Its value is never returned by this module.
LIVE_API_KEY_ENV = "OPENAI_API_KEY"

SecretState = Literal[
    "env_present",
    "env_missing",
    "not_checked",
    "blocked_before_secret_read",
]


@dataclass(frozen=True, slots=True)
class SecretCheckResult:
    """Value-free secret state. ``key_value`` is structurally impossible here."""

    key_source: str  # always "environment"
    key_state: SecretState
    redaction_applied: bool = True

    def to_safe_dict(self) -> dict[str, str | bool]:
        return {
            "keySource": self.key_source,
            "keyState": self.key_state,
            "keyValue": "never",
            "redactionApplied": True,
        }


def read_provider_api_key_if_live_approved(
    *,
    provider_mode: str,
    api_enabled: bool,
    kill_switch_active: bool,
    approval_valid: bool,
    budget_ok: bool,
    host_ok: bool,
) -> SecretCheckResult:
    """Return the value-free secret state, reading the env ONLY past every gate.

    Evaluation order (first gate wins; all short-circuit to
    ``blocked_before_secret_read`` — the env is never inspected):

      1. mode == real            else blocked_before_secret_read
      2. api_enabled             else blocked_before_secret_read
      3. kill switch inactive    else blocked_before_secret_read
      4. approval valid          else blocked_before_secret_read
      5. budget valid            else blocked_before_secret_read
      6. host allowlisted        else blocked_before_secret_read
      7. only now: read OPENAI_API_KEY presence → env_present / env_missing

    The returned object carries only ``keySource`` / ``keyState``. It never
    carries the key value, a header, a bearer token, a prefix, a suffix, a
    length, a hash, or a fingerprint.
    """
    if provider_mode != "real":
        return SecretCheckResult(
            key_source="environment", key_state="not_checked",
        )
    if not api_enabled:
        return SecretCheckResult(
            key_source="environment", key_state="blocked_before_secret_read",
        )
    if kill_switch_active:
        return SecretCheckResult(
            key_source="environment", key_state="blocked_before_secret_read",
        )
    if not approval_valid:
        return SecretCheckResult(
            key_source="environment", key_state="blocked_before_secret_read",
        )
    if not budget_ok:
        return SecretCheckResult(
            key_source="environment", key_state="blocked_before_secret_read",
        )
    if not host_ok:
        return SecretCheckResult(
            key_source="environment", key_state="blocked_before_secret_read",
        )

    # Every gate passed — inspect the env PRESENCE only (never the value).
    import os

    value = os.environ.get(LIVE_API_KEY_ENV, "")
    present = isinstance(value, str) and bool(value.strip())
    return SecretCheckResult(
        key_source="environment",
        key_state="env_present" if present else "env_missing",
    )


def is_secret_state_safe_for_audit(result: SecretCheckResult) -> bool:
    """True only when the result carries no key value / header / token."""
    return result.key_state in (
        "env_present", "env_missing", "not_checked", "blocked_before_secret_read",
    ) and result.key_source == "environment"


__all__ = [
    "LIVE_API_KEY_ENV",
    "SecretState",
    "SecretCheckResult",
    "read_provider_api_key_if_live_approved",
    "is_secret_state_safe_for_audit",
]
