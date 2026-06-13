"""Tests for hermes_cli.dev_web_tool_handler_lookup — Handler Lookup Minimal Implementation.

Phase 1G-04-26: Handler Lookup Minimal Implementation / Still Blocked-Only.

All tests verify:
  - Safe handler descriptor lookup only — no handler invocation
  - No tool handler calls
  - No provider calls
  - No dispatch calls
  - No filesystem mutation
  - No network access
  - No STATIC_ALLOWLIST mutation
  - executionAllowed is always false
  - dispatchAllowed is always false
  - providerSchemaAllowed is always false
  - toolHandlerCalled is always false
  - providerApiCalled is always false
  - Raw token never appears in result
  - Full tokenHash never appears in result
  - Raw arguments never appear in result
  - Secrets never appear in result
  - Callable object never exposed
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_handler_lookup import (
    HANDLER_LOOKUP_ID_PREFIX,
    HANDLER_LOOKUP_SCHEMA_VERSION,
    HANDLER_LOOKUP_STATUS_BLOCKED,
    HANDLER_LOOKUP_STATUS_FOUND,
    HANDLER_LOOKUP_STATUS_NOT_FOUND,
    HANDLER_DESCRIPTOR_VERSION,
    ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED,
    ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID,
    ERROR_HANDLER_LOOKUP_NOT_FOUND,
    ERROR_HANDLER_LOOKUP_POLICY_MISMATCH,
    ERROR_HANDLER_LOOKUP_REGISTRY_UNAVAILABLE,
    ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK,
    ERROR_HANDLER_LOOKUP_UNAVAILABLE,
    ERROR_HANDLER_LOOKUP_WRITTEN_BUT_DISPATCH_NOT_ENABLED,
    ERROR_DISPATCH_NOT_ENABLED,
    DECISION_BLOCKED_HANDLER_LOOKUP_DESCRIPTOR_INVALID,
    DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ALLOWLISTED,
    DECISION_BLOCKED_HANDLER_LOOKUP_NOT_FOUND,
    DECISION_BLOCKED_HANDLER_LOOKUP_POLICY_MISMATCH,
    DECISION_BLOCKED_HANDLER_LOOKUP_REGISTRY_UNAVAILABLE,
    DECISION_BLOCKED_HANDLER_LOOKUP_SIDE_EFFECT_RISK,
    DECISION_BLOCKED_DISPATCH_NOT_ENABLED,
    HandlerLookupResult,
    build_handler_descriptor,
    lookup_handler_descriptor,
    safe_handler_lookup_summary,
    validate_handler_descriptor,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


# ===================================================================
# 1. Handler Descriptor Structure Tests
# ===================================================================


class TestHandlerDescriptorStructure:
    """Verify handler descriptor includes all required fields."""

    def test_descriptor_includes_canonical_name(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["canonicalName"] == "clarify"

    def test_descriptor_includes_handler_id(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert "handlerId" in desc
        assert desc["handlerId"] == "handler_clarify"

    def test_descriptor_includes_registry_key(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert "registryKey" in desc
        assert desc["registryKey"] == "clarify"

    def test_descriptor_includes_module_name(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert "moduleName" in desc
        assert desc["moduleName"] == "builtin.safe_metadata_only"

    def test_descriptor_includes_callable_name(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert "callableName" in desc
        assert desc["callableName"] == "clarify"

    def test_descriptor_includes_risk_tier(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["riskTier"] == "R0"

    def test_descriptor_includes_allowlisted_true_for_clarify(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["allowlisted"] is True

    def test_descriptor_includes_dispatch_allowed_false(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["dispatchAllowed"] is False

    def test_descriptor_includes_execution_allowed_false(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["executionAllowed"] is False

    def test_descriptor_includes_provider_schema_allowed_false(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["providerSchemaAllowed"] is False

    def test_descriptor_includes_side_effect_free_lookup_true(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["sideEffectFreeLookup"] is True

    def test_descriptor_excludes_raw_arguments(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        text = json.dumps(desc)
        assert "arguments" not in text.lower() or "argumentsDigest" in text

    def test_descriptor_excludes_raw_token(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        text = json.dumps(desc)
        assert "confirmationToken" not in text
        assert "rawToken" not in text
        assert "raw_token" not in text

    def test_descriptor_excludes_full_token_hash(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        text = json.dumps(desc)
        assert "tokenHash" not in text
        assert "token_hash" not in text

    def test_descriptor_excludes_provider_credentials(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        text = json.dumps(desc)
        assert "apiKey" not in text
        assert "api_key" not in text
        assert "credential" not in text
        assert "secret" not in text
        assert "password" not in text

    def test_descriptor_excludes_provider_schema_payload(self) -> None:
        """Descriptor excludes Provider Schema payload (the actual schema content)."""
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        # providerSchemaAllowed is a boolean flag, not the Provider Schema payload
        text = json.dumps(desc)
        assert "providerSchemaPayload" not in text
        assert "providerSchemaContent" not in text
        assert "providerSchemaData" not in text
        # providerSchemaAllowed exists but is a boolean flag (false), not schema data

    def test_descriptor_excludes_callable_object(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        # All values must be JSON-serializable types (str, bool, int, etc.)
        # No function or callable objects
        for key, value in desc.items():
            assert not callable(value), f"Descriptor field '{key}' is callable"
            assert not hasattr(value, "__call__"), f"Descriptor field '{key}' has __call__"


# ===================================================================
# 2. Handler Lookup Gate Tests
# ===================================================================


class TestHandlerLookupGates:
    """Verify handler lookup gate behavior."""

    def test_lookup_not_attempted_for_non_allowlisted(self) -> None:
        """Non-allowlisted canonicalName blocks before lookup."""
        result = lookup_handler_descriptor("read_file")
        assert result.found is False
        assert result.error_code == ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED

    def test_handler_exists_but_not_allowlisted_still_blocks(self) -> None:
        """Handler may exist but canonicalName not allowlisted still blocks."""
        # Even if we had a descriptor for read_file, it's not allowlisted
        result = lookup_handler_descriptor("read_file")
        assert result.found is False
        assert result.decision == DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ALLOWLISTED

    def test_missing_handler_blocks(self) -> None:
        """Missing handler descriptor blocks at handler_lookup_not_found."""
        # "clarify" is allowlisted and exists, but what about a tool that
        # is allowlisted but has no descriptor? Test with a custom allowlist.
        result = lookup_handler_descriptor(
            "future_tool",
            allowlist=frozenset({"future_tool"}),
        )
        assert result.found is False
        assert result.error_code == ERROR_HANDLER_LOOKUP_NOT_FOUND
        assert result.handler_lookup_status == HANDLER_LOOKUP_STATUS_NOT_FOUND

    def test_descriptor_invalid_blocks(self) -> None:
        """Invalid descriptor blocks at handler_lookup_descriptor_invalid."""
        # We can't easily corrupt the static descriptor, but we can test
        # validate_handler_descriptor directly
        invalid_desc = {"canonicalName": "clarify"}  # Missing many fields
        error = validate_handler_descriptor(invalid_desc)
        assert error == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    def test_descriptor_canonical_name_mismatch_blocks(self) -> None:
        """Descriptor canonicalName mismatch blocks."""
        desc = {
            "canonicalName": "wrong_name",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        error = validate_handler_descriptor(desc, expected_canonical_name="clarify")
        assert error == ERROR_HANDLER_LOOKUP_POLICY_MISMATCH

    def test_descriptor_risk_tier_missing_blocks(self) -> None:
        """Missing riskTier blocks."""
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": None,  # Invalid
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        error = validate_handler_descriptor(desc)
        assert error == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    def test_descriptor_allowlist_mismatch_blocks(self) -> None:
        """Descriptor allowlisted=False blocks."""
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": False,  # Not allowlisted!
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        error = validate_handler_descriptor(desc)
        assert error == ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED

    def test_descriptor_side_effect_risk_dispatch_blocks(self) -> None:
        """dispatchAllowed=True blocks with side_effect_risk."""
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": True,  # Dangerous!
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        error = validate_handler_descriptor(desc)
        assert error == ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK

    def test_descriptor_side_effect_risk_execution_blocks(self) -> None:
        """executionAllowed=True blocks with side_effect_risk."""
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": True,  # Dangerous!
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        error = validate_handler_descriptor(desc)
        assert error == ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK

    def test_descriptor_side_effect_risk_provider_blocks(self) -> None:
        """providerSchemaAllowed=True blocks with side_effect_risk."""
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": True,  # Dangerous!
            "sideEffectFreeLookup": True,
        }
        error = validate_handler_descriptor(desc)
        assert error == ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK

    def test_descriptor_side_effect_free_lookup_false_blocks(self) -> None:
        """sideEffectFreeLookup=False blocks."""
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": False,  # Not side-effect-free!
        }
        error = validate_handler_descriptor(desc)
        assert error == ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK

    def test_lookup_success_returns_handler_lookup_id(self) -> None:
        """Successful lookup returns handlerLookupId."""
        result = lookup_handler_descriptor("clarify")
        assert result.found is True
        assert result.handler_lookup_id is not None
        assert result.handler_lookup_id.startswith(HANDLER_LOOKUP_ID_PREFIX)

    def test_lookup_success_returns_safe_handler_descriptor(self) -> None:
        """Successful lookup returns safe handlerDescriptor."""
        result = lookup_handler_descriptor("clarify")
        assert result.found is True
        assert result.handler_descriptor is not None
        assert result.handler_descriptor["canonicalName"] == "clarify"
        assert result.handler_descriptor["dispatchAllowed"] is False
        assert result.handler_descriptor["executionAllowed"] is False

    def test_handler_lookup_id_prefix_is_hl(self) -> None:
        """handlerLookupId must start with hl_."""
        result = lookup_handler_descriptor("clarify")
        assert result.found is True
        assert result.handler_lookup_id.startswith("hl_")
        # After prefix, there should be a non-empty random string
        suffix = result.handler_lookup_id[len(HANDLER_LOOKUP_ID_PREFIX):]
        assert len(suffix) > 0

    def test_handler_lookup_id_is_unique_correlation_only(self) -> None:
        """handlerLookupId is unique and correlation-only."""
        results = [lookup_handler_descriptor("clarify") for _ in range(10)]
        ids = [r.handler_lookup_id for r in results if r.handler_lookup_id]
        assert len(set(ids)) == len(ids), "handlerLookupId values must be unique"


# ===================================================================
# 3. Security Invariant Tests
# ===================================================================


class TestSecurityInvariants:
    """Verify security invariants across all handler lookup operations."""

    def test_raw_token_never_in_result(self) -> None:
        """Raw confirmationToken never appears in handler lookup result."""
        result = lookup_handler_descriptor("clarify")
        text = json.dumps(result.safe_summary)
        assert "confirmationToken" not in text
        assert "rawToken" not in text
        assert "raw_token" not in text

    def test_full_token_hash_never_in_result(self) -> None:
        """Full tokenHash never appears in handler lookup result."""
        result = lookup_handler_descriptor("clarify")
        text = json.dumps(result.safe_summary)
        assert "tokenHash" not in text
        if result.handler_descriptor:
            desc_text = json.dumps(result.handler_descriptor)
            assert "tokenHash" not in desc_text

    def test_raw_arguments_never_in_result(self) -> None:
        """Raw arguments never appear in handler lookup result."""
        result = lookup_handler_descriptor("clarify")
        text = json.dumps(result.safe_summary)
        assert "arguments" not in text
        if result.handler_descriptor:
            desc_text = json.dumps(result.handler_descriptor)
            assert "rawArguments" not in desc_text

    def test_secrets_never_in_result(self) -> None:
        """Secrets never appear in handler lookup result."""
        result = lookup_handler_descriptor("clarify")
        text = json.dumps(result.safe_summary)
        assert "secret" not in text.lower()
        assert "password" not in text.lower()
        assert "api_key" not in text.lower()
        assert "apikey" not in text.lower()

    def test_provider_never_called(self) -> None:
        """Provider is never called during handler lookup."""
        # Read source code to verify no provider imports
        source = Path(
            __import__("hermes_cli.dev_web_tool_handler_lookup", fromlist=["__file__"]).__file__
        ).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source

    def test_tool_handler_never_called(self) -> None:
        """Tool Handler is never called during handler lookup."""
        source = Path(
            __import__("hermes_cli.dev_web_tool_handler_lookup", fromlist=["__file__"]).__file__
        ).read_text(encoding="utf-8")
        assert "from tools." not in source
        assert "import tools." not in source

    def test_dispatch_never_called(self) -> None:
        """Dispatch is never called during handler lookup."""
        source = Path(
            __import__("hermes_cli.dev_web_tool_handler_lookup", fromlist=["__file__"]).__file__
        ).read_text(encoding="utf-8")
        assert "import dispatch" not in source
        assert "from dispatch" not in source

    def test_execution_never_started(self) -> None:
        """Execution is never started during handler lookup."""
        result = lookup_handler_descriptor("clarify")
        assert result.found is True
        # No execution-related fields in result
        text = json.dumps(result.safe_summary)
        assert "executionStarted" not in text

    def test_handler_descriptor_does_not_bypass_allowlist(self) -> None:
        """Handler descriptor existence does not bypass STATIC_ALLOWLIST."""
        # clarify has a descriptor AND is allowlisted — should succeed
        result = lookup_handler_descriptor("clarify")
        assert result.found is True

        # read_file has no descriptor AND is not allowlisted — should fail
        result2 = lookup_handler_descriptor("read_file")
        assert result2.found is False
        assert result2.error_code == ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED

    def test_static_allowlist_unchanged_after_lookup(self) -> None:
        """STATIC_ALLOWLIST is unchanged after any lookup."""
        before = frozenset(STATIC_ALLOWLIST)
        lookup_handler_descriptor("clarify")
        lookup_handler_descriptor("read_file")
        lookup_handler_descriptor("nonexistent")
        assert STATIC_ALLOWLIST == before
        assert STATIC_ALLOWLIST == frozenset({"clarify"})


# ===================================================================
# 4. Descriptor Validation Tests
# ===================================================================


class TestDescriptorValidation:
    """Verify descriptor validation logic."""

    def test_valid_clarify_descriptor_passes(self) -> None:
        desc = {
            "canonicalName": "clarify",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        assert validate_handler_descriptor(desc) is None

    def test_missing_field_fails(self) -> None:
        desc = {
            "canonicalName": "clarify",
            # Missing handlerId
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        assert validate_handler_descriptor(desc) == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    def test_non_dict_fails(self) -> None:
        assert validate_handler_descriptor("not a dict") == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID
        assert validate_handler_descriptor(None) == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID
        assert validate_handler_descriptor(42) == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    def test_empty_canonical_name_fails(self) -> None:
        desc = {
            "canonicalName": "",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        assert validate_handler_descriptor(desc) == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    def test_whitespace_canonical_name_fails(self) -> None:
        desc = {
            "canonicalName": "   ",
            "handlerId": "handler_clarify",
            "registryKey": "clarify",
            "moduleName": "builtin.safe_metadata_only",
            "callableName": "clarify",
            "riskTier": "R0",
            "allowlisted": True,
            "dispatchAllowed": False,
            "executionAllowed": False,
            "providerSchemaAllowed": False,
            "sideEffectFreeLookup": True,
        }
        assert validate_handler_descriptor(desc) == ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID


# ===================================================================
# 5. Result Dataclass Tests
# ===================================================================


class TestResultDataclass:
    """Verify HandlerLookupResult immutability."""

    def test_result_is_frozen(self) -> None:
        result = lookup_handler_descriptor("clarify")
        with pytest.raises(AttributeError):
            result.found = False  # type: ignore[misc]

    def test_result_has_created_at(self) -> None:
        result = lookup_handler_descriptor("clarify")
        assert result.found is True
        assert result.created_at is not None
        assert "T" in result.created_at  # ISO 8601 format

    def test_result_has_safe_summary(self) -> None:
        result = lookup_handler_descriptor("clarify")
        assert result.found is True
        assert isinstance(result.safe_summary, dict)
        assert "handlerLookupId" in result.safe_summary
        assert "handlerLookupStatus" in result.safe_summary


# ===================================================================
# 6. Safe Summary Tests
# ===================================================================


class TestSafeSummary:
    """Verify safe summary builder."""

    def test_safe_summary_includes_lookup_id(self) -> None:
        summary = safe_handler_lookup_summary(
            handler_lookup_id="hl_test123",
            handler_lookup_status="found",
        )
        assert summary["handlerLookupId"] == "hl_test123"

    def test_safe_summary_includes_status(self) -> None:
        summary = safe_handler_lookup_summary(
            handler_lookup_id="hl_test123",
            handler_lookup_status="found",
        )
        assert summary["handlerLookupStatus"] == "found"

    def test_safe_summary_includes_canonical_name(self) -> None:
        summary = safe_handler_lookup_summary(
            handler_lookup_id="hl_test123",
            handler_lookup_status="found",
            canonical_name="clarify",
        )
        assert summary["canonicalName"] == "clarify"

    def test_safe_summary_omits_canonical_name_if_not_provided(self) -> None:
        summary = safe_handler_lookup_summary(
            handler_lookup_id="hl_test123",
            handler_lookup_status="found",
        )
        assert "canonicalName" not in summary

    def test_safe_summary_no_secrets(self) -> None:
        summary = safe_handler_lookup_summary(
            handler_lookup_id="hl_test123",
            handler_lookup_status="found",
        )
        text = json.dumps(summary)
        assert "token" not in text.lower() or "handlerLookupId" in text
        assert "secret" not in text
        assert "password" not in text
        assert "credential" not in text


# ===================================================================
# 7. Build Descriptor Tests
# ===================================================================


class TestBuildDescriptor:
    """Verify build_handler_descriptor."""

    def test_build_clarify_descriptor(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        assert desc["canonicalName"] == "clarify"

    def test_build_unknown_returns_none(self) -> None:
        desc = build_handler_descriptor("unknown_tool")
        assert desc is None

    def test_build_returns_copy(self) -> None:
        """Build returns a copy, not a reference."""
        desc1 = build_handler_descriptor("clarify")
        desc2 = build_handler_descriptor("clarify")
        assert desc1 is not None
        assert desc2 is not None
        assert desc1 == desc2
        assert desc1 is not desc2  # Different objects

    def test_build_descriptor_is_json_safe(self) -> None:
        desc = build_handler_descriptor("clarify")
        assert desc is not None
        text = json.dumps(desc)
        assert isinstance(text, str)


# ===================================================================
# 8. Lookup with Custom Allowlist Tests
# ===================================================================


class TestCustomAllowlist:
    """Verify lookup behavior with custom allowlists."""

    def test_custom_allowlist_empty_blocks_all(self) -> None:
        result = lookup_handler_descriptor(
            "clarify",
            allowlist=frozenset(),
        )
        assert result.found is False
        assert result.error_code == ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED

    def test_custom_allowlist_includes_tool(self) -> None:
        result = lookup_handler_descriptor(
            "clarify",
            allowlist=frozenset({"clarify"}),
        )
        assert result.found is True

    def test_custom_allowlist_excludes_tool(self) -> None:
        result = lookup_handler_descriptor(
            "clarify",
            allowlist=frozenset({"read_file"}),
        )
        assert result.found is False
        assert result.error_code == ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED

    def test_default_allowlist_uses_static_allowlist(self) -> None:
        """Default allowlist is STATIC_ALLOWLIST."""
        result = lookup_handler_descriptor("clarify")
        assert result.found is True  # clarify is in STATIC_ALLOWLIST

        result2 = lookup_handler_descriptor("read_file")
        assert result2.found is False  # read_file is NOT in STATIC_ALLOWLIST


# ===================================================================
# 9. No Side Effects Tests
# ===================================================================


class TestNoSideEffects:
    """Verify handler lookup has no side effects."""

    def test_does_not_import_tool_handlers(self) -> None:
        import hermes_cli.dev_web_tool_handler_lookup as hl_mod

        source = Path(hl_mod.__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from tools." not in line, f"Unexpected import: {line}"
            assert "from agent." not in line, f"Unexpected import: {line}"

    def test_does_not_import_provider(self) -> None:
        import hermes_cli.dev_web_tool_handler_lookup as hl_mod

        source = Path(hl_mod.__file__).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source

    def test_does_not_import_dispatch(self) -> None:
        import hermes_cli.dev_web_tool_handler_lookup as hl_mod

        source = Path(hl_mod.__file__).read_text(encoding="utf-8")
        assert "import dispatch" not in source
        assert "from dispatch" not in source

    def test_does_not_import_subprocess_or_socket(self) -> None:
        import hermes_cli.dev_web_tool_handler_lookup as hl_mod

        source = Path(hl_mod.__file__).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "import socket" not in source
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "import urllib" not in source

    def test_lookup_is_idempotent(self) -> None:
        """Multiple lookups do not change state."""
        r1 = lookup_handler_descriptor("clarify")
        r2 = lookup_handler_descriptor("clarify")
        assert r1.found is True
        assert r2.found is True
        # IDs must be unique (correlation only)
        assert r1.handler_lookup_id != r2.handler_lookup_id


# ===================================================================
# 10. Constants Tests
# ===================================================================


class TestConstants:
    """Verify constant values."""

    def test_handler_lookup_id_prefix(self) -> None:
        assert HANDLER_LOOKUP_ID_PREFIX == "hl_"

    def test_schema_version(self) -> None:
        assert isinstance(HANDLER_LOOKUP_SCHEMA_VERSION, int)
        assert HANDLER_LOOKUP_SCHEMA_VERSION >= 1

    def test_descriptor_version(self) -> None:
        assert isinstance(HANDLER_DESCRIPTOR_VERSION, int)
        assert HANDLER_DESCRIPTOR_VERSION >= 1

    def test_status_found(self) -> None:
        assert HANDLER_LOOKUP_STATUS_FOUND == "found"

    def test_status_not_found(self) -> None:
        assert HANDLER_LOOKUP_STATUS_NOT_FOUND == "not_found"

    def test_status_blocked(self) -> None:
        assert HANDLER_LOOKUP_STATUS_BLOCKED == "blocked"

    def test_dispatch_not_enabled_error(self) -> None:
        assert ERROR_DISPATCH_NOT_ENABLED == "dispatch_not_enabled"

    def test_dispatch_not_enabled_decision(self) -> None:
        assert DECISION_BLOCKED_DISPATCH_NOT_ENABLED == "blocked_dispatch_not_enabled"
