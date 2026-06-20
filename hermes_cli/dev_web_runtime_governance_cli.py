"""Phase 3I Runtime Governance CLI — dev-only command group (code allowed, production forbidden).

A developer-facing CLI command group that exposes the **already-implemented**
Phase 3I dev-only descriptor-backed fixture runtime. It is a thin, fail-closed
wrapper over the pure report projections in
:mod:`hermes_cli.dev_web_runtime_governance` — it parses CLI input, calls the
projection functions, and prints a JSON-safe report to stdout.

Supported subcommands:

  - ``list``       — list the frozen reviewed-fixture descriptors (no execution).
  - ``show <id>``  — inspect the registry→runtime binding for a descriptor (no
                     execution).
  - ``run <id> --input JSON``   — run one descriptor-backed fixture operation.
  - ``batch --items JSON``      — run a multi-descriptor batch (isolated, fail-closed).
  - ``audit <id> --input JSON`` — run one descriptor and print its redacted audit.
  - ``p0-report``  — print the conservative P0 evidence projection summary.
  - ``help``       — print the command help (dev-only / fixture-only / production-forbidden).

Hard guarantees (frozen):

  - **reviewed-fixture-descriptor only.** The CLI can only reach the frozen
    reviewed descriptors through the projection module. No arbitrary plugin
    loading, no local plugin directory loading, no remote registry, no
    marketplace, no external plugin fetch, no provider / LLM-generated install.
  - **No real API key read, no external network, no new HTTP route.** This CLI is
    **not** wired into the FastAPI app and adds no route.
  - **No ``~/.hermes`` access and no production ``state.db`` access** — not even
    metadata-only ``stat`` / ``ls`` / ``resolve``.
  - **No file I/O.** No ``--input-file`` / ``--output-file``; no audit / JSONL
    persistence; no runtime store write. Every report is printed to stdout and
    is ``persisted: False``.
  - **Bounded, validated, redacted input.** JSON input is parsed with
    :func:`json.loads`, length-bounded, shape-validated, and the whole report is
    run through :func:`~dev_web_sandbox_guards.redact_sandbox_payload` before it
    is printed. Secret-like / production-path-like / ``~/.hermes``-like input is
    masked in the output; authorization-smuggling metadata is ignored.

Exit codes:

  - ``0`` — the command parsed and ran (``ok`` True). A denied / failed
    descriptor is still ``ok`` True: the CLI reported the outcome correctly.
  - ``2`` — invalid input / usage error (``ok`` False): malformed JSON, an
    oversized payload, a wrong shape, a missing / unsafe descriptor id, or an
    unknown command. The error message is always redacted.

Phase: 3I — Runtime Governance CLI
Status: implemented (dev-only CLI over the existing runtime). NOT a production
        plugin runtime. No arbitrary loading, no remote registry, no marketplace,
        no external network, no real secret read, no new route, no production
        access.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Mapping, Sequence

from hermes_cli.dev_web_plugin_runtime import MAX_BATCH_REQUESTS
from hermes_cli.dev_web_runtime_governance import (
    GOVERNANCE_VERSION,
    assert_no_side_effect_surface,
    authorization_projection,
    build_runtime_audit_report,
    build_runtime_p0_report,
    list_runtime_descriptors,
    run_runtime_descriptor,
    run_runtime_descriptor_batch,
    show_runtime_descriptor_binding,
    side_effect_projection,
)
from hermes_cli.dev_web_sandbox_guards import redact_sandbox_payload, redact_sandbox_text

#: Maximum length (characters) of a single CLI JSON input string (``--input`` /
#: ``--items``). Generous but bounded so the CLI never accepts unbounded input.
MAX_CLI_INPUT_CHARS: int = 32768

#: A safe descriptor id is a clean label over ``[A-Za-z0-9_.\-]`` with no
#: traversal pair and a bounded length — it is a registry lookup key, never a
#: path / command / shell token.
_DESCRIPTOR_ID_SAFE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
)
_MAX_DESCRIPTOR_ID_LEN = 128

#: The frozen set of subcommands the governance CLI accepts.
COMMANDS: tuple[str, ...] = (
    "list",
    "show",
    "run",
    "batch",
    "audit",
    "p0-report",
    "help",
)

#: Canonical short aliases. An alias resolves to its canonical command BEFORE
#: dispatch, so the envelope ``command`` always carries the canonical name and
#: the alias changes no behavior. Aliases are a pure typing convenience.
COMMAND_ALIASES: dict[str, str] = {
    "ls": "list",
    "inspect": "show",
    "exec": "run",
    "evidence": "p0-report",
}

#: The canonical envelope command-group prefix (``dev-runtime.<command>``).
COMMAND_GROUP: str = "dev-runtime"

#: Concrete, copy-pasteable examples surfaced in the help envelope. They are
#: plain strings — no example reads or writes a file.
COMMAND_EXAMPLES: tuple[str, ...] = (
    "hermes dev-runtime list",
    "hermes dev-runtime show descriptor.fixture.echo_uppercase",
    "hermes dev-runtime run descriptor.fixture.echo_uppercase --input '{\"text\":\"hello\"}'",
    "hermes dev-runtime batch --items '[{\"descriptor_id\":\"descriptor.fixture.echo_uppercase\",\"input\":{\"text\":\"hello\"}}]'",
    "hermes dev-runtime audit descriptor.fixture.echo_uppercase --input '{\"text\":\"hello\"}'",
    "hermes dev-runtime p0-report",
)

#: Per-subcommand help (summary + usage + the args it accepts). Surfaced by
#: ``hermes dev-runtime <command> --help``. ``pretty`` / aliases are global and
#: noted once in the root help.
SUBCOMMAND_HELP: dict[str, dict[str, str]] = {
    "list": {
        "summary": "List the frozen reviewed-fixture descriptors (no execution).",
        "usage": "hermes dev-runtime list",
    },
    "show": {
        "summary": "Inspect the registry→runtime binding for a descriptor (no execution).",
        "usage": "hermes dev-runtime show <descriptor-id>",
        "args": "descriptor-id — a reviewed fixture descriptor id (e.g. descriptor.fixture.echo_uppercase).",
    },
    "run": {
        "summary": "Run one descriptor-backed fixture operation.",
        "usage": "hermes dev-runtime run <descriptor-id> --input JSON",
        "args": "descriptor-id — a reviewed fixture descriptor id; --input — a JSON object payload.",
    },
    "batch": {
        "summary": "Run a multi-descriptor batch (isolated, fail-closed, order-preserving).",
        "usage": "hermes dev-runtime batch --items JSON [--fail-fast]",
        "args": "--items — a JSON array of {descriptor_id, input?}; --fail-fast — stop after the first non-allowed result.",
    },
    "audit": {
        "summary": "Run one descriptor and print its redacted audit.",
        "usage": "hermes dev-runtime audit <descriptor-id> --input JSON",
        "args": "descriptor-id — a reviewed fixture descriptor id; --input — a JSON object payload.",
    },
    "p0-report": {
        "summary": "Print the conservative P0 evidence projection summary.",
        "usage": "hermes dev-runtime p0-report",
    },
    "help": {
        "summary": "Print the governance CLI help (dev-only / production-forbidden).",
        "usage": "hermes dev-runtime help",
    },
}


class GovernanceInputError(Exception):
    """A fail-closed input-validation error raised by the governance CLI.

    The ``code`` is a stable, grep-able token; ``message`` is always redacted
    before it reaches the JSON envelope.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical_command(command: Any) -> str:
    """Render *command* as the canonical envelope token ``dev-runtime.<command>``.

    Unknown / non-string input maps to ``dev-runtime.unknown`` (the raw token is
    never echoed — it could carry an unsafe value). ``help`` and the canonical
    commands are rendered verbatim; aliases are resolved by the caller before
    this is called.
    """
    if isinstance(command, str) and command in COMMANDS:
        return f"{COMMAND_GROUP}.{command}"
    return f"{COMMAND_GROUP}.unknown"


def _help_text() -> str:
    """The governance CLI help (states the dev-only / production-forbidden boundary).

    The text deliberately paraphrases the forbidden surfaces (production home,
    production database, secrets) rather than naming their literal tokens, so the
    conservative redactor does not collapse the help string when it is projected
    into the JSON envelope.
    """
    alias_line = ", ".join(f"{a} -> {c}" for a, c in COMMAND_ALIASES.items())
    examples_block = "\n".join(f"  {ex}" for ex in COMMAND_EXAMPLES)
    return (
        "hermes dev-runtime — Phase 3I Runtime Governance CLI\n"
        "\n"
        "Dev-only. Fixture-only. Production-forbidden. This CLI operates ONLY on\n"
        "the frozen reviewed-fixture descriptors. It does not load arbitrary\n"
        "plugins, scan plugin directories, contact a remote registry or marketplace,\n"
        "fetch external plugins, read real secrets, touch the production home,\n"
        "touch a production database, add an HTTP route, or write a runtime store.\n"
        "\n"
        "Subcommands:\n"
        "  list                          List reviewed-fixture descriptors (no execution).\n"
        "  show <descriptor-id>          Inspect the registry→runtime binding (no execution).\n"
        "  run <descriptor-id> --input   Run one descriptor-backed fixture operation.\n"
        "  batch --items JSON            Run a multi-descriptor batch (isolated, fail-closed).\n"
        "  audit <descriptor-id> --input Run one descriptor and print its redacted audit.\n"
        "  p0-report                     Print the P0 evidence projection summary.\n"
        "  help                          Print this help.\n"
        f"\nAliases (canonical behavior, identical output): {alias_line}\n"
        "\nOutput: every command prints a JSON-safe, redacted report to stdout.\n"
        "Default output is compact JSON; pass --pretty for indent=2 JSON. The data\n"
        "content is identical either way (no non-JSON text is added).\n"
        f"\nExamples:\n{examples_block}\n"
        "\nEvery command carries a frozen authorization block and an all-False\n"
        "side-effect surface. Implementation Authorization is NO-GO; Phase 3I\n"
        "production authorization is NOT AUTHORIZED; production runtime is NO-GO;\n"
        "new route is NO-GO; production rollout is NO-GO. A descriptor-backed\n"
        "fixture pass resolves / authorizes nothing (P0 resolved_count stays 0).\n"
        f"\nSchema version: {GOVERNANCE_VERSION}"
    )


def _root_help_result() -> dict[str, Any]:
    """The structured help result projected by the root ``help`` / no-args path."""
    return {
        "schemaVersion": GOVERNANCE_VERSION,
        "source": "dev_web_runtime_governance_cli",
        "help": _help_text(),
        "commands": list(COMMANDS),
        "aliases": dict(COMMAND_ALIASES),
        "examples": list(COMMAND_EXAMPLES),
        "devOnly": True,
        "fixtureOnly": True,
        "production": False,
        "prettySupported": True,
        "redactionApplied": True,
    }


def _subcommand_help_result(command: str) -> dict[str, Any]:
    """The structured help result projected by ``<command> --help``."""
    info = SUBCOMMAND_HELP.get(command, {})
    return {
        "schemaVersion": GOVERNANCE_VERSION,
        "source": "dev_web_runtime_governance_cli",
        "command": command,
        "canonical": _canonical_command(command),
        "summary": info.get("summary", ""),
        "usage": info.get("usage", ""),
        "args": info.get("args", ""),
        "aliases": [a for a, c in COMMAND_ALIASES.items() if c == command],
        "prettySupported": True,
        "devOnly": True,
        "fixtureOnly": True,
        "production": False,
        "redactionApplied": True,
    }


def _validate_descriptor_id(value: Any) -> str:
    """Validate *value* is a safe descriptor-id label, else raise. Fail-closed."""
    if not isinstance(value, str) or not value:
        raise GovernanceInputError("invalid_descriptor_id", "descriptor id is required")
    if len(value) > _MAX_DESCRIPTOR_ID_LEN:
        raise GovernanceInputError("invalid_descriptor_id", "descriptor id is too long")
    if ".." in value:
        raise GovernanceInputError("invalid_descriptor_id", "descriptor id is unsafe")
    if any(ch not in _DESCRIPTOR_ID_SAFE_CHARS for ch in value):
        raise GovernanceInputError("invalid_descriptor_id", "descriptor id is unsafe")
    return value


def _parse_json_input(raw: Any, *, label: str) -> Any:
    """Parse a bounded JSON input string. Raise on oversized / non-JSON input."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise GovernanceInputError("invalid_input_shape", f"{label} must be a JSON string")
    if len(raw) > MAX_CLI_INPUT_CHARS:
        raise GovernanceInputError("oversized_input", f"{label} exceeds the size bound")
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise GovernanceInputError("invalid_json", f"{label} is not valid JSON") from exc


def _parse_run_input(raw: Any) -> Mapping[str, Any] | None:
    """Parse the ``--input`` for ``run`` / ``audit``. Must be a JSON object or None."""
    if raw is None:
        return None
    parsed = _parse_json_input(raw, label="input")
    if parsed is None:
        return None
    if not isinstance(parsed, Mapping):
        raise GovernanceInputError("invalid_input_shape", "input must be a JSON object")
    return parsed


def _parse_batch_items(raw: Any) -> list[dict[str, Any]]:
    """Parse the ``--items`` for ``batch``. Must be a bounded JSON array of objects."""
    parsed = _parse_json_input(raw, label="items")
    if not isinstance(parsed, list):
        raise GovernanceInputError("invalid_input_shape", "items must be a JSON array")
    if len(parsed) > MAX_BATCH_REQUESTS:
        raise GovernanceInputError("batch_oversized", "items exceed the batch size bound")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, Mapping):
            raise GovernanceInputError(
                "invalid_input_shape", f"items[{index}] must be a JSON object"
            )
        descriptor_id = item.get("descriptor_id")
        # Validate the id here so an unsafe / missing id is a clean CLI error
        # rather than a denied runtime result that looks like success.
        _validate_descriptor_id(descriptor_id)
        input_payload = item.get("input")
        if input_payload is not None and not isinstance(input_payload, Mapping):
            raise GovernanceInputError(
                "invalid_input_shape", f"items[{index}].input must be a JSON object"
            )
        normalized: dict[str, Any] = {
            "descriptor_id": descriptor_id,
            "input": input_payload,
        }
        items.append(normalized)
    return items


def _build_parser() -> argparse.ArgumentParser:
    """Build the governance argparse parser (all args optional — validated later)."""
    parser = argparse.ArgumentParser(
        prog="hermes dev-runtime",
        description="Phase 3I Runtime Governance CLI (dev-only, fixture-only, production-forbidden).",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List reviewed-fixture descriptors (no execution).")

    show_p = sub.add_parser("show", help="Inspect a descriptor binding (no execution).")
    show_p.add_argument("descriptor_id", nargs="?", help="Reviewed fixture descriptor id.")

    run_p = sub.add_parser("run", help="Run one descriptor-backed fixture operation.")
    run_p.add_argument("descriptor_id", nargs="?", help="Reviewed fixture descriptor id.")
    run_p.add_argument("--input", default=None, help="JSON object input payload.")

    batch_p = sub.add_parser("batch", help="Run a multi-descriptor batch.")
    batch_p.add_argument("--items", default=None, help="JSON array of {descriptor_id, input?}.")
    batch_p.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first non-allowed result.",
    )

    audit_p = sub.add_parser("audit", help="Run one descriptor and print its redacted audit.")
    audit_p.add_argument("descriptor_id", nargs="?", help="Reviewed fixture descriptor id.")
    audit_p.add_argument("--input", default=None, help="JSON object input payload.")

    sub.add_parser("p0-report", help="Print the P0 evidence projection summary.")
    sub.add_parser("help", help="Print the governance CLI help.")

    return parser


def _print_json(envelope: dict[str, Any], *, pretty: bool = False) -> None:
    """Print a JSON-safe, redacted envelope to stdout.

    Default (``pretty=False``) is compact, single-line JSON with sorted keys; with
    ``pretty=True`` the same data is rendered ``indent=2``. Both are deterministic
    (``sort_keys=True``) and contain no non-JSON text. No timestamp / runId is
    emitted, so the output is a stable snapshot.
    """
    redacted = redact_sandbox_payload(envelope)
    if pretty:
        text = json.dumps(redacted, indent=2, sort_keys=True)
    else:
        text = json.dumps(redacted, sort_keys=True, separators=(",", ":"))
    sys.stdout.write(text)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _envelope(
    command: Any,
    *,
    ok: bool,
    result: Any = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable governance CLI envelope.

    Every envelope — success or failure, including help — carries the frozen
    ``schemaVersion``, the canonical ``command`` token, the frozen
    ``authorization`` block, and the all-False ``sideEffects`` surface. ``ok``
    envelopes carry ``result``; failure envelopes carry a redacted ``error``.
    """
    env: dict[str, Any] = {
        "ok": ok,
        "command": _canonical_command(command),
        "schemaVersion": GOVERNANCE_VERSION,
        "authorization": authorization_projection(),
        "sideEffects": side_effect_projection(),
    }
    if result is not None:
        env["result"] = result
    if error is not None:
        env["error"] = error
    return env


def _dispatch(command: str, args: argparse.Namespace) -> dict[str, Any]:
    """Run one governance subcommand and return its result dict. Fail-closed."""
    if command == "list":
        return list_runtime_descriptors()

    if command == "show":
        descriptor_id = _validate_descriptor_id(args.descriptor_id)
        return show_runtime_descriptor_binding(descriptor_id)

    if command == "run":
        descriptor_id = _validate_descriptor_id(args.descriptor_id)
        input_payload = _parse_run_input(args.input)
        return run_runtime_descriptor(descriptor_id, input_payload)

    if command == "batch":
        items = _parse_batch_items(args.items)
        return run_runtime_descriptor_batch(items, fail_fast=bool(args.fail_fast))

    if command == "audit":
        descriptor_id = _validate_descriptor_id(args.descriptor_id)
        input_payload = _parse_run_input(args.input)
        run_report = run_runtime_descriptor(descriptor_id, input_payload)
        return build_runtime_audit_report(run_report)

    if command == "p0-report":
        return build_runtime_p0_report()

    raise GovernanceInputError("unknown_command", "unknown governance command")


def main(argv: Sequence[str] | None = None) -> int:
    """Governance CLI entry point. Returns the process exit code.

    ``argv`` defaults to ``sys.argv[1:]``. Prints a JSON-safe, redacted envelope
    to stdout. Re-affirms the no-side-effect boundary on every invocation.

    Output mode: default is compact JSON; ``--pretty`` (accepted anywhere on the
    command line) renders the same data ``indent=2``. ``-h`` / ``--help`` anywhere
    prints root help (or, when it follows a known subcommand, that subcommand's
    help). Canonical aliases (``COMMAND_ALIASES``) resolve before dispatch, so the
    envelope ``command`` always carries the canonical token and the alias changes
    no behavior.
    """
    assert_no_side_effect_surface()

    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    # ``--pretty`` is a position-independent global output flag (it is NOT a
    # file flag and adds no I/O). Pre-scan and strip it so the argparse
    # subparsers never have to know about it and so ``dev-runtime --pretty list``
    # and ``dev-runtime list --pretty`` both work.
    pretty = "--pretty" in argv
    if pretty:
        argv = [a for a in argv if a != "--pretty"]

    parser = _build_parser()

    # Help routing: ``-h`` / ``--help`` anywhere → root or subcommand help.
    help_index = next((i for i, a in enumerate(argv) if a in ("-h", "--help")), None)
    if help_index is not None:
        preceding = argv[:help_index]
        sub = next(
            (a for a in preceding if a in COMMANDS or a in COMMAND_ALIASES),
            None,
        )
        canonical = COMMAND_ALIASES.get(sub, sub) if sub else None
        if canonical and canonical != "help":
            envelope = _envelope(
                canonical, ok=True, result=_subcommand_help_result(canonical)
            )
        else:
            envelope = _envelope("help", ok=True, result=_root_help_result())
        _print_json(envelope, pretty=pretty)
        return 0

    # No subcommand, or explicit ``help`` → root help, exit 0.
    if not argv or argv[0] == "help":
        envelope = _envelope("help", ok=True, result=_root_help_result())
        _print_json(envelope, pretty=pretty)
        return 0

    raw_command = argv[0]
    # Alias resolution: an alias maps to its canonical command before dispatch.
    if raw_command in COMMAND_ALIASES:
        command = COMMAND_ALIASES[raw_command]
        argv = [command, *argv[1:]]
    elif raw_command in COMMANDS:
        command = raw_command
    else:
        envelope = _envelope(
            "unknown",
            ok=False,
            error={
                "code": "unknown_command",
                "message": redact_sandbox_text("unknown governance command"),
                "redacted": True,
            },
        )
        _print_json(envelope, pretty=pretty)
        return 2

    # Parse the rest with argparse (it never sees the subcommand token as unknown
    # — it is now the canonical command, which is a registered subparser).
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on usage errors — surface a redacted JSON error.
        envelope = _envelope(
            command,
            ok=False,
            error={
                "code": "invalid_usage",
                "message": redact_sandbox_text("invalid governance CLI usage"),
                "redacted": True,
            },
        )
        _print_json(envelope, pretty=pretty)
        code = exc.code if isinstance(exc.code, int) else 2
        return code

    try:
        result = _dispatch(command, args)
    except GovernanceInputError as exc:
        envelope = _envelope(
            command,
            ok=False,
            error={
                "code": exc.code,
                "message": redact_sandbox_text(exc.message),
                "redacted": True,
            },
        )
        _print_json(envelope, pretty=pretty)
        return 2
    except Exception as exc:  # defensive: never leak an internal trace to stdout
        envelope = _envelope(
            command,
            ok=False,
            error={
                "code": "internal_error",
                "message": redact_sandbox_text(str(exc)),
                "redacted": True,
            },
        )
        _print_json(envelope, pretty=pretty)
        return 2

    envelope = _envelope(command, ok=True, result=result)
    _print_json(envelope, pretty=pretty)
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    sys.exit(main())


__all__ = [
    "COMMANDS",
    "COMMAND_ALIASES",
    "COMMAND_GROUP",
    "COMMAND_EXAMPLES",
    "SUBCOMMAND_HELP",
    "GOVERNANCE_VERSION",
    "MAX_CLI_INPUT_CHARS",
    "GovernanceInputError",
    "main",
]
