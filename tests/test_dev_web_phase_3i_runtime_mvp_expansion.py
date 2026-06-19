"""Phase 3I Dev-only Local Plugin Runtime MVP — Expansion tests.

A dedicated regression suite for the **Phase 3I runtime expansion**: the four
new reviewed fixture operations (`normalize_text`, `validate_required_keys`,
`count_items`, `redact_payload`), the per-operation metadata + allowlist
hardening, descriptor-to-fixture binding for the new operations, batch runtime
execution (`run_dev_plugin_batch`), runtime input/output validation, failure
isolation, audit redaction, and P0 evidence projection.

Scope (frozen, mirrors the task authorization):

  - **code allowed / production forbidden.** The runtime executes ONLY reviewed
    fixture operations bound through a hardcoded allowlist. No arbitrary plugin
    loading, no remote registry, no marketplace, no external plugin fetch, no
    provider-generated / LLM-generated plugin install, no real API-key read, no
    external network, no new route, no production rollout.
  - Every forbidden path is a **fake / temp / string-policy** target; the real
    ``~/.hermes`` and production ``state.db`` are never opened, stated, or
    resolved (not even for metadata). Every secret is an obvious **fake**.

A successful fixture execution (single or batch) is **dev-only partial
evidence**. It is **never** Implementation Authorization GO, **never** Phase 3I
production authorization, **never** real-runtime authorization, **never** a P0
resolution. ``resolved_count`` stays 0 and the authorization flags stay NO-GO /
not-authorized no matter what runs or what untrusted metadata a request carries.
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
    FIXTURE_REGISTRY,
    FIXTURE_SAFETY_FLAGS,
    FixtureInputError,
    FixtureOperation,
    FixtureOutputError,
    MAX_FIXTURE_INPUT_BYTES,
    MAX_FIXTURE_LIST_ITEMS,
    MAX_FIXTURE_NESTING_DEPTH,
    count_items,
    get_fixture_registry,
    normalize_text,
    redact_payload,
    validate_fixture_metadata,
    validate_required_keys,
)
from hermes_cli.dev_web_plugin_runtime import (
    MAX_BATCH_REQUESTS,
    PLUGIN_RUNTIME_AUDIT_SOURCE,
    RUNTIME_FLAGS_FROZEN,
    RUNTIME_REASONS,
    PluginRuntimeBatchRequest,
    PluginRuntimeBatchResult,
    PluginRuntimeRequest,
    RuntimeBinding,
    assert_no_side_effect_surface,
    resolve_runtime_binding,
    run_dev_plugin,
    run_dev_plugin_batch,
)
from hermes_cli.dev_web_p0_evidence import (
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    evaluate_p0_evidence,
)
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    find_runtime_store_artifacts,
    route_governance_new_route_flags,
)
from hermes_cli.dev_web_sandbox_guards import REDACTED_VALUE, contains_secret
from hermes_cli.dev_web_sandbox_runner import run_proof_scenarios
from hermes_cli.dev_web_sandbox_scenarios import (
    FIXED_SCENARIOS,
    RUNTIME_EXPANSION_PROOF_SCENARIOS,
    RUNTIME_PROOF_SCENARIOS,
    get_runtime_expansion_proof_scenarios,
)

#: Obvious fake secrets used to prove redaction. None is real.
FAKE_SECRETS: tuple[str, ...] = (
    "sk-FAKE-SECRET-DO-NOT-LEAK-12345678",
    "Authorization: Bearer fake-bearer-expansion",
    "ghp_fakegeneratedgithubtoken1234",
    "OPENAI_API_KEY=fake-expansion-value",
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
# A. New fixture operations (pure, redaction-safe)
# ===========================================================================


class TestNewFixtureOperations:
    def test_normalize_text_happy_path(self) -> None:
        assert dict(normalize_text({"text": "  Hello   World  "})) == {"text": "Hello World"}

    def test_normalize_text_collapses_all_whitespace(self) -> None:
        out = dict(normalize_text({"text": "\t  a\n\nb \t c  "}))
        assert out == {"text": "a b c"}

    def test_normalize_text_redacts_secret_shaped_input(self) -> None:
        out = dict(normalize_text({"text": "sk-fake-secret-12345678"}))
        assert out == {"text": REDACTED_VALUE}

    def test_normalize_text_rejects_non_string(self) -> None:
        with pytest.raises(FixtureInputError):
            normalize_text({"text": 123})

    def test_normalize_text_rejects_non_mapping(self) -> None:
        with pytest.raises(FixtureInputError):
            normalize_text("not-a-mapping")  # type: ignore[arg-type]

    def test_normalize_text_rejects_oversized(self) -> None:
        with pytest.raises(FixtureInputError):
            normalize_text({"text": "x" * (MAX_FIXTURE_INPUT_BYTES + 1)})

    def test_validate_required_keys_happy_path(self) -> None:
        out = dict(validate_required_keys({"payload": {"name": "Hermes"}, "required": ["name"]}))
        assert out == {"valid": True, "missing": []}

    def test_validate_required_keys_missing_sorted(self) -> None:
        out = dict(validate_required_keys({"payload": {"a": 1}, "required": ["c", "a", "b"]}))
        assert out["valid"] is False
        assert out["missing"] == ["b", "c"]  # sorted, only missing

    def test_validate_required_keys_never_leaks_values(self) -> None:
        out = dict(
            validate_required_keys(
                {"payload": {"secret": "sk-fake-secret-12345678"}, "required": ["secret"]}
            )
        )
        assert out == {"valid": True, "missing": []}
        assert "sk-fake-secret-12345678" not in _blob(out)

    def test_validate_required_keys_redacts_secret_shaped_missing_key(self) -> None:
        out = dict(
            validate_required_keys(
                {"payload": {}, "required": ["sk-fake-key-12345678", "name"]}
            )
        )
        # The missing list is sorted then redacted; the secret-shaped key is
        # collapsed wherever it lands in the sorted order.
        assert REDACTED_VALUE in out["missing"]
        assert "name" in out["missing"]
        assert out["valid"] is False

    def test_validate_required_keys_rejects_non_list_required(self) -> None:
        with pytest.raises(FixtureInputError):
            validate_required_keys({"payload": {}, "required": "name"})

    def test_validate_required_keys_rejects_non_string_required_entry(self) -> None:
        with pytest.raises(FixtureInputError):
            validate_required_keys({"payload": {}, "required": ["ok", 5]})

    def test_validate_required_keys_rejects_non_mapping_payload(self) -> None:
        with pytest.raises(FixtureInputError):
            validate_required_keys({"payload": ["not", "a", "mapping"], "required": []})

    def test_validate_required_keys_rejects_oversized(self) -> None:
        with pytest.raises(FixtureInputError):
            validate_required_keys(
                {"payload": {"a": 1}, "required": ["k"] * (MAX_FIXTURE_INPUT_BYTES + 1)}
            )

    def test_count_items_happy_path(self) -> None:
        assert dict(count_items({"items": [1, 2, 3]})) == {"count": 3}

    def test_count_items_empty_list(self) -> None:
        assert dict(count_items({"items": []})) == {"count": 0}

    def test_count_items_never_leaks_values(self) -> None:
        out = dict(count_items({"items": ["sk-fake-secret-12345678", "x"]}))
        assert out == {"count": 2}
        assert "sk-fake-secret-12345678" not in _blob(out)

    def test_count_items_rejects_non_list(self) -> None:
        with pytest.raises(FixtureInputError):
            count_items({"items": "not-a-list"})

    def test_count_items_rejects_oversized_list(self) -> None:
        with pytest.raises(FixtureInputError):
            count_items({"items": list(range(MAX_FIXTURE_LIST_ITEMS + 1))})

    def test_redact_payload_redacts_fake_secrets(self) -> None:
        out = dict(
            redact_payload(
                {
                    "apiKey": "sk-fake-secret-12345678",
                    "header": "Authorization: Bearer fake-bearer",
                    "pem": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
                    "ok": "plain-value",
                }
            )
        )
        assert out["apiKey"] == REDACTED_VALUE
        assert out["header"] == REDACTED_VALUE
        assert out["pem"] == REDACTED_VALUE
        assert out["ok"] == "plain-value"
        assert contains_secret(out) is False

    def test_redact_payload_redacts_forbidden_paths(self) -> None:
        out = dict(
            redact_payload(
                {
                    "home": "/Users/someone/.hermes/memory/foo",
                    "db": "/fake/production/state.db",
                    "env": "OPENAI_API_KEY=fake-value",
                }
            )
        )
        assert out["home"] == REDACTED_VALUE
        assert out["db"] == REDACTED_VALUE
        assert out["env"] == REDACTED_VALUE
        assert contains_secret(out) is False

    def test_redact_payload_rejects_non_mapping(self) -> None:
        with pytest.raises(FixtureInputError):
            redact_payload("not-a-mapping")  # type: ignore[arg-type]


# ===========================================================================
# B. Fixture registry / allowlist immutability + metadata validation
# ===========================================================================


class TestRegistryImmutability:
    def test_registry_is_a_tuple_and_cannot_grow(self) -> None:
        assert isinstance(FIXTURE_REGISTRY, tuple)
        # A tuple has no append — the registry cannot be extended at runtime.
        assert not hasattr(FIXTURE_REGISTRY, "append")

    def test_allowlist_is_a_frozenset_and_cannot_grow(self) -> None:
        assert isinstance(FIXTURE_ALLOWLIST, frozenset)
        with pytest.raises(AttributeError):
            FIXTURE_ALLOWLIST.add(("fixture.evil", "run"))  # type: ignore[attr-defined]

    def test_fixture_operation_is_frozen_and_slots(self) -> None:
        op = FIXTURE_REGISTRY[0]
        # Frozen + slots: both an existing-field reassignment and a new-attribute
        # assignment must be rejected (some CPython versions raise TypeError
        # rather than AttributeError for the slots case — both are "rejected").
        with pytest.raises(Exception):
            op.plugin_id = "tampered"  # type: ignore[misc]
        with pytest.raises(Exception):
            op.smuggled = True  # type: ignore[attr-defined]

    def test_fixture_metadata_is_a_frozen_view(self) -> None:
        op = FIXTURE_REGISTRY[0]
        meta = op.metadata
        with pytest.raises(TypeError):
            meta["sideEffects"] = True  # type: ignore[index]
        # Every reviewed fixture declares an all-False, side-effect-free surface
        # (the canonical source is the frozen attribute, not the metadata view).
        for flag in FIXTURE_SAFETY_FLAGS:
            assert getattr(op, flag) is False
        # The view still exposes the camelCase safety flags read-only.
        assert meta["sideEffects"] is False
        assert meta["network"] is False

    def test_get_fixture_registry_returns_defensive_copy(self) -> None:
        a = get_fixture_registry()
        b = get_fixture_registry()
        assert a == b
        assert a is not b
        assert a is not FIXTURE_REGISTRY

    def test_validate_fixture_metadata_accepts_real_fixtures(self) -> None:
        for op in FIXTURE_REGISTRY:
            ok, reasons = validate_fixture_metadata(op)
            assert ok is True
            assert reasons == ()

    def test_validate_fixture_metadata_rejects_forged_unsafe_fixture(self) -> None:
        # A directly-constructed FixtureOperation with side_effects=True cannot
        # even be built (construction rejects it), so a smuggler cannot forge
        # one with bad metadata.
        with pytest.raises(ValueError):
            FixtureOperation(
                plugin_id="fixture.evil",
                operation="run",
                description="forged",
                invoker=lambda payload: {},
                side_effects=True,
            )

    def test_validate_fixture_metadata_rejects_non_operation(self) -> None:
        ok, reasons = validate_fixture_metadata(object())
        assert ok is False
        assert "fixture_metadata_missing" in reasons

    def test_validate_fixture_metadata_rejects_tampered_allowed_capabilities(self) -> None:
        # Bypass __post_init__ via object.__setattr__ to simulate a tampered
        # operation whose allowed_capabilities is no longer a tuple. The
        # validator must still catch it.
        op = FIXTURE_REGISTRY[0]
        tampered = FixtureOperation(
            plugin_id=op.plugin_id,
            operation=op.operation,
            description=op.description,
            invoker=op.invoker,
        )
        object.__setattr__(tampered, "allowed_capabilities", "not-a-tuple")  # type: ignore[arg-type]
        ok, reasons = validate_fixture_metadata(tampered)
        assert ok is False

    def test_external_mutation_cannot_affect_registry_lookup(self) -> None:
        # lookup_fixture resolves by the hardcoded registry index; a forged
        # (plugin_id, operation) pair that is NOT in the registry is never bound.
        from hermes_cli.dev_web_fixture_plugins import lookup_fixture

        assert lookup_fixture("fixture.evil", "normalize_text") is None
        assert lookup_fixture("fixture.transform", "evil_op") is None

    def test_forged_fixture_cannot_become_allowed_at_runtime(self) -> None:
        # Even if a caller constructs a valid-looking FixtureOperation, the
        # runtime binds only by hardcoded allowlist membership — the forged
        # operation is never invoked.
        forged = FixtureOperation(
            plugin_id="fixture.transform",
            operation="normalize_text",
            description="forged twin",
            invoker=lambda payload: {"forged": True},
        )
        result = run_dev_plugin(
            _req(
                plugin_id=forged.plugin_id,
                operation=forged.operation,
                input_payload={"text": "hi"},
            )
        )
        # The REAL normalize_text runs (registry lookup), NOT the forged invoker.
        assert dict(result.output_payload) == {"text": "hi"}


# ===========================================================================
# C. Descriptor-to-fixture binding for the new operations
# ===========================================================================


class TestDescriptorBindingExpansion:
    @pytest.mark.parametrize(
        "plugin_id,operation,payload,expected",
        (
            ("fixture.transform", "normalize_text", {"text": "  a  b "}, {"text": "a b"}),
            (
                "fixture.validate",
                "validate_required_keys",
                {"payload": {"x": 1}, "required": ["x"]},
                {"valid": True, "missing": []},
            ),
            ("fixture.math", "count_items", {"items": [1, 2, 3, 4]}, {"count": 4}),
            ("fixture.redact", "redact_payload", {"k": "ok"}, {"k": "ok"}),
        ),
    )
    def test_new_operation_executes_via_descriptor(
        self, plugin_id: str, operation: str, payload: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        result = run_dev_plugin(
            _req(
                descriptor={
                    "pluginId": plugin_id,
                    "operation": operation,
                    "source": "descriptor_only",
                },
                input_payload=payload,
            )
        )
        assert result.allowed is True
        assert result.executed is True
        assert dict(result.output_payload) == expected

    def test_resolve_binding_for_each_new_operation(self) -> None:
        for plugin_id, operation in (
            ("fixture.transform", "normalize_text"),
            ("fixture.validate", "validate_required_keys"),
            ("fixture.math", "count_items"),
            ("fixture.redact", "redact_payload"),
        ):
            binding = resolve_runtime_binding(_req(plugin_id=plugin_id, operation=operation))
            assert binding.resolved is True
            assert isinstance(binding, RuntimeBinding)
            assert binding.fixture is not None
            assert binding.fixture.plugin_id == plugin_id

    @pytest.mark.parametrize(
        "field,value",
        (
            ("module", "pkg.mod"),
            ("command", "python plugin.py"),
            ("entrypoint", "plugin:run"),
            ("url", "https://example.com/plugin.py"),
            ("importlib", "malicious.module"),
            ("dockerImage", "evil:latest"),
            ("shell", "bash -c rm"),
            ("subprocess", "['rm','-rf','/']"),
            ("file", "/tmp/evil.py"),
            ("path", "/tmp/evil"),
            ("pluginDir", "/tmp/plugins"),
            ("localDirectory", "/tmp/local"),
            ("registry", "evil.example.com"),
            ("marketplace", "evil-store"),
            ("remote", "https://evil.example"),
            ("providerGenerated", True),
            ("llmGenerated", True),
            ("executable", "/bin/sh"),
        ),
    )
    def test_descriptor_dangerous_top_level_field_denied(self, field: str, value: Any) -> None:
        descriptor = {
            "pluginId": "fixture.transform",
            "operation": "normalize_text",
            field: value,
        }
        result = run_dev_plugin(
            _req(plugin_id="fixture.transform", operation="normalize_text", descriptor=descriptor)
        )
        assert result.allowed is False
        assert result.executed is False
        assert "descriptor_carries_execution_surface" in result.denial_reasons

    def test_descriptor_dangerous_nested_field_denied(self) -> None:
        descriptor = {
            "pluginId": "fixture.math",
            "operation": "count_items",
            "nested": {"deep": {"module": "pkg.evil"}},
        }
        result = run_dev_plugin(
            _req(plugin_id="fixture.math", operation="count_items", descriptor=descriptor)
        )
        assert result.allowed is False
        assert "descriptor_carries_execution_surface" in result.denial_reasons

    def test_unknown_operation_denied(self) -> None:
        result = run_dev_plugin(_req(plugin_id="fixture.transform", operation="evil_op"))
        assert result.allowed is False
        assert "fixture_not_in_allowlist" in result.denial_reasons

    def test_unknown_plugin_denied(self) -> None:
        result = run_dev_plugin(_req(plugin_id="user.uploaded.plugin", operation="normalize_text"))
        assert result.allowed is False
        assert "fixture_not_in_allowlist" in result.denial_reasons

    def test_capability_mismatch_denied(self) -> None:
        # sandbox.proof.evaluate is a valid default-allowed label, but it is NOT
        # in a pure fixture's allowed set (descriptor.read only) → mismatch.
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.transform",
                operation="normalize_text",
                input_payload={"text": "hi"},
                requested_capabilities=("sandbox.proof.evaluate",),
            )
        )
        assert result.allowed is False
        assert "capability_mismatch_denied" in result.denial_reasons

    def test_capability_mismatch_does_not_fire_for_allowed_label(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.transform",
                operation="normalize_text",
                input_payload={"text": "hi"},
                requested_capabilities=("descriptor.read",),
            )
        )
        assert result.allowed is True

    def test_metadata_smuggling_denied_for_new_operation(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.math",
                operation="count_items",
                input_payload={"items": [1]},
                metadata={"implementation_authorization": "GO", "phase_3i_authorized": True},
            )
        )
        assert result.allowed is False
        assert "metadata_authorization_smuggling_denied" in result.denial_reasons
        assert result.p0_evidence["implementationGate"] == "NO-GO"
        assert result.p0_evidence["phase3iGate"] is False

    def test_binding_to_safe_dict_is_redacted(self) -> None:
        binding = resolve_runtime_binding(
            _req(plugin_id="fixture.validate", operation="validate_required_keys")
        )
        projection = binding.to_safe_dict()
        assert projection["fixture"]["invokerExposed"] is False
        assert contains_secret(projection) is False


# ===========================================================================
# D. Batch runtime execution
# ===========================================================================


class TestBatchExecution:
    def _echo(self, text: str = "a") -> PluginRuntimeRequest:
        return _req(
            plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": text}
        )

    def _count(self) -> PluginRuntimeRequest:
        return _req(plugin_id="fixture.math", operation="count_items", input_payload={"items": [1]})

    def _fault(self) -> PluginRuntimeRequest:
        return _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1})

    def _denied(self) -> PluginRuntimeRequest:
        return _req(plugin_id="local.bad", operation="run")

    def test_batch_all_success(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(), self._count()), batch_id="ok")
        )
        assert isinstance(result, PluginRuntimeBatchResult)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.denied == 0
        # Order preserved.
        assert [r.operation for r in result.results] == ["echo_uppercase", "count_items"]

    def test_batch_mixed_success_denied_failure(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(self._echo(), self._fault(), self._denied(), self._count()),
                batch_id="mixed",
            )
        )
        assert result.total == 4
        assert result.succeeded == 2
        assert result.failed == 1
        assert result.denied == 1

    def test_batch_fail_fast_stops_early(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(self._echo(), self._fault(), self._count()),
                batch_id="ff",
                fail_fast=True,
            )
        )
        # Stopped after the fault (the second request) — the count never ran.
        assert result.total == 2
        assert [r.operation for r in result.results] == ["echo_uppercase", "deliberate_failure"]

    def test_batch_fail_fast_false_continues(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(self._fault(), self._denied(), self._echo()),
                batch_id="nof",
                fail_fast=False,
            )
        )
        assert result.total == 3
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.denied == 1

    def test_batch_order_preserved(self) -> None:
        requests = tuple(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                input_payload={"text": str(i)},
            )
            for i in range(5)
        )
        result = run_dev_plugin_batch(PluginRuntimeBatchRequest(requests=requests, batch_id="ord"))
        assert [dict(r.output_payload)["text"] for r in result.results] == ["0", "1", "2", "3", "4"]

    def test_batch_failure_isolation(self) -> None:
        # A deliberate failure does not poison the next request.
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(self._fault(), self._echo("isolated")),
                batch_id="iso",
            )
        )
        assert result.total == 2
        assert result.results[0].failed is True
        assert result.results[1].allowed is True
        assert dict(result.results[1].output_payload) == {"text": "ISOLATED"}

    def test_batch_metadata_smuggling_fail_closed(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(self._echo(),),
                batch_id="smug",
                metadata={"implementation_authorization": "GO", "resolved": True},
            )
        )
        assert result.total == 0
        assert result.succeeded == 0
        assert "metadata_authorization_smuggling_denied" in result.redacted_audit["denialReasons"]

    def test_batch_audit_redacted(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(
                    _req(
                        plugin_id="fixture.redact",
                        operation="redact_payload",
                        input_payload={"secret": "sk-fake-batch-secret-12345678"},
                    ),
                    self._fault(),
                ),
                batch_id="redact-audit",
            )
        )
        blob = _blob(result.to_safe_dict())
        for secret in FAKE_SECRETS:
            assert secret not in blob
        assert "sk-fake-batch-secret-12345678" not in blob
        assert contains_secret(result.to_safe_dict()) is False

    def test_batch_no_persistent_artifacts(self, tmp_path: Path) -> None:
        run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(), self._fault()), batch_id="artifacts")
        )
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_batch_runtime_flags_frozen(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(),), batch_id="flags")
        )
        assert dict(result.runtime_flags) == RUNTIME_FLAGS_FROZEN
        assert result.redacted_audit["runtimeFlags"] == RUNTIME_FLAGS_FROZEN

    def test_batch_no_production_network_secret_route_store_flags(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(), self._count()), batch_id="boundary")
        )
        for flag in (
            "production_access",
            "external_network",
            "real_secret_read",
            "route_change",
            "runtime_store_write",
            "arbitrary_plugin_load",
            "remote_plugin_fetch",
            "marketplace_access",
        ):
            assert result.runtime_flags[flag] is False
        assert result.runtime_flags["dev_only"] is True
        assert result.runtime_flags["fixture_only"] is True

    def test_batch_does_not_resolve_p0(self) -> None:
        run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=tuple(self._echo() for _ in range(5)),
                batch_id="p0",
            )
        )
        summary = evaluate_p0_evidence()
        assert summary.resolved_count == 0
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorized is False

    def test_batch_p0_projection_unresolved(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(),), batch_id="p0proj")
        )
        assert result.p0_evidence["resolved"] is False
        assert result.p0_evidence["resolvedCount"] == 0
        assert result.p0_evidence["implementationGate"] == "NO-GO"

    def test_batch_audit_persisted_false_and_authorized(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(),), batch_id="audit")
        )
        assert result.redacted_audit["persisted"] is False
        auth = result.redacted_audit["authorizationSummary"]
        assert auth["implementationGate"] == "NO-GO"
        assert auth["phase3iGate"] is False
        assert auth["productionRuntimeGate"] == "NO-GO"

    def test_batch_oversized_fail_closed(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=tuple(self._echo() for _ in range(MAX_BATCH_REQUESTS + 1)),
                batch_id="big",
            )
        )
        assert result.total == 0
        assert "batch_oversized" in result.redacted_audit["denialReasons"]

    def test_batch_unsafe_id_fail_closed(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(),), batch_id="../../etc/passwd")
        )
        assert result.total == 0
        assert "batch_id_unsafe" in result.redacted_audit["denialReasons"]

    def test_batch_malformed_requests_fail_closed(self) -> None:
        # Non-PluginRuntimeRequest items are rejected up front.
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=("not-a-request",), batch_id="malformed")  # type: ignore[arg-type]
        )
        assert result.total == 0
        assert "batch_malformed_requests" in result.redacted_audit["denialReasons"]

    def test_batch_empty_requests_is_safe(self) -> None:
        result = run_dev_plugin_batch(PluginRuntimeBatchRequest(requests=(), batch_id="empty"))
        assert result.total == 0
        assert result.succeeded == 0
        assert result.redacted_audit["persisted"] is False

    def test_batch_result_is_frozen(self) -> None:
        result = run_dev_plugin_batch(
            PluginRuntimeBatchRequest(requests=(self._echo(),), batch_id="frozen")
        )
        with pytest.raises(TypeError):
            result.redacted_audit["persisted"] = True  # type: ignore[index]
        with pytest.raises(TypeError):
            result.runtime_flags["production_access"] = True  # type: ignore[index]

    def test_batch_result_unsafe_flags_rejected_at_construction(self) -> None:
        with pytest.raises(AssertionError):
            PluginRuntimeBatchResult(
                batch_id="x",
                total=0,
                succeeded=0,
                failed=0,
                denied=0,
                runtime_flags={**RUNTIME_FLAGS_FROZEN, "production_access": True},
            )

    def test_batch_request_defensive_copies_metadata(self) -> None:
        metadata = {"note": "benign"}
        request = PluginRuntimeBatchRequest(
            requests=(self._echo(),), batch_id="dc", metadata=metadata
        )
        metadata["implementation_authorization"] = "GO"
        result = run_dev_plugin_batch(request)
        # The post-construction mutation is not seen → batch runs (allowed).
        assert result.total == 1
        assert result.succeeded == 1


# ===========================================================================
# E. Input / output validation
# ===========================================================================


class TestInputOutputValidation:
    def test_oversized_text_rejected(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.transform",
                operation="normalize_text",
                input_payload={"text": "x" * (MAX_FIXTURE_INPUT_BYTES + 1)},
            )
        )
        assert result.allowed is False
        assert result.failed is True
        assert "fixture_input_invalid" in result.denial_reasons

    def test_oversized_dict_rejected(self) -> None:
        huge = {f"k{i}": i for i in range(MAX_FIXTURE_INPUT_BYTES)}
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.inspect",
                operation="summarize_keys",
                input_payload=huge,
            )
        )
        assert result.allowed is False
        assert result.failed is True
        assert "fixture_input_invalid" in result.denial_reasons

    def test_oversized_list_rejected(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.math",
                operation="count_items",
                input_payload={"items": list(range(MAX_FIXTURE_LIST_ITEMS + 1))},
            )
        )
        assert result.allowed is False
        assert "fixture_input_invalid" in result.denial_reasons

    def test_too_deep_nesting_rejected(self) -> None:
        # Build a nesting deeper than MAX_FIXTURE_NESTING_DEPTH.
        deep: dict[str, Any] = {"text": "x"}
        node: dict[str, Any] = deep
        for _ in range(MAX_FIXTURE_NESTING_DEPTH + 2):
            node["nested"] = {}
            node = node["nested"]
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.inspect",
                operation="summarize_keys",
                input_payload=deep,
            )
        )
        assert result.allowed is False
        assert "fixture_input_invalid" in result.denial_reasons

    def test_invalid_type_rejected(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.math",
                operation="count_items",
                input_payload={"items": "not-a-list"},
            )
        )
        assert result.allowed is False
        assert "fixture_input_invalid" in result.denial_reasons

    def test_missing_required_field_rejected(self) -> None:
        # validate_required_keys requires `required` to be a list and `payload`
        # to be a mapping; a missing payload (defaults to {}) is fine, but a
        # missing required that is the wrong type is rejected.
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.validate",
                operation="validate_required_keys",
                input_payload={"payload": {"a": 1}, "required": "not-a-list"},
            )
        )
        assert result.allowed is False
        assert "fixture_input_invalid" in result.denial_reasons

    def test_output_secret_redacted(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.redact",
                operation="redact_payload",
                input_payload={"token": "sk-fake-output-secret-12345678"},
            )
        )
        assert result.allowed is True
        blob = _blob(result.to_safe_dict())
        assert "sk-fake-output-secret-12345678" not in blob
        assert contains_secret(result.to_safe_dict()) is False

    def test_output_production_path_redacted(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.redact",
                operation="redact_payload",
                input_payload={"path": "/Users/someone/.hermes/memory/foo"},
            )
        )
        assert result.allowed is True
        blob = _blob(result.to_safe_dict())
        assert "/Users/someone/.hermes" not in blob
        assert contains_secret(result.to_safe_dict()) is False

    def test_failure_error_redacted(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1})
        )
        assert result.failed is True
        blob = _blob(result.to_safe_dict())
        for secret in FAKE_SECRETS:
            assert secret not in blob
        assert contains_secret(result.to_safe_dict()) is False

    def test_output_non_json_safe_denied(self, monkeypatch) -> None:
        # A fixture whose invoker returns a callable must be rejected by the
        # runtime's output validator. Monkeypatch the allowlist lookup to return
        # such an operation (the hardcoded registry never holds one).
        from hermes_cli import dev_web_plugin_runtime as rt

        bad_op = FixtureOperation(
            plugin_id="fixture.echo",
            operation="echo_uppercase",
            description="bad-output twin",
            invoker=lambda payload: {"bad": lambda: 1},
        )
        monkeypatch.setattr(rt, "lookup_fixture", lambda pid, op: bad_op)
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "x"})
        )
        assert result.allowed is False
        assert result.failed is True
        assert "fixture_output_unsafe" in result.denial_reasons

    def test_assert_fixture_output_rejects_non_native(self) -> None:
        from hermes_cli.dev_web_plugin_runtime import _assert_fixture_output

        with pytest.raises(FixtureOutputError):
            _assert_fixture_output({"ok": 1, "bad": object()})


# ===========================================================================
# F. Security boundary (no dynamic loading / network / shell / secrets)
# ===========================================================================


class TestSecurityBoundary:
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

    def test_no_arbitrary_plugin_directory_loading(self) -> None:
        # The runtime exposes no loader / scanner / directory-walk surface.
        src = self._src("hermes_cli.dev_web_plugin_runtime")
        for token in ("import_module", "walk(", "scandir", "glob(", "listdir", "load_module"):
            assert token not in src, f"runtime references loader surface {token!r}"

    def test_no_marketplace_or_remote_registry_surface(self) -> None:
        src = self._src("hermes_cli.dev_web_plugin_runtime")
        # The words may appear in denial reason strings; an actual fetch surface
        # (a function that contacts a host) must not.
        assert "def fetch_" not in src
        assert "def install_" not in src
        assert "def load_plugin" not in src

    def test_importing_runtime_does_not_stat_production_home(self, monkeypatch) -> None:
        # Behavioral proof: running the runtime (single + batch) over a request
        # that names a forbidden path never escalates to a real stat / lstat of a
        # production path. The source-boundary scan above already proves there is
        # no ``os.stat`` / ``.stat(`` / ``expanduser(`` call surface in the source,
        # so no module reload is needed here (a reload would rebind the fixture
        # module's classes in place and poison other tests' class references).
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

        run_dev_plugin(
            _req(
                plugin_id="fixture.redact",
                operation="redact_payload",
                input_payload={"path": "/Users/x/.hermes/state.db"},
            )
        )
        run_dev_plugin(
            _req(
                plugin_id="fixture.echo",
                operation="echo_uppercase",
                requested_filesystem_paths=("~/.hermes",),
            )
        )
        run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(
                    _req(
                        plugin_id="fixture.echo",
                        operation="echo_uppercase",
                        input_payload={"text": "a"},
                    ),
                ),
                batch_id="stat-probe",
            )
        )

        assert accesses == [], f"runtime stat()'d a production path: {accesses}"

    def test_no_runtime_artifacts_created_batch(self, tmp_path: Path) -> None:
        run_dev_plugin(
            _req(plugin_id="fixture.transform", operation="normalize_text", input_payload={"text": "  x  "})
        )
        run_dev_plugin_batch(
            PluginRuntimeBatchRequest(
                requests=(
                    _req(plugin_id="fixture.math", operation="count_items", input_payload={"items": [1]}),
                    _req(plugin_id="fixture.fault", operation="deliberate_failure", input_payload={"x": 1}),
                ),
                batch_id="no-artifacts",
            )
        )
        assert find_runtime_store_artifacts(tmp_path) == []


# ===========================================================================
# G. dev_web_api isolation + route governance
# ===========================================================================


class TestDevWebApiIsolation:
    def test_runtime_not_imported_by_dev_web_api(self) -> None:
        import importlib

        src = Path(importlib.import_module("hermes_cli.dev_web_api").__file__).read_text(encoding="utf-8")
        assert "dev_web_plugin_runtime" not in src
        assert "dev_web_fixture_plugins" not in src
        assert "run_dev_plugin" not in src
        assert "run_dev_plugin_batch" not in src

    @pytest.mark.parametrize(
        "path",
        (
            "/api/dev/v1/plugins/runtime/batch",
            "/api/dev/v1/plugin-runtime/batch",
            "/api/dev/v1/plugins/execute-batch",
            "/api/dev/v1/fixtures/transform",
            "/api/dev/v1/fixtures/validate",
        ),
    )
    def test_batch_and_fixture_probes_yield_no_route(self, client: TestClient, path: str) -> None:
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
# H. Runtime expansion proof scenarios (separate fixed dev-only library)
# ===========================================================================


class TestRuntimeExpansionScenarios:
    def test_expansion_scenarios_count(self) -> None:
        assert len(RUNTIME_EXPANSION_PROOF_SCENARIOS) == 4
        assert len(get_runtime_expansion_proof_scenarios()) == 4

    def test_expansion_scenarios_disjoint_from_other_libraries(self) -> None:
        expansion_ids = {s.scenario_id for s in RUNTIME_EXPANSION_PROOF_SCENARIOS}
        fixed_ids = {s.scenario_id for s in FIXED_SCENARIOS}
        runtime_ids = {s.scenario_id for s in RUNTIME_PROOF_SCENARIOS}
        assert expansion_ids.isdisjoint(fixed_ids)
        assert expansion_ids.isdisjoint(runtime_ids)
        # The frozen libraries are unchanged.
        assert len(FIXED_SCENARIOS) == 22
        assert len(RUNTIME_PROOF_SCENARIOS) == 5

    @pytest.mark.parametrize("scenario", RUNTIME_EXPANSION_PROOF_SCENARIOS)
    def test_each_expansion_scenario_meets_expectations(self, scenario) -> None:
        result = run_proof_scenarios([scenario])
        assert result.passed_scenarios == 1
        assert result.failed_scenarios == 0

    def test_expansion_scenario_aggregate_locked(self) -> None:
        summary = run_proof_scenarios(list(get_runtime_expansion_proof_scenarios()))
        assert summary.passed_scenarios == 4
        assert summary.failed_scenarios == 0
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_expansion_scenarios_carry_no_secret(self) -> None:
        summary = run_proof_scenarios(list(get_runtime_expansion_proof_scenarios()))
        assert contains_secret(summary.to_safe_dict()) is False

    def test_scenario_pass_does_not_authorize(self) -> None:
        # Running fixtures + every expansion scenario still leaves every
        # authorization flag frozen.
        run_dev_plugin(_req(plugin_id="fixture.transform", operation="normalize_text",
                             input_payload={"text": "x"}))
        run_proof_scenarios(list(get_runtime_expansion_proof_scenarios()))
        summary = evaluate_p0_evidence()
        assert summary.resolved_count == 0
        assert summary.implementation_authorization == "NO-GO"


# ===========================================================================
# I. Authorization + audit + reason-token inventory
# ===========================================================================


class TestAuthorizationAndAudit:
    def test_assert_no_side_effect_surface(self) -> None:
        assert_no_side_effect_surface()

    def test_frozen_authorization_constants(self) -> None:
        assert IMPLEMENTATION_AUTHORIZATION == "NO-GO"
        assert PHASE_3I_AUTHORIZED is False
        assert REAL_RUNTIME == "NO-GO"
        assert NEW_ROUTE == "NO-GO"
        assert PRODUCTION_ROLLOUT == "NO-GO"

    def test_audit_carries_authorization_summary(self) -> None:
        result = run_dev_plugin(
            _req(plugin_id="fixture.echo", operation="echo_uppercase", input_payload={"text": "hi"})
        )
        auth = result.redacted_audit["authorizationSummary"]
        assert auth["implementationGate"] == "NO-GO"
        assert auth["phase3iGate"] is False
        assert auth["productionRuntimeGate"] == "NO-GO"
        assert auth["newRouteGate"] == "NO-GO"
        assert auth["productionRolloutGate"] == "NO-GO"
        assert auth["resolved"] is False
        assert result.redacted_audit["persisted"] is False
        assert contains_secret(result.redacted_audit) is False

    def test_audit_source_stable(self) -> None:
        assert PLUGIN_RUNTIME_AUDIT_SOURCE == "dev_web_plugin_runtime"

    def test_new_reason_tokens_are_in_inventory(self) -> None:
        for reason in (
            "fixture_metadata_unsafe",
            "fixture_metadata_missing",
            "fixture_output_unsafe",
            "capability_mismatch_denied",
            "batch_oversized",
            "batch_id_unsafe",
            "batch_malformed_requests",
            "batch_metadata_smuggling_denied",
        ):
            assert reason in RUNTIME_REASONS

    def test_metadata_validation_wired_into_binding(self) -> None:
        # The runtime binds only fixtures whose metadata re-validates safe.
        for plugin_id, operation in (
            ("fixture.transform", "normalize_text"),
            ("fixture.validate", "validate_required_keys"),
            ("fixture.math", "count_items"),
            ("fixture.redact", "redact_payload"),
        ):
            binding = resolve_runtime_binding(_req(plugin_id=plugin_id, operation=operation))
            assert binding.resolved is True

    def test_redact_fixture_output_is_json_safe(self) -> None:
        result = run_dev_plugin(
            _req(
                plugin_id="fixture.redact",
                operation="redact_payload",
                input_payload={"a": {"b": [1, 2, {"c": "sk-fake-12345678"}]}},
            )
        )
        assert result.allowed is True
        # The output is a JSON-native dict (no callable / module / object).
        import json

        json.dumps(result.to_safe_dict())
        assert contains_secret(result.to_safe_dict()) is False
