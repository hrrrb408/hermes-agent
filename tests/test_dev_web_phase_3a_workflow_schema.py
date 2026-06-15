"""Phase 3A — Workflow schema unit tests.

Verifies the workflow_schema_v1 contract: schema version, id prefixes, the six
allowed step types, the forbidden step types + their blocked reasons, the step
status lifecycle, the frozen safety boundary, and the input sanitizer (no
secrets / tokens / paths / callables).
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_workflow_schema import (
    ALLOWED_STEP_TYPES,
    BLOCKED_AUTONOMOUS_WRITE,
    BLOCKED_DATABASE,
    BLOCKED_EXTERNAL_SERVICE,
    BLOCKED_PRODUCTION,
    BLOCKED_REAL_PROVIDER,
    BLOCKED_ROLLBACK_EXECUTE,
    BLOCKED_SHELL,
    EVENT_WORKFLOW_PLAN_CREATED,
    FORBIDDEN_STEP_TYPES,
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    VALID_STEP_STATUSES,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowDefinition,
    WorkflowStep,
    blocked_reason_for_step_type,
    contains_unsafe_path,
    is_allowed_step_type,
    is_forbidden_step_type,
    is_valid_workflow_id,
    new_workflow_id,
    redact_secret_strings,
    sanitize_workflow_value,
    validate_workflow_definition,
)


class TestSchemaVersion:
    def test_schema_version_is_v1(self) -> None:
        assert WORKFLOW_SCHEMA_VERSION == "workflow_schema_v1"

    def test_id_prefixes(self) -> None:
        for prefix in ("wf_", "wfp_", "wfs_", "wfx_", "wfa_"):
            wid = new_workflow_id(prefix)
            assert wid.startswith(prefix)
            assert is_valid_workflow_id(wid, prefix)

    def test_invalid_id_rejected(self) -> None:
        assert not is_valid_workflow_id("not-an-id", "wf_")
        assert not is_valid_workflow_id("wf_short", "wf_")
        assert not is_valid_workflow_id(None, "wf_")


class TestStepTypes:
    def test_six_allowed_step_types(self) -> None:
        assert ALLOWED_STEP_TYPES == frozenset(
            {
                STEP_READ_ONLY_TOOL,
                STEP_FAKE_PROVIDER_ROUNDTRIP,
                STEP_SANDBOX_WRITE_PREVIEW,
                STEP_ROLLBACK_REFERENCE,
                STEP_MANUAL_NOTE,
                STEP_AUDIT_QUERY,
            }
        )

    @pytest.mark.parametrize(
        "step_type,reason",
        [
            ("real_provider_roundtrip", BLOCKED_REAL_PROVIDER),
            ("sandbox_write_execute", BLOCKED_AUTONOMOUS_WRITE),
            ("rollback_execute", BLOCKED_ROLLBACK_EXECUTE),
            ("shell_command", BLOCKED_SHELL),
            ("database_mutation", BLOCKED_DATABASE),
            ("external_http_request", BLOCKED_EXTERNAL_SERVICE),
            ("production_operation", BLOCKED_PRODUCTION),
            ("plugin_dynamic_load", "blocked_workflow_plugin_dynamic_load_not_allowed"),
        ],
    )
    def test_forbidden_step_types_blocked(self, step_type: str, reason: str) -> None:
        assert is_forbidden_step_type(step_type)
        assert not is_allowed_step_type(step_type)
        assert blocked_reason_for_step_type(step_type) == reason

    def test_unknown_step_type_not_allowed(self) -> None:
        assert not is_allowed_step_type("not_a_real_step")
        assert not is_forbidden_step_type("not_a_real_step")
        assert blocked_reason_for_step_type("not_a_real_step") is None

    def test_status_lifecycle(self) -> None:
        for status in (
            "draft", "planned", "previewed", "approval_required", "approved",
            "ready", "running", "completed", "blocked", "failed", "skipped",
        ):
            assert status in VALID_STEP_STATUSES


class TestSafetyBoundary:
    def test_boundary_frozen_blocked_capabilities(self) -> None:
        b = WORKFLOW_SAFETY_BOUNDARY.to_safe_dict()
        for key in (
            "realProvider", "providerAutoWrite", "autonomousWrite", "writeExecute",
            "rollbackExecute", "shellCommand", "databaseMutation",
            "externalServiceWrite", "productionRollout",
        ):
            assert b[key] == "blocked"
        assert b["sandboxWritePreview"] == "allowed"
        assert b["rollbackReference"] == "allowed"
        assert b["fakeProvider"] == "allowed"
        assert b["manualApproval"] == "required"
        assert b["audit"] == "enabled"


class TestSanitizer:
    def test_redacts_secret_strings(self) -> None:
        assert redact_secret_strings("sk-" + "a" * 20) == "[REDACTED]"
        assert redact_secret_strings("Bearer abc123") == "[REDACTED]"
        assert redact_secret_strings("normal text") == "normal text"

    def test_drops_forbidden_keys(self) -> None:
        out = sanitize_workflow_value(
            {"apiKey": "x", "token": "y", "note": "safe", "nested": {"secret": "z"}}
        )
        assert "apiKey" not in out
        assert "token" not in out
        assert out["note"] == "safe"
        assert "secret" not in out["nested"]

    def test_rejects_callable_and_object_repr(self) -> None:
        out = sanitize_workflow_value({"repr": object()})
        assert out["repr"] is None

    def test_detects_unsafe_paths(self) -> None:
        assert contains_unsafe_path("/etc/passwd")
        assert contains_unsafe_path("~/secrets")
        assert contains_unsafe_path("../escape")
        assert contains_unsafe_path("file:///x")
        assert contains_unsafe_path("/Users/huangruibang/.hermes/x")
        assert contains_unsafe_path("state.db")
        assert not contains_unsafe_path("notes/example.md")


class TestDefinitionValidation:
    def _step(self) -> WorkflowStep:
        return WorkflowStep(
            step_id=new_workflow_id("wfs_"),
            step_type=STEP_READ_ONLY_TOOL,
            title="Read env",
            tool_id="dev_environment_read",
        )

    def test_valid_definition(self) -> None:
        d = WorkflowDefinition(
            workflow_id=new_workflow_id("wf_"),
            schema_version=WORKFLOW_SCHEMA_VERSION,
            title="Demo",
            description=None,
            created_at="2026-06-16T00:00:00+00:00",
            updated_at="2026-06-16T00:00:00+00:00",
            created_by="dev-webui",
            phase="3A",
            mode="dev_workflow_mvp",
            steps=(self._step(),),
            safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        )
        ok, reason = validate_workflow_definition(d)
        assert ok, reason

    def test_rejects_wrong_schema_version(self) -> None:
        d = WorkflowDefinition(
            workflow_id=new_workflow_id("wf_"),
            schema_version="wrong",
            title="Demo",
            description=None,
            created_at="", updated_at="", created_by="x", phase="3A", mode="m",
            steps=(self._step(),), safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        )
        ok, _ = validate_workflow_definition(d)
        assert not ok


def test_workflow_plan_created_event_type() -> None:
    assert EVENT_WORKFLOW_PLAN_CREATED in {
        "workflow_plan_created",
    }
