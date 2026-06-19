"""Phase 3H Dev-only Sandbox Proof Skeleton tests (Block 2).

Comprehensive coverage for the four dev-only sandbox-proof modules
(:mod:`dev_web_sandbox_guards`, :mod:`dev_web_sandbox_policy`,
:mod:`dev_web_sandbox_audit`, :mod:`dev_web_sandbox_proof`):

  - descriptor-only baseline + executable-surface denial;
  - capability default-deny (unknown, every dangerous label, allowed labels
    grant no real execution);
  - filesystem / network / secret guards (traversal, symlink escape,
    ``~/.hermes``, production db, write outside root, every network intent,
    every secret request, redaction with no false positives);
  - kill-switch fail-closed (active denies; inactive grants nothing);
  - in-memory redacted audit record (no raw secret / production path, all
    evidence flags False);
  - failure modes (malformed / oversized / redaction failure);
  - no persistent artifacts after evaluation;
  - source-level boundary: no dynamic loading, no network, no new route.

This is a **skeleton** test: it never executes a plugin, never loads a plugin,
never dynamic-imports, never performs a network call, never reads a real
secret, never touches ``~/.hermes``, and never starts a gateway / dashboard.

Phase: 3H — Dev-only Sandbox Proof Skeleton
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

from hermes_cli import (
    dev_web_sandbox_audit as audit_mod,
    dev_web_sandbox_guards as guards_mod,
    dev_web_sandbox_policy as policy_mod,
    dev_web_sandbox_proof as proof_mod,
)
from hermes_cli.dev_web_sandbox_audit import build_sandbox_audit_record, is_audit_record_safe
from hermes_cli.dev_web_sandbox_guards import (
    contains_secret,
    detect_secret_in_string,
    evaluate_filesystem_path,
    evaluate_network_target,
    evaluate_secret_request,
    redact_sandbox_payload,
    redact_sandbox_text,
)
from hermes_cli.dev_web_sandbox_policy import (
    CAPABILITY_DEFAULT_ALLOWED,
    CAPABILITY_LABELS,
    CapabilityEvaluationContext,
    DANGEROUS_CAPABILITIES,
    evaluate_capability,
    evaluate_descriptor,
    evaluate_kill_switch,
)
from hermes_cli.dev_web_sandbox_proof import (
    FilesystemRequest,
    MAX_REQUEST_ITEMS_PER_CATEGORY,
    SandboxProofRequest,
    evaluate_sandbox_proof,
    is_sandbox_proof_result_safe,
)


# ---------------------------------------------------------------------------
# Descriptor-only baseline
# ---------------------------------------------------------------------------


class TestDescriptorOnly:
    def test_clean_descriptor_allowed_descriptor_only(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.descriptor.x", "status": "visible"})
        assert decision.allowed is True
        assert decision.descriptor_only is True

    def test_descriptor_with_python_import_denied(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x", "pythonImportPath": "malicious.mod"})
        assert decision.allowed is False
        assert "descriptor_carries_execution_surface" in decision.reasons

    @pytest.mark.parametrize(
        "field",
        [
            "pythonImportPath",
            "callable",
            "shellCommand",
            "externalUrl",
            "downloadUrl",
            "pluginPackage",
            "dynamicModule",
            "installCommand",
            "apiKey",
            "Authorization",
            "secret",
            "localPath",
        ],
    )
    def test_descriptor_forbidden_field_denied(self, field: str) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x", field: "evil"})
        assert decision.allowed is False

    def test_nested_forbidden_field_denied(self) -> None:
        decision = evaluate_descriptor(
            {"pluginId": "plugin.x", "metadataSchema": {"shellCommand": "rm -rf"}}
        )
        assert decision.allowed is False

    def test_malformed_descriptor_denied(self) -> None:
        assert evaluate_descriptor("not a dict").allowed is False  # type: ignore[arg-type]
        assert evaluate_descriptor({"status": "visible"}).allowed is False  # no id

    def test_oversized_descriptor_denied(self) -> None:
        big = {"pluginId": "plugin.x", "note": "A" * 40_000}
        assert evaluate_descriptor(big).allowed is False

    def test_descriptor_id_redacted_in_decision(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x.y", "status": "visible"})
        blob = json.dumps(decision.to_safe_dict())
        # Only the safe id characters survive; no path / secret smuggled.
        assert "/Users" not in blob
        assert "state.db" not in blob


# ---------------------------------------------------------------------------
# Capability default-deny
# ---------------------------------------------------------------------------


class TestCapabilityDeny:
    def test_unknown_capability_denied(self) -> None:
        assert evaluate_capability("nonsense.cap").allowed is False
        assert evaluate_capability(123).allowed is False  # type: ignore[arg-type]

    def test_all_fourteen_labels_known(self) -> None:
        assert len(CAPABILITY_LABELS) == 14

    def test_default_allowed_labels(self) -> None:
        assert CAPABILITY_DEFAULT_ALLOWED == {
            "descriptor.read",
            "sandbox.proof.evaluate",
            "audit.redact",
        }
        for cap in CAPABILITY_DEFAULT_ALLOWED:
            decision = evaluate_capability(cap)
            assert decision.allowed is True
            assert decision.note == "proof_label_only_no_real_execution"

    def test_filesystem_read_default_denied_temp_allowed(self) -> None:
        assert evaluate_capability("filesystem.read").allowed is False
        ctx = CapabilityEvaluationContext(allow_temp_filesystem_read=True)
        assert evaluate_capability("filesystem.read", context=ctx).allowed is True

    @pytest.mark.parametrize("cap", sorted(DANGEROUS_CAPABILITIES))
    def test_dangerous_capability_denied(self, cap: str) -> None:
        decision = evaluate_capability(cap)
        assert decision.allowed is False
        assert decision.reasons  # a specific reason

    def test_allowed_label_does_not_grant_execution(self) -> None:
        # Granting descriptor.read must NOT allow plugin.execute.
        assert evaluate_capability("descriptor.read").allowed is True
        assert evaluate_capability("plugin.execute").allowed is False


# ---------------------------------------------------------------------------
# Filesystem guard
# ---------------------------------------------------------------------------


class TestFilesystemGuard:
    def test_allowed_temp_read_passes(self, tmp_path: Path) -> None:
        decision = evaluate_filesystem_path(str(tmp_path / "a.json"), allowed_roots=[str(tmp_path)])
        assert decision.allowed is True
        assert decision.inside_allowed_root is True

    def test_traversal_denied(self, tmp_path: Path) -> None:
        candidate = str(tmp_path / ".." / "escape.json")
        decision = evaluate_filesystem_path(candidate, allowed_roots=[str(tmp_path)])
        assert decision.allowed is False

    def test_symlink_escape_denied(self, tmp_path: Path) -> None:
        link = tmp_path / "escape"
        os.symlink("/etc", link)
        decision = evaluate_filesystem_path(str(link), allowed_roots=[str(tmp_path)])
        assert decision.allowed is False
        assert "symlink_escape" in decision.reasons

    def test_hermes_home_denied(self) -> None:
        decision = evaluate_filesystem_path("/Users/huangruibang/.hermes", allowed_roots=[])
        assert decision.allowed is False
        assert "forbidden_production_home" in decision.reasons

    def test_production_state_db_denied(self) -> None:
        decision = evaluate_filesystem_path("/Users/huangruibang/.hermes/state.db", allowed_roots=[])
        assert decision.allowed is False

    def test_home_fallback_denied(self) -> None:
        home = os.path.expanduser("~")
        decision = evaluate_filesystem_path(home, allowed_roots=[])
        assert decision.allowed is False
        assert "home_directory_fallback" in decision.reasons

    def test_write_outside_root_denied(self, tmp_path: Path) -> None:
        decision = evaluate_filesystem_path("/etc/x.json", allowed_roots=[str(tmp_path)], allow_write=True)
        assert decision.allowed is False

    def test_write_inside_root_allowed(self, tmp_path: Path) -> None:
        decision = evaluate_filesystem_path(
            str(tmp_path / "out.json"), allowed_roots=[str(tmp_path)], allow_write=True
        )
        assert decision.allowed is True

    def test_decision_value_free(self) -> None:
        decision = evaluate_filesystem_path("/Users/huangruibang/.hermes/state.db", allowed_roots=[])
        blob = json.dumps(decision.to_safe_dict())
        assert "/Users/huangruibang/.hermes" not in blob


# ---------------------------------------------------------------------------
# Network guard
# ---------------------------------------------------------------------------


class TestNetworkGuard:
    def test_empty_noop_when_no_capability(self) -> None:
        decision = evaluate_network_target("")
        assert decision.allowed is True

    @pytest.mark.parametrize(
        "target",
        [
            "https://example.com",
            "https://api.openai.com/v1/chat",
            "https://registry.npmjs.org/pkg",
            "https://marketplace.example.com/install",
            "https://telemetry.example.com/callback",
            "https://example.io/download",
        ],
    )
    def test_external_target_denied(self, target: str) -> None:
        decision = evaluate_network_target(target, capability_requested=True)
        assert decision.allowed is False
        assert "network_request_capability_denied" in decision.reasons

    def test_capability_request_alone_denied(self) -> None:
        decision = evaluate_network_target("", capability_requested=True)
        assert decision.allowed is False
        assert "network_request_capability_denied" in decision.reasons

    def test_decision_value_free(self) -> None:
        decision = evaluate_network_target("https://api.openai.com/v1", capability_requested=True)
        blob = json.dumps(decision.to_safe_dict())
        assert "api.openai.com" not in blob


# ---------------------------------------------------------------------------
# Secret guard + redaction
# ---------------------------------------------------------------------------


class TestSecretGuard:
    @pytest.mark.parametrize("name", ["OPENAI_API_KEY", "api_key", "Authorization", "Bearer", "private_key"])
    def test_secret_request_denied(self, name: str) -> None:
        decision = evaluate_secret_request(name)
        assert decision.allowed is False
        assert "secret_request_denied" in decision.reasons
        assert decision.to_safe_dict()["keyValue"] == "never"

    @pytest.mark.parametrize(
        "value",
        [
            "key=sk-abcd1234efgh5678",
            "ghp_AbCdEfGh1234567890",
            "xoxb-1234567890-abcdefXYZ",
            "Authorization: Bearer abc.def.ghi",
            "Bearer sometoken",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIE",
            "/Users/huangruibang/.hermes/state.db",
        ],
    )
    def test_secret_redacted(self, value: str) -> None:
        assert redact_sandbox_text(value) == "[REDACTED]"
        detected, _ = detect_secret_in_string(value)
        assert detected is True

    def test_safe_text_not_redacted(self) -> None:
        assert redact_sandbox_text("just a normal sentence") == "just a normal sentence"
        assert redact_sandbox_text("maxTokens=1024") == "maxTokens=1024"

    def test_payload_redaction_preserves_counts(self) -> None:
        out = redact_sandbox_payload(
            {"api_key": "sk-abcd1234efgh5678", "maxTokens": 100, "msg": "hi", "nested": {"token": "leak"}}
        )
        assert out["api_key"] == "[REDACTED]"
        assert out["maxTokens"] == 100  # count preserved
        assert out["msg"] == "hi"
        assert out["nested"]["token"] == "[REDACTED]"

    def test_contains_secret_no_false_positive_on_counts(self) -> None:
        assert contains_secret({"maxTokens": 100, "totalTokens": 2048}) is False


# ---------------------------------------------------------------------------
# Kill-switch
# ---------------------------------------------------------------------------


class TestKillSwitch:
    def test_active_fail_closed(self) -> None:
        decision = evaluate_kill_switch(True)
        assert decision.active is True
        assert decision.fail_closed is True

    def test_inactive_does_not_grant(self) -> None:
        decision = evaluate_kill_switch(False)
        assert decision.active is False
        assert decision.fail_closed is False
        # An inactive switch still denies every dangerous capability.
        assert evaluate_capability("plugin.execute").allowed is False

    def test_kill_switch_event_in_audit(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied", reasons=["kill_switch_active"], kill_switch_active=True
        )
        assert record["killSwitchActive"] is True
        assert record["decision"] == "denied"


# ---------------------------------------------------------------------------
# In-memory audit record
# ---------------------------------------------------------------------------


class TestAuditRecord:
    def test_contains_denial_reasons(self) -> None:
        record = build_sandbox_audit_record(decision="denied", reasons=["network_request_denied"])
        assert record["decision"] == "denied"
        assert "network_request_denied" in record["reasons"]

    def test_no_raw_secret(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["secret_request_denied"],
            safe_metadata={"api_key": "sk-abcd1234efgh5678"},
        )
        blob = json.dumps(record)
        assert "sk-abcd1234efgh5678" not in blob
        assert "[REDACTED]" in blob

    def test_no_raw_production_path(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["forbidden_production_database"],
            descriptor_id="plugin.x",
        )
        blob = json.dumps(record)
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob

    def test_evidence_flags_all_false(self) -> None:
        record = build_sandbox_audit_record(decision="allowed")
        for flag in (
            "routeChangeRequired",
            "productionAccessRequired",
            "externalNetworkRequired",
            "realSecretRequired",
            "runtimeExecutionRequired",
        ):
            assert record["evidence"][flag] is False

    def test_in_memory_only(self) -> None:
        record = build_sandbox_audit_record(decision="denied")
        assert record["persisted"] is False

    def test_is_audit_record_safe(self) -> None:
        record = build_sandbox_audit_record(decision="allowed")
        assert is_audit_record_safe(record) is True

    def test_decision_coerced_to_denied(self) -> None:
        # Any non-"allowed" decision string fails closed to "denied".
        assert build_sandbox_audit_record(decision="maybe")["decision"] == "denied"

    def test_redaction_failure_fails_closed(self) -> None:
        # A raw secret smuggled into the (un-redacted) reasons list bypasses
        # the metadata redactor but is caught by the final defensive sweep.
        # The record collapses to the fail-closed denial.
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["secret_request_denied", "leak sk-abcd1234efgh5678 here"],
        )
        blob = json.dumps(record)
        assert "sk-abcd1234efgh5678" not in blob
        assert record.get("redactionFailed") is True
        assert record["decision"] == "denied"
        assert record["reasons"] == ["redaction_failed_fail_closed"]


# ---------------------------------------------------------------------------
# Orchestrator (failure modes + invariants)
# ---------------------------------------------------------------------------


def _clean_request(**overrides) -> SandboxProofRequest:
    base = dict(
        descriptor_id="plugin.descriptor.registry_status",
        descriptor_metadata={"pluginId": "plugin.descriptor.registry_status", "status": "visible"},
        mock_operation="proof.evaluate",
        requested_capabilities=("descriptor.read", "sandbox.proof.evaluate"),
    )
    base.update(overrides)
    return SandboxProofRequest(**base)


class TestSandboxProofOrchestrator:
    def test_clean_proof_allowed(self) -> None:
        result = evaluate_sandbox_proof(_clean_request())
        assert result.allowed is True
        assert result.denial_reasons == ()
        assert is_sandbox_proof_result_safe(result) is True

    def test_kill_switch_active_denied(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(kill_switch_active=True))
        assert result.allowed is False
        assert "kill_switch_active" in result.denial_reasons

    @pytest.mark.parametrize(
        "cap",
        [
            "plugin.execute",
            "plugin.load",
            "process.spawn",
            "filesystem.write",
            "network.request",
            "secrets.read",
            "provider.request",
            "database.write",
            "routes.modify",
            "production.access",
        ],
    )
    def test_dangerous_capability_denied(self, cap: str) -> None:
        result = evaluate_sandbox_proof(_clean_request(requested_capabilities=(cap,)))
        assert result.allowed is False
        assert is_sandbox_proof_result_safe(result) is True

    def test_executable_descriptor_denied(self) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(descriptor_metadata={"pluginId": "plugin.x", "shellCommand": "rm -rf"})
        )
        assert result.allowed is False
        assert "descriptor_carries_execution_surface" in result.denial_reasons

    def test_malformed_descriptor_denied(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(descriptor_metadata="not a dict"))  # type: ignore[arg-type]
        assert result.allowed is False

    def test_network_target_denied(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(requested_network_targets=("https://api.openai.com",)))
        assert result.allowed is False

    def test_secret_request_denied(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(requested_secret_names=("OPENAI_API_KEY",)))
        assert result.allowed is False

    def test_production_path_denied(self) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(
                requested_filesystem_paths=(FilesystemRequest(path="/Users/huangruibang/.hermes/state.db"),),
            )
        )
        assert result.allowed is False

    def test_temp_root_read_allowed(self, tmp_path: Path) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(
                requested_filesystem_paths=(FilesystemRequest(path=str(tmp_path / "a.json")),),
                allowed_roots=(str(tmp_path),),
            )
        )
        assert result.allowed is True

    def test_oversized_input_denied(self) -> None:
        too_many = tuple(f"plugin.execute{i}" for i in range(MAX_REQUEST_ITEMS_PER_CATEGORY + 1))
        result = evaluate_sandbox_proof(_clean_request(requested_capabilities=too_many))
        assert result.allowed is False
        assert any("oversized_input" in r for r in result.denial_reasons)

    def test_evidence_flags_all_false_on_allowed(self) -> None:
        result = evaluate_sandbox_proof(_clean_request())
        assert result.route_change_required is False
        assert result.production_access_required is False
        assert result.external_network_required is False
        assert result.real_secret_required is False
        assert result.runtime_execution_required is False

    def test_denied_audit_still_generated(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(requested_capabilities=("plugin.execute",)))
        assert result.audit_record["decision"] == "denied"
        assert is_audit_record_safe(result.audit_record) is True

    def test_result_blob_value_free(self) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(
                requested_filesystem_paths=(FilesystemRequest(path="/Users/huangruibang/.hermes/state.db"),),
                requested_secret_names=("OPENAI_API_KEY",),
            )
        )
        blob = json.dumps(result.to_safe_dict())
        assert "/Users/huangruibang/.hermes" not in blob
        assert "OPENAI_API_KEY" not in blob


# ---------------------------------------------------------------------------
# No persistent artifacts
# ---------------------------------------------------------------------------


class TestNoPersistentArtifacts:
    def test_proof_creates_no_runtime_files(self, tmp_path: Path, monkeypatch) -> None:
        # Run several proofs with cwd inside a temp tree; afterward the tree
        # must contain no runtime-store artifacts.
        monkeypatch.chdir(tmp_path)
        for req in (
            _clean_request(),
            _clean_request(kill_switch_active=True),
            _clean_request(requested_capabilities=("plugin.execute",)),
        ):
            evaluate_sandbox_proof(req)
        from hermes_cli.dev_web_safety_baseline import find_runtime_store_artifacts

        assert find_runtime_store_artifacts(tmp_path) == []

    def test_proof_does_not_open_hermes_home(self) -> None:
        # Evaluate a proof that references the production path as a *denial
        # target*; the proof must deny without opening it.
        result = evaluate_sandbox_proof(
            _clean_request(
                requested_filesystem_paths=(FilesystemRequest(path="/Users/huangruibang/.hermes/state.db"),),
            )
        )
        assert result.allowed is False


# ---------------------------------------------------------------------------
# Source-level boundary
# ---------------------------------------------------------------------------


_FORBIDDEN_SOURCE_TOKENS = (
    "importlib.import_module",
    "__import__(",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.run",
    "shell=True",
    "import requests",
    "import httpx",
    "import aiohttp",
    "socket.socket",
    "urlopen(",
)


@pytest.mark.parametrize("module", [guards_mod, policy_mod, audit_mod, proof_mod])
def test_module_source_has_no_dynamic_loading_or_network(module) -> None:
    src = Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert token not in src, f"{module.__name__}: forbidden token {token!r}"


def test_proof_module_not_imported_by_api() -> None:
    # The orchestrator must NOT be wired into the FastAPI app (no new route).
    from hermes_cli import dev_web_api

    api_src = Path(inspect.getsourcefile(dev_web_api)).read_text(encoding="utf-8")
    assert "dev_web_sandbox_proof" not in api_src
    assert "dev_web_safety_baseline" not in api_src
    assert "dev_web_sandbox_guards" not in api_src
    assert "dev_web_sandbox_policy" not in api_src
    assert "dev_web_sandbox_audit" not in api_src


def test_route_governance_unchanged_with_sandbox_modules(tmp_path: Path) -> None:
    # Importing the sandbox modules must not change the app's route count.
    from fastapi.testclient import TestClient

    from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
    from hermes_cli.dev_web_safety_baseline import assert_route_governance_unchanged

    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    app = create_dev_web_api_app(cfg)
    assert_route_governance_unchanged(app)
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    assert len([p for p in spec["paths"] if p.startswith("/api/dev/v1/")]) == 34
