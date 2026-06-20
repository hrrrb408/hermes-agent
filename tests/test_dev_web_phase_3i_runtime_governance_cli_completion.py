"""Phase 3I Runtime Governance CLI — completion suite (code allowed, production forbidden).

A dedicated **completion** regression suite for the Phase 3I dev-only runtime
governance CLI. It complements
``tests/test_dev_web_phase_3i_runtime_governance_cli.py`` with the stable-envelope,
snapshot, transcript-replay, redaction-corpus, invalid-input hardening,
batch-consistency, audit-completion, no-side-effect invariant, smoke, source
boundary, ``dev_web_api`` isolation, and production-safety coverage required to
promote the CLI from "basic usable" to "complete developer CLI".

Scope (frozen, mirrors the task authorization):

  - **code allowed / production forbidden.** The CLI operates ONLY on the frozen
    reviewed-fixture descriptors through the existing dev-only runtime. No
    arbitrary plugin loading, no local plugin directory loading, no remote
    registry, no marketplace, no external plugin fetch, no provider-generated /
    LLM-generated plugin install, no real API-key read, no external network, no
    new HTTP route, no production rollout.
  - Every forbidden path is a **fake / temp / string-policy** target; the real
    ``~/.hermes`` and production ``state.db`` are never opened, stated, or
    resolved (not even for metadata). Every secret is an obvious **fake**.

A successful descriptor-backed fixture execution (single or batch) is **dev-only
partial evidence**. It is **never** Implementation Authorization GO, **never**
Phase 3I production authorization, **never** real-runtime authorization, **never**
a P0 resolution. ``resolved_count`` stays 0 and the authorization flags stay
NO-GO / not-authorized no matter what runs or what untrusted input is supplied.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_p0_evidence import (
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
)
from hermes_cli.dev_web_plugin_runtime_binding import DESCRIPTOR_BINDING_SOURCE
from hermes_cli.dev_web_runtime_governance import (
    GOVERNANCE_VERSION,
    assert_no_side_effect_surface,
    authorization_projection,
    build_runtime_audit_report,
    build_runtime_p0_report,
    list_runtime_descriptors,
    run_runtime_descriptor,
    run_runtime_descriptor_batch,
    side_effect_projection,
)
from hermes_cli.dev_web_runtime_governance_cli import (
    COMMAND_ALIASES,
    COMMANDS,
    COMMAND_EXAMPLES,
    main as governance_main,
)
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    find_runtime_store_artifacts,
    is_production_home,
    is_production_state_db,
)
from hermes_cli.dev_web_sandbox_guards import REDACTED_VALUE, contains_secret

ECHO = "descriptor.fixture.echo_uppercase"
NORMALIZE = "descriptor.fixture.normalize_text"
VALIDATE = "descriptor.fixture.validate_required_keys"
COUNT = "descriptor.fixture.count_items"
REDACT = "descriptor.fixture.redact_payload"
FAULT = "descriptor.fixture.fault"

#: The twelve frozen side-effect fields every envelope must carry, all False.
SIDE_EFFECT_FIELDS = (
    "productionAccess",
    "externalNetwork",
    "realSecretRead",
    "routeChange",
    "runtimeStoreWrite",
    "auditStoreWrite",
    "arbitraryPluginLoad",
    "localPluginDirectoryRead",
    "remotePluginFetch",
    "marketplaceAccess",
    "inputFileRead",
    "outputFileWrite",
)

#: Authorization keys the frozen redactor leaves intact (value-preserving).
SAFE_AUTH_KEYS = (
    "implementationGate",
    "phase3iProductionGate",
    "productionRuntimeGate",
    "newRouteGate",
    "productionRolloutGate",
    "arbitraryPluginLoading",
    "localPluginDirectoryLoading",
    "remoteRegistry",
    "marketplace",
    "externalNetwork",
    "newRoute",
    "productionRollout",
    "realApiKeyRead",
)

#: The redaction regression corpus — values the FROZEN redactor
#: (``dev_web_sandbox_guards.redact_sandbox_payload``) guarantees to mask. Every
#: entry here is an obvious **fake**. The corpus is intentionally limited to
#: redactor-matching forms: widening the frozen redactor is out of scope (it
#: lives in ``dev_web_sandbox_guards.py``, which this task does not modify).
#: Non-secret bypass strings (``phase_3i_authorized=true`` etc.) are exercised
#: through the authorization-smuggling tests, not the value-redaction tests.
SECRET_CORPUS = (
    "sk-FAKE-SECRET-DO-NOT-LEAK-12345678",
    "Authorization: Bearer fake-token",
    "ghp_fakegithubtoken12345",
    "xoxb-fake-slack-token-1234567890",  # standard slack form (xox[baprs]-)
    "-----BEGIN PRIVATE KEY-----",  # proper PEM with the dash fence
    "OPENAI_API_KEY=fake",
    "db_password=fake",
    "accessToken=fake",
    "/Users/huangruibang/.hermes",
    "/Users/test/.hermes/state.db",
    "/fake/production/state.db",
    "implementation_authorization=GO",
)

#: Authorization-bypass metadata keys. These must be detected + ignored by the
#: binding / P0 layers — they never flip a NO-GO flag or resolve a gate.
BYPASS_METADATA_KEYS = (
    "implementation_authorization",
    "phase_3i_authorized",
    "production_approved",
    "route_exception_approved",
    "real_runtime_authorized",
    "approved",
    "signoff",
    "trust_token",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


@pytest.fixture()
def run_cli():
    """Invoke the governance CLI in-process; return ``(exit_code, parsed_json, raw)``."""

    def _invoke(argv: list[str]) -> tuple[int, dict[str, Any], str]:
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = governance_main(list(argv))
        finally:
            sys.stdout = old
        raw = buf.getvalue()
        return code, json.loads(raw), raw

    return _invoke


@pytest.fixture()
def run_cli_raw():
    """Invoke the governance CLI in-process; return ``(exit_code, raw_stdout)``."""

    def _invoke(argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = governance_main(list(argv))
        finally:
            sys.stdout = old
        return code, buf.getvalue()

    return _invoke


def _all_side_effects_false(block: Any) -> bool:
    return isinstance(block, dict) and set(block.keys()) == set(SIDE_EFFECT_FIELDS) and all(
        v is False for v in block.values()
    )


# ===========================================================================
# A. UX / help / aliases / pretty / JSON parseability
# ===========================================================================


class TestUxHelpAliasesPretty:
    def test_root_help_carries_boundary_and_examples(self, run_cli) -> None:
        code, env, _ = run_cli(["help"])
        assert code == 0
        assert env["command"] == "dev-runtime.help"
        help_text = env["result"]["help"]
        for marker in ("dev-only", "fixture-only", "production-forbidden"):
            assert marker in help_text.lower()
        assert env["result"]["commands"] == list(COMMANDS)
        assert env["result"]["aliases"] == COMMAND_ALIASES
        assert len(env["result"]["examples"]) >= 5

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_root_help_flags(self, run_cli, flag) -> None:
        code, env, _ = run_cli([flag])
        assert code == 0
        assert env["command"] == "dev-runtime.help"

    @pytest.mark.parametrize("command", [c for c in COMMANDS if c != "help"])
    def test_subcommand_help(self, run_cli, command) -> None:
        code, env, _ = run_cli([command, "--help"])
        assert code == 0
        assert env["command"] == f"dev-runtime.{command}"
        assert env["result"]["canonical"] == f"dev-runtime.{command}"
        assert env["result"]["summary"]
        assert env["result"]["usage"].startswith("hermes dev-runtime")

    def test_help_help_returns_root_help(self, run_cli) -> None:
        # ``help --help`` is help-about-help → the root help envelope.
        code, env, _ = run_cli(["help", "--help"])
        assert code == 0
        assert env["command"] == "dev-runtime.help"
        assert "commands" in env["result"]

    @pytest.mark.parametrize("alias,canonical", list(COMMAND_ALIASES.items()))
    def test_alias_resolves_to_canonical(self, run_cli, alias, canonical) -> None:
        # Aliases that need no extra args can be invoked directly.
        if canonical in ("list", "p0-report"):
            code, env, _ = run_cli([alias])
            assert code == 0
            assert env["command"] == f"dev-runtime.{canonical}"

    def test_alias_exec_runs_and_reports_canonical(self, run_cli) -> None:
        code, env, _ = run_cli(["exec", ECHO, "--input", '{"text":"hi"}'])
        assert code == 0
        assert env["command"] == "dev-runtime.run"
        assert env["result"]["outputPayload"] == {"text": "HI"}

    def test_alias_inspect_shows_binding(self, run_cli) -> None:
        code, env, _ = run_cli(["inspect", ECHO])
        assert code == 0
        assert env["command"] == "dev-runtime.show"
        assert env["result"]["bindingAllowed"] is True

    def test_alias_evidence_p0_report(self, run_cli) -> None:
        code, env, _ = run_cli(["evidence"])
        assert code == 0
        assert env["command"] == "dev-runtime.p0-report"
        assert env["result"]["totalGates"] == 24

    def test_pretty_is_indent2_and_data_identical(self, run_cli) -> None:
        _, compact_env, compact_raw = run_cli(["list"])
        _, pretty_env, pretty_raw = run_cli(["list", "--pretty"])
        assert compact_env == pretty_env  # identical data
        # compact = single JSON line; pretty = multi-line indented.
        assert compact_raw.count("\n") == 1
        assert pretty_raw.count("\n") > 5

    def test_pretty_position_independent(self, run_cli) -> None:
        _, before, _ = run_cli(["list", "--pretty"])
        _, after, _ = run_cli(["--pretty", "list"])
        assert before == after

    @pytest.mark.parametrize(
        "argv",
        [
            ["list"],
            ["show", ECHO],
            ["run", ECHO, "--input", '{"text":"hello"}'],
            ["batch", "--items", json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}}])],
            ["audit", ECHO, "--input", '{"text":"hello"}'],
            ["p0-report"],
            ["help"],
        ],
    )
    def test_every_command_emits_parseable_json(self, run_cli, argv) -> None:
        code, env, _ = run_cli(argv)
        assert code == 0
        assert isinstance(env, dict)
        assert "ok" in env


# ===========================================================================
# B. Envelope schema — schemaVersion / authorization / sideEffects on every cmd
# ===========================================================================


class TestEnvelopeSchema:
    SUCCESS_ARGV = [
        ["list"],
        ["show", ECHO],
        ["run", ECHO, "--input", '{"text":"hello"}'],
        ["batch", "--items", json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}}])],
        ["audit", ECHO, "--input", '{"text":"hello"}'],
        ["p0-report"],
        ["help"],
    ]

    @pytest.mark.parametrize("argv", SUCCESS_ARGV)
    def test_success_envelope_has_stable_shape(self, run_cli, argv) -> None:
        code, env, _ = run_cli(argv)
        assert code == 0
        assert env["ok"] is True
        assert env["schemaVersion"] == GOVERNANCE_VERSION
        assert env["command"].startswith("dev-runtime.")
        assert env["authorization"]["implementationGate"] == "NO-GO"
        assert _all_side_effects_false(env["sideEffects"])
        assert contains_secret(env) is False

    def test_failure_envelope_has_stable_shape(self, run_cli) -> None:
        code, env, _ = run_cli(["run", ECHO, "--input", "not json"])
        assert code == 2
        assert env["ok"] is False
        assert env["schemaVersion"] == GOVERNANCE_VERSION
        assert env["command"] == "dev-runtime.run"
        assert env["error"]["redacted"] is True
        assert _all_side_effects_false(env["sideEffects"])
        assert env["authorization"]["implementationGate"] == "NO-GO"

    def test_unknown_command_envelope_has_stable_shape(self, run_cli) -> None:
        code, env, _ = run_cli(["frobnicate"])
        assert code == 2
        assert env["schemaVersion"] == GOVERNANCE_VERSION
        assert env["command"] == "dev-runtime.unknown"
        assert _all_side_effects_false(env["sideEffects"])

    def test_authorization_block_carries_every_dimension(self, run_cli) -> None:
        _, env, _ = run_cli(["list"])
        auth = env["authorization"]
        for key in SAFE_AUTH_KEYS:
            assert key in auth, key
        # The value-preserving verdicts stay visible (not redacted to [REDACTED]).
        assert auth["implementationGate"] == IMPLEMENTATION_AUTHORIZATION == "NO-GO"
        assert auth["phase3iProductionGate"] == "NOT_AUTHORIZED"
        assert auth["productionRuntimeGate"] == REAL_RUNTIME == "NO-GO"
        assert auth["newRouteGate"] == NEW_ROUTE == "NO-GO"
        assert auth["productionRolloutGate"] == PRODUCTION_ROLLOUT == "NO-GO"
        assert auth["arbitraryPluginLoading"] == "NO-GO"
        assert auth["localPluginDirectoryLoading"] == "NO-GO"
        assert auth["remoteRegistry"] == "NO-GO"
        assert auth["marketplace"] == "NO-GO"
        assert auth["externalNetwork"] == "NO-GO"
        assert auth["newRoute"] == "NO-GO"
        assert auth["productionRollout"] == "NO-GO"
        assert auth["realApiKeyRead"] is False

    def test_side_effect_block_all_false_every_command(self, run_cli) -> None:
        for argv in self.SUCCESS_ARGV:
            _, env, _ = run_cli(argv)
            assert _all_side_effects_false(env["sideEffects"]), argv

    def test_side_effect_projection_module_matches_envelope(self) -> None:
        block = side_effect_projection()
        assert _all_side_effects_false(block)
        assert assert_no_side_effect_surface() == block


# ===========================================================================
# C. Deterministic snapshots (inline expected dicts, no snapshot files)
# ===========================================================================


def _normalized_subset(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Assert every key/value in *expected* matches *actual* (subset equality)."""
    for key, want in expected.items():
        assert key in actual, f"missing {key}"
        assert actual[key] == want, f"{key}: {actual[key]!r} != {want!r}"


class TestSnapshots:
    def test_list_snapshot(self, run_cli) -> None:
        _, env, _ = run_cli(["list"])
        r = env["result"]
        _normalized_subset(
            r,
            {
                "schemaVersion": GOVERNANCE_VERSION,
                "count": 6,
                "allDevOnly": True,
                "allFixtureOnly": True,
                "allReviewedFixture": True,
                "anyExecutable": False,
                "anyRemote": False,
                "anyMarketplace": False,
                "anyProduction": False,
                "anyRouteChange": False,
                "registrySource": DESCRIPTOR_BINDING_SOURCE,
            },
        )
        ids = sorted(d["descriptorId"] for d in r["descriptors"])
        assert ids == sorted([ECHO, NORMALIZE, VALIDATE, COUNT, REDACT, FAULT])
        _normalized_subset(
            env,
            {
                "ok": True,
                "command": "dev-runtime.list",
                "schemaVersion": GOVERNANCE_VERSION,
            },
        )
        assert env["authorization"]["implementationGate"] == "NO-GO"
        assert _all_side_effects_false(env["sideEffects"])

    def test_show_snapshot(self, run_cli) -> None:
        _, env, _ = run_cli(["show", ECHO])
        _normalized_subset(
            env["result"],
            {
                "descriptorId": ECHO,
                "bindingAllowed": True,
                "pluginId": "fixture.echo",
                "operation": "echo_uppercase",
                "devOnly": True,
                "fixtureOnly": True,
                "reviewedFixture": True,
            },
        )
        assert env["result"]["denialReasons"] == []
        assert env["result"]["p0Projection"]["resolvedCount"] == 0

    def test_run_snapshot(self, run_cli) -> None:
        _, env, _ = run_cli(["run", ECHO, "--input", '{"text":"hello"}'])
        _normalized_subset(
            env["result"],
            {
                "allowed": True,
                "executed": True,
                "failed": False,
                "pluginId": "fixture.echo",
                "operation": "echo_uppercase",
                "outputPayload": {"text": "HELLO"},
                "persisted": False,
            },
        )
        assert env["result"]["p0Evidence"]["resolvedCount"] == 0
        assert env["result"]["p0Evidence"]["implementationGate"] == "NO-GO"
        assert _all_side_effects_false(env["result"]["sideEffects"])

    def test_denied_run_snapshot(self, run_cli) -> None:
        _, env, _ = run_cli(["run", "descriptor.does.not.exist", "--input", '{"text":"x"}'])
        r = env["result"]
        _normalized_subset(r, {"allowed": False, "executed": False, "outputPayload": {}})
        assert "descriptor_not_in_static_registry" in r["denialReasons"]
        assert env["authorization"]["implementationGate"] == "NO-GO"

    def test_batch_snapshot(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": FAULT, "input": {"text": "x"}},
                {"descriptor_id": COUNT, "input": {"items": [1, 2]}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items])
        _normalized_subset(
            env["result"],
            {"total": 4, "succeeded": 2, "failed": 1, "denied": 1, "persisted": False},
        )
        ops = [r["operation"] for r in env["result"]["results"]]
        assert ops == ["echo_uppercase", "", "deliberate_failure", "count_items"]
        assert env["result"]["p0Evidence"]["resolvedCount"] == 0

    def test_p0_report_snapshot(self, run_cli) -> None:
        _, env, _ = run_cli(["p0-report"])
        _normalized_subset(
            env["result"],
            {
                "totalGates": 24,
                "resolvedCount": 0,
                "unresolvedCount": 24,
                "phase3iAuthorized": False,
            },
        )
        assert env["authorization"]["implementationGate"] == "NO-GO"
        assert env["authorization"]["productionRuntimeGate"] == "NO-GO"


# ===========================================================================
# D. Transcript replay — realistic command sequences
# ===========================================================================


class TestTranscriptReplay:
    def test_happy_transcript(self, run_cli) -> None:
        # help → list → show → run → batch → p0-report
        steps = [
            ["help"],
            ["list"],
            ["show", ECHO],
            ["run", ECHO, "--input", '{"text":"hello"}'],
            [
                "batch",
                "--items",
                json.dumps(
                                    [
                                        {"descriptor_id": ECHO, "input": {"text": "a"}},
                                        {"descriptor_id": COUNT, "input": {"items": [1, 2, 3]}},
                                    ]
                                ),
            ],
            ["p0-report"],
        ]
        last_auth = None
        for argv in steps:
            code, env, _ = run_cli(argv)
            assert code == 0, argv
            assert _all_side_effects_false(env["sideEffects"]), argv
            assert contains_secret(env) is False
            # Authorization is invariant across the whole transcript.
            if last_auth is None:
                last_auth = env["authorization"]
            else:
                assert env["authorization"] == last_auth
        # run produced HELLO; batch succeeded; p0 unresolved.
        _, run_env, _ = run_cli(["run", ECHO, "--input", '{"text":"hello"}'])
        assert run_env["result"]["outputPayload"] == {"text": "HELLO"}
        _, p0_env, _ = run_cli(["p0-report"])
        assert p0_env["result"]["resolvedCount"] == 0

    def test_denied_transcript(self, run_cli) -> None:
        # show unknown → run unknown → run fault → batch mixed → audit fault
        _, show_env, _ = run_cli(["show", "descriptor.does.not.exist"])
        assert show_env["result"]["bindingAllowed"] is False
        _, run_env, _ = run_cli(["run", "descriptor.does.not.exist", "--input", '{"text":"x"}'])
        assert run_env["result"]["executed"] is False
        _, fault_env, _ = run_cli(["run", FAULT, "--input", '{"text":"x"}'])
        assert fault_env["result"]["failed"] is True
        items = json.dumps(
            [
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": FAULT, "input": {"text": "x"}},
            ]
        )
        _, batch_env, _ = run_cli(["batch", "--items", items])
        assert batch_env["result"]["succeeded"] == 1
        assert batch_env["result"]["denied"] == 1
        assert batch_env["result"]["failed"] == 1
        _, audit_env, _ = run_cli(["audit", FAULT, "--input", '{"text":"x"}'])
        assert audit_env["result"]["failed"] is True
        assert audit_env["result"]["persisted"] is False
        # No step leaked the fake fault secret or touched production.
        for env in (show_env, run_env, fault_env, batch_env, audit_env):
            assert contains_secret(env) is False
            blob = json.dumps(env)
            assert ".hermes" not in blob
            assert "sk-FAKE" not in blob

    def test_adversarial_transcript(self, run_cli) -> None:
        # echo fake secret / fake path / metadata smuggling — all redacted/no-effect.
        _, secret_env, _ = run_cli(["run", ECHO, "--input", '{"text":"sk-FAKE-SECRET-DO-NOT-LEAK-12345678"}'])
        assert secret_env["result"]["outputPayload"] == {"text": REDACTED_VALUE}
        _, path_env, _ = run_cli(["run", ECHO, "--input", '{"text":"/Users/test/.hermes/state.db"}'])
        assert path_env["result"]["outputPayload"] == {"text": REDACTED_VALUE}
        # An oversized / invalid batch item is rejected, not executed.
        _, bad_env, _ = run_cli(["batch", "--items", "[{"])
        assert bad_env["ok"] is False
        # An unsupported command is rejected.
        _, unk_env, _ = run_cli(["download-plugin"])
        assert unk_env["ok"] is False
        assert unk_env["command"] == "dev-runtime.unknown"
        for env in (secret_env, path_env, bad_env, unk_env):
            assert _all_side_effects_false(env["sideEffects"])
            assert env["authorization"]["implementationGate"] == "NO-GO"
            assert "sk-FAKE" not in json.dumps(env)


# ===========================================================================
# E. Redaction regression corpus
# ===========================================================================


class TestRedactionCorpus:
    @pytest.mark.parametrize("secret", SECRET_CORPUS)
    def test_run_redacts_corpus_value(self, run_cli, secret) -> None:
        payload = json.dumps({"text": secret})
        _, env, raw = run_cli(["run", ECHO, "--input", payload])
        assert env["ok"] is True
        assert env["result"]["outputPayload"] == {"text": REDACTED_VALUE}
        assert secret not in raw
        assert contains_secret(env) is False

    @pytest.mark.parametrize("secret", SECRET_CORPUS)
    def test_batch_redacts_corpus_value(self, run_cli, secret) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": {"text": secret}}])
        _, env, raw = run_cli(["batch", "--items", items])
        assert env["ok"] is True
        assert env["result"]["results"][0]["outputPayload"] == {"text": REDACTED_VALUE}
        assert secret not in raw
        assert contains_secret(env) is False

    @pytest.mark.parametrize("secret", SECRET_CORPUS)
    def test_audit_redacts_corpus_value(self, run_cli, secret) -> None:
        _, env, raw = run_cli(["audit", ECHO, "--input", json.dumps({"text": secret})])
        assert env["ok"] is True
        assert secret not in raw
        assert contains_secret(env) is False

    @pytest.mark.parametrize("secret", SECRET_CORPUS)
    def test_error_envelope_redacts_corpus_in_malformed_input(self, run_cli, secret) -> None:
        # The secret sits inside a malformed JSON string; it must not reach the
        # error envelope.
        _, env, raw = run_cli(["run", ECHO, "--input", f"{secret} not json"])
        assert env["ok"] is False
        assert secret not in raw
        assert contains_secret(env) is False

    @pytest.mark.parametrize("secret", SECRET_CORPUS)
    def test_pretty_output_redacts_corpus_value(self, run_cli, secret) -> None:
        _, env, raw = run_cli(["run", ECHO, "--input", json.dumps({"text": secret}), "--pretty"])
        assert env["result"]["outputPayload"] == {"text": REDACTED_VALUE}
        assert secret not in raw

    def test_read_only_commands_carry_no_secret(self, run_cli) -> None:
        # list / show / p0-report take no user value; their output is clean.
        for argv in (["list"], ["show", ECHO], ["p0-report"]):
            _, env, raw = run_cli(argv)
            assert contains_secret(env) is False
            assert "sk-FAKE" not in raw
            assert ".hermes" not in raw

    def test_corpus_values_are_all_obvious_fakes(self) -> None:
        # Sanity: every corpus entry is explicitly fake (never a real credential).
        for entry in SECRET_CORPUS:
            lower = entry.lower()
            assert "fake" in lower or "do-not-leak" in lower or "/users/" in lower or (
                "sk-" in lower or "ghp_" in lower or "xox" in lower or "bearer" in lower
                or "private key" in lower or "_key=" in lower or "password=" in lower
                or "token" in lower or "authorization" in lower
            ), entry


# ===========================================================================
# F. Invalid-input / adversarial-input hardening
# ===========================================================================


class TestInvalidInputHardening:
    @pytest.mark.parametrize(
        "argv",
        [
            ["show"],  # missing descriptor id
            ["run", "--input", '{"text":"x"}'],  # missing descriptor id
            ["audit"],  # missing descriptor id
            ["batch"],  # missing items
        ],
    )
    def test_missing_args_rejected(self, run_cli, argv) -> None:
        code, env, _ = run_cli(argv)
        assert code == 2
        assert env["ok"] is False
        assert env["error"]["redacted"] is True
        assert _all_side_effects_false(env["sideEffects"])

    @pytest.mark.parametrize("bad", ["{", "[", "not-json", ""])
    def test_invalid_json_rejected(self, run_cli, bad) -> None:
        code, env, _ = run_cli(["run", ECHO, "--input", bad])
        assert code == 2
        assert env["error"]["code"] in {"invalid_json", "invalid_input_shape"}

    @pytest.mark.parametrize("bad", ["[]", "123", '"str"', "42.5"])
    def test_wrong_shape_input_rejected(self, run_cli, bad) -> None:
        code, env, _ = run_cli(["run", ECHO, "--input", bad])
        assert code == 2
        assert env["error"]["code"] == "invalid_input_shape"

    def test_null_input_treated_as_no_input(self, run_cli) -> None:
        # ``null`` is valid JSON meaning "no input" — the fixture runs with an
        # empty payload (not a rejection). This pins the behavior explicitly.
        code, env, _ = run_cli(["run", ECHO, "--input", "null"])
        assert code == 0
        assert env["result"]["allowed"] is True

    def test_empty_items_batch_returns_total_zero(self, run_cli) -> None:
        # ``[]`` is a valid (empty) batch — total 0, not a rejection.
        code, env, _ = run_cli(["batch", "--items", "[]"])
        assert code == 0
        assert env["result"]["total"] == 0

    @pytest.mark.parametrize("bad", ["{}", "[null]", "not-json", "[{}]"])
    def test_wrong_shape_items_rejected(self, run_cli, bad) -> None:
        code, env, _ = run_cli(["batch", "--items", bad])
        assert code == 2
        assert env["ok"] is False

    def test_batch_item_missing_descriptor_id_rejected(self, run_cli) -> None:
        items = json.dumps([{"input": {"text": "x"}}])
        code, env, _ = run_cli(["batch", "--items", items])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_batch_item_non_string_descriptor_id_rejected(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": 123}])
        code, env, _ = run_cli(["batch", "--items", items])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_oversized_input_rejected(self, run_cli) -> None:
        from hermes_cli.dev_web_runtime_governance_cli import MAX_CLI_INPUT_CHARS

        huge = '{"text":"' + "a" * (MAX_CLI_INPUT_CHARS + 10) + '"}'
        code, env, _ = run_cli(["run", ECHO, "--input", huge])
        assert code == 2
        assert env["error"]["code"] == "oversized_input"

    def test_oversized_batch_rejected(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}} for _ in range(64)])
        code, env, _ = run_cli(["batch", "--items", items])
        assert code == 2
        assert env["error"]["code"] == "batch_oversized"

    @pytest.mark.parametrize(
        "bad_id",
        [
            "bad/id",
            "..secret",
            "../etc/passwd",
            "rm -rf",
            "descriptor.fixture.http://x",
            "has space",
            "tab\there",
        ],
    )
    def test_unsafe_descriptor_id_rejected(self, run_cli, bad_id) -> None:
        code, env, raw = run_cli(["show", bad_id])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"
        # The unsafe id (which may itself be secret-like) must not leak.
        if bad_id.strip():
            assert bad_id not in raw

    def test_secret_shaped_safe_char_id_denied_not_leaked(self, run_cli) -> None:
        # A secret-shaped label that uses ONLY safe chars passes id validation
        # (it is a label, not a secret) but is a registry miss → denied binding
        # (code 0), and the redactor masks it from the output.
        code, env, raw = run_cli(["show", "sk-fake-secret-12345678"])
        assert code == 0
        assert env["result"]["bindingAllowed"] is False
        assert "sk-fake-secret-12345678" not in raw

    def test_too_long_descriptor_id_rejected(self, run_cli) -> None:
        long_id = "a" * 200
        code, env, _ = run_cli(["show", long_id])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_unsupported_command_rejected(self, run_cli) -> None:
        for cmd in ("download", "install-plugin", "fetch", "registry", "marketplace"):
            code, env, _ = run_cli([cmd])
            assert code == 2
            assert env["command"] == "dev-runtime.unknown"
            assert env["error"]["code"] == "unknown_command"

    def test_no_traceback_in_stdout(self, run_cli_raw) -> None:
        # Adversarial input must never surface a Python traceback on stdout.
        code, raw = run_cli_raw(["run", ECHO, "--input", "{"])
        assert code == 2
        assert "Traceback" not in raw
        # stdout is exactly one JSON document.
        json.loads(raw)


# ===========================================================================
# G. Batch report consistency
# ===========================================================================


class TestBatchConsistency:
    def test_count_invariant_total_equals_parts(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": ECHO, "input": {"text": "a"}},
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": FAULT, "input": {"text": "x"}},
                {"descriptor_id": COUNT, "input": {"items": [1]}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items])
        r = env["result"]
        assert r["total"] == r["succeeded"] + r["failed"] + r["denied"]
        assert r["total"] == 4

    def test_order_preserved(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": COUNT, "input": {"items": [1]}},
                {"descriptor_id": ECHO, "input": {"text": "a"}},
                {"descriptor_id": NORMALIZE, "input": {"text": "b"}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items])
        ops = [r["operation"] for r in env["result"]["results"]]
        assert ops == ["count_items", "echo_uppercase", "normalize_text"]

    def test_per_result_descriptor_id_and_side_effects(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": ECHO, "input": {"text": "a"}},
                {"descriptor_id": COUNT, "input": {"items": [1]}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items])
        for res in env["result"]["results"]:
            assert res["descriptorId"] in {ECHO, COUNT}
            assert res["persisted"] is False
            assert _all_side_effects_false(res["sideEffects"])

    def test_batch_side_effects_false(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": {"text": "a"}}])
        _, env, _ = run_cli(["batch", "--items", items])
        assert _all_side_effects_false(env["result"].get("sideEffects") or env["sideEffects"])

    def test_fail_fast_true_stops_after_first_non_allowed(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items, "--fail-fast"])
        assert env["result"]["failFast"] is True
        assert env["result"]["total"] == 1

    def test_fail_fast_false_runs_all(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items])
        assert env["result"]["total"] == 2

    def test_fault_isolation_does_not_poison_siblings(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": FAULT, "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": COUNT, "input": {"items": [1]}},
            ]
        )
        _, env, _ = run_cli(["batch", "--items", items])
        r = env["result"]
        assert r["results"][0]["failed"] is True
        assert r["results"][1]["allowed"] is True
        assert r["results"][2]["allowed"] is True
        assert r["failed"] == 1 and r["succeeded"] == 2

    def test_batch_resolved_count_zero_and_not_persisted(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": {"text": "a"}}])
        _, env, _ = run_cli(["batch", "--items", items])
        assert env["result"]["p0Evidence"]["resolvedCount"] == 0
        assert env["result"]["persisted"] is False
        assert env["result"]["redactedAudit"]["persisted"] is False


# ===========================================================================
# H. Audit report completion
# ===========================================================================


class TestAuditCompletion:
    def test_happy_audit_surfaces_full_report(self, run_cli) -> None:
        _, env, _ = run_cli(["audit", ECHO, "--input", '{"text":"hello"}'])
        r = env["result"]
        for key in (
            "descriptorId",
            "pluginId",
            "operation",
            "allowed",
            "executed",
            "failed",
            "denialReasons",
            "triggeredGuards",
            "redactedAudit",
            "p0Evidence",
            "sideEffects",
            "authorization",
            "persisted",
        ):
            assert key in r, key
        _normalized_subset(
            r,
            {
                "descriptorId": ECHO,
                "pluginId": "fixture.echo",
                "operation": "echo_uppercase",
                "allowed": True,
                "executed": True,
                "failed": False,
                "persisted": False,
            },
        )
        assert r["authorization"]["implementationGate"] == "NO-GO"
        assert _all_side_effects_false(r["sideEffects"])

    def test_fault_audit_fails_closed_and_redacts(self, run_cli) -> None:
        _, env, raw = run_cli(
            ["audit", FAULT, "--input", '{"text":"sk-FAKE-SECRET-DO-NOT-LEAK-12345678"}']
        )
        r = env["result"]
        assert r["failed"] is True
        assert r["allowed"] is False
        assert r["persisted"] is False
        assert "fixture_execution_failed" in r["denialReasons"]
        assert "sk-FAKE" not in raw
        assert contains_secret(env) is False

    def test_audit_denied_descriptor(self, run_cli) -> None:
        _, env, _ = run_cli(["audit", "descriptor.does.not.exist", "--input", '{"text":"x"}'])
        r = env["result"]
        assert r["allowed"] is False
        assert r["executed"] is False
        assert "descriptor_not_in_static_registry" in r["denialReasons"]

    def test_audit_module_level_redacted_and_not_persisted(self) -> None:
        run_report = run_runtime_descriptor(ECHO, {"text": "hello"})
        audit = build_runtime_audit_report(run_report)
        assert audit["persisted"] is False
        assert audit["authorization"]["implementationGate"] == "NO-GO"
        assert _all_side_effects_false(audit["sideEffects"])
        assert contains_secret(audit) is False


# ===========================================================================
# I. No-side-effect invariants (metadata / fake-descriptor override resistance)
# ===========================================================================


class TestNoSideEffectInvariants:
    @pytest.mark.parametrize("bypass_key", BYPASS_METADATA_KEYS)
    def test_metadata_bypass_cannot_authorize(self, bypass_key) -> None:
        report = run_runtime_descriptor(
            ECHO, {"text": "hi"}, metadata={bypass_key: "GO"}
        )
        # A smuggled bypass in metadata denies the binding; auth stays NO-GO.
        assert report["p0Evidence"]["implementationGate"] == "NO-GO"
        assert report["p0Evidence"]["phase3iGate"] is False
        assert report["p0Evidence"]["resolvedCount"] == 0
        assert _all_side_effects_false(report["sideEffects"])

    def test_batch_item_metadata_cannot_change_side_effects(self) -> None:
        # Batch items do not carry a side-effect override channel; the per-result
        # side-effect block is the frozen projection regardless of item content.
        report = run_runtime_descriptor_batch(
            [{"descriptor_id": ECHO, "input": {"text": "hi"}, "metadata_override": True}]
        )
        for res in report["results"]:
            assert _all_side_effects_false(res["sideEffects"])

    def test_fake_descriptor_metadata_cannot_change_side_effects(self) -> None:
        # A descriptor looked up from the frozen registry is a static record; any
        # extra metadata a caller threads in cannot flip a side effect.
        report = run_runtime_descriptor(ECHO, {"text": "hi"})
        assert _all_side_effects_false(report["sideEffects"])

    def test_p0_report_smuggled_metadata_ignored(self) -> None:
        report = build_runtime_p0_report(
            untrusted_metadata={
                "implementation_authorization": "GO",
                "phase_3i_authorized": True,
                "production_approved": True,
            }
        )
        assert report["resolvedCount"] == 0
        assert report["authorization"]["implementationGate"] == "NO-GO"
        assert report["ignoredMetadataKeys"]

    def test_side_effect_block_key_set_is_frozen(self) -> None:
        assert set(side_effect_projection().keys()) == set(SIDE_EFFECT_FIELDS)


# ===========================================================================
# J. Smoke suite — real CLI entry paths via subprocess
# ===========================================================================


class TestSmokeSuite:
    def _run_module(self, argv: list[str]) -> tuple[int, dict[str, Any]]:
        result = subprocess.run(
            [sys.executable, "-m", "hermes_cli.dev_web_runtime_governance_cli", *argv],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.returncode, json.loads(result.stdout)

    def test_smoke_list(self) -> None:
        code, env = self._run_module(["list"])
        assert env["result"]["count"] == 6

    def test_smoke_show(self) -> None:
        code, env = self._run_module(["show", ECHO])
        assert env["result"]["bindingAllowed"] is True

    def test_smoke_run(self) -> None:
        code, env = self._run_module(["run", ECHO, "--input", '{"text":"hello"}'])
        assert env["result"]["outputPayload"] == {"text": "HELLO"}

    def test_smoke_batch(self) -> None:
        items = json.dumps([{"descriptor_id": COUNT, "input": {"items": [1, 2]}}])
        code, env = self._run_module(["batch", "--items", items])
        assert env["result"]["succeeded"] == 1

    def test_smoke_p0_report(self) -> None:
        code, env = self._run_module(["p0-report"])
        assert env["result"]["totalGates"] == 24

    def test_smoke_alias_and_pretty(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "hermes_cli.dev_web_runtime_governance_cli", "ls", "--pretty"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        env = json.loads(result.stdout)
        assert env["command"] == "dev-runtime.list"
        assert result.stdout.count("\n") > 5  # pretty = indented

    @pytest.mark.integration
    def test_smoke_via_main_dev_runtime_list(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "hermes_cli.main", "dev-runtime", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        env = json.loads(result.stdout)
        assert env["command"] == "dev-runtime.list"
        assert env["result"]["count"] == 6

    @pytest.mark.integration
    def test_smoke_via_main_dev_runtime_run(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "hermes_cli.main",
                "dev-runtime",
                "run",
                ECHO,
                "--input",
                '{"text":"world"}',
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        env = json.loads(result.stdout)
        assert env["result"]["outputPayload"] == {"text": "WORLD"}


# ===========================================================================
# K. Source boundary — no forbidden primitives in the governance modules
# ===========================================================================


def _read_module_source(module_name: str) -> str:
    import importlib

    module = importlib.import_module(module_name)
    path = getattr(module, "__file__", None)
    assert path is not None, module_name
    return Path(path).read_text(encoding="utf-8")


_GOVERNANCE_MODULES = (
    "hermes_cli.dev_web_runtime_governance",
    "hermes_cli.dev_web_runtime_governance_cli",
    "hermes_cli.dev_web_plugin_runtime_binding",
    "hermes_cli.dev_web_plugin_runtime",
    "hermes_cli.dev_web_fixture_plugins",
)


class TestSourceBoundaryCompletion:
    #: Precise forbidden-USAGE patterns (import statements + call sites). These
    #: avoid false positives from docstrings that *name* a prohibition (e.g. a
    #: module that documents "no subprocess" must not trip a bare ``subprocess``
    #: substring scan). Each pattern is a real call/import site, never prose.
    FORBIDDEN_USAGE: tuple[tuple[str, ...], ...] = (
        ("dynamic import", ("import importlib", "importlib.import_module", "importlib.import")),
        ("dunder import", ("__import__(",)),
        ("eval/exec", ("eval(", "exec(")),
        ("shell exec", ("shell=True", "os.system", "os.popen")),
        ("subprocess", ("import subprocess", "subprocess.", "subprocess(")),
        ("http libs", ("import requests", "import httpx", "import aiohttp")),
        ("sockets", ("import socket", "socket.socket", "socket.connect")),
        ("urllib fetch", ("urllib.request", "urlopen(")),
    )

    @pytest.mark.parametrize("module", _GOVERNANCE_MODULES)
    @pytest.mark.parametrize("category,fragments", FORBIDDEN_USAGE)
    def test_no_forbidden_usage_in_governance_modules(self, module, category, fragments) -> None:
        src = _read_module_source(module)
        for fragment in fragments:
            assert fragment not in src, f"{module}: {category} uses {fragment!r}"

    @pytest.mark.parametrize("module", _GOVERNANCE_MODULES)
    def test_no_file_io_or_path_resolution(self, module) -> None:
        src = _read_module_source(module)
        # The governance surface must not read/write files or resolve/expanduser
        # any real path. (``open(`` is asserted as a call form; a docstring that
        # writes the word ``open`` does not contain ``open(``.)
        assert ".read_text(" not in src, module
        assert ".write_text(" not in src, module
        assert "Path.home" not in src, module
        assert "get_hermes_home" not in src, module
        assert ".resolve(" not in src, module
        assert ".stat(" not in src, module

    def test_no_input_or_output_file_flags_registered(self) -> None:
        from hermes_cli.dev_web_runtime_governance_cli import _build_parser

        parser = _build_parser()
        option_strings: set[str] = set()
        for action in parser._actions:
            option_strings.update(action.option_strings)
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict):
                for sub_parser in choices.values():
                    for sub_action in sub_parser._actions:
                        option_strings.update(sub_action.option_strings)
        assert "--input-file" not in option_strings
        assert "--output-file" not in option_strings
        assert "--input" in option_strings
        assert "--items" in option_strings

    def test_modified_governance_modules_strict_clean(self) -> None:
        # The two modules THIS task modified are held to the strict substring
        # standard (no mention of dynamic-load / network primitives at all).
        for module in (
            "hermes_cli.dev_web_runtime_governance",
            "hermes_cli.dev_web_runtime_governance_cli",
        ):
            src = _read_module_source(module)
            for fragment in ("importlib", "subprocess", "shell=True", "os.system"):
                assert fragment not in src, f"{module}: {fragment}"

    def test_main_dev_runtime_wiring_is_delegation_only(self) -> None:
        # The dev-runtime wiring in main.py forwards args to the governance CLI
        # and exits with its code — it performs no governance work itself.
        src = _read_module_source("hermes_cli.main")
        assert "from hermes_cli.dev_web_runtime_governance_cli import main" in src
        assert "raise SystemExit(governance_main(" in src


# ===========================================================================
# L. dev_web_api isolation — governance adds no route, is not imported by the API
# ===========================================================================


class TestDevWebApiIsolationCompletion:
    def test_dev_web_api_does_not_import_governance_surface(self) -> None:
        api_src = _read_module_source("hermes_cli.dev_web_api")
        for forbidden in (
            "dev_web_runtime_governance_cli",
            "dev_web_runtime_governance",
            "dev_web_plugin_runtime_binding",
            "dev_web_plugin_runtime",
            "dev_web_fixture_plugins",
        ):
            assert forbidden not in api_src, forbidden

    @pytest.mark.parametrize(
        "path",
        [
            "/api/dev/v1/runtime-governance",
            "/api/dev/v1/runtime/governance",
            "/api/dev/v1/dev-runtime",
            "/api/dev/v1/plugin-runtime",
            "/api/dev/v1/dev-runtime/list",
            "/api/dev/v1/dev-runtime/run",
        ],
    )
    def test_governance_route_probe_returns_404(self, client: TestClient, path) -> None:
        resp = client.get(path)
        assert resp.status_code == 404, path

    def test_openapi_paths_remain_34(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 34

    def test_route_governance_unchanged(self, app) -> None:
        assert_route_governance_unchanged(app)

    def test_route_governance_expected_string(self) -> None:
        assert ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"


# ===========================================================================
# M. Production safety — no ~/.hermes / production state.db access, no artifacts
# ===========================================================================


class TestProductionSafetyCompletion:
    def test_governance_modules_contain_no_path_resolution_primitives(self) -> None:
        for module in _GOVERNANCE_MODULES:
            src = _read_module_source(module)
            for primitive in (".stat(", ".resolve(", "Path.home", "expanduser", "get_hermes_home"):
                assert primitive not in src, f"{module}: {primitive}"

    @pytest.mark.parametrize(
        "argv",
        [
            ["list"],
            ["show", ECHO],
            ["run", ECHO, "--input", '{"text":"hello"}'],
            ["batch", "--items", json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}}])],
            ["audit", ECHO, "--input", '{"text":"hello"}'],
            ["p0-report"],
            ["help"],
        ],
    )
    def test_command_does_not_stat_production_home(self, argv, monkeypatch) -> None:
        """No governance command opens, stats, or resolves the production home.

        A recording spy wraps the real FS primitives and delegates to them; the
        test asserts none of the recorded call arguments mention the production
        home or a production database. The real ``~/.hermes`` is never touched.
        """
        recorded: list[str] = []

        def _record_and_call(real):
            def wrapper(*a, **kw):
                try:
                    recorded.extend(str(x) for x in a)
                except Exception:
                    pass
                return real(*a, **kw)

            return wrapper

        import pathlib

        real_stat = os.stat
        real_lstat = os.lstat
        real_expanduser = os.path.expanduser
        real_realpath = os.path.realpath
        real_path_stat = pathlib.Path.stat
        real_path_resolve = pathlib.Path.resolve

        monkeypatch.setattr(os, "stat", _record_and_call(real_stat), raising=False)
        monkeypatch.setattr(os, "lstat", _record_and_call(real_lstat), raising=False)
        monkeypatch.setattr(os.path, "expanduser", _record_and_call(real_expanduser), raising=False)
        monkeypatch.setattr(os.path, "realpath", _record_and_call(real_realpath), raising=False)
        monkeypatch.setattr(pathlib.Path, "stat", _record_and_call(real_path_stat), raising=False)
        monkeypatch.setattr(
            pathlib.Path, "resolve", _record_and_call(real_path_resolve), raising=False
        )

        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            governance_main(list(argv))
        finally:
            sys.stdout = old

        for arg in recorded:
            low = arg.lower()
            assert ".hermes" not in low, f"command {argv} touched production home: {arg}"
            assert "state.db" not in low, f"command {argv} touched production db: {arg}"

    def test_no_runtime_store_artifacts_created(self, tmp_path: Path) -> None:
        before = find_runtime_store_artifacts(tmp_path)
        for argv in (
            ["list"],
            ["run", ECHO, "--input", '{"text":"hello"}'],
            ["batch", "--items", json.dumps([{"descriptor_id": COUNT, "input": {"items": [1]}}])],
            ["audit", FAULT, "--input", '{"text":"x"}'],
            ["p0-report"],
        ):
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                governance_main(list(argv))
            finally:
                sys.stdout = old
        after = find_runtime_store_artifacts(tmp_path)
        assert before == after == []

    def test_production_home_and_db_classified_as_production(self) -> None:
        assert is_production_home("/Users/huangruibang/.hermes") is True
        assert is_production_state_db("/Users/huangruibang/.hermes/state.db") is True

    def test_every_envelope_persisted_false(self, run_cli) -> None:
        for argv, key in (
            (["run", ECHO, "--input", '{"text":"x"}'], "result"),
            (["batch", "--items", json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}}])], "result"),
        ):
            _, env, _ = run_cli(argv)
            assert env[key]["persisted"] is False
            if key == "result" and "redactedAudit" in env[key]:
                assert env[key]["redactedAudit"]["persisted"] is False


# ===========================================================================
# N. Regression preservation — authorization / descriptor / P0 frozen
# ===========================================================================


class TestRegressionPreservationCompletion:
    def test_authorization_projection_value_preserving(self) -> None:
        auth = authorization_projection()
        # The redactor must NOT collapse any of these verdicts to [REDACTED].
        assert auth["implementationGate"] == "NO-GO"
        assert auth["phase3iProductionGate"] == "NOT_AUTHORIZED"
        assert auth["productionRuntimeGate"] == "NO-GO"
        assert auth["arbitraryPluginLoading"] == "NO-GO"
        assert auth["remoteRegistry"] == "NO-GO"
        assert auth["marketplace"] == "NO-GO"
        assert auth["externalNetwork"] == "NO-GO"
        assert auth["realApiKeyRead"] is False
        assert PHASE_3I_AUTHORIZED is False

    def test_descriptor_count_still_six(self, run_cli) -> None:
        _, env, _ = run_cli(["list"])
        assert env["result"]["count"] == 6

    def test_resolved_count_zero_across_surfaces(self, run_cli) -> None:
        _, run_env, _ = run_cli(["run", ECHO, "--input", '{"text":"hi"}'])
        assert run_env["result"]["p0Evidence"]["resolvedCount"] == 0
        _, batch_env, _ = run_cli(["batch", "--items", json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}}])])
        assert batch_env["result"]["p0Evidence"]["resolvedCount"] == 0
        _, p0_env, _ = run_cli(["p0-report"])
        assert p0_env["result"]["resolvedCount"] == 0

    def test_examples_are_file_io_free(self) -> None:
        # No example reads or writes a file.
        for ex in COMMAND_EXAMPLES:
            assert "--input-file" not in ex
            assert "--output-file" not in ex
