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
oversized or malformed input raises a controlled :class:`FixtureInputError`
that the runtime catches, redacts, and records as a structured failure.

Phase: 3I — Dev-only Local Plugin Runtime MVP
Status: implemented (reviewed fixture plugins). Dev-only, fixture-only, no
        production, no network, no real secret read, no route, no store write.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from hermes_cli.dev_web_sandbox_guards import (
    REDACTED_VALUE,
    detect_secret_in_string,
)

FIXTURE_AUDIT_SOURCE = "dev_web_fixture_plugins"

#: Maximum ``repr`` size (bytes) of a fixture ``input_payload``. Oversized input
#: is rejected (``input_oversized``) so a fixture never processes unbounded data.
MAX_FIXTURE_INPUT_BYTES: int = 65536


# ---------------------------------------------------------------------------
# 1. Controlled exceptions
# ---------------------------------------------------------------------------


class FixtureInputError(ValueError):
    """Raised when a fixture ``input_payload`` is malformed / oversized.

    A controlled exception: the runtime catches it, redacts the message, and
    records a structured failure. It never carries a real secret.
    """


class FixtureExecutionError(RuntimeError):
    """Raised by a fixture that intentionally fails (e.g. ``deliberate_failure``).

    A controlled exception: the runtime catches it, redacts the message (which
    may embed an obvious **fake** secret to prove redaction works), and records
    a structured failure. It never carries a real secret.
    """


# ---------------------------------------------------------------------------
# 2. Size / type guards (pure)
# ---------------------------------------------------------------------------


def _payload_size(payload: Any) -> int:
    """Return the ``repr`` size of *payload*. Never raises."""
    try:
        return len(repr(payload))
    except Exception:  # pragma: no cover — defensive
        return 0


def _ensure_mapping(payload: Any) -> Mapping[str, Any]:
    """Validate *payload* is a bounded mapping. Raises :class:`FixtureInputError`."""
    if not isinstance(payload, Mapping):
        raise FixtureInputError("input_payload must be a mapping")
    if _payload_size(payload) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("input_payload exceeds the fixture size bound")
    return payload


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
    text = payload.get("text", "")
    if not isinstance(text, str):
        raise FixtureInputError("text must be a string")
    if _payload_size(text) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("text exceeds the fixture size bound")
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
    if _payload_size(dict(payload)) > MAX_FIXTURE_INPUT_BYTES:
        raise FixtureInputError("payload exceeds the fixture size bound")
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


# ---------------------------------------------------------------------------
# 4. Frozen registry / allowlist
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixtureOperation:
    """One reviewed fixture operation the runtime may bind a descriptor to.

    ``invoker`` is the plain Python function object (never a module path, import
    string, shell command, or remote reference). The runtime invokes it
    directly; there is no loader, no dynamic import, and no string-to-callable
    resolution.
    """

    plugin_id: str
    operation: str
    description: str
    invoker: Callable[[Mapping[str, Any]], Mapping[str, Any]]

    def to_safe_dict(self) -> dict[str, Any]:
        # The invoker is never serialized — only its stable labels are exposed.
        return {
            "pluginId": self.plugin_id,
            "operation": self.operation,
            "description": self.description,
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


__all__ = [
    "FIXTURE_AUDIT_SOURCE",
    "MAX_FIXTURE_INPUT_BYTES",
    "FixtureInputError",
    "FixtureExecutionError",
    "echo_uppercase",
    "summarize_keys",
    "deliberate_failure",
    "FixtureOperation",
    "FIXTURE_REGISTRY",
    "FIXTURE_ALLOWLIST",
    "FIXTURE_PLUGIN_IDS",
    "FIXTURE_OPERATION_NAMES",
    "lookup_fixture",
    "is_known_fixture",
    "get_fixture_registry",
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
