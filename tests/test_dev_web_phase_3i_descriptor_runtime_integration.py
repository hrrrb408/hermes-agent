"""Phase 3I Runtime Descriptor Registry Integration tests.

A dedicated regression suite for the **Phase 3I descriptor-registry → runtime
integration** (:mod:`hermes_cli.dev_web_plugin_runtime_binding`): the bridge
between the Phase 3D Static Plugin Descriptor Registry and the Phase 3I
dev-only local plugin runtime.

Scope (frozen, mirrors the task authorization):

  - **code allowed / production forbidden.** The binding layer executes ONLY
    reviewed fixture operations bound through the frozen fixture allowlist, and
    only for descriptors sourced from the static descriptor registry. No
    arbitrary plugin loading, no local plugin directory loading, no remote
    registry, no marketplace, no external plugin fetch, no provider-generated /
    LLM-generated plugin install, no real API-key read, no external network, no
    new route, no production rollout.
  - Every forbidden path is a **fake / temp / string-policy** target; the real
    ``~/.hermes`` and production ``state.db`` are never opened, stated, or
    resolved (not even for metadata). Every secret is an obvious **fake**.

A successful descriptor-backed fixture execution (single or batch) is
**dev-only partial evidence**. It is **never** Implementation Authorization GO,
**never** Phase 3I production authorization, **never** real-runtime
authorization, **never** a P0 resolution. ``resolved_count`` stays 0 and the
authorization flags stay NO-GO / not-authorized no matter what runs or what
untrusted metadata a descriptor or request carries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_fixture_plugins import (
    FIXTURE_ALLOWLIST,
    FIXTURE_OPERATION_NAMES,
    FIXTURE_PLUGIN_IDS,
)
from hermes_cli.dev_web_p0_evidence import (
    GATES,
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    evaluate_p0_evidence,
)
from hermes_cli.dev_web_plugin_descriptor_registry import (
    get_plugin_descriptor_status_block,
    validate_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_runtime import (
    RUNTIME_FLAGS_FROZEN,
    PluginRuntimeBatchResult,
    PluginRuntimeResult,
)
from hermes_cli.dev_web_plugin_runtime_binding import (
    DESCRIPTOR_BINDING_REASONS,
    DESCRIPTOR_BINDING_SOURCE,
    REVIEWED_FIXTURE_DESCRIPTORS,
    RuntimeDescriptorBinding,
    assert_no_side_effect_surface,
    get_reviewed_fixture_descriptors,
    lookup_reviewed_fixture_descriptor,
    resolve_runtime_descriptor_binding,
    run_dev_plugin_batch_from_descriptors,
    run_dev_plugin_from_descriptor,
    run_dev_plugin_from_registry_descriptor,
    validate_runtime_descriptor_for_fixture_runtime,
)
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    find_runtime_store_artifacts,
)
from hermes_cli.dev_web_sandbox_guards import REDACTED_VALUE, contains_secret
from hermes_cli.dev_web_sandbox_runner import run_proof_scenarios
from hermes_cli.dev_web_sandbox_scenarios import (
    DESCRIPTOR_REGISTRY_PROOF_SCENARIOS,
    FIXED_SCENARIOS,
    RUNTIME_EXPANSION_PROOF_SCENARIOS,
    RUNTIME_PROOF_SCENARIOS,
    get_descriptor_registry_proof_scenarios,
)

#: Obvious fake secrets used to prove redaction. None is real.
FAKE_SECRETS: tuple[str, ...] = (
    "sk-FAKE-SECRET-DO-NOT-LEAK-12345678",
    "Authorization: Bearer fake-bearer-descriptor",
    "ghp_fakegeneratedgithubtoken1234",
)

#: Fake production-path-like values used to prove redaction. None is real.
FAKE_PATHS: tuple[str, ...] = (
    "/Users/someone/.hermes/state.db",
    "~/.hermes",
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


def _base_descriptor(**overrides: Any) -> dict[str, Any]:
    """A clean reviewed-fixture descriptor (echo) with optional overrides."""
    desc: dict[str, Any] = {
        "descriptorId": "descriptor.fixture.echo_uppercase",
        "pluginId": "fixture.echo",
        "operation": "echo_uppercase",
        "source": "local_static_descriptor",
        "version": "phase-3i-fixture-descriptor-v1",
        "requestedCapabilities": ("descriptor.read",),
    }
    desc.update(overrides)
    return desc


def _descriptor_for(plugin_id: str, operation: str, descriptor_id: str = "") -> dict[str, Any]:
    """Return the reviewed descriptor for a known ``(plugin_id, operation)`` pair."""
    for entry in REVIEWED_FIXTURE_DESCRIPTORS:
        if entry["pluginId"] == plugin_id and entry["operation"] == operation:
            base = dict(entry)
            if descriptor_id:
                base["descriptorId"] = descriptor_id
            return base
    raise AssertionError(f"no reviewed descriptor for {plugin_id}/{operation}")


# ===========================================================================
# A. Registry discovery / descriptor-only preservation
# ===========================================================================


class TestRegistryDiscovery:
    def test_phase_3d_registry_is_descriptor_only_and_valid(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid is True
        # The registry never executes a plugin by itself.
        status = get_plugin_descriptor_status_block()
        assert status["pluginRuntimeImplemented"] is False
        assert status["pluginLoaderImplemented"] is False
        assert status["dynamicLoadingAllowed"] is False
        assert status["pluginExecutionAllowed"] is False
        assert status["newRouteIntroduced"] is False

    def test_binding_module_preserves_descriptor_only_invariants(self) -> None:
        assert_no_side_effect_surface()
        # The reviewed fixture descriptors are static records; none carries an
        # executable surface, and every one names an exact allowlist member.
        for entry in REVIEWED_FIXTURE_DESCRIPTORS:
            assert (entry["pluginId"], entry["operation"]) in FIXTURE_ALLOWLIST
            assert "module" not in entry
            assert "command" not in entry
            assert "entrypoint" not in entry

    def test_registry_does_not_import_runtime_modules(self) -> None:
        import importlib

        src = Path(
            importlib.import_module("hermes_cli.dev_web_plugin_descriptor_registry").__file__
        ).read_text(encoding="utf-8")
        # The descriptor registry must not pull in the runtime or the binding.
        assert "dev_web_plugin_runtime_binding" not in src
        assert "run_dev_plugin" not in src
        assert "resolve_runtime_binding" not in src

    def test_binding_does_not_touch_production_or_state_db(self) -> None:
        # The binding module source never opens / stats / resolves any path.
        import importlib

        src = Path(
            importlib.import_module("hermes_cli.dev_web_plugin_runtime_binding").__file__
        ).read_text(encoding="utf-8")
        for token in ("open(", ".stat(", ".resolve(", "expanduser("):
            assert token not in src, f"binding references forbidden surface {token!r}"

    def test_importing_binding_does_not_resolve_production_home(self, monkeypatch) -> None:
        # Behavioral proof: importing + running the binding never escalates to a
        # real stat / lstat of a production path.
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

        run_dev_plugin_from_descriptor(_base_descriptor(), {"text": "x"})
        run_dev_plugin_from_descriptor(
            _base_descriptor(descriptorId="d", metadata={"example": FAKE_PATHS[0]})
        )
        assert accesses == [], f"binding stat()'d a production path: {accesses}"


# ===========================================================================
# B. Binding happy path (each allowed descriptor binds + executes)
# ===========================================================================


class TestBindingHappyPath:
    @pytest.mark.parametrize(
        "plugin_id, operation, payload, expected",
        (
            ("fixture.echo", "echo_uppercase", {"text": "hello"}, {"text": "HELLO"}),
            ("fixture.transform", "normalize_text", {"text": "  a   b  "}, {"text": "a b"}),
            (
                "fixture.validate",
                "validate_required_keys",
                {"payload": {"name": "x"}, "required": ["name"]},
                {"valid": True, "missing": []},
            ),
            ("fixture.math", "count_items", {"items": [1, 2, 3, 4]}, {"count": 4}),
        ),
    )
    def test_allowed_descriptor_binds_and_executes(
        self, plugin_id: str, operation: str, payload: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        descriptor = _descriptor_for(plugin_id, operation)
        binding = resolve_runtime_descriptor_binding(descriptor)
        assert binding.binding_allowed is True
        assert binding.source == DESCRIPTOR_BINDING_SOURCE
        assert binding.fixture_only is True
        assert binding.dev_only is True
        assert binding.reviewed_fixture is True
        assert binding.plugin_id == plugin_id
        assert binding.operation == operation

        result = run_dev_plugin_from_descriptor(descriptor, payload)
        assert result.allowed is True
        assert result.executed is True
        assert result.failed is False
        assert dict(result.output_payload) == expected
        # The audit carries the descriptor id + the static-registry source.
        assert result.redacted_audit.get("registrySource") == DESCRIPTOR_BINDING_SOURCE
        binding_view = result.redacted_audit.get("descriptorBinding", {})
        assert binding_view.get("bindingAllowed") is True
        assert binding_view.get("source") == DESCRIPTOR_BINDING_SOURCE
        # P0: dev-only partial evidence; resolves / authorizes nothing.
        assert result.p0_evidence.get("resolved") is False
        assert result.p0_evidence.get("resolvedCount") == 0
        assert result.p0_evidence.get("implementationGate") == IMPLEMENTATION_AUTHORIZATION
        assert result.p0_evidence.get("phase3iGate") is False

    def test_redact_payload_descriptor_redacts_fake_secrets(self) -> None:
        descriptor = _descriptor_for("fixture.redact", "redact_payload")
        result = run_dev_plugin_from_descriptor(
            descriptor, {"token": FAKE_SECRETS[0], "path": FAKE_PATHS[0]}
        )
        assert result.allowed is True
        assert result.executed is True
        blob = _blob(result.output_payload) + _blob(result.redacted_audit)
        for fake in FAKE_SECRETS:
            assert fake not in blob
        assert "state.db" not in _blob(result.output_payload)
        # Runtime flags frozen.
        assert dict(result.runtime_flags) == RUNTIME_FLAGS_FROZEN

    def test_fault_descriptor_executes_then_fails(self) -> None:
        descriptor = _descriptor_for("fixture.fault", "deliberate_failure")
        result = run_dev_plugin_from_descriptor(descriptor, {"x": 1})
        assert result.allowed is False
        assert result.failed is True
        assert result.executed is True  # the fixture ran, then failed
        assert "fixture_execution_failed" in result.denial_reasons
        # The fake secret in the failure message is redacted everywhere.
        blob = _blob(result.output_payload) + _blob(result.redacted_audit) + _blob(result.errors)
        assert "sk-FAKE-SECRET-DO-NOT-LEAK-12345678" not in blob
        # P0: failure-mode evidence; still resolves nothing.
        assert result.p0_evidence.get("resolved") is False

    def test_registry_descriptor_lookup_executes(self) -> None:
        result = run_dev_plugin_from_registry_descriptor(
            REVIEWED_FIXTURE_DESCRIPTORS,
            "descriptor.fixture.count_items",
            {"items": [10, 20]},
        )
        assert result.allowed is True
        assert result.executed is True
        assert dict(result.output_payload) == {"count": 2}

    def test_registry_descriptor_lookup_returns_defensive_copy(self) -> None:
        fetched = lookup_reviewed_fixture_descriptor(REVIEWED_FIXTURE_DESCRIPTORS, "descriptor.fixture.echo_uppercase")
        assert fetched is not None
        fetched["pluginId"] = "tampered"
        # The static table is unaffected.
        again = lookup_reviewed_fixture_descriptor(REVIEWED_FIXTURE_DESCRIPTORS, "descriptor.fixture.echo_uppercase")
        assert again is not None
        assert again["pluginId"] == "fixture.echo"

    def test_no_side_effects_no_route_no_store(self, tmp_path: Path) -> None:
        descriptor = _descriptor_for("fixture.echo", "echo_uppercase")
        run_dev_plugin_from_descriptor(descriptor, {"text": "a"})
        assert find_runtime_store_artifacts(tmp_path) == []
        assert dict(run_dev_plugin_from_descriptor(descriptor, {"text": "a"}).runtime_flags) == RUNTIME_FLAGS_FROZEN


# ===========================================================================
# C. Binding denied path (each denied descriptor is refused)
# ===========================================================================


class TestBindingDeniedPath:
    @pytest.mark.parametrize(
        "overrides, expected_reason",
        (
            ({"source": "remote_registry"}, "remote_registry_denied"),
            ({"source": "marketplace"}, "marketplace_denied"),
            ({"marketplace": "evil"}, "descriptor_carries_execution_surface"),
            ({"command": "evil-run"}, "descriptor_carries_execution_surface"),
            ({"module": "pkg.mod"}, "descriptor_carries_execution_surface"),
            ({"entrypoint": "main"}, "descriptor_carries_execution_surface"),
            ({"url": "https://evil.example"}, "descriptor_carries_execution_surface"),
            ({"dockerImage": "evil:latest"}, "descriptor_carries_execution_surface"),
            ({"pluginId": "fixture.unknown"}, "descriptor_plugin_id_not_fixture"),
            ({"operation": "unknown_op"}, "descriptor_operation_not_fixture"),
            ({"requestedCapabilities": ("sandbox.proof.evaluate",)}, "capability_mismatch_denied"),
            ({"productionAllowed": True}, "descriptor_metadata_production_smuggling"),
        ),
    )
    def test_denied_descriptor_is_refused(self, overrides: dict[str, Any], expected_reason: str) -> None:
        descriptor = _base_descriptor(descriptorId="descriptor.denied", **overrides)
        binding = resolve_runtime_descriptor_binding(descriptor)
        assert binding.binding_allowed is False
        assert expected_reason in binding.denial_reasons
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        assert result.allowed is False
        assert result.executed is False
        # Authorization stays NO-GO regardless of the denial.
        assert result.p0_evidence.get("implementationGate") == IMPLEMENTATION_AUTHORIZATION
        assert result.p0_evidence.get("resolved") is False

    def test_remote_registry_source_value_denied_by_binding(self) -> None:
        # The binding layer's provenance check denies a ``source: remote_registry``
        # value even though the descriptor-only evaluator alone would allow it.
        descriptor = _base_descriptor(descriptorId="d.rr", source="remote_registry")
        allowed, reasons, _ = validate_runtime_descriptor_for_fixture_runtime(descriptor)
        assert allowed is False
        assert "remote_registry_denied" in reasons

    def test_provider_and_llm_generated_sources_denied(self) -> None:
        for source, reason in (
            ("provider_generated", "provider_generated_denied"),
            ("llm_generated", "llm_generated_denied"),
            ("external_fetch", "external_fetch_denied"),
        ):
            descriptor = _base_descriptor(descriptorId=f"d.{source}", source=source)
            binding = resolve_runtime_descriptor_binding(descriptor)
            assert binding.binding_allowed is False
            assert reason in binding.denial_reasons

    def test_capability_mismatch_denied(self) -> None:
        descriptor = _base_descriptor(
            descriptorId="d.cm", requestedCapabilities=("sandbox.proof.evaluate",)
        )
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        assert result.allowed is False
        assert "capability_mismatch_denied" in result.denial_reasons

    def test_secret_leak_in_metadata_redacted_and_denied(self) -> None:
        descriptor = _base_descriptor(
            descriptorId="d.sl", metadata={"note": FAKE_SECRETS[0]}
        )
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        assert result.allowed is False
        assert "descriptor_metadata_secret_leak" in result.denial_reasons
        # The fake secret is never echoed into any projection.
        blob = _blob(result.redacted_audit) + _blob(result.output_payload) + _blob(result.denial_reasons)
        for fake in FAKE_SECRETS:
            assert fake not in blob

    def test_path_leak_in_metadata_denied(self) -> None:
        descriptor = _base_descriptor(descriptorId="d.pl", metadata={"example": FAKE_PATHS[0]})
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        assert result.allowed is False
        assert "descriptor_metadata_path_leak" in result.denial_reasons

    def test_registry_descriptor_not_found_denied(self) -> None:
        result = run_dev_plugin_from_registry_descriptor(
            REVIEWED_FIXTURE_DESCRIPTORS, "descriptor.does.not.exist", {}
        )
        assert result.allowed is False
        assert result.executed is False
        assert "descriptor_not_in_static_registry" in result.denial_reasons

    def test_missing_descriptor_denied(self) -> None:
        result = run_dev_plugin_from_descriptor(None)
        assert result.allowed is False
        assert result.executed is False

    def test_malformed_descriptor_denied(self) -> None:
        result = run_dev_plugin_from_descriptor("not-a-mapping")
        assert result.allowed is False
        assert result.executed is False


# ===========================================================================
# D. Nested dangerous descriptor fields (dict / list / casing / JSON string)
# ===========================================================================


class TestNestedDangerousFields:
    @pytest.mark.parametrize(
        "metadata_value",
        (
            {"command": "evil"},                       # nested dict
            [{"module": "pkg.mod"}],                   # list of dict
            {"deep": {"entrypoint": "main"}},          # deep dict
            {"container": [{"shell": "evil"}]},        # dict + list + dict
            {"dockerImage": "evil:latest"},            # camelCase
            {"plugin_path": "/evil"},                  # snake_case (path stem)
            {"plugin-path": "/evil"},                  # kebab-case (path stem)
        ),
    )
    def test_nested_execution_surface_denied(self, metadata_value: Any) -> None:
        descriptor = _base_descriptor(
            descriptorId="d.nested", metadata=metadata_value
        )
        binding = resolve_runtime_descriptor_binding(descriptor)
        assert binding.binding_allowed is False
        # The descriptor carries an execution surface somewhere nested.
        assert any(
            r in binding.denial_reasons
            for r in (
                "descriptor_carries_execution_surface",
                "descriptor_metadata_secret_leak",
                "descriptor_metadata_path_leak",
            )
        )
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        assert result.allowed is False
        assert result.executed is False

    def test_jsonlike_string_descriptor_value_does_not_smuggle_execution(self) -> None:
        # A stringified-JSON value under a clean key is treated as opaque text;
        # it must not be parsed into an execution surface, and the clean
        # descriptor still binds.
        descriptor = _base_descriptor(
            descriptorId="d.json",
            description='{"command":"evil"} not parsed',
        )
        binding = resolve_runtime_descriptor_binding(descriptor)
        assert binding.binding_allowed is True


# ===========================================================================
# E. Descriptor metadata smuggling (authorization bypass attempts ignored)
# ===========================================================================


class TestMetadataSmuggling:
    @pytest.mark.parametrize(
        "smuggle_key, smuggle_value",
        (
            ("implementation_authorization", "GO"),
            ("implementationAuthorization", "GO"),
            ("phase_3i_authorized", True),
            ("phase3iAuthorized", True),
            ("production_approved", True),
            ("route_exception_approved", True),
            ("real_runtime_authorized", True),
            ("p0_resolved", True),
            ("approved_by_ai", True),
            ("trust_token", "fake-trust"),
        ),
    )
    def test_metadata_smuggling_denied_and_ignored(
        self, smuggle_key: str, smuggle_value: Any
    ) -> None:
        # Smuggling keys that do NOT trip the descriptor secret-surface scan
        # land in the binding's smuggling detector; keys that DO trip it
        # (e.g. implementation_authorization → authorization) are denied even
        # earlier. Either way: denied, no escalation.
        descriptor = _base_descriptor(
            descriptorId="d.smuggle", metadata={smuggle_key: smuggle_value}
        )
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        assert result.allowed is False
        assert result.p0_evidence.get("resolved") is False
        assert result.p0_evidence.get("implementationGate") == IMPLEMENTATION_AUTHORIZATION
        assert result.p0_evidence.get("phase3iGate") is False

    def test_request_metadata_smuggling_denied(self) -> None:
        descriptor = _base_descriptor()
        smuggling = {
            "implementation_authorization": "GO",
            "phase_3i_authorized": True,
            "approved": True,
            "trust_token": "fake",
            "p0_resolved": True,
        }
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"}, metadata=smuggling)
        assert result.allowed is False
        assert "descriptor_metadata_smuggling_denied" in result.denial_reasons

    def test_smuggling_does_not_resolve_any_gate(self) -> None:
        # The 24-gate summary must stay fully unresolved regardless of smuggling.
        smuggling = {
            "implementation_authorization": "GO",
            "phase_3i_authorized": True,
            "production_approved": True,
            "route_exception_approved": True,
            "p0_resolved": True,
            "resolved_ids": ["P0-15", "P0-22", "P0-24"],
            "approved_by_ai": True,
            "trust_token": "fake-real-trust",
        }
        summary = evaluate_p0_evidence(untrusted_metadata=smuggling)
        assert summary.resolved_count == 0
        assert summary.implementation_authorization == IMPLEMENTATION_AUTHORIZATION
        assert summary.phase_3i_authorized is False
        assert summary.real_runtime == REAL_RUNTIME
        assert summary.new_route == NEW_ROUTE
        assert summary.production_rollout == PRODUCTION_ROLLOUT
        assert all(not g.is_resolved() for g in GATES)


# ===========================================================================
# F. Batch descriptor runtime execution
# ===========================================================================


class TestBatchDescriptorRuntime:
    def test_batch_all_allowed(self) -> None:
        descriptors = [
            _descriptor_for("fixture.echo", "echo_uppercase"),
            _descriptor_for("fixture.math", "count_items"),
            _descriptor_for("fixture.transform", "normalize_text"),
        ]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="all-allowed")
        assert isinstance(batch, PluginRuntimeBatchResult)
        assert batch.total == 3
        assert batch.succeeded == 3
        assert batch.failed == 0
        assert batch.denied == 0
        # Result order preserved; descriptor ids preserved per result.
        assert [r.plugin_id for r in batch.results] == [
            "fixture.echo",
            "fixture.math",
            "fixture.transform",
        ]
        assert batch.p0_evidence.get("resolved") is False

    def test_batch_mixed_isolated(self) -> None:
        descriptors = [
            _descriptor_for("fixture.echo", "echo_uppercase"),
            _base_descriptor(descriptorId="d.bad", source="remote_registry"),  # denied
            _descriptor_for("fixture.fault", "deliberate_failure"),  # failure
            _descriptor_for("fixture.math", "count_items"),  # allowed
        ]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="mixed")
        assert batch.total == 4
        assert batch.succeeded == 2  # echo + math
        assert batch.denied == 1  # remote registry
        assert batch.failed == 1  # fault
        # Isolation: the denied / failed descriptors did not poison the allowed ones.
        assert batch.results[0].allowed is True
        assert batch.results[2].failed is True
        assert batch.results[3].allowed is True

    def test_batch_fail_fast_stops_at_first_non_allowed(self) -> None:
        descriptors = [
            _descriptor_for("fixture.echo", "echo_uppercase"),
            _base_descriptor(descriptorId="d.bad", source="marketplace"),  # denied → stop
            _descriptor_for("fixture.math", "count_items"),  # should NOT run
        ]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="ff", fail_fast=True)
        assert batch.total == 2  # stopped after the denial
        assert batch.results[1].allowed is False

    def test_batch_fail_fast_false_runs_all(self) -> None:
        descriptors = [
            _base_descriptor(descriptorId="d.bad1", source="marketplace"),
            _descriptor_for("fixture.echo", "echo_uppercase"),
            _base_descriptor(descriptorId="d.bad2", source="remote_registry"),
        ]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="nofail", fail_fast=False)
        assert batch.total == 3

    def test_batch_metadata_smuggling_fails_closed(self) -> None:
        descriptors = [_descriptor_for("fixture.echo", "echo_uppercase")]
        batch = run_dev_plugin_batch_from_descriptors(
            descriptors,
            batch_id="smuggle",
            metadata={"implementation_authorization": "GO", "approved": True},
        )
        assert batch.total == 0
        assert "descriptor_batch_metadata_smuggling_denied" in batch.errors

    def test_batch_oversized_fails_closed(self) -> None:
        descriptors = [
            _descriptor_for("fixture.echo", "echo_uppercase") for _ in range(40)
        ]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="big")
        assert batch.total == 0
        assert "descriptor_batch_oversized" in batch.errors

    def test_batch_malformed_fails_closed(self) -> None:
        batch = run_dev_plugin_batch_from_descriptors("not-a-list", batch_id="bad")
        assert batch.total == 0
        assert "descriptor_batch_malformed" in batch.errors

    def test_batch_audit_redacted_and_unpersisted(self) -> None:
        descriptors = [
            _descriptor_for("fixture.redact", "redact_payload"),
        ]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="redact-batch")
        blob = _blob(batch.redacted_audit)
        for fake in FAKE_SECRETS:
            assert fake not in blob
        assert batch.redacted_audit.get("persisted") is False
        assert batch.redacted_audit.get("registrySource") == DESCRIPTOR_BINDING_SOURCE

    def test_batch_resolves_nothing(self) -> None:
        descriptors = [_descriptor_for("fixture.echo", "echo_uppercase")]
        batch = run_dev_plugin_batch_from_descriptors(descriptors, batch_id="noop0")
        assert batch.p0_evidence.get("resolved") is False
        assert batch.p0_evidence.get("resolvedCount") == 0
        assert batch.p0_evidence.get("implementationGate") == IMPLEMENTATION_AUTHORIZATION
        assert dict(batch.runtime_flags) == RUNTIME_FLAGS_FROZEN


# ===========================================================================
# G. Immutability / tamper resistance
# ===========================================================================


class TestImmutability:
    def test_mutate_descriptor_after_binding_does_not_affect_result(self) -> None:
        descriptor = _descriptor_for("fixture.echo", "echo_uppercase")
        binding = resolve_runtime_descriptor_binding(descriptor)
        assert binding.binding_allowed is True
        # Mutate the caller dict after binding.
        descriptor["pluginId"] = "fixture.unknown"
        descriptor["source"] = "remote_registry"
        # The already-resolved binding is frozen + deep-copied.
        assert binding.plugin_id == "fixture.echo"
        assert binding.binding_allowed is True

    def test_mutate_descriptor_after_request_does_not_affect_runtime(self) -> None:
        descriptor = _descriptor_for("fixture.echo", "echo_uppercase")
        # Hold a reference, then mutate before running.
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "hi"})
        descriptor["pluginId"] = "fixture.unknown"
        # The already-produced result is frozen.
        assert result.allowed is True
        assert result.output_payload == {"text": "HI"}

    def test_mutate_returned_binding_does_not_authorize(self) -> None:
        descriptor = _base_descriptor(descriptorId="d", source="remote_registry")
        binding = resolve_runtime_descriptor_binding(descriptor)
        # The binding is a frozen dataclass; attempting to flip authorization
        # via attribute assignment is blocked by frozen=True.
        with pytest.raises(Exception):
            binding.binding_allowed = True  # type: ignore[misc]

    def test_mutate_result_audit_does_not_leak(self) -> None:
        descriptor = _descriptor_for("fixture.echo", "echo_uppercase")
        result = run_dev_plugin_from_descriptor(descriptor, {"text": "x"})
        # The audit is a frozen MappingProxyType; in-place mutation is blocked.
        with pytest.raises(TypeError):
            result.redacted_audit["registrySource"] = "production"  # type: ignore[index]

    def test_repeated_execution_shares_no_state(self) -> None:
        descriptor = _descriptor_for("fixture.echo", "echo_uppercase")
        r1 = run_dev_plugin_from_descriptor(descriptor, {"text": "a"})
        r2 = run_dev_plugin_from_descriptor(descriptor, {"text": "b"})
        assert r1.output_payload == {"text": "A"}
        assert r2.output_payload == {"text": "B"}
        # Each result's audit is an independent frozen mapping.
        assert r1.redacted_audit is not r2.redacted_audit


# ===========================================================================
# H. Source boundary (no dynamic loading / network / shell / secrets)
# ===========================================================================


class TestSourceBoundary:
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
        ("hermes_cli.dev_web_plugin_runtime_binding",),
    )
    def test_module_source_has_no_forbidden_surface(self, module_name: str) -> None:
        src = self._src(module_name)
        for token in self._FORBIDDEN_TOKENS:
            assert token not in src, f"{module_name}: forbidden token {token!r}"

    def test_no_arbitrary_plugin_directory_loading(self) -> None:
        src = self._src("hermes_cli.dev_web_plugin_runtime_binding")
        for token in ("import_module", "walk(", "scandir", "glob(", "listdir", "load_module"):
            assert token not in src, f"binding references loader surface {token!r}"

    def test_no_marketplace_or_remote_fetch_surface(self) -> None:
        src = self._src("hermes_cli.dev_web_plugin_runtime_binding")
        assert "def fetch_" not in src
        assert "def install_" not in src
        assert "def load_plugin" not in src

    def test_binding_does_not_import_dev_web_api(self) -> None:
        src = self._src("hermes_cli.dev_web_plugin_runtime_binding")
        assert "dev_web_api" not in src
        assert "create_dev_web_api_app" not in src

    def test_reasons_are_a_known_token_set(self) -> None:
        # Every registry-level reason the binding emits must be a member of the
        # frozen binding token set (runtime-sourced reasons such as
        # ``capability_mismatch_denied`` / ``fixture_execution_failed`` belong to
        # the runtime's :data:`~dev_web_plugin_runtime.RUNTIME_REASONS` and are
        # merged in separately).
        for token in (
            "descriptor_not_in_static_registry",
            "remote_registry_denied",
            "marketplace_denied",
            "descriptor_metadata_smuggling_denied",
            "descriptor_carries_execution_surface",
            "descriptor_metadata_secret_leak",
            "descriptor_metadata_path_leak",
        ):
            assert token in DESCRIPTOR_BINDING_REASONS


# ===========================================================================
# I. dev_web_api isolation + route governance
# ===========================================================================


class TestDevWebApiIsolation:
    def test_binding_not_imported_by_dev_web_api(self) -> None:
        import importlib

        src = Path(importlib.import_module("hermes_cli.dev_web_api").__file__).read_text(encoding="utf-8")
        assert "dev_web_plugin_runtime_binding" not in src
        assert "run_dev_plugin_from_descriptor" not in src
        assert "resolve_runtime_descriptor_binding" not in src
        assert "REVIEWED_FIXTURE_DESCRIPTORS" not in src

    @pytest.mark.parametrize(
        "path",
        (
            "/api/dev/v1/plugins/descriptor-runtime",
            "/api/dev/v1/plugins/descriptor-runtime/batch",
            "/api/dev/v1/descriptor-registry/runtime",
            "/api/dev/v1/plugins/from-descriptor",
            "/api/dev/v1/plugins/registry-descriptor",
        ),
    )
    def test_descriptor_runtime_probes_yield_no_route(self, client: TestClient, path: str) -> None:
        response = client.get(path)
        assert response.status_code == 404

    def test_route_governance_unchanged(self, app) -> None:
        assert_route_governance_unchanged(app, expected=ROUTE_GOVERNANCE_EXPECTED)

    def test_frozen_scenario_libraries_unchanged(self) -> None:
        assert len(FIXED_SCENARIOS) == 22
        assert len(RUNTIME_PROOF_SCENARIOS) == 5
        assert len(RUNTIME_EXPANSION_PROOF_SCENARIOS) == 4
        assert len(DESCRIPTOR_REGISTRY_PROOF_SCENARIOS) == 5
        assert len(get_descriptor_registry_proof_scenarios()) == 5


# ===========================================================================
# J. Production safety (no ~/.hermes / state.db / process / artifact)
# ===========================================================================


class TestProductionSafety:
    def test_running_descriptor_runtime_does_not_stat_production(self, monkeypatch) -> None:
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

        run_dev_plugin_from_descriptor(_descriptor_for("fixture.echo", "echo_uppercase"), {"text": "x"})
        run_dev_plugin_from_descriptor(
            _base_descriptor(descriptorId="d.denied", source="remote_registry"), {}
        )
        run_dev_plugin_batch_from_descriptors(
            [_descriptor_for("fixture.math", "count_items")],
            batch_id="prod-safe",
        )
        assert accesses == [], f"descriptor runtime stat()'d production: {accesses}"

    def test_no_runtime_artifacts_created(self, tmp_path: Path) -> None:
        run_dev_plugin_from_descriptor(_descriptor_for("fixture.echo", "echo_uppercase"), {"text": "x"})
        run_dev_plugin_batch_from_descriptors(
            [
                _descriptor_for("fixture.fault", "deliberate_failure"),
                _descriptor_for("fixture.math", "count_items"),
            ],
            batch_id="no-artifacts",
        )
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_denied_descriptor_does_not_stat_production(self, monkeypatch) -> None:
        import os

        accesses: list[str] = []
        real_stat = os.stat

        def _spy(func):
            def wrapper(path, *args, **kwargs):
                text = str(path)
                if ".hermes" in text.lower() or "state.db" in text.lower():
                    accesses.append(text)
                return func(path, *args, **kwargs)

            return wrapper

        monkeypatch.setattr(os, "stat", _spy(real_stat))
        run_dev_plugin_from_descriptor(
            _base_descriptor(descriptorId="d.cmd", command="evil"), {}
        )
        assert accesses == []


# ===========================================================================
# K. P0 integration (partial evidence only; resolves nothing)
# ===========================================================================


class TestP0Integration:
    def test_happy_path_creates_partial_evidence_only(self) -> None:
        result = run_dev_plugin_from_descriptor(
            _descriptor_for("fixture.echo", "echo_uppercase"), {"text": "x"}
        )
        assert result.p0_evidence.get("classification") == "partial_evidence"
        assert result.p0_evidence.get("resolved") is False
        assert result.p0_evidence.get("resolvedCount") == 0
        assert result.p0_evidence.get("implementationGate") == IMPLEMENTATION_AUTHORIZATION
        assert result.p0_evidence.get("phase3iGate") is False
        assert result.p0_evidence.get("realRuntimeGate") == REAL_RUNTIME
        assert result.p0_evidence.get("newRouteGate") == NEW_ROUTE
        assert result.p0_evidence.get("productionRolloutGate") == PRODUCTION_ROLLOUT

    def test_denied_descriptor_creates_guard_evidence(self) -> None:
        result = run_dev_plugin_from_descriptor(
            _base_descriptor(descriptorId="d.denied", source="remote_registry"), {}
        )
        assert result.p0_evidence.get("classification") == "guard_evidence"
        assert result.p0_evidence.get("resolved") is False

    def test_failure_descriptor_creates_failure_mode_evidence(self) -> None:
        result = run_dev_plugin_from_descriptor(
            _descriptor_for("fixture.fault", "deliberate_failure"), {"x": 1}
        )
        assert result.p0_evidence.get("classification") == "failure_mode_evidence"
        assert result.p0_evidence.get("resolved") is False

    def test_batch_creates_reproducibility_evidence_only(self) -> None:
        batch = run_dev_plugin_batch_from_descriptors(
            [_descriptor_for("fixture.echo", "echo_uppercase")], batch_id="p0-batch"
        )
        assert batch.p0_evidence.get("resolved") is False
        assert batch.p0_evidence.get("resolvedCount") == 0
        assert batch.p0_evidence.get("implementationGate") == IMPLEMENTATION_AUTHORIZATION

    def test_resolved_count_stays_zero_globally(self) -> None:
        # Run a full happy path + batch + denied; the 24-gate summary is intact.
        run_dev_plugin_from_descriptor(_descriptor_for("fixture.echo", "echo_uppercase"), {"text": "x"})
        run_dev_plugin_batch_from_descriptors(
            [_descriptor_for("fixture.math", "count_items")], batch_id="global"
        )
        summary = evaluate_p0_evidence()
        assert summary.resolved_count == 0
        assert summary.total_gates == 24
        assert summary.implementation_authorization == IMPLEMENTATION_AUTHORIZATION
        assert summary.phase_3i_authorized is False


# ===========================================================================
# L. Proof scenarios (the separate descriptor-registry scenario library)
# ===========================================================================


class TestDescriptorRegistryProofScenarios:
    @pytest.mark.parametrize("scenario", DESCRIPTOR_REGISTRY_PROOF_SCENARIOS)
    def test_scenario_passes_proof_runner(self, scenario: Any) -> None:
        summary = run_proof_scenarios([scenario])
        assert summary.passed_scenarios == 1
        assert summary.failed_scenarios == 0

    def test_scenario_run_resolves_nothing(self) -> None:
        summary = run_proof_scenarios(list(get_descriptor_registry_proof_scenarios()))
        assert summary.passed_scenarios == len(DESCRIPTOR_REGISTRY_PROOF_SCENARIOS)
        assert summary.failed_scenarios == 0
        assert summary.implementation_authorization == IMPLEMENTATION_AUTHORIZATION
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == REAL_RUNTIME
        assert summary.new_route == NEW_ROUTE
        assert summary.production_rollout == PRODUCTION_ROLLOUT
