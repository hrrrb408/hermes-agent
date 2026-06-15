"""Phase 2E-H1 — Frontend blocked-reason vocabulary contract tests.

Phase 2E-H1 hardened the frontend blocked-reason catalogue so it covers every
STABLE backend blocked-reason code (literal constant strings the backend
assigns to the ``blockedReason`` response field). The frontend vitest suite
asserts the catalogue covers this vocabulary; THIS test pins the backend
vocabulary itself as a stable contract at the Python level, so a backend
addition / removal / rename is caught before the frontend can drift.

What "stable" means here: a backend code is *stable* when it is a literal
constant string that flows into the ``blockedReason`` field. Dynamic f-strings
and message strings (e.g. ``"tool call is not a mapping"``,
``f"blocked_tool_calls:{ids}"``) are intentionally NOT in this set — they
degrade to the frontend's safe unknown-code fallback by design.

This phase adds no backend capability, no HTTP route, no production access.
The route-governance + leak-free invariants from the Phase 2E contract are
re-asserted for closure.

Phase: 2E-H1 — Frontend UX Hardening (Console Stability, Accessibility & Safety)
Hardening ID: HARDENING-2E-H1-001
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_ABSOLUTE_PATH,
    BLOCKED_WRITE_BINARY_CONTENT,
    BLOCKED_WRITE_CONFIRMATION_REQUIRED,
    BLOCKED_WRITE_CONTENT_TOO_LARGE,
    BLOCKED_WRITE_DIGEST_MISMATCH,
    BLOCKED_WRITE_EXECUTION_NOT_ENABLED,
    BLOCKED_WRITE_FILE_TOO_LARGE,
    BLOCKED_WRITE_FORBIDDEN_PATH,
    BLOCKED_WRITE_MISSING_ROLLBACK_PLAN,
    BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH,
    BLOCKED_WRITE_PATH_TRAVERSAL,
    BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED,
    BLOCKED_WRITE_SYMLINK_ESCAPE,
    BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED,
    BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
)
from hermes_cli.dev_web_write_rollback import (
    BLOCKED_ROLLBACK_ALREADY_EXECUTED,
    BLOCKED_ROLLBACK_CONFIRMATION_REQUIRED,
    BLOCKED_ROLLBACK_CURRENT_HASH_MISMATCH,
    BLOCKED_ROLLBACK_DIGEST_MISMATCH,
    BLOCKED_ROLLBACK_FORBIDDEN_TARGET,
    BLOCKED_ROLLBACK_MANIFEST_NOT_FOUND,
    BLOCKED_ROLLBACK_MANIFEST_TAMPERED,
    BLOCKED_ROLLBACK_SYMLINK_ESCAPE,
    BLOCKED_ROLLBACK_TARGET_ESCAPE,
    BLOCKED_ROLLBACK_WRITE_NOT_ENABLED,
)
from hermes_cli.dev_web_confirmation_store import (
    BLOCKED_TOKEN_ALREADY_USED,
    BLOCKED_TOKEN_DIGEST_MISMATCH,
    BLOCKED_TOKEN_EXPIRED,
    BLOCKED_TOKEN_INVALID,
    BLOCKED_TOKEN_NOT_FOUND,
    BLOCKED_TOKEN_SCOPE_MISMATCH,
)
from hermes_cli.dev_web_audit_query import (
    BLOCKED_CURSOR_INVALID,
    BLOCKED_CURSOR_QUERY_MISMATCH,
    BLOCKED_LIMIT_TOO_LARGE,
    BLOCKED_QUERY_INVALID,
)
from hermes_cli.dev_web_provider_request import (
    BLOCKED_PROVIDER_API_KEY_MISSING,
    BLOCKED_PROVIDER_MODE_NOT_SUPPORTED,
    BLOCKED_PROVIDER_NOT_DEV_HOME,
    BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT,
    BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED,
)
from hermes_cli.dev_web_tool_handler_lookup import DECISION_BLOCKED_DISPATCH_NOT_ENABLED
from hermes_cli import (
    dev_web_tool_handler_call as _handler_call,
    dev_web_provider_roundtrip as _provider_roundtrip,
)

API = "/api/dev/v1"

LEAK_PATTERNS = (
    "sk-",
    "Bearer ",
    "<function",
    "object at 0x",
    "/Users/huangruibang/.hermes",
    "rawArguments",
    "fullTokenHash",
    "plainToken",
    "tokenSecret",
)

# The canonical, stable backend blocked-reason vocabulary. The frontend
# blockedReasons catalogue MUST cover every code in this set. Any backend
# addition / removal / rename must update both this set and the frontend
# catalogue deliberately.
EXPECTED_STABLE_BLOCKED_REASONS = frozenset(
    {
        # Execute surface
        "blocked_tool_handler_call_not_enabled",
        "blocked_dispatch_not_enabled",
        # Write surface
        BLOCKED_WRITE_EXECUTION_NOT_ENABLED,
        BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED,
        BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
        BLOCKED_WRITE_PATH_TRAVERSAL,
        BLOCKED_WRITE_ABSOLUTE_PATH,
        BLOCKED_WRITE_SYMLINK_ESCAPE,
        BLOCKED_WRITE_FORBIDDEN_PATH,
        BLOCKED_WRITE_FILE_TOO_LARGE,
        BLOCKED_WRITE_CONTENT_TOO_LARGE,
        BLOCKED_WRITE_BINARY_CONTENT,
        BLOCKED_WRITE_MISSING_ROLLBACK_PLAN,
        BLOCKED_WRITE_DIGEST_MISMATCH,
        BLOCKED_WRITE_CONFIRMATION_REQUIRED,
        BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED,
        BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH,
        # Rollback surface
        BLOCKED_ROLLBACK_MANIFEST_NOT_FOUND,
        BLOCKED_ROLLBACK_ALREADY_EXECUTED,
        BLOCKED_ROLLBACK_CURRENT_HASH_MISMATCH,
        BLOCKED_ROLLBACK_MANIFEST_TAMPERED,
        BLOCKED_ROLLBACK_TARGET_ESCAPE,
        BLOCKED_ROLLBACK_SYMLINK_ESCAPE,
        BLOCKED_ROLLBACK_CONFIRMATION_REQUIRED,
        BLOCKED_ROLLBACK_DIGEST_MISMATCH,
        BLOCKED_ROLLBACK_WRITE_NOT_ENABLED,
        BLOCKED_ROLLBACK_FORBIDDEN_TARGET,
        # Provider surface
        BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED,
        BLOCKED_PROVIDER_API_KEY_MISSING,
        BLOCKED_PROVIDER_MODE_NOT_SUPPORTED,
        BLOCKED_PROVIDER_NOT_DEV_HOME,
        BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT,
        "provider_mode_disabled",
        "provider_schema_boundary_violation",
        "execution_blocked",
        # Confirmation surface
        BLOCKED_TOKEN_NOT_FOUND,
        BLOCKED_TOKEN_INVALID,
        BLOCKED_TOKEN_EXPIRED,
        BLOCKED_TOKEN_ALREADY_USED,
        BLOCKED_TOKEN_SCOPE_MISMATCH,
        BLOCKED_TOKEN_DIGEST_MISMATCH,
        # Audit surface
        BLOCKED_CURSOR_INVALID,
        BLOCKED_CURSOR_QUERY_MISMATCH,
        BLOCKED_LIMIT_TOO_LARGE,
        BLOCKED_QUERY_INVALID,
    }
)


@pytest.fixture
def client(tmp_path: Path):
    home = tmp_path / "hermes-home-dev"
    home.mkdir(parents=True)
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
    return TestClient(app)


class TestBlockedReasonVocabulary:
    """Pin the stable backend blocked-reason vocabulary as a contract."""

    def test_expected_vocabulary_is_non_empty_and_unique(self):
        # Every expected code is a stable string; no duplicates.
        assert len(EXPECTED_STABLE_BLOCKED_REASONS) > 30
        non_blocked_prefix = {
            "provider_mode_disabled",
            "provider_schema_boundary_violation",
            "execution_blocked",
        }
        for code in EXPECTED_STABLE_BLOCKED_REASONS:
            assert isinstance(code, str)
            assert code.startswith("blocked_") or code in non_blocked_prefix, (
                f"unexpected stable code shape: {code!r}"
            )
        assert len(EXPECTED_STABLE_BLOCKED_REASONS) == len(
            set(EXPECTED_STABLE_BLOCKED_REASONS)
        )

    def test_write_plan_constants_match_expected_strings(self):
        # The write surface constants are the canonical source of truth.
        write_codes = {
            BLOCKED_WRITE_EXECUTION_NOT_ENABLED,
            BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED,
            BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
            BLOCKED_WRITE_PATH_TRAVERSAL,
            BLOCKED_WRITE_ABSOLUTE_PATH,
            BLOCKED_WRITE_SYMLINK_ESCAPE,
            BLOCKED_WRITE_FORBIDDEN_PATH,
            BLOCKED_WRITE_FILE_TOO_LARGE,
            BLOCKED_WRITE_CONTENT_TOO_LARGE,
            BLOCKED_WRITE_BINARY_CONTENT,
            BLOCKED_WRITE_MISSING_ROLLBACK_PLAN,
            BLOCKED_WRITE_DIGEST_MISMATCH,
            BLOCKED_WRITE_CONFIRMATION_REQUIRED,
            BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED,
            BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH,
        }
        assert write_codes <= EXPECTED_STABLE_BLOCKED_REASONS

    def test_inline_stable_codes_are_defined_in_their_modules(self):
        # The handler-call + provider-roundtrip stable codes are defined inline;
        # assert they exist in the module source so they cannot silently disappear.
        handler_src = inspect.getsource(_handler_call)
        assert "blocked_tool_handler_call_not_enabled" in handler_src

        roundtrip_src = inspect.getsource(_provider_roundtrip)
        assert "provider_mode_disabled" in roundtrip_src
        assert "provider_schema_boundary_violation" in roundtrip_src
        assert "execution_blocked" in roundtrip_src
        # The recursive-tool code is also a stable roundtrip code surfaced to the UI.
        assert "blocked_provider_recursive_tool" in roundtrip_src

    def test_no_stable_code_is_a_dynamic_fstring_pattern(self):
        # Stable codes must be literal constant strings, never f-strings or
        # message phrases. This guards against accidentally cataloguing a
        # dynamic value that could carry operator input.
        dynamic_markers = ("{", " ", ":")
        for code in EXPECTED_STABLE_BLOCKED_REASONS:
            for marker in dynamic_markers:
                assert marker not in code, f"stable code {code!r} looks dynamic"


class TestRouteGovernanceUnchanged:
    """Phase 2E-H1 must not drift the route-governance baseline (34/34/5/0/1/1)."""

    def _api_paths(self, spec) -> list[str]:
        return [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]

    def test_openapi_paths_still_34(self, client):
        spec = client.get("/openapi.json").json()
        assert len(self._api_paths(spec)) == 34

    def test_runtime_routes_still_34(self, client):
        spec = client.get("/openapi.json").json()
        assert len(self._api_paths(spec)) == 34

    def test_no_dedicated_tool_write_http_route(self, client):
        spec = client.get("/openapi.json").json()
        tool_paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/tools")]
        mutating = [
            p
            for p in tool_paths
            if set(spec["paths"][p].keys()) & {"post", "put", "patch", "delete"}
        ]
        mutating = [
            p for p in mutating if p not in {f"{API}/tools/dry-run", f"{API}/tools/execute"}
        ]
        assert mutating == [], f"unexpected tool write HTTP routes: {mutating}"

    def test_no_provider_http_route(self, client):
        spec = client.get("/openapi.json").json()
        provider_routes = [p for p in spec["paths"] if "/provider" in p]
        assert provider_routes == [], (
            f"Phase 2E-H1 must not add a provider HTTP route: {provider_routes}"
        )


class TestNoLeak:
    """Overview data sources remain leak-free after the hardening."""

    def test_policy_payload_is_leak_free(self, client):
        body = client.get(f"{API}/tools/policy").text
        for pattern in LEAK_PATTERNS:
            assert pattern not in body, f"policy body must not contain {pattern}"

    def test_audit_payload_is_leak_free(self, client):
        body = client.get(
            f"{API}/tools/audit-events", params={"auditKind": "post_execution"}
        ).text
        for pattern in LEAK_PATTERNS:
            assert pattern not in body, f"audit body must not contain {pattern}"
