"""Phase 3E–3H P0 Evidence Consolidation & Hardening tests.

A second pass over the dev-only safety baseline + sandbox proof skeleton. The
Phase 3E–3H recovery landed five modules + 144 tests; this file consolidates
their **P0 evidence** and adds a round of **boundary / edge-case hardening**
coverage:

  - **P0 evidence matrix** — the matrix doc exists, names every code/test
    artifact, and preserves every NO-GO (implementation authorization, real
    plugin runtime, Phase 3I, new route, production rollout).
  - **Request / result immutability** — caller mutation of inputs / returned
    dicts cannot pollute the proof result or its audit record.
  - **Descriptor validation** — id traversal / path-separator / shell / wildcard
    tokens are denied (``descriptor_id_unsafe``), not merely redacted.
  - **Capability normalization** — every injection-shaped / unknown / wildcard
    capability is denied; normalization cannot elevate a dangerous capability.
  - **Filesystem guard** — relative escape, nested / mixed-separator
    traversal, dot segments, case-variant production path, runtime-store names.
  - **Network guard** — https / loopback / IPv6 / file:// / ftp:// / ws:// /
    wss:// / registry / marketplace / provider endpoint / mixed-case scheme.
  - **Secrets / redaction** — ``sk-`` / ``ghp_`` / ``xox`` / Bearer / PEM /
    ``.env``-style ``API_KEY=`` / ``OPENAI_API_KEY=`` / production paths,
    redacted in audit reasons, metadata, and error detail.
  - **Kill switch** — active denies a clean descriptor-only proof; cannot be
    overridden by request metadata; invalid (non-bool) state fails closed;
    never signals a process.
  - **Audit** — in-memory only; redacts reasons / metadata / exceptions;
    carries every frozen "did-not-happen" evidence flag; fails closed on a
    redaction slip.
  - **Source boundary** — no dynamic loading, no network, no shell, no process
    signaling across the five modules (the baseline's single read-only ``git``
    subprocess remains allowed and confined).
  - **Dev-Web API isolation** — no ``dev_web_*.py`` module imports the sandbox
    proof skeleton; route governance stays ``34/34/5/0/1/1``.
  - **No persistent runtime artifacts** — evaluating proofs creates none.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never signals the production gateway, never starts a gateway /
dashboard, never performs a network call, never reads a real secret, and
introduces no new route. Every secret value used here is an obvious fake.

Phase: 3E–3H — P0 Evidence Consolidation & Hardening
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import (
    dev_web_safety_baseline as baseline_mod,
    dev_web_sandbox_audit as audit_mod,
    dev_web_sandbox_guards as guards_mod,
    dev_web_sandbox_policy as policy_mod,
    dev_web_sandbox_proof as proof_mod,
)
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_safety_baseline import (
    PRODUCTION_HERMES_HOME,
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    evaluate_path_safety,
    find_runtime_store_artifacts,
    route_governance_counts,
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
    CAPABILITY_LABELS,
    CAPABILITY_REASONS,
    DESCRIPTOR_REASONS,
    DANGEROUS_CAPABILITIES,
    CapabilityEvaluationContext,
    evaluate_capability,
    evaluate_descriptor,
    evaluate_kill_switch,
)
from hermes_cli.dev_web_sandbox_proof import (
    FilesystemRequest,
    SandboxProofRequest,
    evaluate_sandbox_proof,
    is_sandbox_proof_result_safe,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_DOC = REPO_ROOT / "docs" / "webui" / "phase-3e-h-p0-evidence-matrix.md"

# Obvious fakes — never a real credential. The shapes mirror real secret
# formats so the redactor is exercised realistically.
FAKE_SK = "sk-abcd1234efgh5678"
FAKE_GHP = "ghp_AbCdEfGh1234567890"
FAKE_XOX = "xoxb-1234567890-abcdefXYZ"
FAKE_BEARER = "Authorization: Bearer abc.def.ghi"
FAKE_PEM = "-----BEGIN RSA PRIVATE KEY-----\nMIIEfakekeymaterial\n-----END RSA PRIVATE KEY-----"


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


def _clean_request(**overrides) -> SandboxProofRequest:
    base = dict(
        descriptor_id="plugin.descriptor.registry_status",
        descriptor_metadata={"pluginId": "plugin.descriptor.registry_status", "status": "visible"},
        mock_operation="proof.evaluate",
        requested_capabilities=("descriptor.read", "sandbox.proof.evaluate"),
    )
    base.update(overrides)
    return SandboxProofRequest(**base)


def _src(module) -> str:
    return Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")


# ===========================================================================
# 1. P0 evidence matrix
# ===========================================================================


class TestP0EvidenceMatrix:
    def test_matrix_doc_exists(self) -> None:
        assert MATRIX_DOC.is_file(), f"missing evidence matrix: {MATRIX_DOC}"

    def test_matrix_doc_references_code_artifacts(self) -> None:
        text = MATRIX_DOC.read_text(encoding="utf-8")
        for module in (
            "dev_web_safety_baseline.py",
            "dev_web_sandbox_guards.py",
            "dev_web_sandbox_policy.py",
            "dev_web_sandbox_audit.py",
            "dev_web_sandbox_proof.py",
        ):
            assert module in text, f"matrix does not reference code module {module}"
        # References the test surface too.
        assert "test_dev_web_phase_3e_h_safety_baseline" in text
        assert "test_dev_web_phase_3h_sandbox_proof_skeleton" in text

    def test_matrix_lists_all_24_p0_gates(self) -> None:
        text = MATRIX_DOC.read_text(encoding="utf-8")
        for i in range(1, 25):
            assert f"P0-{i:02d}" in text, f"matrix missing P0-{i:02d}"

    def test_matrix_does_not_authorize_implementation(self) -> None:
        text = MATRIX_DOC.read_text(encoding="utf-8")
        # Implementation Authorization must remain NO-GO.
        assert "Implementation Authorization" in text
        assert "NO-GO" in text
        # No phrase claims implementation was authorized / approved / a GO.
        for forbidden in (
            "Implementation Authorization: GO",
            "Implementation Authorization = GO",
            "implementation authorized",
            "implementation is authorized",
        ):
            assert forbidden.lower() not in text.lower(), forbidden

    def test_matrix_does_not_authorize_phase_3i(self) -> None:
        text = MATRIX_DOC.read_text(encoding="utf-8")
        assert "Phase 3I" in text or "Phase 3I".lower() in text.lower()
        assert "not authorized" in text.lower()
        for forbidden in (
            "phase 3i authorized",
            "phase 3i is authorized",
            "phase 3i: go",
        ):
            assert forbidden.lower() not in text.lower(), forbidden

    def test_matrix_preserves_real_runtime_and_production_no_go(self) -> None:
        text = MATRIX_DOC.read_text(encoding="utf-8")
        for theme in (
            "Real plugin runtime",
            "Production rollout",
            "New route",
        ):
            assert theme in text, theme
        # No claim that a real runtime / production rollout proceeded.
        for forbidden in (
            "real plugin runtime: go",
            "production rollout: go",
            "new route: go",
        ):
            assert forbidden.lower() not in text.lower(), forbidden


# ===========================================================================
# 2. Request / result immutability
# ===========================================================================


class TestImmutability:
    def test_request_snapshots_descriptor_metadata(self) -> None:
        meta = {"pluginId": "plugin.x", "status": "visible"}
        request = SandboxProofRequest(descriptor_id="plugin.x", descriptor_metadata=meta)
        # Mutate the caller's dict after construction.
        meta["shellCommand"] = "rm -rf"
        assert request.descriptor_metadata is not meta
        assert "shellCommand" not in (request.descriptor_metadata or {})

    def test_request_snapshots_safe_metadata(self) -> None:
        safe = {"note": "alpha"}
        request = SandboxProofRequest(descriptor_id="plugin.x", safe_metadata=safe)
        safe["note"] = "changed"
        safe["extra"] = "leaked"
        assert request.safe_metadata is not safe
        assert request.safe_metadata == {"note": "alpha"}

    def test_request_nested_mutation_isolated(self) -> None:
        meta = {"pluginId": "plugin.x", "nested": {"keep": 1}}
        request = SandboxProofRequest(descriptor_id="plugin.x", descriptor_metadata=meta)
        meta["nested"]["keep"] = 999  # deep mutation of caller dict
        assert request.descriptor_metadata["nested"]["keep"] == 1

    def test_to_safe_dict_copy_does_not_pollute_result(self) -> None:
        result = evaluate_sandbox_proof(_clean_request())
        snapshot = result.to_safe_dict()
        snapshot["audit"]["reasons"].append("injected")
        snapshot["denialReasons"].append("injected")
        # The original result + audit record must be unaffected.
        assert "injected" not in result.audit_record.get("reasons", [])
        assert "injected" not in result.denial_reasons

    def test_two_results_do_not_share_audit_objects(self) -> None:
        r1 = evaluate_sandbox_proof(_clean_request())
        r2 = evaluate_sandbox_proof(_clean_request())
        assert r1.audit_record is not r2.audit_record
        r1.audit_record["reasons"].append("x")
        assert "x" not in r2.audit_record.get("reasons", [])

    def test_result_audit_record_decoupled_from_builder(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(requested_capabilities=("plugin.execute",)))
        # Mutating the result's audit in place must not raise / leak into a
        # fresh safe-dict projection (the projection is a deep copy).
        result.audit_record["reasons"].append("mutated")
        projection = result.to_safe_dict()
        projection["audit"]["reasons"].clear()
        # The in-place mutation we made persists on the stored record (it is
        # mutable), but a second independent projection is unaffected by the
        # first projection's clear():
        projection2 = result.to_safe_dict()
        assert "mutated" in projection2["audit"]["reasons"]

    def test_to_safe_dict_re_redacts_in_place_secret_injection(self) -> None:
        # Regression: a holder mutating result.audit_record in place (e.g.
        # injecting a secret under a key) must NOT leak through to_safe_dict(),
        # which re-redacts the projection.
        result = evaluate_sandbox_proof(_clean_request())
        result.audit_record["safeMetadata"] = {"apiKey": FAKE_SK}
        result.audit_record["reasons"] = ["benign", f"leak {FAKE_SK}"]
        blob = json.dumps(result.to_safe_dict())
        assert FAKE_SK not in blob
        assert result.to_safe_dict()["audit"]["safeMetadata"]["apiKey"] == "[REDACTED]"


# ===========================================================================
# 3. Descriptor validation edge cases
# ===========================================================================


class TestDescriptorIdHardening:
    def test_unsafe_reason_registered(self) -> None:
        assert "descriptor_id_unsafe" in DESCRIPTOR_REASONS

    @pytest.mark.parametrize(
        "descriptor_id",
        [
            "../etc/passwd",          # traversal-like
            "plugin/x",               # path separator
            "plugin\\x",              # backslash separator
            "plugin|x",               # shell pipe
            "plugin;x",               # shell semicolon
            "plugin$(whoami)",        # shell substitution
            "plugin`id`",             # shell backtick
            "plugin>x",               # redirect
            "plugin*x",               # wildcard
            "plugin..x",              # traversal pair
            "plugin id",              # whitespace
            "plugin\x00x",            # null byte
        ],
    )
    def test_unsafe_descriptor_id_denied(self, descriptor_id: str) -> None:
        decision = evaluate_descriptor({"pluginId": descriptor_id, "status": "visible"})
        assert decision.allowed is False
        assert "descriptor_id_unsafe" in decision.reasons

    def test_missing_descriptor_id_denied(self) -> None:
        decision = evaluate_descriptor({"status": "visible"})
        assert decision.allowed is False
        assert "descriptor_id_missing" in decision.reasons

    def test_empty_descriptor_id_denied(self) -> None:
        decision = evaluate_descriptor({"pluginId": "", "status": "visible"})
        assert decision.allowed is False
        assert "descriptor_id_missing" in decision.reasons

    def test_clean_descriptor_id_still_allowed(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.descriptor.x", "status": "visible"})
        assert decision.allowed is True
        assert decision.descriptor_only is True

    def test_descriptor_metadata_with_secret_field_denied(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x", "apiKey": FAKE_SK})
        assert decision.allowed is False
        assert "descriptor_carries_execution_surface" in decision.reasons

    def test_descriptor_metadata_with_external_url_denied(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x", "externalUrl": "https://x.example"})
        assert decision.allowed is False

    def test_descriptor_metadata_with_module_hint_denied(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x", "pythonImportPath": "evil.mod"})
        assert decision.allowed is False

    def test_oversized_descriptor_denied(self) -> None:
        decision = evaluate_descriptor({"pluginId": "plugin.x", "note": "A" * 40_000})
        assert decision.allowed is False
        assert "descriptor_oversized" in decision.reasons

    def test_unsafe_id_does_not_leak_into_audit(self) -> None:
        decision = evaluate_descriptor({"pluginId": "../etc/passwd", "status": "visible"})
        blob = json.dumps(decision.to_safe_dict())
        assert "etc/passwd" not in blob
        assert ".." not in blob

    @pytest.mark.parametrize(
        "field",
        [
            "entrypoint",
            "entry_point",
            "module",
            "import",
            "command",
            "cmd",
            "exec",
            "shell",
            "bash",
            "url",
            "downloadUrl",
            "install",
            "packageUrl",
            "dockerImage",
            "wheelUrl",
            "manifestUrl",
            "password",
            "credentials",
            "private_key",
            "apikey",
            "API_KEY",
            "accessToken",
            "secret_data",
        ],
    )
    def test_synonym_execution_surface_field_denied(self, field: str) -> None:
        # Regression: the Phase 3D forbidden-field blocklist matches exact
        # names; synonym keys (entrypoint / module / command / url / password /
        # private_key / apikey / dockerImage …) must ALSO be denied by the
        # extended surface scan, not pass as descriptor-only.
        decision = evaluate_descriptor({"pluginId": "plugin.x", field: "evil-value"})
        assert decision.allowed is False
        assert "descriptor_carries_execution_surface" in decision.reasons

    def test_clean_descriptor_keys_not_false_positive(self) -> None:
        # Benign descriptor keys must not trip the extended surface scan.
        decision = evaluate_descriptor(
            {
                "pluginId": "plugin.descriptor.x",
                "status": "visible",
                "name": "demo",
                "version": "1.0",
                "description": "a clean descriptor",
                "author": "dev",
                "category": "tool",
            }
        )
        assert decision.allowed is True
        assert decision.descriptor_only is True


# ===========================================================================
# 4. Capability normalization edge cases
# ===========================================================================


class TestCapabilityNormalizationHardening:
    def test_injection_reason_registered(self) -> None:
        assert "capability_injection_denied" in CAPABILITY_REASONS

    @pytest.mark.parametrize(
        "capability",
        [
            "plugin.*",            # wildcard
            "plugin.*.execute",    # embedded wildcard
            "plugin.execute?",     # glob char
            "PLUGIN.EXECUTE",      # uppercase (not a known label)
            " plugin.execute ",    # whitespace-wrapped (not exact match)
            "plugin.execute/../",  # traversal-like
            "plugin|execute",      # shell pipe
            "plugin;execute",      # shell semicolon
            "plugin$(x)",          # shell substitution
            "plugin.execute\n",    # control char / not exact
            "plugin\\execute",     # backslash
        ],
    )
    def test_injection_or_unknown_capability_denied(self, capability: str) -> None:
        decision = evaluate_capability(capability)
        assert decision.allowed is False
        # Every dangerous label stays denied even if presented with casing /
        # whitespace tricks — normalization never elevates a dangerous cap.
        if capability.strip().lower().strip(".*?;|`$()<>/\\") in DANGEROUS_CAPABILITIES:
            assert decision.allowed is False

    def test_unknown_capability_denied(self) -> None:
        assert evaluate_capability("nonsense.cap").allowed is False
        assert evaluate_capability(123).allowed is False  # type: ignore[arg-type]
        assert evaluate_capability(None).allowed is False  # type: ignore[arg-type]
        assert evaluate_capability("").allowed is False

    def test_duplicate_dangerous_capabilities_all_denied(self) -> None:
        from hermes_cli.dev_web_sandbox_policy import evaluate_capabilities

        decisions = evaluate_capabilities(["plugin.execute", "plugin.execute", "plugin.execute"])
        assert len(decisions) == 3
        assert all(not d.allowed for d in decisions)

    def test_injection_capability_masked_in_decision(self) -> None:
        decision = evaluate_capability("plugin.$(whoami)")
        blob = json.dumps(decision.to_safe_dict())
        # The raw injection string must not be echoed into the audit field.
        assert "$(whoami)" not in blob
        assert decision.capability == "<invalid>"

    def test_allowed_label_still_allowed_and_safe(self) -> None:
        for cap in ("descriptor.read", "sandbox.proof.evaluate", "audit.redact"):
            decision = evaluate_capability(cap)
            assert decision.allowed is True
            assert decision.note == "proof_label_only_no_real_execution"

    def test_label_set_unchanged(self) -> None:
        assert len(CAPABILITY_LABELS) == 14


# ===========================================================================
# 5. Filesystem guard edge cases
# ===========================================================================


class TestFilesystemGuardHardening:
    def test_relative_path_outside_root_denied(self, tmp_path: Path) -> None:
        decision = evaluate_filesystem_path("../escape.json", allowed_roots=[str(tmp_path)])
        assert decision.allowed is False

    def test_nested_traversal_denied(self, tmp_path: Path) -> None:
        candidate = str(tmp_path / "a" / ".." / ".." / ".." / "etc" / "passwd")
        decision = evaluate_filesystem_path(candidate, allowed_roots=[str(tmp_path)])
        assert decision.allowed is False

    def test_mixed_separator_traversal_denied(self, tmp_path: Path) -> None:
        candidate = str(tmp_path) + "\\..\\escape.json"
        decision = evaluate_filesystem_path(candidate, allowed_roots=[str(tmp_path)])
        assert decision.allowed is False

    def test_trailing_slash_handled(self, tmp_path: Path) -> None:
        candidate = str(tmp_path / "fixture.json") + "/"
        decision = evaluate_filesystem_path(candidate, allowed_roots=[str(tmp_path)])
        # Trailing slash is benign; an in-root read stays allowed (no crash).
        assert decision.allowed is True

    def test_dot_segments_collapse_in_root(self, tmp_path: Path) -> None:
        candidate = str(tmp_path / "a" / "." / "b.json")
        decision = evaluate_filesystem_path(candidate, allowed_roots=[str(tmp_path)])
        assert decision.allowed is True
        assert decision.inside_allowed_root is True

    def test_symlink_inside_root_pointing_outside_denied(self, tmp_path: Path) -> None:
        link = tmp_path / "escape"
        os.symlink("/etc", link)
        decision = evaluate_filesystem_path(str(link), allowed_roots=[str(tmp_path)])
        assert decision.allowed is False

    def test_case_variant_production_path_denied(self) -> None:
        # On a case-insensitive host /.HERMES resolves to /.hermes — the
        # string-only evaluator must deny the case variant too.
        decision = evaluate_filesystem_path("/Users/huangruibang/.HERMES/state.db", allowed_roots=[])
        assert decision.allowed is False

    def test_case_variant_production_home_without_db_denied(self) -> None:
        # Exercises the case-insensitive absolute-production-path check
        # directly (no state.db stem to lean on).
        decision = evaluate_filesystem_path("/Users/huangruibang/.HERMES/notes.txt", allowed_roots=[])
        assert decision.allowed is False

    def test_fake_state_db_under_nested_path_denied(self) -> None:
        decision = evaluate_filesystem_path("/tmp/x/y/z/state.db", allowed_roots=[])
        assert decision.allowed is False

    @pytest.mark.parametrize(
        "name",
        [
            "plugin_registry.json",
            "plugin_execution_store.json",
            "provider_live_store.json",
            "workflow_runtime_store.json",
            "audit_runtime_store.json",
            "capability_runtime_store.json",
            "plugin_runtime.jsonl",
        ],
    )
    def test_runtime_store_write_denied_inside_root(self, tmp_path: Path, name: str) -> None:
        decision = evaluate_filesystem_path(
            str(tmp_path / name), allowed_roots=[str(tmp_path)], allow_write=True
        )
        assert decision.allowed is False

    def test_production_home_denied_via_baseline(self) -> None:
        result = evaluate_path_safety(str(PRODUCTION_HERMES_HOME / "memory" / "records"), allowed_roots=[])
        assert result["allowed"] is False

    @pytest.mark.parametrize(
        "sensitive",
        [
            "/Users/huangruibang/.ssh/config",
            "/Users/huangruibang/.aws/credentials",
            "/etc/passwd",
            "/etc/shadow",
            "/Users/huangruibang/.gnupg/secring.gpg",
            "/var/log/system.log",
        ],
    )
    def test_sensitive_host_read_denied_default_deny(self, sensitive: str) -> None:
        # Regression: a read of an arbitrary host path with no allowed root
        # (or outside a supplied root) must be denied (default-deny), not
        # allowed. These paths are referenced only as denial targets and are
        # never opened by the test.
        decision = evaluate_filesystem_path(sensitive, allowed_roots=[])
        assert decision.allowed is False
        assert "read_outside_allowed_root" in decision.reasons
        # And the raw sensitive path is not echoed unredacted.
        assert decision.path_redacted == "[REDACTED]" or sensitive not in json.dumps(
            decision.to_safe_dict()
        )

    def test_read_inside_root_still_allowed(self, tmp_path: Path) -> None:
        # The default-deny rule must not regress legitimate in-root reads.
        decision = evaluate_filesystem_path(
            str(tmp_path / "fixture.json"), allowed_roots=[str(tmp_path)]
        )
        assert decision.allowed is True
        assert decision.inside_allowed_root is True

    def test_decision_value_free(self) -> None:
        decision = evaluate_filesystem_path("/Users/huangruibang/.hermes/state.db", allowed_roots=[])
        blob = json.dumps(decision.to_safe_dict())
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob


# ===========================================================================
# 6. Network guard edge cases
# ===========================================================================


class TestNetworkGuardHardening:
    @pytest.mark.parametrize(
        "target",
        [
            "https://example.com",
            "http://localhost:8080",
            "http://127.0.0.1:5180",
            "http://[::1]:5180",
            "file:///etc/passwd",
            "ftp://example.com/file",
            "ws://example.com/socket",
            "wss://example.com/socket",
            "https://registry.npmjs.org/pkg",
            "https://marketplace.example.com/install",
            "https://api.openai.com/v1/chat",
            "https://provider.example.com/v1",
            "  https://example.com  ",   # whitespace wrapped
            "HTTPS://EXAMPLE.COM",       # mixed-case scheme
            "example.com",               # bare DNS-like host
        ],
    )
    def test_every_network_target_denied(self, target: str) -> None:
        decision = evaluate_network_target(target, capability_requested=True)
        assert decision.allowed is False
        assert "network_request_capability_denied" in decision.reasons

    def test_empty_target_with_capability_denied(self) -> None:
        decision = evaluate_network_target("", capability_requested=True)
        assert decision.allowed is False
        assert "network_request_capability_denied" in decision.reasons

    def test_no_target_no_capability_is_noop(self) -> None:
        decision = evaluate_network_target("")
        assert decision.allowed is True
        assert decision.reasons == ()

    def test_target_value_free_in_audit(self) -> None:
        decision = evaluate_network_target("https://api.openai.com/v1", capability_requested=True)
        blob = json.dumps(decision.to_safe_dict())
        assert "api.openai.com" not in blob


# ===========================================================================
# 7. Secrets / redaction edge cases
# ===========================================================================


class TestSecretRedactionHardening:
    @pytest.mark.parametrize(
        "value",
        [
            FAKE_SK,
            FAKE_GHP,
            FAKE_XOX,
            FAKE_BEARER,
            "Bearer sometoken123",
            FAKE_PEM,
            "API_KEY=abc123def456",
            "OPENAI_API_KEY=sk-fake1234567890",
            "DB_PASSWORD=hunter2",
            "CLIENT_SECRET=xyz789",
            "config: API_KEY=leaked-value",
            "/Users/huangruibang/.hermes/state.db",
            "~/.hermes/state.db",
            "error: token=sk-abcd1234efgh5678 rejected",
            "sk-abcd1234efgh5678 sk-abcd1234efgh5678 sk-abcd1234efgh5678",
        ],
    )
    def test_fake_secret_redacted(self, value: str) -> None:
        assert redact_sandbox_text(value) == "[REDACTED]"
        detected, reason = detect_secret_in_string(value)
        assert detected is True
        assert reason == "secret_value_detected"

    @pytest.mark.parametrize(
        "value",
        [
            "just a normal sentence",
            "maxTokens=1024",
            "temperature=0.7",
            "DEBUG=true",
            "a normal log line without secrets",
        ],
    )
    def test_safe_text_not_redacted(self, value: str) -> None:
        assert redact_sandbox_text(value) == value
        assert detect_secret_in_string(value)[0] is False

    def test_secret_in_json_text_redacted(self) -> None:
        value = '{"api_key": "sk-abcd1234efgh5678", "model": "gpt-fake"}'
        assert redact_sandbox_text(value) == "[REDACTED]"

    def test_payload_redacts_secret_fields(self) -> None:
        out = redact_sandbox_payload(
            {"api_key": FAKE_SK, "maxTokens": 100, "nested": {"token": FAKE_GHP}}
        )
        assert out["api_key"] == "[REDACTED]"
        assert out["maxTokens"] == 100
        assert out["nested"]["token"] == "[REDACTED]"

    def test_secret_request_denied_and_value_free(self) -> None:
        decision = evaluate_secret_request("OPENAI_API_KEY")
        assert decision.allowed is False
        assert decision.to_safe_dict()["keyValue"] == "never"

    def test_audit_redacts_secret_in_reasons(self) -> None:
        # A raw secret smuggled into the reasons list is caught by the final
        # defensive sweep → fail-closed denial record.
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["secret_request_denied", f"leak {FAKE_SK} here"],
        )
        blob = json.dumps(record)
        assert FAKE_SK not in blob
        assert record.get("redactionFailed") is True

    def test_audit_redacts_secret_in_error_detail(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["provider_request_denied"],
            safe_error_detail=f"upstream rejected key {FAKE_SK}",
        )
        blob = json.dumps(record)
        assert FAKE_SK not in blob
        assert record["errorDetail"] == "[REDACTED]"

    def test_audit_redacts_secret_in_metadata(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied",
            safe_metadata={"Authorization": FAKE_BEARER, "note": "ok"},
        )
        blob = json.dumps(record)
        assert FAKE_BEARER not in blob
        assert "Bearer" not in blob
        assert record["safeMetadata"]["Authorization"] == "[REDACTED]"

    def test_contains_secret_no_false_positive_on_counts(self) -> None:
        assert contains_secret({"maxTokens": 100, "totalTokens": 2048, "DEBUG": "true"}) is False

    @pytest.mark.parametrize(
        "value",
        [
            "db_password=hunter2",
            "api_key=abc123def456",
            "password=s3cr3tpw",
            "access_token=xyz789abc",
            "client_secret=xyz789",
            "openai_api_key=sk-fake1234567890",
            "accessToken=eyJfakejwt",
            "private_key=-----BEGIN PRIVATE KEY-----",
        ],
    )
    def test_lowercase_env_secret_redacted(self, value: str) -> None:
        # Regression: lowercase / mixed-case .env credential lines must be
        # redacted just like their UPPER_CASE equivalents.
        assert redact_sandbox_text(value) == "[REDACTED]"
        assert detect_secret_in_string(value)[0] is True

    def test_audit_smuggled_lowercase_secret_fails_closed(self) -> None:
        # A secret smuggled into reasons / errorDetail must trip the final
        # defensive sweep → fail-closed denial record (no raw secret).
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["provider_request_denied", "db_password=hunter2"],
            safe_error_detail="failed: password=s3cr3tpw",
        )
        blob = json.dumps(record)
        assert "hunter2" not in blob
        assert "s3cr3tpw" not in blob
        assert record.get("redactionFailed") is True
        assert is_audit_record_safe(record) is True


# ===========================================================================
# 8. Kill-switch hardening
# ===========================================================================


class TestKillSwitchHardening:
    def test_active_denies_clean_descriptor_only_proof(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(kill_switch_active=True))
        assert result.allowed is False
        assert "kill_switch_active" in result.denial_reasons

    def test_active_denies_every_capability(self) -> None:
        # Even an allowed label is blocked when the switch is armed.
        result = evaluate_sandbox_proof(
            _clean_request(kill_switch_active=True, requested_capabilities=("descriptor.read",))
        )
        assert result.allowed is False

    def test_cannot_be_overridden_by_metadata(self) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(
                kill_switch_active=True,
                safe_metadata={"kill_switch_active": False, "override": True},
            )
        )
        # Metadata is never consulted; the switch stays armed.
        assert result.allowed is False
        assert "kill_switch_active" in result.denial_reasons

    def test_invalid_state_fails_closed(self) -> None:
        # Non-bool / non-None values are an invalid kill-switch state → armed.
        for invalid in ("false", "no", 0, [], {}, "anything"):
            decision = evaluate_kill_switch(invalid)
            assert decision.active is True
            assert decision.fail_closed is True

    def test_none_and_false_are_inactive(self) -> None:
        assert evaluate_kill_switch(None).active is False
        assert evaluate_kill_switch(False).active is False

    def test_state_reflected_in_audit(self) -> None:
        result = evaluate_sandbox_proof(_clean_request(kill_switch_active=True))
        assert result.audit_record["killSwitchActive"] is True

    def test_never_signals_a_process(self) -> None:
        src = _src(policy_mod)
        assert "os.kill" not in src
        assert "signal.signal" not in src
        assert "import subprocess" not in src
        assert "subprocess.run" not in src
        assert "os.system" not in src


# ===========================================================================
# 9. Audit hardening
# ===========================================================================


class TestAuditHardening:
    def test_in_memory_only(self) -> None:
        record = build_sandbox_audit_record(decision="denied")
        assert record["persisted"] is False
        assert is_audit_record_safe(record) is True

    def test_carries_every_evidence_flag_false(self) -> None:
        record = build_sandbox_audit_record(decision="allowed")
        for flag in (
            "routeChangeRequired",
            "productionAccessRequired",
            "externalNetworkRequired",
            "realSecretRequired",
            "runtimeExecutionRequired",
        ):
            assert record["evidence"][flag] is False

    def test_includes_required_fields(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied",
            reasons=["network_request_denied"],
            triggered_guards=["network_deny"],
            requested_capabilities=["network.request"],
            descriptor_id="plugin.x",
            kill_switch_active=False,
        )
        for key in (
            "decision",
            "reasons",
            "triggeredGuards",
            "requestedCapabilities",
            "descriptorId",
            "killSwitchActive",
            "safeMetadata",
            "evidence",
            "redactionApplied",
            "persisted",
        ):
            assert key in record, key
        assert record["decision"] == "denied"

    def test_decision_coerced_to_denied(self) -> None:
        assert build_sandbox_audit_record(decision="maybe")["decision"] == "denied"

    def test_redaction_failure_fails_closed(self) -> None:
        record = build_sandbox_audit_record(
            decision="denied", reasons=[f"leak {FAKE_SK}"]
        )
        assert record.get("redactionFailed") is True
        assert record["decision"] == "denied"

    def test_audit_module_source_writes_no_file(self) -> None:
        src = _src(audit_mod)
        # The audit builder is in-memory only: no persistence primitives.
        for token in ("open(", "json.dump", ".write(", "sqlite3", "import pathlib", "os.remove"):
            assert token not in src, f"audit source contains {token!r}"

    def test_audit_module_source_has_no_network_or_dynamic_loading(self) -> None:
        src = _src(audit_mod)
        for token in (
            "import importlib",
            "importlib.import_module",
            "__import__(",
            "import subprocess",
            "subprocess.run",
            "socket.socket",
            "urllib.request",
            "import requests",
            "import httpx",
            "import aiohttp",
        ):
            assert token not in src, token


# ===========================================================================
# 10. Source-code boundary (all five modules)
# ===========================================================================


# Usage-pattern tokens (not bare words): the module docstrings intentionally
# spell out the *absent* surfaces ("No ``subprocess`` / ``shell`` / socket"), so
# a bare-word check would false-positive on the documentation. We grep for the
# actual call/import shapes instead — mirroring the skeleton test suite.
_STRICT_FORBIDDEN_TOKENS = (
    "import importlib",
    "importlib.import_module",
    "importlib.importer",
    "__import__(",
    "eval(",
    "exec(",
    "os.system",
    "shell=True",
    "import subprocess",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_output",
    "import requests",
    "import httpx",
    "import aiohttp",
    "socket.socket",
    "socket.connect",
    "urllib.request",
    "os.kill",
    "signal.signal",
)


@pytest.mark.parametrize("module", [guards_mod, policy_mod, audit_mod, proof_mod])
def test_sandbox_module_source_has_no_forbidden_surface(module) -> None:
    src = _src(module)
    for token in _STRICT_FORBIDDEN_TOKENS:
        assert token not in src, f"{module.__name__}: forbidden token {token!r}"


@pytest.mark.parametrize("module", [guards_mod, policy_mod, audit_mod, proof_mod])
def test_sandbox_module_has_no_subprocess(module) -> None:
    src = _src(module)
    for token in ("import subprocess", "subprocess.run", "subprocess.Popen", "subprocess.call"):
        assert token not in src, f"{module.__name__}: {token!r}"


def test_baseline_subprocess_confined_to_read_only_git() -> None:
    src = _src(baseline_mod)
    # The single allowed subprocess is the read-only .claude git helper.
    assert src.count("subprocess.run") == 1
    assert "shell=True" not in src
    for write_op in (
        '["git", "add"',
        '["git", "commit"',
        '["git", "reset"',
        '["git", "clean"',
        '["git", "push"',
    ):
        assert write_op not in src, write_op
    # The git helper must run with a fixed arg tuple (shell=False implicit).
    assert "subprocess.run(" in src


def test_baseline_has_no_network_or_dynamic_loading() -> None:
    src = _src(baseline_mod)
    for token in (
        "importlib.import_module",
        "__import__(",
        "import requests",
        "import httpx",
        "import aiohttp",
        "socket.socket",
        "urllib.request",
        "os.system",
    ):
        assert token not in src, token


# ===========================================================================
# 11. Dev-Web API isolation
# ===========================================================================


SANDBOX_MODULES = {
    "dev_web_sandbox_proof",
    "dev_web_sandbox_guards",
    "dev_web_sandbox_policy",
    "dev_web_sandbox_audit",
    "dev_web_safety_baseline",
    "dev_web_p0_evidence",
    "dev_web_sandbox_runner",
    "dev_web_sandbox_scenarios",
}


def test_no_dev_web_module_imports_sandbox_skeleton() -> None:
    dev_dir = REPO_ROOT / "hermes_cli"
    candidates = sorted(dev_dir.glob("dev_web_*.py"))
    assert len(candidates) > 5  # sanity: the glob found the family
    for path in candidates:
        if path.stem in SANDBOX_MODULES:
            continue
        src = path.read_text(encoding="utf-8")
        for mod in SANDBOX_MODULES:
            assert mod not in src, f"{path.name} references sandbox module {mod}"


def test_sandbox_proof_not_wired_into_fastapi_app(tmp_path: Path) -> None:
    api_src = (REPO_ROOT / "hermes_cli" / "dev_web_api.py").read_text(encoding="utf-8")
    for mod in SANDBOX_MODULES:
        assert mod not in api_src, f"dev_web_api.py references {mod}"


# ===========================================================================
# 12. Route governance unchanged
# ===========================================================================


class TestRouteGovernanceUnchanged:
    def test_counts_match_frozen_baseline(self, app) -> None:
        counts = route_governance_counts(app)
        assert counts == {
            "openApiPaths": 34,
            "runtimeRoutes": 34,
            "toolGetRoutes": 5,
            "toolWriteRoutes": 0,
            "toolDryRunRoutes": 1,
            "toolExecutionRoutes": 1,
        }

    def test_assert_unchanged_passes(self, app) -> None:
        assert_route_governance_unchanged(app)  # must not raise

    def test_openapi_paths_string_is_34_34_5_0_1_1(self, app) -> None:
        from hermes_cli.dev_web_safety_baseline import format_route_governance

        assert format_route_governance(route_governance_counts(app)) == ROUTE_GOVERNANCE_EXPECTED

    def test_new_route_flags_all_zero(self) -> None:
        from hermes_cli.dev_web_safety_baseline import route_governance_new_route_flags

        flags = route_governance_new_route_flags()
        assert flags == {
            "newHttpRoute": 0,
            "newToolWriteRoute": 0,
            "newProviderRoute": 0,
            "newPluginRoute": 0,
            "newRuntimeRoute": 0,
        }

    def test_no_descriptor_or_plugin_route_exposed(self, app) -> None:
        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lower = path.lower()
            assert "descriptor" not in lower
            assert "/plugin" not in lower
            assert "/sandbox" not in lower


# ===========================================================================
# 13. No persistent runtime artifacts
# ===========================================================================


class TestNoPersistentArtifacts:
    def test_hardening_proofs_create_no_runtime_files(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        for req in (
            _clean_request(),
            _clean_request(kill_switch_active=True),
            _clean_request(requested_capabilities=("plugin.execute",)),
            _clean_request(
                descriptor_metadata={"pluginId": "../etc/passwd", "status": "visible"}
            ),
            _clean_request(requested_network_targets=("https://api.openai.com",)),
            _clean_request(requested_secret_names=("OPENAI_API_KEY",)),
        ):
            evaluate_sandbox_proof(req)
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_hardening_does_not_open_hermes_home(self) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(
                requested_filesystem_paths=(
                    FilesystemRequest(path="/Users/huangruibang/.hermes/state.db"),
                ),
            )
        )
        assert result.allowed is False
        assert is_sandbox_proof_result_safe(result) is True


# ===========================================================================
# 14. End-to-end: hardened proof still value-free + safe
# ===========================================================================


class TestHardenedProofEndToEnd:
    def test_clean_proof_remains_allowed_and_safe(self) -> None:
        result = evaluate_sandbox_proof(_clean_request())
        assert result.allowed is True
        assert is_sandbox_proof_result_safe(result) is True

    def test_denied_proof_remains_safe(self) -> None:
        result = evaluate_sandbox_proof(
            _clean_request(
                requested_capabilities=("plugin.execute",),
                requested_network_targets=("https://marketplace.example.com/install",),
                requested_secret_names=("OPENAI_API_KEY",),
            )
        )
        assert result.allowed is False
        assert is_sandbox_proof_result_safe(result) is True
        blob = json.dumps(result.to_safe_dict())
        assert "marketplace.example.com" not in blob
        assert "OPENAI_API_KEY" not in blob

    def test_evidence_flags_all_false_after_hardening(self) -> None:
        result = evaluate_sandbox_proof(_clean_request())
        assert result.route_change_required is False
        assert result.production_access_required is False
        assert result.external_network_required is False
        assert result.real_secret_required is False
        assert result.runtime_execution_required is False
