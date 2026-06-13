"""Tests for hermes_cli.dev_web_tool_dispatch — Dispatch Minimal Implementation.

Phase 1G-04-28: Dispatch Minimal Implementation / Still Blocked-Only.

All tests verify:
  - Safe dispatch plan / envelope construction only — no handler invocation
  - No tool handler calls
  - No provider calls
  - No dispatch runtime invocation
  - No filesystem mutation
  - No network access
  - No STATIC_ALLOWLIST mutation
  - executionAllowed is always false
  - dispatchAllowed is always false
  - providerSchemaAllowed is always false
  - toolHandlerCallAllowed is always false
  - toolHandlerCalled is always false
  - providerApiCalled is always false
  - Raw token never appears in result
  - Full tokenHash never appears in result
  - Raw arguments never appear in result
  - Secrets never appear in result
  - Callable object never exposed
  - Dispatch plan success still blocks at the Tool Handler call boundary
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_dispatch import (
    DISPATCH_ID_PREFIX,
    DISPATCH_PLAN_VERSION,
    DISPATCH_ROUTING_MODE,
    DISPATCH_SCHEMA_VERSION,
    DISPATCH_STATUS_BLOCKED,
    DISPATCH_STATUS_PLANNED,
    FINAL_BLOCK_TOOL_HANDLER_CALL_NOT_ENABLED,
    ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISSING,
    ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH,
    ERROR_DISPATCH_NOT_ALLOWLISTED,
    ERROR_DISPATCH_PLAN_INVALID,
    ERROR_DISPATCH_PLAN_UNAVAILABLE,
    ERROR_DISPATCH_POLICY_MISMATCH,
    ERROR_DISPATCH_REGISTRY_MISMATCH,
    ERROR_DISPATCH_SIDE_EFFECT_RISK,
    ERROR_DISPATCH_UNAVAILABLE,
    ERROR_DISPATCH_WRITTEN_BUT_TOOL_HANDLER_CALL_NOT_ENABLED,
    ERROR_TOOL_HANDLER_CALL_NOT_ENABLED,
    DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISSING,
    DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH,
    DECISION_BLOCKED_DISPATCH_NOT_ALLOWLISTED,
    DECISION_BLOCKED_DISPATCH_PLAN_INVALID,
    DECISION_BLOCKED_DISPATCH_PLAN_UNAVAILABLE,
    DECISION_BLOCKED_DISPATCH_POLICY_MISMATCH,
    DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH,
    DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK,
    DECISION_BLOCKED_DISPATCH_UNAVAILABLE,
    DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED,
    DispatchPlan,
    DispatchResult,
    build_dispatch_plan,
    create_dispatch_plan,
    generate_dispatch_id,
    safe_dispatch_summary,
    validate_dispatch_plan,
)
from hermes_cli.dev_web_tool_handler_lookup import build_handler_descriptor
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


def _clarify_descriptor() -> dict:
    """Return a fresh safe descriptor for clarify."""
    desc = build_handler_descriptor("clarify")
    assert desc is not None
    return desc


# ===================================================================
# 1. Dispatch Plan Structure Tests
# ===================================================================


class TestDispatchPlanStructure:
    """Verify dispatch plan includes all required safe fields."""

    def _plan(self) -> dict:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
            toolset_name="builtin",
        )
        assert r.built is True
        assert r.dispatch_plan is not None
        return r.dispatch_plan

    def test_plan_includes_dispatch_id(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert r.dispatch_id is not None

    def test_plan_includes_canonical_name(self) -> None:
        plan = self._plan()
        assert plan["canonicalName"] == "clarify"

    def test_plan_includes_handler_lookup_id(self) -> None:
        plan = self._plan()
        assert plan["handlerLookupId"] == "hl_test"

    def test_plan_includes_handler_id(self) -> None:
        plan = self._plan()
        assert plan["handlerId"] == "handler_clarify"

    def test_plan_includes_registry_key(self) -> None:
        plan = self._plan()
        assert plan["registryKey"] == "clarify"

    def test_plan_includes_toolset_name_if_available(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
            toolset_name="builtin",
        )
        assert r.dispatch_plan["toolsetName"] == "builtin"

    def test_plan_omits_toolset_name_if_not_available(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert "toolsetName" not in r.dispatch_plan

    def test_plan_includes_routing_mode(self) -> None:
        plan = self._plan()
        assert plan["routingMode"] == DISPATCH_ROUTING_MODE
        assert plan["routingMode"] == "metadata_only"

    def test_plan_includes_dispatch_allowed_false(self) -> None:
        plan = self._plan()
        assert plan["dispatchAllowed"] is False

    def test_plan_includes_tool_handler_call_allowed_false(self) -> None:
        plan = self._plan()
        assert plan["toolHandlerCallAllowed"] is False

    def test_plan_includes_execution_allowed_false(self) -> None:
        plan = self._plan()
        assert plan["executionAllowed"] is False

    def test_plan_includes_provider_schema_allowed_false(self) -> None:
        plan = self._plan()
        assert plan["providerSchemaAllowed"] is False

    def test_plan_includes_side_effect_free_dispatch_true(self) -> None:
        plan = self._plan()
        assert plan["sideEffectFreeDispatch"] is True

    def test_plan_excludes_raw_arguments(self) -> None:
        plan = self._plan()
        text = json.dumps(plan)
        assert "rawArguments" not in text
        assert "arguments" not in text.lower() or "argumentsDigest" in text

    def test_plan_excludes_raw_token(self) -> None:
        plan = self._plan()
        text = json.dumps(plan)
        assert "confirmationToken" not in text
        assert "rawToken" not in text
        assert "raw_token" not in text

    def test_plan_excludes_full_token_hash(self) -> None:
        plan = self._plan()
        text = json.dumps(plan)
        assert "tokenHash" not in text
        assert "token_hash" not in text

    def test_plan_excludes_provider_credentials(self) -> None:
        plan = self._plan()
        text = json.dumps(plan)
        assert "apiKey" not in text
        assert "api_key" not in text
        assert "credential" not in text
        assert "secret" not in text
        assert "password" not in text

    def test_plan_excludes_provider_schema_payload(self) -> None:
        plan = self._plan()
        text = json.dumps(plan)
        assert "providerSchemaPayload" not in text
        assert "providerSchemaContent" not in text

    def test_plan_excludes_callable_object(self) -> None:
        plan = self._plan()
        for _key, value in plan.items():
            assert not callable(value), f"Plan field is callable"
            assert not hasattr(value, "__call__"), f"Plan field has __call__"

    def test_plan_excludes_function_repr(self) -> None:
        plan = self._plan()
        text = json.dumps(plan)
        assert "<function" not in text
        assert "callable" not in text.lower()


# ===================================================================
# 2. Dispatch Gate Tests
# ===================================================================


class TestDispatchGates:
    """Verify dispatch gate behavior."""

    def test_dispatch_not_attempted_with_missing_handler_lookup_id(self) -> None:
        """Missing handlerLookupId blocks at dispatch_plan_unavailable."""
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id=None,
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_PLAN_UNAVAILABLE
        assert r.decision == DECISION_BLOCKED_DISPATCH_PLAN_UNAVAILABLE

    def test_dispatch_not_attempted_with_empty_handler_lookup_id(self) -> None:
        """Empty handlerLookupId blocks at dispatch_plan_unavailable."""
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="   ",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_PLAN_UNAVAILABLE

    def test_non_allowlisted_canonical_name_blocks_before_dispatch(self) -> None:
        """Non-allowlisted canonicalName blocks at dispatch_not_allowlisted."""
        r = build_dispatch_plan(
            canonical_name="read_file",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
            allowlist=frozenset({"read_file"}),
        )
        # read_file is in the custom allowlist but its descriptor canonicalName
        # is "clarify", so it mismatches. Either way it must block.
        assert r.built is False

    def test_canonical_name_not_in_custom_allowlist_blocks(self) -> None:
        """canonicalName present in descriptor but excluded by allowlist blocks."""
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
            allowlist=frozenset({"read_file"}),  # clarify excluded
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_NOT_ALLOWLISTED
        assert r.decision == DECISION_BLOCKED_DISPATCH_NOT_ALLOWLISTED

    def test_missing_handler_descriptor_blocks(self) -> None:
        """Missing handler descriptor blocks at handler_descriptor_missing."""
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=None,
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISSING
        assert r.decision == DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISSING

    def test_non_dict_handler_descriptor_blocks(self) -> None:
        """Non-dict handler descriptor blocks at handler_descriptor_missing."""
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor="not-a-dict",  # type: ignore[arg-type]
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISSING

    def test_canonical_name_mismatch_blocks(self) -> None:
        """Descriptor canonicalName mismatch blocks at handler_descriptor_mismatch."""
        desc = _clarify_descriptor()
        desc["canonicalName"] = "wrong_name"
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=desc,
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH
        assert r.decision == DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH

    def test_registry_key_mismatch_blocks(self) -> None:
        """Descriptor registryKey != canonicalName blocks at registry_mismatch."""
        desc = _clarify_descriptor()
        desc["registryKey"] = "not_clarify"
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=desc,
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_REGISTRY_MISMATCH
        assert r.decision == DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH

    def test_risk_tier_mismatch_blocks(self) -> None:
        """Descriptor riskTier != expected risk_tier blocks at policy_mismatch."""
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
            risk_tier="R4",  # descriptor says R0
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_POLICY_MISMATCH
        assert r.decision == DECISION_BLOCKED_DISPATCH_POLICY_MISMATCH

    def test_side_effect_risk_dispatch_allowed_blocks(self) -> None:
        """Descriptor dispatchAllowed=True blocks at side_effect_risk."""
        desc = _clarify_descriptor()
        desc["dispatchAllowed"] = True
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=desc,
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_SIDE_EFFECT_RISK
        assert r.decision == DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK

    def test_side_effect_risk_execution_allowed_blocks(self) -> None:
        """Descriptor executionAllowed=True blocks at side_effect_risk."""
        desc = _clarify_descriptor()
        desc["executionAllowed"] = True
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=desc,
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_side_effect_risk_provider_schema_allowed_blocks(self) -> None:
        """Descriptor providerSchemaAllowed=True blocks at side_effect_risk."""
        desc = _clarify_descriptor()
        desc["providerSchemaAllowed"] = True
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=desc,
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_empty_canonical_name_blocks(self) -> None:
        """Empty canonicalName blocks at dispatch_plan_invalid."""
        r = build_dispatch_plan(
            canonical_name="",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is False
        assert r.error_code == ERROR_DISPATCH_PLAN_INVALID
        assert r.decision == DECISION_BLOCKED_DISPATCH_PLAN_INVALID

    def test_dispatch_success_returns_dispatch_id(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert r.dispatch_id is not None

    def test_dispatch_success_returns_safe_dispatch_plan(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert r.dispatch_plan is not None
        assert r.dispatch_plan["canonicalName"] == "clarify"
        assert r.dispatch_plan["dispatchAllowed"] is False

    def test_dispatch_id_prefix_is_dsp(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert r.dispatch_id.startswith(DISPATCH_ID_PREFIX)
        assert r.dispatch_id.startswith("dsp_")
        suffix = r.dispatch_id[len(DISPATCH_ID_PREFIX):]
        assert len(suffix) > 0

    def test_dispatch_id_is_unique_correlation_only(self) -> None:
        results = [
            build_dispatch_plan(
                canonical_name="clarify",
                handler_lookup_id="hl_test",
                handler_descriptor=_clarify_descriptor(),
            )
            for _ in range(10)
        ]
        ids = [r.dispatch_id for r in results if r.dispatch_id]
        assert len(set(ids)) == len(ids), "dispatchId values must be unique"

    def test_dispatch_success_final_block_is_tool_handler_call_not_enabled(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert r.final_block == FINAL_BLOCK_TOOL_HANDLER_CALL_NOT_ENABLED
        assert r.decision == DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED
        assert r.error_code == ERROR_DISPATCH_WRITTEN_BUT_TOOL_HANDLER_CALL_NOT_ENABLED

    def test_dispatch_plan_existence_does_not_bypass_static_allowlist(self) -> None:
        """A dispatch plan can only be built for allowlisted tools."""
        # clarify is allowlisted — plan builds
        r_ok = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r_ok.built is True

        # read_file is NOT allowlisted — no plan, even with a descriptor
        read_desc = dict(_clarify_descriptor())
        read_desc["canonicalName"] = "read_file"
        read_desc["registryKey"] = "read_file"
        r_no = build_dispatch_plan(
            canonical_name="read_file",
            handler_lookup_id="hl_test",
            handler_descriptor=read_desc,
        )
        assert r_no.built is False
        assert r_no.error_code == ERROR_DISPATCH_NOT_ALLOWLISTED


# ===================================================================
# 3. Security Invariant Tests
# ===================================================================


class TestSecurityInvariants:
    """Verify security invariants across all dispatch operations."""

    def _result_text(self) -> str:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        full = {
            "dispatch_plan": r.dispatch_plan,
            "safe_summary": r.safe_summary,
            "dispatch_id": r.dispatch_id,
            "dispatch_status": r.dispatch_status,
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

    def test_raw_arguments_never_in_result(self) -> None:
        text = self._result_text()
        assert "rawArguments" not in text

    def test_secrets_never_in_result(self) -> None:
        text = self._result_text()
        lower = text.lower()
        assert "secret" not in lower
        assert "password" not in lower
        assert "api_key" not in lower
        assert "apikey" not in lower
        assert "authorization" not in lower

    def test_provider_never_called(self) -> None:
        source = Path(
            __import__("hermes_cli.dev_web_tool_dispatch", fromlist=["__file__"]).__file__
        ).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source

    def test_tool_handler_never_called(self) -> None:
        source = Path(
            __import__("hermes_cli.dev_web_tool_dispatch", fromlist=["__file__"]).__file__
        ).read_text(encoding="utf-8")
        assert "from tools." not in source
        assert "import tools." not in source

    def test_dispatch_runtime_never_invoked(self) -> None:
        source = Path(
            __import__("hermes_cli.dev_web_tool_dispatch", fromlist=["__file__"]).__file__
        ).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "import socket" not in source
        assert "import requests" not in source
        assert "import httpx" not in source

    def test_execution_never_started(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        # Side-effect flags remain false
        assert r.side_effect_flags["executionStarted"] is False
        assert r.side_effect_flags["executionAllowed"] is False
        assert r.side_effect_flags["toolHandlerCalled"] is False
        assert r.side_effect_flags["providerApiCalled"] is False

    def test_dispatch_plan_contains_no_callable_object(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        for _key, value in r.dispatch_plan.items():
            assert not callable(value)
            assert not hasattr(value, "__call__")

    def test_dispatch_plan_contains_no_function_repr(self) -> None:
        text = self._result_text()
        assert "<function" not in text
        assert "functools" not in text

    def test_side_effect_flags_all_false_on_failure(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id=None,
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is False
        for _k, v in r.side_effect_flags.items():
            assert v is False

    def test_static_allowlist_unchanged_after_dispatch(self) -> None:
        before = frozenset(STATIC_ALLOWLIST)
        build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        build_dispatch_plan(
            canonical_name="read_file",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert STATIC_ALLOWLIST == before
        assert STATIC_ALLOWLIST == frozenset({"clarify"})


# ===================================================================
# 4. Dispatch Plan Validation Tests
# ===================================================================


class TestDispatchPlanValidation:
    """Verify validate_dispatch_plan logic."""

    def _valid_plan(self) -> dict:
        return {
            "canonicalName": "clarify",
            "handlerLookupId": "hl_test",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "routingMode": DISPATCH_ROUTING_MODE,
            "dispatchAllowed": False,
            "toolHandlerCallAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeDispatch": True,
        }

    def test_valid_plan_passes(self) -> None:
        assert validate_dispatch_plan(self._valid_plan()) is None

    def test_non_dict_fails(self) -> None:
        assert validate_dispatch_plan("not-a-dict") == ERROR_DISPATCH_PLAN_INVALID  # type: ignore[arg-type]
        assert validate_dispatch_plan(None) == ERROR_DISPATCH_PLAN_INVALID  # type: ignore[arg-type]

    def test_missing_field_fails(self) -> None:
        plan = self._valid_plan()
        del plan["handlerId"]
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_PLAN_INVALID

    def test_none_field_fails(self) -> None:
        plan = self._valid_plan()
        plan["registryKey"] = None
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_PLAN_INVALID

    def test_empty_canonical_name_fails(self) -> None:
        plan = self._valid_plan()
        plan["canonicalName"] = ""
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_PLAN_INVALID

    def test_wrong_routing_mode_fails(self) -> None:
        plan = self._valid_plan()
        plan["routingMode"] = "runtime_invocation"
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_PLAN_INVALID

    def test_dispatch_allowed_true_fails(self) -> None:
        plan = self._valid_plan()
        plan["dispatchAllowed"] = True
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_tool_handler_call_allowed_true_fails(self) -> None:
        plan = self._valid_plan()
        plan["toolHandlerCallAllowed"] = True
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_execution_allowed_true_fails(self) -> None:
        plan = self._valid_plan()
        plan["executionAllowed"] = True
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_provider_schema_allowed_true_fails(self) -> None:
        plan = self._valid_plan()
        plan["providerSchemaAllowed"] = True
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_side_effect_free_dispatch_false_fails(self) -> None:
        plan = self._valid_plan()
        plan["sideEffectFreeDispatch"] = False
        assert validate_dispatch_plan(plan) == ERROR_DISPATCH_SIDE_EFFECT_RISK

    def test_canonical_name_mismatch_fails(self) -> None:
        error = validate_dispatch_plan(
            self._valid_plan(),
            expected_canonical_name="other",
        )
        assert error == ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH

    def test_handler_lookup_id_mismatch_fails(self) -> None:
        error = validate_dispatch_plan(
            self._valid_plan(),
            expected_handler_lookup_id="hl_other",
        )
        assert error == ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH

    def test_registry_key_mismatch_fails(self) -> None:
        error = validate_dispatch_plan(
            self._valid_plan(),
            expected_registry_key="other",
        )
        assert error == ERROR_DISPATCH_REGISTRY_MISMATCH


# ===================================================================
# 5. Result Dataclass / Summary Tests
# ===================================================================


class TestResultAndSummary:
    """Verify DispatchResult immutability and safe summary builder."""

    def test_dispatch_plan_dataclass_is_frozen(self) -> None:
        plan = DispatchPlan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_id="handler_clarify",
            registry_key="clarify",
            routing_mode=DISPATCH_ROUTING_MODE,
            dispatch_allowed=False,
            tool_handler_call_allowed=False,
            execution_allowed=False,
            provider_schema_allowed=False,
            side_effect_free_dispatch=True,
            dispatch_plan_version=DISPATCH_PLAN_VERSION,
        )
        with pytest.raises(AttributeError):
            plan.canonical_name = "other"  # type: ignore[misc]

    def test_dispatch_result_dataclass_is_frozen(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        with pytest.raises(AttributeError):
            r.built = False  # type: ignore[misc]

    def test_result_has_created_at(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert r.created_at is not None
        assert "T" in r.created_at  # ISO 8601

    def test_result_has_safe_summary(self) -> None:
        r = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r.built is True
        assert isinstance(r.safe_summary, dict)
        assert r.safe_summary["dispatchId"] == r.dispatch_id
        assert r.safe_summary["dispatchStatus"] == DISPATCH_STATUS_PLANNED

    def test_create_dispatch_plan_alias_matches_build(self) -> None:
        r1 = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        r2 = create_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r1.built == r2.built
        assert r1.dispatch_status == r2.dispatch_status
        assert r1.dispatch_plan == r2.dispatch_plan

    def test_safe_summary_includes_dispatch_id(self) -> None:
        summary = safe_dispatch_summary(
            dispatch_id="dsp_test123",
            dispatch_status=DISPATCH_STATUS_PLANNED,
        )
        assert summary["dispatchId"] == "dsp_test123"

    def test_safe_summary_includes_status(self) -> None:
        summary = safe_dispatch_summary(
            dispatch_id="dsp_test123",
            dispatch_status=DISPATCH_STATUS_PLANNED,
        )
        assert summary["dispatchStatus"] == "planned"

    def test_safe_summary_no_secrets(self) -> None:
        summary = safe_dispatch_summary(
            dispatch_id="dsp_test123",
            dispatch_status=DISPATCH_STATUS_PLANNED,
        )
        text = json.dumps(summary)
        assert "secret" not in text
        assert "password" not in text
        assert "token" not in text.lower() or "dispatch" in text.lower()


# ===================================================================
# 6. Constants Tests
# ===================================================================


class TestConstants:
    """Verify constant values."""

    def test_dispatch_id_prefix(self) -> None:
        assert DISPATCH_ID_PREFIX == "dsp_"

    def test_routing_mode_metadata_only(self) -> None:
        assert DISPATCH_ROUTING_MODE == "metadata_only"

    def test_schema_version(self) -> None:
        assert isinstance(DISPATCH_SCHEMA_VERSION, int)
        assert DISPATCH_SCHEMA_VERSION >= 1

    def test_plan_version(self) -> None:
        assert isinstance(DISPATCH_PLAN_VERSION, int)
        assert DISPATCH_PLAN_VERSION >= 1

    def test_status_planned(self) -> None:
        assert DISPATCH_STATUS_PLANNED == "planned"

    def test_status_blocked(self) -> None:
        assert DISPATCH_STATUS_BLOCKED == "blocked"

    def test_final_block_constant(self) -> None:
        assert FINAL_BLOCK_TOOL_HANDLER_CALL_NOT_ENABLED == "blocked_tool_handler_call_not_enabled"

    def test_tool_handler_call_not_enabled_error(self) -> None:
        assert ERROR_TOOL_HANDLER_CALL_NOT_ENABLED == "tool_handler_call_not_enabled"

    def test_dispatch_unavailable_error(self) -> None:
        assert ERROR_DISPATCH_UNAVAILABLE == "dispatch_unavailable"

    def test_dispatch_written_but_blocked_error(self) -> None:
        assert (
            ERROR_DISPATCH_WRITTEN_BUT_TOOL_HANDLER_CALL_NOT_ENABLED
            == "dispatch_written_but_tool_handler_call_not_enabled"
        )

    def test_generate_dispatch_id_prefix(self) -> None:
        did = generate_dispatch_id()
        assert did.startswith(DISPATCH_ID_PREFIX)
        assert len(did) > len(DISPATCH_ID_PREFIX)

    def test_generate_dispatch_id_unique(self) -> None:
        ids = [generate_dispatch_id() for _ in range(20)]
        assert len(set(ids)) == len(ids)


# ===================================================================
# 7. No Side Effects Tests
# ===================================================================


class TestNoSideEffects:
    """Verify dispatch module has no side effects."""

    def test_does_not_import_tool_handlers(self) -> None:
        import hermes_cli.dev_web_tool_dispatch as dispatch_mod

        source = Path(dispatch_mod.__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from tools." not in line, f"Unexpected import: {line}"
            assert "from agent." not in line, f"Unexpected import: {line}"

    def test_does_not_import_provider(self) -> None:
        import hermes_cli.dev_web_tool_dispatch as dispatch_mod

        source = Path(dispatch_mod.__file__).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source

    def test_does_not_import_subprocess_or_socket(self) -> None:
        import hermes_cli.dev_web_tool_dispatch as dispatch_mod

        source = Path(dispatch_mod.__file__).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "import socket" not in source
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "import urllib" not in source

    def test_dispatch_is_idempotent(self) -> None:
        """Multiple dispatch builds do not change state."""
        r1 = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        r2 = build_dispatch_plan(
            canonical_name="clarify",
            handler_lookup_id="hl_test",
            handler_descriptor=_clarify_descriptor(),
        )
        assert r1.built is True
        assert r2.built is True
        # dispatchIds must be unique (correlation only)
        assert r1.dispatch_id != r2.dispatch_id
