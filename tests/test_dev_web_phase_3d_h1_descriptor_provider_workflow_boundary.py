"""Phase 3D-H1 — Provider / workflow boundary / no generated plugin.

Hardens Lens 8: a provider response / tool_calls / workflow output can **never**
create, install, enable, or execute a plugin descriptor. There is no function
that accepts a provider response or tool_calls and produces a descriptor. The
provider-generated-plugin and LLM-generated-plugin-install flags are False, and
the provider / workflow bridge descriptors stay disabled.

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hermes_cli import dev_web_plugin_descriptor_registry as registry_mod
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_registry import (
    LLM_GENERATED_PLUGIN_INSTALL_ALLOWED,
    PROVIDER_GENERATED_PLUGIN_ALLOWED,
    validate_manifest,
)

_FORBIDDEN_PROVIDER_WORKFLOW_APIS = (
    "create_descriptor_from_provider",
    "create_descriptor_from_tool_calls",
    "create_descriptor_from_workflow",
    "install_from_provider",
    "register_from_provider",
    "ingest_provider_response",
    "ingest_tool_calls",
    "ingest_workflow_output",
    "provider_install",
    "workflow_install",
    "auto_install",
    "auto_enable",
    "auto_advance",
)


class TestNoGenerationApi:
    @pytest.mark.parametrize("attr", _FORBIDDEN_PROVIDER_WORKFLOW_APIS)
    def test_registry_has_no_generation_api(self, attr: str) -> None:
        assert not hasattr(registry_mod, attr), f"unexpected generation API: {attr}"

    def test_source_has_no_provider_response_handler(self) -> None:
        src = Path(inspect.getsourcefile(registry_mod)).read_text(encoding="utf-8")
        # No handler that consumes a provider response / tool_calls / workflow output.
        for token in ("tool_calls", "provider_response", "workflow_output", "auto_advance"):
            assert token not in src, f"registry source references {token}"


class TestFrozenBoundaryFlags:
    def test_provider_generated_plugin_disabled(self) -> None:
        assert PROVIDER_GENERATED_PLUGIN_ALLOWED is False

    def test_llm_generated_plugin_install_disabled(self) -> None:
        assert LLM_GENERATED_PLUGIN_INSTALL_ALLOWED is False

    def test_status_block_disallows_generation(self) -> None:
        block = registry_mod.get_plugin_descriptor_status_block()
        assert block["providerGeneratedPluginAllowed"] is False
        assert block["llmGeneratedPluginInstallAllowed"] is False


class TestProviderWorkflowBridgesDisabled:
    def test_provider_bridge_descriptor_is_disabled(self) -> None:
        entry = next(
            e for e in get_static_manifest() if e["pluginId"] == "plugin.descriptor.provider_boundary_bridge"
        )
        assert entry["status"] == "disabled"
        assert entry["disabledByDefault"] is True
        assert entry["devOnly"] is True
        assert entry["productionAllowed"] is False

    def test_workflow_bridge_descriptor_is_disabled(self) -> None:
        entry = next(
            e for e in get_static_manifest() if e["pluginId"] == "plugin.descriptor.workflow_step_bridge"
        )
        assert entry["status"] == "disabled"
        assert entry["disabledByDefault"] is True
        assert entry["devOnly"] is True
        assert entry["productionAllowed"] is False

    def test_provider_bridge_does_not_bind_a_live_request_capability(self) -> None:
        entry = next(
            e for e in get_static_manifest() if e["pluginId"] == "plugin.descriptor.provider_boundary_bridge"
        )
        # The bridge binds only read-only boundary capabilities — never a live request.
        for cid in entry["capabilityBindings"]:
            assert "live" not in cid
            assert cid in {"provider.real_boundary_status", "provider.real_request_preview"}

    def test_workflow_bridge_binds_only_read_only_steps(self) -> None:
        entry = next(
            e for e in get_static_manifest() if e["pluginId"] == "plugin.descriptor.workflow_step_bridge"
        )
        for cid in entry["capabilityBindings"]:
            assert cid.startswith("workflow.step.")
        assert entry["permissionClass"] == "READ_ONLY"


class TestManifestCannotBeAugmentedByProviderOrWorkflow:
    def test_static_manifest_is_the_only_source(self) -> None:
        # The manifest is a frozen tuple; there is no runtime append path.
        manifest = get_static_manifest()
        assert isinstance(manifest, tuple)
        # Validation only ever reads what is passed in — a provider-injected
        # entry with a forbidden field is rejected, never silently added.
        report = validate_manifest(get_static_manifest())
        assert report.valid
        assert report.descriptor_count == 12
