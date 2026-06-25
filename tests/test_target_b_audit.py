"""Phase 4B — Target B audit trail layer tests.

Asserts ``hermes_cli/dev_web_target_b_audit.py`` is inert, frozen, and
fail-closed:

  - the audit trail is in-memory only — nothing is persisted, no JSONL is
    written, no audit store is committed;
  - every audit payload is defense-in-depth redacted (secrets / production
    paths / fake-authorization markers masked);
  - the denied-execution + policy-evaluation audit events are built in-memory;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive (no file write, no JSONL), and no
    production home or production ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_audit as audit
from hermes_cli.dev_web_target_b_audit import (
    assert_audit_layer_disabled,
    build_audit_redaction_policy,
    build_audit_trail_report,
    build_denied_execution_audit,
    build_policy_evaluation_audit,
    build_target_b_audit_event,
    redact_target_b_audit_payload,
)

REDACTION_CORPUS = [
    "sk-FAKE-SECRET-DO-NOT-LEAK",
    "Authorization: Bearer fake",
    "ghp_fakegithubtoken",
    "xox-fake-slack-token",
    "BEGIN PRIVATE KEY fake",
    "trust_token=fake",
    "registry_token=fake",
    "plugin_signature=fake-private-key",
    "target_b_authorized=true",
    "production_runtime_go=true",
    "approved_by_ai=true",
    "implementation_authorization=GO",
]


class TestPersistenceInMemoryOnly:
    def test_redaction_policy_in_memory_only(self) -> None:
        p = build_audit_redaction_policy()
        assert p.persisted is False
        assert p.audit_log_committed is False
        assert p.secrets_redacted is True
        assert p.production_paths_redacted is True
        assert p.fake_authorization_redacted is True

    def test_report_in_memory_only(self) -> None:
        report = build_audit_trail_report()
        assert report.persistence == "in_memory_only"
        assert report.persisted is False
        assert report.audit_log_committed is False

    def test_event_not_persisted(self) -> None:
        event = build_denied_execution_audit()
        assert event.persisted is False


class TestRedaction:
    @pytest.mark.parametrize("value", REDACTION_CORPUS)
    def test_audit_payload_redacts_secret(self, value: str) -> None:
        redacted = redact_target_b_audit_payload({"field": value})
        assert redacted["field"] == "[REDACTED]"

    def test_audit_event_redacts_payload(self) -> None:
        event = build_target_b_audit_event(
            event_id="evt",
            decision="denied",
            reason="r",
            layer="audit",
            payload={"credential": "sk-FAKE-LEAK", "note": "trust_token=fake"},
        )
        text = str(event.to_safe_dict())
        assert "[REDACTED]" in text
        assert "sk-FAKE-LEAK" not in text
        assert "trust_token=fake" not in text

    def test_denied_execution_audit_built(self) -> None:
        event = build_denied_execution_audit(payload={"a": "b"})
        assert event.decision == "denied"
        assert event.persisted is False

    def test_policy_evaluation_audit_built(self) -> None:
        event = build_policy_evaluation_audit()
        assert event.persisted is False

    def test_assert_audit_layer_disabled_passes(self) -> None:
        assert_audit_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(audit.__file__)

    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
        "json.dump",
        ".jsonl",
    )

    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"audit source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"audit source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
