"""API-level tests for the read-only tool audit events route (Phase 1G-04-30).

Covers GET /api/dev/v1/tools/audit-events: success, query params, validation,
read-only guarantee, safety, and route governance (34/34/5/0/1/1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"
AUDIT_URL = f"{API}/tools/audit-events"


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def client_no_home() -> TestClient:
    return TestClient(create_dev_web_api_app(DevWebApiConfig(hermes_home=None)))


@pytest.fixture
def client_with_home(tmp_path: Path) -> tuple[TestClient, Path]:
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
    return TestClient(app), home


def _audit_dir(home: Path) -> Path:
    return home / "gateway" / "dev" / "audit"


def _write(home: Path, filename: str, events: list) -> None:
    p = _audit_dir(home) / filename
    with p.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


# ── Success ─────────────────────────────────────────────────────────────


class TestAuditEventsApiSuccess:
    def test_get_post_execution_success(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-post-execution-audit.jsonl",
            [
                {
                    "postExecutionAuditId": "pexa_1",
                    "executeRequestId": "exe_1",
                    "preExecutionAuditId": "pea_1",
                    "handlerLookupId": "hl_1",
                    "dispatchId": "dsp_1",
                    "handlerCallId": "thc_1",
                    "canonicalName": "clarify",
                    "executionStatus": "completed",
                    "handlerCallStatus": "completed",
                    "eventType": "clarify_execution_completed",
                    "sideEffectFlags": {
                        "providerSchemaSent": False,
                        "providerApiCalled": False,
                        "externalSideEffects": False,
                    },
                    "resultSummary": {
                        "toolResultType": "clarify",
                        "messageLength": 5,
                        "questionCount": 1,
                    },
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        resp = client.get(
            AUDIT_URL, params={"auditKind": "post_execution"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["auditKind"] == "post_execution"
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["auditId"] == "pexa_1"
        assert item["handlerCallId"] == "thc_1"
        assert item["sideEffects"]["providerSchemaSent"] is False
        assert item["sideEffects"]["providerApiCalled"] is False
        assert item["sideEffects"]["externalSideEffects"] is False
        assert item["safeSummary"]["questionCount"] == 1

    def test_get_dry_run_success(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-dry-run-audit.jsonl",
            [{"eventId": "e1", "canonicalName": "clarify", "decision": "would_allow"}],
        )
        resp = client.get(AUDIT_URL, params={"auditKind": "dry_run"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"][0]["decision"] == "would_allow"

    def test_get_pre_execution_success(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-pre-execution-audit.jsonl",
            [
                {
                    "preExecutionAuditId": "pea_1",
                    "executeRequestId": "exe_1",
                    "canonicalName": "clarify",
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        resp = client.get(AUDIT_URL, params={"auditKind": "pre_execution"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"][0]["auditId"] == "pea_1"

    def test_missing_file_returns_empty_items(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.get(AUDIT_URL, params={"auditKind": "dry_run"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["hasMore"] is False

    def test_limit_query_works(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-dry-run-audit.jsonl",
            [
                {"eventId": f"e{i}", "canonicalName": "clarify"} for i in range(5)
            ],
        )
        resp = client.get(
            AUDIT_URL, params={"auditKind": "dry_run", "limit": 2}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["hasMore"] is True
        assert data["nextCursor"] == "2"

    def test_canonical_name_filter(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-dry-run-audit.jsonl",
            [
                {"eventId": "a", "canonicalName": "clarify"},
                {"eventId": "b", "canonicalName": "read_file"},
            ],
        )
        resp = client.get(
            AUDIT_URL,
            params={"auditKind": "dry_run", "canonicalName": "clarify"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [i["auditId"] for i in data["items"]] == ["a"]

    def test_cursor_pagination(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-dry-run-audit.jsonl",
            [
                {"eventId": f"e{i}", "canonicalName": "clarify"} for i in range(5)
            ],
        )
        resp1 = client.get(
            AUDIT_URL, params={"auditKind": "dry_run", "limit": 2}
        )
        cursor = resp1.json()["data"]["nextCursor"]
        resp2 = client.get(
            AUDIT_URL,
            params={"auditKind": "dry_run", "limit": 2, "cursor": cursor},
        )
        assert [i["auditId"] for i in resp2.json()["data"]["items"]] == ["e2", "e1"]


# ── Validation errors ───────────────────────────────────────────────────


class TestAuditEventsApiValidation:
    def test_invalid_audit_kind_returns_400(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.get(AUDIT_URL, params={"auditKind": "bogus"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "TOOL_AUDIT_EVENTS_INVALID_KIND"

    def test_missing_audit_kind_returns_422(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.get(AUDIT_URL)
        # FastAPI Query(required=True) → 422
        assert resp.status_code == 422

    def test_invalid_cursor_returns_400(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.get(
            AUDIT_URL,
            params={"auditKind": "dry_run", "cursor": "abc"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "TOOL_AUDIT_EVENTS_INVALID_CURSOR"

    def test_no_hermes_home_returns_503(self, client_no_home) -> None:
        resp = client_no_home.get(AUDIT_URL, params={"auditKind": "dry_run"})
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "TOOL_AUDIT_EVENTS_UNAVAILABLE"


# ── Read-only guarantee ─────────────────────────────────────────────────


class TestAuditEventsApiReadOnly:
    def test_post_not_allowed(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.post(AUDIT_URL, json={"auditKind": "dry_run"})
        assert resp.status_code == 405

    def test_put_not_allowed(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.put(AUDIT_URL, json={"auditKind": "dry_run"})
        assert resp.status_code == 405

    def test_delete_not_allowed(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.delete(AUDIT_URL)
        assert resp.status_code == 405

    def test_patch_not_allowed(self, client_with_home) -> None:
        client, _ = client_with_home
        resp = client.patch(AUDIT_URL, json={"auditKind": "dry_run"})
        assert resp.status_code == 405


# ── Safety: no secrets / raw token / raw arguments / production path ────


class TestAuditEventsApiSafety:
    def test_no_raw_token_in_response(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-pre-execution-audit.jsonl",
            [
                {
                    "preExecutionAuditId": "pea_1",
                    "confirmationToken": "raw-token-secret-abc",
                    "tokenHash": "aabbccdd" * 8,
                    "canonicalName": "clarify",
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        resp = client.get(AUDIT_URL, params={"auditKind": "pre_execution"})
        text = json.dumps(resp.json())
        assert "raw-token-secret-abc" not in text
        assert "aabbccdd" not in text
        assert "confirmationToken" not in text
        assert "tokenHash" not in text

    def test_no_raw_arguments_in_response(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-dry-run-audit.jsonl",
            [
                {
                    "eventId": "e1",
                    "canonicalName": "clarify",
                    "argumentsPreview": {"secret": "super-secret"},
                    "redactedArgumentsPreview": {"api_key": "[REDACTED]"},
                }
            ],
        )
        resp = client.get(AUDIT_URL, params={"auditKind": "dry_run"})
        text = json.dumps(resp.json())
        assert "super-secret" not in text
        assert "argumentsPreview" not in text
        assert "redactedArgumentsPreview" not in text

    def test_no_secrets_in_response(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-dry-run-audit.jsonl",
            [
                {
                    "eventId": "e1",
                    "canonicalName": "clarify",
                    "sourceContext": "sk-test-fake-redacted-value-12345678",
                    "authorization": "Bearer fake-token",
                }
            ],
        )
        resp = client.get(AUDIT_URL, params={"auditKind": "dry_run"})
        text = json.dumps(resp.json())
        assert "sk-test-fake-redacted-value-12345678" not in text
        assert "Bearer fake-token" not in text

    def test_no_production_path_in_response(self, client_with_home) -> None:
        client, _ = client_with_home
        for kind in ("dry_run", "pre_execution", "post_execution"):
            resp = client.get(AUDIT_URL, params={"auditKind": kind})
            text = json.dumps(resp.json())
            assert "/Users/huangruibang/.hermes" not in text
            assert "/home/" not in text

    def test_no_callable_or_provider_payload(self, client_with_home) -> None:
        client, home = client_with_home
        _write(
            home,
            "tool-post-execution-audit.jsonl",
            [
                {
                    "postExecutionAuditId": "pexa_1",
                    "canonicalName": "clarify",
                    "providerPayload": {"apiKey": "sk-leak"},
                    "callable": "<function at 0x1>",
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        resp = client.get(AUDIT_URL, params={"auditKind": "post_execution"})
        text = json.dumps(resp.json())
        assert "providerPayload" not in text
        assert "sk-leak" not in text
        assert "<function at" not in text


# ── Route governance: 34 / 34 / 5 / 0 / 1 / 1 ──────────────────────────


class TestAuditEventsApiRouteGovernance:
    def test_business_paths_count_is_34(self, client_with_home) -> None:
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 34

    def test_tool_get_routes_count_is_5(self, client_with_home) -> None:
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        tool_paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/tools")]
        get_routes = [
            p for p in tool_paths if "get" in spec["paths"][p]
        ]
        assert len(get_routes) == 5
        assert "/api/dev/v1/tools/audit-events" in get_routes

    def test_tool_write_routes_remain_0(self, client_with_home) -> None:
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        tool_paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/tools")]
        # No PUT/PATCH/DELETE on any tool path
        for p in tool_paths:
            methods = set(spec["paths"][p].keys()) & {
                "get", "post", "put", "patch", "delete"
            }
            assert not (methods & {"put", "patch", "delete"}), p

    def test_audit_events_is_get_only(self, client_with_home) -> None:
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        methods = set(
            spec["paths"]["/api/dev/v1/tools/audit-events"].keys()
        ) & {"get", "post", "put", "patch", "delete"}
        assert methods == {"get"}

    def test_static_allowlist_remains_clarify_only(self) -> None:
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

        assert STATIC_ALLOWLIST == frozenset({"clarify", "tool_policy_read", "route_governance_read", "audit_events_read", "dev_environment_read", "release_status_read"})

    def test_no_provider_routes(self, client_with_home) -> None:
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        provider_paths = [
            p for p in spec["paths"] if "provider" in p.lower()
        ]
        assert provider_paths == []
