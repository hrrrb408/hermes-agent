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

import re
from dataclasses import dataclass
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
        "capability_injection_denied",
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


#: Characters / tokens that mark a capability string as injection-shaped
#: (wildcard, traversal, path separator, shell metacharacter, null byte). Such
#: strings are rejected explicitly with ``capability_injection_denied`` rather
#: than merely falling through to ``unknown_capability``, so the boundary stays
#: intentional even if the frozen label set is ever loosened. This never allows
#: anything exact-membership would not already deny.
_CAPABILITY_INJECTION_TOKENS: tuple[str, ...] = (
    "*",
    "?",
    "..",
    ";",
    "|",
    "&",
    "$",
    "`",
    "<",
    ">",
    "\\",
    "/",
    "\x00",
)


def _is_capability_injection(capability: str) -> bool:
    """True if *capability* carries wildcard / traversal / shell metacharacters."""
    return any(tok in capability for tok in _CAPABILITY_INJECTION_TOKENS)


def evaluate_capability(
    capability: Any,
    *,
    context: CapabilityEvaluationContext | None = None,
) -> CapabilityDecision:
    """Evaluate a single capability. Default-deny.

    Rules (first match wins):

      1. Non-string / empty / whitespace → denied (``unknown_capability``).
      2. Injection-shaped (wildcard / traversal / shell) → denied
         (``capability_injection_denied``); the raw string is masked and never
         echoed into the audit.
      3. Not a known label → denied (``unknown_capability``).
      4. A frozen default-allowed label → allowed **as a label**; the note
         records that it grants nothing at runtime.
      5. ``filesystem.read`` → allowed only when the context marks a temp-root
         fixture; otherwise denied (``capability_default_denied``).
      6. Any dangerous capability → denied with the specific reason.
      7. Everything else → denied (``capability_default_denied``).
    """
    if not isinstance(capability, str) or not capability.strip():
        return CapabilityDecision(
            capability=str(capability) if isinstance(capability, str) else "<invalid>",
            allowed=False,
            reasons=("unknown_capability",),
        )
    if _is_capability_injection(capability):
        return CapabilityDecision(
            capability="<invalid>",
            allowed=False,
            reasons=("capability_injection_denied",),
        )
    if capability not in CAPABILITY_LABELS:
        return CapabilityDecision(
            capability=capability,
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
    (``sandbox_proof_fail_closed``). ``active`` False / None → evaluation may
    proceed through the guards, **but** an inactive switch grants no dangerous
    capability (the note records this). Any **non-bool, non-None** value
    (string / number / container) is an *invalid* kill-switch state and is
    treated as armed — fail-closed — so an ambiguous flag cannot disarm the
    switch. The kill switch is a dev-only flag; it never signals / stops /
    restarts any process, and cannot be overridden by request metadata (the
    orchestrator reads only the ``kill_switch_active`` field).
    """
    if active is None or isinstance(active, bool):
        is_active = bool(active)
    else:
        # Invalid state → fail closed (armed).
        is_active = True
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
        "descriptor_id_unsafe",
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

    if not _descriptor_id_is_safe(descriptor_id):
        # An id containing traversal / path-separator / shell / wildcard
        # characters is denied outright (never merely redacted) — a clean
        # descriptor id is a label, not a path or command.
        return DescriptorDecision(
            descriptor_id_redacted="",
            descriptor_only=False,
            allowed=False,
            reasons=("descriptor_id_unsafe",),
        )

    forbidden = is_forbidden_field_present(dict(descriptor_metadata))
    if forbidden is not None:
        return DescriptorDecision(
            descriptor_id_redacted=_redact_descriptor_id(descriptor_id),
            descriptor_only=False,
            allowed=False,
            reasons=("descriptor_carries_execution_surface",),
        )

    # Extended execution/secret-surface scan: the Phase 3D blocklist matches
    # forbidden fields by exact name, so a synonym key (``entrypoint``,
    # ``module``, ``command``, ``url``, ``password``, ``private_key``,
    # ``dockerImage`` …) would slip through. Deny any key whose segmented form
    # denotes an execution / secret surface, recursively.
    if _descriptor_has_extended_surface(descriptor_metadata):
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


#: A clean descriptor id is a label over ``[A-Za-z0-9_.\-]`` only. Anything
#: containing traversal (``..``), path separators, shell metacharacters, or
#: wildcards is unsafe and denied before redaction.
_DESCRIPTOR_ID_SAFE: re.Pattern[str] = re.compile(r"[A-Za-z0-9_.\-]+")


def _descriptor_id_is_safe(descriptor_id: str) -> bool:
    """True iff *descriptor_id* is a clean label (full match against the safe set)."""
    if not isinstance(descriptor_id, str) or not descriptor_id:
        return False
    # An id with a traversal pair (``..``) is unsafe even though ``.`` is in
    # the safe charset.
    if ".." in descriptor_id:
        return False
    return _DESCRIPTOR_ID_SAFE.fullmatch(descriptor_id) is not None


def _redact_descriptor_id(descriptor_id: str) -> str:
    """Return a sanitized descriptor id for audit (never a path / secret)."""
    if not isinstance(descriptor_id, str):
        return ""
    # Keep only the stable id characters; drop anything path/secret-like.
    cleaned = re.sub(r"[^A-Za-z0-9_.\-]", "", descriptor_id)
    return cleaned[:128]


#: Execution-surface key segments. A descriptor key whose segmented form (or a
#: contiguous join of segments) carries one of these denotes an execution
#: surface — denied even if the exact key name is not in the Phase 3D
#: ``FORBIDDEN_FIELDS`` enumeration. Plurals included for exec (rarely config).
_DESCRIPTOR_EXEC_STEMS: frozenset[str] = frozenset(
    {
        "entrypoint",
        "entrypoints",
        "module",
        "modules",
        "import",
        "imports",
        "importpath",
        "importlib",
        "importmodule",
        "loadmodule",
        "dlopen",
        "command",
        "commands",
        "cmd",
        "exec",
        "execute",
        "executable",
        "shell",
        "bash",
        "script",
        "scripts",
        "url",
        "href",
        "download",
        "downloads",
        "install",
        "installs",
        "installcommand",
        "package",
        "packages",
        "packageurl",
        "docker",
        "dockerimage",
        "image",
        "container",
        "wheel",
        "wheelurl",
        "manifest",
        "manifesturl",
        "callable",
        "function",
        "handler",
        "binary",
        "subprocess",
        "childprocess",
        "process",
        "spawn",
        "webhook",
        "callback",
        "registry",
        "marketplace",
        "generated",
        "fetch",
    }
)

#: Normalized (alnum-only, lowercased) compound descriptor keys that denote an
#: execution surface but do **not** tokenize to a stem above — e.g. a dotted
#: ``os``/``system`` key normalizes to ``ossystem`` and a ``plugin``/``load``
#: dotted key to ``pluginload``. ``plugin`` / ``system`` / ``load`` are
#: deliberately *not* bare stems (``plugin`` would false-match ``pluginId``;
#: ``system`` / ``load`` are too generic), so these specific dotted / snake
#: smuggles are matched on their joined normalized form instead. Precise by
#: construction: no allowed descriptor field normalizes to one of these.
_DESCRIPTOR_DANGEROUS_COMPOUNDS: frozenset[str] = frozenset(
    {
        "ossystem",
        "osexec",
        "osspawn",
        "osexit",
        "ossystemcall",
        "pluginload",
        "pluginexec",
        "pluginexecute",
        "pluginrun",
        "plugincall",
        "pluginspawn",
        "pluginimport",
        "subprocesscall",
        "popen",
        "systemcall",
        "importlib",
        "importmodule",
        "loadmodule",
        "dlopen",
    }
)

#: Secret-surface key segments for a descriptor. ``token`` is intentionally
#: singular (``maxTokens`` → ``tokens`` is not matched).
_DESCRIPTOR_SECRET_STEMS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secrets",
        "token",
        "credential",
        "credentials",
        "apikey",
        "privatekey",
        "accesstoken",
        "authtoken",
        "authorization",
    }
)


def _descriptor_key_is_surface(key: Any) -> bool:
    """True if a descriptor key name denotes an execution / secret surface.

    Splits the key on separators and camelCase, then checks single tokens and
    contiguous joins (length 2–3) against the stem sets. ``api_key`` →
    ``apikey``; ``dockerImage`` → ``docker``/``image``; ``pluginId`` →
    ``plugin``/``id`` (not a surface); ``maxTokens`` is not a descriptor key
    concern and resolves to ``tokens`` (not a stem).

    A second pass normalizes the whole key to alnum-only lowercase and matches
    it against :data:`_DESCRIPTOR_DANGEROUS_COMPOUNDS`, so a dotted / snake
    smuggle like an ``os``/``system`` or ``plugin``/``load`` dotted key — whose
    individual tokens are too generic to be stems — is still detected as an
    execution surface.
    """
    if not isinstance(key, str):
        return False
    tokens: list[str] = []
    for part in re.split(r"[^A-Za-z0-9]+", key):
        if not part:
            continue
        sub = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", part)
        tokens.extend(s.lower() for s in (sub or [part.lower()]))
    joins: set[str] = set(tokens)
    n = len(tokens)
    for i in range(n):
        for j in range(i + 2, min(i + 4, n + 1)):
            joins.add("".join(tokens[i:j]))
    if joins & (_DESCRIPTOR_EXEC_STEMS | _DESCRIPTOR_SECRET_STEMS):
        return True
    normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
    if normalized_key and normalized_key in _DESCRIPTOR_DANGEROUS_COMPOUNDS:
        return True
    return False


def _descriptor_has_extended_surface(node: Any) -> bool:
    """Recursive scan for execution/secret-surface keys beyond FORBIDDEN_FIELDS.

    Walks dicts / lists / tuples; a non-dict leaf is harmless. Descriptors are
    JSON-native (acyclic), so no cycle guard is required.
    """
    if isinstance(node, Mapping):
        for key, val in node.items():
            if _descriptor_key_is_surface(key):
                return True
            if _descriptor_has_extended_surface(val):
                return True
    elif isinstance(node, (list, tuple)):
        for item in node:
            if _descriptor_has_extended_surface(item):
                return True
    return False


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
