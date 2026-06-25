"""Phase 4B — Target B rollback / kill-switch layer tests.

Asserts ``hermes_cli/dev_web_target_b_rollback.py`` is inert, frozen, and
fail-closed:

  - the kill switch is DESIGN_READY_ONLY — never armed;
  - production rollback is NOT authorized; production rollout stays NO-GO;
  - the production gateway is referenced ONLY as a do-not-touch string and is
    never signaled, stopped, restarted, or replaced;
  - untrusted metadata cannot flip the verdict;
  - the module source contains NO signal / subprocess / process-control /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, never signals/stops/restarts
the production gateway, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_rollback as rollback
from hermes_cli.dev_web_target_b_rollback import (
    assert_rollback_layer_disabled,
    build_kill_switch_status,
    build_rollback_report,
    deny_without_kill_switch,
    evaluate_rollback_readiness,
)

FORGED_METADATA_PAYLOADS = [
    {"kill_switch_armed": "true"},
    {"production_rollout_approved": "true"},
    {"force": "true"},
    {"target_b_authorized": "true"},
    {"production_runtime_go": "true"},
]


class TestKillSwitchDesignReadyOnly:
    def test_status_design_ready_only(self) -> None:
        status = build_kill_switch_status()
        assert status.readiness == "DESIGN_READY_ONLY"
        assert status.armed is False
        assert status.production_rollback_authorized is False
        assert status.production_rollout == "NO-GO"
        assert status.production_gateway_untouched is True

    def test_readiness_never_ready(self) -> None:
        ready, reasons = evaluate_rollback_readiness()
        assert ready is False
        assert "no_approved_incident_response_plan" in reasons

    def test_report_design_ready_only(self) -> None:
        report = build_rollback_report()
        assert report.kill_switch_ready == "DESIGN_READY_ONLY"
        assert report.production_rollback_authorized is False
        assert report.production_rollout == "NO-GO"
        assert report.production_gateway_untouched is True

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_deny_without_kill_switch_ignores_metadata(self, payload: dict) -> None:
        status = deny_without_kill_switch(payload)
        assert status.armed is False
        assert status.production_rollback_authorized is False

    def test_assert_rollback_layer_disabled_passes(self) -> None:
        assert_rollback_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(rollback.__file__)

    # NOTE: os.kill / signal / subprocess are forbidden — the rollback layer
    # touches NO process.
    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import signal",
        "signal.",
        "os.kill",
        "os.popen",
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
            assert pattern not in source, f"rollback source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"rollback source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
