"""Tests for hermes_cli.dev_web_tool_handler_call — Clarify-only Handler Call.

Phase 1G-04-29: Clarify-only Handler Call + Post-execution Audit.

All tests verify:
  - Default-disabled: unset gate blocks the handler call
  - Explicit dev gate enables clarify-only handler call
  - Non-clarify canonicalName never invokes a handler
  - Dispatch plan existence is NOT handler-call permission
  - No tool handler imports / no provider imports / no dispatch runtime
  - No raw confirmationToken, full tokenHash, raw unredacted arguments, or
    secrets in any result
  - No callable object / function repr exposed
  - Provider Schema never sent, Provider API never called
  - All external side-effect flags always false
  - handlerCallId prefix is thc_
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.dev_web_tool_handler_call import (
    CLARIFY_MAX_CHOICES,
    CLARIFY_TOOL_TYPE,
    DECISION_BLOCKED_HANDLER_CALL_CANONICAL_NAME_MISMATCH,
    DECISION_BLOCKED_HANDLER_CALL_DISPATCH_PLAN_MISSING,
    DECISION_BLOCKED_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING,
    DECISION_BLOCKED_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH,
    DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY,
    DECISION_BLOCKED_HANDLER_CALL_PLAN_INVALID,
    DECISION_BLOCKED_HANDLER_CALL_REGISTRY_MISMATCH,
    DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK,
    DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED,
    ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH,
    ERROR_HANDLER_CALL_DISPATCH_PLAN_MISSING,
    ERROR_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING,
    ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH,
    ERROR_HANDLER_CALL_NOT_CLARIFY,
    ERROR_HANDLER_CALL_NOT_ENABLED,
    ERROR_HANDLER_CALL_PLAN_INVALID,
    ERROR_HANDLER_CALL_REGISTRY_MISMATCH,
    ERROR_HANDLER_CALL_SIDE_EFFECT_RISK,
    EXECUTION_STATUS_BLOCKED,
    EXECUTION_STATUS_COMPLETED,
    GATE_HANDLER_CALL_ENABLE,
    HANDLER_CALL_ID_PREFIX,
    HANDLER_CALL_PLAN_VERSION,
    HANDLER_CALL_SCHEMA_VERSION,
    HANDLER_CALL_STATUS_BLOCKED,
    HANDLER_CALL_STATUS_COMPLETED,
    HandlerCallPlan,
    HandlerCallResult,
    HANDLER_CALL_GATE_ENV,
    attempt_clarify_handler_call,
    build_handler_call_plan,
    generate_handler_call_id,
    is_handler_call_enabled,
    normalize_handler_result,
    safe_handler_call_summary,
    validate_handler_call_plan,
)
from hermes_cli.dev_web_tool_dispatch import build_dispatch_plan
from hermes_cli.dev_web_tool_handler_lookup import build_handler_descriptor


# ===================================================================
# Helpers
# ===================================================================


def _clarify_descriptor() -> dict:
    desc = build_handler_descriptor("clarify")
    assert desc is not None
    return desc


def _clarify_dispatch_plan(handler_lookup_id: str = "hl_test") -> dict:
    r = build_dispatch_plan(
        canonical_name="clarify",
        handler_lookup_id=handler_lookup_id,
        handler_descriptor=_clarify_descriptor(),
        toolset_name="builtin",
    )
    assert r.built is True
    assert r.dispatch_plan is not None
    return r.dispatch_plan


def _gate_enabled():
    return patch.dict(os.environ, {HANDLER_CALL_GATE_ENV: "true"}, clear=False)


def _gate_unset():
    """Context manager ensuring the handler-call gate env var is unset."""
    return patch.dict(os.environ, {}, clear=False)


def _pop_gate():
    os.environ.pop(HANDLER_CALL_GATE_ENV, None)


def _attempt(**overrides):
    """Call attempt_clarify_handler_call with sensible defaults."""
    defaults = dict(
        canonical_name="clarify",
        handler_descriptor=_clarify_descriptor(),
        dispatch_plan=_clarify_dispatch_plan(),
        handler_lookup_id="hl_test",
        dispatch_id="dsp_test",
        execute_request_id="exe_test",
        pre_execution_audit_id="pea_test",
        arguments={"question": "Which option?", "choices": ["a", "b"]},
    )
    defaults.update(overrides)
    return attempt_clarify_handler_call(**defaults)


# ===================================================================
# 1. Default-disabled gate tests
# ===================================================================


class TestDefaultDisabledGate:
    """Verify the handler call is default-disabled."""

    def test_default_unset_blocks(self) -> None:
        with _gate_unset():
            _pop_gate()
            assert is_handler_call_enabled() is False
            result = _attempt()
        assert result.called is False
        assert result.handler_call_status == HANDLER_CALL_STATUS_BLOCKED
        assert result.execution_status == EXECUTION_STATUS_BLOCKED
        assert result.error_code == ERROR_HANDLER_CALL_NOT_ENABLED
        assert result.decision == DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED
        assert result.gate == GATE_HANDLER_CALL_ENABLE

    def test_default_unset_blocks_with_full_valid_chain(self) -> None:
        """Even with all upstream fields valid, unset gate blocks."""
        with _gate_unset():
            _pop_gate()
            result = _attempt()
        assert result.called is False
        assert result.tool_result is None
        assert result.handler_call_id is None

    def test_empty_value_blocks(self) -> None:
        with patch.dict(os.environ, {HANDLER_CALL_GATE_ENV: ""}, clear=False):
            result = _attempt()
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_NOT_ENABLED

    def test_true_uppercase_blocks(self) -> None:
        with patch.dict(os.environ, {HANDLER_CALL_GATE_ENV: "TRUE"}, clear=False):
            result = _attempt()
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_NOT_ENABLED

    def test_one_blocks(self) -> None:
        with patch.dict(os.environ, {HANDLER_CALL_GATE_ENV: "1"}, clear=False):
            result = _attempt()
        assert result.called is False

    def test_yes_blocks(self) -> None:
        with patch.dict(os.environ, {HANDLER_CALL_GATE_ENV: "yes"}, clear=False):
            result = _attempt()
        assert result.called is False

    def test_false_blocks(self) -> None:
        with patch.dict(os.environ, {HANDLER_CALL_GATE_ENV: "false"}, clear=False):
            result = _attempt()
        assert result.called is False


# ===================================================================
# 2. Explicit-enabled clarify-only tests
# ===================================================================


class TestExplicitEnabledClarify:
    """Verify the explicit dev gate enables clarify-only handler call."""

    def test_explicit_enabled_completes_clarify(self) -> None:
        with _gate_enabled():
            result = _attempt()
        assert result.called is True
        assert result.handler_call_status == HANDLER_CALL_STATUS_COMPLETED
        assert result.execution_status == EXECUTION_STATUS_COMPLETED
        assert result.canonical_name == "clarify"
        assert result.error_code is None
        assert result.decision is None

    def test_handler_call_id_prefix_is_thc(self) -> None:
        with _gate_enabled():
            result = _attempt()
        assert result.called is True
        assert result.handler_call_id is not None
        assert result.handler_call_id.startswith(HANDLER_CALL_ID_PREFIX)
        assert result.handler_call_id.startswith("thc_")
        suffix = result.handler_call_id[len(HANDLER_CALL_ID_PREFIX):]
        assert len(suffix) > 0

    def test_handler_call_id_is_unique(self) -> None:
        ids = []
        with _gate_enabled():
            for _ in range(10):
                result = _attempt()
                assert result.called is True
                ids.append(result.handler_call_id)
        assert len(set(ids)) == len(ids)

    def test_tool_result_is_normalized_clarify_envelope(self) -> None:
        with _gate_enabled():
            result = _attempt(arguments={"question": "Pick one", "choices": ["x", "y"]})
        assert result.called is True
        assert result.tool_result is not None
        assert result.tool_result["type"] == "clarify"
        assert result.tool_result["message"] == "Pick one"
        assert isinstance(result.tool_result["questions"], list)
        assert len(result.tool_result["questions"]) == 2
        assert result.tool_result["questions"][0]["label"] == "x"

    def test_open_ended_clarify_has_empty_questions(self) -> None:
        with _gate_enabled():
            result = _attempt(arguments={"question": "What now?"})
        assert result.called is True
        assert result.tool_result["questions"] == []

    def test_choices_bounded_to_max(self) -> None:
        many = [f"c{i}" for i in range(CLARIFY_MAX_CHOICES + 5)]
        with _gate_enabled():
            result = _attempt(arguments={"question": "q", "choices": many})
        assert result.called is True
        assert len(result.tool_result["questions"]) == CLARIFY_MAX_CHOICES

    def test_missing_question_uses_safe_default(self) -> None:
        with _gate_enabled():
            result = _attempt(arguments={"choices": ["a"]})
        assert result.called is True
        assert isinstance(result.tool_result["message"], str)
        assert result.tool_result["message"]


# ===================================================================
# 3. Clarify-only enforcement tests
# ===================================================================


class TestClarifyOnly:
    """Verify non-clarify canonicalName never invokes a handler."""

    def test_non_clarify_blocks_even_when_gate_enabled(self) -> None:
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="read_file",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=_clarify_dispatch_plan(),
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_NOT_CLARIFY
        assert result.decision == DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY

    def test_non_clarify_does_not_produce_tool_result(self) -> None:
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="web_search",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=_clarify_dispatch_plan(),
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.tool_result is None
        assert result.handler_call_id is None


# ===================================================================
# 4. Consistency / dispatch plan tests
# ===================================================================


class TestConsistencyGates:
    """Verify consistency gates block before handler call."""

    def test_dispatch_plan_missing_blocks(self) -> None:
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=None,
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_DISPATCH_PLAN_MISSING
        assert result.decision == DECISION_BLOCKED_HANDLER_CALL_DISPATCH_PLAN_MISSING

    def test_handler_descriptor_missing_blocks(self) -> None:
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=None,
                dispatch_plan=_clarify_dispatch_plan(),
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING
        assert (
            result.decision == DECISION_BLOCKED_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING
        )

    def test_dispatch_plan_canonical_name_mismatch_blocks(self) -> None:
        plan = _clarify_dispatch_plan()
        bad_plan = dict(plan)
        bad_plan["canonicalName"] = "read_file"
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=bad_plan,
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH
        assert result.decision == DECISION_BLOCKED_HANDLER_CALL_CANONICAL_NAME_MISMATCH

    def test_handler_lookup_id_mismatch_blocks(self) -> None:
        plan = _clarify_dispatch_plan(handler_lookup_id="hl_real")
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=plan,
                handler_lookup_id="hl_different",  # mismatch
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH
        assert result.decision == DECISION_BLOCKED_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH

    def test_descriptor_canonical_name_mismatch_blocks(self) -> None:
        desc = _clarify_descriptor()
        bad_desc = dict(desc)
        bad_desc["canonicalName"] = "read_file"
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=bad_desc,
                dispatch_plan=_clarify_dispatch_plan(),
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH

    def test_registry_key_mismatch_blocks(self) -> None:
        desc = _clarify_descriptor()
        bad_desc = dict(desc)
        bad_desc["registryKey"] = "not_clarify"
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=bad_desc,
                dispatch_plan=_clarify_dispatch_plan(),
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_REGISTRY_MISMATCH
        assert result.decision == DECISION_BLOCKED_HANDLER_CALL_REGISTRY_MISMATCH

    def test_side_effect_risk_in_dispatch_plan_blocks(self) -> None:
        plan = _clarify_dispatch_plan()
        bad_plan = dict(plan)
        bad_plan["toolHandlerCallAllowed"] = True  # unsafe
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="clarify",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=bad_plan,
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        assert result.called is False
        assert result.error_code == ERROR_HANDLER_CALL_SIDE_EFFECT_RISK
        assert result.decision == DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK


# ===================================================================
# 5. Side-effect invariants (provider disabled)
# ===================================================================


class TestSideEffectInvariants:
    """Verify all side-effect / provider flags stay false."""

    def test_external_side_effects_false_on_success(self) -> None:
        with _gate_enabled():
            result = _attempt()
        assert result.called is True
        assert result.side_effects["externalSideEffects"] is False
        assert result.side_effects["providerSchemaSent"] is False
        assert result.side_effects["providerApiCalled"] is False
        assert result.side_effects["filesystemChanged"] is False
        assert result.side_effects["networkCalled"] is False

    def test_provider_schema_never_sent(self) -> None:
        with _gate_enabled():
            result = _attempt()
        assert result.side_effects["providerSchemaSent"] is False

    def test_provider_api_never_called(self) -> None:
        with _gate_enabled():
            result = _attempt()
        assert result.side_effects["providerApiCalled"] is False

    def test_side_effects_false_on_block(self) -> None:
        with _gate_enabled():
            result = attempt_clarify_handler_call(
                canonical_name="read_file",
                handler_descriptor=_clarify_descriptor(),
                dispatch_plan=_clarify_dispatch_plan(),
                handler_lookup_id="hl_test",
                dispatch_id="dsp_test",
            )
        for _k, v in result.side_effects.items():
            assert v is False


# ===================================================================
# 6. Security / no-secret tests
# ===================================================================


class TestSecurityInvariants:
    """Verify no secrets / raw token / raw arguments / callable exposure."""

    def _result_text(self) -> str:
        with _gate_enabled():
            result = _attempt(
                arguments={
                    "question": "Which option?",
                    "choices": ["a", "b"],
                    "api_key": "sk-should_not_appear1234567",
                    "token": "should_not_appear",
                },
            )
        assert result.called is True
        full = {
            "tool_result": result.tool_result,
            "side_effects": result.side_effects,
            "handler_call_id": result.handler_call_id,
            "safe_summary": result.safe_summary,
        }
        return json.dumps(full)

    def test_raw_token_never_in_result(self) -> None:
        text = self._result_text()
        assert "confirmationToken" not in text
        assert "rawToken" not in text
        assert "raw_token" not in text

    def test_full_token_hash_never_in_result(self) -> None:
        text = self._result_text()
        assert "tokenHash" not in text
        assert "token_hash" not in text

    def test_provider_credentials_excluded(self) -> None:
        # api_key field is dropped (not a clarify field); secret patterns redacted
        with _gate_enabled():
            result = _attempt(
                arguments={
                    "question": "q",
                    "api_key": "sk-abcdef1234567890",
                },
            )
        text = json.dumps(result.tool_result)
        assert "sk-abcdef1234567890" not in text

    def test_secret_question_value_redacted(self) -> None:
        with _gate_enabled():
            result = _attempt(arguments={"question": "sk-abcdef1234567890"})
        # Secret-looking question text is redacted
        assert result.tool_result["message"] != "sk-abcdef1234567890"

    def test_no_callable_object_in_result(self) -> None:
        with _gate_enabled():
            result = _attempt()
        full = {
            "tool_result": result.tool_result,
            "side_effects": result.side_effects,
            "safe_summary": result.safe_summary,
        }
        def _walk(obj):
            if callable(obj):
                return True
            if isinstance(obj, dict):
                return any(_walk(v) for v in obj.values())
            if isinstance(obj, list):
                return any(_walk(v) for v in obj)
            return False
        assert _walk(full) is False

    def test_no_function_repr_in_result(self) -> None:
        text = self._result_text()
        assert "<function" not in text
        assert "callable" not in text.lower()

    def test_does_not_import_tool_handlers(self) -> None:
        import hermes_cli.dev_web_tool_handler_call as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from tools." not in line, f"Unexpected import: {line}"
            assert "from agent." not in line, f"Unexpected import: {line}"

    def test_does_not_import_provider(self) -> None:
        import hermes_cli.dev_web_tool_handler_call as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source

    def test_does_not_import_subprocess_or_socket(self) -> None:
        import hermes_cli.dev_web_tool_handler_call as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "import socket" not in source
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "import urllib" not in source


# ===================================================================
# 7. Plan builder / validation tests
# ===================================================================


class TestPlanBuilderAndValidation:
    """Verify build_handler_call_plan + validate_handler_call_plan."""

    def test_build_plan_returns_plan(self) -> None:
        plan, err = build_handler_call_plan(
            canonical_name="clarify",
            handler_descriptor=_clarify_descriptor(),
            dispatch_plan=_clarify_dispatch_plan(),
            handler_lookup_id="hl_test",
            dispatch_id="dsp_test",
            arguments={"question": "q"},
        )
        assert plan is not None
        assert err == (None, None, None)
        assert isinstance(plan, HandlerCallPlan)
        assert plan.canonical_name == "clarify"
        assert plan.normalized_arguments == {"question": "q"}

    def test_build_plan_drops_non_clarify_fields(self) -> None:
        plan, _ = build_handler_call_plan(
            canonical_name="clarify",
            handler_descriptor=_clarify_descriptor(),
            dispatch_plan=_clarify_dispatch_plan(),
            handler_lookup_id="hl_test",
            dispatch_id="dsp_test",
            arguments={"question": "q", "api_key": "secret", "extra": "dropped"},
        )
        assert plan is not None
        assert "api_key" not in plan.normalized_arguments
        assert "extra" not in plan.normalized_arguments
        assert "question" in plan.normalized_arguments

    def test_validate_plan_success(self) -> None:
        plan, _ = build_handler_call_plan(
            canonical_name="clarify",
            handler_descriptor=_clarify_descriptor(),
            dispatch_plan=_clarify_dispatch_plan(),
            handler_lookup_id="hl_test",
            dispatch_id="dsp_test",
        )
        assert plan is not None
        assert validate_handler_call_plan(
            plan,
            expected_canonical_name="clarify",
            expected_handler_lookup_id="hl_test",
            expected_registry_key="clarify",
        ) is None

    def test_validate_plan_non_clarify_fails(self) -> None:
        plan = HandlerCallPlan(
            canonical_name="read_file",
            handler_lookup_id="hl_test",
            dispatch_id="dsp_test",
            handler_id="handler_clarify",
            registry_key="clarify",
            execute_request_id=None,
            pre_execution_audit_id=None,
            normalized_arguments={},
            handler_call_plan_version=HANDLER_CALL_PLAN_VERSION,
        )
        assert validate_handler_call_plan(plan) == ERROR_HANDLER_CALL_NOT_CLARIFY

    def test_plan_to_safe_dict_has_no_secrets(self) -> None:
        plan, _ = build_handler_call_plan(
            canonical_name="clarify",
            handler_descriptor=_clarify_descriptor(),
            dispatch_plan=_clarify_dispatch_plan(),
            handler_lookup_id="hl_test",
            dispatch_id="dsp_test",
            arguments={"question": "safe question"},
        )
        d = plan.to_safe_dict()
        text = json.dumps(d)
        assert "secret" not in text.lower()
        assert "token" not in text.lower() or "audit" in text.lower()


# ===================================================================
# 8. Result dataclass / summary / constants tests
# ===================================================================


class TestResultAndSummary:
    """Verify HandlerCallResult immutability + safe summary builder."""

    def test_result_is_frozen(self) -> None:
        with _gate_enabled():
            result = _attempt()
        with pytest.raises(AttributeError):
            result.called = False  # type: ignore[misc]

    def test_plan_is_frozen(self) -> None:
        plan, _ = build_handler_call_plan(
            canonical_name="clarify",
            handler_descriptor=_clarify_descriptor(),
            dispatch_plan=_clarify_dispatch_plan(),
            handler_lookup_id="hl_test",
            dispatch_id="dsp_test",
        )
        with pytest.raises(AttributeError):
            plan.canonical_name = "other"  # type: ignore[misc]

    def test_safe_summary_fields(self) -> None:
        summary = safe_handler_call_summary(
            handler_call_id="thc_abc",
            handler_call_status=HANDLER_CALL_STATUS_COMPLETED,
            execution_status=EXECUTION_STATUS_COMPLETED,
            canonical_name="clarify",
        )
        assert summary["handlerCallId"] == "thc_abc"
        assert summary["handlerCallStatus"] == "completed"
        assert summary["executionStatus"] == "completed"
        assert summary["canonicalName"] == "clarify"

    def test_safe_summary_no_secrets(self) -> None:
        summary = safe_handler_call_summary(
            handler_call_id="thc_abc",
            handler_call_status=HANDLER_CALL_STATUS_COMPLETED,
            execution_status=EXECUTION_STATUS_COMPLETED,
        )
        text = json.dumps(summary)
        assert "secret" not in text.lower()
        assert "password" not in text.lower()

    def test_constants(self) -> None:
        assert HANDLER_CALL_ID_PREFIX == "thc_"
        assert CLARIFY_TOOL_TYPE == "clarify"
        assert CLARIFY_MAX_CHOICES == 4
        assert HANDLER_CALL_SCHEMA_VERSION >= 1
        assert HANDLER_CALL_PLAN_VERSION >= 1
        assert HANDLER_CALL_STATUS_COMPLETED == "completed"
        assert HANDLER_CALL_STATUS_BLOCKED == "blocked"
        assert EXECUTION_STATUS_COMPLETED == "completed"
        assert EXECUTION_STATUS_BLOCKED == "blocked"

    def test_generate_handler_call_id_prefix(self) -> None:
        hid = generate_handler_call_id()
        assert hid.startswith(HANDLER_CALL_ID_PREFIX)

    def test_generate_handler_call_id_unique(self) -> None:
        ids = [generate_handler_call_id() for _ in range(20)]
        assert len(set(ids)) == len(ids)

    def test_normalize_handler_result_redacts_secrets(self) -> None:
        normalized = normalize_handler_result(
            handler_call_id="thc_x",
            canonical_name="clarify",
            raw_tool_result={"type": "clarify", "message": "sk-abcdef1234567890", "questions": []},
        )
        assert normalized["message"] != "sk-abcdef1234567890"
        assert normalized["type"] == "clarify"


# ===================================================================
# 9. STATIC_ALLOWLIST unchanged tests
# ===================================================================


class TestStaticAllowlistUnchanged:
    """Verify handler call never mutates STATIC_ALLOWLIST."""

    def test_allowlist_remains_clarify_only(self) -> None:
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST
        before = frozenset(STATIC_ALLOWLIST)
        with _gate_enabled():
            _attempt()
        with _gate_unset():
            _pop_gate()
            _attempt()
        assert STATIC_ALLOWLIST == before
        assert STATIC_ALLOWLIST == frozenset({"clarify"})
