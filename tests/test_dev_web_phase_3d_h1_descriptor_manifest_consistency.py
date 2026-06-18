"""Phase 3D-H1 — Descriptor manifest determinism / mirror consistency.

Hardens Lens 1: the static plugin-descriptor manifest must be deterministic,
stable, and descriptor-only. Verifies the manifest is a single source of truth,
its descriptor count / IDs / order / pinned timestamps are stable, the read
model shape is value-free, and drift is detectable (any mutation to a pinned
field fails validation). No plugin runtime, no loader, no dynamic loading.

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import copy

import pytest

from hermes_cli.dev_web_plugin_descriptor_manifest import (
    CREATED_AT,
    MANIFEST_VERSION,
    STATIC_PLUGIN_DESCRIPTOR_MANIFEST,
    UPDATED_AT,
    get_static_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_registry import (
    build_registry_summary,
    get_descriptor_detail,
    get_plugin_descriptor_status_block,
    list_descriptor_details,
    validate_manifest,
)

#: Frozen descriptor IDs in deterministic order (visible → disabled → blocked).
_EXPECTED_PLUGIN_IDS: tuple[str, ...] = (
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
)

_EXPECTED_CREATED_AT = "2026-06-18T00:00:00Z"
_EXPECTED_UPDATED_AT = "2026-06-18T00:00:00Z"
_EXPECTED_VERSION = "phase3d-static-descriptor-v1"


class TestManifestDeterminism:
    def test_get_static_manifest_returns_twelve_entries(self) -> None:
        manifest = get_static_manifest()
        assert len(manifest) == 12

    def test_static_constant_matches_accessor(self) -> None:
        assert STATIC_PLUGIN_DESCRIPTOR_MANIFEST == get_static_manifest()

    def test_manifest_is_deterministic_across_loads(self) -> None:
        first = get_static_manifest()
        second = get_static_manifest()
        # Same identity is allowed (frozen tuple); content must be identical.
        assert [e["pluginId"] for e in first] == [e["pluginId"] for e in second]
        assert first == second

    def test_plugin_ids_are_unique(self) -> None:
        ids = [e["pluginId"] for e in get_static_manifest()]
        assert len(ids) == len(set(ids))

    def test_plugin_ids_match_frozen_set_in_order(self) -> None:
        ids = tuple(e["pluginId"] for e in get_static_manifest())
        assert ids == _EXPECTED_PLUGIN_IDS

    def test_order_is_visible_then_disabled_then_blocked(self) -> None:
        statuses = [e["status"] for e in get_static_manifest()]
        assert statuses == ["visible"] * 3 + ["disabled"] * 4 + ["blocked"] * 5


class TestPinnedTimestamps:
    def test_created_at_is_pinned_constant(self) -> None:
        assert CREATED_AT == _EXPECTED_CREATED_AT

    def test_updated_at_is_pinned_constant(self) -> None:
        assert UPDATED_AT == _EXPECTED_UPDATED_AT

    def test_version_is_pinned_constant(self) -> None:
        assert MANIFEST_VERSION == _EXPECTED_VERSION

    def test_every_entry_carries_pinned_timestamps(self) -> None:
        for entry in get_static_manifest():
            assert entry["createdAt"] == _EXPECTED_CREATED_AT
            assert entry["updatedAt"] == _EXPECTED_UPDATED_AT
            assert entry["version"] == _EXPECTED_VERSION


class TestReadModelShape:
    def test_validation_passes_on_static_manifest(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid
        assert report.error_count == 0
        assert report.descriptor_count == 12
        assert report.visible_count == 3
        assert report.disabled_count == 4
        assert report.blocked_count == 5

    def test_status_block_carries_descriptor_counts(self) -> None:
        block = get_plugin_descriptor_status_block()
        assert block["descriptorCount"] == 12
        assert block["visibleCount"] == 3
        assert block["disabledCount"] == 4
        assert block["blockedCount"] == 5
        assert block["registryVersion"] == _EXPECTED_VERSION
        assert block["status"] == "enabled"
        assert block["validation"]["valid"] is True

    def test_status_block_summary_equals_build_registry_summary(self) -> None:
        # The /status entry point must agree with the explicit builder.
        assert get_plugin_descriptor_status_block() == build_registry_summary()

    def test_list_descriptor_details_returns_one_per_entry_with_redaction(self) -> None:
        details = list_descriptor_details(get_static_manifest())
        assert len(details) == 12
        for detail in details:
            assert detail["redactionApplied"] is True

    def test_get_descriptor_detail_roundtrip(self) -> None:
        for plugin_id in _EXPECTED_PLUGIN_IDS:
            detail = get_descriptor_detail(get_static_manifest(), plugin_id)
            assert detail is not None
            assert detail["pluginId"] == plugin_id

    def test_get_descriptor_detail_unknown_returns_none(self) -> None:
        assert get_descriptor_detail(get_static_manifest(), "plugin.descriptor.does_not_exist") is None


class TestDriftDetection:
    """Any drift in a pinned invariant must flip validation to invalid."""

    @pytest.mark.parametrize(
        "field,value",
        [
            ("devOnly", False),
            ("productionAllowed", True),
            ("disabledByDefault", False),
        ],
    )
    def test_mutating_first_version_invariant_fails_validation(
        self, field: str, value: object
    ) -> None:
        entries = [copy.deepcopy(e) for e in get_static_manifest()]
        entries[0][field] = value
        assert not validate_manifest(entries).valid

    def test_forcing_blocked_descriptor_visible_fails_validation(self) -> None:
        # A descriptor bound to a forbidden capability must stay blocked.
        entries = [copy.deepcopy(e) for e in get_static_manifest()]
        blocked = next(
            e for e in entries if e["pluginId"] == "plugin.descriptor.dynamic_plugin_load_blocked"
        )
        blocked["status"] = "visible"
        assert not validate_manifest(entries).valid

    def test_introducing_a_duplicate_plugin_id_fails_validation(self) -> None:
        entries = [copy.deepcopy(e) for e in get_static_manifest()]
        entries[1]["pluginId"] = entries[0]["pluginId"]
        assert not validate_manifest(entries).valid

    def test_dropping_a_required_field_fails_validation(self) -> None:
        entries = [copy.deepcopy(e) for e in get_static_manifest()]
        del entries[0]["permissionClass"]
        assert not validate_manifest(entries).valid

    def test_invalid_manifest_summary_is_validation_failed(self) -> None:
        entries = [copy.deepcopy(e) for e in get_static_manifest()]
        entries[0]["pythonImportPath"] = "evil.module"  # forbidden field
        report = validate_manifest(entries)
        summary = build_registry_summary(report)
        assert summary["status"] == "validation_failed"
        assert summary["validation"]["valid"] is False
