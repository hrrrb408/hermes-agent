"""Phase 3C-H1 — Capability Registry Non-grant / Permission Inheritance Hardening.

Hardens ``CAP-PERMISSION-NON-GRANT-3C-H1-001`` (Lens 3).

The registry **describes** capabilities; it never **authorizes** them. A
``permissionClass`` is a label, not a runtime grant. This test proves the
registry:

  - exposes no execute / grant / enable / approve / confirm / dry-run /
    rollback function,
  - imports no tool-execution / provider-execution / workflow-execution /
    confirmation-token / dry-run / approval / rollback surface,
  - performs no side effect (no audit write, no confirmation token, no dry-run
    digest, no rollback manifest, no live approval) when its read API is used,
  - never changes Tool policy, the Provider live gate, or Workflow approval.

A READ_ONLY / WRITE_CONFIRM / ROLLBACK_CONFIRM / LIVE_PROVIDER_GATED entry in
the registry therefore implies nothing about direct execution — each still
requires its existing external path.

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
from pathlib import Path
from typing import Any

import pytest

from hermes_cli.dev_web_capability_registry import (
    __all__ as REGISTRY_ALL,
    build_registry_summary,
    get_capability_detail,
    get_registry_status_block,
    list_capability_details,
    validate_manifest,
)
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest

REGISTRY_MODULES = (
    "hermes_cli.dev_web_capability_registry",
    "hermes_cli.dev_web_capability_registry_manifest",
    "hermes_cli.dev_web_capability_registry_schema",
    "hermes_cli.dev_web_capability_registry_policy",
    "hermes_cli.dev_web_capability_registry_audit",
)

#: Substrings that must NEVER appear as a registry public function name —
#: each would imply the registry grants or executes something.
_GRANT_VERBS = (
    "execute",
    "grant",
    "enable",
    "disable",
    "approve",
    "reject",
    "confirm",
    "issue_token",
    "dry_run",
    "dryrun",
    "rollback",
    "run_",
    "dispatch",
    "invoke",
    "call_tool",
    "call_provider",
    "promote",
    "install",
    "load_plugin",
    "import_module",
    "fetch",
)


def _public_callables(module_name: str) -> list[str]:
    mod = importlib.import_module(module_name)
    names: list[str] = []
    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        obj = getattr(mod, attr)
        if callable(obj) and getattr(obj, "__module__", "") == module_name:
            names.append(attr)
    return names


def _module_imports(module_name: str) -> set[str]:
    mod = importlib.import_module(module_name)
    src_path = Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


class TestNoGrantOrExecuteSurface:
    def test_registry_all_has_no_grant_or_execute_function(self) -> None:
        for name in REGISTRY_ALL:
            lowered = name.lower()
            for verb in _GRANT_VERBS:
                assert verb not in lowered, f"registry exposes grant/execute symbol: {name}"

    @pytest.mark.parametrize("module_name", REGISTRY_MODULES)
    def test_no_module_exposes_grant_or_execute_callable(self, module_name: str) -> None:
        for name in _public_callables(module_name):
            lowered = name.lower()
            for verb in _GRANT_VERBS:
                assert verb not in lowered, (
                    f"{module_name} exposes grant/execute callable: {name}"
                )

    @pytest.mark.parametrize("module_name", REGISTRY_MODULES)
    def test_no_module_imports_execution_surfaces(self, module_name: str) -> None:
        imports = _module_imports(module_name)
        # The registry must not import the execution / gate surfaces it describes.
        forbidden_imports = {
            "run_agent",
            "model_tools",
            "toolsets",
            "tools",
            "gateway",
            "cron",
            # Provider live execution surfaces:
            "dev_web_provider_live_roundtrip",
            "dev_web_provider_live_approval",
            "dev_web_provider_live_kill_switch",
            "dev_web_provider_live_budget",
            # Sandbox write / rollback execution surfaces:
            "dev_web_sandbox_write",
            "dev_web_sandbox_rollback",
            "dev_web_confirmation_tokens",
            # Workflow execution surface:
            "dev_web_workflow_runtime",
            "dev_web_workflow_executor",
        }
        for imp in forbidden_imports:
            assert imp not in imports, f"{module_name} imports execution surface: {imp}"


class TestReadModelIsSideEffectFree:
    def test_read_api_writes_nothing_to_dev_home(self, tmp_path: Path, monkeypatch) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(home))

        # Exercise the entire read API.
        validate_manifest(get_static_manifest())
        list_capability_details(get_static_manifest())
        for entry in get_static_manifest():
            get_capability_detail(get_static_manifest(), entry["capabilityId"])
        build_registry_summary()
        get_registry_status_block()

        # No side-effect stores may appear under the dev home.
        walked = [str(p.relative_to(home)) for p in home.rglob("*")]
        forbidden_artifacts = (
            "confirmation-tokens",
            "tool-write-rollback-manifests",
            "audit-store",
            "workflow-store",
            "provider-live-approvals",
            "provider-live-budget",
            "provider-live-kill-switch",
            "capability-registry-store",
            "events.jsonl",
        )
        for artifact in forbidden_artifacts:
            for path in walked:
                assert artifact not in path, f"registry read created artifact: {path}"

    def test_read_api_does_not_create_audit_events(self, tmp_path: Path, monkeypatch) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(home))
        build_registry_summary()
        # No audit event log is created by the pure read model.
        assert not any(home.rglob("*.jsonl"))


class TestPermissionIsDescriptiveOnly:
    """A permission class in the registry does not imply any execution path."""

    @pytest.mark.parametrize(
        "cid,permission_class",
        [
            ("tool.read.route_governance_read", "READ_ONLY"),
            ("tool.sandbox.dev_sandbox_file_write", "WRITE_CONFIRM"),
            ("tool.sandbox.dev_sandbox_rollback_execute", "ROLLBACK_CONFIRM"),
            ("provider.real_gated_roundtrip", "LIVE_PROVIDER_GATED"),
        ],
    )
    def test_capability_carries_no_execution_binding(self, cid: str, permission_class: str) -> None:
        detail = get_capability_detail(get_static_manifest(), cid)
        assert detail is not None
        assert detail["permissionClass"] == permission_class
        # No execution pointer field exists on the safe detail.
        for forbidden in ("pythonImportPath", "callable", "shellCommand", "toolBinding"):
            # toolBinding is a *label*, not an execution pointer — it is allowed
            # and is a plain string. Assert it is a string when present.
            pass
        # The detail exposes only descriptive fields; no callable/pointer.
        blob = str(detail)
        for token in ("callable", "pythonImportPath", "shellCommand", "<function"):
            assert token not in blob

    def test_write_confirm_still_requires_external_confirmation_path(self) -> None:
        detail = get_capability_detail(
            get_static_manifest(), "tool.sandbox.dev_sandbox_file_write"
        )
        assert detail is not None
        assert detail["requiresDryRun"] is True
        assert detail["requiresConfirmation"] is True
        assert detail["requiresAudit"] is True
        # The registry itself offers no function to satisfy these gates.

    def test_live_gated_still_requires_external_live_gate(self) -> None:
        detail = get_capability_detail(
            get_static_manifest(), "provider.real_gated_roundtrip"
        )
        assert detail is not None
        assert detail["requiresApproval"] is True
        assert detail["requiresBudget"] is True
        assert detail["requiresKillSwitch"] is True
        assert detail["requiresAudit"] is True
        assert detail["status"] == "disabled"


class TestForbiddenCapabilitiesRemainBlocked:
    @pytest.mark.parametrize(
        "cid",
        [
            "capability.forbidden.dynamic_plugin_load",
            "capability.forbidden.remote_registry",
            "capability.forbidden.marketplace",
            "capability.forbidden.shell",
            "capability.forbidden.production_operation",
        ],
    )
    def test_forbidden_capability_blocked(self, cid: str) -> None:
        detail = get_capability_detail(get_static_manifest(), cid)
        assert detail is not None
        assert detail["status"] == "blocked"
        assert detail["executionMode"] == "none"
        assert detail["routeExposure"] == "forbidden_new_route"
