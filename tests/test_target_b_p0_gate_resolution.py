"""Phase 4C — Target B P0 gate resolution evaluator tests.

Asserts ``hermes_cli/dev_web_target_b_p0_gate_resolution.py`` is inert, frozen,
and fail-closed:

  - the resolved-count delta is 0 by default;
  - P0 resolved stays 0; pending human review stays 5;
  - P0-15 / P0-16 / P0-18 / P0-19 / P0-22 remain pending;
  - code evidence alone cannot resolve a gate;
  - metadata / fake approval cannot resolve a gate;
  - a fixture approval cannot resolve production gates;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_p0_gate_resolution as p0_gate_resolution
from hermes_cli.dev_web_target_b_p0_gate_resolution import (
    P0GateResolutionInput,
    assert_p0_not_resolved_without_authorization,
    build_p0_gate_coverage_report,
    build_p0_gate_resolution_input,
    evaluate_pending_p0_gate_resolution,
)
from hermes_cli.dev_web_target_b_human_approval import (
    build_fixture_human_approval,
    validate_human_approval_record,
)
from hermes_cli.dev_web_target_b_trust_token import (
    build_fixture_trust_token,
    validate_trust_token_envelope,
)

PENDING = ("P0-15", "P0-16", "P0-18", "P0-19", "P0-22")


class TestP0GatesNotResolvedByDefault:
    def test_default_input_resolves_nothing(self) -> None:
        result = evaluate_pending_p0_gate_resolution()
        assert result.resolved_count_delta == 0
        assert result.p0_resolved_count == 0
        assert result.pending_human_review == 5
        for row in result.coverage:
            assert row.resolved is False

    def test_report_zero_delta(self) -> None:
        report = build_p0_gate_coverage_report()
        assert report.p0_total == 24
        assert report.p0_resolved == 0
        assert report.p0_partial_evidence == 19
        assert report.pending_human_review == 5
        assert report.resolved_count_delta == 0
        assert set(report.pending_human_review_gates) == set(PENDING)
        assert report.production_authorization == "NO-GO"

    def test_coverage_lists_every_pending_gate(self) -> None:
        result = evaluate_pending_p0_gate_resolution()
        assert {row.gate_id for row in result.coverage} == set(PENDING)


class TestEvidenceAloneCannotResolve:
    def test_evidence_for_every_gate_still_unresolved(self) -> None:
        inputs = P0GateResolutionInput(
            human_approval=None,
            trust_token=None,
            evidence_gate_ids=PENDING,
        )
        result = evaluate_pending_p0_gate_resolution(inputs)
        assert result.resolved_count_delta == 0
        for row in result.coverage:
            assert row.has_evidence is True
            assert row.resolved is False

    def test_metadata_cannot_resolve(self) -> None:
        result = evaluate_pending_p0_gate_resolution(
            untrusted_metadata={"p0_resolved": "true", "approved": "true"}
        )
        assert result.resolved_count_delta == 0


class TestFixtureApprovalCannotResolveProductionGates:
    def test_fixture_approval_plus_evidence_does_not_resolve(self) -> None:
        fixture_approval = validate_human_approval_record(build_fixture_human_approval())
        fixture_token = validate_trust_token_envelope(build_fixture_trust_token())
        # The fixture approval/token are NOT valid (fixture_only), so even with
        # full evidence the gates stay unresolved.
        inputs = P0GateResolutionInput(
            human_approval=fixture_approval,
            trust_token=fixture_token,
            evidence_gate_ids=PENDING,
            fixture_only=True,
        )
        result = evaluate_pending_p0_gate_resolution(inputs)
        assert result.resolved_count_delta == 0
        assert result.fixture_only is True
        for row in result.coverage:
            assert row.resolved is False


class TestSourcePurity:
    MODULE_PATH = Path(p0_gate_resolution.__file__)

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

    def test_assert_p0_not_resolved_without_authorization_passes(self) -> None:
        assert_p0_not_resolved_without_authorization()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
