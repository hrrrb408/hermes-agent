"""Tests for hermes_cli.dev_web_tool_post_execution_audit — Post-Execution Audit.

Phase 1G-04-29: Clarify-only Handler Call + Post-execution Audit.

All tests verify:
  - postExecutionAuditId generated (prefix "pexa_")
  - Audit path lives under the dev HERMES_HOME audit dir
  - Path traversal / production home is blocked
  - Append-only JSONL write
  - Event contains all required safe correlation fields
  - Event excludes raw token, full tokenHash, raw arguments, provider
    credentials, callable objects, secrets
  - Write failure fails closed (no success without audit)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_post_execution_audit import (
    DECISION_BLOCKED_POST_EXECUTION_AUDIT_PATH_FORBIDDEN,
    DECISION_BLOCKED_POST_EXECUTION_AUDIT_UNAVAILABLE,
    DECISION_BLOCKED_POST_EXECUTION_AUDIT_WRITE_FAILED,
    ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN,
    ERROR_POST_EXECUTION_AUDIT_UNAVAILABLE,
    ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED,
    GATE_POST_EXECUTION_AUDIT_PATH,
    GATE_POST_EXECUTION_AUDIT_WRITE,
    POST_EXECUTION_AUDIT_EVENT_TYPE,
    POST_EXECUTION_AUDIT_FILENAME,
    POST_EXECUTION_AUDIT_ID_PREFIX,
    POST_EXECUTION_AUDIT_RECORD_TYPE,
    POST_EXECUTION_AUDIT_SCHEMA_VERSION,
    PostExecutionAuditPackageResult,
    PostExecutionAuditWriteResult,
    build_post_execution_audit_package,
    get_post_execution_audit_store_path,
    safe_post_execution_audit_summary,
    validate_post_execution_audit_path,
    write_post_execution_audit_event,
)


# ===================================================================
# Helpers
# ===================================================================


def _sample_fields(**overrides):
    """Sample safe fields for build_post_execution_audit_package."""
    defaults = dict(
        execute_request_id="exe_test",
        pre_execution_audit_id="pea_test",
        handler_lookup_id="hl_test",
        dispatch_id="dsp_test",
        handler_call_id="thc_test",
        canonical_name="clarify",
        execution_status="completed",
        handler_call_status="completed",
        dry_run_decision_digest="sha256:abc",
        confirmation_token_id="ctok_test",
        tool_result={"type": "clarify", "message": "Which?", "questions": []},
    )
    defaults.update(overrides)
    return defaults


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def tmp_hermes_home(tmp_path: Path) -> Path:
    return tmp_path / "hermes-home-dev"


@pytest.fixture
def audit_dir(tmp_hermes_home: Path) -> Path:
    d = tmp_hermes_home / "gateway" / "dev" / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def audit_file(audit_dir: Path) -> Path:
    return audit_dir / POST_EXECUTION_AUDIT_FILENAME


# ===================================================================
# 1. Package builder tests
# ===================================================================


class TestPackageBuilder:
    """Verify build_post_execution_audit_package."""

    def test_package_success(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        assert r.success is True
        assert r.audit_package is not None
        assert r.post_execution_audit_id is not None
        assert r.error_code is None

    def test_package_generates_pexa_id(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        assert r.success is True
        assert r.post_execution_audit_id.startswith(POST_EXECUTION_AUDIT_ID_PREFIX)
        assert r.post_execution_audit_id.startswith("pexa_")

    def test_package_id_is_unique(self) -> None:
        ids = [
            build_post_execution_audit_package(**_sample_fields()).post_execution_audit_id
            for _ in range(10)
        ]
        assert len(set(ids)) == len(ids)

    def test_package_record_type(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        assert r.audit_package["recordType"] == POST_EXECUTION_AUDIT_RECORD_TYPE
        assert r.audit_package["eventType"] == POST_EXECUTION_AUDIT_EVENT_TYPE
        assert r.audit_package["schemaVersion"] == POST_EXECUTION_AUDIT_SCHEMA_VERSION

    def test_package_contains_all_correlation_fields(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        pkg = r.audit_package
        assert pkg["executeRequestId"] == "exe_test"
        assert pkg["preExecutionAuditId"] == "pea_test"
        assert pkg["handlerLookupId"] == "hl_test"
        assert pkg["dispatchId"] == "dsp_test"
        assert pkg["handlerCallId"] == "thc_test"
        assert pkg["canonicalName"] == "clarify"

    def test_package_result_summary_is_safe(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        summary = r.audit_package["resultSummary"]
        # Safe summary: type + counts only, no raw message content
        assert summary["toolResultType"] == "clarify"
        assert summary["messageLength"] == len("Which?")
        assert summary["questionCount"] == 0
        assert "message" not in summary  # no raw message content

    def test_package_excludes_raw_arguments(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        text = json.dumps(r.audit_package)
        assert "rawArguments" not in text
        # The tool_result message content must NOT appear in the audit event
        # (only the safe result summary counts are recorded).
        assert "Which?" not in text

    def test_package_excludes_raw_token(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        text = json.dumps(r.audit_package)
        # No raw token field names
        assert "rawToken" not in text
        assert "raw_token" not in text
        # The package holds only a SAFE confirmationTokenId (correlation),
        # never the raw confirmation token credential itself.
        assert r.audit_package["confirmationTokenId"] == "ctok_test"
        # A distinctive raw-token value must never leak into the package.
        assert "tok-secret-DO-NOT-LEAK-1234567" not in text

    def test_package_excludes_full_token_hash(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        text = json.dumps(r.audit_package)
        assert "tokenHash" not in text
        assert "token_hash" not in text

    def test_package_excludes_provider_credentials(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        text = json.dumps(r.audit_package).lower()
        assert "api_key" not in text
        assert "apikey" not in text
        assert "password" not in text

    def test_package_excludes_callable_object(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        def _walk(obj):
            if callable(obj):
                return True
            if isinstance(obj, dict):
                return any(_walk(v) for v in obj.values())
            if isinstance(obj, list):
                return any(_walk(v) for v in obj)
            return False
        assert _walk(r.audit_package) is False

    def test_package_side_effect_flags_all_false(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        flags = r.audit_package["sideEffectFlags"]
        for _k, v in flags.items():
            assert v is False
        assert flags["providerSchemaSent"] is False
        assert flags["providerApiCalled"] is False

    def test_package_missing_required_field_fails(self) -> None:
        # Omit a required field by passing empty handler_call_id
        r = build_post_execution_audit_package(
            **_sample_fields(handler_call_id=None)
        )
        assert r.success is False
        assert r.audit_package is None
        assert r.error_code is not None


# ===================================================================
# 2. JSONL writer tests
# ===================================================================


class TestJsonlWriter:
    """Verify write_post_execution_audit_event."""

    def test_write_success(self, tmp_hermes_home: Path) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        assert pkg.success
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert result.written is True
        assert result.post_execution_audit_id == pkg.post_execution_audit_id
        assert result.error_code is None

    def test_write_creates_audit_file(self, tmp_hermes_home: Path, audit_file: Path) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert audit_file.exists()

    def test_write_is_append_only(self, tmp_hermes_home: Path, audit_file: Path) -> None:
        for _ in range(3):
            pkg = build_post_execution_audit_package(**_sample_fields())
            write_post_execution_audit_event(
                hermes_home=str(tmp_hermes_home),
                audit_package=pkg.audit_package,
            )
        lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            json.loads(line)  # each line is valid JSON

    def test_write_event_contains_correlation_fields(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        rec = json.loads(audit_file.read_text(encoding="utf-8").strip())
        assert rec["executeRequestId"] == "exe_test"
        assert rec["preExecutionAuditId"] == "pea_test"
        assert rec["handlerLookupId"] == "hl_test"
        assert rec["dispatchId"] == "dsp_test"
        assert rec["handlerCallId"] == "thc_test"
        assert rec["canonicalName"] == "clarify"
        assert rec["postExecutionAuditId"].startswith("pexa_")

    def test_write_under_dev_hermes_home(
        self, tmp_hermes_home: Path,
    ) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        audit_dir, audit_file, err = get_post_execution_audit_store_path(
            str(tmp_hermes_home)
        )
        assert err is None
        assert audit_file.exists()
        # Path must be under the dev HERMES_HOME audit dir
        assert str(audit_file).startswith(str(tmp_hermes_home))

    def test_write_invalid_package_fails_closed(self, tmp_hermes_home: Path) -> None:
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=None,  # type: ignore[arg-type]
        )
        assert result.written is False
        assert result.error_code is not None
        assert result.post_execution_audit_id is None

    def test_write_non_dict_package_fails_closed(self, tmp_hermes_home: Path) -> None:
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package="not-a-dict",  # type: ignore[arg-type]
        )
        assert result.written is False

    def test_safe_summary_written_status(self, tmp_hermes_home: Path) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert result.safe_summary["postExecutionAuditStatus"] == "written"


# ===================================================================
# 3. Path guard tests
# ===================================================================


class TestPathGuard:
    """Verify the post-execution audit path guard blocks production."""

    def test_validate_dev_path_ok(self, tmp_hermes_home: Path) -> None:
        ok, err = validate_post_execution_audit_path(str(tmp_hermes_home))
        assert ok is True
        assert err is None

    def test_production_home_blocked(self) -> None:
        ok, err = validate_post_execution_audit_path("/Users/huangruibang/.hermes")
        assert ok is False
        assert err == ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    def test_production_subtree_blocked(self) -> None:
        ok, err = validate_post_execution_audit_path(
            "/Users/huangruibang/.hermes/gateway/dev"
        )
        assert ok is False
        assert err == ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    def test_none_hermes_home_no_env_blocks(self) -> None:
        """Empty HERMES_HOME blocks (path guard unavailable)."""
        old = os.environ.pop("HERMES_HOME", None)
        try:
            ok, err = validate_post_execution_audit_path(None)
            assert ok is False
            assert err is not None
        finally:
            if old is not None:
                os.environ["HERMES_HOME"] = old

    def test_write_to_production_home_fails_closed(
        self, tmp_hermes_home: Path,
    ) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        result = write_post_execution_audit_event(
            hermes_home="/Users/huangruibang/.hermes",
            audit_package=pkg.audit_package,
        )
        assert result.written is False
        assert result.error_code == ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN
        assert result.decision == DECISION_BLOCKED_POST_EXECUTION_AUDIT_PATH_FORBIDDEN
        assert result.gate == GATE_POST_EXECUTION_AUDIT_PATH

    def test_write_to_none_home_no_env_fails_closed(self) -> None:
        """Write to None home with HERMES_HOME unset fails closed."""
        old = os.environ.pop("HERMES_HOME", None)
        try:
            pkg = build_post_execution_audit_package(**_sample_fields())
            result = write_post_execution_audit_event(
                hermes_home=None,
                audit_package=pkg.audit_package,
            )
            assert result.written is False
            assert result.error_code is not None
        finally:
            if old is not None:
                os.environ["HERMES_HOME"] = old

    def test_production_file_not_created(self, tmp_path: Path) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        write_post_execution_audit_event(
            hermes_home="/Users/huangruibang/.hermes",
            audit_package=pkg.audit_package,
        )
        prod_file = Path("/Users/huangruibang/.hermes/gateway/dev/audit") / POST_EXECUTION_AUDIT_FILENAME
        assert not prod_file.exists()


# ===================================================================
# 4. Fail-closed tests
# ===================================================================


class TestFailClosed:
    """Verify write failure fails closed."""

    def test_mkdir_failure_fails_closed(
        self, tmp_hermes_home: Path, monkeypatch,
    ) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())

        def _raise(*_a, **_kw):
            raise OSError("simulated mkdir failure")

        monkeypatch.setattr(Path, "mkdir", _raise)
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert result.written is False
        assert result.error_code == ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED
        assert result.decision == DECISION_BLOCKED_POST_EXECUTION_AUDIT_WRITE_FAILED
        assert result.gate == GATE_POST_EXECUTION_AUDIT_WRITE

    def test_open_failure_fails_closed(
        self, tmp_hermes_home: Path, monkeypatch,
    ) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())

        original_open = Path.open

        def _flaky_open(self, *args, **kwargs):
            if "a" in (args[0] if args else kwargs.get("mode", "")):
                raise OSError("simulated append failure")
            return original_open(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", _flaky_open)
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert result.written is False
        assert result.error_code == ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED

    def test_no_success_response_when_write_fails(
        self, tmp_hermes_home: Path, monkeypatch,
    ) -> None:
        """When post-audit write fails, written=False — no success possible."""
        pkg = build_post_execution_audit_package(**_sample_fields())

        def _raise(*_a, **_kw):
            raise OSError("simulated")

        monkeypatch.setattr(Path, "mkdir", _raise)
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        # Caller MUST treat written=False as fail-closed
        assert result.written is False
        assert result.post_execution_audit_id is None


# ===================================================================
# 5. Immutability / summary / constants tests
# ===================================================================


class TestImmutabilityAndConstants:
    """Verify dataclass immutability + constants."""

    def test_write_result_is_frozen(self, tmp_hermes_home: Path) -> None:
        pkg = build_post_execution_audit_package(**_sample_fields())
        result = write_post_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        with pytest.raises(AttributeError):
            result.written = False  # type: ignore[misc]

    def test_package_result_is_frozen(self) -> None:
        r = build_post_execution_audit_package(**_sample_fields())
        with pytest.raises(AttributeError):
            r.success = False  # type: ignore[misc]

    def test_constants(self) -> None:
        assert POST_EXECUTION_AUDIT_ID_PREFIX == "pexa_"
        assert POST_EXECUTION_AUDIT_FILENAME == "tool-post-execution-audit.jsonl"
        assert POST_EXECUTION_AUDIT_RECORD_TYPE == "tool_post_execution_audit"
        assert POST_EXECUTION_AUDIT_SCHEMA_VERSION >= 1

    def test_safe_summary_written(self) -> None:
        summary = safe_post_execution_audit_summary("pexa_abc")
        assert summary["postExecutionAuditId"] == "pexa_abc"
        assert summary["postExecutionAuditStatus"] == "written"

    def test_safe_summary_none(self) -> None:
        summary = safe_post_execution_audit_summary(None)
        assert summary["postExecutionAuditId"] is None
        assert summary["postExecutionAuditStatus"] is None


# ===================================================================
# 6. No-side-effect / no-import tests
# ===================================================================


class TestNoSideEffects:
    """Verify the module has no provider / handler / dispatch imports."""

    def test_does_not_import_tool_handlers(self) -> None:
        import hermes_cli.dev_web_tool_post_execution_audit as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from tools." not in line, f"Unexpected import: {line}"
            assert "from agent." not in line, f"Unexpected import: {line}"

    def test_does_not_import_provider(self) -> None:
        import hermes_cli.dev_web_tool_post_execution_audit as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source
