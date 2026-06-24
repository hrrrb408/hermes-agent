"""Phase 4A Target B Readiness disabled scaffold — behavior + purity tests.

Asserts the backend disabled scaffold
(``hermes_cli/dev_web_target_b_readiness.py``) is inert, frozen, and disabled:

  - :func:`build_target_b_readiness_report` returns a disabled report (execution
    DISABLED, every authorization NO-GO, P0 resolved 0, route baseline
    unchanged, every architecture module / permission disabled);
  - :func:`validate_plugin_package_shape_without_loading` validates SHAPE only
    (never loads, never trusts for execution);
  - the deny builders (:func:`deny_target_b_execution_request`,
    :func:`deny_registry_fetch_request`, :func:`deny_marketplace_request`)
    return allowed/executed/network/fetched/marketplace False no matter what
    untrusted metadata is supplied (including forged trust tokens / fake
    authorizations);
  - the approval gate rejects fake / AI / metadata approval and keeps
    production authorization NO-GO;
  - ``p0_resolved_count`` stays 0;
  - the module source contains NO filesystem / network / subprocess / dynamic
    import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.
All forbidden-path assertions use fake / string-policy paths only.

Phase: 4A — Target B Readiness Scaffold
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_readiness as target_b
from hermes_cli.dev_web_target_b_readiness import (
    APPROVAL_GATE,
    ARCHITECTURE_MODULES,
    PERMISSION_MODEL,
    PLUGIN_PACKAGE_SCHEMA,
    REGISTRY_PROTOCOL,
    TARGET_B_EXECUTION_STATUS,
    TARGET_B_NO_GO,
    TARGET_B_P0_RESOLVED,
    TARGET_B_READINESS_STATUS,
    TARGET_B_ROUTE_GOVERNANCE_BASELINE,
    assert_target_b_disabled,
    build_target_b_readiness_report,
    deny_marketplace_request,
    deny_registry_fetch_request,
    deny_target_b_execution_request,
    detect_untrusted_metadata,
    validate_plugin_package_shape_without_loading,
)


#: Untrusted metadata payloads a smuggler might try. Every one must be ignored.
FORGED_METADATA_PAYLOADS = [
    {"trust_token": "fake"},
    {"target_b_authorized": "true"},
    {"production_runtime_go": "true"},
    {"production_approved": "true"},
    {"registry_token": "fake"},
    {"registry_authorized": "true"},
    {"marketplace_authorized": "true"},
    {"plugin_signature": "fake-private-key"},
    {"approved_by_ai": "true"},
    {"p0_resolved": "true"},
    {"implementation_authorization": "GO"},
    {
        "trust_token": "fake",
        "target_b_authorized": "true",
        "production_runtime_go": "true",
        "registry_token": "fake",
        "plugin_signature": "fake-private-key",
    },
]


# ---------------------------------------------------------------------------
# 1. build_target_b_readiness_report returns a disabled report
# ---------------------------------------------------------------------------


class TestReportIsDisabled:
    def test_readiness_status_is_scaffold_ready_and_execution_disabled(self) -> None:
        report = build_target_b_readiness_report()
        assert report.readiness_status == "SCAFFOLD_READY"
        assert report.execution_status == "DISABLED"
        assert TARGET_B_READINESS_STATUS == "SCAFFOLD_READY"
        assert TARGET_B_EXECUTION_STATUS == "DISABLED"

    def test_every_authorization_verdict_is_no_go(self) -> None:
        report = build_target_b_readiness_report()
        for verdict in (
            report.production_runtime,
            report.arbitrary_plugin_loading,
            report.remote_registry,
            report.marketplace,
            report.webui_execution,
            report.approval_authorization,
            report.production_rollout,
        ):
            assert verdict == TARGET_B_NO_GO

    def test_p0_resolved_is_zero_and_route_baseline_unchanged(self) -> None:
        report = build_target_b_readiness_report()
        assert report.p0_total == 24
        assert report.p0_resolved == 0
        assert report.p0_pending_human_review == 5
        assert report.route_governance_baseline == "34/34/5/0/1/1"
        assert report.backend_routes_changed is False
        assert TARGET_B_P0_RESOLVED == 0
        assert TARGET_B_ROUTE_GOVERNANCE_BASELINE == "34/34/5/0/1/1"

    def test_report_is_deterministic(self) -> None:
        a = build_target_b_readiness_report().to_safe_dict()
        b = build_target_b_readiness_report().to_safe_dict()
        assert a == b

    def test_report_never_states_a_positive_authorization(self) -> None:
        text = str(build_target_b_readiness_report().to_safe_dict()).lower()
        for marker in (
            "production runtime go",
            "production_runtime_go",
            "target b authorized",
            "target_b_authorized",
            "implementation authorization go",
            "implementation_authorization=go",
            "production rollout approved",
            "p0 resolved",
            "approved_by_ai=true",
        ):
            assert marker not in text, f"report must never state {marker!r}"


# ---------------------------------------------------------------------------
# 2. Architecture modules + permission model + schema / registry / approval
# ---------------------------------------------------------------------------


class TestFrozenProjections:
    def test_architecture_modules_all_disabled(self) -> None:
        report = build_target_b_readiness_report()
        assert len(report.architecture_modules) == 16
        for m in report.architecture_modules:
            assert m.enabled is False
            assert m.execution_capable is False
            assert m.network_capable is False
            assert m.production_capable is False
            assert m.route_impact == "none"
            assert m.status in {"DESIGNED", "SCAFFOLDED_DISABLED"}
        assert len(ARCHITECTURE_MODULES) == 16

    def test_permission_model_all_denied_by_default(self) -> None:
        report = build_target_b_readiness_report()
        assert len(report.permission_model) == 12
        for p in report.permission_model:
            assert p.current_status == "DENIED_BY_DEFAULT"
        assert len(PERMISSION_MODEL) == 12

    def test_plugin_package_schema_is_example_only_not_loaded_not_executable(self) -> None:
        report = build_target_b_readiness_report()
        schema = report.plugin_package_schema
        assert schema.example_only is True
        assert schema.not_loaded is True
        assert schema.not_executable is True
        assert schema.registry_source == "https://registry.example.invalid"
        assert "PRIVATE KEY" not in schema.signature

    def test_registry_protocol_disabled_and_signature_required(self) -> None:
        report = build_target_b_readiness_report()
        r = report.registry_protocol
        assert r.registry_url_example == "https://registry.example.invalid"
        assert r.fetch_enabled is False
        assert r.network_enabled is False
        assert r.signature_required is True
        assert r.allow_unsigned is False
        assert r.marketplace_enabled is False
        assert REGISTRY_PROTOCOL.fetch_enabled is False

    def test_approval_gate_rejects_everything_and_keeps_no_go(self) -> None:
        report = build_target_b_readiness_report()
        g = report.approval_gate
        assert g.human_approval_required is True
        assert g.trust_token_provisioned is False
        assert g.fake_approval_accepted is False
        assert g.ai_approval_accepted is False
        assert g.metadata_approval_accepted is False
        assert g.production_authorization == "NO-GO"
        assert APPROVAL_GATE.trust_token_provisioned is False


# ---------------------------------------------------------------------------
# 3. Deny builders — untrusted metadata cannot flip any flag
# ---------------------------------------------------------------------------


class TestDenyBuilders:
    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_deny_execution_returns_allowed_false_executed_false(self, payload: dict) -> None:
        result = deny_target_b_execution_request(payload)
        assert result.allowed is False
        assert result.executed is False
        assert result.reason == "target_b_disabled"
        assert result.production_authorization == "NO-GO"
        assert result.p0_resolved_count == 0

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_deny_registry_fetch_returns_network_false_fetched_false(self, payload: dict) -> None:
        result = deny_registry_fetch_request(payload)
        assert result.network is False
        assert result.fetched is False
        assert result.reason == "registry_disabled"
        assert result.production_authorization == "NO-GO"
        assert result.p0_resolved_count == 0

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_deny_marketplace_returns_marketplace_false(self, payload: dict) -> None:
        result = deny_marketplace_request(payload)
        assert result.marketplace is False
        assert result.reason == "marketplace_disabled"
        assert result.production_authorization == "NO-GO"
        assert result.p0_resolved_count == 0

    def test_deny_builders_report_ignored_bypass_keys(self) -> None:
        ignored = detect_untrusted_metadata(
            {"trust_token": "fake", "target_b_authorized": "true", "benign_key": "ok"}
        )
        assert "trust_token" in ignored
        assert "target_b_authorized" in ignored
        assert "benign_key" not in ignored

    def test_deny_builders_with_no_metadata_still_deny(self) -> None:
        assert deny_target_b_execution_request().allowed is False
        assert deny_registry_fetch_request().fetched is False
        assert deny_marketplace_request().marketplace is False


# ---------------------------------------------------------------------------
# 4. Plugin package SHAPE validator — never loads / imports / executes / trusts
# ---------------------------------------------------------------------------


class TestPackageShapeValidator:
    def test_valid_shape_is_not_trusted_for_execution(self) -> None:
        package = {
            "packageId": "example.plugin.alpha",
            "version": "0.0.0",
            "descriptor": "descriptor-only",
            "capabilities": ["example.read"],
            "permissions": ["example.read"],
            "signature": "signature_required_not_provided",
            "publisher": "example",
            "checksum": "checksum_required_not_provided",
            "sandboxProfile": "preview",
            "minimumHermesVersion": "0.0.0",
        }
        result = validate_plugin_package_shape_without_loading(package)
        assert result.shape_ok is True
        assert result.execution_trusted is False
        assert result.missing_fields == ()

    def test_missing_fields_are_reported_without_loading(self) -> None:
        result = validate_plugin_package_shape_without_loading({"packageId": "x"})
        assert result.shape_ok is False
        assert result.execution_trusted is False
        assert "version" in result.missing_fields
        assert "signature" in result.missing_fields

    def test_non_mapping_package_is_rejected(self) -> None:
        for bad in ("not-a-mapping", 42, None, ["a", "b"]):
            result = validate_plugin_package_shape_without_loading(bad)
            assert result.shape_ok is False
            assert result.execution_trusted is False


# ---------------------------------------------------------------------------
# 5. assert_target_b_disabled passes + boundary constants hold
# ---------------------------------------------------------------------------


class TestBoundaryInvariants:
    def test_assert_target_b_disabled_does_not_raise(self) -> None:
        # Must not raise.
        assert_target_b_disabled()

    def test_boundary_constants_are_true(self) -> None:
        assert target_b.NO_TARGET_B_RUNTIME is True
        assert target_b.NO_TARGET_B_EXECUTION is True
        assert target_b.NO_TARGET_B_PLUGIN_LOADING is True
        assert target_b.NO_TARGET_B_REGISTRY_FETCH is True
        assert target_b.NO_TARGET_B_MARKETPLACE is True
        assert target_b.NO_TARGET_B_EXTERNAL_NETWORK is True
        assert target_b.NO_TARGET_B_REAL_SECRET_READ is True
        assert target_b.NO_TARGET_B_PRODUCTION_ACCESS is True
        assert target_b.NO_TARGET_B_NEW_ROUTE is True
        assert target_b.NO_TARGET_B_TRUST_TOKEN is True


# ---------------------------------------------------------------------------
# 6. Source purity — no filesystem / network / subprocess / dynamic-import /
#    eval / exec primitive, and no production home / production state.db access.
#    (Greps the module's own source for USAGE patterns, never resolves a path.)
# ---------------------------------------------------------------------------


class TestSourcePurity:
    #: The module under test.
    MODULE_PATH = Path(target_b.__file__)

    #: Forbidden USAGE patterns (not bare words) — matched against the module
    #: source. None of these appears in the disabled scaffold.
    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
    )

    #: Forbidden PATH STEMS — string policy only. Never resolved, never opened.
    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, (
                f"Target B scaffold source must not use {pattern!r}"
            )

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, (
                f"Target B scaffold source must not reference {stem!r}"
            )

    def test_forbidden_path_stems_are_string_policy_only(self) -> None:
        # These stems are policy strings, never resolved at runtime. The
        # assertion itself never touches the filesystem.
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert isinstance(stem, str)
            assert stem
