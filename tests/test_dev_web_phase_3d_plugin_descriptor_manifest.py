"""Phase 3D — Plugin Descriptor Registry static manifest tests.

Verifies the static manifest is deterministic, tracked, dev-only,
disabled-by-default, descriptor-only, and carries no execution surface. Every
descriptor binds at least one existing Phase 3C capabilityId, no descriptor
introduces a new capabilityId or permission class, and no descriptor is
executable.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest as get_capability_manifest
from hermes_cli.dev_web_plugin_descriptor_manifest import (
    CREATED_AT,
    MANIFEST_VERSION,
    UPDATED_AT,
    STATIC_PLUGIN_DESCRIPTOR_MANIFEST,
    get_static_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_schema import (
    ALLOWED_FIELDS,
    FORBIDDEN_FIELDS,
    is_forbidden_field_present,
)


class TestManifestShape:
    def test_manifest_is_a_tuple_of_dicts(self) -> None:
        assert isinstance(STATIC_PLUGIN_DESCRIPTOR_MANIFEST, tuple)
        assert len(STATIC_PLUGIN_DESCRIPTOR_MANIFEST) >= 8
        for entry in STATIC_PLUGIN_DESCRIPTOR_MANIFEST:
            assert isinstance(entry, dict)

    def test_manifest_getter_returns_same_data(self) -> None:
        assert get_static_manifest() is STATIC_PLUGIN_DESCRIPTOR_MANIFEST

    def test_manifest_version_pinned(self) -> None:
        assert MANIFEST_VERSION == "phase3d-static-descriptor-v1"

    def test_timestamps_pinned_and_equal(self) -> None:
        # Deterministic — not wall-clock derived.
        assert CREATED_AT == UPDATED_AT
        assert CREATED_AT.endswith("Z")


class TestDescriptorInvariants:
    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_dev_only(self, entry: dict) -> None:
        assert entry["devOnly"] is True

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_production_not_allowed(self, entry: dict) -> None:
        assert entry["productionAllowed"] is False

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_disabled_by_default(self, entry: dict) -> None:
        assert entry["disabledByDefault"] is True

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_descriptor_only_mode(self, entry: dict) -> None:
        assert entry["executionMode"] == "descriptor_only"

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_no_forbidden_field(self, entry: dict) -> None:
        assert is_forbidden_field_present(entry) is None

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_only_allowed_fields(self, entry: dict) -> None:
        for key in entry:
            assert key in ALLOWED_FIELDS, f"unexpected field {key}"
            assert key not in FORBIDDEN_FIELDS

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_every_descriptor_has_nonempty_bindings(self, entry: dict) -> None:
        bindings = entry["capabilityBindings"]
        assert isinstance(bindings, (list, tuple))
        assert len(bindings) >= 1
        for cid in bindings:
            assert isinstance(cid, str) and cid

    @pytest.mark.parametrize("entry", list(STATIC_PLUGIN_DESCRIPTOR_MANIFEST))
    def test_blocked_descriptors_have_reason(self, entry: dict) -> None:
        if entry["status"] == "blocked":
            assert entry.get("blockedReason")


class TestCapabilityBinding:
    def test_all_bindings_reference_existing_phase_3c_capabilities(self) -> None:
        capability_ids = {e["capabilityId"] for e in get_capability_manifest()}
        for entry in STATIC_PLUGIN_DESCRIPTOR_MANIFEST:
            for cid in entry["capabilityBindings"]:
                assert cid in capability_ids, f"{entry['pluginId']} binds unknown capability {cid}"

    def test_no_descriptor_introduces_new_capability_id(self) -> None:
        # Every binding must exist; this re-asserts it from the registry angle.
        capability_ids = {e["capabilityId"] for e in get_capability_manifest()}
        for entry in STATIC_PLUGIN_DESCRIPTOR_MANIFEST:
            assert set(entry["capabilityBindings"]) <= capability_ids

    def test_blocked_descriptors_bind_forbidden_capabilities(self) -> None:
        forbidden_caps = {
            "capability.forbidden.dynamic_plugin_load",
            "capability.forbidden.remote_registry",
            "capability.forbidden.marketplace",
            "capability.forbidden.shell",
            "capability.forbidden.database_mutation",
            "capability.forbidden.external_http",
            "capability.forbidden.production_operation",
        }
        blocked = [e for e in STATIC_PLUGIN_DESCRIPTOR_MANIFEST if e["status"] == "blocked"]
        assert len(blocked) == 5
        # Each blocked descriptor binds at least one forbidden capability.
        for entry in blocked:
            assert set(entry["capabilityBindings"]) & forbidden_caps


class TestExpectedDescriptors:
    def test_expected_descriptor_ids_present(self) -> None:
        ids = {e["pluginId"] for e in STATIC_PLUGIN_DESCRIPTOR_MANIFEST}
        for pid in (
            "plugin.descriptor.registry_status",
            "plugin.descriptor.capability_binding_view",
            "plugin.descriptor.audit_view",
            "plugin.descriptor.read_only_tool_bridge",
            "plugin.descriptor.sandbox_write_preview_bridge",
            "plugin.descriptor.provider_boundary_bridge",
            "plugin.descriptor.workflow_step_bridge",
            "plugin.descriptor.dynamic_plugin_load_blocked",
            "plugin.descriptor.remote_registry_blocked",
            "plugin.descriptor.marketplace_blocked",
            "plugin.descriptor.external_execution_blocked",
            "plugin.descriptor.production_operation_blocked",
        ):
            assert pid in ids

    def test_plugin_ids_unique(self) -> None:
        ids = [e["pluginId"] for e in STATIC_PLUGIN_DESCRIPTOR_MANIFEST]
        assert len(ids) == len(set(ids))

    def test_descriptor_count(self) -> None:
        assert len(STATIC_PLUGIN_DESCRIPTOR_MANIFEST) == 12
