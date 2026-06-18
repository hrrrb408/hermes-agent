"""Phase 3C-H1 — Tool / Provider / Workflow Capability Mapping Hardening.

Hardens ``CAP-MAPPING-3C-H1-001`` (Lens 5 / 6 / 7).

Verifies the EXACT permission-class / status mapping for every described tool,
provider, and workflow capability. The registry describes the real boundaries
already implemented in Phases 2A–2E / 3A / 3B; this pins them so a mapping
regression (e.g. a forbidden provider write re-classified as READ_ONLY) fails
this test.

Mapping invariants (Lens 5 / 6 / 7):
  - read-only tools            → READ_ONLY
  - sandbox writes             → WRITE_CONFIRM (dry-run + confirmation + audit)
  - sandbox rollback           → ROLLBACK_CONFIRM
  - provider fake / boundary   → READ_ONLY
  - provider live              → LIVE_PROVIDER_GATED (listed, disabled, not executed)
  - provider write / auto      → ADMIN_FORBIDDEN (permanently blocked)
  - workflow read-only steps   → READ_ONLY
  - workflow write preview     → WRITE_PREVIEW
  - workflow write / rollback  → blocked until separately authorized
  - workflow auto-advance      → ADMIN_FORBIDDEN (permanently blocked)

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_capability_registry import get_capability_detail
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest


def _detail(cid: str) -> dict:
    d = get_capability_detail(get_static_manifest(), cid)
    assert d is not None, f"missing capability {cid}"
    return d


class TestToolMapping:
    @pytest.mark.parametrize(
        "cid",
        [
            "tool.read.clarify",
            "tool.read.tool_policy_read",
            "tool.read.route_governance_read",
            "tool.read.audit_events_read",
            "tool.read.dev_environment_read",
            "tool.read.release_status_read",
        ],
    )
    def test_read_only_tool_mapping(self, cid: str) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == "READ_ONLY"
        assert d["executionMode"] == "read_only"
        assert d["status"] == "enabled"
        assert d["requiresAudit"] is True

    @pytest.mark.parametrize(
        "cid",
        [
            "tool.sandbox.dev_sandbox_file_write",
            "tool.sandbox.dev_sandbox_file_append",
            "tool.sandbox.dev_sandbox_file_patch",
        ],
    )
    def test_sandbox_write_mapping(self, cid: str) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == "WRITE_CONFIRM"
        assert d["executionMode"] == "confirmed_execute"
        assert d["requiresDryRun"] is True
        assert d["requiresConfirmation"] is True
        assert d["requiresAudit"] is True

    def test_sandbox_readback_is_read_only(self) -> None:
        d = _detail("tool.sandbox.dev_sandbox_file_readback")
        assert d["permissionClass"] == "READ_ONLY"
        assert d["executionMode"] == "read_only"

    def test_sandbox_rollback_mapping(self) -> None:
        d = _detail("tool.sandbox.dev_sandbox_rollback_execute")
        assert d["permissionClass"] == "ROLLBACK_CONFIRM"
        assert d["executionMode"] == "confirmed_execute"
        assert d["requiresConfirmation"] is True
        assert d["requiresAudit"] is True


class TestProviderMapping:
    @pytest.mark.parametrize(
        "cid",
        [
            "provider.fake_roundtrip",
            "provider.real_boundary_status",
            "provider.real_request_preview",
            "provider.tool_call_classification",
        ],
    )
    def test_provider_read_only_mapping(self, cid: str) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == "READ_ONLY"
        assert d["executionMode"] in {"read_only", "dry_run"}
        assert d["status"] == "enabled"

    def test_provider_real_gated_roundtrip_is_live_gated(self) -> None:
        d = _detail("provider.real_gated_roundtrip")
        assert d["permissionClass"] == "LIVE_PROVIDER_GATED"
        assert d["executionMode"] == "manual_live"
        assert d["requiresApproval"] is True
        assert d["requiresBudget"] is True
        assert d["requiresKillSwitch"] is True
        assert d["requiresAudit"] is True
        # Disabled by default; never auto-executed.
        assert d["status"] == "disabled"
        assert d["disabledByDefault"] is True

    def test_provider_live_manual_one_shot_listed_not_executed(self) -> None:
        d = _detail("provider.live_manual_one_shot")
        assert d["permissionClass"] == "LIVE_PROVIDER_GATED"
        assert d["executionMode"] == "manual_live"
        # Listed only — disabled, not executed in the first version.
        assert d["status"] == "disabled"
        assert d["disabledByDefault"] is True
        assert d["requiresBudget"] is True
        assert d["requiresKillSwitch"] is True
        assert d["requiresApproval"] is True

    @pytest.mark.parametrize(
        "cid,blocked_reason_fragment",
        [
            ("provider.tool_execution", "provider_tool_execution_blocked"),
            ("provider.write", "provider_write_forbidden"),
            ("provider.auto_write", "provider_auto_write_forbidden"),
            ("provider.autonomous_action", "provider_autonomous_action_forbidden"),
        ],
    )
    def test_provider_write_and_autonomy_permanently_blocked(
        self, cid: str, blocked_reason_fragment: str
    ) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == "ADMIN_FORBIDDEN"
        assert d["status"] == "blocked"
        assert d["executionMode"] == "none"
        assert d["routeExposure"] == "forbidden_new_route"
        assert blocked_reason_fragment in (d.get("blockedReason") or "")


class TestWorkflowMapping:
    @pytest.mark.parametrize(
        "cid",
        [
            "workflow.step.read_only_tool",
            "workflow.step.fake_provider_roundtrip",
            "workflow.step.rollback_reference",
            "workflow.step.manual_note",
            "workflow.step.audit_query",
        ],
    )
    def test_workflow_read_only_step_mapping(self, cid: str) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == "READ_ONLY"
        assert d["executionMode"] == "read_only"
        assert d["status"] == "enabled"

    def test_workflow_sandbox_write_preview_is_write_preview(self) -> None:
        d = _detail("workflow.step.sandbox_write_preview")
        assert d["permissionClass"] == "WRITE_PREVIEW"
        assert d["executionMode"] == "dry_run"
        assert d["requiresDryRun"] is True

    @pytest.mark.parametrize(
        "cid,permission_class",
        [
            ("workflow.write_execute", "WRITE_CONFIRM"),
            ("workflow.rollback_execute", "ROLLBACK_CONFIRM"),
        ],
    )
    def test_workflow_write_and_rollback_blocked_until_authorized(
        self, cid: str, permission_class: str
    ) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == permission_class
        assert d["status"] == "blocked"
        assert d["executionMode"] == "none"
        assert d["routeExposure"] == "forbidden_new_route"
        assert d["trustLevel"] == "EXPERIMENTAL_DISABLED"

    @pytest.mark.parametrize(
        "cid",
        [
            "workflow.auto_advance",
            "workflow.autonomous_write",
            "workflow.background_schedule",
        ],
    )
    def test_workflow_autonomy_permanently_blocked(self, cid: str) -> None:
        d = _detail(cid)
        assert d["permissionClass"] == "ADMIN_FORBIDDEN"
        assert d["status"] == "blocked"
        assert d["executionMode"] == "none"
        assert d["routeExposure"] == "forbidden_new_route"


class TestRegistryDoesNotBypassExternalGates:
    """The mapping describes gates; it never satisfies them. Confirm the
    WRITE_CONFIRM / ROLLBACK_CONFIRM / LIVE_PROVIDER_GATED entries still
    declare every gate the real external path requires."""

    def test_write_confirm_tools_declare_full_gate_set(self) -> None:
        for cid in (
            "tool.sandbox.dev_sandbox_file_write",
            "tool.sandbox.dev_sandbox_file_append",
            "tool.sandbox.dev_sandbox_file_patch",
        ):
            d = _detail(cid)
            assert d["requiresDryRun"] is True
            assert d["requiresConfirmation"] is True
            assert d["requiresAudit"] is True

    def test_live_provider_entries_declare_full_gate_set(self) -> None:
        for cid in ("provider.real_gated_roundtrip", "provider.live_manual_one_shot"):
            d = _detail(cid)
            assert d["requiresApproval"] is True
            assert d["requiresBudget"] is True
            assert d["requiresKillSwitch"] is True
            assert d["requiresAudit"] is True
