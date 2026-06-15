"""Phase 2D — Audit security boundary tests.

Verifies the P0 security invariants of the durable audit store:
  - no secret / raw token / full tokenHash / raw arguments / API key /
    callable repr / production path ever reaches store output or disk
  - the unified sanitizer closes the Phase 2A str(object) fallback
  - the store root is confined to the dev HERMES_HOME (never repo / ~/.hermes /
    state.db)
  - cursor tokens carry no path / secret / index internals
  - corrupt lines never crash the API
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store
from hermes_cli.dev_web_audit_query import (
    build_audit_query,
    decode_audit_cursor,
    encode_audit_cursor,
    AuditCursor,
    query_audit_events,
)
from hermes_cli.dev_web_audit_sanitizer import (
    NON_JSON_VALUE_SENTINEL,
    sanitize_audit_value,
)
from hermes_cli.dev_web_audit_store import (
    ERROR_STORE_ROOT_FORBIDDEN,
    append_audit_event,
    build_audit_event,
    ensure_audit_store,
    get_audit_store_root,
    iter_all_events,
    validate_audit_store_root,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


SENSITIVE = [
    "sk-abcd1234efgh5678ijkl",
    "Bearer secret-token-value",
    "Authorization: Bearer xyz",
    "api_key=ABCDEF1234567890",
    "-----BEGIN RSA PRIVATE KEY-----\nMIIBVwIBADAN\n-----END RSA PRIVATE KEY-----",
    "aabbccdd" * 8,  # full tokenHash (pure hex digest)
]


class TestNoSecretsOnDisk:
    def test_secrets_never_persisted(self, dev_home):
        for i, secret in enumerate(SENSITIVE):
            append_audit_event(
                build_audit_event(
                    event_type="sec", audit_kind="internal", event_id=f"s{i}",
                    summary={"leaked": secret},
                    safe_metadata={"api_key": secret, "nested": {"token": secret}},
                ),
                hermes_home=dev_home,
            )
        root, _ = get_audit_store_root(dev_home)
        on_disk = "\n".join(
            raw for _s, _l, _e, raw in iter_all_events(root, include_corrupt=True)
        )
        for secret in SENSITIVE:
            assert secret not in on_disk, f"secret persisted: {secret[:12]}…"

    def test_raw_token_under_forbidden_key_redacted(self, dev_home):
        # A raw token value is redacted when stored under a forbidden key name.
        append_audit_event(
            build_audit_event(
                event_type="sec", audit_kind="internal", event_id="rt1",
                safe_metadata={"rawToken": "raw-token-secret-abc"},
            ),
            hermes_home=dev_home,
        )
        root, _ = get_audit_store_root(dev_home)
        on_disk = "\n".join(
            raw for _s, _l, _e, raw in iter_all_events(root, include_corrupt=True)
        )
        assert "raw-token-secret-abc" not in on_disk

    def test_raw_arguments_field_redacted_on_disk(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="raw1",
                safe_metadata={"rawArguments": {"secret": "shh"}},
            ),
            hermes_home=dev_home,
        )
        root, _ = get_audit_store_root(dev_home)
        on_disk = "\n".join(
            raw for _s, _l, _e, raw in iter_all_events(root, include_corrupt=True)
        )
        assert "shh" not in on_disk


class TestNoSecretsInQueryOutput:
    def test_query_output_secret_free(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="q1",
                summary={"api_key": "sk-leak-1234567890abcdef"},
                safe_metadata={"tokenHash": "aabbccdd" * 8},
            ),
            hermes_home=dev_home,
        )
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10), hermes_home=dev_home
        )
        blob = json.dumps(res.items)
        assert "sk-leak" not in blob
        assert "aabbccdd" * 8 not in blob


class TestSanitizerClosesStrFallback:
    def test_callable_never_repr(self):
        assert sanitize_audit_value(lambda x: x) == NON_JSON_VALUE_SENTINEL

    def test_object_at_repr_scrubbed(self):
        class C:
            pass

        out = sanitize_audit_value(f"value={C()!r}")
        assert "object at 0x" not in out


class TestStoreRootConfined:
    def test_repo_root_rejected(self):
        assert validate_audit_store_root(Path("/Users/huangruibang/Code/hermes-agent-dev")) == ERROR_STORE_ROOT_FORBIDDEN

    def test_production_home_rejected(self):
        assert validate_audit_store_root(Path("/Users/huangruibang/.hermes")) == ERROR_STORE_ROOT_FORBIDDEN

    def test_state_db_rejected(self):
        assert validate_audit_store_root(Path("/tmp/state.db")) == ERROR_STORE_ROOT_FORBIDDEN

    def test_store_under_dev_home_only(self, dev_home):
        root, err = get_audit_store_root(dev_home)
        assert err is None
        assert "hermes-home-dev" in str(root)
        assert ".hermes/audit-store" not in str(root)
        assert "hermes-agent-dev" not in str(root) or "hermes-home-dev" in str(root)


class TestCursorCarriesNoSecrets:
    def test_cursor_has_no_path_or_secret(self, dev_home):
        for i in range(3):
            append_audit_event(
                build_audit_event(event_type="t", audit_kind="internal", event_id=f"c{i}"),
                hermes_home=dev_home,
            )
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=1), hermes_home=dev_home
        )
        token = res.next_cursor
        assert token is not None
        assert "/Users/" not in token
        assert "hermes-home" not in token
        assert "audit-store" not in token
        assert "eventId" not in token

    def test_cursor_decode_does_not_leak(self):
        import dataclasses

        token = encode_audit_cursor(
            AuditCursor(99, "desc", "hash", "2026-06-15T00:00:00+00:00")
        )
        back = decode_audit_cursor(token)
        assert back is not None
        # Decoded cursor carries only safe scalar fields.
        fields = {f.name for f in dataclasses.fields(back)}
        assert {"last_sequence", "direction", "query_hash"}.issubset(fields)


class TestCorruptNeverCrashesApi:
    def test_corrupt_line_does_not_crash(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        root, _ = get_audit_store_root(str(home))
        seg = root / "events" / "audit-000001.jsonl"
        seg.parent.mkdir(parents=True, exist_ok=True)
        with seg.open("w", encoding="utf-8") as f:
            f.write('{"eventId":"e1","sequence":1,"createdAt":"2026-06-15T00:00:00+00:00","eventType":"t","auditKind":"internal","schemaVersion":"audit_schema_v2"}\n')
            f.write("THIS IS CORRUPT JSON\n")
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
        client = TestClient(app)
        resp = client.get("/api/dev/v1/tools/audit-events", params={
            "auditKind": "internal", "search": "t",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 1
        assert data["skippedMalformed"] >= 1


class TestNoApiOutputLeaks:
    def test_no_callable_or_raw_args_in_api(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="api1",
                safe_metadata={"rawArguments": {"a": 1}, "callable": "<function x>"},
            ),
            hermes_home=str(home),
        )
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
        client = TestClient(app)
        resp = client.get("/api/dev/v1/tools/audit-events", params={
            "auditKind": "internal", "search": "t",
        })
        text = json.dumps(resp.json())
        assert "<function" not in text
        assert "rawArguments" not in text
        assert "object at 0x" not in text

    def test_no_production_path_in_api(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
        client = TestClient(app)
        resp = client.get("/api/dev/v1/tools/audit-events", params={
            "auditKind": "internal", "search": "t",
        })
        text = json.dumps(resp.json())
        assert "/Users/huangruibang/.hermes" not in text
        assert "state.db" not in text


class TestNoRuntimeArtifactsCommitted:
    """The audit store files must be runtime artifacts, never committed."""

    def test_audit_store_gitignored(self):
        from pathlib import Path as _P

        gitignore = _P(".gitignore").read_text(encoding="utf-8") if _P(".gitignore").exists() else ""
        # The dev audit-store lives under HERMES_HOME which is outside the repo,
        # so it is never tracked. We assert the legacy JSONL artifacts and the
        # token/rollback stores remain ignored.
        for pattern in (
            "tool-dry-run-audit.jsonl",
            "confirmation-tokens",
            "tool-write-rollback-manifests",
            "audit-store",
        ):
            assert pattern in gitignore, f"{pattern} not in .gitignore"
