"""Phase 3H Dev-only Sandbox Proof Skeleton — Policy (Block 2).

The coarse policy layer of the dev-only sandbox proof:

  - **Capability default-deny evaluator** — every capability is denied unless
    it is one of the three frozen "proof-label-only" capabilities
    (``descriptor.read`` / ``sandbox.proof.evaluate`` / ``audit.redact``).
    Those three are allowed *as labels* — they never represent real execution
    permission. A granted capability does not bypass any guard.
  - **Kill-switch policy** — when the kill switch is **active**, every proof
    evaluation fails closed. An **inactive** kill switch does **not** grant any
    dangerous capability (it only means evaluation is not pre-emptively
    blocked). The kill switch is a dev-only policy flag; it never signals a
    process and never touches production.
  - **Descriptor-only enforcement** — a descriptor may be read / validated but
    never executed. A descriptor carrying any executable / module / command /
    entrypoint / import / shell / url / secret field is denied outright. This
    reuses the Phase 3D recursive forbidden-field scanner so the descriptor
    boundary cannot drift between modules.

Hard guarantees (frozen, see docs/webui/phase-3h-sandbox-proof-planning.md):

  - Pure / deterministic / stdlib-only. No ``importlib`` / ``__import__`` /
    ``subprocess`` / ``shell`` / network / secret read.
  - **Never** executes a descriptor, never loads a plugin, never dynamic-imports.
  - A granted capability is a *label*; it grants nothing at runtime.
  - The kill switch never signals / stops / restarts any process.

Phase: 3H — Dev-only Sandbox Proof Skeleton
Status: implemented (policy). No plugin execution, no dynamic loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from hermes_cli.dev_web_plugin_descriptor_schema import is_forbidden_field_present

SANDBOX_POLICY_AUDIT_SOURCE = "dev_web_sandbox_policy"

# ---------------------------------------------------------------------------
# 1. Capability taxonomy + default-deny evaluator
# ---------------------------------------------------------------------------

#: The frozen capability label set a sandbox proof recognizes. These are
#: *labels* only — none represents a real execution grant.
CAPABILITY_LABELS: frozenset[str] = frozenset(
    {
        "descriptor.read",
        "sandbox.proof.evaluate",
        "audit.redact",
        "filesystem.read",
        "filesystem.write",
        "network.request",
        "secrets.read",
        "provider.request",
        "database.write",
        "process.spawn",
        "plugin.execute",
        "plugin.load",
        "routes.modify",
        "production.access",
    }
)

#: Capabilities allowed **as labels** in a dev-only / static-descriptor proof
#: context. They never represent real execution: granting one of these does
#: not bypass any guard and does not enable a runtime path.
CAPABILITY_DEFAULT_ALLOWED: frozenset[str] = frozenset(
    {
        "descriptor.read",
        "sandbox.proof.evaluate",
        "audit.redact",
    }
)

#: Capabilities that are unconditionally denied — they would require a real
#: runtime path, external network, a real secret, or production access. These
#: map 1:1 to the denial surfaces the sandbox proof must never open.
DANGEROUS_CAPABILITIES: frozenset[str] = frozenset(
    {
        "filesystem.write",
        "network.request",
        "secrets.read",
        "provider.request",
        "database.write",
        "process.spawn",
        "plugin.execute",
        "plugin.load",
        "routes.modify",
        "production.access",
    }
)

#: Stable reason tokens the capability evaluator emits.
CAPABILITY_REASONS: frozenset[str] = frozenset(
    {
        "unknown_capability",
        "capability_default_denied",
        "dangerous_capability_denied",
        "plugin_execution_denied",
        "plugin_load_denied",
        "process_spawn_denied",
        "filesystem_write_denied",
        "network_request_denied",
        "secret_read_denied",
        "provider_request_denied",
        "database_write_denied",
        "routes_modify_denied",
        "production_access_denied",
    }
)

#: Per-capability specific denial reason (more precise than the generic default).
_CAPABILITY_DENY_REASONS: dict[str, str] = {
    "plugin.execute": "plugin_execution_denied",
    "plugin.load": "plugin_load_denied",
    "process.spawn": "process_spawn_denied",
    "filesystem.write": "filesystem_write_denied",
    "network.request": "network_request_denied",
    "secrets.read": "secret_read_denied",
    "provider.request": "provider_request_denied",
    "database.write": "database_write_denied",
    "routes.modify": "routes_modify_denied",
    "production.access": "production_access_denied",
}


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    """Per-capability decision. A granted capability is a label, not a grant."""

    capability: str
    allowed: bool
    reasons: tuple[str, ...] = ()
    note: str = ""

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "note": self.note,
            "redactionApplied": True,
        }


@dataclass(frozen=True, slots=True)
class CapabilityEvaluationContext:
    """Optional context for the capability evaluator.

    ``allow_temp_filesystem_read`` lets a test fixture / temp-root caller mark
    that a ``filesystem.read`` is scoped to a temp root (the filesystem guard
    still enforces the actual boundary). Default is False → ``filesystem.read``
    is denied by the policy layer too.
    """

    allow_temp_filesystem_read: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "allowTempFilesystemRead": self.allow_temp_filesystem_read,
            "redactionApplied": True,
        }


def evaluate_capability(
    capability: Any,
    *,
    context: CapabilityEvaluationContext | None = None,
) -> CapabilityDecision:
    """Evaluate a single capability. Default-deny.

    Rules (first match wins):

      1. Unknown capability → denied (``unknown_capability``).
      2. A frozen default-allowed label → allowed **as a label**; the note
         records that it grants nothing at runtime.
      3. ``filesystem.read`` → allowed only when the context marks a temp-root
         fixture; otherwise denied (``capability_default_denied``).
      4. Any dangerous capability → denied with the specific reason.
      5. Everything else → denied (``capability_default_denied``).
    """
    if not isinstance(capability, str) or capability not in CAPABILITY_LABELS:
        return CapabilityDecision(
            capability=str(capability) if isinstance(capability, str) else "<invalid>",
            allowed=False,
            reasons=("unknown_capability",),
        )

    if capability in CAPABILITY_DEFAULT_ALLOWED:
        return CapabilityDecision(
            capability=capability,
            allowed=True,
            reasons=(),
            note="proof_label_only_no_real_execution",
        )

    if capability == "filesystem.read":
        ctx = context or CapabilityEvaluationContext()
        if ctx.allow_temp_filesystem_read:
            return CapabilityDecision(
                capability=capability,
                allowed=True,
                reasons=(),
                note="temp_root_scoped_read_only",
            )
        return CapabilityDecision(
            capability=capability,
            allowed=False,
            reasons=("capability_default_denied",),
        )

    if capability in DANGEROUS_CAPABILITIES:
        reason = _CAPABILITY_DENY_REASONS.get(capability, "dangerous_capability_denied")
        return CapabilityDecision(
            capability=capability,
            allowed=False,
            reasons=(reason,),
        )

    return CapabilityDecision(
        capability=capability,
        allowed=False,
        reasons=("capability_default_denied",),
    )


def evaluate_capabilities(
    capabilities: Any,
    *,
    context: CapabilityEvaluationContext | None = None,
) -> list[CapabilityDecision]:
    """Evaluate an iterable of capabilities. Returns one decision each."""
    if not isinstance(capabilities, (list, tuple, set, frozenset)):
        return []
    return [evaluate_capability(c, context=context) for c in capabilities if c is not None]


# ---------------------------------------------------------------------------
# 2. Kill-switch policy
# ---------------------------------------------------------------------------

#: The frozen kill-switch trigger reasons relevant to a sandbox proof. These
#: never signal a process; they are dev-only policy labels.
KILL_SWITCH_TRIGGER_SANDBOX_PROOF = "sandbox_proof_fail_closed"
KILL_SWITCH_TRIGGER_DESCRIPTOR_EXECUTION_SURFACE = "descriptor_execution_surface"
KILL_SWITCH_TRIGGER_FORBIDDEN_PATH = "forbidden_path_request"
KILL_SWITCH_TRIGGER_EXTERNAL_NETWORK = "external_network_request"
KILL_SWITCH_TRIGGER_REAL_SECRET = "real_secret_request"
KILL_SWITCH_TRIGGER_ROUTE_GOVERNANCE_DRIFT = "route_governance_drift"

KILL_SWITCH_TRIGGERS: frozenset[str] = frozenset(
    {
        KILL_SWITCH_TRIGGER_SANDBOX_PROOF,
        KILL_SWITCH_TRIGGER_DESCRIPTOR_EXECUTION_SURFACE,
        KILL_SWITCH_TRIGGER_FORBIDDEN_PATH,
        KILL_SWITCH_TRIGGER_EXTERNAL_NETWORK,
        KILL_SWITCH_TRIGGER_REAL_SECRET,
        KILL_SWITCH_TRIGGER_ROUTE_GOVERNANCE_DRIFT,
    }
)


@dataclass(frozen=True, slots=True)
class KillSwitchDecision:
    """Kill-switch policy decision. Never signals a process."""

    active: bool
    fail_closed: bool
    reason: str
    note: str

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "failClosed": self.fail_closed,
            "reason": self.reason,
            "note": self.note,
            "redactionApplied": True,
        }


def evaluate_kill_switch(active: Any) -> KillSwitchDecision:
    """Evaluate the kill switch for a sandbox proof.

    ``active`` True → every proof evaluation fails closed
    (``sandbox_proof_fail_closed``). ``active`` False → evaluation may proceed
    through the guards, **but** an inactive switch grants no dangerous
    capability (the note records this). The kill switch is a dev-only flag; it
    never signals / stops / restarts any process.
    """
    is_active = bool(active)
    if is_active:
        return KillSwitchDecision(
            active=True,
            fail_closed=True,
            reason=KILL_SWITCH_TRIGGER_SANDBOX_PROOF,
            note="kill_switch_active_blocks_all_proof_evaluation",
        )
    return KillSwitchDecision(
        active=False,
        fail_closed=False,
        reason="",
        note="kill_switch_inactive_does_not_grant_capabilities",
    )


# ---------------------------------------------------------------------------
# 3. Descriptor-only enforcement
# ---------------------------------------------------------------------------

#: Stable reason tokens the descriptor evaluator emits.
DESCRIPTOR_REASONS: frozenset[str] = frozenset(
    {
        "malformed_descriptor",
        "descriptor_carries_execution_surface",
        "descriptor_oversized",
        "descriptor_id_missing",
    }
)

#: Maximum descriptor-metadata size (bytes of ``repr``). Oversized → denied.
MAX_DESCRIPTOR_SIZE: int = 32768

#: The descriptor execution-surface fields whose presence converts a descriptive
#: record into an execution path. Reused from the Phase 3D schema via
#: :func:`is_forbidden_field_present` (which scans recursively).


@dataclass(frozen=True, slots=True)
class DescriptorDecision:
    """Descriptor-only enforcement decision."""

    descriptor_id_redacted: str
    descriptor_only: bool
    allowed: bool
    reasons: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "descriptorId": self.descriptor_id_redacted,
            "descriptorOnly": self.descriptor_only,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "redactionApplied": True,
        }


def evaluate_descriptor(descriptor_metadata: Any) -> DescriptorDecision:
    """Enforce descriptor-only: a descriptor may be read, never executed.

    Denies when the metadata:

      - is not a dict (``malformed_descriptor``);
      - carries any forbidden / executable / module / command / entrypoint /
        import / shell / url / secret field anywhere (recursive scan via the
        Phase 3D :func:`is_forbidden_field_present`) —
        ``descriptor_carries_execution_surface``;
      - is oversized (``descriptor_oversized``).

    A clean static descriptor is allowed **as a descriptor-only read**: the note
    records that it triggers no loader, no runtime, no dynamic loading.
    """
    if not isinstance(descriptor_metadata, Mapping):
        return DescriptorDecision(
            descriptor_id_redacted="",
            descriptor_only=False,
            allowed=False,
            reasons=("malformed_descriptor",),
        )

    descriptor_id = descriptor_metadata.get("pluginId") or descriptor_metadata.get("descriptorId")
    if not isinstance(descriptor_id, str) or not descriptor_id:
        return DescriptorDecision(
            descriptor_id_redacted="",
            descriptor_only=False,
            allowed=False,
            reasons=("descriptor_id_missing",),
        )

    forbidden = is_forbidden_field_present(dict(descriptor_metadata))
    if forbidden is not None:
        return DescriptorDecision(
            descriptor_id_redacted=_redact_descriptor_id(descriptor_id),
            descriptor_only=False,
            allowed=False,
            reasons=("descriptor_carries_execution_surface",),
        )

    try:
        size = len(repr(dict(descriptor_metadata)))
    except Exception:  # pragma: no cover — defensive
        size = 0
    if size > MAX_DESCRIPTOR_SIZE:
        return DescriptorDecision(
            descriptor_id_redacted=_redact_descriptor_id(descriptor_id),
            descriptor_only=False,
            allowed=False,
            reasons=("descriptor_oversized",),
        )

    return DescriptorDecision(
        descriptor_id_redacted=_redact_descriptor_id(descriptor_id),
        descriptor_only=True,
        allowed=True,
        reasons=(),
    )


def _redact_descriptor_id(descriptor_id: str) -> str:
    """Return a sanitized descriptor id for audit (never a path / secret)."""
    if not isinstance(descriptor_id, str):
        return ""
    # Keep only the stable id characters; drop anything path/secret-like.
    import re

    cleaned = re.sub(r"[^A-Za-z0-9_.\-]", "", descriptor_id)
    return cleaned[:128]


__all__ = [
    "SANDBOX_POLICY_AUDIT_SOURCE",
    "CAPABILITY_LABELS",
    "CAPABILITY_DEFAULT_ALLOWED",
    "DANGEROUS_CAPABILITIES",
    "CAPABILITY_REASONS",
    "CapabilityDecision",
    "CapabilityEvaluationContext",
    "evaluate_capability",
    "evaluate_capabilities",
    "KILL_SWITCH_TRIGGERS",
    "KILL_SWITCH_TRIGGER_SANDBOX_PROOF",
    "KILL_SWITCH_TRIGGER_DESCRIPTOR_EXECUTION_SURFACE",
    "KILL_SWITCH_TRIGGER_FORBIDDEN_PATH",
    "KILL_SWITCH_TRIGGER_EXTERNAL_NETWORK",
    "KILL_SWITCH_TRIGGER_REAL_SECRET",
    "KILL_SWITCH_TRIGGER_ROUTE_GOVERNANCE_DRIFT",
    "KillSwitchDecision",
    "evaluate_kill_switch",
    "DESCRIPTOR_REASONS",
    "MAX_DESCRIPTOR_SIZE",
    "DescriptorDecision",
    "evaluate_descriptor",
]
