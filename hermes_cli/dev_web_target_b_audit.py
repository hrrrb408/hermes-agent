"""Phase 4B — Target B audit trail layer (pure stdlib, fail-closed).

Layer 10 of the Phase 4B Target B engineering path. Defines the **audit
trail** model: audit events, the redaction policy, and the denied-execution /
policy-evaluation audit builders.

The audit trail is **in-memory only**: nothing is persisted, no JSONL is
written, and no audit store is committed. Every audit payload is
defense-in-depth redacted so a future editor adding a secret / production path
/ fake-authorization substring can never leak it through an audit record.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_common import (
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen audit decision + redaction policy
# ---------------------------------------------------------------------------

#: Audit decision verbs.
AUDIT_DECISION_DENIED: str = "denied"
AUDIT_DECISION_PREVIEW: str = "preview_only"
AUDIT_DECISION_REDACTED: str = "redacted"

#: The audit persistence model. In-memory only; nothing is committed.
AUDIT_PERSISTENCE_IN_MEMORY_ONLY: str = "in_memory_only"
AUDIT_PERSISTED: bool = False


@dataclass(frozen=True, slots=True)
class AuditRedactionPolicy:
    """The frozen audit redaction policy."""

    persisted: bool
    secrets_redacted: bool
    production_paths_redacted: bool
    fake_authorization_redacted: bool
    audit_log_committed: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "persisted": self.persisted,
                "secretsRedacted": self.secrets_redacted,
                "productionPathsRedacted": self.production_paths_redacted,
                "fakeAuthorizationRedacted": self.fake_authorization_redacted,
                "auditLogCommitted": self.audit_log_committed,
            }
        )


#: The frozen audit redaction policy. In-memory only; redaction on.
AUDIT_REDACTION_POLICY: AuditRedactionPolicy = AuditRedactionPolicy(
    persisted=False,
    secrets_redacted=True,
    production_paths_redacted=True,
    fake_authorization_redacted=True,
    audit_log_committed=False,
)


def build_audit_redaction_policy() -> AuditRedactionPolicy:
    """Return a defensive copy of the frozen audit redaction policy."""
    p = AUDIT_REDACTION_POLICY
    return AuditRedactionPolicy(
        persisted=p.persisted,
        secrets_redacted=p.secrets_redacted,
        production_paths_redacted=p.production_paths_redacted,
        fake_authorization_redacted=p.fake_authorization_redacted,
        audit_log_committed=p.audit_log_committed,
    )


# ---------------------------------------------------------------------------
# 2. The audit event
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetBAuditEvent:
    """A single, redacted, in-memory-only Target B audit event."""

    event_id: str
    decision: str
    reason: str
    layer: str
    persisted: bool
    payload: dict[str, Any]

    def to_safe_dict(self) -> dict[str, Any]:
        # Redact at the boundary so no secret / path / fake-authorization ever
        # leaves the audit surface.
        return redact_target_b_payload(
            {
                "eventId": self.event_id,
                "decision": self.decision,
                "reason": self.reason,
                "layer": self.layer,
                "persisted": self.persisted,
                "payload": self.payload,
            }
        )


def build_target_b_audit_event(
    *,
    event_id: str,
    decision: str,
    reason: str,
    layer: str,
    payload: Any = None,
) -> TargetBAuditEvent:
    """Build a redacted, in-memory-only Target B audit event. Pure."""
    return TargetBAuditEvent(
        event_id=event_id if isinstance(event_id, str) else "<invalid>",
        decision=decision if isinstance(decision, str) else AUDIT_DECISION_REDACTED,
        reason=reason if isinstance(reason, str) else "<invalid>",
        layer=layer if isinstance(layer, str) else "<invalid>",
        persisted=AUDIT_PERSISTED,
        payload=redact_target_b_payload(payload) if isinstance(payload, dict) else {},
    )


def build_denied_execution_audit(
    *,
    event_id: str = "target-b-execution-denied",
    layer: str = "execution_policy",
    reason: str = "target_b_disabled",
    payload: Any = None,
) -> TargetBAuditEvent:
    """Build the denied-execution audit event. In-memory only."""
    return build_target_b_audit_event(
        event_id=event_id,
        decision=AUDIT_DECISION_DENIED,
        reason=reason,
        layer=layer,
        payload=payload,
    )


def build_policy_evaluation_audit(
    *,
    event_id: str = "target-b-policy-evaluated",
    layer: str = "execution_policy",
    reason: str = "policy_evaluated_denied",
    payload: Any = None,
) -> TargetBAuditEvent:
    """Build the policy-evaluation audit event. In-memory only."""
    return build_target_b_audit_event(
        event_id=event_id,
        decision=AUDIT_DECISION_PREVIEW,
        reason=reason,
        layer=layer,
        payload=payload,
    )


def redact_target_b_audit_payload(payload: Any) -> Any:
    """Redact an arbitrary audit payload. Pure / total — never raises."""
    return redact_target_b_payload(payload)


@dataclass(frozen=True, slots=True)
class AuditTrailReport:
    """The frozen aggregate audit-trail readiness report."""

    persistence: str
    persisted: bool
    audit_log_committed: bool
    secrets_redacted: bool
    production_paths_redacted: bool
    fake_authorization_redacted: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "persistence": self.persistence,
                "persisted": self.persisted,
                "auditLogCommitted": self.audit_log_committed,
                "secretsRedacted": self.secrets_redacted,
                "productionPathsRedacted": self.production_paths_redacted,
                "fakeAuthorizationRedacted": self.fake_authorization_redacted,
            }
        )


def build_audit_trail_report() -> AuditTrailReport:
    """Build the frozen aggregate audit-trail report. In-memory only."""
    p = build_audit_redaction_policy()
    return AuditTrailReport(
        persistence=AUDIT_PERSISTENCE_IN_MEMORY_ONLY,
        persisted=p.persisted,
        audit_log_committed=p.audit_log_committed,
        secrets_redacted=p.secrets_redacted,
        production_paths_redacted=p.production_paths_redacted,
        fake_authorization_redacted=p.fake_authorization_redacted,
    )


def assert_audit_layer_disabled() -> None:
    """Re-affirm the audit layer disabled invariants. Pure."""
    p = build_audit_redaction_policy()
    assert p.persisted is False
    assert p.audit_log_committed is False
    assert p.secrets_redacted is True
    event = build_denied_execution_audit(
        payload={"credential": "sk-FAKE-DO-NOT-LEAK", "note": "trust_token=fake"}
    )
    text = str(event.to_safe_dict())
    assert "[REDACTED]" in text
    assert "sk-FAKE-DO-NOT-LEAK" not in text
    report = build_audit_trail_report()
    assert report.persisted is False
    assert report.audit_log_committed is False


__all__ = [
    # decisions / persistence
    "AUDIT_DECISION_DENIED",
    "AUDIT_DECISION_PREVIEW",
    "AUDIT_DECISION_REDACTED",
    "AUDIT_PERSISTENCE_IN_MEMORY_ONLY",
    "AUDIT_PERSISTED",
    # redaction policy
    "AuditRedactionPolicy",
    "AUDIT_REDACTION_POLICY",
    "build_audit_redaction_policy",
    "redact_target_b_audit_payload",
    # event
    "TargetBAuditEvent",
    "build_target_b_audit_event",
    "build_denied_execution_audit",
    "build_policy_evaluation_audit",
    # report
    "AuditTrailReport",
    "build_audit_trail_report",
    # boundary
    "assert_audit_layer_disabled",
]
