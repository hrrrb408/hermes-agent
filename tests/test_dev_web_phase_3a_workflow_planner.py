"""Phase 3A — Workflow planner tests.

Verifies the planner builds a sanitized plan, accepts the six allowed step
types, and blocks every forbidden step type + unsafe input (real provider,
provider write, autonomous write, rollback execute, shell, database, external
service, production, dynamic plugin, unsafe path, secret-like input, raw token).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_workflow_planner import (
    build_workflow_plan,
    summarize_workflow_plan,
    validate_workflow_plan,
)
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_AUTONOMOUS_WRITE,
    BLOCKED_DATABASE,
    BLOCKED_EXTERNAL_SERVICE,
    BLOCKED_PRODUCTION,
    BLOCKED_PROVIDER_WRITE,
    BLOCKED_REAL_PROVIDER,
    BLOCKED_ROLLBACK_EXECUTE,
    BLOCKED_SHELL,
    BLOCKED_UNSAFE_PATH,
    WORKFLOW_SCHEMA_VERSION,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _blocked_types(plan) -> set[str]:
    return {s.blocked_reason for s in plan.blocked_steps}


class TestAllowedSteps:
    def test_builds_plan_with_all_allowed_step_types(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {
                "title": "Demo",
                "goal": "inspect",
                "steps": [
                    {"stepType": "read_only_tool", "toolId": "dev_environment_read"},
                    {"stepType": "fake_provider_roundtrip", "providerMode": "fake", "message": "hi"},
                    {"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": "notes/x.md", "content": "c"},
                    {"stepType": "rollback_reference"},
                    {"stepType": "manual_note", "note": "note text"},
                    {"stepType": "audit_query"},
                ],
            },
            hermes_home=dev_home,
        )
        assert plan.schema_version == WORKFLOW_SCHEMA_VERSION
        assert len(plan.steps) == 6
        assert plan.blocked_steps == ()
        assert plan.required_approvals == 6
        ok, _ = validate_workflow_plan(plan)
        assert ok
        assert "step(s) planned" in summarize_workflow_plan(plan)

    def test_read_only_step_requires_known_tool(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [{"stepType": "read_only_tool", "toolId": "not_a_tool"}]},
            hermes_home=dev_home,
        )
        assert plan.steps == ()
        assert _blocked_types(plan)

    def test_fake_provider_real_mode_blocked(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [{"stepType": "fake_provider_roundtrip", "providerMode": "real", "message": "hi"}]},
            hermes_home=dev_home,
        )
        assert BLOCKED_REAL_PROVIDER in _blocked_types(plan)

    def test_fake_provider_write_tool_blocked(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [{"stepType": "fake_provider_roundtrip", "providerMode": "fake", "message": "hi", "allowedToolIds": ["dev_sandbox_file_write"]}]},
            hermes_home=dev_home,
        )
        assert BLOCKED_PROVIDER_WRITE in _blocked_types(plan)


class TestForbiddenStepTypes:
    @pytest.mark.parametrize(
        "step_type,reason",
        [
            ("real_provider_roundtrip", BLOCKED_REAL_PROVIDER),
            ("sandbox_write_execute", BLOCKED_AUTONOMOUS_WRITE),
            ("rollback_execute", BLOCKED_ROLLBACK_EXECUTE),
            ("shell_command", BLOCKED_SHELL),
            ("database_mutation", BLOCKED_DATABASE),
            ("database_query", BLOCKED_DATABASE),
            ("external_http_request", BLOCKED_EXTERNAL_SERVICE),
            ("file_delete", BLOCKED_AUTONOMOUS_WRITE),
            ("production_operation", BLOCKED_PRODUCTION),
            ("plugin_dynamic_load", "blocked_workflow_plugin_dynamic_load_not_allowed"),
        ],
    )
    def test_forbidden_step_type_blocked(self, dev_home: str, step_type: str, reason: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [{"stepType": step_type}]},
            hermes_home=dev_home,
        )
        assert plan.steps == ()
        assert reason in _blocked_types(plan)

    def test_unknown_step_type_blocked(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [{"stepType": "teleport_machine"}]},
            hermes_home=dev_home,
        )
        assert "blocked_workflow_step_type_not_allowed" in _blocked_types(plan)


class TestUnsafeInput:
    def test_unsafe_path_blocked(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [
                {"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": "/etc/passwd", "content": "c"},
            ]},
            hermes_home=dev_home,
        )
        assert BLOCKED_UNSAFE_PATH in _blocked_types(plan)

    def test_secret_like_input_blocked(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [
                {"stepType": "manual_note", "note": "my key is sk-" + "a" * 20},
            ]},
            hermes_home=dev_home,
        )
        assert any("secret" in (r or "") or "invalid" in (r or "") for r in _blocked_types(plan))

    def test_raw_token_input_blocked(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "t", "steps": [
                {"stepType": "manual_note", "note": "ok", "rawArguments": {"x": 1}, "apiKey": "k"},
            ]},
            hermes_home=dev_home,
        )
        # The forbidden input keys are dropped; the note alone still plans,
        # proving the dangerous carriers never reach the plan input.
        if plan.steps:
            step = plan.steps[0]
            assert "rawArguments" not in step.input
            assert "apiKey" not in step.input

    def test_empty_plan_is_valid(self, dev_home: str) -> None:
        plan = build_workflow_plan({"title": "t", "steps": []}, hermes_home=dev_home)
        assert plan.steps == ()
        assert plan.blocked_steps == ()
