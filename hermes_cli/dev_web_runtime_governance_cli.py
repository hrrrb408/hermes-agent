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


class GovernanceInputError(Exception):
    """A fail-closed input-validation error raised by the governance CLI.

    The ``code`` is a stable, grep-able token; ``message`` is always redacted
    before it reaches the JSON envelope.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _help_text() -> str:
    """The governance CLI help (states the dev-only / production-forbidden boundary).

    The text deliberately paraphrases the forbidden surfaces (production home,
    production database, secrets) rather than naming their literal tokens, so the
    conservative redactor does not collapse the help string when it is projected
    into the JSON envelope.
    """
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
        "\n"
        "Every command prints a JSON-safe, redacted report to stdout with a frozen\n"
        "authorization block. Implementation Authorization is NO-GO; Phase 3I\n"
        "production authorization is NOT AUTHORIZED; production runtime is NO-GO;\n"
        "new route is NO-GO; production rollout is NO-GO. A descriptor-backed\n"
        "fixture pass resolves / authorizes nothing (P0 resolved_count stays 0).\n"
        f"\nSchema version: {GOVERNANCE_VERSION}"
    )


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


def _print_json(envelope: dict[str, Any]) -> None:
    """Print a JSON-safe, redacted envelope to stdout (sort_keys for determinism)."""
    redacted = redact_sandbox_payload(envelope)
    sys.stdout.write(json.dumps(redacted, indent=2, sort_keys=True))
    sys.stdout.write("\n")
    sys.stdout.flush()


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
    """
    assert_no_side_effect_surface()

    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    parser = _build_parser()

    # No subcommand (or explicit help) → print the help envelope, exit 0.
    if not argv or argv[0] in ("help", "-h", "--help"):
        envelope = {
            "ok": True,
            "command": "help",
            "result": {
                "schemaVersion": GOVERNANCE_VERSION,
                "source": "dev_web_runtime_governance_cli",
                "help": _help_text(),
                "commands": list(COMMANDS),
                "devOnly": True,
                "fixtureOnly": True,
                "production": False,
                "redactionApplied": True,
            },
            "authorization": authorization_projection(),
        }
        _print_json(envelope)
        return 0

    command = argv[0]
    if command not in COMMANDS:
        envelope = {
            "ok": False,
            "command": "help",
            "error": {
                "code": "unknown_command",
                "message": redact_sandbox_text("unknown governance command"),
                "redacted": True,
            },
            "authorization": authorization_projection(),
        }
        _print_json(envelope)
        return 2

    # Parse the rest with argparse (it never sees the subcommand token).
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on usage errors — surface a redacted JSON error.
        envelope = {
            "ok": False,
            "command": command,
            "error": {
                "code": "invalid_usage",
                "message": redact_sandbox_text("invalid governance CLI usage"),
                "redacted": True,
            },
            "authorization": authorization_projection(),
        }
        _print_json(envelope)
        code = exc.code if isinstance(exc.code, int) else 2
        return code

    try:
        result = _dispatch(command, args)
    except GovernanceInputError as exc:
        envelope = {
            "ok": False,
            "command": command,
            "error": {
                "code": exc.code,
                "message": redact_sandbox_text(exc.message),
                "redacted": True,
            },
            "authorization": authorization_projection(),
        }
        _print_json(envelope)
        return 2
    except Exception as exc:  # defensive: never leak an internal trace to stdout
        envelope = {
            "ok": False,
            "command": command,
            "error": {
                "code": "internal_error",
                "message": redact_sandbox_text(str(exc)),
                "redacted": True,
            },
            "authorization": authorization_projection(),
        }
        _print_json(envelope)
        return 2

    envelope = {
        "ok": True,
        "command": command,
        "result": result,
        "authorization": authorization_projection(),
    }
    _print_json(envelope)
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    sys.exit(main())


__all__ = [
    "COMMANDS",
    "GOVERNANCE_VERSION",
    "MAX_CLI_INPUT_CHARS",
    "GovernanceInputError",
    "main",
]
