"""Phase 4B — Target B runtime orchestrator tests.

Asserts ``hermes_cli/dev_web_target_b_runtime.py`` is inert, frozen, and
fail-closed:

  - :func:`prepare_plugin_execution` returns a PREVIEW ONLY — nothing is loaded,
    imported, or executed;
  - :func:`execute_plugin_gated` returns a DENIED result unconditionally — no
    plugin is executed, no subprocess spawned, no network opened, no secret read,
    no filesystem write;
  - :func:`dry_run_plugin_execution_policy` evaluates without side effects and
    is always denied today;
  - a denied-execution audit event is built (in-memory only);
  - untrusted metadata cannot flip the verdict;
  - the module source contains NO filesystem / network / subprocess /
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

from hermes_cli import dev_web_target_b_runtime as runtime
from hermes_cli.dev_web_target_b_package import build_example_package_descriptor
from hermes_cli.dev_web_target_b_runtime import (
    PluginExecutionRequest,
    assert_runtime_layer_disabled,
    build_denied_runtime_audit,
    build_runtime_execution_preview,
    build_runtime_readiness_report,
    dry_run_plugin_execution_policy,
    execute_plugin_gated,
    prepare_plugin_execution,
)

FORGED_METADATA_PAYLOADS = [
    {"allowed": "true"},
    {"production_runtime_go": "true"},
    {"target_b_authorized": "true"},
    {"force": "true"},
    {"sandbox_bypass": "true"},
]


def _valid_request() -> PluginExecutionRequest:
    return PluginExecutionRequest(
        descriptor=build_example_package_descriptor(),
        entrypoint="tool:example.tool.alpha",
        untrusted_metadata={},
    )


class TestPreparePreview:
    def test_prepare_returns_preview_only(self) -> None:
        preview = prepare_plugin_execution(_valid_request())
        assert preview.prepared is True
        assert preview.execution_preview_only is True
        assert preview.package_valid is True
        assert preview.package_trusted is False
        assert preview.policy_allowed is False

    def test_prepare_non_request_rejected(self) -> None:
        preview = prepare_plugin_execution("not-a-request")
        assert preview.prepared is True  # understood, but
        assert preview.package_valid is False


class TestExecuteDenied:
    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_execute_denied(self, payload: dict) -> None:
        result = execute_plugin_gated(_valid_request(), payload)
        assert result.executed is False
        assert result.allowed is False
        assert result.production_authorization == "NO-GO"

    def test_execute_with_no_request_denied(self) -> None:
        result = execute_plugin_gated(None)
        assert result.executed is False
        assert result.allowed is False
        assert result.prepared is False

    def test_dry_run_denied(self) -> None:
        report = dry_run_plugin_execution_policy(_valid_request())
        assert report.allowed is False

    def test_dry_run_with_no_request_denied(self) -> None:
        report = dry_run_plugin_execution_policy()
        assert report.allowed is False

    def test_denied_audit_event_built(self) -> None:
        event_id = build_denied_runtime_audit({"force": "true"})
        assert event_id == "target-b-runtime-denied"


class TestReportAndBoundary:
    def test_build_runtime_execution_preview_preview_only(self) -> None:
        preview = build_runtime_execution_preview(build_example_package_descriptor())
        assert preview.execution_preview_only is True
        assert preview.policy_allowed is False

    def test_report_disabled(self) -> None:
        report = build_runtime_readiness_report()
        assert report.runtime_enabled is False
        assert report.execution_allowed is False
        assert report.production_authorization == "NO-GO"
        assert report.prepared_preview_only is True

    def test_assert_runtime_layer_disabled_passes(self) -> None:
        assert_runtime_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(runtime.__file__)

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
            assert pattern not in source, f"runtime source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"runtime source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
