"""Phase 3A-H1 — Workflow schema hardening (Lens 1: Step Type Boundary).

Adversarial boundary tests for ``workflow_schema_v1``: the schema version is an
immutable literal, the allowed/forbidden step-type sets are frozen, disjoint,
and complete (every forbidden step type maps to a precise blocked reason), the
forbidden-input-key carrier list covers the full brief, and the sanitizer is
deep, side-effect-free, and never raises on hostile input (bytes, sets, custom
objects, deep nesting, cyclic-shaped depth).

These tests pin the contract so a regression that widens the step-type surface,
drops a forbidden carrier, or weakens redaction is caught immediately.
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_workflow_schema import (
    ALLOWED_PROVIDER_MODES,
    ALLOWED_STEP_TYPES,
    BLOCKED_AUTONOMOUS_WRITE,
    BLOCKED_DATABASE,
    BLOCKED_EXTERNAL_SERVICE,
    BLOCKED_PLUGIN_DYNAMIC_LOAD,
    BLOCKED_PRODUCTION,
    BLOCKED_PROVIDER_WRITE,
    BLOCKED_REAL_PROVIDER,
    BLOCKED_ROLLBACK_EXECUTE,
    BLOCKED_SHELL,
    FORBIDDEN_STEP_BLOCKED_REASONS,
    FORBIDDEN_STEP_TYPES,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_FAKE,
    PROVIDER_MODE_REAL,
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    VALID_STEP_STATUSES,
    VALID_WORKFLOW_EVENT_TYPES,
    WORKFLOW_BLOCKED_REASONS,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowDefinition,
    WorkflowStep,
    blocked_reason_for_step_type,
    coerce_bounded_string,
    contains_secret_material,
    contains_unsafe_path,
    is_allowed_step_type,
    is_forbidden_input_key,
    is_forbidden_step_type,
    is_shell_like,
    is_valid_workflow_event_type,
    is_valid_workflow_id,
    new_workflow_id,
    redact_secret_strings,
    sanitize_workflow_value,
    validate_workflow_definition,
)


# ---------------------------------------------------------------------------
# 1. Schema version + id generation (immutable literal + id contract)
# ---------------------------------------------------------------------------


class TestSchemaVersionAndIds:
    def test_schema_version_is_the_immutable_v1_literal(self) -> None:
        assert WORKFLOW_SCHEMA_VERSION == "workflow_schema_v1"

    def test_every_id_prefix_round_trips_validation(self) -> None:
        for prefix in ("wf_", "wfp_", "wfs_", "wfx_", "wfa_", "wfap_"):
            wid = new_workflow_id(prefix)
            assert is_valid_workflow_id(wid, prefix)
            # Each generated id is hex-suffixed and of bounded length.
            assert wid[len(prefix):].replace("0", "a").isalnum()

    @pytest.mark.parametrize(
        "bad",
        [
            "", "not-an-id", "wf_short", "wf__uppercase", "WF_" + "a" * 20,
            "wf_" + "g" * 20, "wf_" + "a" * 11, None, 123, [], {},
        ],
    )
    def test_invalid_ids_rejected(self, bad: object) -> None:
        assert not is_valid_workflow_id(bad, "wf_")

    def test_id_wrong_prefix_rejected(self) -> None:
        good = new_workflow_id("wfs_")
        assert not is_valid_workflow_id(good, "wfx_")


# ---------------------------------------------------------------------------
# 2. Step-type boundary (frozen, disjoint, complete)
# ---------------------------------------------------------------------------


class TestStepTypeBoundary:
    def test_exactly_six_allowed_step_types(self) -> None:
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

    def test_allowed_and_forbidden_are_disjoint(self) -> None:
        # No step type may be both allowed and forbidden (an ambiguous type would
        # be a safety hole).
        assert not (ALLOWED_STEP_TYPES & FORBIDDEN_STEP_TYPES)

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
    def test_every_forbidden_step_type_blocks_with_precise_reason(
        self, step_type: str, reason: str
    ) -> None:
        assert is_forbidden_step_type(step_type)
        assert not is_allowed_step_type(step_type)
        assert blocked_reason_for_step_type(step_type) == reason
        # The full forbidden map has an entry for every forbidden type.
        assert FORBIDDEN_STEP_BLOCKED_REASONS[step_type] == reason

    def test_forbidden_map_covers_every_forbidden_type(self) -> None:
        assert set(FORBIDDEN_STEP_BLOCKED_REASONS) == set(FORBIDDEN_STEP_TYPES)

    def test_unknown_step_type_is_neither_allowed_nor_forbidden(self) -> None:
        for t in ("teleport_machine", "", "READ_ONLY_TOOL", "read_only_tool "):
            assert not is_allowed_step_type(t)
            assert not is_forbidden_step_type(t)
            assert blocked_reason_for_step_type(t) is None

    def test_non_string_step_type_rejected(self) -> None:
        for t in (None, 1, [], object()):
            assert not is_allowed_step_type(t)
            assert not is_forbidden_step_type(t)


class TestProviderModeBoundary:
    def test_real_provider_mode_is_not_allowed(self) -> None:
        assert PROVIDER_MODE_REAL not in ALLOWED_PROVIDER_MODES

    def test_disabled_and_fake_are_the_only_allowed_modes(self) -> None:
        assert ALLOWED_PROVIDER_MODES == frozenset(
            {PROVIDER_MODE_DISABLED, PROVIDER_MODE_FAKE}
        )


# ---------------------------------------------------------------------------
# 3. Blocked-reason catalogue + event-type vocabulary
# ---------------------------------------------------------------------------


class TestBlockedReasonAndEventVocabulary:
    def test_every_blocked_reason_is_workflow_prefixed(self) -> None:
        for code in WORKFLOW_BLOCKED_REASONS:
            assert code.startswith("blocked_workflow_")

    def test_all_forbidden_reasons_are_in_the_catalogue(self) -> None:
        catalogue = set(WORKFLOW_BLOCKED_REASONS)
        for reason in FORBIDDEN_STEP_BLOCKED_REASONS.values():
            assert reason in catalogue

    def test_every_event_type_is_workflow_prefixed_and_valid(self) -> None:
        for ev in VALID_WORKFLOW_EVENT_TYPES:
            assert ev.startswith("workflow_")
            assert is_valid_workflow_event_type(ev)

    @pytest.mark.parametrize(
        "ev",
        [
            "workflow_plan_created", "workflow_plan_blocked",
            "workflow_execution_created", "workflow_step_preview_created",
            "workflow_step_approval_created", "workflow_step_approval_used",
            "workflow_step_started", "workflow_step_completed",
            "workflow_step_blocked", "workflow_step_failed",
            "workflow_timeline_updated", "workflow_execution_completed",
        ],
    )
    def test_required_audit_event_type_present(self, ev: str) -> None:
        assert is_valid_workflow_event_type(ev)

    def test_unknown_event_type_rejected(self) -> None:
        assert not is_valid_workflow_event_type("workflow_evil")
        assert not is_valid_workflow_event_type(None)


class TestStatusLifecycle:
    def test_full_status_set_present(self) -> None:
        for s in (
            "draft", "planned", "previewed", "approval_required", "approved",
            "ready", "running", "completed", "blocked", "failed", "skipped",
        ):
            assert s in VALID_STEP_STATUSES


# ---------------------------------------------------------------------------
# 4. Forbidden input-key carrier coverage
# ---------------------------------------------------------------------------


class TestForbiddenInputCarriers:
    @pytest.mark.parametrize(
        "key",
        [
            "rawArguments", "rawArgs", "fullTokenHash", "tokenSecret",
            "plainToken", "rawToken", "apiKey", "api_key", "authorization",
            "bearer", "password", "secret", "credential", "cookie",
            "callable", "handler", "sourcePath", "absolutePath",
            "API-KEY", "Api_Key", "client_secret", "access_token",
            "refresh_token", "private_key",
        ],
    )
    def test_required_carriers_are_forbidden(self, key: str) -> None:
        assert is_forbidden_input_key(key), key

    def test_safe_keys_are_allowed(self) -> None:
        for key in ("note", "message", "targetRelativePath", "toolId", "stepType", "limit"):
            assert not is_forbidden_input_key(key), key

    def test_non_string_key_is_forbidden(self) -> None:
        assert is_forbidden_input_key(None)
        assert is_forbidden_input_key(123)


# ---------------------------------------------------------------------------
# 5. Sanitizer (deep, side-effect-free, never raises)
# ---------------------------------------------------------------------------


class TestSanitizerDepth:
    def test_redacts_nested_secret_strings(self) -> None:
        out = redact_secret_strings({"a": {"b": ["sk-" + "a" * 20, "ok"]}})
        assert out["a"]["b"][0] == "[REDACTED]"
        assert out["a"]["b"][1] == "ok"

    def test_redacts_tuple_and_list_uniformly(self) -> None:
        assert redact_secret_strings(("sk-" + "a" * 20,)) == ("[REDACTED]",)
        assert redact_secret_strings(["Bearer xyz"]) == ["[REDACTED]"]

    @pytest.mark.parametrize(
        "secret",
        [
            "sk-" + "a" * 20,
            "Bearer abc123",
            "Authorization: Bearer x",
            "-----BEGIN RSA PRIVATE KEY-----",
        ],
    )
    def test_secret_detection(self, secret: str) -> None:
        assert contains_secret_material({"x": secret})

    def test_drops_forbidden_keys_at_every_depth(self) -> None:
        out = sanitize_workflow_value(
            {"note": "safe", "apiKey": "k", "nested": {"tokenSecret": "z", "ok": 1}}
        )
        assert "apiKey" not in out
        assert "tokenSecret" not in out["nested"]
        assert out["note"] == "safe"
        assert out["nested"]["ok"] == 1

    def test_rejects_callable_and_object_repr(self) -> None:
        out = sanitize_workflow_value({"repr": object(), "fn": lambda: None})
        assert out["repr"] is None
        assert out["fn"] is None

    def test_never_raises_on_hostile_input(self) -> None:
        # bytes, sets, custom objects, deeply nested — the sanitizer degrades
        # safely and never raises.
        class Weird:
            pass

        hostile = {
            "b": b"bytes", "s": {1, 2, 3}, "o": Weird(), "nested": {"deep": {"x": [object()]}},
        }
        out = sanitize_workflow_value(hostile)
        assert isinstance(out, dict)
        # bytes / sets / objects reduce to None (non JSON-native).
        assert out["b"] is None
        assert out["s"] is None

    def test_depth_is_bounded(self) -> None:
        # A pathologically deep structure collapses past the depth bound.
        deep: dict = {}
        cur = deep
        for _ in range(20):
            cur["n"] = {}
            cur = cur["n"]
        out = sanitize_workflow_value({"root": deep})
        assert isinstance(out, dict)

    def test_primitive_passthrough(self) -> None:
        assert sanitize_workflow_value(5) == 5
        assert sanitize_workflow_value(3.14) == 3.14
        assert sanitize_workflow_value(True) is True
        assert sanitize_workflow_value(None) is None


class TestPathAndShellDetection:
    @pytest.mark.parametrize(
        "value",
        [
            "/etc/passwd", "~/secrets", "../escape", "file:///x",
            "/Users/huangruibang/.hermes/x", "state.db", "\\\\windows\\share",
            "notes/../secret", "ok/../.hermes",
        ],
    )
    def test_unsafe_path_detected(self, value: str) -> None:
        assert contains_unsafe_path(value)

    @pytest.mark.parametrize("value", ["notes/example.md", "workflow-demo/x.md", "example"])
    def test_safe_relative_path_allowed(self, value: str) -> None:
        assert not contains_unsafe_path(value)
        assert not is_shell_like(value)

    @pytest.mark.parametrize("ch", list("|;`$><&\n\r"))
    def test_shell_metacharacters_detected(self, ch: str) -> None:
        assert is_shell_like(f"cmd{ch}rm")

    def test_shell_like_rejects_non_string(self) -> None:
        assert not is_shell_like(None)
        assert not is_shell_like(123)


class TestBoundedString:
    def test_truncates_long_strings(self) -> None:
        assert coerce_bounded_string("a" * 500, max_length=10) == "a" * 10

    def test_rejects_non_string_and_empty(self) -> None:
        assert coerce_bounded_string(None, max_length=10) is None
        assert coerce_bounded_string("   ", max_length=10) is None
        assert coerce_bounded_string(123, max_length=10) is None

    def test_rejects_secret_laden_string(self) -> None:
        assert coerce_bounded_string("sk-" + "a" * 20, max_length=100) is None


# ---------------------------------------------------------------------------
# 6. Definition validation (structural)
# ---------------------------------------------------------------------------


def _step() -> WorkflowStep:
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_READ_ONLY_TOOL,
        title="Read env",
        tool_id="dev_environment_read",
    )


def _definition(**overrides: object) -> WorkflowDefinition:
    base: dict[str, object] = {
        "workflow_id": new_workflow_id("wf_"),
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "title": "Demo",
        "description": None,
        "created_at": "2026-06-16T00:00:00+00:00",
        "updated_at": "2026-06-16T00:00:00+00:00",
        "created_by": "dev-webui",
        "phase": "3A",
        "mode": "dev_workflow_mvp",
        "steps": (_step(),),
        "safety_boundary": WORKFLOW_SAFETY_BOUNDARY,
    }
    base.update(overrides)
    return WorkflowDefinition(**base)  # type: ignore[arg-type]


class TestDefinitionValidation:
    def test_valid_definition_passes(self) -> None:
        ok, reason = validate_workflow_definition(_definition())
        assert ok, reason

    def test_rejects_non_definition(self) -> None:
        ok, _ = validate_workflow_definition({"not": "a definition"})  # type: ignore[arg-type]
        assert not ok

    def test_rejects_wrong_schema_version(self) -> None:
        ok, _ = validate_workflow_definition(_definition(schema_version="v2"))
        assert not ok

    def test_rejects_malformed_workflow_id(self) -> None:
        ok, _ = validate_workflow_definition(_definition(workflow_id="bad"))
        assert not ok

    def test_rejects_empty_or_overlong_title(self) -> None:
        assert not validate_workflow_definition(_definition(title=""))[0]
        assert not validate_workflow_definition(_definition(title="x" * 500))[0]

    def test_rejects_no_steps(self) -> None:
        assert not validate_workflow_definition(_definition(steps=()))[0]

    def test_rejects_duplicate_step_ids(self) -> None:
        s = _step()
        assert not validate_workflow_definition(_definition(steps=(s, s)))[0]

    def test_rejects_non_allowed_step_type(self) -> None:
        bad = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type="shell_command", title="bad"
        )
        assert not validate_workflow_definition(_definition(steps=(bad,)))[0]
