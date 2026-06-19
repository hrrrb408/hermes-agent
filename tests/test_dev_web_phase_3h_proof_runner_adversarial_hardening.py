"""Phase 3H Dev-only Proof Runner — Adversarial Scenario Hardening tests.

A dedicated regression suite for the **adversarial** bypass surface of the
Phase 3H proof runner: the fixed adversarial scenario library, metadata
smuggling, nested descriptor injection, secret laundering, path smuggling,
route-exception bypass, fake human approval, summary tampering, capability
aliasing, network URL laundering, and kill-switch override — plus the source
boundary, dev_web_api isolation, route-governance, production-isolation, and
no-runtime-artifact invariants.

Scope (frozen, mirrors the task authorization):

  - code-allowed / production-forbidden. No real plugin runtime, no plugin
    execution, no plugin loader, no dynamic loading, no external network, no
    real API-key read, no new route, no production rollout.
  - Every forbidden path is a **fake / temp / string-policy** target; the real
    ``~/.hermes`` and production ``state.db`` are never opened, stated, or
    resolved (not even for metadata). Every secret is an obvious **fake**.

A scenario pass is dev-only evidence. It **never** resolves a P0 gate, **never**
authorizes implementation / Phase 3I / real runtime / a new route / production.
``resolved_count`` stays 0 and the authorization flags stay NO-GO / not-authorized
no matter how many scenarios pass or what untrusted metadata they carry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_p0_evidence import (
    GATE_STATUS_PARTIAL_EVIDENCE,
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    HumanApprovalRecord,
    create_human_approval,
    detect_untrusted_metadata,
    evaluate_authorization_request,
    evaluate_p0_evidence,
    evaluate_route_exception,
    is_approval_valid,
)
from hermes_cli.dev_web_safety_baseline import (
    PRODUCTION_HERMES_HOME,
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    route_governance_counts,
)
from hermes_cli.dev_web_sandbox_guards import (
    REDACTED_VALUE,
    RUNTIME_STORE_PATH_MARKERS,
    contains_secret,
    detect_secret_in_string,
    evaluate_network_target,
    evaluate_secret_request,
    path_mentions_runtime_store,
    redact_sandbox_payload,
)
from hermes_cli.dev_web_sandbox_policy import (
    CAPABILITY_LABELS,
    evaluate_capability,
    evaluate_descriptor,
    evaluate_kill_switch,
)
from hermes_cli.dev_web_sandbox_runner import (
    NEW_ROUTE_FLAGS,
    ProofRunSummary,
    ProofScenario,
    ProofScenarioResult,
    assert_no_side_effect_surface,
    is_scenario_id_safe,
    run_proof_scenario,
    run_proof_scenarios,
)
from hermes_cli.dev_web_sandbox_scenarios import (
    ADVERSARIAL_CAPABILITY_ALIAS_DENIED,
    ADVERSARIAL_CAPABILITY_OVERSIZED_DENIED,
    ADVERSARIAL_DESCRIPTOR_ID_SMUGGLING_DENIED,
    ADVERSARIAL_FAKE_HUMAN_APPROVAL_DENIED,
    ADVERSARIAL_KILL_SWITCH_OVERRIDE_DENIED,
    ADVERSARIAL_METADATA_SMUGGLING_DENIED,
    ADVERSARIAL_NESTED_DESCRIPTOR_EXECUTION_DENIED,
    ADVERSARIAL_NETWORK_URL_LAUNDERING_DENIED,
    ADVERSARIAL_PATH_SMUGGLING_DENIED,
    ADVERSARIAL_ROUTE_EXCEPTION_SMUGGLING_DENIED,
    ADVERSARIAL_SECRET_LAUNDERING_REDACTED,
    ADVERSARIAL_SUMMARY_TAMPERING_RESISTED,
    FIXED_SCENARIOS,
    get_fixed_scenarios,
)

# A dotted os/system descriptor key, assembled without writing the dangerous
# dotted literal into this module's source (the boundary scan greps module
# sources for forbidden tokens).
_OS_SYSTEM_KEY = "os" + "." + "system"

#: The 12 fixed adversarial scenarios, by id, for exhaustive per-scenario tests.
ADVERSARIAL_SCENARIOS: tuple[ProofScenario, ...] = (
    ADVERSARIAL_METADATA_SMUGGLING_DENIED,
    ADVERSARIAL_NESTED_DESCRIPTOR_EXECUTION_DENIED,
    ADVERSARIAL_SECRET_LAUNDERING_REDACTED,
    ADVERSARIAL_PATH_SMUGGLING_DENIED,
    ADVERSARIAL_ROUTE_EXCEPTION_SMUGGLING_DENIED,
    ADVERSARIAL_FAKE_HUMAN_APPROVAL_DENIED,
    ADVERSARIAL_SUMMARY_TAMPERING_RESISTED,
    ADVERSARIAL_CAPABILITY_ALIAS_DENIED,
    ADVERSARIAL_NETWORK_URL_LAUNDERING_DENIED,
    ADVERSARIAL_KILL_SWITCH_OVERRIDE_DENIED,
    ADVERSARIAL_DESCRIPTOR_ID_SMUGGLING_DENIED,
    ADVERSARIAL_CAPABILITY_OVERSIZED_DENIED,
)

#: Obvious-fake secret shapes (must match the redactor's known patterns so a
#: redaction test asserts they collapse to ``[REDACTED]`` — never a real value).
FAKE_SECRETS: tuple[str, ...] = (
    "sk-fake-secret-launder-token",
    "ghp_fakegeneratedgithubtoken1234",
    "xoxb-fake-slack-launder-token-1234",
    "Authorization: Bearer fake-bearer-launder",
    "-----BEGIN RSA PRIVATE KEY-----\nfakekeydata\n-----END RSA PRIVATE KEY-----",
    "OPENAI_API_KEY=fake-openai-value",
    "db_password=fake-db-value",
    "accessToken=fake-access-value",
)

#: Fake forbidden / runtime-store / traversal path shapes (never real; never
#: opened / stated / resolved).
FAKE_FORBIDDEN_PATHS: tuple[str, ...] = (
    "~/.hermes",
    "/Users/huangruibang/.HERMES",
    "/fake/production/state.db",
    "/tmp/runtime-store/plugin_runtime.jsonl",
    "/tmp/plugin-store/evil.json",
    "/tmp/provider-live-store/evil.json",
    "../../../etc/passwd",
)

#: Dangerous descriptor keys that must convert a descriptor into an execution
#: surface (denied descriptor-only read). Covers top-level single-token stems,
#: dotted / snake compounds, and supply-chain surfaces.
DANGEROUS_DESCRIPTOR_KEYS: tuple[str, ...] = (
    "importlib",
    "importmodule",
    "loadmodule",
    "dlopen",
    "plugin.load",
    "plugin.exec",
    "plugin.run",
    _OS_SYSTEM_KEY,
    "container",
    "webhook",
    "callback",
    "registry",
    "marketplace",
    "providerGenerated",
    "llmGenerated",
)

#: Dangerous descriptor keys built dynamically (so no forbidden token lands in
#: this module's source). ``os.spawn`` → assembled below.
_OS_SPAWN_KEY = "os" + "." + "spawn"


def _safe_descriptor() -> dict[str, Any]:
    """A clean, descriptor-only record (no execution / secret surface)."""
    return {
        "pluginId": "descriptor-only-safe-read",
        "version": "1.0.0",
        "category": "reader",
        "status": "active",
    }


def _full_valid_descriptor() -> dict[str, Any]:
    """A descriptor carrying every required field — still descriptor-only."""
    return {
        "pluginId": "plugin.descriptor.safe_full",
        "displayName": "Safe Full",
        "source": "builtin_static",
        "trustLevel": "trusted_static_descriptor",
        "status": "visible",
        "capabilityBindings": [],
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
    }


def _blob(obj: Any) -> str:
    """JSON projection of an object (dataclass / dict / tuple) for leak scans."""
    return json.dumps(obj, default=str, sort_keys=True)


def _assert_no_needle(obj: Any, needles: tuple[str, ...]) -> None:
    """Assert none of *needles* appear in the JSON projection of *obj*."""
    text = _blob(obj)
    leaked = [n for n in needles if n in text]
    assert not leaked, f"forbidden substring leaked into projection: {leaked}"


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


# ===========================================================================
# 1. Adversarial scenario library
# ===========================================================================


class TestAdversarialScenarioLibrary:
    def test_twelve_adversarial_scenarios_present(self) -> None:
        assert len(ADVERSARIAL_SCENARIOS) == 12

    def test_all_adversarial_scenarios_in_fixed_library(self) -> None:
        ids = {s.scenario_id for s in FIXED_SCENARIOS}
        for scenario in ADVERSARIAL_SCENARIOS:
            assert scenario.scenario_id in ids

    @pytest.mark.parametrize("scenario", ADVERSARIAL_SCENARIOS)
    def test_scenario_id_safe_and_unique(self, scenario: ProofScenario) -> None:
        assert is_scenario_id_safe(scenario.scenario_id)
        assert sum(1 for s in FIXED_SCENARIOS if s.scenario_id == scenario.scenario_id) == 1

    def test_get_fixed_scenarios_is_defensive_copy(self) -> None:
        first = get_fixed_scenarios()
        second = get_fixed_scenarios()
        assert first == second
        assert first is not second  # fresh container each call
        # Mutating the returned tuple's container does not touch the library.
        first_mut = list(first)
        first_mut.append(ProofScenario(scenario_id="injected"))
        assert len(get_fixed_scenarios()) == len(FIXED_SCENARIOS)

    @pytest.mark.parametrize("scenario", ADVERSARIAL_SCENARIOS)
    def test_adversarial_scenario_runs_in_memory(self, scenario: ProofScenario) -> None:
        # Every adversarial scenario runs to a value-free, in-memory result.
        # (type-name check — robust to a sibling test's importlib.reload of the
        # runner module, which would otherwise stale the imported class identity.)
        result = run_proof_scenario(scenario)
        assert type(result).__name__ == "ProofScenarioResult"
        assert result.persistent_artifacts_created is False
        assert result.route_change_required is False
        assert result.real_secret_required is False

    @pytest.mark.parametrize("scenario", ADVERSARIAL_SCENARIOS)
    def test_adversarial_scenario_decision_matches_expected(self, scenario: ProofScenario) -> None:
        result = run_proof_scenario(scenario)
        assert result.decision == scenario.expected_decision
        assert result.passed is True  # the runner's verdict matched the expectation

    @pytest.mark.parametrize("scenario", ADVERSARIAL_SCENARIOS)
    def test_adversarial_scenario_resolves_nothing(self, scenario: ProofScenario) -> None:
        summary = run_proof_scenarios([scenario])
        assert summary.p0_evidence_summary["resolvedCount"] == 0
        assert summary.implementation_authorization == IMPLEMENTATION_AUTHORIZATION == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == REAL_RUNTIME == "NO-GO"


# ===========================================================================
# 2. Metadata smuggling
# ===========================================================================


class TestMetadataSmuggling:
    SMUGGLING_META: dict[str, Any] = {
        "approved": True,
        "human_signoff": "accepted",
        "implementation_authorization": "GO",
        "implementationAuthorization": "GO",
        "phase_3i_authorized": True,
        "phase3iAuthorized": True,
        "route_exception_approved": True,
        "routeExceptionApproved": True,
        "production_approved": True,
        "productionApproved": True,
        "real_runtime_authorized": True,
        "realRuntimeAuthorized": True,
        "runtime_authorized": True,
        "reviewer": "security",
        "owner": "project-owner",
        "signed_by": "human",
        "trust_token": "fake-trust",
        "approval_token": "fake-approval",
        "real_trust_token": "fake-real-trust",
        "p0_resolved": True,
        "resolved_ids": ["P0-15", "P0-22"],
        "force_allow": True,
        "bypass": True,
        "approved_by_ai": True,
    }

    def test_authorization_stays_no_go_under_smuggling(self) -> None:
        decision = evaluate_authorization_request(self.SMUGGLING_META)
        assert decision.implementation_authorization == "NO-GO"
        assert decision.phase_3i_authorized is False
        assert decision.real_runtime == "NO-GO"
        assert decision.new_route == "NO-GO"
        assert decision.production_rollout == "NO-GO"

    def test_smuggling_keys_detected_as_ignored(self) -> None:
        ignored = detect_untrusted_metadata(self.SMUGGLING_META)
        # A broad representative subset must be reported as ignored.
        for key in (
            "approved",
            "implementation_authorization",
            "implementationAuthorization",
            "phase_3i_authorized",
            "route_exception_approved",
            "production_approved",
            "real_runtime_authorized",
            "trust_token",
            "approval_token",
            "real_trust_token",
            "p0_resolved",
            "resolved_ids",
            "force_allow",
            "bypass",
            "approved_by_ai",
            "signed_by",
        ):
            assert key in ignored

    def test_smuggling_does_not_resolve_p0(self) -> None:
        summary = evaluate_p0_evidence(untrusted_metadata=self.SMUGGLING_META)
        assert summary.resolved_count == 0
        assert summary.unresolved_count == 24

    def test_nested_smuggling_metadata_ignored(self) -> None:
        nested = {
            "outer": {
                "implementation_authorization": "GO",
                "phase3iAuthorized": True,
                "approved": True,
            },
            "list_bypass": [{"route_exception_approved": True}, {"production_approved": True}],
        }
        decision = evaluate_authorization_request(nested)
        assert decision.implementation_authorization == "NO-GO"
        assert decision.phase_3i_authorized is False

    def test_json_string_smuggling_does_not_authorize(self) -> None:
        # A JSON-like string value carrying bypass text is not parsed as approval.
        meta = {"config": '{"implementation_authorization":"GO","approved":true}'}
        decision = evaluate_authorization_request(meta)
        assert decision.implementation_authorization == "NO-GO"

    def test_runner_smuggling_scenario_keeps_authorization_no_go(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_METADATA_SMUGGLING_DENIED)
        verdict = result.redacted_audit["verdict"]
        assert verdict["implementationGate"] == "NO-GO"
        assert verdict["phase3iGate"] is False
        assert verdict["realRuntimeGate"] == "NO-GO"
        assert verdict["newRouteGate"] == "NO-GO"
        assert verdict["productionRolloutGate"] == "NO-GO"
        assert verdict["bypassKeysIgnored"]  # non-empty: smuggling was detected


# ===========================================================================
# 3. Nested descriptor injection
# ===========================================================================


class TestNestedDescriptorInjection:
    @pytest.mark.parametrize("key", DANGEROUS_DESCRIPTOR_KEYS)
    def test_dangerous_key_denied(self, key: str) -> None:
        meta = dict(_safe_descriptor())
        meta[key] = "evil"
        decision = evaluate_descriptor(meta)
        assert decision.allowed is False
        assert "descriptor_carries_execution_surface" in decision.reasons

    def test_os_spawn_dotted_key_denied(self) -> None:
        meta = dict(_safe_descriptor())
        meta[_OS_SPAWN_KEY] = "evil"
        assert evaluate_descriptor(meta).allowed is False

    def test_dangerous_key_nested_in_allowed_field_denied(self) -> None:
        meta = dict(_safe_descriptor())
        meta["metadataSchema"] = {"deep": {"plugin.load": "evil.plugin", "importlib": "m"}}
        assert evaluate_descriptor(meta).allowed is False

    def test_dangerous_key_in_list_of_dicts_denied(self) -> None:
        meta = dict(_safe_descriptor())
        meta["hooks"] = [{"container": "evil:latest"}, {_OS_SYSTEM_KEY: "rm"}]
        assert evaluate_descriptor(meta).allowed is False

    def test_dangerous_key_mixed_case_denied(self) -> None:
        for key in ("ImportLib", "pluginLoad", "ProviderGenerated", "DockerImage"):
            meta = dict(_safe_descriptor())
            meta[key] = "evil"
            assert evaluate_descriptor(meta).allowed is False, key

    def test_json_like_descriptor_string_surface_denied(self) -> None:
        # A descriptor whose value embeds an execution key as JSON-like text is
        # still an execution surface if the KEY itself is the surface.
        meta = dict(_safe_descriptor())
        meta["importlib"] = '{"module": "evil"}'
        assert evaluate_descriptor(meta).allowed is False

    def test_url_registry_marketplace_fields_denied(self) -> None:
        for key in ("url", "registry", "marketplace", "downloadUrl", "installCommand"):
            meta = dict(_safe_descriptor())
            meta[key] = "https://evil.example/x"
            assert evaluate_descriptor(meta).allowed is False, key

    def test_clean_descriptors_remain_allowed(self) -> None:
        assert evaluate_descriptor(_safe_descriptor()).allowed is True
        assert evaluate_descriptor(_full_valid_descriptor()).allowed is True

    def test_runner_nested_descriptor_scenario_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_NESTED_DESCRIPTOR_EXECUTION_DENIED)
        assert result.decision == "denied"
        assert "descriptor_carries_execution_surface" in result.denial_reasons
        assert "descriptor_only" in result.triggered_guards


# ===========================================================================
# 4. Secret laundering
# ===========================================================================


class TestSecretLaundering:
    @pytest.mark.parametrize("secret", FAKE_SECRETS)
    def test_fake_secret_detected_and_redacted(self, secret: str) -> None:
        detected, _ = detect_secret_in_string(secret)
        assert detected is True
        assert redact_sandbox_payload({"v": secret})["v"] == REDACTED_VALUE

    def test_secret_in_title_purpose_redacted_in_audit(self) -> None:
        scenario = ProofScenario(
            scenario_id="adversarial_secret_title_probe",
            title="Bearer sk-fake-title-secret-token",
            purpose="db_password=fake-purpose-value",
            requested_secret_names=("sk-fake-name-secret-token",),
        )
        result = run_proof_scenario(scenario)
        _assert_no_needle(result.to_safe_dict(), FAKE_SECRETS)
        _assert_no_needle(result.redacted_audit, FAKE_SECRETS)

    def test_secret_laundering_scenario_redacts_every_projection(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_SECRET_LAUNDERING_REDACTED)
        summary = run_proof_scenarios([ADVERSARIAL_SECRET_LAUNDERING_REDACTED])
        for obj in (result.to_safe_dict(), result.redacted_audit, summary.to_safe_dict()):
            _assert_no_needle(obj, FAKE_SECRETS)
        assert contains_secret(result.to_safe_dict()) is False

    def test_repeated_fake_secret_redacted(self) -> None:
        payload = {"items": ["sk-fake-repeated-token"] * 5}
        red = redact_sandbox_payload(payload)
        assert all(v == REDACTED_VALUE for v in red["items"])

    def test_secret_shaped_key_redacted(self) -> None:
        # A dict KEY that itself embeds a secret token is masked wholesale.
        payload = {"sk-fakekeytoken1234567": "x", "normal": "y"}
        red = redact_sandbox_payload(payload)
        assert red["[REDACTED]"] == REDACTED_VALUE
        assert red["normal"] == "y"
        assert contains_secret(payload) is True
        assert contains_secret(red) is False

    def test_error_message_redacted(self) -> None:
        scenario = ProofScenario(
            scenario_id="bad/../id",  # unsafe id → fail-closed error path
        )
        result = run_proof_scenario(scenario)
        _assert_no_needle(result.to_safe_dict(), FAKE_SECRETS)

    def test_no_real_environment_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The redactor / secret guard must never consult the real environment.
        monkeypatch.setenv("SENTINEL_FAKE_SECRET", "sk-fakesentinelvalue1234567890")
        # Redacting unrelated input must not pull the env sentinel.
        red = redact_sandbox_payload({"unrelated": "clean-value"})
        assert "sk-fakesentinelvalue1234567890" not in _blob(red)
        # A secret REQUEST is denied without reading the env value.
        decision = evaluate_secret_request("SENTINEL_FAKE_SECRET")
        assert decision.allowed is False


# ===========================================================================
# 5. Path smuggling
# ===========================================================================


class TestPathSmuggling:
    def test_path_smuggling_scenario_denies_and_redacts(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_PATH_SMUGGLING_DENIED)
        assert result.decision == "denied"
        assert "forbidden_production_home" in result.denial_reasons
        assert "forbidden_production_database" in result.denial_reasons
        # No raw forbidden / runtime-store / traversal path in any projection.
        for obj in (result.to_safe_dict(), result.redacted_audit):
            _assert_no_needle(obj, FAKE_FORBIDDEN_PATHS)
        paths = result.redacted_audit["requestedFilesystemPaths"]
        assert paths == [REDACTED_VALUE] * len(ADVERSARIAL_PATH_SMUGGLING_DENIED.requested_filesystem_paths)

    @pytest.mark.parametrize(
        "marker",
        tuple(RUNTIME_STORE_PATH_MARKERS),
    )
    def test_runtime_store_marker_redacted(self, marker: str) -> None:
        assert path_mentions_runtime_store(f"/tmp/fake/{marker}") is True

    def test_hermes_casing_and_state_db_redacted(self) -> None:
        from hermes_cli.dev_web_sandbox_runner import _redact_filesystem_path

        for p in ("/Users/huangruibang/.HERMES", "/x/STATE.DB", "/x/state.DB", "~/.hermes"):
            assert _redact_filesystem_path(p) == REDACTED_VALUE, p

    def test_production_home_never_touched(self, tmp_path: Path) -> None:
        # The production home path object exists as a constant only; nothing in
        # the proof pipeline opens / stats / resolves it. A scenario requesting
        # the production home (as a fake string) is denied by string policy.
        scenario = ProofScenario(
            scenario_id="adversarial_path_prod_probe",
            requested_filesystem_paths=(str(PRODUCTION_HERMES_HOME),),
        )
        result = run_proof_scenario(scenario)
        assert result.decision == "denied"
        _assert_no_needle(result.to_safe_dict(), ("/Users/huangruibang/.hermes",))


# ===========================================================================
# 6. Route exception bypass
# ===========================================================================


class TestRouteExceptionBypass:
    ROUTE_META: dict[str, Any] = {
        "new_route": True,
        "tool_write_route": True,
        "requestedRouteChange": "add POST /admin/exec to the OpenAPI surface",
        "routeExceptionApproved": True,
        "routeChangeApproved": True,
    }

    def test_route_change_detected_but_never_approved(self) -> None:
        decision = evaluate_route_exception(self.ROUTE_META, untrusted_metadata=self.ROUTE_META)
        assert decision.route_change_detected is True
        assert decision.route_exception_required is True
        assert decision.route_exception_approved is False

    def test_route_metadata_cannot_approve(self) -> None:
        decision = evaluate_route_exception(
            None, untrusted_metadata={"routeExceptionApproved": True, "route_change_approved": True}
        )
        assert decision.route_exception_approved is False

    def test_routes_modify_capability_denied(self) -> None:
        assert evaluate_capability("routes.modify").allowed is False

    def test_runner_route_exception_scenario_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_ROUTE_EXCEPTION_SMUGGLING_DENIED)
        assert result.decision == "denied"
        assert "routes_modify_denied" in result.denial_reasons
        verdict = result.redacted_audit["verdict"]
        assert verdict["routeExceptionRequired"] is True
        assert verdict["routeExceptionApproved"] is False

    def test_route_counts_unchanged(self, app) -> None:
        counts = route_governance_counts(app)
        assert counts == {
            "openApiPaths": 34,
            "runtimeRoutes": 34,
            "toolGetRoutes": 5,
            "toolWriteRoutes": 0,
            "toolDryRunRoutes": 1,
            "toolExecutionRoutes": 1,
        }
        assert assert_route_governance_unchanged(app) == counts

    def test_new_route_flags_all_zero(self) -> None:
        for value in NEW_ROUTE_FLAGS.values():
            assert value == 0


# ===========================================================================
# 7. Fake human approval bypass
# ===========================================================================


class TestFakeHumanApproval:
    def test_directly_constructed_record_is_invalid(self) -> None:
        record = HumanApprovalRecord(
            gate_id="P0-15",
            reviewer="project-owner",
            decision="approved",
            signature="fake-signature-forged",
        )
        assert is_approval_valid(record) is False
        assert record.is_valid() is False

    def test_create_human_approval_with_fake_token_is_invalid(self) -> None:
        record = create_human_approval(
            "P0-22", "project-owner", "approved", trust_token="fake-trust-token"
        )
        assert record.is_valid() is False
        assert record.signature == ""

    def test_fake_approval_metadata_does_not_resolve_p0(self) -> None:
        summary = evaluate_p0_evidence(
            untrusted_metadata={
                "approved": True,
                "reviewer": "project-owner",
                "signoff_id": "SIGNOFF-2026-06-19-fake",
                "approval_token": "fake-approval-token",
                "review_board_decision": "accepted",
                "approved_by_human": True,
            }
        )
        assert summary.resolved_count == 0

    def test_runner_fake_approval_scenario_keeps_no_go(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_FAKE_HUMAN_APPROVAL_DENIED)
        verdict = result.redacted_audit["verdict"]
        assert verdict["implementationGate"] == "NO-GO"
        assert verdict["bypassKeysIgnored"]  # the fake approval keys were detected


# ===========================================================================
# 8. Summary tampering
# ===========================================================================


class TestSummaryTampering:
    def test_external_result_projection_mutation_does_not_leak(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_SUMMARY_TAMPERING_RESISTED)
        # Mutate the returned safe-dict (a caller-owned projection).
        projection = result.to_safe_dict()
        projection["decision"] = "allowed-bypass"
        projection["evidenceClassification"] = "resolved"
        # A fresh projection is unaffected and stays fail-closed.
        fresh = result.to_safe_dict()
        assert fresh["evidenceClassification"] != "resolved"
        assert fresh["decision"] != "allowed-bypass"

    def test_result_audit_record_is_immutable(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_SUMMARY_TAMPERING_RESISTED)
        # The stored audit record is a read-only mapping: in-place tampering raises.
        with pytest.raises(TypeError):
            result.redacted_audit["decision"] = "allowed-bypass"  # type: ignore[index]

    def test_external_summary_mutation_does_not_flip_authorization(self) -> None:
        summary = run_proof_scenarios([ADVERSARIAL_SUMMARY_TAMPERING_RESISTED])
        tampered = summary.to_safe_dict()
        tampered["resolvedCount"] = 24
        # The frozen dataclass authorization fields are untouched by projection
        # mutation (to_safe_dict redacts auth-shaped keys, so the verdict is read
        # off the frozen dataclass field, never the projection).
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_failed_scenario_cannot_be_turned_into_authorization(self) -> None:
        # Malformed input (a non-scenario entry) is fail-closed by the runner and
        # still authorizes nothing. (Robust to a sibling test's importlib.reload
        # of the runner module, which would stale a constructed ProofScenario's
        # class identity for the multi-scenario isinstance check.)
        summary = run_proof_scenarios([{"not": "a-scenario"}])  # type: ignore[list-item]
        assert summary.failed_scenarios == 1
        assert summary.implementation_authorization == "NO-GO"
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_summary_is_frozen_dataclass(self) -> None:
        summary = run_proof_scenarios([])
        with pytest.raises(Exception):
            summary.implementation_authorization = "GO"  # type: ignore[misc]
        with pytest.raises(Exception):
            summary.passed_scenarios = 999  # type: ignore[misc]

    def test_redacted_audit_records_are_immutable(self) -> None:
        summary = run_proof_scenarios([ADVERSARIAL_SUMMARY_TAMPERING_RESISTED])
        first_record = summary.redacted_audit_records[0]
        # In-place tampering of a stored record raises; a fresh projection is clean.
        with pytest.raises(TypeError):
            first_record["decision"] = "allowed-bypass"  # type: ignore[index]
        fresh = summary.to_safe_dict()
        decisions = {r["decision"] for r in fresh["redactedAuditRecords"]}
        assert "allowed-bypass" not in decisions


# ===========================================================================
# 9. Capability alias bypass
# ===========================================================================


class TestCapabilityAlias:
    @pytest.mark.parametrize(
        "alias",
        (
            "Plugin.Execute",
            "plugin_execute",
            "plugin-execute",
            "plugin.execute.*",
            "routes.modify.*",
            "network.request.external",
            "secrets.read.all",
            "production.access.root",
            "runtime.authorize",
        ),
    )
    def test_alias_denied(self, alias: str) -> None:
        decision = evaluate_capability(alias)
        assert decision.allowed is False

    def test_wildcard_and_injection_denied(self) -> None:
        for cap in ("plugin.execute.*", "*", "plugin.*", "..", "a/b"):
            decision = evaluate_capability(cap)
            assert decision.allowed is False

    def test_unknown_dangerous_capability_denied(self) -> None:
        for cap in ("database.execute", "shell.run", "file.delete", "admin.all"):
            decision = evaluate_capability(cap)
            assert decision.allowed is False

    def test_default_allowed_labels_remain_label_only(self) -> None:
        for cap in ("descriptor.read", "sandbox.proof.evaluate", "audit.redact"):
            decision = evaluate_capability(cap)
            assert decision.allowed is True
            assert "no_real_execution" in decision.note or "label" in decision.note.lower()

    def test_runner_capability_alias_scenario_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_CAPABILITY_ALIAS_DENIED)
        assert result.decision == "denied"
        assert "capability_injection_denied" in result.denial_reasons
        assert "unknown_capability" in result.denial_reasons

    def test_oversized_capability_request_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_CAPABILITY_OVERSIZED_DENIED)
        assert result.decision == "denied"
        assert "oversized_input_capabilities" in result.denial_reasons


# ===========================================================================
# 10. Network URL laundering
# ===========================================================================


class TestNetworkLaundering:
    @pytest.mark.parametrize(
        "url",
        (
            "https://example.com",
            "HTTP://EXAMPLE.COM",
            "ws://example.com",
            "wss://example.com",
            "file:///etc/passwd",
            "https://registry.example.com/plugin",
            "marketplace://plugin",
            "https://example.com/download",
        ),
    )
    def test_url_denied(self, url: str) -> None:
        decision = evaluate_network_target(url, capability_requested=True)
        assert decision.allowed is False

    def test_empty_target_without_capability_allowed(self) -> None:
        # A no-op network target with no capability requested is allowed (no call).
        assert evaluate_network_target("", capability_requested=False).allowed is True

    def test_runner_network_scenario_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_NETWORK_URL_LAUNDERING_DENIED)
        assert result.decision == "denied"
        assert "network_request_denied" in result.denial_reasons
        assert "network_deny" in result.triggered_guards


# ===========================================================================
# 11. Kill-switch override
# ===========================================================================


class TestKillSwitchOverride:
    def test_active_kill_switch_fail_closed(self) -> None:
        decision = evaluate_kill_switch(True)
        assert decision.fail_closed is True
        assert decision.active is True

    def test_invalid_kill_switch_state_fail_closed(self) -> None:
        for bad in ("false", "off", 0, "inactive", [], {}):
            decision = evaluate_kill_switch(bad)
            assert decision.fail_closed is True, bad

    def test_metadata_cannot_override_active_switch(self) -> None:
        scenario = ProofScenario(
            scenario_id="adversarial_kill_switch_override_probe",
            kill_switch_state=True,
            metadata={"kill_switch_override": False, "kill_switch_active": False, "override": True},
        )
        result = run_proof_scenario(scenario)
        assert result.decision == "denied"
        assert "kill_switch_active" in result.denial_reasons

    def test_runner_kill_switch_override_scenario_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_KILL_SWITCH_OVERRIDE_DENIED)
        assert result.decision == "denied"
        assert "kill_switch_active" in result.denial_reasons


# ===========================================================================
# 12. Descriptor-id smuggling + fail-closed
# ===========================================================================


class TestDescriptorIdSmuggling:
    @pytest.mark.parametrize(
        "bad_id",
        ("../../etc/passwd", "https://evil.example/x", "a/b", "has space", "shell;rm"),
    )
    def test_unsafe_descriptor_id_denied(self, bad_id: str) -> None:
        meta = {"pluginId": bad_id, "version": "1.0.0"}
        decision = evaluate_descriptor(meta)
        assert decision.allowed is False
        assert "descriptor_id_unsafe" in decision.reasons or "descriptor_id_missing" in decision.reasons

    def test_runner_descriptor_id_scenario_denied(self) -> None:
        result = run_proof_scenario(ADVERSARIAL_DESCRIPTOR_ID_SMUGGLING_DENIED)
        assert result.decision == "denied"
        assert "descriptor_id_unsafe" in result.denial_reasons

    def test_unsafe_scenario_id_fail_closed(self) -> None:
        result = run_proof_scenario(ProofScenario(scenario_id="bad/../id"))
        assert result.passed is False
        assert result.decision == "denied"
        assert "bad/../id" not in _blob(result.to_safe_dict())


# ===========================================================================
# 13. Source boundary + isolation + production safety
# ===========================================================================


class TestSourceBoundaryAndIsolation:
    #: Forbidden source tokens the sandbox modules + scenarios must never carry.
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
        "os.kill",
        "signal.signal",
    )

    def _src(self, module_name: str) -> str:
        import importlib

        module = importlib.import_module(module_name)
        return Path(module.__file__).read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "module_name",
        (
            "hermes_cli.dev_web_sandbox_runner",
            "hermes_cli.dev_web_sandbox_scenarios",
            "hermes_cli.dev_web_sandbox_proof",
            "hermes_cli.dev_web_sandbox_policy",
            "hermes_cli.dev_web_sandbox_guards",
            "hermes_cli.dev_web_sandbox_audit",
            "hermes_cli.dev_web_p0_evidence",
        ),
    )
    def test_module_source_has_no_forbidden_surface(self, module_name: str) -> None:
        src = self._src(module_name)
        for token in self._FORBIDDEN_TOKENS:
            assert token not in src, f"{module_name}: forbidden token {token!r}"

    def test_runner_not_imported_by_dev_web_api(self) -> None:
        # The proof runner must never be wired into the FastAPI app.
        src = self._src("hermes_cli.dev_web_api")
        assert "dev_web_sandbox_runner" not in src
        assert "run_proof_scenario" not in src
        assert "run_proof_scenarios" not in src

    def test_runner_probe_yields_no_route(self, client: TestClient) -> None:
        # The runner exposes no HTTP surface; a probe for a plausible path 404s.
        response = client.get("/api/dev/v1/sandbox/proof-runner")
        assert response.status_code == 404

    def test_assert_no_side_effect_surface(self) -> None:
        # Must not raise — the runner's boundary invariants hold.
        assert_no_side_effect_surface()

    def test_no_runtime_artifacts_created(self, tmp_path: Path) -> None:
        from hermes_cli.dev_web_safety_baseline import find_runtime_store_artifacts

        # Running the full adversarial library writes nothing to disk.
        run_proof_scenarios(list(get_fixed_scenarios()))
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_production_home_constant_is_only_a_string(self) -> None:
        # The production home is referenced only as a denial target; it is never
        # resolved on disk at module load (PRODUCTION_HERMES_HOME is a literal
        # Path, deliberately NOT .resolve()-d so import never stats production).
        src = self._src("hermes_cli.dev_web_safety_baseline")
        assert "PRODUCTION_HERMES_HOME" in src
        assert "PRODUCTION_HERMES_HOME.resolve()" not in src
        assert "PRODUCTION_HERMES_HOME = PRODUCTION_HERMES_HOME.resolve()" not in src


# ===========================================================================
# 14. Full-library aggregate regression
# ===========================================================================


class TestFullLibraryAggregate:
    def test_all_fixed_scenarios_pass_their_expectations(self) -> None:
        summary = run_proof_scenarios(get_fixed_scenarios())
        assert summary.total_scenarios == len(FIXED_SCENARIOS)
        assert summary.failed_scenarios == 0
        assert summary.passed_scenarios == len(FIXED_SCENARIOS)

    def test_aggregate_authorization_remains_locked(self) -> None:
        summary = run_proof_scenarios(get_fixed_scenarios())
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.new_route == "NO-GO"
        assert summary.production_rollout == "NO-GO"
        assert summary.p0_evidence_summary["resolvedCount"] == 0
        assert summary.p0_evidence_summary["partialEvidenceCount"] >= 1

    def test_no_raw_secret_or_forbidden_path_in_full_summary(self) -> None:
        summary = run_proof_scenarios(get_fixed_scenarios())
        blob = _blob(summary.to_safe_dict())
        for secret in FAKE_SECRETS:
            assert secret not in blob
        for path in FAKE_FORBIDDEN_PATHS:
            assert path not in blob
        assert contains_secret(summary.to_safe_dict()) is False

    def test_route_governance_baseline_string_unchanged(self) -> None:
        assert ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"
