"""Phase 2B — Provider Schema Builder tests.

Verifies the provider schema is projected only from the Phase 2A read-only
allowlist, carries no write tools / provider-recursive tools / secrets /
callables, and validates cleanly against the boundary.

Phase: 2B — Provider Schema / API Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_schema import (
    build_provider_request_schema_summary,
    build_provider_tool_schema,
    build_provider_tool_schema_for_tool,
    redact_provider_schema_for_audit,
    validate_provider_schema_boundary,
    validate_provider_schema_bundle,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


ALLOWED = frozenset(STATIC_ALLOWLIST)


class TestProviderSchemaMembership:
    def test_schema_contains_exactly_allowlist_tools(self) -> None:
        bundle = build_provider_tool_schema()
        names = {t.name for t in bundle.tools}
        assert names == ALLOWED
        assert len(bundle.tools) == 6

    def test_schema_contains_no_write_tools(self) -> None:
        bundle = build_provider_tool_schema()
        names = {t.name for t in bundle.tools}
        for write_tool in ("write_file", "patch", "memory", "send_message", "terminal"):
            assert write_tool not in names

    def test_schema_contains_no_provider_recursive_tools(self) -> None:
        bundle = build_provider_tool_schema()
        for t in bundle.tools:
            # No tool advertises itself as a provider-callable round-trip tool.
            assert "provider" not in t.name

    def test_all_tools_read_only(self) -> None:
        bundle = build_provider_tool_schema()
        for t in bundle.tools:
            assert t.read_only is True
            assert t.provider_required is False
            assert t.write_required is False
            assert t.external_side_effects is False
            assert t.safety_tier == "read_only_safe"

    def test_single_tool_builder_returns_none_for_unknown(self) -> None:
        assert build_provider_tool_schema_for_tool("write_file") is None
        assert build_provider_tool_schema_for_tool("does_not_exist") is None

    def test_single_tool_builder_returns_entry_for_allowlisted(self) -> None:
        entry = build_provider_tool_schema_for_tool("route_governance_read")
        assert entry is not None
        assert entry.name == "route_governance_read"
        assert entry.read_only is True

    def test_allowed_tool_ids_intersection(self) -> None:
        bundle = build_provider_tool_schema(frozenset({"route_governance_read", "write_file"}))
        names = {t.name for t in bundle.tools}
        assert names == {"route_governance_read"}


class TestProviderSchemaBoundaryValidation:
    def test_valid_bundle_passes(self) -> None:
        bundle = build_provider_tool_schema()
        result = validate_provider_schema_bundle(bundle)
        assert result.valid, result.errors

    def test_boundary_rejects_non_allowlisted_raw_schema(self) -> None:
        bundle = build_provider_tool_schema()
        raw = bundle.to_safe_dict()
        # Inject a write tool into the raw schema → boundary must reject it.
        raw["tools"].append({
            "name": "write_file", "readOnly": True,
            "providerRequired": False, "writeRequired": False,
            "externalSideEffects": False,
        })
        result = validate_provider_schema_boundary(raw)
        assert not result.valid
        assert any("write_file" in e for e in result.errors)

    def test_boundary_rejects_write_flag_true(self) -> None:
        raw = {"tools": [{
            "name": "route_governance_read", "readOnly": True,
            "providerRequired": False, "writeRequired": True,
            "externalSideEffects": False,
        }]}
        result = validate_provider_schema_boundary(raw)
        assert not result.valid

    def test_boundary_rejects_non_object(self) -> None:
        result = validate_provider_schema_boundary("not a mapping")  # type: ignore[arg-type]
        assert not result.valid


class TestProviderSchemaSummaryAndRedaction:
    def test_summary_reports_counts(self) -> None:
        summary = build_provider_request_schema_summary()
        assert summary["toolCount"] == 6
        assert summary["writeToolCount"] == 0
        assert summary["providerRecursiveToolCount"] == 0
        assert summary["readOnlyOnly"] is True

    def test_redaction_drops_full_parameters_by_default(self) -> None:
        bundle = build_provider_tool_schema()
        audit = redact_provider_schema_for_audit(bundle)
        assert audit["redactionApplied"] is True
        for tool in audit["tools"]:
            # parameters dict is not carried in the audit projection.
            assert "parameters" not in tool
            assert set(tool) <= {
                "name", "readOnly", "providerRequired", "writeRequired",
                "externalSideEffects", "safetyTier", "descriptionLength",
                "descriptionPreview", "parameterCount",
            }

    def test_schema_safe_dict_has_no_callable_or_secret(self) -> None:
        bundle = build_provider_tool_schema()
        rendered = repr(bundle.to_safe_dict())
        for needle in ("callable", "function", "<function", "sk-", "Bearer "):
            assert needle not in rendered
