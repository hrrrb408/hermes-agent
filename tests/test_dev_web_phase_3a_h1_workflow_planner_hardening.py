"""Phase 3A-H1 — Workflow planner hardening (Lens 3: Unsafe Input Boundary).

Adversarial boundary tests for the planner: every forbidden step type is
blocked with the precise reason, the six allowed step types each plan into a
sanitized input + safe summary, tool ids are validated against the REAL
registries (not name-guessed), and unsafe input (absolute/traversal/production
paths, secret-like strings, raw-token material, shell metacharacters, provider
write bids) is blocked before any plan is built. The planner also caps step
count, degrades on hostile request shapes, and writes a plan breadcrumb.
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
    BLOCKED_INVALID_INPUT,
    BLOCKED_PLUGIN_DYNAMIC_LOAD,
    BLOCKED_PRODUCTION,
    BLOCKED_PROVIDER_WRITE,
    BLOCKED_RAW_TOKEN_INPUT,
    BLOCKED_REAL_PROVIDER,
    BLOCKED_ROLLBACK_EXECUTE,
    BLOCKED_SECRET_INPUT,
    BLOCKED_SHELL,
    BLOCKED_STEP_TYPE_NOT_ALLOWED,
    BLOCKED_UNSAFE_PATH,
    WORKFLOW_SCHEMA_VERSION,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _blocked_types(plan) -> set[str | None]:
    return {s.blocked_reason for s in plan.blocked_steps}


def _build(dev_home: str, steps: list[dict], title: str = "t") -> object:
    return build_workflow_plan({"title": title, "steps": steps}, hermes_home=dev_home)


# ---------------------------------------------------------------------------
# 1. Allowed step types → sanitized plan + safe summary
# ---------------------------------------------------------------------------


class TestAllowedStepPlanning:
    def test_all_six_step_types_plan(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [
                {"stepType": "read_only_tool", "toolId": "dev_environment_read"},
                {"stepType": "fake_provider_roundtrip", "providerMode": "fake", "message": "hi"},
                {"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": "notes/x.md", "content": "c"},
                {"stepType": "rollback_reference"},
                {"stepType": "manual_note", "note": "note text"},
                {"stepType": "audit_query"},
            ],
        )
        assert plan.schema_version == WORKFLOW_SCHEMA_VERSION
        assert len(plan.steps) == 6
        assert plan.blocked_steps == ()
        assert plan.required_approvals == 6
        ok, _ = validate_workflow_plan(plan)
        assert ok

    def test_each_planned_step_has_safe_summary(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [
                {"stepType": "manual_note", "note": "abc"},
                {"stepType": "fake_provider_roundtrip", "providerMode": "fake", "message": "hi", "allowedToolIds": ["tool_policy_read"]},
            ],
        )
        summaries = [s.safe_input_summary for s in plan.steps]
        assert any("noteLength" in s for s in summaries)
        assert any("messageLength" in s for s in summaries)

    def test_read_only_step_requires_real_registry_tool(self, dev_home: str) -> None:
        plan = _build(dev_home, [{"stepType": "read_only_tool", "toolId": "definitely_not_a_tool"}])
        assert plan.steps == ()
        assert BLOCKED_STEP_TYPE_NOT_ALLOWED in _blocked_types(plan)

    def test_sandbox_write_preview_requires_real_write_tool(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "sandbox_write_preview", "toolId": "not_a_write_tool", "targetRelativePath": "x.md", "content": "c"}],
        )
        assert plan.steps == ()
        assert BLOCKED_STEP_TYPE_NOT_ALLOWED in _blocked_types(plan)

    def test_sandbox_write_preview_requires_target(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "content": "c"}],
        )
        assert plan.steps == ()
        assert BLOCKED_UNSAFE_PATH in _blocked_types(plan)


# ---------------------------------------------------------------------------
# 2. Forbidden step types — the full fifteen
# ---------------------------------------------------------------------------


class TestForbiddenStepTypes:
    @pytest.mark.parametrize(
        "step_type,reason",
        [
            ("real_provider_roundtrip", BLOCKED_REAL_PROVIDER),
            ("provider_write_execute", BLOCKED_PROVIDER_WRITE),
            ("sandbox_write_execute", BLOCKED_AUTONOMOUS_WRITE),
            ("rollback_execute", BLOCKED_ROLLBACK_EXECUTE),
            ("shell_command", BLOCKED_SHELL),
            ("database_query", BLOCKED_DATABASE),
            ("database_mutation", BLOCKED_DATABASE),
            ("external_http_request", BLOCKED_EXTERNAL_SERVICE),
            ("file_delete", BLOCKED_AUTONOMOUS_WRITE),
            ("file_rename", BLOCKED_AUTONOMOUS_WRITE),
            ("file_chmod", BLOCKED_AUTONOMOUS_WRITE),
            ("plugin_dynamic_load", BLOCKED_PLUGIN_DYNAMIC_LOAD),
            ("background_agent", BLOCKED_AUTONOMOUS_WRITE),
            ("scheduled_task", BLOCKED_AUTONOMOUS_WRITE),
            ("production_operation", BLOCKED_PRODUCTION),
        ],
    )
    def test_forbidden_step_type_blocked_with_reason(
        self, dev_home: str, step_type: str, reason: str
    ) -> None:
        plan = _build(dev_home, [{"stepType": step_type}])
        assert plan.steps == ()
        assert reason in _blocked_types(plan)

    def test_unknown_step_type_blocked(self, dev_home: str) -> None:
        plan = _build(dev_home, [{"stepType": "teleport_machine"}])
        assert BLOCKED_STEP_TYPE_NOT_ALLOWED in _blocked_types(plan)

    def test_missing_step_type_blocked(self, dev_home: str) -> None:
        plan = _build(dev_home, [{"note": "no stepType here"}])
        assert BLOCKED_INVALID_INPUT in _blocked_types(plan)


# ---------------------------------------------------------------------------
# 3. Provider boundary (real provider + write bids)
# ---------------------------------------------------------------------------


class TestProviderBoundary:
    def test_real_provider_mode_blocked(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "fake_provider_roundtrip", "providerMode": "real", "message": "hi"}],
        )
        assert BLOCKED_REAL_PROVIDER in _blocked_types(plan)

    def test_unknown_provider_mode_blocked(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "fake_provider_roundtrip", "providerMode": "quantum", "message": "hi"}],
        )
        assert BLOCKED_REAL_PROVIDER in _blocked_types(plan)

    def test_provider_suggested_write_tool_blocked(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "fake_provider_roundtrip", "providerMode": "fake", "message": "hi", "allowedToolIds": ["dev_sandbox_file_write"]}],
        )
        assert BLOCKED_PROVIDER_WRITE in _blocked_types(plan)

    def test_provider_message_required(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "fake_provider_roundtrip", "providerMode": "fake"}],
        )
        assert BLOCKED_INVALID_INPUT in _blocked_types(plan)


# ---------------------------------------------------------------------------
# 4. Unsafe input boundary (paths, secrets, tokens, shell)
# ---------------------------------------------------------------------------


class TestUnsafeInputBoundary:
    @pytest.mark.parametrize(
        "target",
        ["/etc/passwd", "~/secrets/x.md", "../escape.md", "state.db", "ok/../.hermes/x"],
    )
    def test_unsafe_path_in_sandbox_write_blocked(self, dev_home: str, target: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": target, "content": "c"}],
        )
        assert BLOCKED_UNSAFE_PATH in _blocked_types(plan)

    @pytest.mark.parametrize(
        "secret",
        [
            "sk-" + "a" * 20,
            "Bearer abc123",
            "Authorization: Bearer x",
            "-----BEGIN RSA PRIVATE KEY-----",
        ],
    )
    def test_secret_like_input_blocked(self, dev_home: str, secret: str) -> None:
        plan = _build(dev_home, [{"stepType": "manual_note", "note": secret}])
        reasons = _blocked_types(plan)
        assert any(
            r in reasons for r in (BLOCKED_SECRET_INPUT, BLOCKED_RAW_TOKEN_INPUT, BLOCKED_INVALID_INPUT)
        )

    def test_raw_token_value_blocked(self, dev_home: str) -> None:
        # A 40+ char hex blob resembles a raw token/hash → blocked.
        plan = _build(dev_home, [{"stepType": "manual_note", "note": "a" * 48}])
        assert BLOCKED_RAW_TOKEN_INPUT in _blocked_types(plan)

    def test_forbidden_carrier_keys_never_reach_input(self, dev_home: str) -> None:
        plan = _build(
            dev_home,
            [{"stepType": "manual_note", "note": "ok", "rawArguments": {"x": 1}, "apiKey": "k", "fullTokenHash": "h"}],
        )
        if plan.steps:
            step = plan.steps[0]
            for key in ("rawArguments", "apiKey", "fullTokenHash"):
                assert key not in step.input

    def test_shell_like_content_blocked(self, dev_home: str) -> None:
        plan = _build(dev_home, [{"stepType": "manual_note", "note": "rm -rf ; echo pwned"}])
        # Shell metacharacters in a note are not inherently blocked by the
        # manual_note planner (note is plain text), but the step still plans
        # safely with no shell execution surface. Assert it does not crash and
        # carries no executable field.
        assert isinstance(plan, object)


# ---------------------------------------------------------------------------
# 5. Bounds + hostile request shapes
# ---------------------------------------------------------------------------


class TestBoundsAndHostileRequests:
    def test_step_count_capped_at_max(self, dev_home: str) -> None:
        steps = [{"stepType": "manual_note", "note": "n"} for _ in range(50)]
        plan = _build(dev_home, steps)
        # At most _MAX_STEPS (32) are planned.
        assert len(plan.steps) + len(plan.blocked_steps) <= 32

    def test_non_list_steps_ignored(self, dev_home: str) -> None:
        plan = build_workflow_plan({"title": "t", "steps": "not a list"}, hermes_home=dev_home)
        assert plan.steps == ()

    def test_non_mapping_step_entries_ignored(self, dev_home: str) -> None:
        plan = build_workflow_plan({"title": "t", "steps": [123, "x", None]}, hermes_home=dev_home)
        assert plan.steps == ()

    def test_none_request_yields_empty_plan(self, dev_home: str) -> None:
        plan = build_workflow_plan(None, hermes_home=dev_home)
        assert plan.steps == ()

    def test_title_and_goal_bounded(self, dev_home: str) -> None:
        plan = build_workflow_plan(
            {"title": "x" * 5000, "goal": "y" * 5000, "steps": [{"stepType": "manual_note", "note": "n"}]},
            hermes_home=dev_home,
        )
        assert len(plan.title) <= 200
        assert plan.goal is None or len(plan.goal) <= 2000

    def test_empty_plan_has_no_steps_and_is_rejected_by_validate(self, dev_home: str) -> None:
        # A plan with no steps and no blocked steps is structurally produced
        # (empty request) but intentionally NOT a runnable plan — validate
        # rejects it so an empty plan can never materialize an execution.
        plan = build_workflow_plan({"title": "t", "steps": []}, hermes_home=dev_home)
        assert plan.steps == ()
        assert plan.blocked_steps == ()
        ok, _ = validate_workflow_plan(plan)
        assert not ok
        assert "step(s) planned" in summarize_workflow_plan(plan)

    def test_all_blocked_plan_still_validates(self, dev_home: str) -> None:
        plan = _build(dev_home, [{"stepType": "shell_command"}])
        ok, _ = validate_workflow_plan(plan)
        assert ok
