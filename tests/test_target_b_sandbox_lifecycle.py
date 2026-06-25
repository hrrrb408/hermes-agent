"""Phase 4C — Target B sandbox worker lifecycle approval tests.

Asserts ``hermes_cli/dev_web_target_b_sandbox_lifecycle.py`` is inert, frozen,
and fail-closed:

  - the lifecycle is not approved by default;
  - no worker starts, no process spawns, no network / filesystem write / secrets;
  - the production gateway (PID 28428) is untouched;
  - the default plan is never approved and metadata cannot flip it;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, never spawns a process, and
introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_sandbox_lifecycle as sandbox_lifecycle
from hermes_cli.dev_web_target_b_sandbox_lifecycle import (
    SandboxWorkerLifecyclePlan,
    assert_sandbox_lifecycle_not_approved,
    build_sandbox_lifecycle_plan,
    build_sandbox_lifecycle_report,
    evaluate_sandbox_lifecycle_approval,
    validate_sandbox_lifecycle_plan,
)


class TestSandboxLifecycleNotApproved:
    def test_default_plan_not_approved(self) -> None:
        plan = build_sandbox_lifecycle_plan()
        assert plan.approved is False
        assert plan.worker_model == "disabled"
        assert plan.start_policy == "never"

    def test_evaluation_denies_everything(self) -> None:
        result = evaluate_sandbox_lifecycle_approval()
        assert result.lifecycle_approved is False
        assert result.worker_start_allowed is False
        assert result.process_spawn_allowed is False
        assert result.network_allowed is False
        assert result.filesystem_write_allowed is False
        assert result.secrets_allowed is False
        assert result.production_gateway_untouched is True
        assert result.production_authorization == "NO-GO"

    def test_metadata_cannot_flip_approval(self) -> None:
        result = evaluate_sandbox_lifecycle_approval(
            untrusted_metadata={"sandbox_bypass": "true", "kill_switch_armed": "true"}
        )
        assert result.lifecycle_approved is False
        assert "sandbox_bypass" in result.ignored_metadata_keys
        assert "kill_switch_armed" in result.ignored_metadata_keys

    def test_report_denies_everything(self) -> None:
        report = build_sandbox_lifecycle_report()
        assert report.lifecycle_approved is False
        assert report.worker_start_allowed is False
        assert report.process_spawn_allowed is False
        assert report.network_allowed is False
        assert report.filesystem_write_allowed is False
        assert report.secrets_allowed is False
        assert report.production_gateway_untouched is True
        assert report.production_authorization == "NO-GO"


class TestPlanValidation:
    def test_default_plan_requires_reviewer(self) -> None:
        ok, reasons = validate_sandbox_lifecycle_plan(build_sandbox_lifecycle_plan())
        assert ok is False
        assert "reviewer_approval_required" in reasons

    def test_secrets_never_allowed(self) -> None:
        from hermes_cli.dev_web_target_b_sandbox_lifecycle import (
            DEFAULT_RESOURCE_LIMITS,
            SandboxIsolationPolicy,
        )

        plan = SandboxWorkerLifecyclePlan(
            worker_model="x",
            start_policy="manual",
            stop_policy="manual",
            restart_policy="manual",
            resource_limits=DEFAULT_RESOURCE_LIMITS,
            isolation_policy=SandboxIsolationPolicy(
                filesystem_write_allowed=False,
                network_allowed=False,
                process_spawn_allowed=False,
                secrets_allowed=True,
                host_mount_allowed=False,
                privileged_allowed=False,
            ),
            logging_policy="x",
            crash_policy="x",
            kill_switch_policy="x",
            reviewer_approval_id="reviewer-1",
        )
        ok, reasons = validate_sandbox_lifecycle_plan(plan)
        assert ok is False
        assert "secrets_never_allowed" in reasons


class TestSourcePurity:
    MODULE_PATH = Path(sandbox_lifecycle.__file__)

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
        "os.kill",
        "signal.",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
        "docker",
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

    def test_assert_sandbox_lifecycle_not_approved_passes(self) -> None:
        assert_sandbox_lifecycle_not_approved()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
