"""Phase 3I Dev-only Local Plugin Runtime MVP tests.

A dedicated regression suite for the **Phase 3I dev-only local plugin runtime**:
the reviewed fixture plugins (:mod:`hermes_cli.dev_web_fixture_plugins`) and the
runtime itself (:mod:`hermes_cli.dev_web_plugin_runtime`), plus the runtime-themed
proof scenarios in :mod:`hermes_cli.dev_web_sandbox_scenarios`.

Scope (frozen, mirrors the task authorization):

  - **code allowed / production forbidden.** The runtime executes ONLY reviewed
    fixture operations bound through a hardcoded allowlist. No arbitrary plugin
    loading, no remote registry, no marketplace, no external plugin fetch, no
    provider-generated / LLM-generated plugin install, no real API-key read, no
    external network, no new route, no production rollout.
  - Every forbidden path is a **fake / temp / string-policy** target; the real
    ``~/.hermes`` and production ``state.db`` are never opened, stated, or
    resolved (not even for metadata). Every secret is an obvious **fake**.

A successful fixture execution is **dev-only partial evidence**. It is **never**
Implementation Authorization GO, **never** Phase 3I production authorization,
**never** real-runtime authorization, **never** a P0 resolution.
``resolved_count`` stays 0 and the authorization flags stay NO-GO /
not-authorized no matter what runs or what untrusted metadata a request carries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_fixture_plugins import (
    MAX_FIXTURE_INPUT_BYTES,
    FIXTURE_ALLOWLIST,
    FIXTURE_OPERATION_NAMES,
    FIXTURE_PLUGIN_IDS,
    FIXTURE_REGISTRY,
    FixtureExecutionError,
    FixtureInputError,
    deliberate_failure,
    echo_uppercase,
    get_fixture_registry,
    is_known_fixture,
    lookup_fixture,
    summarize_keys,
)
from hermes_cli.dev_web_p0_evidence import (
    GATE_STATUS_PARTIAL_EVIDENCE,
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    HumanApprovalRecord,
    create_human_approval,
    evaluate_p0_evidence,
    is_approval_valid,
)
from hermes_cli.dev_web_plugin_runtime import (
    MAX_REQUEST_ITEMS_PER_CATEGORY,
    PLUGIN_RUNTIME_AUDIT_SOURCE,
    PLUGIN_RUNTIME_VERSION,
    RUNTIME_FLAGS_FROZEN,
    RUNTIME_POLICY,
    PluginRuntimePolicy,
    PluginRuntimeRequest,
    PluginRuntimeResult,
    RuntimeBinding,
    assert_no_side_effect_surface,
    is_runtime_result_safe,
    resolve_runtime_binding,
    run_dev_plugin,
    validate_runtime_binding,
)
from hermes_cli.dev_web_safety_baseline import (
    PRODUCTION_HERMES_HOME,
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    find_runtime_store_artifacts,
    route_governance_counts,
)
from hermes_cli.dev_web_sandbox_guards import REDACTED_VALUE, contains_secret
from hermes_cli.dev_web_sandbox_runner import run_proof_scenario, run_proof_scenarios
from hermes_cli.dev_web_sandbox_scenarios import (
    FIXED_SCENARIOS,
    LOCAL_RUNTIME_DESCRIPTOR_EXECUTION_DENIED,
    LOCAL_RUNTIME_ECHO_DESCRIPTOR_ALLOWED,
    LOCAL_RUNTIME_KILL_SWITCH_DENIED,
    LOCAL_RUNTIME_NETWORK_DENIED,
    LOCAL_RUNTIME_SECRET_DENIED,
    RUNTIME_PROOF_SCENARIOS,
    get_runtime_proof_scenarios,
)

#: Obvious fake secrets used to prove redaction. None is real.
FAKE_SECRETS: tuple[str, ...] = (
    "sk-FAKE-SECRET-DO-NOT-LEAK-12345678",
    "Authorization: Bearer fake-bearer-runtime",
    "ghp_fakegeneratedgithubtoken1234",
)

#: Obvious fake / forbidden paths. None is opened or stated.
FAKE_FORBIDDEN_PATHS: tuple[str, ...] = (
    "~/.hermes",
    "/fake/production/state.db",
    "/tmp/runtime/plugin_runtime.jsonl",
)


def _blob(obj: Any) -> str:
    """Flatten any structure to a string for substring assertions."""
    return repr(obj)


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


def _req(**kwargs: Any) -> PluginRuntimeRequest:
    return PluginRuntimeRequest(**kwargs)


# ===========================================================================
# 0. Boundary constants + fixtures sanity
# ===========================================================================


class TestBoundaryAndRegistry:
    def test_assert_no_side_effect_surface_runtime(self) -> None:
        assert_no_side_effect_surface()

    def test_assert_no_side_effect_surface_fixtures(self) -> None:
        from hermes_cli.dev_web_fixture_plugins import assert_no_side_effect_surface as fx

        fx()

    def test_fixture_registry_is_frozen_and_complete(self) -> None:
        assert len(FIXTURE_REGISTRY) == 3
        assert len(FIXTURE_ALLOWLIST) == 3
        assert FIXTURE_PLUGIN_IDS == frozenset({"fixture.echo", "fixture.inspect", "fixture.fault"})
        assert FIXTURE_OPERATION_NAMES == frozenset(
            {"echo_uppercase", "summarize_keys", "deliberate_failure"}
        )

    def test_runtime_flags_are_frozen_constants(self) -> None:
        assert RUNTIME_FLAGS_FROZEN == {
            "dev_only": True,
            "fixture_only": True,
            "production_access": False,
            "external_network": False,
            "real_secret_read": False,
            "route_change": False,
            "runtime_store_write": False,
            "arbitrary_plugin_load": False,
            "remote_plugin_fetch": False,
            "marketplace_access": False,
        }

    def test_version_and_source_stable(self) -> None:
        assert PLUGIN_RUNTIME_VERSION == "phase-3i-dev-only-local-plugin-runtime-mvp-v1"
        assert PLUGIN_RUNTIME_AUDIT_SOURCE == "dev_web_plugin_runtime"

    def test_get_fixture_registry_returns_defensive_copy(self) -> None:
        a = get_fixture_registry()
        b = get_fixture_registry()
        assert a == b
        assert a is not b
        assert a is not FIXTURE_REGISTRY


# ===========================================================================
# A. Fixture operation behavior (pure, redaction-safe)
# ===========================================================================


class TestFixtureOperations:
    def test_echo_uppercase_basic(self) -> None:
        assert dict(echo_uppercase({"text": "hello"})) == {"text": "HELLO"}

    def test_echo_uppercase_redacts_secret_shaped_input(self) -> None:
        out = dict(echo_uppercase({"text": "sk-fake-secret-12345678"}))
        assert out == {"text": REDACTED_VALUE}

    def test_echo_uppercase_rejects_non_string_text(self) -> None:
        with pytest.raises(FixtureInputError):
            echo_uppercase({"text": 123})

    def test_echo_uppercase_rejects_non_mapping(self) -> None:
        with pytest.raises(FixtureInputError):
            echo_uppercase("not-a-mapping")  # type: ignore[arg-type]

    def test_echo_uppercase_rejects_oversized_input(self) -> None:
        with pytest.raises(FixtureInputError):
            echo_uppercase({"text": "x" * (MAX_FIXTURE_INPUT_BYTES + 1)})

    def test_summarize_keys_basic(self) -> None:
        out = dict(summarize_keys({"a": 1, "b": 2}))
        assert out == {"keys": ["a", "b"], "count": 2}

    def test_summarize_keys_never_leaks_values(self) -> None:
        out = dict(summarize_keys({"a": "sk-fake-secret-12345678", "b": "secret-value"}))
        # Values are never projected; only keys + count.
        assert out == {"keys": ["a", "b"], "count": 2}
        assert "sk-fake-secret-12345678" not in _blob(out)

    def test_summarize_keys_redacts_secret_shaped_keys(self) -> None:
        out = dict(summarize_keys({"sk-fake-key-12345678": 1, "ok": 2}))
        assert out["keys"][0] == REDACTED_VALUE
        assert out["keys"][1] == "ok"
        assert out["count"] == 2

    def test_summarize_keys_rejects_non_mapping(self) -> None:
        with pytest.raises(FixtureInputError):
            summarize_keys(["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_deliberate_failure_always_raises_with_fake_secret(self) -> None:
        with pytest.raises(FixtureExecutionError) as exc_info:
            deliberate_failure({"x": 1})
        # The fake secret is in the message (the runtime must redact it).
        assert "sk-FAKE-SECRET-DO-NOT-LEAK" in str(exc_info.value)

    def test_deliberate_failure_rejects_non_mapping_as_input_error(self) -> None:
        with pytest.raises(FixtureInputError):
            deliberate_failure("not-a-mapping")  # type: ignore[arg-type]

    def test_lookup_fixture_exact_membership(self) -> None:
        assert lookup_fixture("fixture.echo", "echo_uppercase") is not None
        assert lookup_fixture("fixture.echo", "summarize_keys") is None
        assert lookup_fixture("local.path.plugin", "run") is None
        assert is_known_fixture("fixture.fault", "deliberate_failure") is True
        assert is_known_fixture("fixture.echo", "shell") is False


# ===========================================================================
# A'. Runtime happy path
# ===========================================================================


class TestRuntimeHappyPath:
    def test_echo_uppercase_executes(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hello"})
        )
        assert result.allowed is True
        assert result.executed is True
        assert result.failed is False
        assert dict(result.output_payload) == {"text": "HELLO"}
        assert dict(result.runtime_flags) == RUNTIME_FLAGS_FROZEN
        # All the "did not happen" flags are False.
        for flag in ("production_access", "external_network", "real_secret_read",
                     "route_change", "runtime_store_write", "arbitrary_plugin_load",
                     "remote_plugin_fetch", "marketplace_access"):
            assert result.runtime_flags[flag] is False
        assert result.runtime_flags["dev_only"] is True
        assert result.runtime_flags["fixture_only"] is True

    def test_echo_uppercase_p0_partial_evidence_not_resolved(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"})
        )
        assert result.p0_evidence["classification"] == "partial_evidence"
        assert result.p0_evidence["resolved"] is False
        assert result.p0_evidence["resolvedCount"] == 0
        assert result.p0_evidence["implementationGate"] == "NO-GO"
        assert result.p0_evidence["phase3iGate"] is False
        assert result.p0_evidence["realRuntimeGate"] == "NO-GO"

    def test_summarize_keys_executes_deterministic(self) -> None:
        r1 = run_dev_plugin(
            _req(plugin_id="fixture.inspect", operation="summarize_keys", input_payload={"a": 1, "b": 2})
        )
        r2 = run_dev_plugin(
            _req(plugin_id="fixture.inspect", operation="summarize_keys", input_payload={"a": 1, "b": 2})
        )
        assert r1.allowed and r1.executed
        assert dict(r1.output_payload) == {"keys": ["a", "b"], "count": 2}
        assert dict(r1.output_payload) == dict(r2.output_payload)

    def test_summarize_keys_no_secret_value_leak(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.inspect",
                operation="summarize_keys",
                input_payload={"leak": "sk-fake-secret-12345678"},
            )
        )
        assert result.allowed is True
        blob = _blob(result.to_safe_dict())
        assert "sk-fake-secret-12345678" not in blob
        assert contains_secret(result.to_safe_dict()) is False

    def test_descriptor_binding_executes_fixture(self) -> None:
        # The binding may be supplied entirely via a clean descriptor.
        result = run_dev_plugin(
            _req(
                descriptor={
                    "pluginId": "fixture.echo",
                    "operation": "echo_uppercase",
                    "source": "descriptor_only",
                },
                input_payload={"text": "via-descriptor"},
            )
        )
        assert result.allowed is True
        assert result.executed is True
        assert dict(result.output_payload) == {"text": "VIA-DESCRIPTOR"}

    def test_is_runtime_result_safe_on_happy_path(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "x"})
        )
        assert is_runtime_result_safe(result) is True
        assert is_runtime_result_safe(result.to_safe_dict()) is True


# ===========================================================================
# B. Runtime denied path
# ===========================================================================


class TestRuntimeDeniedPath:
    def test_unknown_plugin_id_denied(self) -> None:
        result = run_dev_plugin(_req(plugin_id="local.path.plugin", operation="run"))
        assert result.allowed is False
        assert result.executed is False
        assert "fixture_not_in_allowlist" in result.denial_reasons
        assert "fixture_binding" in result.triggered_guards

    def test_remote_registry_plugin_id_denied(self) -> None:
        result = run_dev_plugin(_req(plugin_id="remote.registry.plugin", operation="fetch"))
        assert result.allowed is False
        assert "fixture_not_in_allowlist" in result.denial_reasons

    def test_unknown_operation_denied(self) -> None:
        result = run_dev_plugin(_req(plugin_id="fixture.echo", operation="not_a_real_op"))
        assert result.allowed is False
        assert "fixture_not_in_allowlist" in result.denial_reasons

    @pytest.mark.parametrize("verb", ("import", "__import__", "shell", "execute", "exec", "eval", "run"))
    def test_dangerous_operation_verb_denied(self, verb: str) -> None:
        result = run_dev_plugin(_req(plugin_id="fixture.echo", operation=verb))
        assert result.allowed is False
        assert "dangerous_operation_denied" in result.denial_reasons
        assert "fixture_not_in_allowlist" in result.denial_reasons

    def test_missing_plugin_id_denied(self) -> None:
        result = run_dev_plugin(_req(operation="echo_uppercase"))
        assert result.allowed is False
        assert "plugin_id_missing" in result.denial_reasons

    def test_missing_operation_denied(self) -> None:
        result = run_dev_plugin(_req(plugin_id="fixture.echo"))
        assert result.allowed is False
        assert "operation_missing" in result.denial_reasons

    @pytest.mark.parametrize(
        "field,value",
        (
            ("module", "pkg.mod"),
            ("command", "python plugin.py"),
            ("entrypoint", "plugin:run"),
            ("url", "https://example.com/plugin.py"),
            ("importlib", "malicious.module"),
            ("dockerImage", "evil:latest"),
        ),
    )
    def test_descriptor_dangerous_field_denied(self, field: str, value: str) -> None:
        descriptor = {"pluginId": "fixture.echo", "operation": "echo_uppercase", field: value}
        result = run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", descriptor=descriptor))
        assert result.allowed is False
        assert result.executed is False
        assert "descriptor_carries_execution_surface" in result.denial_reasons

    @pytest.mark.parametrize(
        "source_type,reason",
        (
            ("remote_registry", "remote_registry_denied"),
            ("marketplace", "marketplace_denied"),
            ("external_fetch", "external_fetch_denied"),
            ("provider_generated", "provider_generated_denied"),
            ("llm_generated", "llm_generated_denied"),
        ),
    )
    def test_descriptor_untrusted_source_denied(self, source_type: str, reason: str) -> None:
        descriptor = {
            "pluginId": "fixture.echo",
            "operation": "echo_uppercase",
            "sourceType": source_type,
        }
        result = run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", descriptor=descriptor))
        assert result.allowed is False
        assert reason in result.denial_reasons

    def test_descriptor_provider_generated_key_denied(self) -> None:
        descriptor = {"pluginId": "fixture.echo", "operation": "echo_uppercase", "providerGenerated": True}
        result = run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", descriptor=descriptor))
        assert result.allowed is False
        assert "descriptor_carries_execution_surface" in result.denial_reasons

    def test_descriptor_llm_generated_key_denied(self) -> None:
        descriptor = {"pluginId": "fixture.echo", "operation": "echo_uppercase", "llmGenerated": True}
        result = run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", descriptor=descriptor))
        assert result.allowed is False
        assert "descriptor_carries_execution_surface" in result.denial_reasons

    def test_descriptor_malformed_denied(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", descriptor="not-a-mapping")
        )
        assert result.allowed is False
        assert "malformed_descriptor" in result.denial_reasons

    def test_network_target_denied(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_network_targets=("https://example.com",),
                requested_capabilities=("network.request",),
            )
        )
        assert result.allowed is False
        assert "network_request_denied" in result.denial_reasons
        assert "network_deny" in result.triggered_guards

    def test_secret_request_denied(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_secret_names=("OPENAI_API_KEY",),
                requested_capabilities=("secrets.read",),
            )
        )
        assert result.allowed is False
        assert "secret_request_denied" in result.denial_reasons
        assert "secret_unavailable" in result.triggered_guards

    @pytest.mark.parametrize("path", FAKE_FORBIDDEN_PATHS)
    def test_filesystem_forbidden_path_denied(self, path: str) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_filesystem_paths=(path,),
            )
        )
        assert result.allowed is False
        assert "filesystem_boundary" in result.triggered_guards

    def test_production_access_capability_denied(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_capabilities=("production.access",),
            )
        )
        assert result.allowed is False
        assert "production_access_denied" in result.denial_reasons

    def test_route_modify_capability_denied(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_capabilities=("routes.modify",),
            )
        )
        assert result.allowed is False
        assert "routes_modify_denied" in result.denial_reasons

    def test_plugin_execute_capability_denied(self) -> None:
        # Requesting the real plugin.execute capability is denied; the fixture
        # executes via the allowlist, NOT via a capability grant.
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_capabilities=("plugin.execute",),
            )
        )
        assert result.allowed is False
        assert "plugin_execution_denied" in result.denial_reasons

    def test_kill_switch_active_denied(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", kill_switch_state=True)
        )
        assert result.allowed is False
        assert result.executed is False
        assert "kill_switch_active" in result.denial_reasons
        assert "kill_switch" in result.triggered_guards

    def test_kill_switch_invalid_state_denied(self) -> None:
        # A non-bool / non-None kill switch is treated as armed → fail closed.
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", kill_switch_state="off")  # type: ignore[arg-type]
        )
        assert result.allowed is False
        assert "kill_switch_active" in result.denial_reasons

    @pytest.mark.parametrize(
        "metadata",
        (
            {"implementation_authorization": "GO"},
            {"implementationAuthorization": "GO"},
            {"phase_3i_authorized": True},
            {"phase3iAuthorized": True},
            {"production_approved": True},
            {"route_exception_approved": True},
            {"real_runtime_authorized": True},
            {"approved": True, "human_signoff": "accepted"},
            {"trust_token": "fake", "review_board_decision": "accepted"},
            {"p0_resolved": True, "resolved_ids": ["P0-15"]},
        ),
    )
    def test_metadata_authorization_smuggling_denied(self, metadata: dict[str, Any]) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                input_payload={"text": "hi"},
                metadata=metadata,
            )
        )
        assert result.allowed is False
        assert "metadata_authorization_smuggling_denied" in result.denial_reasons
        # Authorization flags stay frozen regardless.
        assert result.p0_evidence["implementationGate"] == "NO-GO"
        assert result.p0_evidence["phase3iGate"] is False

    def test_oversized_capabilities_denied(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_capabilities=tuple(f"cap.alias.{i}" for i in range(MAX_REQUEST_ITEMS_PER_CATEGORY + 1)),
            )
        )
        assert result.allowed is False
        assert "oversized_input_capabilities" in result.denial_reasons


# ===========================================================================
# C. Runtime failure handling (fail-closed, redacted)
# ===========================================================================


class TestRuntimeFailurePath:
    def test_deliberate_failure_is_caught_and_redacted(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1})
        )
        assert result.executed is True  # the fixture WAS invoked
        assert result.allowed is False  # but it failed
        assert result.failed is True
        assert "fixture_execution_failed" in result.denial_reasons
        assert "failure_handler" in result.triggered_guards
        assert result.p0_evidence["classification"] == "failure_mode_evidence"
        # The fake secret must NOT leak into any projection.
        blob = _blob(result.to_safe_dict())
        for secret in FAKE_SECRETS:
            assert secret not in blob
        assert contains_secret(result.to_safe_dict()) is False

    def test_failure_redacted_error_recorded(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1})
        )
        assert len(result.errors) == 1
        assert "sk-FAKE-SECRET-DO-NOT-LEAK" not in result.errors[0]

    def test_failure_audit_is_safe_and_in_memory(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1})
        )
        assert result.redacted_audit["persisted"] is False
        assert result.redacted_audit["redactionApplied"] is True
        assert contains_secret(result.redacted_audit) is False
        assert result.redacted_audit["runtimeFlags"] == RUNTIME_FLAGS_FROZEN

    def test_fixture_input_invalid_failure_is_classified(self) -> None:
        # An oversized input to a reviewed fixture is an input error, not a
        # deliberate execution failure.
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                input_payload={"text": "x" * (MAX_FIXTURE_INPUT_BYTES + 1)},
            )
        )
        assert result.executed is True
        assert result.allowed is False
        assert result.failed is True
        assert "fixture_input_invalid" in result.denial_reasons
        assert result.p0_evidence["classification"] == "failure_mode_evidence"


# ===========================================================================
# D. Immutability / tamper resistance
# ===========================================================================


class TestImmutabilityAndTamperResistance:
    def test_request_input_deep_copied(self) -> None:
        payload = {"text": "hello"}
        request = _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload=payload)
        payload["text"] = "mutated"
        result = run_dev_plugin(request)
        # The runtime evaluated the ORIGINAL payload, not the mutated one.
        assert dict(result.output_payload) == {"text": "HELLO"}

    def test_request_descriptor_deep_copied(self) -> None:
        descriptor = {"pluginId": "fixture.echo", "operation": "echo_uppercase"}
        request = _req(plugin_id="fixture.echo", operation="echo_uppercase", descriptor=descriptor)
        descriptor["module"] = "smuggled.module"
        result = run_dev_plugin(request)
        # The smuggled field was added AFTER construction → not seen → allowed.
        assert result.allowed is True

    def test_result_output_is_defensively_copied(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"})
        )
        # output_payload is a frozen MappingProxyType; mutation raises.
        with pytest.raises(TypeError):
            result.output_payload["text"] = "tampered"  # type: ignore[index]

    def test_result_audit_is_defensively_copied(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"})
        )
        with pytest.raises(TypeError):
            result.redacted_audit["decision"] = "allowed-tampered"  # type: ignore[index]

    def test_mutating_result_projection_does_not_leak_secret(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"})
        )
        projection = result.to_safe_dict()
        # Mutating the projected dict cannot smuggle a secret past is_runtime_result_safe,
        # but the original result stays safe regardless.
        assert is_runtime_result_safe(result) is True
        projection["runtimeFlags"] = {**projection["runtimeFlags"], "production_access": True}
        # The tampered projection is no longer safe; the result object still is.
        assert is_runtime_result_safe(projection) is False
        assert is_runtime_result_safe(result) is True

    def test_mutating_metadata_does_not_authorize(self) -> None:
        metadata = {"note": "benign"}
        request = _req(
            plugin_id="fixture.echo",
            operation="echo_uppercase",
            input_payload={"text": "hi"},
            metadata=metadata,
        )
        metadata["implementation_authorization"] = "GO"
        result = run_dev_plugin(request)
        assert result.allowed is True  # benign metadata → still allowed
        assert result.p0_evidence["implementationGate"] == "NO-GO"

    def test_repeated_execution_shares_no_mutable_state(self) -> None:
        results = [
            run_dev_plugin(
                _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": str(i)})
            )
            for i in range(5)
        ]
        # Each result is independent; mutating one does not affect another.
        assert all(dict(r.output_payload) == {"text": str(i).upper()} for i, r in enumerate(results))
        assert all(is_runtime_result_safe(r) for r in results)

    def test_runtime_flags_cannot_be_constructed_unsafe(self) -> None:
        # A result constructed with tampered runtime_flags raises at construction.
        with pytest.raises(AssertionError):
            PluginRuntimeResult(
                allowed=True,
                executed=True,
                failed=False,
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                runtime_flags={**RUNTIME_FLAGS_FROZEN, "production_access": True},
            )


# ===========================================================================
# E. Source boundary scan (runtime + fixture modules have no execution surface)
# ===========================================================================


class TestSourceBoundary:
    # Call-pattern tokens (never bare words) so a denial-list docstring that
    # legitimately mentions ``subprocess`` / ``read_text`` (as dev_web_sandbox_guards
    # does) does not false-positive. Only an actual call surface matches.
    _FORBIDDEN_TOKENS: tuple[str, ...] = (
        "importlib.import_module",
        "__import__(",
        "eval(",
        "exec(",
        "shell=True",
        "import requests",
        "import httpx",
        "import aiohttp",
        "socket.socket",
        "socket.connect",
        "urllib.request",
        "os.system",
        "os.kill",
        "signal.signal",
        "import subprocess",
        "subprocess.",
        "open(",
        ".read_text(",
        ".write_text(",
        ".stat(",
        ".resolve(",
        "expanduser(",
    )

    def _src(self, module_name: str) -> str:
        import importlib

        module = importlib.import_module(module_name)
        return Path(module.__file__).read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "module_name",
        (
            "hermes_cli.dev_web_plugin_runtime",
            "hermes_cli.dev_web_fixture_plugins",
        ),
    )
    def test_module_source_has_no_forbidden_surface(self, module_name: str) -> None:
        src = self._src(module_name)
        for token in self._FORBIDDEN_TOKENS:
            assert token not in src, f"{module_name}: forbidden token {token!r}"

    @pytest.mark.parametrize(
        "module_name",
        (
            "hermes_cli.dev_web_plugin_runtime",
            "hermes_cli.dev_web_fixture_plugins",
        ),
    )
    def test_module_does_not_import_dev_web_api(self, module_name: str) -> None:
        src = self._src(module_name)
        assert "dev_web_api" not in src
        assert "create_dev_web_api_app" not in src

    def test_fixture_module_only_static_imports(self) -> None:
        # The fixture module imports only the sandbox redactor (a named Hermes
        # module). No dynamic loader, no network lib, no path/open.
        src = self._src("hermes_cli.dev_web_fixture_plugins")
        assert "from hermes_cli.dev_web_sandbox_guards import" in src
        assert "import importlib" not in src
        assert "importlib.import_module" not in src
        assert "subprocess." not in src


# ===========================================================================
# F. dev_web_api isolation + route governance
# ===========================================================================


class TestDevWebApiIsolation:
    def test_runtime_not_imported_by_dev_web_api(self) -> None:
        import importlib

        src = Path(importlib.import_module("hermes_cli.dev_web_api").__file__).read_text(encoding="utf-8")
        assert "dev_web_plugin_runtime" not in src
        assert "dev_web_fixture_plugins" not in src
        assert "run_dev_plugin" not in src

    @pytest.mark.parametrize(
        "path",
        (
            "/api/dev/v1/plugins/runtime",
            "/api/dev/v1/plugin-runtime",
            "/api/dev/v1/runtime/plugin",
            "/api/dev/v1/plugins/execute",
            "/api/dev/v1/fixtures/echo",
        ),
    )
    def test_runtime_probe_yields_no_route(self, client: TestClient, path: str) -> None:
        response = client.get(path)
        assert response.status_code == 404

    def test_route_governance_unchanged(self, app) -> None:
        counts = assert_route_governance_unchanged(app)
        assert counts == {
            "openApiPaths": 34,
            "runtimeRoutes": 34,
            "toolGetRoutes": 5,
            "toolWriteRoutes": 0,
            "toolDryRunRoutes": 1,
            "toolExecutionRoutes": 1,
        }

    def test_no_new_route_flags_zero(self) -> None:
        from hermes_cli.dev_web_safety_baseline import route_governance_new_route_flags

        flags = route_governance_new_route_flags()
        assert flags == {
            "newHttpRoute": 0,
            "newToolWriteRoute": 0,
            "newProviderRoute": 0,
            "newPluginRoute": 0,
            "newRuntimeRoute": 0,
        }

    def test_route_governance_baseline_string_unchanged(self) -> None:
        assert ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"


# ===========================================================================
# G. Production safety (no ~/.hermes, no state.db, no artifacts, no process)
# ===========================================================================


class TestProductionSafety:
    def test_production_home_constant_is_only_a_string(self) -> None:
        # The production home is referenced only as a denial target; it is never
        # resolved on disk at module load. The runtime/fixture modules never name
        # the absolute production path at all.
        import importlib

        for module_name in ("hermes_cli.dev_web_plugin_runtime", "hermes_cli.dev_web_fixture_plugins"):
            src = Path(importlib.import_module(module_name).__file__).read_text(encoding="utf-8")
            assert "PRODUCTION_HERMES_HOME" not in src
            assert "/Users/huangruibang/.hermes" not in src
            assert ".resolve()" not in src

    def test_no_filesystem_access_tokens_in_source(self) -> None:
        # The runtime/fixture source contains no real filesystem-access call.
        # (``state.db`` / ``~/.hermes`` may appear as denial-target *strings* in
        # docstrings — like dev_web_safety_baseline — but never as an access.)
        import importlib

        for module_name in ("hermes_cli.dev_web_plugin_runtime", "hermes_cli.dev_web_fixture_plugins"):
            src = Path(importlib.import_module(module_name).__file__).read_text(encoding="utf-8")
            for token in ("open(", ".stat(", ".resolve(", "expanduser(", ".read_text(", ".write_text("):
                assert token not in src, f"{module_name}: forbidden access token {token!r}"

    def test_importing_runtime_does_not_stat_production_home(self, monkeypatch) -> None:
        # Behavioral proof: importing the runtime modules and running every path
        # (including a ~/.hermes request) never escalates to a real stat / lstat
        # of a production path. String-only denial — no metadata access.
        import importlib
        import os

        accesses: list[str] = []

        real_stat = os.stat
        real_lstat = os.lstat

        def _spy(func):
            def wrapper(path, *args, **kwargs):
                text = str(path)
                low = text.lower()
                if ".hermes" in low or "state.db" in low:
                    accesses.append(text)
                return func(path, *args, **kwargs)

            return wrapper

        monkeypatch.setattr(os, "stat", _spy(real_stat))
        monkeypatch.setattr(os, "lstat", _spy(real_lstat))
        # Re-import fresh to exercise module load under the spy.
        importlib.reload(importlib.import_module("hermes_cli.dev_web_fixture_plugins"))
        importlib.reload(importlib.import_module("hermes_cli.dev_web_plugin_runtime"))

        # Run happy / denied / failure paths including a forbidden-path request.
        run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"}))
        run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", requested_filesystem_paths=("~/.hermes",)))
        run_dev_plugin(_req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1}))

        assert accesses == [], f"runtime stat()'d a production path: {accesses}"

    def test_no_runtime_artifacts_created(self, tmp_path: Path) -> None:
        # Running happy / denied / failure paths writes nothing to disk.
        run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"}))
        run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", requested_network_targets=("https://example.com",)))
        run_dev_plugin(_req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1}))
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_runtime_source_has_no_process_or_gateway_surface(self) -> None:
        # The runtime never signals / stops / restarts any process and is not
        # wired into gateway management. (Bare "subprocess" appears in a
        # denial-list docstring; only an actual import / call surface matches.)
        import importlib

        src = Path(importlib.import_module("hermes_cli.dev_web_plugin_runtime").__file__).read_text(encoding="utf-8")
        for token in ("os.kill", "signal.signal", "import psutil", "psutil.", "import subprocess", "subprocess."):
            assert token not in src, f"runtime module references {token!r}"


# ===========================================================================
# H. P0 evidence integration
# ===========================================================================


class TestP0Integration:
    def test_successful_fixture_execution_is_partial_evidence_only(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"})
        )
        assert result.p0_evidence["classification"] == "partial_evidence"
        assert result.p0_evidence["resolved"] is False
        assert result.p0_evidence["resolvedCount"] == 0

    def test_denied_fixture_execution_is_guard_evidence(self) -> None:
        result = run_dev_plugin(_req(plugin_id="unknown.plugin", operation="run"))
        assert result.p0_evidence["classification"] == "guard_evidence"
        assert result.p0_evidence["resolved"] is False

    def test_failed_fixture_execution_is_failure_mode_evidence(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1})
        )
        assert result.p0_evidence["classification"] == "failure_mode_evidence"

    def test_p0_resolved_count_remains_zero_globally(self) -> None:
        # Run many successful fixtures; the global P0 summary stays unresolved.
        for _ in range(10):
            run_dev_plugin(
                _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "x"})
            )
        summary = evaluate_p0_evidence()
        assert summary.resolved_count == 0
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorized is False
        assert summary.real_runtime == "NO-GO"

    def test_frozen_authorization_constants(self) -> None:
        assert IMPLEMENTATION_AUTHORIZATION == "NO-GO"
        assert PHASE_3I_AUTHORIZED is False
        assert REAL_RUNTIME == "NO-GO"
        assert NEW_ROUTE == "NO-GO"
        assert PRODUCTION_ROLLOUT == "NO-GO"

    def test_scenario_pass_does_not_authorize(self) -> None:
        # A successful fixture run + runtime proof scenarios all passing still
        # leaves every authorization flag frozen.
        run_dev_plugin(_req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "x"}))
        summary = run_proof_scenarios(list(get_runtime_proof_scenarios()))
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_fake_human_approval_record_is_invalid(self) -> None:
        # A forged approval (direct construction or metadata-derived) cannot
        # resolve a gate — the trust token is None in the dev skeleton.
        record = create_human_approval("P0-15", "project owner", "approved", trust_token="fake")
        assert is_approval_valid(record) is False
        assert record.is_valid() is False
        forged = HumanApprovalRecord(gate_id="P0-15", reviewer="project owner", decision="approved", signature="forged")
        assert is_approval_valid(forged) is False
        summary = evaluate_p0_evidence(approvals=[record, forged])
        assert summary.resolved_count == 0

    def test_implementation_authorization_cannot_flip(self) -> None:
        # Supplying authorization metadata to the runtime cannot flip the flags.
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                input_payload={"text": "hi"},
                metadata={"implementation_authorization": "GO", "phase_3i_authorized": True},
            )
        )
        assert result.allowed is False  # smuggling denied
        assert result.p0_evidence["implementationGate"] == "NO-GO"
        assert result.p0_evidence["phase3iGate"] is False


# ===========================================================================
# I. Descriptor-to-fixture binding resolution
# ===========================================================================


class TestRuntimeBinding:
    def test_resolve_known_fixture(self) -> None:
        binding = resolve_runtime_binding(
            _req(plugin_id="fixture.echo", operation="echo_uppercase")
        )
        assert binding.resolved is True
        assert binding.fixture is not None
        assert binding.fixture.plugin_id == "fixture.echo"
        ok, reasons = validate_runtime_binding(binding)
        assert ok is True and reasons == ()

    def test_resolve_via_descriptor(self) -> None:
        binding = resolve_runtime_binding(
            _req(
                descriptor={
                    "pluginId": "fixture.inspect",
                    "operation": "summarize_keys",
                    "source": "descriptor_only",
                }
            )
        )
        assert binding.resolved is True
        assert binding.plugin_id == "fixture.inspect"
        assert binding.operation == "summarize_keys"

    def test_resolve_unknown_fixture_unresolved(self) -> None:
        binding = resolve_runtime_binding(_req(plugin_id="remote.registry", operation="fetch"))
        assert binding.resolved is False
        assert binding.fixture is None
        assert "fixture_not_in_allowlist" in binding.reasons

    def test_resolve_descriptor_with_execution_surface_unresolved(self) -> None:
        binding = resolve_runtime_binding(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                descriptor={"pluginId": "fixture.echo", "operation": "echo_uppercase", "module": "x"},
            )
        )
        assert binding.resolved is False
        assert "descriptor_carries_execution_surface" in binding.reasons

    def test_binding_to_safe_dict_has_no_fixture_invoker(self) -> None:
        binding = resolve_runtime_binding(
            _req(plugin_id="fixture.echo", operation="echo_uppercase")
        )
        projection = binding.to_safe_dict()
        # The callable itself is never serialized — only its labels + a flag.
        assert projection["fixture"]["invokerExposed"] is False
        assert "invoker" not in projection["fixture"]  # no key named "invoker"
        blob = _blob(projection["fixture"])
        assert "function" not in blob and "<locals>" not in blob


# ===========================================================================
# J. Runtime proof scenarios (separate fixed dev-only library)
# ===========================================================================


class TestRuntimeProofScenarios:
    def test_runtime_scenarios_count(self) -> None:
        assert len(RUNTIME_PROOF_SCENARIOS) == 5
        assert len(get_runtime_proof_scenarios()) == 5

    def test_runtime_scenarios_separate_from_fixed(self) -> None:
        # The Phase 3H 22-scenario library is unchanged.
        assert len(FIXED_SCENARIOS) == 22
        runtime_ids = {s.scenario_id for s in RUNTIME_PROOF_SCENARIOS}
        fixed_ids = {s.scenario_id for s in FIXED_SCENARIOS}
        assert runtime_ids.isdisjoint(fixed_ids)

    @pytest.mark.parametrize(
        "scenario",
        RUNTIME_PROOF_SCENARIOS,
    )
    def test_each_runtime_scenario_meets_expectations(self, scenario) -> None:
        result = run_proof_scenario(scenario)
        assert result.passed is True, f"{scenario.scenario_id}: {result.denial_reasons}"

    def test_runtime_scenario_aggregate_locked(self) -> None:
        summary = run_proof_scenarios(list(get_runtime_proof_scenarios()))
        assert summary.failed_scenarios == 0
        assert summary.passed_scenarios == 5
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_runtime_scenarios_carry_no_secret(self) -> None:
        summary = run_proof_scenarios(list(get_runtime_proof_scenarios()))
        assert contains_secret(summary.to_safe_dict()) is False

    def test_individual_scenario_constants(self) -> None:
        assert LOCAL_RUNTIME_ECHO_DESCRIPTOR_ALLOWED.expected_decision == "allowed"
        assert LOCAL_RUNTIME_NETWORK_DENIED.expected_decision == "denied"
        assert LOCAL_RUNTIME_SECRET_DENIED.expected_decision == "denied"
        assert LOCAL_RUNTIME_KILL_SWITCH_DENIED.expected_decision == "denied"
        assert LOCAL_RUNTIME_DESCRIPTOR_EXECUTION_DENIED.expected_decision == "denied"
