"""Phase 3I Dev-only Local Plugin Runtime — Reviewed Fixture Plugins.

A frozen, in-memory set of **reviewed, side-effect-free fixture plugin
operations** that the dev-only local plugin runtime
(:mod:`hermes_cli.dev_web_plugin_runtime`) may invoke. Each operation is a pure
Python function over an ``input_payload`` mapping — it transforms the payload in
memory and returns a result mapping. Nothing else.

This is the **only** executable surface the Phase 3I runtime is authorized to
call, and only through the hardcoded ``FIXTURE_REGISTRY`` allowlist in this
module. The registry is the binding target for descriptor-to-fixture binding:
a descriptor may name one of these ``(plugin_id, operation)`` pairs and nothing
else.

Hard guarantees (frozen):

  - Pure / deterministic / stdlib-only. No ``importlib`` loader, no
    ``__import__`` call, no ``subprocess``, no shell, no ``eval`` / ``exec``,
    no ``open`` / ``read_text`` / ``write_text`` / ``stat`` / ``resolve`` of any
    path, no ``requests`` / ``httpx`` / ``aiohttp`` / socket / DNS.
  - **Never** reads the environment, ``.env``, a real API key, ``Authorization``
    / ``Bearer`` material, or a PEM private key. A secret-shaped input value is
    **redacted in the returned output** (``[REDACTED]``); it is never read from
    a secret store.
  - **Never** performs a network call of any kind and **never** touches the
    filesystem or production state.
  - Introduces **no** HTTP route and is **not** imported by the FastAPI app.
  - Writes nothing: no JSONL, no database, no runtime store. Every operation is
    a pure in-memory transform.

A fixture operation succeeds only on a well-formed, bounded ``input_payload``;
oversized, too-deep, or malformed input raises a controlled
:class:`FixtureInputError` that the runtime catches, redacts, and records as a
structured failure. A fixture that returns a non-JSON-safe value (a callable /
module / object) raises a controlled :class:`FixtureOutputError` so the runtime
records it as a fail-closed result and never leaks the non-native value.

Phase: 3I — Dev-only Local Plugin Runtime MVP (expanded fixture surface)
Status: implemented (reviewed fixture plugins). Dev-only, fixture-only, no
        production, no network, no real secret read, no route, no store write.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from hermes_cli.dev_web_sandbox_guards import (
    REDACTED_VALUE,
    detect_secret_in_string,
)

FIXTURE_AUDIT_SOURCE = "dev_web_fixture_plugins"

#: Maximum ``repr`` size (bytes) of a fixture ``input_payload`` (or any single
#: field / list within it). Oversized input is rejected (``input_oversized``)
#: so a fixture never processes unbounded data.
MAX_FIXTURE_INPUT_BYTES: int = 65536

#: Maximum nesting depth of a fixture ``input_payload``. A nested object deeper
#: than this is rejected (``input_too_deep``) before any transform runs, so a
#: fixture never recurses into unbounded depth.
MAX_FIXTURE_NESTING_DEPTH: int = 8

#: Maximum number of items in a list input (e.g. ``count_items``). Oversized
#: lists are rejected (``input_oversized``) rather than counted.
MAX_FIXTURE_LIST_ITEMS: int = 4096


# ---------------------------------------------------------------------------
# 1. Controlled exceptions
# ---------------------------------------------------------------------------


class FixtureInputError(ValueError):
    """Raised when a fixture ``input_payload`` is malformed / oversized / too deep.

    A controlled exception: the runtime catches it, redacts the message, and
    records a structured failure. It never carries a real secret.
    """


class FixtureExecutionError(RuntimeError):
    """Raised by a fixture that intentionally fails (e.g. ``deliberate_failure``).

    A controlled exception: the runtime catches it, redacts the message (which
    may embed an obvious **fake** secret to prove redaction works), and records
    a structured failure. It never carries a real secret.
    """


class FixtureOutputError(RuntimeError):
    """Raised when a fixture returns a non-JSON-safe result.

    A controlled exception: a fixture must return a JSON-native mapping (no
    callables, modules, or arbitrary objects). A non-safe value is rejected
    (``output_unsafe``) and collapsed by the runtime so the non-native value is
    never echoed into an audit projection. It never carries a real secret.
    """


# ---------------------------------------------------------------------------
# 2. Size / type / depth guards (pure)
# ---------------------------------------------------------------------------


def _payload_size(payload: Any) -> int:
    """Return the ``repr`` size of *payload*. Never raises."""
    try:
        return len(repr(payload))
    except Exception:  # pragma: no cover — defensive
        return 0


def _payload_depth(payload: Any, depth: int = 0) -> int:
    """Return the maximum nesting depth of *payload*. Never raises.

    Bounds recursion at a high sentinel so a cyclic structure cannot loop
    forever — fixtures only ever receive JSON-native (acyclic) input.
    """
    if depth > 64:  # pragma: no cover — defensive bound
        return depth
    if isinstance(payload, Mapping):
        if not payload:
            return depth + 1
        return 1 + max(_payload_depth(v, depth + 1) for v in payload.values())
    if isinstance(payload, (list, tuple)):
        if not payload:
            return depth + 1
        return 1 + max(_payload_depth(v, depth + 1) for v in payload)
    return depth


def _ensure_mapping(payload: Any) -> Mapping[str, Any]:
    """Validate *payload* is a bounded, not-too-deep mapping.

    Raises :class:`FixtureInputError` on a non-mapping, oversized, or too-deep
    payload.
    """
    if not isinstance(payload, Mapping):
        raise FixtureInputError("input_payload must be a mapping")
    if _payload_size(payload) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("input_payload exceeds the fixture size bound")
    if _payload_depth(payload) > MAX_FIXTURE_NESTING_DEPTH:
        raise FixtureInputError("input_payload exceeds the fixture depth bound")
    return payload


def _ensure_bounded_text(text: Any) -> str:
    """Validate *text* is a bounded string. Raises :class:`FixtureInputError`."""
    if not isinstance(text, str):
        raise FixtureInputError("text must be a string")
    if _payload_size(text) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("text exceeds the fixture size bound")
    return text


def _ensure_bounded_list(items: Any) -> list[Any]:
    """Validate *items* is a bounded list. Raises :class:`FixtureInputError`."""
    if not isinstance(items, list):
        raise FixtureInputError("items must be a list")
    if len(items) > MAX_FIXTURE_LIST_ITEMS:
        raise FixtureInputError("items list exceeds the fixture size bound")
    if _payload_size(items) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("items list exceeds the fixture size bound")
    return items


# ---------------------------------------------------------------------------
# 3. Fixture operations (pure, deterministic, redaction-safe)
# ---------------------------------------------------------------------------


def echo_uppercase(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Echo the ``text`` field uppercased.

    Input ``{"text": "hello"}`` → ``{"text": "HELLO"}``. A secret-shaped input
    value is collapsed to :data:`REDACTED_VALUE` in the output (no value leak).
    No side effects, deterministic, rejects non-string / oversized input.
    """
    payload = _ensure_mapping(input_payload)
    text = _ensure_bounded_text(payload.get("text", ""))
    detected, _ = detect_secret_in_string(text)
    return {"text": REDACTED_VALUE if detected else text.upper()}


def summarize_keys(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Summarize the keys of a mapping.

    Input ``{"a": 1, "b": 2}`` → ``{"keys": ["a", "b"], "count": 2}``. Only the
    keys are projected (never the values — no value leak by construction). A
    secret-shaped key is collapsed to :data:`REDACTED_VALUE`. Deterministic;
    rejects oversized input.
    """
    payload = _ensure_mapping(input_payload)
    redacted_keys: list[str] = []
    for key in payload.keys():
        key_text = str(key)
        detected, _ = detect_secret_in_string(key_text)
        redacted_keys.append(REDACTED_VALUE if detected else key_text)
    return {"keys": redacted_keys, "count": len(payload)}


def deliberate_failure(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Always raise a controlled failure carrying an obvious **fake** secret.

    Used to prove the runtime's failure handling: the exception is caught, the
    fake secret in the message is redacted from every projection, and the
    runtime records a structured fail-closed result. The fake secret is
    deliberately ``sk-``-shaped so the redactor is exercised end-to-end.
    """
    # Validate the payload shape first so a malformed input is reported as an
    # input error (not a deliberate failure) — the failure path is reserved for
    # a well-formed input that the fixture then rejects on purpose.
    _ensure_mapping(input_payload)
    raise FixtureExecutionError(
        "deliberate fixture failure — fake secret "
        "sk-FAKE-SECRET-DO-NOT-LEAK-12345678 must be redacted by the runtime"
    )


def normalize_text(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Trim and collapse internal whitespace in the ``text`` field.

    Input ``{"text": "  Hello   World  "}`` → ``{"text": "Hello World"}``. A
    secret-shaped input value is collapsed to :data:`REDACTED_VALUE` (no value
    leak). Pure / deterministic / no I/O / no env read. Rejects non-string and
    oversized input.
    """
    payload = _ensure_mapping(input_payload)
    text = _ensure_bounded_text(payload.get("text", ""))
    detected, _ = detect_secret_in_string(text)
    if detected:
        return {"text": REDACTED_VALUE}
    # Collapse runs of whitespace (spaces / tabs / newlines) to a single space
    # and trim the ends — pure stdlib, no regex backtracking concerns at this
    # bounded size.
    collapsed = " ".join(text.split())
    return {"text": collapsed}


def validate_required_keys(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate a ``payload`` mapping carries every ``required`` key.

    Input ``{"payload": {"name": "Hermes"}, "required": ["name"]}`` →
    ``{"valid": true, "missing": []}``. ``required`` must be a list of strings;
    ``payload`` must be a mapping. Missing keys are returned sorted. A
    secret-shaped key in the output is collapsed to :data:`REDACTED_VALUE`. The
    ``payload`` *values* are never projected (no value leak). Deterministic /
    no side effects; rejects malformed or oversized input.
    """
    outer = _ensure_mapping(input_payload)
    required_raw = outer.get("required", [])
    if not isinstance(required_raw, (list, tuple)):
        raise FixtureInputError("required must be a list of strings")
    required: list[str] = []
    for item in required_raw:
        if not isinstance(item, str) or not item:
            raise FixtureInputError("required entries must be non-empty strings")
        required.append(item)
    if _payload_size(required) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("required list exceeds the fixture size bound")

    payload_raw = outer.get("payload", {})
    if not isinstance(payload_raw, Mapping):
        raise FixtureInputError("payload must be a mapping")
    if _payload_size(payload_raw) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("payload exceeds the fixture size bound")

    payload_keys = {str(k) for k in payload_raw.keys()}
    missing_sorted = sorted({k for k in required if k not in payload_keys})
    # Redact a secret-shaped missing key so the output never echoes a secret
    # token a caller smuggled into ``required``.
    redacted_missing = [
        (REDACTED_VALUE if detect_secret_in_string(k)[0] else k) for k in missing_sorted
    ]
    valid = len(missing_sorted) == 0
    return {"valid": valid, "missing": redacted_missing}


def count_items(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Count the items in the ``items`` list.

    Input ``{"items": [1, 2, 3]}`` → ``{"count": 3}``. Only the count is
    returned — the values are never projected (no value leak by construction).
    Deterministic / no side effects; rejects non-list and oversized input.
    """
    payload = _ensure_mapping(input_payload)
    items = _ensure_bounded_list(payload.get("items", []))
    return {"count": len(items)}


def redact_payload(input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the input payload with every fake secret / forbidden path redacted.

    Any dict input is run through the sandbox redactor: fake secrets (``sk-`` /
    ``ghp_`` / ``xox`` / ``Bearer`` / ``Authorization`` / PEM), production-path
    values (``~/.hermes`` / ``state.db``), and secret-bearing field values are
    collapsed to :data:`REDACTED_VALUE`. No file write, no network, no env read.
    The output is a fresh plain dict (JSON-native).
    """
    payload = _ensure_mapping(input_payload)
    # Imported lazily to keep the import graph of this module minimal and to
    # avoid a top-level cycle note; the redactor is a pure stdlib helper.
    from hermes_cli.dev_web_sandbox_guards import redact_sandbox_payload

    redacted = redact_sandbox_payload(dict(payload))
    # The redactor guarantees a JSON-native structure; coerce to a plain dict so
    # the runtime's output validator sees a clean mapping.
    if isinstance(redacted, dict):
        return dict(redacted)
    return {"redacted": REDACTED_VALUE}


# ---------------------------------------------------------------------------
# 4. Frozen registry / allowlist + per-operation metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixtureOperation:
    """One reviewed fixture operation the runtime may bind a descriptor to.

    ``invoker`` is the plain Python function object (never a module path, import
    string, shell command, or remote reference). The runtime invokes it
    directly; there is no loader, no dynamic import, and no string-to-callable
    resolution.

    The metadata fields (``side_effects`` / ``network`` / ``secrets`` /
    ``filesystem`` / ``production`` / ``route_change``) are frozen and must all
    be ``False`` for a reviewed fixture: the runtime re-validates them at bind
    time and denies an operation whose metadata is missing or unsafe (a
    defense-in-depth check — the registry only ever holds safe operations).
    ``allowed_capabilities`` is the set of capability *labels* a request may
    carry alongside this fixture; a request asking for a capability outside this
    set is denied (``capability_mismatch_denied``).
    """

    plugin_id: str
    operation: str
    description: str
    invoker: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    allowed_capabilities: tuple[str, ...] = ("descriptor.read",)
    input_policy: str = "bounded_json_mapping"
    output_policy: str = "json_safe_redacted_mapping"
    side_effects: bool = False
    network: bool = False
    secrets: bool = False
    filesystem: bool = False
    production: bool = False
    route_change: bool = False

    def __post_init__(self) -> None:
        # A reviewed fixture must declare a fully-safe, side-effect-free
        # surface. This is enforced at construction so a future editor cannot
        # accidentally register an unsafe operation.
        if not isinstance(self.plugin_id, str) or not self.plugin_id:
            raise ValueError("plugin_id must be a non-empty string")
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("operation must be a non-empty string")
        if not callable(self.invoker):
            raise ValueError("invoker must be a callable")
        for flag in (self.side_effects, self.network, self.secrets,
                     self.filesystem, self.production, self.route_change):
            if flag is not False:
                raise ValueError("reviewed fixture metadata must be all-False")

    @property
    def metadata(self) -> Mapping[str, Any]:
        """A frozen view of this operation's safety metadata."""
        return MappingProxyType(
            {
                "pluginId": self.plugin_id,
                "operation": self.operation,
                "allowedCapabilities": tuple(self.allowed_capabilities),
                "inputPolicy": self.input_policy,
                "outputPolicy": self.output_policy,
                "sideEffects": self.side_effects,
                "network": self.network,
                "secrets": self.secrets,
                "filesystem": self.filesystem,
                "production": self.production,
                "routeChange": self.route_change,
            }
        )

    def to_safe_dict(self) -> dict[str, Any]:
        # The invoker is never serialized — only its stable labels + metadata.
        return {
            "pluginId": self.plugin_id,
            "operation": self.operation,
            "description": self.description,
            "allowedCapabilities": list(self.allowed_capabilities),
            "inputPolicy": self.input_policy,
            "outputPolicy": self.output_policy,
            "sideEffects": self.side_effects,
            "network": self.network,
            "secrets": self.secrets,
            "filesystem": self.filesystem,
            "production": self.production,
            "routeChange": self.route_change,
            "invokerExposed": False,
            "redactionApplied": True,
        }


#: The frozen, ordered registry of reviewed fixture operations. This is the
#: ONLY executable surface the Phase 3I runtime is authorized to call.
FIXTURE_REGISTRY: tuple[FixtureOperation, ...] = (
    FixtureOperation(
        plugin_id="fixture.echo",
        operation="echo_uppercase",
        description="Echo the text field uppercased; redacts secret-shaped input.",
        invoker=echo_uppercase,
    ),
    FixtureOperation(
        plugin_id="fixture.inspect",
        operation="summarize_keys",
        description="Summarize mapping keys; never leaks values; redacts secret keys.",
        invoker=summarize_keys,
    ),
    FixtureOperation(
        plugin_id="fixture.fault",
        operation="deliberate_failure",
        description="Always fails with a controlled, fake-secret-bearing exception.",
        invoker=deliberate_failure,
    ),
    FixtureOperation(
        plugin_id="fixture.transform",
        operation="normalize_text",
        description="Trim and collapse whitespace; redacts secret-shaped input.",
        invoker=normalize_text,
    ),
    FixtureOperation(
        plugin_id="fixture.validate",
        operation="validate_required_keys",
        description="Validate required keys; returns sorted missing; redacts secret keys.",
        invoker=validate_required_keys,
    ),
    FixtureOperation(
        plugin_id="fixture.math",
        operation="count_items",
        description="Count list items; never leaks values.",
        invoker=count_items,
    ),
    FixtureOperation(
        plugin_id="fixture.redact",
        operation="redact_payload",
        description="Redact fake secrets and forbidden paths from a payload.",
        invoker=redact_payload,
    ),
)

#: The frozen allowlist of ``(plugin_id, operation)`` pairs the runtime may bind.
#: Hardcoded — never derived from user input, filesystem scan, or remote fetch.
FIXTURE_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {(op.plugin_id, op.operation) for op in FIXTURE_REGISTRY}
)

#: The frozen set of reviewed fixture plugin ids.
FIXTURE_PLUGIN_IDS: frozenset[str] = frozenset({op.plugin_id for op in FIXTURE_REGISTRY})

#: The frozen set of reviewed fixture operation names.
FIXTURE_OPERATION_NAMES: frozenset[str] = frozenset(
    {op.operation for op in FIXTURE_REGISTRY}
)


def _registry_index() -> dict[tuple[str, str], FixtureOperation]:
    return {(op.plugin_id, op.operation): op for op in FIXTURE_REGISTRY}


_REGISTRY_INDEX: dict[tuple[str, str], FixtureOperation] = _registry_index()


def lookup_fixture(plugin_id: Any, operation: Any) -> FixtureOperation | None:
    """Return the reviewed fixture for ``(plugin_id, operation)``, else ``None``.

    Exact-membership lookup against the hardcoded registry — never a fuzzy /
    prefix / wildcard match, never a path or module resolution.
    """
    if not isinstance(plugin_id, str) or not isinstance(operation, str):
        return None
    return _REGISTRY_INDEX.get((plugin_id, operation))


def is_known_fixture(plugin_id: Any, operation: Any) -> bool:
    """True iff ``(plugin_id, operation)`` is a reviewed fixture allowlist entry."""
    return lookup_fixture(plugin_id, operation) is not None


def get_fixture_registry() -> tuple[FixtureOperation, ...]:
    """Return a defensive copy of the frozen fixture registry."""
    return tuple(op for op in FIXTURE_REGISTRY)


#: The metadata fields the runtime re-validates at bind time. Each must be
#: ``False`` for a reviewed fixture; a missing or unsafe field denies the bind.
FIXTURE_SAFETY_FLAGS: tuple[str, ...] = (
    "side_effects",
    "network",
    "secrets",
    "filesystem",
    "production",
    "route_change",
)


def validate_fixture_metadata(operation: Any) -> tuple[bool, tuple[str, ...]]:
    """Re-validate a fixture operation's safety metadata.

    Returns ``(ok, reasons)``. A non-:class:`FixtureOperation`, an incomplete
    metadata block, or any non-``False`` safety flag denies the operation. This
    is a defense-in-depth gate: the hardcoded registry only ever holds safe
    operations, so a real bind always passes — but a forged / injected operation
    with tampered metadata is rejected here.
    """
    if not isinstance(operation, FixtureOperation):
        return False, ("fixture_metadata_missing",)
    reasons: list[str] = []
    for flag in FIXTURE_SAFETY_FLAGS:
        if getattr(operation, flag) is not False:
            reasons.append("fixture_metadata_unsafe")
            break
    if not isinstance(operation.allowed_capabilities, tuple):
        reasons.append("fixture_metadata_unsafe")
    if reasons:
        return False, tuple(reasons)
    return True, ()


# ---------------------------------------------------------------------------
# 5. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

NO_FILESYSTEM_ACCESS: bool = True
NO_NETWORK_ACCESS: bool = True
NO_ENV_READ: bool = True
NO_REAL_SECRET_READ: bool = True
NO_SUBPROCESS: bool = True
NO_DYNAMIC_IMPORT: bool = True
NO_PRODUCTION_ACCESS: bool = True
NO_NEW_ROUTE: bool = True


def assert_no_side_effect_surface() -> None:
    """Re-affirm the fixture no-side-effect invariants (pure assertion helper)."""
    assert NO_FILESYSTEM_ACCESS is True
    assert NO_NETWORK_ACCESS is True
    assert NO_ENV_READ is True
    assert NO_REAL_SECRET_READ is True
    assert NO_SUBPROCESS is True
    assert NO_DYNAMIC_IMPORT is True
    assert NO_PRODUCTION_ACCESS is True
    assert NO_NEW_ROUTE is True
    assert all(isinstance(op, FixtureOperation) for op in FIXTURE_REGISTRY)
    assert len(FIXTURE_ALLOWLIST) == len(FIXTURE_REGISTRY)
    # Every reviewed fixture declares a fully-safe, side-effect-free surface.
    for op in FIXTURE_REGISTRY:
        ok, _ = validate_fixture_metadata(op)
        assert ok, f"fixture {op.plugin_id}/{op.operation} has unsafe metadata"


__all__ = [
    "FIXTURE_AUDIT_SOURCE",
    "MAX_FIXTURE_INPUT_BYTES",
    "MAX_FIXTURE_NESTING_DEPTH",
    "MAX_FIXTURE_LIST_ITEMS",
    "FixtureInputError",
    "FixtureExecutionError",
    "FixtureOutputError",
    "echo_uppercase",
    "summarize_keys",
    "deliberate_failure",
    "normalize_text",
    "validate_required_keys",
    "count_items",
    "redact_payload",
    "FixtureOperation",
    "FIXTURE_SAFETY_FLAGS",
    "FIXTURE_REGISTRY",
    "FIXTURE_ALLOWLIST",
    "FIXTURE_PLUGIN_IDS",
    "FIXTURE_OPERATION_NAMES",
    "lookup_fixture",
    "is_known_fixture",
    "get_fixture_registry",
    "validate_fixture_metadata",
    "NO_FILESYSTEM_ACCESS",
    "NO_NETWORK_ACCESS",
    "NO_ENV_READ",
    "NO_REAL_SECRET_READ",
    "NO_SUBPROCESS",
    "NO_DYNAMIC_IMPORT",
    "NO_PRODUCTION_ACCESS",
    "NO_NEW_ROUTE",
    "assert_no_side_effect_surface",
]
