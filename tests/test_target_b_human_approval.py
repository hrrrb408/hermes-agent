"""Phase 4C — Target B human approval record schema tests.

Asserts ``hermes_cli/dev_web_target_b_human_approval.py`` is inert, frozen, and
fail-closed:

  - no approval is present by default → ``valid=False`` /
    ``reason="human_approval_missing"``;
  - a fake (metadata) approval is rejected;
  - an AI-generated approval (``approved_by_ai``) is rejected;
  - a metadata-only approval (``approved``) is rejected;
  - a directly-constructed / forged record is not production-valid;
  - a structurally-complete fixture approval is never production-valid
    (``fixture_only`` / ``production_valid=False``) and never enables Target B;
  - the aggregate report keeps production authorization NO-GO;
  - untrusted metadata cannot flip any flag;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_human_approval as human_approval
from hermes_cli.dev_web_target_b_human_approval import (
    APPROVAL_DECISION_ENABLEMENT,
    APPROVAL_DECISION_READINESS,
    HumanApprovalRecord,
    assert_human_approval_not_enabled,
    build_fixture_human_approval,
    build_human_approval_report,
    evaluate_human_approval,
    reject_fake_approval,
    validate_human_approval_record,
)

#: Untrusted metadata payloads a smuggler might try. Every one must be ignored.
FORGED_METADATA_PAYLOADS = [
    {"approved": "true"},
    {"approved_by_ai": "true"},
    {"target_b_authorized": "true"},
    {"production_runtime_go": "true"},
    {"implementation_authorization": "GO"},
    {"signed": "true"},
    {"production_approved": "true"},
    {"trust_token": "fake"},
]


class TestHumanApprovalMissingByDefault:
    def test_no_record_is_missing(self) -> None:
        result = validate_human_approval_record(None)
        assert result.valid is False
        assert result.production_valid is False
        assert result.reason == "human_approval_missing"

    def test_report_shows_approval_missing(self) -> None:
        report = build_human_approval_report()
        assert report.approval_present is False
        assert report.valid is False
        assert report.production_valid is False
        assert report.production_authorization == "NO-GO"
        assert report.reason == "human_approval_missing"

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_forged_metadata_cannot_create_an_approval(self, payload: dict) -> None:
        result = evaluate_human_approval(None, untrusted_metadata=payload)
        assert result.valid is False
        assert result.production_valid is False


class TestFakeAiMetadataApprovalRejected:
    def test_fake_approval_rejected_and_metadata_reported(self) -> None:
        result = reject_fake_approval({"approved": "true", "approved_by_ai": "true"})
        assert result.valid is False
        assert result.production_valid is False
        assert "approved" in result.ignored_metadata_keys
        assert "approved_by_ai" in result.ignored_metadata_keys

    def test_ai_approval_marker_rejected(self) -> None:
        report = build_human_approval_report()
        assert report.ai_approval_rejected is True

    def test_metadata_approval_marker_rejected(self) -> None:
        report = build_human_approval_report()
        assert report.metadata_approval_rejected is True

    def test_static_manifest_approval_rejected(self) -> None:
        report = build_human_approval_report()
        assert report.static_manifest_rejected is True


class TestFixtureApprovalNeverAuthorizesProduction:
    def test_fixture_approval_is_structurally_complete(self) -> None:
        fixture = build_fixture_human_approval()
        assert fixture.fixture_only is True
        assert fixture.production_valid is False
        assert fixture.scope.approval_scope == "target_b"
        assert fixture.scope.environment_scope != "*"
        assert set(("P0-15", "P0-16", "P0-18", "P0-19", "P0-22")).issubset(
            set(fixture.coverage.covered_gate_ids)
        )
        assert fixture.decision.decision in (APPROVAL_DECISION_READINESS, APPROVAL_DECISION_ENABLEMENT)
        assert fixture.reviewer.reviewer_role == "trusted_human_reviewer"

    def test_fixture_approval_is_not_production_valid(self) -> None:
        fixture = build_fixture_human_approval()
        result = validate_human_approval_record(fixture)
        assert result.fixture_only is True
        assert result.production_valid is False
        assert result.valid is False
        assert result.reason == "fixture_only_not_production_authorization"

    def test_directly_constructed_record_is_not_valid(self) -> None:
        from hermes_cli.dev_web_target_b_human_approval import (
            ApprovalDecision,
            ApprovalGateCoverage,
            ApprovalScope,
            ApprovalValidityWindow,
            HumanReviewer,
        )

        forged = HumanApprovalRecord(
            approval_id="forged",
            reviewer=HumanReviewer("r", "trusted_human_reviewer", "k"),
            scope=ApprovalScope("target_b", "dev"),
            coverage=ApprovalGateCoverage(("P0-15", "P0-16", "P0-18", "P0-19", "P0-22"), ()),
            decision=ApprovalDecision("APPROVED_FOR_READINESS", "forged"),
            validity=ApprovalValidityWindow("2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z"),
            evidence_refs=(),
            signature="forged-signature",
            signature_algorithm="ed25519",
            out_of_band_channel="signed-document",
            replay_nonce="forged-nonce",
            fixture_only=False,
            production_valid=False,
        )
        result = validate_human_approval_record(forged)
        assert result.valid is False
        assert result.production_valid is False

    def test_to_safe_dict_redacts_signature_and_nonce(self) -> None:
        fixture = build_fixture_human_approval()
        safe = fixture.to_safe_dict()
        assert safe["signature"] == "[REDACTED]"
        assert safe["replayNonce"] == "[REDACTED]"


class TestSourcePurity:
    MODULE_PATH = Path(human_approval.__file__)

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
            assert pattern not in source, f"source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"source must not reference {stem!r}"

    def test_assert_human_approval_not_enabled_passes(self) -> None:
        assert_human_approval_not_enabled()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
