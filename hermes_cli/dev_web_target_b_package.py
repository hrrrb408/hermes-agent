"""Phase 4B — Target B Signed Plugin Package schema layer (pure stdlib).

Layer 1+2 of the Phase 4B Target B engineering path. Defines the **signed
plugin package** schema and a battery of *shape* validators. Every validator
inspects metadata only — it **never loads, imports, unpacks, executes, fetches,
or trusts** a package.

A package is described by a plain mapping (the descriptor). The validators
report whether the descriptor carries the expected SHAPE fields, whether the
identity / version / permission / capability / entrypoint / checksum /
signature metadata is *well-formed*, and whether the package is *loadable* /
*executable* / *trusted*. The defaults are fail-closed:

  - ``valid`` is True only when every shape + format rule passes;
  - ``trusted`` is **always False** — shape validation never grants trust;
  - ``loadable`` is **always False** — no package is ever loaded;
  - ``executable`` is **always False** — no package is ever executed.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_REGISTRY_EXAMPLE_DOMAIN,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen schema fields + format rules
# ---------------------------------------------------------------------------

#: The signed plugin package descriptor SHAPE fields. Presence never loads,
#: imports, unpacks, executes, fetches, or trusts a package. Field names are
#: deliberately benign (no module path, no shell command, no install command,
#: no download URL).
PACKAGE_SHAPE_FIELDS: tuple[str, ...] = (
    "package_id",
    "package_name",
    "version",
    "publisher",
    "manifest_version",
    "hermes_min_version",
    "descriptor",
    "capabilities",
    "permissions",
    "entrypoints",
    "checksum",
    "signature",
    "signature_algorithm",
    "registry_source",
    "sandbox_profile",
    "created_at",
    "review_metadata",
)

#: Allowed signature algorithm identifiers (well-formed names only — never a
#: trust decision). The deterministic fixture verifier accepts the
#: ``fixture-hmac-sha256`` algorithm in tests only.
SIGNATURE_ALGORITHMS: frozenset[str] = frozenset(
    {
        "ed25519",
        "ecdsa-p256-sha256",
        "rsa-pss-sha256",
        "fixture-hmac-sha256",
    }
)

#: Allowed manifest versions (well-formed names only).
MANIFEST_VERSIONS: frozenset[str] = frozenset(
    {
        "1",
        "1.0",
    }
)

#: Allowed checksum algorithms (prefix of a well-formed checksum field).
CHECKSUM_ALGORITHMS: frozenset[str] = frozenset(
    {
        "sha256",
        "sha512",
        "blake2b",
    }
)

#: A well-formed package id: lowercase ascii letters / digits / ``.`` / ``-`` /
#: ``_``, dotted segments, 1..128 chars.
_PACKAGE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

#: A well-formed semver-ish version: ``MAJOR.MINOR.PATCH`` (+ optional
#: ``-prerelease`` / ``+build``), ascii digits.
_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(-[0-9a-z.-]+)?(\+[0-9a-z.-]+)?$"
)

#: A well-formed checksum: ``<algo>:<hex>`` where hex is 32..128 lowercase hex
#: chars (the algorithm prefix is checked against :data:`CHECKSUM_ALGORITHMS`).
_CHECKSUM_RE = re.compile(r"^(sha256|sha512|blake2b):[0-9a-f]{32,128}$")

#: A well-formed publisher id (same shape rules as a package id).
_PUBLISHER_RE = _PACKAGE_ID_RE

#: A well-formed signature: ``<algo>:<base64-or-hex>`` — at least 16 payload
#: chars. This validates *shape only* — it never verifies the signature.
_SIGNATURE_RE = re.compile(r"^[a-z0-9-]+:[A-Za-z0-9+/=_-]{16,4096}$")

#: Entrypoint declaration shape. Entrypoints are **declarations only** — they
#: are never imported, never resolved, never executed. A well-formed entrypoint
#: is a ``kind:name`` pair where ``kind`` is a benign declaration verb.
_ENTRYPOINT_KINDS: frozenset[str] = frozenset(
    {
        "tool",
        "provider",
        "capability",
    }
)
_ENTRYPOINT_RE = re.compile(r"^(tool|provider|capability):[a-z0-9][a-z0-9._-]{0,63}$")


def _is_str_list(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value)


# ---------------------------------------------------------------------------
# 2. Frozen permission / capability taxonomies (cross-checked here for shape)
# ---------------------------------------------------------------------------

#: The full plugin permission taxonomy used by the implementation layers. Every
#: entry is denied by default (see dev_web_target_b_permissions.py).
PACKAGE_PERMISSION_TAXONOMY: tuple[str, ...] = (
    "filesystem.read",
    "filesystem.write",
    "network.http",
    "network.registry",
    "secrets.read",
    "provider.read",
    "provider.write",
    "ui.render",
    "tool.invoke",
    "database.read",
    "database.write",
    "process.spawn",
    "runtime.execute",
    "plugin.install",
    "marketplace.fetch",
)

#: The capability declaration taxonomy. Capabilities are metadata only — they
#: grant nothing at runtime.
PACKAGE_CAPABILITY_TAXONOMY: tuple[str, ...] = (
    "display.surface",
    "display.toolbar",
    "display.status",
    "read.descriptor",
    "read.capability",
    "event.emit.readonly",
)

#: Capabilities that imply execution / network / filesystem / secret access are
#: NOT allowed as a pure display / metadata capability.
_DISALLOWED_CAPABILITY_STEMS: frozenset[str] = frozenset(
    {
        "execute",
        "spawn",
        "network",
        "filesystem",
        "secret",
        "install",
        "fetch",
        "write",
        "process",
        "shell",
        "import",
        "dynamic",
    }
)

_ALLOWED_PERMISSION_SET: frozenset[str] = frozenset(PACKAGE_PERMISSION_TAXONOMY)
_ALLOWED_CAPABILITY_SET: frozenset[str] = frozenset(PACKAGE_CAPABILITY_TAXONOMY)


# ---------------------------------------------------------------------------
# 3. The package descriptor projection + the per-concern validators
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PluginPackageDescriptor:
    """A read-only projection of a signed plugin package descriptor.

    Every field is documentation metadata only. No file is opened, no module is
    imported, no entrypoint is executed, no registry source is fetched, and no
    checksum or signature is verified. ``example_only`` / ``not_loaded`` /
    ``not_executable`` are frozen True.
    """

    package_id: str
    package_name: str
    version: str
    publisher: str
    manifest_version: str
    hermes_min_version: str
    descriptor: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    entrypoints: tuple[str, ...]
    checksum: str
    signature: str
    signature_algorithm: str
    registry_source: str
    sandbox_profile: str
    created_at: str
    review_metadata: tuple[str, ...]
    example_only: bool
    not_loaded: bool
    not_executable: bool

    def to_raw_descriptor(self) -> dict[str, Any]:
        """Return the canonical snake_case raw descriptor mapping.

        This is the shape a package author would supply and that the package
        validators operate on. It is **never loaded, imported, or executed** —
        it is plain metadata. A defensive copy is returned.
        """
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "version": self.version,
            "publisher": self.publisher,
            "manifest_version": self.manifest_version,
            "hermes_min_version": self.hermes_min_version,
            "descriptor": self.descriptor,
            "capabilities": list(self.capabilities),
            "permissions": list(self.permissions),
            "entrypoints": list(self.entrypoints),
            "checksum": self.checksum,
            "signature": self.signature,
            "signature_algorithm": self.signature_algorithm,
            "registry_source": self.registry_source,
            "sandbox_profile": self.sandbox_profile,
            "created_at": self.created_at,
            "review_metadata": list(self.review_metadata),
        }

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "packageId": self.package_id,
                "packageName": self.package_name,
                "version": self.version,
                "publisher": self.publisher,
                "manifestVersion": self.manifest_version,
                "hermesMinVersion": self.hermes_min_version,
                "descriptor": self.descriptor,
                "capabilities": list(self.capabilities),
                "permissions": list(self.permissions),
                "entrypoints": list(self.entrypoints),
                "checksum": self.checksum,
                "signature": self.signature,
                "signatureAlgorithm": self.signature_algorithm,
                "registrySource": self.registry_source,
                "sandboxProfile": self.sandbox_profile,
                "createdAt": self.created_at,
                "reviewMetadata": list(self.review_metadata),
                "exampleOnly": self.example_only,
                "notLoaded": self.not_loaded,
                "notExecutable": self.not_executable,
            }
        )


@dataclass(frozen=True, slots=True)
class PackageValidation:
    """The aggregate result of :func:`validate_plugin_package_without_loading`.

    Reports whether a package descriptor is *valid* (shape + format) and —
    independently — whether it is *trusted* / *loadable* / *executable*.
    ``trusted`` / ``loadable`` / ``executable`` are **always False**: shape
    validation grants no trust and triggers no loading or execution.
    """

    valid: bool
    trusted: bool
    loadable: bool
    executable: bool
    shape_ok: bool
    identity_ok: bool
    permissions_ok: bool
    capabilities_ok: bool
    entrypoints_ok: bool
    checksum_ok: bool
    signature_ok: bool
    reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "valid": self.valid,
                "trusted": self.trusted,
                "loadable": self.loadable,
                "executable": self.executable,
                "shapeOk": self.shape_ok,
                "identityOk": self.identity_ok,
                "permissionsOk": self.permissions_ok,
                "capabilitiesOk": self.capabilities_ok,
                "entrypointsOk": self.entrypoints_ok,
                "checksumOk": self.checksum_ok,
                "signatureOk": self.signature_ok,
                "reasons": list(self.reasons),
            }
        )


def validate_plugin_package_shape(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate that *package* carries every expected descriptor SHAPE field.

    Returns ``(shape_ok, missing_fields)``. **No file is opened, no module is
    imported, no entrypoint is executed, no registry source is fetched, and no
    checksum or signature is verified.**
    """
    if not isinstance(package, Mapping):
        return False, tuple(PACKAGE_SHAPE_FIELDS)
    present = {k for k in package.keys() if isinstance(k, str)}
    missing = tuple(f for f in PACKAGE_SHAPE_FIELDS if f not in present)
    return not missing, missing


def validate_plugin_package_identity(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate the package id / version / publisher / manifest format.

    Returns ``(identity_ok, reasons)``. Pure format checks only.
    """
    if not isinstance(package, Mapping):
        return False, ("package_not_a_mapping",)
    reasons: list[str] = []
    pid = package.get("package_id")
    if not isinstance(pid, str) or not _PACKAGE_ID_RE.match(pid):
        reasons.append("package_id_malformed")
    name = package.get("package_name")
    if not isinstance(name, str) or not name.strip():
        reasons.append("package_name_missing")
    version = package.get("version")
    if not isinstance(version, str) or not _SEMVER_RE.match(version):
        reasons.append("version_malformed")
    publisher = package.get("publisher")
    if not isinstance(publisher, str) or not _PUBLISHER_RE.match(publisher):
        reasons.append("publisher_malformed")
    manifest = package.get("manifest_version")
    if manifest not in MANIFEST_VERSIONS:
        reasons.append("manifest_version_unknown")
    hermes_min = package.get("hermes_min_version")
    if not isinstance(hermes_min, str) or not _SEMVER_RE.match(hermes_min):
        reasons.append("hermes_min_version_malformed")
    return not reasons, tuple(reasons)


def validate_plugin_package_permissions(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate that every declared permission is in the allowed taxonomy.

    Returns ``(permissions_ok, reasons)``. Shape only — this **never grants**
    a permission. The permission model itself (every permission denied by
    default) lives in :mod:`dev_web_target_b_permissions`.
    """
    if not isinstance(package, Mapping):
        return False, ("package_not_a_mapping",)
    perms = package.get("permissions")
    if not _is_str_list(perms):
        return False, ("permissions_not_a_string_list",)
    reasons: list[str] = []
    for p in perms:
        if p not in _ALLOWED_PERMISSION_SET:
            reasons.append(f"permission_not_allowed:{p}")
    return not reasons, tuple(reasons)


def validate_plugin_package_capabilities(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate that every declared capability is a benign display/metadata one.

    Returns ``(capabilities_ok, reasons)``. A capability implying execution /
    network / filesystem / secret / install / fetch access is rejected — even
    though capabilities grant nothing at runtime, they must not smuggle an
    executable capability through the declaration surface.
    """
    if not isinstance(package, Mapping):
        return False, ("package_not_a_mapping",)
    caps = package.get("capabilities")
    if not _is_str_list(caps):
        return False, ("capabilities_not_a_string_list",)
    reasons: list[str] = []
    for c in caps:
        if c not in _ALLOWED_CAPABILITY_SET:
            reasons.append(f"capability_not_allowed:{c}")
            continue
        lowered = c.lower()
        if any(stem in lowered for stem in _DISALLOWED_CAPABILITY_STEMS):
            reasons.append(f"capability_implies_side_effect:{c}")
    return not reasons, tuple(reasons)


def validate_plugin_package_entrypoints(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate that every entrypoint is a *declaration* only — never executed.

    Returns ``(entrypoints_ok, reasons)``. Each entrypoint must match a
    ``kind:name`` declaration shape. This **never imports, resolves, or
    executes** an entrypoint.
    """
    if not isinstance(package, Mapping):
        return False, ("package_not_a_mapping",)
    eps = package.get("entrypoints")
    if not _is_str_list(eps):
        return False, ("entrypoints_not_a_string_list",)
    reasons: list[str] = []
    for ep in eps:
        if not _ENTRYPOINT_RE.match(ep):
            reasons.append(f"entrypoint_malformed:{ep}")
    return not reasons, tuple(reasons)


def validate_plugin_package_checksum_metadata(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate the *format* of the checksum field — never verify the checksum.

    Returns ``(checksum_ok, reasons)``. The checksum must be a well-formed
    ``<algo>:<hex>`` string. **No file is read and no hash is computed.**
    """
    if not isinstance(package, Mapping):
        return False, ("package_not_a_mapping",)
    checksum = package.get("checksum")
    if not isinstance(checksum, str) or not _CHECKSUM_RE.match(checksum):
        return False, ("checksum_malformed",)
    return True, ()


def validate_plugin_package_signature_metadata(package: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate the *format* of the signature fields — never trust the signature.

    Returns ``(signature_ok, reasons)``. The signature must be a well-formed
    ``<algo>:<payload>`` string and the algorithm must be a known identifier.
    **This never verifies the signature** — see
    :mod:`dev_web_target_b_signature`.
    """
    if not isinstance(package, Mapping):
        return False, ("package_not_a_mapping",)
    reasons: list[str] = []
    signature = package.get("signature")
    if not isinstance(signature, str) or not _SIGNATURE_RE.match(signature):
        reasons.append("signature_malformed")
    algorithm = package.get("signature_algorithm")
    if algorithm not in SIGNATURE_ALGORITHMS:
        reasons.append("signature_algorithm_unknown")
    return not reasons, tuple(reasons)


def validate_plugin_package_without_loading(package: Any) -> PackageValidation:
    """Validate a plugin package descriptor's shape + format — never load it.

    Runs every per-concern validator and aggregates the result. ``valid`` is
    True only when every check passes. ``trusted`` / ``loadable`` /
    ``executable`` are **always False**: shape validation grants no trust,
    triggers no loading, and performs no execution.

    **No file is opened, no module is imported, no entrypoint is executed, no
    registry source is fetched, no checksum is computed, and no signature is
    verified.**
    """
    shape_ok, _missing = validate_plugin_package_shape(package)
    identity_ok, _id_reasons = validate_plugin_package_identity(package)
    permissions_ok, _perm_reasons = validate_plugin_package_permissions(package)
    capabilities_ok, _cap_reasons = validate_plugin_package_capabilities(package)
    entrypoints_ok, _ep_reasons = validate_plugin_package_entrypoints(package)
    checksum_ok, _cs_reasons = validate_plugin_package_checksum_metadata(package)
    signature_ok, _sig_reasons = validate_plugin_package_signature_metadata(package)
    reasons: list[str] = []
    if not shape_ok:
        reasons.append("shape_fields_missing")
    if not identity_ok:
        reasons.append("identity_format_invalid")
    if not permissions_ok:
        reasons.append("permissions_outside_taxonomy")
    if not capabilities_ok:
        reasons.append("capabilities_outside_taxonomy")
    if not entrypoints_ok:
        reasons.append("entrypoints_declaration_invalid")
    if not checksum_ok:
        reasons.append("checksum_format_invalid")
    if not signature_ok:
        reasons.append("signature_format_invalid")
    if reasons:
        reasons.append("shape_validation_grants_no_trust")
    else:
        reasons.append("shape_and_format_valid_no_trust")
    valid = (
        shape_ok
        and identity_ok
        and permissions_ok
        and capabilities_ok
        and entrypoints_ok
        and checksum_ok
        and signature_ok
    )
    return PackageValidation(
        valid=valid,
        # Frozen: shape validation never grants trust / loading / execution.
        trusted=False,
        loadable=False,
        executable=False,
        shape_ok=shape_ok,
        identity_ok=identity_ok,
        permissions_ok=permissions_ok,
        capabilities_ok=capabilities_ok,
        entrypoints_ok=entrypoints_ok,
        checksum_ok=checksum_ok,
        signature_ok=signature_ok,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 4. A frozen, fake, static, non-executable example descriptor
# ---------------------------------------------------------------------------


def build_example_package_descriptor() -> PluginPackageDescriptor:
    """Build the frozen, fake, static, non-executable example package descriptor.

    Every value is a documentation placeholder. No real plugin file is loaded,
    no entrypoint is executed, no registry source is fetched, and no checksum or
    signature is verified. The example registry source uses a reserved
    ``.invalid`` domain.
    """
    return PluginPackageDescriptor(
        package_id="example.plugin.alpha",
        package_name="Example Plugin Alpha (placeholder)",
        version="0.1.0",
        publisher="example.publisher",
        manifest_version="1.0",
        hermes_min_version="0.0.0",
        descriptor="descriptor-only preview (no module path)",
        capabilities=("display.surface", "read.capability"),
        permissions=("filesystem.read",),
        entrypoints=("tool:example.tool.alpha",),
        checksum="sha256:" + "0" * 64,
        signature="fixture-hmac-sha256:" + "A" * 64,
        signature_algorithm="fixture-hmac-sha256",
        registry_source=TARGET_B_REGISTRY_EXAMPLE_DOMAIN,
        sandbox_profile="sandbox profile preview (no enforcement)",
        created_at="1970-01-01T00:00:00Z",
        review_metadata=("review_metadata_preview_no_decision",),
        example_only=True,
        not_loaded=True,
        not_executable=True,
    )


def assert_package_layer_disabled() -> None:
    """Re-affirm the package layer disabled invariants. Pure."""
    example = build_example_package_descriptor()
    assert example.example_only is True
    assert example.not_loaded is True
    assert example.not_executable is True
    assert example.registry_source == TARGET_B_REGISTRY_EXAMPLE_DOMAIN
    # A perfectly-shaped example descriptor is valid but NOT trusted / loadable
    # / executable.
    result = validate_plugin_package_without_loading(example.to_raw_descriptor())
    assert result.valid is True
    assert result.trusted is False
    assert result.loadable is False
    assert result.executable is False


__all__ = [
    # schema
    "PACKAGE_SHAPE_FIELDS",
    "SIGNATURE_ALGORITHMS",
    "MANIFEST_VERSIONS",
    "CHECKSUM_ALGORITHMS",
    "PACKAGE_PERMISSION_TAXONOMY",
    "PACKAGE_CAPABILITY_TAXONOMY",
    # models
    "PluginPackageDescriptor",
    "PackageValidation",
    # validators
    "validate_plugin_package_shape",
    "validate_plugin_package_identity",
    "validate_plugin_package_permissions",
    "validate_plugin_package_capabilities",
    "validate_plugin_package_entrypoints",
    "validate_plugin_package_checksum_metadata",
    "validate_plugin_package_signature_metadata",
    "validate_plugin_package_without_loading",
    # example + boundary
    "build_example_package_descriptor",
    "assert_package_layer_disabled",
]
