"""Phase 2D — Audit API (durable store path) tests.

Verifies the enhanced ``GET /api/dev/v1/tools/audit-events`` route:
  - store-mode response shape (storeStatus / indexStatus / schemaVersion /
    previousCursor / query)
  - cursor pagination via the route
  - filters via the route
  - safe search via the route
  - cursor tamper / mismatch rejection
  - legacy offset mode preserved (backward compatibility)
  - route governance unchanged (34 paths, 5 tool GETs, 0 write, GET-only)
  - no secret / raw argument / callable repr / production path in output
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_tool_dry_run_audit import (
    build_dry_run_audit_event,
    write_dry_run_audit_event,
)

API = "/api/dev/v1"
AUDIT_URL = f"{API}/tools/audit-events"


@pytest.fixture
def client_with_home(tmp_path: Path):
    home = tmp_path / "hermes-home-dev"
    home.mkdir(parents=True)
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
    return TestClient(app), home


class _FakeDryRun:
    def to_safe_dict(self):
        return {
            "canonicalName": "clarify", "exists": True, "riskTier": "P0",
            "decision": "would_block", "reasonCodes": [],
            "policyNotes": [], "redactedArgumentsPreview": {},
            "forbiddenFields": ["api_key"], "missingRequiredFields": [],
            "executionAllowed": False, "dispatchAllowed": False,
            "providerSchemaAllowed": False, "auditWritten": False,
        }


def _seed_dry_run(home: Path, n=3):
    for i in range(n):
        ev = build_dry_run_audit_event(dry_run_result=_FakeDryRun(), request_id=f"req-{i}")
        write_dry_run_audit_event(ev, hermes_home=str(home))


class TestStoreModeResponse:
    def test_store_mode_returns_enriched_shape(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 2)
        resp = client.get(AUDIT_URL, params={"auditKind": "dry_run", "search": "clarify"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        for key in ("items", "nextCursor", "previousCursor", "hasMore",
                    "storeStatus", "indexStatus", "schemaVersion", "query"):
            assert key in data
        assert data["schemaVersion"] == "audit_schema_v2"
        assert data["storeStatus"]["schemaVersion"] == "audit_schema_v2"

    def test_store_mode_with_filter(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 3)
        resp = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "toolId": "clarify", "limit": 10,
        })
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(i["toolId"] == "clarify" for i in items)
        assert len(items) == 3

    def test_store_mode_pagination(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 5)
        r1 = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "search": "clarify", "limit": 2,
        })
        d1 = r1.json()["data"]
        assert len(d1["items"]) == 2
        assert d1["hasMore"] is True
        r2 = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "search": "clarify", "limit": 2,
            "cursor": d1["nextCursor"],
        })
        assert r2.status_code == 200
        d2 = r2.json()["data"]
        assert len(d2["items"]) == 2


class TestStoreModeValidation:
    def test_cursor_tamper_returns_400(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 2)
        resp = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "search": "clarify", "cursor": "!!garbage!!",
        })
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "TOOL_AUDIT_EVENTS_INVALID_CURSOR"

    def test_cursor_query_mismatch_returns_400(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 3)
        r1 = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "toolId": "clarify", "limit": 1,
        })
        nc = r1.json()["data"]["nextCursor"]
        # Change filter → mismatch.
        r2 = client.get(AUDIT_URL, params={
            "auditKind": "rollback", "limit": 1, "cursor": nc,
        })
        assert r2.status_code == 400

    def test_provider_kind_only_in_store_mode(self, client_with_home):
        client, home = client_with_home
        # provider kind is valid in store mode (search present).
        resp = client.get(AUDIT_URL, params={
            "auditKind": "provider", "search": "x",
        })
        assert resp.status_code == 200
        # ...but rejected in legacy mode.
        resp2 = client.get(AUDIT_URL, params={"auditKind": "provider"})
        assert resp2.status_code == 400


class TestLegacyBackwardCompat:
    def test_legacy_mode_still_works(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 2)
        resp = client.get(AUDIT_URL, params={"auditKind": "dry_run", "limit": 2})
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Legacy shape: auditKind / items / nextCursor / hasMore / skippedMalformed.
        assert data["auditKind"] == "dry_run"
        assert "storeStatus" not in data

    def test_legacy_offset_cursor(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 5)
        r1 = client.get(AUDIT_URL, params={"auditKind": "dry_run", "limit": 2})
        nc = r1.json()["data"]["nextCursor"]
        r2 = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "limit": 2, "cursor": nc,
        })
        assert r2.status_code == 200

    def test_missing_audit_kind_422(self, client_with_home):
        client, _ = client_with_home
        resp = client.get(AUDIT_URL)
        assert resp.status_code == 422


class TestRouteGovernance:
    def test_paths_still_34(self, client_with_home):
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 34

    def test_tool_get_routes_still_5(self, client_with_home):
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        tool_paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/tools")]
        get_routes = [p for p in tool_paths if "get" in spec["paths"][p]]
        assert len(get_routes) == 5

    def test_audit_events_get_only(self, client_with_home):
        client, _ = client_with_home
        spec = client.get("/openapi.json").json()
        methods = set(spec["paths"]["/api/dev/v1/tools/audit-events"].keys()) & {
            "get", "post", "put", "patch", "delete"
        }
        assert methods == {"get"}

    def test_post_not_allowed(self, client_with_home):
        client, _ = client_with_home
        assert client.post(AUDIT_URL, json={}).status_code == 405


class TestNoSecretLeakage:
    def test_no_raw_token_or_secret_in_store_output(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 1)
        resp = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "search": "clarify",
        })
        text = json.dumps(resp.json())
        assert "api_key" not in text.lower()
        assert "sk-" not in text
        assert "/Users/huangruibang/.hermes" not in text

    def test_no_callable_repr_in_output(self, client_with_home):
        client, home = client_with_home
        _seed_dry_run(home, 1)
        resp = client.get(AUDIT_URL, params={
            "auditKind": "dry_run", "toolId": "clarify",
        })
        text = json.dumps(resp.json())
        assert "<function" not in text
        assert "object at 0x" not in text
