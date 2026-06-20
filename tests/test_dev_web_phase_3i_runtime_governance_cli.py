"""Phase 3I Runtime Governance CLI tests.

A dedicated regression suite for the **Phase 3I dev-only runtime governance CLI**
(:mod:`hermes_cli.dev_web_runtime_governance` +
:mod:`hermes_cli.dev_web_runtime_governance_cli`): a developer-facing command
group that exposes the *already-implemented* descriptor-backed fixture runtime
through ``list / show / run / batch / audit / p0-report / help`` subcommands.

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

import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_safety_baseline as baseline
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_p0_evidence import (
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
)
from hermes_cli.dev_web_plugin_runtime import RUNTIME_FLAGS_FROZEN
from hermes_cli.dev_web_plugin_runtime_binding import (
    DESCRIPTOR_BINDING_SOURCE,
    REVIEWED_FIXTURE_DESCRIPTORS,
    resolve_runtime_descriptor_binding,
    run_dev_plugin_batch_from_descriptors,
)
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
from hermes_cli.dev_web_runtime_governance_cli import (
    COMMANDS,
    MAX_CLI_INPUT_CHARS,
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
    """Invoke the governance CLI in-process and return ``(exit_code, parsed_json)``."""
    import io

    def _invoke(argv: list[str]) -> tuple[int, dict[str, Any]]:
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = governance_main(list(argv))
        finally:
            sys.stdout = old
        return code, json.loads(buf.getvalue())

    return _invoke


# ===========================================================================
# 1. Governance projection module
# ===========================================================================


class TestGovernanceProjections:
    """Direct tests of the report projection functions (no CLI parsing)."""

    def test_assert_no_side_effect_surface(self) -> None:
        assert_no_side_effect_surface()  # must not raise

    def test_authorization_projection_is_all_no_go(self) -> None:
        auth = authorization_projection()
        assert auth["implementationGate"] == IMPLEMENTATION_AUTHORIZATION == "NO-GO"
        assert auth["productionRuntimeGate"] == REAL_RUNTIME == "NO-GO"
        assert auth["newRouteGate"] == NEW_ROUTE == "NO-GO"
        assert auth["productionRolloutGate"] == PRODUCTION_ROLLOUT == "NO-GO"
        # Phase 3I is frozen False → NOT_AUTHORIZED.
        assert PHASE_3I_AUTHORIZED is False
        assert auth["phase3iProductionGate"] == "NOT_AUTHORIZED"

    def test_list_returns_six_reviewed_fixture_descriptors(self) -> None:
        report = list_runtime_descriptors()
        assert report["schemaVersion"] == GOVERNANCE_VERSION
        assert report["registrySource"] == DESCRIPTOR_BINDING_SOURCE
        assert report["count"] == 6
        ids = {d["descriptorId"] for d in report["descriptors"]}
        assert ids == {ECHO, NORMALIZE, VALIDATE, COUNT, REDACT, FAULT}
        # Every descriptor is a static, reviewed, dev-only, fixture-only record
        # that carries NO execution surface and requests NO route change.
        for d in report["descriptors"]:
            assert d["source"] == DESCRIPTOR_BINDING_SOURCE
            assert d["devOnly"] is True
            assert d["fixtureOnly"] is True
            assert d["reviewedFixture"] is True
            assert d["executable"] is False
            assert d["remote"] is False
            assert d["marketplace"] is False
            assert d["production"] is False
            assert d["routeChange"] is False
        assert report["allDevOnly"] is True
        assert report["allFixtureOnly"] is True
        assert report["allReviewedFixture"] is True
        assert report["anyExecutable"] is False
        assert report["anyRouteChange"] is False
        assert report["redactionApplied"] is True
        # Listing performs NO execution — the report has no result/audit surface.
        assert "results" not in report
        assert contains_secret(report) is False

    def test_show_allowed_binding_for_echo(self) -> None:
        report = show_runtime_descriptor_binding(ECHO)
        assert report["descriptorId"] == ECHO
        assert report["bindingAllowed"] is True
        assert report["pluginId"] == "fixture.echo"
        assert report["operation"] == "echo_uppercase"
        assert report["denialReasons"] == []
        assert report["runtimeFlags"] == RUNTIME_FLAGS_FROZEN
        # show does NOT execute — there is no outputPayload / executed flag.
        assert "outputPayload" not in report
        assert report["p0Projection"]["resolved"] is False

    def test_show_denied_binding_for_unknown_id(self) -> None:
        report = show_runtime_descriptor_binding("descriptor.does.not.exist")
        assert report["bindingAllowed"] is False
        assert "descriptor_not_in_static_registry" in report["denialReasons"]
        assert report["redactedDescriptor"] == {"notFound": True, "redactionApplied": True}

    def test_show_denied_binding_for_non_string_id(self) -> None:
        report = show_runtime_descriptor_binding(12345)  # type: ignore[arg-type]
        assert report["bindingAllowed"] is False
        assert "descriptor_not_in_static_registry" in report["denialReasons"]

    def test_run_echo_uppercase(self) -> None:
        report = run_runtime_descriptor(ECHO, {"text": "hello"})
        assert report["allowed"] is True
        assert report["executed"] is True
        assert report["failed"] is False
        assert report["outputPayload"] == {"text": "HELLO"}
        assert report["persisted"] is False
        assert report["p0Evidence"]["resolved"] is False
        assert report["p0Evidence"]["implementationGate"] == "NO-GO"

    def test_run_normalize_text(self) -> None:
        report = run_runtime_descriptor(NORMALIZE, {"text": "  Hello   World  "})
        assert report["allowed"] is True
        assert report["outputPayload"] == {"text": "Hello World"}

    def test_run_count_items_honors_input(self) -> None:
        report = run_runtime_descriptor(COUNT, {"items": [1, 2, 3, 4, 5]})
        assert report["allowed"] is True
        assert report["outputPayload"] == {"count": 5}

    def test_run_validate_required_keys(self) -> None:
        report = run_runtime_descriptor(
            VALIDATE, {"payload": {"a": 1, "b": 2}, "required": ["a", "b"]}
        )
        assert report["allowed"] is True
        assert report["outputPayload"]["valid"] is True

    def test_run_denied_unknown_descriptor(self) -> None:
        report = run_runtime_descriptor("descriptor.does.not.exist", {"text": "x"})
        assert report["allowed"] is False
        assert report["executed"] is False
        assert "descriptor_not_in_static_registry" in report["denialReasons"]
        assert report["outputPayload"] == {}

    def test_run_fault_fails_closed(self) -> None:
        report = run_runtime_descriptor(FAULT, {"text": "x"})
        assert report["failed"] is True
        assert report["allowed"] is False
        assert "fixture_execution_failed" in report["denialReasons"]
        # The fake secret in the deliberate failure message must be redacted.
        assert contains_secret(report) is False
        assert "sk-FAKE" not in json.dumps(report)

    def test_run_secret_input_is_redacted(self) -> None:
        report = run_runtime_descriptor(ECHO, {"text": "sk-secret12345abcd"})
        # echo_uppercase masks a secret-shaped input value before uppercasing.
        assert report["outputPayload"] == {"text": REDACTED_VALUE}
        assert contains_secret(report) is False

    def test_run_hermes_path_input_is_redacted(self) -> None:
        report = run_runtime_descriptor(ECHO, {"text": "/Users/test/.hermes/state.db"})
        assert report["outputPayload"] == {"text": REDACTED_VALUE}
        assert ".hermes" not in json.dumps(report["outputPayload"])

    def test_metadata_smuggling_does_not_authorize(self) -> None:
        # A request that smuggles an authorization bypass in metadata is denied
        # by the binding layer; the authorization flags stay NO-GO regardless.
        report = run_runtime_descriptor(
            ECHO,
            {"text": "hi"},
            metadata={"implementation_authorization": "GO", "phase_3i_authorized": True},
        )
        assert report["allowed"] is False
        # Authorization never flips to GO via smuggled metadata.
        assert report["p0Evidence"]["implementationGate"] == "NO-GO"
        assert report["p0Evidence"]["phase3iGate"] is False
        assert contains_secret(report) is False

    def test_batch_all_allowed_with_per_item_input(self) -> None:
        report = run_runtime_descriptor_batch(
            [
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": COUNT, "input": {"items": [1, 2, 3]}},
            ]
        )
        assert report["total"] == 2
        assert report["succeeded"] == 2
        assert report["failed"] == 0
        assert report["denied"] == 0
        assert report["failFast"] is False
        assert report["results"][0]["outputPayload"] == {"text": "HI"}
        assert report["results"][1]["outputPayload"] == {"count": 3}
        assert report["p0Evidence"]["resolved"] is False

    def test_batch_mixed_isolates_success_denial_failure(self) -> None:
        report = run_runtime_descriptor_batch(
            [
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": FAULT, "input": {"text": "x"}},
                {"descriptor_id": COUNT, "input": {"items": [1]}},
            ]
        )
        assert report["total"] == 4
        assert report["succeeded"] == 2  # echo + math
        assert report["denied"] == 1  # unknown id
        assert report["failed"] == 1  # deliberate fault
        # Order preserved.
        assert report["results"][0]["allowed"] is True
        assert report["results"][1]["allowed"] is False
        assert report["results"][2]["failed"] is True
        assert report["results"][3]["allowed"] is True

    def test_batch_fail_fast_stops_after_first_non_allowed(self) -> None:
        report = run_runtime_descriptor_batch(
            [
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": COUNT, "input": {"items": [1]}},
            ],
            fail_fast=True,
        )
        assert report["failFast"] is True
        assert report["total"] == 1  # stopped after the first denial
        assert report["results"][0]["allowed"] is False

    def test_batch_fail_fast_false_runs_all(self) -> None:
        report = run_runtime_descriptor_batch(
            [
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
            ],
            fail_fast=False,
        )
        assert report["total"] == 2
        assert report["succeeded"] == 1
        assert report["denied"] == 1

    def test_batch_canonical_path_when_no_input(self) -> None:
        # When no item carries an explicit input and every id resolves, the
        # governance batch delegates to the canonical batch machinery.
        descriptors = [
            d for d in REVIEWED_FIXTURE_DESCRIPTORS if d["descriptorId"] in {ECHO, NORMALIZE}
        ]
        canonical = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="gov-canon")
        governance = run_runtime_descriptor_batch(
            [{"descriptor_id": ECHO}, {"descriptor_id": NORMALIZE}]
        )
        # Same total / succeeded / classification as the canonical batch.
        assert governance["total"] == canonical.total
        assert governance["succeeded"] == canonical.succeeded
        assert governance["failed"] == canonical.failed
        assert governance["denied"] == canonical.denied

    def test_batch_redacted_and_not_persisted(self) -> None:
        report = run_runtime_descriptor_batch(
            [{"descriptor_id": ECHO, "input": {"text": "sk-secret12345abcd"}}]
        )
        assert report["persisted"] is False
        assert report["redactedAudit"]["persisted"] is False
        assert contains_secret(report) is False

    def test_p0_report_resolved_count_zero(self) -> None:
        report = build_runtime_p0_report()
        assert report["totalGates"] == 24
        assert report["resolvedCount"] == 0
        assert report["unresolvedCount"] == 24
        assert report["implementationAuthorization"] in {"NO-GO", REDACTED_VALUE}
        assert report["realRuntime"] == "NO-GO"
        assert report["newRoute"] == "NO-GO"
        assert report["productionRollout"] == "NO-GO"
        assert report["phase3iAuthorized"] is False
        assert report["authorization"]["implementationGate"] == "NO-GO"
        assert report["authorization"]["phase3iProductionGate"] == "NOT_AUTHORIZED"

    def test_p0_report_ignores_smuggled_authorization(self) -> None:
        report = build_runtime_p0_report(
            untrusted_metadata={"implementation_authorization": "GO", "phase_3i_authorized": True}
        )
        assert report["resolvedCount"] == 0
        assert report["authorization"]["implementationGate"] == "NO-GO"
        # Smuggled bypass keys are reported as ignored, never honored.
        assert report["ignoredMetadataKeys"]

    def test_audit_report_is_redacted(self) -> None:
        run_report = run_runtime_descriptor(ECHO, {"text": "hello"})
        audit = build_runtime_audit_report(run_report)
        assert audit["allowed"] is True
        assert audit["redactedAudit"]
        assert audit["p0Evidence"]["resolved"] is False
        assert audit["persisted"] is False
        assert audit["authorization"]["implementationGate"] == "NO-GO"
        assert contains_secret(audit) is False

    def test_audit_report_handles_non_mapping(self) -> None:
        audit = build_runtime_audit_report("not a mapping")  # type: ignore[arg-type]
        assert audit["malformed"] is True
        assert audit["redactionApplied"] is True


# ===========================================================================
# 2. CLI — list / show / run / batch / audit / p0-report
# ===========================================================================


class TestCliList:
    def test_list_exits_zero_and_is_json_safe(self, run_cli) -> None:
        code, env = run_cli(["list"])
        assert code == 0
        assert env["ok"] is True
        assert env["command"] == "list"
        assert env["result"]["count"] == 6
        assert env["authorization"]["implementationGate"] == "NO-GO"
        assert contains_secret(env) is False

    def test_list_descriptors_are_reviewed_fixture_only(self, run_cli) -> None:
        _, env = run_cli(["list"])
        for d in env["result"]["descriptors"]:
            assert d["devOnly"] is True
            assert d["fixtureOnly"] is True
            assert d["reviewedFixture"] is True
            assert d["executable"] is False
            assert d["production"] is False
            assert d["remote"] is False
            assert d["marketplace"] is False
            assert d["routeChange"] is False

    def test_list_has_no_raw_secret_or_production_path(self, run_cli) -> None:
        _, env = run_cli(["list"])
        blob = json.dumps(env)
        assert ".hermes" not in blob
        assert "state.db" not in blob
        assert contains_secret(env) is False


class TestCliShow:
    def test_show_allowed_binding(self, run_cli) -> None:
        code, env = run_cli(["show", ECHO])
        assert code == 0
        assert env["result"]["bindingAllowed"] is True
        assert env["result"]["pluginId"] == "fixture.echo"

    def test_show_denied_binding_for_unknown(self, run_cli) -> None:
        code, env = run_cli(["show", "descriptor.does.not.exist"])
        assert code == 0  # the command ran; the binding is denied
        assert env["result"]["bindingAllowed"] is False

    def test_show_missing_id_is_rejected(self, run_cli) -> None:
        code, env = run_cli(["show"])
        assert code == 2
        assert env["ok"] is False
        assert env["error"]["code"] == "invalid_descriptor_id"


class TestCliRun:
    def test_run_echo_uppercases(self, run_cli) -> None:
        code, env = run_cli(["run", ECHO, "--input", '{"text":"hello"}'])
        assert code == 0
        assert env["result"]["allowed"] is True
        assert env["result"]["outputPayload"] == {"text": "HELLO"}

    def test_run_normalize(self, run_cli) -> None:
        code, env = run_cli(["run", NORMALIZE, "--input", '{"text":"  a   b  "}'])
        assert code == 0
        assert env["result"]["outputPayload"] == {"text": "a b"}

    def test_run_count_items(self, run_cli) -> None:
        code, env = run_cli(["run", COUNT, "--input", '{"items":[1,2,3]}'])
        assert code == 0
        assert env["result"]["outputPayload"] == {"count": 3}

    def test_run_denied_descriptor_does_not_execute(self, run_cli) -> None:
        code, env = run_cli(["run", "descriptor.does.not.exist", "--input", '{"text":"x"}'])
        assert code == 0
        assert env["result"]["allowed"] is False
        assert env["result"]["executed"] is False

    def test_run_fault_fails_closed(self, run_cli) -> None:
        code, env = run_cli(["run", FAULT, "--input", '{"text":"x"}'])
        assert code == 0
        assert env["result"]["failed"] is True
        assert env["result"]["allowed"] is False
        assert "sk-FAKE" not in json.dumps(env)

    def test_run_secret_input_redacted(self, run_cli) -> None:
        code, env = run_cli(["run", ECHO, "--input", '{"text":"sk-secret12345abcd"}'])
        assert code == 0
        assert env["result"]["outputPayload"] == {"text": REDACTED_VALUE}
        assert contains_secret(env) is False

    def test_run_hermes_path_input_redacted(self, run_cli) -> None:
        code, env = run_cli(
            ["run", ECHO, "--input", '{"text":"/Users/test/.hermes/state.db"}']
        )
        assert code == 0
        assert env["result"]["outputPayload"] == {"text": REDACTED_VALUE}
        blob = json.dumps(env)
        assert ".hermes/state.db" not in blob

    def test_run_authorization_stays_no_go(self, run_cli) -> None:
        _, env = run_cli(["run", ECHO, "--input", '{"text":"hello"}'])
        assert env["authorization"]["implementationGate"] == "NO-GO"
        assert env["authorization"]["phase3iProductionGate"] == "NOT_AUTHORIZED"
        assert env["authorization"]["productionRuntimeGate"] == "NO-GO"
        assert env["result"]["p0Evidence"]["resolved"] is False


class TestCliBatch:
    def test_batch_all_allowed(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": COUNT, "input": {"items": [1, 2, 3]}},
            ]
        )
        code, env = run_cli(["batch", "--items", items])
        assert code == 0
        r = env["result"]
        assert r["total"] == 2 and r["succeeded"] == 2 and r["failed"] == 0 and r["denied"] == 0
        assert r["results"][1]["outputPayload"] == {"count": 3}

    def test_batch_mixed_isolated(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": FAULT, "input": {"text": "x"}},
            ]
        )
        code, env = run_cli(["batch", "--items", items])
        assert code == 0
        r = env["result"]
        assert r["total"] == 3 and r["succeeded"] == 1 and r["denied"] == 1 and r["failed"] == 1

    def test_batch_fail_fast_true(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
            ]
        )
        code, env = run_cli(["batch", "--items", items, "--fail-fast"])
        assert code == 0
        assert env["result"]["failFast"] is True
        assert env["result"]["total"] == 1

    def test_batch_fail_fast_false_runs_all(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": "descriptor.does.not.exist", "input": {"text": "x"}},
                {"descriptor_id": ECHO, "input": {"text": "hi"}},
            ]
        )
        code, env = run_cli(["batch", "--items", items])
        assert code == 0
        assert env["result"]["total"] == 2

    def test_batch_order_preserved(self, run_cli) -> None:
        items = json.dumps(
            [
                {"descriptor_id": COUNT, "input": {"items": [1]}},
                {"descriptor_id": ECHO, "input": {"text": "a"}},
                {"descriptor_id": NORMALIZE, "input": {"text": "b"}},
            ]
        )
        _, env = run_cli(["batch", "--items", items])
        ops = [r["operation"] for r in env["result"]["results"]]
        assert ops == ["count_items", "echo_uppercase", "normalize_text"]

    def test_batch_secret_redaction(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": {"text": "ghp_abcdefgh12345"}}])
        _, env = run_cli(["batch", "--items", items])
        assert env["result"]["results"][0]["outputPayload"] == {"text": REDACTED_VALUE}
        assert contains_secret(env) is False

    def test_batch_p0_resolved_count_zero(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": {"text": "hi"}}])
        _, env = run_cli(["batch", "--items", items])
        assert env["result"]["p0Evidence"]["resolvedCount"] == 0


class TestCliAudit:
    def test_audit_runs_and_projects_redacted_audit(self, run_cli) -> None:
        code, env = run_cli(["audit", ECHO, "--input", '{"text":"hello"}'])
        assert code == 0
        assert env["result"]["allowed"] is True
        assert env["result"]["redactedAudit"]
        assert env["result"]["p0Evidence"]["resolved"] is False
        assert contains_secret(env) is False


class TestCliP0Report:
    def test_p0_report_totals_and_authorization(self, run_cli) -> None:
        code, env = run_cli(["p0-report"])
        assert code == 0
        r = env["result"]
        assert r["totalGates"] == 24
        assert r["resolvedCount"] == 0
        assert env["authorization"]["implementationGate"] == "NO-GO"
        assert env["authorization"]["phase3iProductionGate"] == "NOT_AUTHORIZED"
        assert env["authorization"]["productionRuntimeGate"] == "NO-GO"
        assert env["authorization"]["newRouteGate"] == "NO-GO"
        assert env["authorization"]["productionRolloutGate"] == "NO-GO"


class TestCliHelp:
    def test_help_exits_zero_and_states_boundary(self, run_cli) -> None:
        code, env = run_cli(["help"])
        assert code == 0
        help_text = env["result"]["help"]
        assert "dev-only" in help_text.lower()
        assert "fixture-only" in help_text.lower()
        assert "production-forbidden" in help_text.lower()
        assert env["result"]["commands"] == list(COMMANDS)

    def test_no_args_prints_help(self, run_cli) -> None:
        code, env = run_cli([])
        assert code == 0
        assert env["command"] == "help"


# ===========================================================================
# 3. CLI — invalid input / failure paths
# ===========================================================================


class TestCliInvalidInput:
    def test_invalid_json_rejected(self, run_cli) -> None:
        code, env = run_cli(["run", ECHO, "--input", "not json"])
        assert code == 2
        assert env["ok"] is False
        assert env["error"]["code"] == "invalid_json"
        assert env["error"]["redacted"] is True

    def test_oversized_json_rejected(self, run_cli) -> None:
        huge = '{"text":"' + "a" * (MAX_CLI_INPUT_CHARS + 10) + '"}'
        code, env = run_cli(["run", ECHO, "--input", huge])
        assert code == 2
        assert env["error"]["code"] == "oversized_input"

    def test_wrong_shape_input_rejected(self, run_cli) -> None:
        code, env = run_cli(["run", ECHO, "--input", "[1,2,3]"])
        assert code == 2
        assert env["error"]["code"] == "invalid_input_shape"

    def test_missing_descriptor_id_rejected(self, run_cli) -> None:
        code, env = run_cli(["run", "--input", '{"text":"x"}'])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_unsafe_descriptor_id_with_slash_rejected(self, run_cli) -> None:
        code, env = run_cli(["show", "bad/id"])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_unsafe_descriptor_id_traversal_rejected(self, run_cli) -> None:
        code, env = run_cli(["show", "..secret"])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_unsafe_descriptor_id_space_rejected(self, run_cli) -> None:
        code, env = run_cli(["show", "rm -rf"])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_unknown_command_rejected(self, run_cli) -> None:
        code, env = run_cli(["frobnicate"])
        assert code == 2
        assert env["error"]["code"] == "unknown_command"

    def test_batch_oversized_rejected(self, run_cli) -> None:
        items = json.dumps(
            [{"descriptor_id": ECHO, "input": {"text": "x"}} for _ in range(64)]
        )
        code, env = run_cli(["batch", "--items", items])
        assert code == 2
        assert env["error"]["code"] == "batch_oversized"

    def test_batch_item_missing_descriptor_id_rejected(self, run_cli) -> None:
        items = json.dumps([{"input": {"text": "x"}}])
        code, env = run_cli(["batch", "--items", items])
        assert code == 2
        assert env["error"]["code"] == "invalid_descriptor_id"

    def test_batch_not_a_list_rejected(self, run_cli) -> None:
        code, env = run_cli(["batch", "--items", '{"descriptor_id":"x"}'])
        assert code == 2
        assert env["error"]["code"] == "invalid_input_shape"

    def test_batch_item_bad_input_shape_rejected(self, run_cli) -> None:
        items = json.dumps([{"descriptor_id": ECHO, "input": [1, 2, 3]}])
        code, env = run_cli(["batch", "--items", items])
        assert code == 2
        assert env["error"]["code"] == "invalid_input_shape"

    def test_invalid_input_message_is_redacted(self, run_cli) -> None:
        code, env = run_cli(["run", ECHO, "--input", "sk-leakedsecret12345 not json"])
        assert code == 2
        blob = json.dumps(env)
        assert "sk-leakedsecret12345" not in blob


# ===========================================================================
# 4. Source boundary — the new modules contain no forbidden surface
# ===========================================================================


def _module_source(module: Any) -> str:
    path = inspect.getsourcefile(module)
    assert path is not None
    return Path(path).read_text(encoding="utf-8")


class TestSourceBoundary:
    """Scan the governance + CLI module sources for forbidden surfaces."""

    @pytest.fixture()
    def gov_src(self) -> str:
        from hermes_cli import dev_web_runtime_governance as gov

        return _module_source(gov)

    @pytest.fixture()
    def cli_src(self) -> str:
        from hermes_cli import dev_web_runtime_governance_cli as cli

        return _module_source(cli)

    @pytest.mark.parametrize("fragment", [
        "importlib",
        "__import__(",
        "eval(",
        "exec(",
        "shell=True",
        "os.system",
        "import requests",
        "import httpx",
        "import aiohttp",
        "socket.connect",
        "urllib.request",
    ])
    def test_no_dynamic_loading_or_network(self, gov_src, cli_src, fragment) -> None:
        assert fragment not in gov_src, fragment
        assert fragment not in cli_src, fragment

    def test_no_subprocess_in_governance_modules(self, gov_src, cli_src) -> None:
        assert "subprocess" not in gov_src
        assert "subprocess" not in cli_src

    def test_no_file_io_or_path_resolution(self, gov_src, cli_src) -> None:
        for src in (gov_src, cli_src):
            assert ".read_text(" not in src
            assert ".write_text(" not in src
            assert ".resolve(" not in src
            assert ".expanduser(" not in src
            # No raw open()/stat() of files (input or output).
            assert "open(" not in src

    def test_no_marketplace_or_remote_registry_fetch(self, gov_src, cli_src) -> None:
        for src in (gov_src, cli_src):
            assert "marketplace_fetch" not in src
            assert "remote_registry_fetch" not in src
            assert "fetch_plugin" not in src

    def test_no_input_file_or_output_file_flags(self) -> None:
        # The CLI must not register input/output file flags (no file I/O). We
        # inspect the parser's option strings (incl. subparsers) rather than
        # grepping source so a docstring that *documents* the prohibition is not
        # a false positive.
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
        assert "--input" in option_strings  # the only input flag, JSON only
        assert "--items" in option_strings

    def test_boundary_constants_frozen_true(self) -> None:
        from hermes_cli import dev_web_runtime_governance as gov

        assert gov.NO_REAL_PLUGIN_RUNTIME is True
        assert gov.NO_ARBITRARY_PLUGIN_LOADING is True
        assert gov.NO_LOCAL_PLUGIN_DIRECTORY_LOADING is True
        assert gov.NO_REMOTE_REGISTRY is True
        assert gov.NO_MARKETPLACE is True
        assert gov.NO_EXTERNAL_NETWORK is True
        assert gov.NO_REAL_API_KEY_READ is True
        assert gov.NO_NEW_ROUTE is True
        assert gov.NO_PRODUCTION_ACCESS is True
        assert gov.NO_HERMES_HOME_ACCESS is True
        assert gov.NO_PRODUCTION_STATE_DB_ACCESS is True
        assert gov.NO_RUNTIME_STORE_WRITE is True
        assert gov.NO_FILE_READ is True
        assert gov.NO_FILE_WRITE is True


# ===========================================================================
# 5. dev_web_api isolation — governance adds no route, is not imported by the API
# ===========================================================================


class TestDevWebApiIsolation:
    def test_dev_web_api_does_not_import_governance_modules(self) -> None:
        api_src = _module_source(__import__("hermes_cli.dev_web_api", fromlist=["x"]))
        # The FastAPI app must not import the governance / runtime / binding /
        # fixture modules — the CLI is a separate surface that adds no route.
        assert "dev_web_runtime_governance" not in api_src
        assert "dev_web_runtime_governance_cli" not in api_src

    def test_runtime_governance_route_probe_returns_404(self, client: TestClient) -> None:
        for path in (
            "/api/dev/v1/runtime-governance",
            "/api/dev/v1/runtime/governance",
            "/api/dev/v1/dev-runtime",
            "/api/dev/v1/plugin-runtime",
        ):
            resp = client.get(path)
            assert resp.status_code == 404, path

    def test_openapi_paths_remain_34(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 34

    def test_route_governance_unchanged(self, app) -> None:
        # 34/34/5/0/1/1 — the CLI adds no HTTP route.
        assert_route_governance_unchanged(app)

    def test_route_governance_expected_string(self) -> None:
        assert ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"


# ===========================================================================
# 6. Production safety — no ~/.hermes / production state.db access, no artifacts
# ===========================================================================


class TestProductionSafety:
    def test_governance_modules_have_no_home_path_resolution(self) -> None:
        from hermes_cli import dev_web_runtime_governance as gov
        from hermes_cli import dev_web_runtime_governance_cli as cli

        for src in (_module_source(gov), _module_source(cli)):
            # No Path.home / expanduser / resolve / stat / open of any real path.
            assert "Path.home" not in src
            assert "expanduser" not in src
            assert ".resolve(" not in src
            assert ".stat(" not in src

    def test_importing_modules_does_not_reference_hermes_home(self) -> None:
        # The modules never derive a HERMES_HOME path; they only reference
        # production as a denial-target string inside the inherited guards. We
        # assert no path-resolution call sites (the real risk) — a docstring that
        # names the production home as a prohibition is allowed documentation.
        from hermes_cli import dev_web_runtime_governance as gov
        from hermes_cli import dev_web_runtime_governance_cli as cli

        for src in (_module_source(gov), _module_source(cli)):
            assert "get_hermes_home" not in src
            assert "Path.home" not in src
            assert "expanduser" not in src
            assert ".resolve(" not in src
            assert ".stat(" not in src

    def test_production_home_classified_as_production(self) -> None:
        # The safety policy treats the production home as production (denied).
        # This is a string-policy check — the real path is never opened.
        assert is_production_home("/Users/huangruibang/.hermes") is True

    def test_production_state_db_classified(self) -> None:
        assert is_production_state_db("/Users/huangruibang/.hermes/state.db") is True

    def test_cli_run_creates_no_runtime_store_artifacts(self, run_cli, tmp_path: Path) -> None:
        before = find_runtime_store_artifacts(tmp_path)
        run_cli(["run", ECHO, "--input", '{"text":"hello"}'])
        run_cli(["batch", "--items", json.dumps([{"descriptor_id": COUNT, "input": {"items": [1]}}])])
        run_cli(["p0-report"])
        after = find_runtime_store_artifacts(tmp_path)
        assert before == after == []

    def test_every_report_is_not_persisted(self, run_cli) -> None:
        _, env = run_cli(["run", ECHO, "--input", '{"text":"x"}'])
        assert env["result"]["persisted"] is False
        _, env = run_cli(["batch", "--items", json.dumps([{"descriptor_id": ECHO, "input": {"text": "x"}}])])
        assert env["result"]["persisted"] is False
        assert env["result"]["redactedAudit"]["persisted"] is False


# ===========================================================================
# 7. Regression preservation — the underlying runtime + registry are unchanged
# ===========================================================================


class TestRegressionPreservation:
    def test_reviewed_descriptors_still_bind(self) -> None:
        for descriptor in REVIEWED_FIXTURE_DESCRIPTORS:
            binding = resolve_runtime_descriptor_binding(descriptor)
            assert binding.binding_allowed is True, descriptor["descriptorId"]
            assert binding.dev_only is True
            assert binding.fixture_only is True

    def test_canonical_batch_still_works(self) -> None:
        descriptors = [d for d in REVIEWED_FIXTURE_DESCRIPTORS if d["descriptorId"] == ECHO]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="regression")
        assert batch.total == 1
        assert batch.succeeded == 1
        assert batch.p0_evidence["resolved"] is False

    def test_descriptor_count_unchanged(self) -> None:
        report = list_runtime_descriptors()
        assert report["count"] == len(REVIEWED_FIXTURE_DESCRIPTORS) == 6


# ===========================================================================
# 8. End-to-end subprocess — the hermes dev-runtime wiring is real
# ===========================================================================


class TestSubprocessWiring:
    """Invoke the governance CLI as a real subprocess to prove the wiring."""

    def _run(self, argv: list[str]) -> tuple[int, dict[str, Any]]:
        result = subprocess.run(
            [sys.executable, "-m", "hermes_cli.dev_web_runtime_governance_cli", *argv],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.returncode, json.loads(result.stdout)

    def test_subprocess_list(self) -> None:
        code, env = self._run(["list"])
        assert code == 0
        assert env["ok"] is True
        assert env["result"]["count"] == 6

    def test_subprocess_run(self) -> None:
        code, env = self._run(["run", ECHO, "--input", '{"text":"hello"}'])
        assert code == 0
        assert env["result"]["outputPayload"] == {"text": "HELLO"}

    def test_subprocess_p0_report(self) -> None:
        code, env = self._run(["p0-report"])
        assert code == 0
        assert env["result"]["totalGates"] == 24
        assert env["result"]["resolvedCount"] == 0

    @pytest.mark.integration
    def test_full_cli_wiring_via_main(self) -> None:
        """``hermes dev-runtime list`` routes through the main CLI dispatcher."""
        result = subprocess.run(
            [sys.executable, "-m", "hermes_cli.main", "dev-runtime", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        env = json.loads(result.stdout)
        assert env["ok"] is True
        assert env["command"] == "list"
        assert env["result"]["count"] == 6
        assert env["authorization"]["implementationGate"] == "NO-GO"

    @pytest.mark.integration
    def test_full_cli_wiring_run_via_main(self) -> None:
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
