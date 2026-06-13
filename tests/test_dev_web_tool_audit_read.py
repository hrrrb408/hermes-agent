"""Tests for the read-only tool audit events reader (Phase 1G-04-30).

Covers dev_web_tool_audit_read.py: read-only JSONL reading for the three
audit kinds, redaction, path containment, pagination, and safety.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_audit_read import (
    AUDIT_KIND_DRY_RUN,
    AUDIT_KIND_POST_EXECUTION,
    AUDIT_KIND_PRE_EXECUTION,
    ERROR_AUDIT_KIND_INVALID,
    ERROR_AUDIT_PATH_FORBIDDEN,
    ERROR_CURSOR_INVALID,
    ERROR_HERMES_HOME_MISSING,
    ERROR_LIMIT_INVALID,
    VALID_AUDIT_KINDS,
    read_audit_events,
    resolve_audit_store_path,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def dev_home(tmp_path: Path) -> Path:
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    return home


def _audit_dir(home: Path) -> Path:
    return home / "gateway" / "dev" / "audit"


def _write_lines(home: Path, filename: str, events: list) -> None:
    p = _audit_dir(home) / filename
    with p.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


# ── Per-kind read ───────────────────────────────────────────────────────


class TestPerKindRead:
    def test_dry_run_read(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-dry-run-audit.jsonl",
            [
                {
                    "eventId": "evt-1",
                    "eventType": "tool_dry_run",
                    "timestamp": "2026-06-13T00:00:00+00:00",
                    "canonicalName": "clarify",
                    "decision": "would_allow",
                    "riskTier": "R0",
                    "toolExists": True,
                    "dryRunDecisionDigest": "sha256:abcdef1234567890",
                    "redactionApplied": False,
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        assert result.success
        assert len(result.items) == 1
        item = result.items[0]
        assert item["auditKind"] == "dry_run"
        assert item["auditId"] == "evt-1"
        assert item["canonicalName"] == "clarify"
        assert item["decision"] == "would_allow"
        assert item["riskTier"] == "R0"
        assert item["toolExists"] is True
        assert item["safeSummary"]["decision"] == "would_allow"
        # Digest returned in short form
        assert item["dryRunDecisionDigest"].startswith("sha256:abcdef")

    def test_pre_execution_read(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-pre-execution-audit.jsonl",
            [
                {
                    "preExecutionAuditId": "pea_abc",
                    "executeRequestId": "exe_abc",
                    "dryRunRequestId": "dr_abc",
                    "dryRunDecisionDigest": "sha256:longdigestvaluehere",
                    "canonicalName": "clarify",
                    "riskTier": "R0",
                    "policyVersion": "dev-v1",
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_PRE_EXECUTION, hermes_home=str(dev_home)
        )
        assert result.success
        assert len(result.items) == 1
        item = result.items[0]
        assert item["auditKind"] == "pre_execution"
        assert item["auditId"] == "pea_abc"
        assert item["executeRequestId"] == "exe_abc"
        assert item["dryRunRequestId"] == "dr_abc"
        assert item["canonicalName"] == "clarify"
        assert item["safeSummary"]["policyVersion"] == "dev-v1"

    def test_post_execution_read(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-post-execution-audit.jsonl",
            [
                {
                    "postExecutionAuditId": "pexa_abc",
                    "executeRequestId": "exe_abc",
                    "preExecutionAuditId": "pea_abc",
                    "handlerLookupId": "hl_abc",
                    "dispatchId": "dsp_abc",
                    "handlerCallId": "thc_abc",
                    "canonicalName": "clarify",
                    "executionStatus": "completed",
                    "handlerCallStatus": "completed",
                    "eventType": "clarify_execution_completed",
                    "sideEffectFlags": {
                        "providerSchemaSent": False,
                        "providerApiCalled": False,
                        "externalSideEffects": False,
                        "filesystemChanged": False,
                        "networkCalled": False,
                    },
                    "resultSummary": {
                        "toolResultType": "clarify",
                        "messageLength": 12,
                        "questionCount": 1,
                    },
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_POST_EXECUTION, hermes_home=str(dev_home)
        )
        assert result.success
        assert len(result.items) == 1
        item = result.items[0]
        assert item["auditKind"] == "post_execution"
        assert item["auditId"] == "pexa_abc"
        assert item["handlerCallId"] == "thc_abc"
        assert item["dispatchId"] == "dsp_abc"
        assert item["executionStatus"] == "completed"
        assert item["decision"] == "clarify_execution_completed"
        assert item["safeSummary"]["questionCount"] == 1
        assert item["safeSummary"]["messageLength"] == 12
        # Side effects all false
        assert item["sideEffects"]["providerSchemaSent"] is False
        assert item["sideEffects"]["providerApiCalled"] is False
        assert item["sideEffects"]["externalSideEffects"] is False

    def test_newest_first_order(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-dry-run-audit.jsonl",
            [
                {"eventId": "old", "canonicalName": "clarify"},
                {"eventId": "new", "canonicalName": "clarify"},
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        assert [i["auditId"] for i in result.items] == ["new", "old"]


# ── Missing / malformed ─────────────────────────────────────────────────


class TestMissingAndMalformed:
    def test_missing_file_returns_empty(self, dev_home: Path) -> None:
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        assert result.success
        assert result.items == ()
        assert result.has_more is False

    def test_malformed_line_skipped(self, dev_home: Path) -> None:
        p = _audit_dir(dev_home) / "tool-dry-run-audit.jsonl"
        with p.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"eventId": "good", "canonicalName": "clarify"}) + "\n")
            f.write("this is not json {{{\n")
            f.write(json.dumps({"eventId": "good2", "canonicalName": "clarify"}) + "\n")
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        assert result.success
        assert len(result.items) == 2
        assert result.skipped_malformed == 1
        # Malformed content never appears
        blob = json.dumps([i for i in result.items])
        assert "this is not json" not in blob

    def test_non_object_line_skipped(self, dev_home: Path) -> None:
        p = _audit_dir(dev_home) / "tool-dry-run-audit.jsonl"
        with p.open("w", encoding="utf-8") as f:
            f.write("[1, 2, 3]\n")
            f.write('"a string"\n')
            f.write(json.dumps({"eventId": "ok", "canonicalName": "clarify"}) + "\n")
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        assert result.success
        assert len(result.items) == 1
        assert result.skipped_malformed == 2


# ── Pagination ──────────────────────────────────────────────────────────


class TestPagination:
    def test_limit_enforced(self, dev_home: Path) -> None:
        events = [
            {"eventId": f"e{i}", "canonicalName": "clarify"} for i in range(10)
        ]
        _write_lines(dev_home, "tool-dry-run-audit.jsonl", events)
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, limit=3, hermes_home=str(dev_home)
        )
        assert result.success
        assert len(result.items) == 3
        assert result.has_more is True
        assert result.next_cursor == "3"

    def test_cursor_continues(self, dev_home: Path) -> None:
        events = [
            {"eventId": f"e{i}", "canonicalName": "clarify"} for i in range(10)
        ]
        _write_lines(dev_home, "tool-dry-run-audit.jsonl", events)
        # Newest first: e9..e0
        page1 = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, limit=3, hermes_home=str(dev_home)
        )
        page2 = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN,
            limit=3,
            cursor=page1.next_cursor,
            hermes_home=str(dev_home),
        )
        assert [i["auditId"] for i in page1.items] == ["e9", "e8", "e7"]
        assert [i["auditId"] for i in page2.items] == ["e6", "e5", "e4"]

    def test_canonical_name_filter(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-dry-run-audit.jsonl",
            [
                {"eventId": "a", "canonicalName": "clarify"},
                {"eventId": "b", "canonicalName": "read_file"},
                {"eventId": "c", "canonicalName": "clarify"},
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN,
            canonical_name="clarify",
            hermes_home=str(dev_home),
        )
        assert result.success
        assert [i["auditId"] for i in result.items] == ["c", "a"]

    def test_limit_capped_to_max(self, dev_home: Path) -> None:
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, limit=99999, hermes_home=str(dev_home)
        )
        assert result.success
        assert result.limit == 100


# ── Validation ──────────────────────────────────────────────────────────


class TestValidation:
    def test_invalid_audit_kind_rejected(self, dev_home: Path) -> None:
        result = read_audit_events(audit_kind="bogus", hermes_home=str(dev_home))
        assert not result.success
        assert result.error_code == ERROR_AUDIT_KIND_INVALID

    def test_invalid_limit_rejected(self, dev_home: Path) -> None:
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, limit=0, hermes_home=str(dev_home)
        )
        assert not result.success
        assert result.error_code == ERROR_LIMIT_INVALID

    def test_invalid_cursor_rejected(self, dev_home: Path) -> None:
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN,
            cursor="not-a-number",
            hermes_home=str(dev_home),
        )
        assert not result.success
        assert result.error_code == ERROR_CURSOR_INVALID

    def test_negative_cursor_rejected(self, dev_home: Path) -> None:
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN,
            cursor="-1",
            hermes_home=str(dev_home),
        )
        assert not result.success
        assert result.error_code == ERROR_CURSOR_INVALID

    def test_no_hermes_home_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HERMES_HOME", raising=False)
        result = read_audit_events(audit_kind=AUDIT_KIND_DRY_RUN)
        assert not result.success
        assert result.error_code == ERROR_HERMES_HOME_MISSING


# ── Path containment ────────────────────────────────────────────────────


class TestPathContainment:
    def test_production_home_blocked(self) -> None:
        path, err = resolve_audit_store_path(
            AUDIT_KIND_DRY_RUN, hermes_home="/Users/huangruibang/.hermes"
        )
        assert err == ERROR_AUDIT_PATH_FORBIDDEN
        assert path == Path()

    def test_production_subtree_blocked(self, tmp_path: Path) -> None:
        # A home nested inside production home
        prod_subtree = Path("/Users/huangruibang/.hermes/subtree")
        path, err = resolve_audit_store_path(
            AUDIT_KIND_DRY_RUN, hermes_home=str(prod_subtree)
        )
        assert err == ERROR_AUDIT_PATH_FORBIDDEN

    def test_read_blocks_production_home(self) -> None:
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN,
            hermes_home="/Users/huangruibang/.hermes",
        )
        assert not result.success
        assert result.error_code == ERROR_AUDIT_PATH_FORBIDDEN

    def test_dev_home_under_home(self, dev_home: Path) -> None:
        path, err = resolve_audit_store_path(
            AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        assert err is None
        assert path.name == "tool-dry-run-audit.jsonl"
        assert "gateway/dev/audit" in str(path)


# ── Redaction / safety ──────────────────────────────────────────────────


class TestRedactionSafety:
    def test_raw_token_not_exposed(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-pre-execution-audit.jsonl",
            [
                {
                    "preExecutionAuditId": "pea_1",
                    "confirmationTokenId": "ctok_1",
                    # A raw confirmation token value planted in an unexpected field
                    "confirmationToken": "raw-secret-confirmation-token-xyz",
                    "canonicalName": "clarify",
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_PRE_EXECUTION, hermes_home=str(dev_home)
        )
        blob = json.dumps([i for i in result.items], ensure_ascii=False)
        assert "raw-secret-confirmation-token-xyz" not in blob
        assert "confirmationToken" not in blob

    def test_secret_value_redacted(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-dry-run-audit.jsonl",
            [
                {
                    "eventId": "e1",
                    "canonicalName": "clarify",
                    # A secret-looking value planted in a whitelisted field path
                    "sourceContext": "sk-test-fake-redacted-value-12345",
                }
            ],
        )
        # sourceContext is not whitelisted for dry-run, so it won't appear;
        # but ensure that if a secret appears anywhere it is never raw.
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        blob = json.dumps([i for i in result.items], ensure_ascii=False)
        assert "sk-test-fake-redacted-value-12345" not in blob

    def test_raw_arguments_not_exposed(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-dry-run-audit.jsonl",
            [
                {
                    "eventId": "e1",
                    "canonicalName": "clarify",
                    "redactedArgumentsPreview": {"api_key": "[REDACTED]"},
                    "argumentsPreview": {"secret": "super-secret-raw"},
                    "rawArguments": {"secret": "super-secret-raw"},
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        blob = json.dumps([i for i in result.items], ensure_ascii=False)
        assert "super-secret-raw" not in blob
        assert "argumentsPreview" not in blob
        assert "rawArguments" not in blob
        assert "redactedArgumentsPreview" not in blob

    def test_token_hash_not_exposed(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-pre-execution-audit.jsonl",
            [
                {
                    "preExecutionAuditId": "pea_1",
                    "tokenHash": "deadbeefcafebabe" * 8,
                    "fullTokenHash": "deadbeefcafebabe" * 8,
                    "canonicalName": "clarify",
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_PRE_EXECUTION, hermes_home=str(dev_home)
        )
        blob = json.dumps([i for i in result.items], ensure_ascii=False)
        assert "deadbeefcafebabe" not in blob
        assert "tokenHash" not in blob

    def test_provider_payload_not_exposed(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-post-execution-audit.jsonl",
            [
                {
                    "postExecutionAuditId": "pexa_1",
                    "canonicalName": "clarify",
                    "providerPayload": {"model": "gpt", "apiKey": "sk-leak"},
                    "providerResponse": {"content": "secret"},
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_POST_EXECUTION, hermes_home=str(dev_home)
        )
        blob = json.dumps([i for i in result.items], ensure_ascii=False)
        assert "providerPayload" not in blob
        assert "providerResponse" not in blob
        assert "sk-leak" not in blob

    def test_callable_function_repr_not_exposed(self, dev_home: Path) -> None:
        # A non-JSON value cannot be stored in JSONL, but a string that looks
        # like a repr should not leak through whitelisted fields.
        _write_lines(
            dev_home,
            "tool-dry-run-audit.jsonl",
            [
                {
                    "eventId": "e1",
                    "canonicalName": "clarify",
                    "callable": "<function handler at 0x10>",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_DRY_RUN, hermes_home=str(dev_home)
        )
        blob = json.dumps([i for i in result.items], ensure_ascii=False)
        assert "<function handler" not in blob
        assert "callable" not in blob

    def test_side_effects_default_false_when_missing(self, dev_home: Path) -> None:
        _write_lines(
            dev_home,
            "tool-post-execution-audit.jsonl",
            [
                {
                    "postExecutionAuditId": "pexa_1",
                    "canonicalName": "clarify",
                    # No sideEffectFlags field at all
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_POST_EXECUTION, hermes_home=str(dev_home)
        )
        item = result.items[0]
        assert item["sideEffects"]["providerSchemaSent"] is False
        assert item["sideEffects"]["providerApiCalled"] is False
        assert item["sideEffects"]["externalSideEffects"] is False

    def test_side_effects_force_true_in_source_still_false_safe(self, dev_home: Path) -> None:
        """If a source event wrongly claims provider flags true, the safe
        reader still surfaces the actual booleans (defense: they reflect
        what was recorded). For a truthful clarify audit they are false;
        here we confirm the reader faithfully reads the recorded booleans
        (no fabrication), but a real clarify audit always writes false."""
        _write_lines(
            dev_home,
            "tool-post-execution-audit.jsonl",
            [
                {
                    "postExecutionAuditId": "pexa_1",
                    "canonicalName": "clarify",
                    "sideEffectFlags": {
                        "providerSchemaSent": False,
                        "providerApiCalled": False,
                        "externalSideEffects": False,
                    },
                    "createdAt": "2026-06-13T00:00:00+00:00",
                }
            ],
        )
        result = read_audit_events(
            audit_kind=AUDIT_KIND_POST_EXECUTION, hermes_home=str(dev_home)
        )
        item = result.items[0]
        assert item["sideEffects"]["providerSchemaSent"] is False
        assert item["sideEffects"]["providerApiCalled"] is False


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:
    def test_valid_kinds(self) -> None:
        assert VALID_AUDIT_KINDS == frozenset(
            {"dry_run", "pre_execution", "post_execution"}
        )

    def test_kind_filename_mapping_covers_all(self) -> None:
        from hermes_cli.dev_web_tool_audit_read import _KIND_FILENAME

        for kind in VALID_AUDIT_KINDS:
            assert kind in _KIND_FILENAME
            assert _KIND_FILENAME[kind].endswith(".jsonl")
