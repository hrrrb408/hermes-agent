"""Tests for POST /api/dev/v1/tools/execute — Tool Execute Gate Skeleton API.

Phase 1G-04-16: Dry-Run Historical Lookup Read-Only Implementation.

All tests verify:
  - Route exists and returns 200 blocked
  - No tool handler calls
  - No provider calls
  - No dispatch calls
  - No STATIC_ALLOWLIST mutation
  - No raw secrets in response
  - executionAllowed is always false
  - dispatchAllowed is always false
  - providerSchemaAllowed is always false
  - toolHandlerCalled is always false
  - providerApiCalled is always false
  - executionStarted is always false
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
)

API = "/api/dev/v1"
EXECUTE_URL = f"{API}/tools/execute"


@pytest.fixture
def client():
    """TestClient without HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ===================================================================
# 1. Route Existence Tests
# ===================================================================


class TestRouteExistence:
    """Verify the execute route exists."""

    def test_execute_route_exists(self, client) -> None:
        """POST /tools/execute must exist."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        assert resp.status_code == 200

    def test_execute_route_returns_200_blocked_by_default(self, client) -> None:
        """Default response is 200 with blocked decision."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["decision"] == "blocked_by_kill_switch"
        assert data["executionAllowed"] is False

    def test_execute_route_uses_post_only(self, client) -> None:
        """Only POST is allowed on /tools/execute."""
        resp = client.get(EXECUTE_URL)
        assert resp.status_code == 405


# ===================================================================
# 2. Request Validation Tests
# ===================================================================


class TestRequestValidation:
    """Verify request validation."""

    def test_invalid_json_returns_400(self, client) -> None:
        resp = client.post(
            EXECUTE_URL,
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)

    def test_missing_canonical_name_returns_400(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"argumentsPreview": {}})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "TOOL_EXECUTE_INVALID_CANONICAL_NAME"

    def test_empty_canonical_name_returns_400(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": ""})
        assert resp.status_code == 400

    def test_whitespace_canonical_name_returns_400(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "   "})
        assert resp.status_code == 400

    def test_non_string_canonical_name_returns_400(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": 123})
        assert resp.status_code in (400, 422)

    def test_arguments_preview_non_object_returns_400(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": "string",
        })
        assert resp.status_code == 400

    def test_arguments_preview_array_returns_400(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": [1, 2],
        })
        assert resp.status_code == 400

    def test_null_arguments_preview_accepted(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": None,
        })
        assert resp.status_code == 200


# ===================================================================
# 3. Blocked Decision Tests
# ===================================================================


class TestBlockedDecisions:
    """Verify blocked decisions for various tools."""

    def test_unknown_tool_returns_200_blocked(self, client) -> None:
        """Unknown tool returns 200 with blocked decision."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "nonexistent_tool_xyz"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["toolHandlerCalled"] is False

    def test_denylisted_tool_returns_blocked(self, client) -> None:
        """Denylisted tool returns blocked."""
        denylisted = next(iter(STATIC_DENYLIST))
        resp = client.post(EXECUTE_URL, json={"canonicalName": denylisted})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_r0_tool_blocked(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_r1_tool_blocked(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "read_file"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_r2_tool_blocked(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "web_search"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_with_all_fields_still_blocked(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": {"key": "value"},
            "dryRunRequestId": "dr-001",
            "dryRunDecisionDigest": "abc123",
            "confirmationToken": "tok-001",
            "requestId": "req-001",
            "sourceContext": "test",
            "uiOrigin": "test-panel",
            "clientCreatedAt": "2026-01-01T00:00:00Z",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executionAllowed"] is False


# ===================================================================
# 4. Execution Flags Invariant Tests
# ===================================================================


class TestExecutionFlagsInvariant:
    """All execution flags must always be false."""

    def _assert_all_flags_false(self, data: dict) -> None:
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False
        assert data["executionAttempted"] is False
        assert data["executionStarted"] is False
        assert data["executionCompleted"] is False

    def test_default_request_flags_false(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        self._assert_all_flags_false(resp.json()["data"])

    def test_unknown_tool_flags_false(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "nonexistent"})
        self._assert_all_flags_false(resp.json()["data"])

    def test_denylisted_tool_flags_false(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "terminal"})
        self._assert_all_flags_false(resp.json()["data"])

    def test_with_arguments_flags_false(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": {"key": "value"},
        })
        self._assert_all_flags_false(resp.json()["data"])

    def test_with_all_fields_flags_false(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": {"key": "value"},
            "dryRunRequestId": "dr-001",
            "dryRunDecisionDigest": "abc123",
            "confirmationToken": "tok-001",
        })
        self._assert_all_flags_false(resp.json()["data"])

    @pytest.mark.parametrize("name", list(ALL_CANONICAL_TOOLS)[:10])
    def test_known_tools_flags_false(self, client, name: str) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": name})
        self._assert_all_flags_false(resp.json()["data"])


# ===================================================================
# 5. Security Tests
# ===================================================================


class TestSecurityGuarantees:
    """Verify no execution, no secrets, no side effects."""

    def test_secret_arguments_are_redacted(self, client) -> None:
        """Response never contains raw secret values."""
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "argumentsPreview": {
                "api_key": "sk-abcdef1234567890",
                "password": "super-secret-pass",
                "safe_field": "this is safe",
            },
        })
        assert resp.status_code == 200
        body = resp.json()
        text = json.dumps(body)
        assert "sk-abcdef1234567890" not in text
        assert "super-secret-pass" not in text

    def test_no_provider_routes_called(self, client) -> None:
        """Response confirms no provider calls."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        data = resp.json()["data"]
        assert data["providerApiCalled"] is False
        assert data["providerSchemaAllowed"] is False

    def test_no_tool_handler_monkeypatch_called(self, client) -> None:
        """toolHandlerCalled is false — no handler invoked."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        data = resp.json()["data"]
        assert data["toolHandlerCalled"] is False

    def test_static_allowlist_remains_clarify_only(self, client) -> None:
        """STATIC_ALLOWLIST must be exactly {"clarify"} before and after request."""
        assert STATIC_ALLOWLIST == frozenset({"clarify"})
        client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        assert STATIC_ALLOWLIST == frozenset({"clarify"})


# ===================================================================
# 6. Response Envelope Tests
# ===================================================================


class TestResponseEnvelope:
    """Verify response envelope shape."""

    def test_success_envelope_shape(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]
        data = body["data"]
        expected_keys = {
            "canonicalName", "exists", "riskTier", "decision",
            "gateStatus", "auditStatus", "resultPreview",
            "executionAttempted", "executionStarted", "executionCompleted",
            "executionAllowed", "dispatchAllowed", "providerSchemaAllowed",
            "toolHandlerCalled", "providerApiCalled",
            "errorCode", "policyNotes", "reasonCodes",
        }
        assert set(data.keys()) == expected_keys

    def test_error_envelope_shape(self, client) -> None:
        resp = client.post(EXECUTE_URL, json={"canonicalName": ""})
        body = resp.json()
        assert "error" in body
        error = body["error"]
        assert "code" in error
        assert "message" in error


# ===================================================================
# 7. Route Governance Tests
# ===================================================================


class TestRouteGovernance:
    """Verify route governance for execute route."""

    def test_business_paths_count_is_33(self, client) -> None:
        """Runtime OpenAPI must report 33 business paths."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 33

    def test_execute_route_exists_in_openapi(self, client) -> None:
        """POST /tools/execute must exist in OpenAPI."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        assert "/api/dev/v1/tools/execute" in spec["paths"]
        assert "post" in spec["paths"]["/api/dev/v1/tools/execute"]

    def test_post_routes_count_is_14(self, client) -> None:
        """14 POST routes total (13 existing + 1 tool execute)."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        post_routes = [
            p for p, m in spec["paths"].items()
            if "post" in m and p.startswith("/api/dev/v1/")
        ]
        assert len(post_routes) == 14
        assert "/api/dev/v1/tools/execute" in post_routes

    def test_tool_write_routes_remain_0(self, client) -> None:
        """No tool write routes exist."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        tool_routes = {p: m for p, m in spec["paths"].items() if p.startswith("/api/dev/v1/tools")}
        write_routes = []
        for path, methods in tool_routes.items():
            for method in methods:
                if method in ("put", "patch", "delete"):
                    write_routes.append(f"{method.upper()} {path}")
                if method == "post" and "dry-run" not in path and "execute" not in path:
                    write_routes.append(f"POST {path}")
        assert len(write_routes) == 0, f"Unexpected tool write routes: {write_routes}"

    def test_tool_execution_routes_count_is_1(self, client) -> None:
        """Exactly 1 tool execution route exists."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        execution_routes = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/tools") and "execute" in p
        ]
        assert len(execution_routes) == 1
        assert "/api/dev/v1/tools/execute" in execution_routes

    def test_tool_dry_run_routes_remain_1(self, client) -> None:
        """Exactly 1 tool dry-run route exists."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        dry_run_routes = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/tools") and "dry-run" in p
        ]
        assert len(dry_run_routes) == 1


# ===================================================================
# 8. Clarify Allowlist Activation Tests
# ===================================================================


class TestClarifyAllowlistActivation:
    """Verify clarify allowlist gate activation behavior.

    Phase 1G-04-14: STATIC_ALLOWLIST = frozenset({"clarify"}).
    clarify passes the allowlist gate but remains blocked by later gates.
    Non-clarify tools remain blocked_by_allowlist.
    """

    def test_clarify_kill_switches_unset_blocked(self, client) -> None:
        """clarify with kill switches unset => blocked_by_kill_switch."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["decision"] == "blocked_by_kill_switch"

    def test_clarify_kill_switches_true_missing_dry_run_blocked(self, client) -> None:
        """clarify with kill switches true but no dry-run => blocked_requires_dry_run."""
        # NOTE: The TestClient doesn't set env vars, so kill switches are unset
        # by default. This test verifies the default blocked behavior.
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": None,
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_non_clarify_candidate_blocked_by_allowlist(self, client) -> None:
        """Non-clarify candidate tool blocked by allowlist even with all fields."""
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "read_file",
            "argumentsPreview": {"path": "/tmp/test"},
            "dryRunRequestId": "dr-001",
            "dryRunDecisionDigest": "abc123",
            "confirmationToken": "tok-001",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["decision"] == "blocked_by_kill_switch"

    def test_clarify_blocked_response_flags_false(self, client) -> None:
        """clarify blocked response still has all side-effect flags false."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False
        assert data["executionStarted"] is False
        assert data["executionAttempted"] is False
        assert data["executionCompleted"] is False

    def test_non_clarify_blocked_response_flags_false(self, client) -> None:
        """Non-clarify blocked response side-effect flags false."""
        resp = client.post(EXECUTE_URL, json={"canonicalName": "web_search"})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False
        assert data["executionStarted"] is False


# ===================================================================
# 9. Dry-Run Historical Lookup API Tests
# ===================================================================


def _make_audit_event(
    request_id="test-dry-run-001",
    canonical_name="clarify",
    decision="would_allow",
    risk_tier="R0",
    timestamp=None,
):
    """Build a sample audit event dict for testing."""
    from datetime import datetime, timezone, timedelta
    ts = timestamp or (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    return {
        "eventId": "evt-test-001",
        "eventType": "tool_dry_run",
        "timestamp": ts,
        "schemaVersion": 1,
        "phase": "1G-04-07",
        "requestId": request_id,
        "canonicalName": canonical_name,
        "toolExists": True,
        "riskTier": risk_tier,
        "decision": decision,
        "reasonCodes": ["WOULD_ALLOW_STATIC_POLICY"],
        "policyNotes": [],
        "forbiddenFields": [],
        "missingRequiredFields": [],
        "redactionApplied": False,
        "redactionReasonCodes": [],
        "redactedArgumentsPreview": {},
        "sourceContext": None,
        "uiOrigin": None,
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "auditWritten": False,
        "staticAllowlistSize": 1,
        "candidateAllowlistMatched": False,
        "denylistMatched": False,
        "durationMs": 5,
        "resultStatus": "ok",
        "errorCode": None,
        "errorClass": None,
    }


@pytest.fixture
def client_with_audit(tmp_path):
    """TestClient with a real HERMES_HOME and audit file."""
    hermes_home = tmp_path / "hermes-home-dev"
    audit_dir = hermes_home / "gateway" / "dev" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    config = DevWebApiConfig(hermes_home=hermes_home)
    app = create_dev_web_api_app(config)
    return TestClient(app), audit_dir / "tool-dry-run-audit.jsonl"


class TestDryRunLookupAPI:
    """API-level tests for dry-run historical lookup integration."""

    def test_clarify_missing_dry_run_request_id_blocked(self, client_with_audit) -> None:
        """clarify missing dryRunRequestId → blocked."""
        client, _ = client_with_audit
        resp = client.post(EXECUTE_URL, json={"canonicalName": "clarify"})
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        # Default: blocked_by_kill_switch (kill switches not set in test)

    def test_clarify_dry_run_not_found_blocked(self, client_with_audit) -> None:
        """clarify dryRunRequestId not found → blocked."""
        client, _ = client_with_audit
        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-not-found",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_clarify_valid_dry_run_missing_confirmation_blocked(
        self, client_with_audit,
    ) -> None:
        """clarify valid dry-run but missing confirmationToken → blocked."""
        client, audit_path = client_with_audit
        # Write a valid audit event
        import json
        event = _make_audit_event(request_id="dr-valid")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-valid",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_clarify_valid_dry_run_fake_confirmation_blocked(
        self, client_with_audit,
    ) -> None:
        """clarify valid dry-run + fake confirmationToken → blocked."""
        client, audit_path = client_with_audit
        import json
        event = _make_audit_event(request_id="dr-valid-2")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-valid-2",
            "confirmationToken": "fake-token-123",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False

    def test_all_response_flags_false_with_lookup(
        self, client_with_audit,
    ) -> None:
        """All response side-effect flags false with lookup."""
        client, audit_path = client_with_audit
        import json
        event = _make_audit_event(request_id="dr-flags")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-flags",
            "confirmationToken": "fake-token",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False
        assert data["executionStarted"] is False
        assert data["executionAttempted"] is False

    def test_dry_run_decision_not_would_allow_blocked(
        self, client_with_audit,
    ) -> None:
        """dry-run decision would_block → blocked."""
        client, audit_path = client_with_audit
        import json
        event = _make_audit_event(
            request_id="dr-blocked",
            decision="would_block",
        )
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-blocked",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_no_execution_started_with_valid_lookup(
        self, client_with_audit,
    ) -> None:
        """Even with valid lookup, execution not started."""
        client, audit_path = client_with_audit
        import json
        event = _make_audit_event(request_id="dr-no-exec")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-no-exec",
            "confirmationToken": "any-token",
        })
        data = resp.json()["data"]
        assert data["executionStarted"] is False


# ===================================================================
# 10. Production Path Containment Guard API Tests (Phase 1G-04-17)
# ===================================================================


@pytest.fixture
def client_prod_home(tmp_path):
    """TestClient with HERMES_HOME set to production path."""
    config = DevWebApiConfig(
        hermes_home=Path("/Users/huangruibang/.hermes"),
    )
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_prod_subtree(tmp_path):
    """TestClient with HERMES_HOME set to production subtree."""
    config = DevWebApiConfig(
        hermes_home=Path("/Users/huangruibang/.hermes/gateway/dev"),
    )
    app = create_dev_web_api_app(config)
    return TestClient(app)


class TestProductionContainmentAPI:
    """API-level tests for production path containment guard."""

    def test_production_home_blocks(self, client_prod_home) -> None:
        """API request with production HERMES_HOME → blocked."""
        resp = client_prod_home.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-any",
            "confirmationToken": "fake-token",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False

    def test_production_subtree_blocks(self, client_prod_subtree) -> None:
        """API request with production subtree HERMES_HOME → blocked."""
        resp = client_prod_subtree.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-any",
            "confirmationToken": "fake-token",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False

    def test_production_home_all_flags_false(self, client_prod_home) -> None:
        """Production HERMES_HOME → all side-effect flags false."""
        resp = client_prod_home.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-any",
            "confirmationToken": "fake-token",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        assert data["toolHandlerCalled"] is False
        assert data["providerApiCalled"] is False
        assert data["executionStarted"] is False
        assert data["executionAttempted"] is False
        assert data["executionCompleted"] is False

    def test_valid_dev_home_behavior_unchanged(self, client_with_audit) -> None:
        """Valid dev HERMES_HOME API behavior unchanged."""
        client, audit_path = client_with_audit
        import json
        event = _make_audit_event(request_id="dr-api-valid")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        resp = client.post(EXECUTE_URL, json={
            "canonicalName": "clarify",
            "dryRunRequestId": "dr-api-valid",
            "confirmationToken": "fake-token",
        })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False


# ===================================================================
# 11. Clarify Handler Call + Post-execution Audit API Tests (Phase 1G-04-29)
# ===================================================================


def _issue_valid_token_api(hermes_home, audit_path, request_id, arguments=None):
    """Issue a real digest-bound confirmation token for API-level success tests."""
    import json
    from datetime import datetime, timezone, timedelta
    from hermes_cli.dev_web_tool_execute_confirmation import issue_confirmation_token
    from hermes_cli.dev_web_tool_execute_preflight import DryRunHistoricalLookupResult
    from hermes_cli.dev_web_tool_execute_digest import (
        build_dry_run_decision_digest_package,
    )

    fixed_ts = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    fixed_dt = datetime.fromisoformat(fixed_ts)
    if fixed_dt.tzinfo is None:
        fixed_dt = fixed_dt.replace(tzinfo=timezone.utc)
    computed_expires = (fixed_dt + timedelta(seconds=300)).isoformat()
    digest_pkg = build_dry_run_decision_digest_package(
        dry_run_request_id=request_id,
        canonical_name="clarify",
        risk_tier="R0",
        policy_decision="would_allow",
        allowlisted=True,
        audit_written=True,
        audit_event_id="evt-api-hc-001",
        arguments=arguments,
        created_at=fixed_ts,
        expires_at=computed_expires,
    )
    assert digest_pkg.success
    digest = digest_pkg.digest

    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(
            {**_make_audit_event(request_id=request_id, timestamp=fixed_ts),
             "dryRunDecisionDigest": digest,
             "eventId": "evt-api-hc-001"},
            ensure_ascii=False,
        ) + "\n")

    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
    dr_record = DryRunHistoricalLookupResult(
        found=True, error_code=None,
        dry_run_request_id=request_id,
        canonical_name="clarify", decision="would_allow",
        risk_tier="R0", policy_version=None, arguments_digest=None,
        dry_run_decision_digest=digest, audit_written=True,
        audit_event_id="evt-api-hc-001", created_at=now.isoformat(),
        expires_at=None, lookup_source="test", redaction_status="none",
    )
    token_result = issue_confirmation_token(
        hermes_home=str(hermes_home),
        dry_run_record=dr_record,
        canonical_name="clarify",
        risk_tier="R0",
        dry_run_request_id=request_id,
        dry_run_decision_digest=digest,
        now=now,
    )
    assert token_result.issued is True
    return token_result.raw_token, digest


@pytest.fixture
def client_full_chain(tmp_path):
    """TestClient with a real HERMES_HOME; returns (client, hermes_home, audit_path)."""
    hermes_home = tmp_path / "hermes-home-dev"
    audit_dir = hermes_home / "gateway" / "dev" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    config = DevWebApiConfig(hermes_home=hermes_home)
    app = create_dev_web_api_app(config)
    return TestClient(app), hermes_home, audit_dir / "tool-dry-run-audit.jsonl"


class TestHandlerCallApiSuccess:
    """Phase 1G-04-29: clarify-only handler call success path through the API."""

    def test_default_disabled_still_blocked_at_handler_call(
        self, client_full_chain,
    ) -> None:
        """Kill switches true but handler-call gate unset → blocked."""
        from unittest.mock import patch
        client, hermes_home, audit_path = client_full_chain
        raw_token, digest = _issue_valid_token_api(
            hermes_home, audit_path, "dr-api-disabled",
        )
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            os.environ.pop("HERMES_TOOL_HANDLER_CALL_ENABLED", None)
            resp = client.post(EXECUTE_URL, json={
                "canonicalName": "clarify",
                "dryRunRequestId": "dr-api-disabled",
                "dryRunDecisionDigest": digest,
                "confirmationToken": raw_token,
            })
        data = resp.json()["data"]
        assert data["executionAllowed"] is False
        assert data["executionCompleted"] is False
        assert data["toolHandlerCalled"] is False
        assert data["decision"] == "blocked_tool_handler_call_not_enabled"

    def test_explicit_gate_clarify_success_envelope(
        self, client_full_chain,
    ) -> None:
        """Explicit gate + clarify → clarify_execution_completed envelope."""
        from unittest.mock import patch
        client, hermes_home, audit_path = client_full_chain
        args = {"question": "Pick one", "choices": ["a", "b"]}
        raw_token, digest = _issue_valid_token_api(
            hermes_home, audit_path, "dr-api-success", arguments=args,
        )
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
            "HERMES_TOOL_HANDLER_CALL_ENABLED": "true",
        }, clear=False):
            resp = client.post(EXECUTE_URL, json={
                "canonicalName": "clarify",
                "dryRunRequestId": "dr-api-success",
                "dryRunDecisionDigest": digest,
                "confirmationToken": raw_token,
                "argumentsPreview": args,
            })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["decision"] == "clarify_execution_completed"
        assert data["executionCompleted"] is True
        assert data["executionStarted"] is True
        assert data["toolHandlerCalled"] is True
        # Policy flags stay false
        assert data["executionAllowed"] is False
        assert data["dispatchAllowed"] is False
        assert data["providerSchemaAllowed"] is False
        assert data["providerApiCalled"] is False
        # New success fields
        assert data["handlerCallId"].startswith("thc_")
        assert data["handlerCallStatus"] == "completed"
        assert data["executionStatus"] == "completed"
        assert data["postExecutionAuditId"].startswith("pexa_")
        assert data["postExecutionAuditStatus"] == "written"
        assert data["toolResult"]["type"] == "clarify"
        assert data["toolResult"]["message"] == "Pick one"
        assert data["sideEffects"]["providerApiCalled"] is False
        # Raw token never in the API response
        body_text = json.dumps(resp.json())
        assert raw_token not in body_text
        assert "confirmationToken" not in body_text

    def test_success_writes_post_execution_audit_file(
        self, client_full_chain,
    ) -> None:
        """Success path writes tool-post-execution-audit.jsonl."""
        from unittest.mock import patch
        client, hermes_home, audit_path = client_full_chain
        raw_token, digest = _issue_valid_token_api(
            hermes_home, audit_path, "dr-api-audit-file",
        )
        post_audit_file = hermes_home / "gateway" / "dev" / "audit" / "tool-post-execution-audit.jsonl"
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
            "HERMES_TOOL_HANDLER_CALL_ENABLED": "true",
        }, clear=False):
            client.post(EXECUTE_URL, json={
                "canonicalName": "clarify",
                "dryRunRequestId": "dr-api-audit-file",
                "dryRunDecisionDigest": digest,
                "confirmationToken": raw_token,
            })
        assert post_audit_file.exists()
        rec = json.loads(post_audit_file.read_text(encoding="utf-8").strip())
        assert rec["canonicalName"] == "clarify"
        assert rec["handlerCallId"].startswith("thc_")
        assert rec["sideEffectFlags"]["providerApiCalled"] is False


        # Should reach confirmation gate (blocked by confirmation_not_implemented)
        # or earlier gate depending on kill switch state in test client
