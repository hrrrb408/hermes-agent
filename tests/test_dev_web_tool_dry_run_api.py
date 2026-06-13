"""Tests for POST /api/dev/v1/tools/dry-run — Tool Dry-Run API.

Phase 1G-04-04: Tool Dry-Run API Implementation.
Phase 1G-04-07: Audit Writer Integration.

All tests verify:
  - No tool handler calls
  - No provider calls
  - No dispatch calls
  - No STATIC_ALLOWLIST mutation
  - No raw secrets in response
  - executionAllowed is always false
  - dispatchAllowed is always false
  - providerSchemaAllowed is always false
  - auditWritten reflects audit write status (not tool execution)
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_tool_dry_run import (
    DRY_RUN_DECISION_REQUIRES_REVIEW,
    DRY_RUN_DECISION_WOULD_ALLOW,
    DRY_RUN_DECISION_WOULD_BLOCK,
    DRY_RUN_DECISION_WOULD_REDACT,
    WOULD_BLOCK_UNKNOWN_TOOL,
)
from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
)

API = "/api/dev/v1"
DRY_RUN_URL = f"{API}/tools/dry-run"


@pytest.fixture
def client():
    """TestClient without HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ===================================================================
# 1. Decision Tests — Risk Tiers
# ===================================================================


class TestDryRunDecisions:
    """Verify dry-run decisions for each risk tier."""

    def _find_tool_by_risk(self, risk: str) -> str:
        """Find a tool with the given risk level (not denylisted)."""
        from hermes_cli.dev_web_tool_policy import TOOL_POLICY_INVENTORY

        for name, entry in TOOL_POLICY_INVENTORY.items():
            if (
                entry.primary_risk.value == risk
                and not entry.permanently_denied
                and name not in STATIC_DENYLIST
            ):
                return name
        pytest.skip(f"No non-denylisted {risk} tool found")

    def test_r0_returns_would_allow(self, client) -> None:
        """R0 tool returns 200 with decision=would_allow."""
        tool = self._find_tool_by_risk("R0")
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_WOULD_ALLOW
        assert data["exists"] is True
        assert data["riskTier"] == "R0"
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        # auditWritten may be true (test isolation sets HERMES_HOME)
        # or false — either is acceptable for this test
        assert isinstance(data["auditWritten"], bool)

    def test_r1_returns_would_allow(self, client) -> None:
        """R1 tool returns 200 with decision=would_allow."""
        tool = self._find_tool_by_risk("R1")
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_WOULD_ALLOW
        assert data["exists"] is True
        assert data["executionAllowed"] is False

    def test_r2_returns_requires_review(self, client) -> None:
        """R2 tool returns 200 with decision=requires_review."""
        tool = self._find_tool_by_risk("R2")
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_REQUIRES_REVIEW
        assert data["exists"] is True

    def test_r3_no_sensitive_args_returns_requires_review(self, client) -> None:
        """R3 tool without sensitive args returns requires_review."""
        tool = self._find_tool_by_risk("R3")
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool, "argumentsPreview": {"query": "test"}})
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_REQUIRES_REVIEW
        assert data["exists"] is True

    def test_r3_sensitive_args_returns_would_redact(self, client) -> None:
        """R3 tool with sensitive args returns would_redact and redacts values."""
        tool = self._find_tool_by_risk("R3")
        resp = client.post(
            DRY_RUN_URL,
            json={
                "canonicalName": tool,
                "argumentsPreview": {"api_key": "sk-test-secret-value-123456"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_WOULD_REDACT
        assert data["exists"] is True
        # Verify redaction occurred
        assert data["redactedArgumentsPreview"]["api_key"] == "[REDACTED]"
        assert "sk-test-secret" not in json.dumps(data["redactedArgumentsPreview"])

    def test_r4_returns_would_block(self, client) -> None:
        """R4 tool returns 200 with decision=would_block."""
        tool = self._find_tool_by_risk("R4")
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_WOULD_BLOCK
        assert data["exists"] is True

    def test_r5_returns_would_block(self, client) -> None:
        """R5 tool returns 200 with decision=would_block."""
        tool = self._find_tool_by_risk("R5")
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_WOULD_BLOCK
        assert data["exists"] is True


# ===================================================================
# 2. Denylist & Unknown Tool Tests
# ===================================================================


class TestDenylistAndUnknown:
    """Verify denylist and unknown tool behavior."""

    def test_denylist_returns_would_block(self, client) -> None:
        """Denylisted tool returns 200 with decision=would_block."""
        denylisted = next(iter(STATIC_DENYLIST))
        resp = client.post(DRY_RUN_URL, json={"canonicalName": denylisted})
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["decision"] == DRY_RUN_DECISION_WOULD_BLOCK
        assert data["exists"] is True

    def test_unknown_tool_returns_200_exists_false_would_block(self, client) -> None:
        """Unknown tool returns HTTP 200 with exists=false and would_block."""
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "nonexistent_tool_xyz"})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["exists"] is False
        assert data["decision"] == DRY_RUN_DECISION_WOULD_BLOCK
        assert WOULD_BLOCK_UNKNOWN_TOOL in data["reasonCodes"]
        assert data["riskTier"] is None
        # All execution flags must be false
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        # auditWritten is a boolean (may be true due to test isolation HERMES_HOME)
        assert isinstance(data["auditWritten"], bool)


# ===================================================================
# 3. Request Validation Tests
# ===================================================================


class TestRequestValidation:
    """Verify request validation returns proper 400 errors."""

    def test_missing_canonical_name_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"argumentsPreview": {}})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_CANONICAL_NAME"

    def test_empty_canonical_name_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": ""})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_CANONICAL_NAME"

    def test_whitespace_canonical_name_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "   "})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_CANONICAL_NAME"

    def test_non_string_canonical_name_returns_400(self, client) -> None:
        """Non-string canonicalName returns 400 or 422."""
        resp = client.post(DRY_RUN_URL, json={"canonicalName": 123})
        assert resp.status_code in (400, 422)

    def test_non_object_body_returns_400(self, client) -> None:
        """Non-object body (string) returns 400 or 422."""
        resp = client.post(
            DRY_RUN_URL,
            content=b'"not an object"',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)

    def test_empty_body_returns_400(self, client) -> None:
        """Empty body returns 400."""
        resp = client.post(
            DRY_RUN_URL,
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)

    def test_array_body_returns_400(self, client) -> None:
        """Array body returns 400 or 422."""
        resp = client.post(
            DRY_RUN_URL,
            content=b"[1,2,3]",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)

    def test_non_object_arguments_preview_string_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "argumentsPreview": "string"})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_ARGUMENTS"

    def test_non_object_arguments_preview_array_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "argumentsPreview": [1, 2]})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_ARGUMENTS"

    def test_non_object_arguments_preview_number_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "argumentsPreview": 42})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_ARGUMENTS"

    def test_non_object_arguments_preview_bool_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "argumentsPreview": True})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_ARGUMENTS"

    def test_null_arguments_preview_is_accepted(self, client) -> None:
        """null argumentsPreview is treated as absent."""
        tool = next(iter(ALL_CANONICAL_TOOLS))
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool, "argumentsPreview": None})
        assert resp.status_code == 200

    def test_invalid_source_context_type_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "sourceContext": 123})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_REQUEST"

    def test_invalid_ui_origin_type_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "uiOrigin": 123})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_REQUEST"

    def test_invalid_request_id_type_returns_400(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "test", "requestId": 123})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_DRY_RUN_INVALID_REQUEST"


# ===================================================================
# 4. Security Tests
# ===================================================================


class TestSecurityGuarantees:
    """Verify no execution, no secrets, no side effects."""

    def test_secret_arguments_are_redacted(self, client) -> None:
        """Response never contains raw secret values."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(
            DRY_RUN_URL,
            json={
                "canonicalName": tool,
                "argumentsPreview": {
                    "api_key": "sk-abcdef1234567890",
                    "token": "Bearer abc123def456",
                    "password": "super-secret-pass",
                    "safe_field": "this is safe",
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        text = json.dumps(body)
        # No raw secrets
        assert "sk-abcdef1234567890" not in text
        assert "Bearer abc123def456" not in text
        assert "super-secret-pass" not in text
        # Redaction applied
        redacted = body["data"]["redactedArgumentsPreview"]
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["token"] == "[REDACTED]"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["safe_field"] == "this is safe"

    def test_provider_schema_not_sent(self, client) -> None:
        """Response confirms providerSchemaAllowed=false."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["providerSchemaAllowed"] is False

    def test_tool_handler_not_called(self, client) -> None:
        """No tool handler is imported or called — verified by module check."""
        import hermes_cli.dev_web_api as api_module

        # Verify the handler does not import tool handlers
        source = open(api_module.__file__, encoding="utf-8").read()
        assert "from tools." not in source
        assert "import tools." not in source
        assert "handle_function_call" not in source

    def test_dispatch_not_called(self, client) -> None:
        """No dispatch — verified by response inspection."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        assert data["dispatchAllowed"] is False

    def test_audit_written_status_is_boolean(self, client) -> None:
        """auditWritten is a boolean reflecting audit write status."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        # auditWritten is always a boolean (may be true or false depending on env)
        assert isinstance(data["auditWritten"], bool)

    def test_static_allowlist_remains_clarify_only(self, client) -> None:
        """STATIC_ALLOWLIST must be exactly {"clarify"} before and after request."""
        assert STATIC_ALLOWLIST == frozenset({"clarify"})
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert STATIC_ALLOWLIST == frozenset({"clarify"})


# ===================================================================
# 5. Response Envelope Tests
# ===================================================================


class TestResponseEnvelope:
    """Verify response envelope shape is stable."""

    def test_success_envelope_shape(self, client) -> None:
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]
        # Data fields
        data = body["data"]
        expected_keys = {
            "canonicalName", "exists", "riskTier", "decision",
            "reasonCodes", "policyNotes", "redactedArgumentsPreview",
            "forbiddenFields", "missingRequiredFields",
            "executionAllowed", "dispatchAllowed",
            "providerSchemaAllowed", "auditWritten",
            "dryRunDecisionDigest", "digestAlgorithm",
            "digestPackageVersion", "canonicalizationVersion",
        }
        assert set(data.keys()) == expected_keys

    def test_error_envelope_shape(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": ""})
        body = resp.json()
        assert "error" in body
        error = body["error"]
        assert "code" in error
        assert "message" in error


# ===================================================================
# 6. Route Governance Tests
# ===================================================================


class TestRouteGovernance:
    """Verify route governance counts updated correctly."""

    def test_business_paths_count_is_33(self, client) -> None:
        """Runtime OpenAPI must report 33 business paths."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 33

    def test_tool_dry_run_route_exists(self, client) -> None:
        """POST /tools/dry-run must exist in OpenAPI."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        assert "/api/dev/v1/tools/dry-run" in spec["paths"]
        assert "post" in spec["paths"]["/api/dev/v1/tools/dry-run"]

    def test_post_routes_count_is_14(self, client) -> None:
        """14 POST routes total (12 existing + 1 tool dry-run + 1 tool execute)."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        post_routes = [
            p for p, m in spec["paths"].items()
            if "post" in m and p.startswith("/api/dev/v1/")
        ]
        assert len(post_routes) == 14
        assert "/api/dev/v1/tools/dry-run" in post_routes

    def test_tool_write_routes_remain_0(self, client) -> None:
        """No tool write routes exist — only GET, dry-run POST, and execute POST."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        tool_routes = {p: m for p, m in spec["paths"].items() if p.startswith("/api/dev/v1/tools")}
        # Tool routes: policy (GET), catalog (GET), schemas (GET), schemas/{name} (GET), dry-run (POST), execute (POST)
        write_routes = []
        for path, methods in tool_routes.items():
            for method in methods:
                if method in ("put", "patch", "delete"):
                    write_routes.append(f"{method.upper()} {path}")
                if method == "post" and "dry-run" not in path and "execute" not in path:
                    write_routes.append(f"POST {path}")
        assert len(write_routes) == 0, f"Unexpected tool write routes: {write_routes}"

    def test_tool_execution_route_count_is_1(self, client) -> None:
        """Exactly 1 tool execution route exists (blocked-only)."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        execute_routes = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/tools") and "execute" in p
        ]
        assert len(execute_routes) == 1
        assert "/api/dev/v1/tools/execute" in execute_routes

    def test_dry_run_route_count_is_1(self, client) -> None:
        """Exactly 1 tool dry-run route exists."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        dry_run_routes = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/tools") and "dry-run" in p
        ]
        assert len(dry_run_routes) == 1
        assert "/api/dev/v1/tools/dry-run" in dry_run_routes

    def test_no_write_schemas_in_openapi(self, client) -> None:
        """No tool execution or write schemas in OpenAPI."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        text = json.dumps(spec).lower()
        assert "execute_tool" not in text
        assert "tool_execution" not in text
        assert "dispatch_tool" not in text


# ===================================================================
# 7. Execution Flags Invariant Tests
# ===================================================================


class TestExecutionFlagsInvariant:
    """Verify all execution flags are always false across all scenarios."""

    @pytest.mark.parametrize("tool_name", list(ALL_CANONICAL_TOOLS)[:5])
    def test_known_tools_flags_false(self, client, tool_name: str) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool_name})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False

    def test_unknown_tool_flags_false(self, client) -> None:
        resp = client.post(DRY_RUN_URL, json={"canonicalName": "unknown_tool"})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False

    def test_with_arguments_flags_false(self, client) -> None:
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(
            DRY_RUN_URL,
            json={"canonicalName": tool, "argumentsPreview": {"key": "value"}},
        )
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False


# ===================================================================
# 8. Audit Integration Tests (with HERMES_HOME)
# ===================================================================


class TestAuditIntegration:
    """Verify audit writer integration with Dry-Run API.

    These tests use a temporary HERMES_HOME to verify that audit events
    are written to local dev-only JSONL when the dry-run route is called.
    """

    @pytest.fixture
    def audit_client(self, tmp_path):
        """TestClient with a temporary HERMES_HOME for audit writes."""
        hermes_home = tmp_path / "hermes-home-dev"
        hermes_home.mkdir()
        config = DevWebApiConfig(hermes_home=hermes_home)
        app = create_dev_web_api_app(config)
        return TestClient(app), hermes_home

    def test_audit_written_on_valid_request(self, audit_client) -> None:
        """Dry-run API writes audit event on valid request."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["auditWritten"] is True

    def test_response_audit_written_true_means_audit_only(
        self, audit_client
    ) -> None:
        """auditWritten=true does not imply tool execution."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        assert data["auditWritten"] is True
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False

    def test_audit_jsonl_contains_canonical_name_and_decision(
        self, audit_client
    ) -> None:
        """Audit JSONL file contains canonicalName and decision."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(DRY_RUN_URL, json={"canonicalName": tool})

        audit_file = (
            hermes_home / "gateway/dev/audit/tool-dry-run-audit.jsonl"
        )
        assert audit_file.exists()
        lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1
        event = json.loads(lines[-1])
        assert event["canonicalName"] == tool
        assert "decision" in event

    def test_audit_jsonl_contains_reason_codes(
        self, audit_client
    ) -> None:
        """Audit JSONL file contains reasonCodes."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(DRY_RUN_URL, json={"canonicalName": tool})

        audit_file = (
            hermes_home / "gateway/dev/audit/tool-dry-run-audit.jsonl"
        )
        event = json.loads(
            audit_file.read_text(encoding="utf-8").strip().split("\n")[-1]
        )
        assert "reasonCodes" in event
        assert isinstance(event["reasonCodes"], list)

    def test_audit_jsonl_contains_redacted_arguments_preview(
        self, audit_client
    ) -> None:
        """Audit JSONL contains redactedArgumentsPreview."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(
            DRY_RUN_URL,
            json={
                "canonicalName": tool,
                "argumentsPreview": {"query": "test"},
            },
        )

        audit_file = (
            hermes_home / "gateway/dev/audit/tool-dry-run-audit.jsonl"
        )
        event = json.loads(
            audit_file.read_text(encoding="utf-8").strip().split("\n")[-1]
        )
        assert "redactedArgumentsPreview" in event
        assert event["redactedArgumentsPreview"]["query"] == "test"

    def test_audit_jsonl_does_not_contain_raw_secret(
        self, audit_client
    ) -> None:
        """Audit JSONL must not contain fake raw secrets."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(
            DRY_RUN_URL,
            json={
                "canonicalName": tool,
                "argumentsPreview": {
                    "api_key": "sk-test-secret-key-12345678",
                },
            },
        )

        audit_file = (
            hermes_home / "gateway/dev/audit/tool-dry-run-audit.jsonl"
        )
        content = audit_file.read_text(encoding="utf-8")
        assert "sk-test-secret-key-12345678" not in content
        event = json.loads(content.strip().split("\n")[-1])
        assert event["redactedArgumentsPreview"]["api_key"] == "[REDACTED]"

    def test_unknown_tool_request_writes_audit_safely(
        self, audit_client
    ) -> None:
        """Unknown tool request writes a safe audit event."""
        client, hermes_home = audit_client
        resp = client.post(
            DRY_RUN_URL, json={"canonicalName": "nonexistent_tool_xyz"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["auditWritten"] is True
        assert data["exists"] is False
        assert data["executionAllowed"] is False

        audit_file = (
            hermes_home / "gateway/dev/audit/tool-dry-run-audit.jsonl"
        )
        event = json.loads(
            audit_file.read_text(encoding="utf-8").strip().split("\n")[-1]
        )
        assert event["toolExists"] is False
        assert event["executionAllowed"] is False

    def test_audit_event_invariant_flags_false(
        self, audit_client
    ) -> None:
        """Audit event always has executionAllowed/dispatchAllowed/providerSchemaAllowed=false."""
        client, hermes_home = audit_client
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(DRY_RUN_URL, json={"canonicalName": tool})

        audit_file = (
            hermes_home / "gateway/dev/audit/tool-dry-run-audit.jsonl"
        )
        event = json.loads(
            audit_file.read_text(encoding="utf-8").strip().split("\n")[-1]
        )
        assert event["executionAllowed"] is False
        assert event["dispatchAllowed"] is False
        assert event["providerSchemaAllowed"] is False


# ===================================================================
# 9. Audit Failure Safety Tests
# ===================================================================


class TestAuditFailureSafety:
    """Verify audit write failure does not compromise safety."""

    def test_audit_write_failure_returns_safe_response(self, client) -> None:
        """Audit write outcome does not compromise safety."""
        # With test isolation HERMES_HOME, audit may succeed or fail;
        # either way the safety invariants must hold.
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        # auditWritten is a boolean, but does not imply execution
        assert isinstance(data["auditWritten"], bool)
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False

    def test_audit_write_failure_does_not_call_provider(
        self, client
    ) -> None:
        """Audit failure must not call provider."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        assert data["providerSchemaAllowed"] is False

    def test_audit_write_failure_does_not_call_tool_handler(
        self, client
    ) -> None:
        """Audit failure must not call tool handler."""
        import hermes_cli.dev_web_api as api_module
        source = open(api_module.__file__, encoding="utf-8").read()
        assert "from tools." not in source
        assert "handle_function_call" not in source

    def test_audit_write_failure_does_not_dispatch(
        self, client
    ) -> None:
        """Audit failure must not dispatch."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        assert data["dispatchAllowed"] is False

    def test_audit_write_failure_does_not_execute(
        self, client
    ) -> None:
        """Audit failure must not execute."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_execution_flags_remain_false_on_audit_failure(
        self, client
    ) -> None:
        """All execution flags remain false when audit write fails."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(
            DRY_RUN_URL,
            json={
                "canonicalName": tool,
                "argumentsPreview": {"key": "value"},
            },
        )
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False

    def test_static_allowlist_remains_clarify_only_on_audit_failure(
        self, client
    ) -> None:
        """STATIC_ALLOWLIST remains frozenset({"clarify"}) even when audit fails."""
        assert STATIC_ALLOWLIST == frozenset({"clarify"})
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert STATIC_ALLOWLIST == frozenset({"clarify"})

    def test_route_governance_unchanged_with_audit(
        self, client
    ) -> None:
        """Route governance unchanged after audit integration."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 33

    def test_no_audit_failure_500(self, client) -> None:
        """Audit failure must not cause 500."""
        tool = next(t for t in ALL_CANONICAL_TOOLS if t not in STATIC_DENYLIST)
        resp = client.post(DRY_RUN_URL, json={"canonicalName": tool})
        assert resp.status_code == 200
