"""Phase 4A — Target B Readiness disabled scaffold (pure stdlib).

Target B is the *long-term* goal of opening a real production plugin runtime:
signed / arbitrary plugin loading, a remote registry, a marketplace, WebUI
execution, and a production rollout. **Phase 4A implements ONLY the readiness
scaffold** — the frozen architecture models, the disabled interfaces, the
permission / approval gate models, the deny builders, and the tests proving
every dangerous capability stays disabled.

This module is the **backend disabled contract** that a future implementation
phase must satisfy. It is deliberately inert:

  - Pure / deterministic / stdlib-only. No filesystem access, no network, no
    subprocess, no dynamic import, no real secret read, no production access,
    no production home directory access, and no production state database
    access.
  - Every Target B authorization verdict is frozen ``NO-GO``; every capability
    is frozen disabled; every permission is frozen ``DENIED_BY_DEFAULT``; the
    production authorization is frozen ``NO-GO``; ``p0_resolved_count`` stays 0.
  - The deny builders (:func:`deny_target_b_execution_request`,
    :func:`deny_registry_fetch_request`, :func:`deny_marketplace_request`)
    unconditionally return an *allowed/executed/network/marketplace = False*
    result no matter what untrusted metadata is supplied.
  - :func:`validate_plugin_package_shape_without_loading` validates a plugin
    package's *shape* only (does it carry the expected descriptor fields?) — it
    never loads, imports, unpacks, or trusts the package.

This module is **not** imported by ``dev_web_api`` (the read-only WebUI surface
is frontend-only), so it adds **no backend route** and changes **no route
governance counts**.

Phase: 4A — Target B Readiness Scaffold
Status: implemented (disabled scaffold). NOT an authorization, NOT an approval,
        NOT a signoff, NOT a closeout, and NOT production authorization.
        Resolves nothing; enables nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# 0. Self-contained defense-in-depth redactor
#
# The scaffold is deliberately **self-contained**: it imports no other dev_web
# module (so it stays out of the sandbox-safety-family import graph and adds no
# coupling). A tiny local redactor masks any secret-shaped / production-path /
# fake-authorization substring should one ever reach a projected payload — the
# scaffold itself carries no secrets today. Mirrors the conservative spirit of
# the backend redact_sandbox_payload (prefer masking over exposing) without
# depending on it. Pure / total / stdlib-only.
# ---------------------------------------------------------------------------

#: Secret / production-path / fake-authorization stems a redactor masks. These
#: are *patterns* (not real values) — they exist only to scrub a substring.
_REDACT_STEMS: frozenset[str] = frozenset(
    {
        "sk-",
        "bearer ",
        "authorization:",
        "ghp_",
        "xox",
        "begin private key",
        "production home",
        "state database",
        "implementation_authorization=go",
        "implementation authorization = go",
        "openai_api_key",
        "db_password",
        "accesstoken",
        "phase_3i_authorized=true",
        "production_approved=true",
        "route_exception_approved=true",
        "approved_by_ai=true",
        "trust_token=fake",
        "trust_token=",
        "registry_token=fake",
        "registry_token=",
        "plugin_signature=fake-private-key",
        "plugin_signature=",
        "target_b_authorized=true",
        "target_b_authorized=",
        "production_runtime_go=true",
        "production_runtime_go=",
    }
)

#: The mask placeholder emitted by the redactor.
_REDACTED: str = "[REDACTED]"


def _redact_string(value: str) -> str:
    """Mask *value* entirely if it contains any redaction stem. Pure / total."""
    if not isinstance(value, str) or not value:
        return ""
    lowered = value.lower()
    for stem in _REDACT_STEMS:
        if stem in lowered:
            return _REDACTED
    return value


def _redact_payload(payload: Any, *, depth: int = 0) -> Any:
    """Recursively redact secret-shaped strings in *payload*. Pure / total.

    Walks dicts / lists / tuples / strings; leaves every other value untouched.
    Never raises, never reads files or the network.
    """
    if depth > 32:  # depth guard against pathological nesting
        return _REDACTED
    if isinstance(payload, str):
        return _redact_string(payload)
    if isinstance(payload, Mapping):
        return {k: _redact_payload(v, depth=depth + 1) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        redacted = [_redact_payload(v, depth=depth + 1) for v in payload]
        return redacted if isinstance(payload, list) else tuple(redacted)
    return payload

# ---------------------------------------------------------------------------
# 1. Frozen schema / status / verdict constants (cannot be flipped by metadata)
# ---------------------------------------------------------------------------

#: Schema version mirrored by the frontend Target B readiness view-model.
TARGET_B_READINESS_VERSION: str = "phase-4a-target-b-readiness-v1"

#: The frozen Target B readiness status — scaffold drafted, never an enablement.
TARGET_B_READINESS_STATUS: str = "SCAFFOLD_READY"

#: The frozen Target B execution status — always disabled.
TARGET_B_EXECUTION_STATUS: str = "DISABLED"

#: The frozen authorization verdict for every Target B dimension.
TARGET_B_NO_GO: str = "NO-GO"

#: The frozen route-governance baseline (unchanged by this scaffold).
TARGET_B_ROUTE_GOVERNANCE_BASELINE: str = "34/34/5/0/1/1"

#: The frozen P0 totals (resolved_count stays 0).
TARGET_B_P0_TOTAL: int = 24
TARGET_B_P0_RESOLVED: int = 0
TARGET_B_P0_PENDING_HUMAN_REVIEW: int = 5

#: The frozen permission disposition — denied by default, never granted.
TARGET_B_PERMISSION_DENIED: str = "DENIED_BY_DEFAULT"

#: The stable reason token every deny builder returns.
TARGET_B_DISABLED_REASON: str = "target_b_disabled"

#: The stable reason token the registry / marketplace deny builders return.
TARGET_B_REGISTRY_DISABLED_REASON: str = "registry_disabled"
TARGET_B_MARKETPLACE_DISABLED_REASON: str = "marketplace_disabled"

#: The real, out-of-band trust token that would sign a genuine human approval
#: for Target B. It is **deliberately None** in the dev skeleton — it would be
#: provisioned by a separate, auditable human process that is explicitly out of
#: scope. Because it is None, no approval constructed from request metadata —
#: or forged by direct construction — can ever enable Target B.
_REAL_TRUST_TOKEN: str | None = None

# ---------------------------------------------------------------------------
# 2. Frozen plugin permission model (every permission denied by default)
# ---------------------------------------------------------------------------

#: The frozen permission taxonomy — every entry is denied by default.
_PERMISSION_TAXONOMY: tuple[tuple[str, str], ...] = (
    ("filesystem.read", "Filesystem read"),
    ("filesystem.write", "Filesystem write"),
    ("network.http", "Network HTTP"),
    ("network.registry", "Network registry"),
    ("secrets.read", "Secrets read"),
    ("provider.read", "Provider read"),
    ("provider.write", "Provider write"),
    ("ui.render", "UI render"),
    ("tool.invoke", "Tool invoke"),
    ("database.read", "Database read"),
    ("database.write", "Database write"),
    ("process.spawn", "Process spawn"),
)

#: The frozen plugin package SHAPE fields a package descriptor may carry. These
#: are *shape expectations only* — their presence never loads, imports, unpacks,
#: executes, fetches, or trusts a package. Field names are deliberately benign
#: (no module path, no shell command, no install command, no download URL).
_PLUGIN_PACKAGE_SHAPE_FIELDS: tuple[str, ...] = (
    "packageId",
    "version",
    "descriptor",
    "capabilities",
    "permissions",
    "signature",
    "publisher",
    "checksum",
    "sandboxProfile",
    "minimumHermesVersion",
)


@dataclass(frozen=True, slots=True)
class PermissionEntry:
    """One permission in the plugin permission model — always denied."""

    key: str
    label: str
    current_status: str

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "key": self.key,
                "label": self.label,
                "currentStatus": self.current_status,
            }
        )


def _build_permission_entries() -> tuple[PermissionEntry, ...]:
    return tuple(
        PermissionEntry(key=key, label=label, current_status=TARGET_B_PERMISSION_DENIED)
        for key, label in _PERMISSION_TAXONOMY
    )


#: The frozen permission model. Immutable; every permission denied by default.
PERMISSION_MODEL: tuple[PermissionEntry, ...] = _build_permission_entries()

assert len(PERMISSION_MODEL) == 12, "permission model must contain exactly 12 permissions"
assert all(p.current_status == TARGET_B_PERMISSION_DENIED for p in PERMISSION_MODEL)

# ---------------------------------------------------------------------------
# 3. Frozen architecture module board (16 designed / scaffolded-disabled modules)
# ---------------------------------------------------------------------------

#: Lifecycle statuses a Target B architecture module may carry (never enabled).
_MODULE_DESIGNED: str = "DESIGNED"
_MODULE_SCAFFOLDED_DISABLED: str = "SCAFFOLDED_DISABLED"

#: The frozen architecture modules — every one disabled / non-executing /
#: non-networking / non-production / no route. Mirrors the frontend manifest.
_ARCHITECTURE_MODULES_RAW: tuple[tuple[str, str, str, str, str], ...] = (
    # (key, module, status, risk_level, required_gate)
    ("packageFormat", "Plugin Package Format", _MODULE_DESIGNED, "high", "supply-chain policy review (P0-05)"),
    ("signatureVerification", "Plugin Signature Verification", _MODULE_SCAFFOLDED_DISABLED, "critical", "signature verification implementation"),
    ("permissionModel", "Plugin Permission Model", _MODULE_DESIGNED, "high", "permission model approval (P0-06)"),
    ("capabilityDeclaration", "Plugin Capability Declaration", _MODULE_DESIGNED, "medium", "capability review board"),
    ("registryProtocol", "Remote Registry Protocol", _MODULE_SCAFFOLDED_DISABLED, "critical", "registry trust policy + external-network review"),
    ("registryTrustPolicy", "Registry Trust Policy", _MODULE_DESIGNED, "critical", "registry trust policy approval"),
    ("marketplacePolicy", "Marketplace Policy", _MODULE_SCAFFOLDED_DISABLED, "critical", "marketplace trust model + human approval"),
    ("sandboxBoundary", "Runtime Sandbox Boundary", _MODULE_DESIGNED, "critical", "approved sandbox model (P0-01 / P0-19)"),
    ("executionBroker", "Execution Broker", _MODULE_SCAFFOLDED_DISABLED, "critical", "worker lifecycle approval (P0-19)"),
    ("webuiExecutionFlow", "WebUI Execution Request Flow", _MODULE_SCAFFOLDED_DISABLED, "high", "execution-route review + human approval"),
    ("approvalGate", "Approval / Authorization Gate", _MODULE_DESIGNED, "critical", "implementation authorization (P0-15 / P0-22)"),
    ("auditTrail", "Audit Trail", _MODULE_SCAFFOLDED_DISABLED, "medium", "audit / redaction model approval (P0-07)"),
    ("rollbackKillSwitch", "Rollback / Kill Switch", _MODULE_DESIGNED, "high", "rollback / incident plan approval (P0-21 / P0-23)"),
    ("secretHandling", "Secret Handling Boundary", _MODULE_DESIGNED, "critical", "secret handling policy (P0-10)"),
    ("networkPolicy", "Network Policy", _MODULE_SCAFFOLDED_DISABLED, "critical", "external-network allowlist + human approval"),
    ("rolloutPlan", "Production Rollout Plan", _MODULE_DESIGNED, "critical", "production rollout authorization (P0-15)"),
)


@dataclass(frozen=True, slots=True)
class ArchitectureModule:
    """One Target B architecture module — disabled by construction."""

    key: str
    module: str
    status: str
    enabled: bool
    execution_capable: bool
    network_capable: bool
    production_capable: bool
    route_impact: str
    risk_level: str
    required_gate: str

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "key": self.key,
                "module": self.module,
                "status": self.status,
                "enabled": self.enabled,
                "executionCapable": self.execution_capable,
                "networkCapable": self.network_capable,
                "productionCapable": self.production_capable,
                "routeImpact": self.route_impact,
                "riskLevel": self.risk_level,
                "requiredGate": self.required_gate,
            }
        )


def _build_architecture_modules() -> tuple[ArchitectureModule, ...]:
    return tuple(
        ArchitectureModule(
            key=str(row[0]),
            module=str(row[1]),
            status=str(row[2]),
            enabled=False,
            execution_capable=False,
            network_capable=False,
            production_capable=False,
            route_impact="none",
            risk_level=str(row[3]),
            required_gate=str(row[4]),
        )
        for row in _ARCHITECTURE_MODULES_RAW
    )


#: The frozen architecture module board. Immutable; every module disabled.
ARCHITECTURE_MODULES: tuple[ArchitectureModule, ...] = _build_architecture_modules()

assert len(ARCHITECTURE_MODULES) == 16, "architecture board must contain exactly 16 modules"
assert all(
    not m.enabled
    and not m.execution_capable
    and not m.network_capable
    and not m.production_capable
    for m in ARCHITECTURE_MODULES
)

# ---------------------------------------------------------------------------
# 4. Frozen plugin package schema / registry protocol / approval gate previews
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PluginPackageSchema:
    """A fake, static, non-executable plugin package schema preview.

    Every field is a documentation placeholder. No real plugin file is loaded,
    no entrypoint is executed, no registry source is fetched, and no checksum is
    verified. The example registry source uses a reserved ``.invalid`` domain.
    """

    package_id: str
    version: str
    descriptor: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    entrypoints: tuple[str, ...]
    signature: str
    publisher: str
    registry_source: str
    checksum: str
    sandbox_profile: str
    minimum_hermes_version: str
    example_only: bool
    not_loaded: bool
    not_executable: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "packageId": self.package_id,
                "version": self.version,
                "descriptor": self.descriptor,
                "capabilities": list(self.capabilities),
                "permissions": list(self.permissions),
                "entrypoints": list(self.entrypoints),
                "signature": self.signature,
                "publisher": self.publisher,
                "registrySource": self.registry_source,
                "checksum": self.checksum,
                "sandboxProfile": self.sandbox_profile,
                "minimumHermesVersion": self.minimum_hermes_version,
                "exampleOnly": self.example_only,
                "notLoaded": self.not_loaded,
                "notExecutable": self.not_executable,
            }
        )


#: The frozen plugin package schema preview. Fake / static / non-executable.
PLUGIN_PACKAGE_SCHEMA: PluginPackageSchema = PluginPackageSchema(
    package_id="example.plugin.alpha (placeholder)",
    version="0.0.0-placeholder",
    descriptor="descriptor-only preview (no module path)",
    capabilities=("example.capability.read (placeholder)",),
    permissions=("example.permission.read (placeholder)",),
    entrypoints=("entrypoint preview (not executed)",),
    signature="signature_required_not_provided",
    publisher="example publisher (placeholder)",
    registry_source="https://registry.example.invalid",
    checksum="checksum_required_not_provided",
    sandbox_profile="sandbox profile preview (no enforcement)",
    minimum_hermes_version="0.0.0-placeholder",
    example_only=True,
    not_loaded=True,
    not_executable=True,
)


@dataclass(frozen=True, slots=True)
class RegistryProtocolPreview:
    """The frozen remote registry protocol preview.

    The registry URL is a documentation string using a reserved ``.invalid``
    domain — it is NEVER fetched. Network and fetch stay disabled; a signature
    is required; unsigned packages are never allowed; the marketplace stays
    disabled.
    """

    registry_url_example: str
    fetch_enabled: bool
    network_enabled: bool
    trust_policy_required: bool
    signature_required: bool
    allow_unsigned: bool
    marketplace_enabled: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "registryUrlExample": self.registry_url_example,
                "fetchEnabled": self.fetch_enabled,
                "networkEnabled": self.network_enabled,
                "trustPolicyRequired": self.trust_policy_required,
                "signatureRequired": self.signature_required,
                "allowUnsigned": self.allow_unsigned,
                "marketplaceEnabled": self.marketplace_enabled,
            }
        )


#: The frozen registry protocol preview. Disabled / never fetched.
REGISTRY_PROTOCOL: RegistryProtocolPreview = RegistryProtocolPreview(
    registry_url_example="https://registry.example.invalid",
    fetch_enabled=False,
    network_enabled=False,
    trust_policy_required=True,
    signature_required=True,
    allow_unsigned=False,
    marketplace_enabled=False,
)


@dataclass(frozen=True, slots=True)
class ApprovalGateProjection:
    """The frozen approval / authorization gate projection.

    Human approval is required; no trust token is provisioned; fake / AI /
    metadata approval is rejected. Production authorization stays NO-GO.
    """

    human_approval_required: bool
    trust_token_provisioned: bool
    fake_approval_accepted: bool
    ai_approval_accepted: bool
    metadata_approval_accepted: bool
    production_authorization: str

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "humanApprovalRequired": self.human_approval_required,
                "trustTokenProvisioned": self.trust_token_provisioned,
                "fakeApprovalAccepted": self.fake_approval_accepted,
                "aiApprovalAccepted": self.ai_approval_accepted,
                "metadataApprovalAccepted": self.metadata_approval_accepted,
                "productionAuthorization": self.production_authorization,
            }
        )


#: The frozen approval gate projection. No trust token; metadata cannot approve.
APPROVAL_GATE: ApprovalGateProjection = ApprovalGateProjection(
    human_approval_required=True,
    trust_token_provisioned=False,
    fake_approval_accepted=False,
    ai_approval_accepted=False,
    metadata_approval_accepted=False,
    production_authorization=TARGET_B_NO_GO,
)


# ---------------------------------------------------------------------------
# 5. Untrusted-metadata detection (bypass prevention)
# ---------------------------------------------------------------------------

#: Metadata keys that look like a Target B authorization bypass attempt.
#: Detected and ignored by every public deny builder. The list is intentionally
#: broad: every approval / authorization / trust-token / registry / marketplace
#: / production / runtime / resolved variant a smuggler might invent is reported
#: as ignored. Detection is diagnostic only — the authorization flags are frozen
#: constants regardless, so an undetected variant still authorizes nothing.
_UNTRUSTED_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "approved",
        "approve",
        "authorization",
        "authorized",
        "authorised",
        "implementation_authorization",
        "implementationAuthorization",
        "trust_token",
        "trustToken",
        "real_trust_token",
        "realTrustToken",
        "target_b_authorized",
        "targetBAuthorized",
        "production_approved",
        "productionApproved",
        "production_runtime_go",
        "productionRuntimeGo",
        "production_rollout_approved",
        "productionRolloutApproved",
        "registry_token",
        "registryToken",
        "registry_authorized",
        "registryAuthorized",
        "marketplace_authorized",
        "marketplaceAuthorized",
        "plugin_signature",
        "pluginSignature",
        "signed",
        "signature",
        "bypass",
        "override",
        "force",
        "force_allow",
        "forceAllow",
        "skip_review",
        "p0_resolved",
        "p0Resolved",
        "resolved",
        "approved_by_ai",
        "approvedByAi",
        "approved_by_human",
        "approvedByHuman",
        "token",
        "secret",
        "password",
        "apikey",
        "api_key",
    }
)


def detect_untrusted_metadata(metadata: Any) -> tuple[str, ...]:
    """Return the sorted bypass-shaped keys present in *metadata*.

    Pure inspection — the keys are reported so a caller/audit can record that a
    bypass attempt was detected and ignored. Never raises.
    """
    if not isinstance(metadata, Mapping):
        return ()
    found: set[str] = set()
    for key in metadata.keys():
        if not isinstance(key, str):
            continue
        if key in _UNTRUSTED_METADATA_KEYS:
            found.add(key)
        else:
            normalized = key.strip().lower().replace("-", "_")
            if normalized in _UNTRUSTED_METADATA_KEYS:
                found.add(key)
    return tuple(sorted(found))


# ---------------------------------------------------------------------------
# 6. Deny builders (every dangerous capability stays disabled)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DenialResult:
    """The frozen result every deny builder returns. Always denied.

    ``allowed`` / ``executed`` / ``network`` / ``fetched`` / ``marketplace`` are
    False; ``production_authorization`` is NO-GO; ``p0_resolved_count`` is 0 no
    matter what untrusted metadata is supplied.
    """

    allowed: bool
    executed: bool
    network: bool
    fetched: bool
    marketplace: bool
    reason: str
    production_authorization: str
    p0_resolved_count: int
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "allowed": self.allowed,
                "executed": self.executed,
                "network": self.network,
                "fetched": self.fetched,
                "marketplace": self.marketplace,
                "reason": self.reason,
                "productionAuthorization": self.production_authorization,
                "p0ResolvedCount": self.p0_resolved_count,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


def deny_target_b_execution_request(untrusted_metadata: Any = None) -> DenialResult:
    """Deny a Target B execution request. Always allowed=False, executed=False.

    *untrusted_metadata* is inspected only to report which bypass-shaped keys
    were detected and ignored; it cannot flip any flag. No plugin is executed,
    no runtime is started, and no production authorization is granted.
    """
    ignored = detect_untrusted_metadata(untrusted_metadata)
    return DenialResult(
        allowed=False,
        executed=False,
        network=False,
        fetched=False,
        marketplace=False,
        reason=TARGET_B_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        p0_resolved_count=TARGET_B_P0_RESOLVED,
        ignored_metadata_keys=ignored,
    )


def deny_registry_fetch_request(untrusted_metadata: Any = None) -> DenialResult:
    """Deny a remote registry fetch request. Always network=False, fetched=False.

    The registry is never contacted; no external network is opened; no listing
    is fetched. *untrusted_metadata* is inspected only to report ignored keys.
    """
    ignored = detect_untrusted_metadata(untrusted_metadata)
    return DenialResult(
        allowed=False,
        executed=False,
        network=False,
        fetched=False,
        marketplace=False,
        reason=TARGET_B_REGISTRY_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        p0_resolved_count=TARGET_B_P0_RESOLVED,
        ignored_metadata_keys=ignored,
    )


def deny_marketplace_request(untrusted_metadata: Any = None) -> DenialResult:
    """Deny a marketplace request. Always marketplace=False.

    The marketplace is never reachable; no listing is fetched; no install is
    performed. *untrusted_metadata* is inspected only to report ignored keys.
    """
    ignored = detect_untrusted_metadata(untrusted_metadata)
    return DenialResult(
        allowed=False,
        executed=False,
        network=False,
        fetched=False,
        marketplace=False,
        reason=TARGET_B_MARKETPLACE_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        p0_resolved_count=TARGET_B_P0_RESOLVED,
        ignored_metadata_keys=ignored,
    )


# ---------------------------------------------------------------------------
# 7. Plugin package SHAPE validator (never loads / imports / executes / trusts)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PackageShapeValidation:
    """The result of :func:`validate_plugin_package_shape_without_loading`.

    Reports whether a package mapping carries the expected descriptor SHAPE
    fields. ``shape_ok`` is True only when every required field is present; the
    validator never loads, imports, unpacks, executes, fetches, or trusts the
    package, and ``execution_trusted`` is always False.
    """

    shape_ok: bool
    missing_fields: tuple[str, ...]
    execution_trusted: bool
    reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "shapeOk": self.shape_ok,
                "missingFields": list(self.missing_fields),
                "executionTrusted": self.execution_trusted,
                "reasons": list(self.reasons),
            }
        )


def validate_plugin_package_shape_without_loading(package: Any) -> PackageShapeValidation:
    """Validate a plugin package's *shape* only — never load it.

    Returns a :class:`PackageShapeValidation` reporting which expected descriptor
    fields are present. **No file is opened, no module is imported, no entrypoint
    is executed, no registry source is fetched, and no checksum is verified.**
    A package with a valid shape is *not* trusted for execution —
    ``execution_trusted`` is always False.
    """
    if not isinstance(package, Mapping):
        return PackageShapeValidation(
            shape_ok=False,
            missing_fields=tuple(_PLUGIN_PACKAGE_SHAPE_FIELDS),
            execution_trusted=False,
            reasons=("package_not_a_mapping",),
        )
    present: set[str] = set()
    for key in package.keys():
        if isinstance(key, str):
            present.add(key)
    missing = tuple(field for field in _PLUGIN_PACKAGE_SHAPE_FIELDS if field not in present)
    reasons: list[str] = []
    if missing:
        reasons.append("shape_fields_missing")
    else:
        reasons.append("shape_fields_present_no_trust")
    return PackageShapeValidation(
        shape_ok=not missing,
        missing_fields=missing,
        execution_trusted=False,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 8. Target B readiness report (the disabled aggregate)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetBReadinessReport:
    """The frozen, disabled Target B readiness report.

    Every authorization verdict is NO-GO; execution is DISABLED; production
    authorization is NO-GO; ``p0_resolved_count`` is 0; the route baseline is
    unchanged; and the architecture / permission / schema / registry / approval
    projections are all frozen disabled. No field implies enablement.
    """

    schema_version: str
    readiness_status: str
    execution_status: str
    production_runtime: str
    arbitrary_plugin_loading: str
    remote_registry: str
    marketplace: str
    webui_execution: str
    approval_authorization: str
    production_rollout: str
    p0_total: int
    p0_resolved: int
    p0_pending_human_review: int
    route_governance_baseline: str
    backend_routes_changed: bool
    permission_model: tuple[PermissionEntry, ...]
    architecture_modules: tuple[ArchitectureModule, ...]
    plugin_package_schema: PluginPackageSchema
    registry_protocol: RegistryProtocolPreview
    approval_gate: ApprovalGateProjection

    def to_safe_dict(self) -> dict[str, Any]:
        return _redact_payload(
            {
                "schemaVersion": self.schema_version,
                "readinessStatus": self.readiness_status,
                "executionStatus": self.execution_status,
                "productionRuntime": self.production_runtime,
                "arbitraryPluginLoading": self.arbitrary_plugin_loading,
                "remoteRegistry": self.remote_registry,
                "marketplace": self.marketplace,
                "webuiExecution": self.webui_execution,
                "approvalAuthorization": self.approval_authorization,
                "productionRollout": self.production_rollout,
                "p0Total": self.p0_total,
                "p0Resolved": self.p0_resolved,
                "p0PendingHumanReview": self.p0_pending_human_review,
                "routeGovernanceBaseline": self.route_governance_baseline,
                "backendRoutesChanged": self.backend_routes_changed,
                "permissionModel": [p.to_safe_dict() for p in self.permission_model],
                "architectureModules": [m.to_safe_dict() for m in self.architecture_modules],
                "pluginPackageSchema": self.plugin_package_schema.to_safe_dict(),
                "registryProtocol": self.registry_protocol.to_safe_dict(),
                "approvalGate": self.approval_gate.to_safe_dict(),
            }
        )


def build_target_b_readiness_report() -> TargetBReadinessReport:
    """Build the frozen, disabled Target B readiness report.

    Every authorization verdict is NO-GO; execution is DISABLED;
    ``p0_resolved`` is 0; the route baseline is unchanged; and every capability
    is disabled. Pure and deterministic — no time, no random, no network, no
    file, no production access.
    """
    return TargetBReadinessReport(
        schema_version=TARGET_B_READINESS_VERSION,
        readiness_status=TARGET_B_READINESS_STATUS,
        execution_status=TARGET_B_EXECUTION_STATUS,
        production_runtime=TARGET_B_NO_GO,
        arbitrary_plugin_loading=TARGET_B_NO_GO,
        remote_registry=TARGET_B_NO_GO,
        marketplace=TARGET_B_NO_GO,
        webui_execution=TARGET_B_NO_GO,
        approval_authorization=TARGET_B_NO_GO,
        production_rollout=TARGET_B_NO_GO,
        p0_total=TARGET_B_P0_TOTAL,
        p0_resolved=TARGET_B_P0_RESOLVED,
        p0_pending_human_review=TARGET_B_P0_PENDING_HUMAN_REVIEW,
        route_governance_baseline=TARGET_B_ROUTE_GOVERNANCE_BASELINE,
        backend_routes_changed=False,
        permission_model=PERMISSION_MODEL,
        architecture_modules=ARCHITECTURE_MODULES,
        plugin_package_schema=PLUGIN_PACKAGE_SCHEMA,
        registry_protocol=REGISTRY_PROTOCOL,
        approval_gate=APPROVAL_GATE,
    )


# ---------------------------------------------------------------------------
# 9. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

NO_TARGET_B_RUNTIME: bool = True
NO_TARGET_B_EXECUTION: bool = True
NO_TARGET_B_PLUGIN_LOADING: bool = True
NO_TARGET_B_REGISTRY_FETCH: bool = True
NO_TARGET_B_MARKETPLACE: bool = True
NO_TARGET_B_EXTERNAL_NETWORK: bool = True
NO_TARGET_B_REAL_SECRET_READ: bool = True
NO_TARGET_B_PRODUCTION_ACCESS: bool = True
NO_TARGET_B_NEW_ROUTE: bool = True
NO_TARGET_B_TRUST_TOKEN: bool = True


def assert_target_b_disabled() -> None:
    """Re-affirm the Target B disabled-scaffold invariants.

    Raises ``AssertionError`` if any invariant has drifted. Pure — never touches
    the filesystem, the network, or production.
    """
    assert NO_TARGET_B_RUNTIME is True
    assert NO_TARGET_B_EXECUTION is True
    assert NO_TARGET_B_PLUGIN_LOADING is True
    assert NO_TARGET_B_REGISTRY_FETCH is True
    assert NO_TARGET_B_MARKETPLACE is True
    assert NO_TARGET_B_EXTERNAL_NETWORK is True
    assert NO_TARGET_B_REAL_SECRET_READ is True
    assert NO_TARGET_B_PRODUCTION_ACCESS is True
    assert NO_TARGET_B_NEW_ROUTE is True
    assert NO_TARGET_B_TRUST_TOKEN is True
    assert _REAL_TRUST_TOKEN is None, "Target B scaffold must hold no trust token"
    assert TARGET_B_EXECUTION_STATUS == "DISABLED"
    assert TARGET_B_P0_RESOLVED == 0
    report = build_target_b_readiness_report()
    assert report.execution_status == "DISABLED"
    assert report.production_runtime == "NO-GO"
    assert report.remote_registry == "NO-GO"
    assert report.marketplace == "NO-GO"
    assert report.webui_execution == "NO-GO"
    assert report.approval_authorization == "NO-GO"
    assert report.production_rollout == "NO-GO"
    assert report.p0_resolved == 0
    assert report.backend_routes_changed is False
    assert all(not m.enabled for m in report.architecture_modules)
    assert all(p.current_status == TARGET_B_PERMISSION_DENIED for p in report.permission_model)
    assert report.approval_gate.trust_token_provisioned is False


__all__ = [
    # constants
    "TARGET_B_READINESS_VERSION",
    "TARGET_B_READINESS_STATUS",
    "TARGET_B_EXECUTION_STATUS",
    "TARGET_B_NO_GO",
    "TARGET_B_ROUTE_GOVERNANCE_BASELINE",
    "TARGET_B_P0_TOTAL",
    "TARGET_B_P0_RESOLVED",
    "TARGET_B_P0_PENDING_HUMAN_REVIEW",
    "TARGET_B_PERMISSION_DENIED",
    "TARGET_B_DISABLED_REASON",
    "TARGET_B_REGISTRY_DISABLED_REASON",
    "TARGET_B_MARKETPLACE_DISABLED_REASON",
    # models
    "PermissionEntry",
    "PERMISSION_MODEL",
    "ArchitectureModule",
    "ARCHITECTURE_MODULES",
    "PluginPackageSchema",
    "PLUGIN_PACKAGE_SCHEMA",
    "RegistryProtocolPreview",
    "REGISTRY_PROTOCOL",
    "ApprovalGateProjection",
    "APPROVAL_GATE",
    # metadata detection
    "detect_untrusted_metadata",
    # deny builders
    "DenialResult",
    "deny_target_b_execution_request",
    "deny_registry_fetch_request",
    "deny_marketplace_request",
    # shape validator
    "PackageShapeValidation",
    "validate_plugin_package_shape_without_loading",
    # report
    "TargetBReadinessReport",
    "build_target_b_readiness_report",
    # boundary
    "NO_TARGET_B_RUNTIME",
    "NO_TARGET_B_EXECUTION",
    "NO_TARGET_B_PLUGIN_LOADING",
    "NO_TARGET_B_REGISTRY_FETCH",
    "NO_TARGET_B_MARKETPLACE",
    "NO_TARGET_B_EXTERNAL_NETWORK",
    "NO_TARGET_B_REAL_SECRET_READ",
    "NO_TARGET_B_PRODUCTION_ACCESS",
    "NO_TARGET_B_NEW_ROUTE",
    "NO_TARGET_B_TRUST_TOKEN",
    "assert_target_b_disabled",
]
