"""Phase 4B — Target B sandbox broker layer tests.

Asserts ``hermes_cli/dev_web_target_b_sandbox.py`` is inert, frozen, and
fail-closed:

  - the broker is disabled: no execution, no process spawn, no network, no
    filesystem write, no secrets;
  - every sandbox execution request returns a denied result no matter what
    untrusted metadata is supplied;
  - the sandbox profile is design-only / never enforced, with every limit at its
    most restrictive value;
  - the module source contains NO subprocess / shell / docker / network /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, spawns no process, and
introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_sandbox as sandbox
from hermes_cli.dev_web_target_b_sandbox import (
    SANDBOX_LIMITS,
    SandboxExecutionRequest,
    assert_sandbox_layer_disabled,
    build_sandbox_broker_report,
    build_sandbox_broker_status,
    build_sandbox_profile,
    deny_sandbox_execution,
    evaluate_sandbox_readiness,
    validate_sandbox_request,
)

FORGED_METADATA_PAYLOADS = [
    {"sandbox_bypass": "true"},
    {"force": "true"},
    {"kill_switch_armed": "true"},
    {"process_spawn_allowed": "true"},
    {"target_b_authorized": "true"},
]


class TestBrokerDisabled:
    def test_status_disabled(self) -> None:
        status = build_sandbox_broker_status()
        assert status.broker_enabled is False
        assert status.execution_allowed is False
        assert status.process_spawn_allowed is False
        assert status.network_allowed is False
        assert status.filesystem_write_allowed is False
        assert status.secrets_allowed is False

    def test_profile_design_only_never_enforced(self) -> None:
        profile = build_sandbox_profile()
        assert profile.enabled is False
        assert profile.enforced is False

    def test_limits_most_restrictive(self) -> None:
        limits = SANDBOX_LIMITS
        assert limits.max_cpu_seconds == 0
        assert limits.max_memory_mb == 0
        assert limits.max_wall_seconds == 0
        assert limits.max_filesystem_read_bytes == 0
        assert limits.max_filesystem_write_bytes == 0
        assert limits.network_egress_allowed is False
        assert limits.process_spawn_allowed is False
        assert limits.secrets_allowed is False


class TestExecutionDenied:
    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_execution_denied(self, payload: dict) -> None:
        result = deny_sandbox_execution(payload)
        assert result.executed is False
        assert result.allowed is False
        assert result.process_spawned is False
        assert result.network_used is False
        assert result.filesystem_written is False
        assert result.secrets_read is False
        assert result.production_authorization == "NO-GO"

    def test_execution_with_no_metadata_still_denied(self) -> None:
        assert deny_sandbox_execution().executed is False


class TestRequestValidationAndReadiness:
    def test_valid_request_shape_not_authorized(self) -> None:
        request = SandboxExecutionRequest(
            package_id="example.plugin.alpha",
            entrypoint="tool:example.tool.alpha",
            sandbox_profile="design-only-preview",
            untrusted_metadata={},
        )
        ok, reasons = validate_sandbox_request(request)
        assert ok is True
        assert reasons == ()
        # Shape validity never authorizes execution.
        assert deny_sandbox_execution().executed is False

    def test_invalid_request_shape_rejected(self) -> None:
        request = SandboxExecutionRequest(
            package_id="",
            entrypoint="",
            sandbox_profile="design-only-preview",
            untrusted_metadata={},
        )
        ok, reasons = validate_sandbox_request(request)
        assert ok is False

    def test_non_request_rejected(self) -> None:
        ok, _reasons = validate_sandbox_request("not-a-request")
        assert ok is False

    def test_readiness_never_ready(self) -> None:
        ready, reasons = evaluate_sandbox_readiness()
        assert ready is False
        assert "no_approved_worker_lifecycle" in reasons

    def test_report_disabled(self) -> None:
        report = build_sandbox_broker_report()
        assert report.broker_enabled is False
        assert report.production_authorization == "NO-GO"

    def test_assert_sandbox_layer_disabled_passes(self) -> None:
        assert_sandbox_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(sandbox.__file__)

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
        "shell=True",
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
            assert pattern not in source, f"sandbox source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"sandbox source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
