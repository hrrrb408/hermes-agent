"""Phase 3H Dev-only Sandbox Proof Skeleton — In-memory Audit (Block 2).

Builds a **redacted, in-memory** audit record for a sandbox-proof evaluation.
The record is never persisted: no JSONL append, no database write, no file
write, no production-state mutation. It exists only to carry a verifiable,
value-free breadcrumb that a proof evaluated (and what it denied) — useful for
tests and for a future, separately-authorized durable audit writer.

The record is value-free:

  - no raw secret (every secret value / secret-field string / production path
    is ``[REDACTED]`` before it can reach the record);
  - no raw production path (``~/.hermes`` / ``state.db`` collapse to
    ``[REDACTED]``);
  - no route change, no production access, no external network, no real
    secret, no runtime execution is ever recorded as ``True`` — these are the
    frozen "did not happen" evidence flags.

Hard guarantees (frozen):

  - In-memory only. This module opens **no** file, **no** socket, **no**
    database. The returned dict is the only artifact.
  - Redaction is applied defensively: the builder re-redacts the whole record
    one more time before returning, so a defective caller cannot leak a value.
  - A redaction failure fails closed: if the final sweep detects a secret, the
    record is replaced with a minimal ``redaction_failed`` denial.

Phase: 3H — Dev-only Sandbox Proof Skeleton
Status: implemented (in-memory audit). No persistence, no new route.
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_sandbox_guards import contains_secret, redact_sandbox_payload

SANDBOX_AUDIT_SOURCE = "dev_web_sandbox_audit"
SANDBOX_AUDIT_VERSION = "phase-3h-sandbox-proof-audit-v1"

#: The frozen evidence flags every audit record carries. All are constants;
#: a dev-only sandbox proof requires none of them.
EVIDENCE_FLAGS: tuple[str, ...] = (
    "routeChangeRequired",
    "productionAccessRequired",
    "externalNetworkRequired",
    "realSecretRequired",
    "runtimeExecutionRequired",
)


def _evidence_flags() -> dict[str, bool]:
    """Return the frozen 'did-not-happen' evidence flags (all False)."""
    return {flag: False for flag in EVIDENCE_FLAGS}


def build_sandbox_audit_record(
    *,
    decision: str,
    reasons: list[str] | tuple[str, ...] = (),
    triggered_guards: list[str] | tuple[str, ...] = (),
    requested_capabilities: list[str] | tuple[str, ...] = (),
    descriptor_id: str | None = None,
    kill_switch_active: bool | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a redacted, in-memory sandbox-proof audit record.

    Parameters are projected to safe scalars / lists and re-redacted before
    return. ``decision`` is coerced to ``"denied"`` unless it is exactly
    ``"allowed"`` (fail-closed default). The record never carries a raw
    secret or production path.
    """
    coerced_decision = "allowed" if decision == "allowed" else "denied"

    safe_reasons = _to_clean_list(reasons)
    safe_guards = _to_clean_list(triggered_guards)
    safe_caps = _to_clean_list(requested_capabilities)

    sanitized_descriptor = _sanitize_descriptor_id(descriptor_id)
    sanitized_meta = redact_sandbox_payload(dict(safe_metadata) if safe_metadata else {})

    record: dict[str, Any] = {
        "schemaVersion": SANDBOX_AUDIT_VERSION,
        "source": SANDBOX_AUDIT_SOURCE,
        "decision": coerced_decision,
        "reasons": safe_reasons,
        "triggeredGuards": safe_guards,
        "requestedCapabilities": safe_caps,
        "descriptorId": sanitized_descriptor,
        "killSwitchActive": bool(kill_switch_active) if kill_switch_active is not None else None,
        "safeMetadata": sanitized_meta,
        "evidence": _evidence_flags(),
        "redactionApplied": True,
        "persisted": False,
    }

    # Defensive final re-redaction: if anything secret-shaped slipped through,
    # fail closed to a minimal denial record.
    if contains_secret(record):
        return _redaction_failed_record()

    return record


def _to_clean_list(items: Any) -> list[str]:
    if not isinstance(items, (list, tuple, set, frozenset)):
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, str) and item:
            cleaned = item.strip()
            if cleaned:
                out.append(cleaned)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _sanitize_descriptor_id(descriptor_id: Any) -> str:
    if not isinstance(descriptor_id, str):
        return ""
    import re

    cleaned = re.sub(r"[^A-Za-z0-9_.\-]", "", descriptor_id)
    return cleaned[:128]


def _redaction_failed_record() -> dict[str, Any]:
    """Minimal fail-closed record emitted when the final sweep detects a secret."""
    return {
        "schemaVersion": SANDBOX_AUDIT_VERSION,
        "source": SANDBOX_AUDIT_SOURCE,
        "decision": "denied",
        "reasons": ["redaction_failed_fail_closed"],
        "triggeredGuards": ["redaction_failure"],
        "requestedCapabilities": [],
        "descriptorId": "",
        "killSwitchActive": None,
        "safeMetadata": {},
        "evidence": _evidence_flags(),
        "redactionApplied": True,
        "redactionFailed": True,
        "persisted": False,
    }


def is_audit_record_safe(record: Any) -> bool:
    """True iff *record* carries no secret / production path and is in-memory."""
    if not isinstance(record, Mapping):
        return False
    if record.get("persisted") is True:
        return False
    if contains_secret(record):
        return False
    # Every evidence flag must be False.
    evidence = record.get("evidence")
    if not isinstance(evidence, Mapping):
        return False
    for flag in EVIDENCE_FLAGS:
        if evidence.get(flag) is not False:
            return False
    return True


__all__ = [
    "SANDBOX_AUDIT_SOURCE",
    "SANDBOX_AUDIT_VERSION",
    "EVIDENCE_FLAGS",
    "build_sandbox_audit_record",
    "is_audit_record_safe",
]
