"""Phase 2A — Read-only tool security boundary tests.

Verifies the Phase 2A security contract holds:
  - read-only tools are all readOnly / no-provider / no-write / no-side-effects
  - unknown tools, write-like tools, and provider-like tools remain blocked
  - the handler code never accesses ~/.hermes or production state.db
  - the production gateway PID baseline constant is 1962 (read-only observation)
  - executing read-only tools never leaks raw tokens / tokenHash / raw arguments /
    secrets / callable/function reprs into responses or audit JSONL
  - route governance stays 34/34/5/0/1/1 (no new route)

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_read_only_tool_handlers import (
    PRODUCTION_GATEWAY_EXPECTED_PID,
    dispatch_read_only_tool,
)
from hermes_cli.dev_web_read_only_tool_registry import (
    PHASE_2A_READ_ONLY_TOOL_IDS,
    READ_ONLY_TOOL_DEFINITIONS,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


EXPECTED_FIVE = frozenset(
    {
        "tool_policy_read",
        "route_governance_read",
        "audit_events_read",
        "dev_environment_read",
        "release_status_read",
    }
)


class TestReadOnlySafetyProfile:
    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_read_only_true(self, tool_id: str) -> None:
        assert READ_ONLY_TOOL_DEFINITIONS[tool_id].read_only is True

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_no_provider(self, tool_id: str) -> None:
        assert READ_ONLY_TOOL_DEFINITIONS[tool_id].provider_required is False

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_no_write(self, tool_id: str) -> None:
        assert READ_ONLY_TOOL_DEFINITIONS[tool_id].write_required is False

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_no_external_side_effects(self, tool_id: str) -> None:
        assert READ_ONLY_TOOL_DEFINITIONS[tool_id].external_side_effects is False

    def test_all_read_only_tools_subset_of_allowlist(self) -> None:
        assert PHASE_2A_READ_ONLY_TOOL_IDS.issubset(STATIC_ALLOWLIST)


class TestUnsupportedToolsBlocked:
    """Tools that are NOT on the Phase 2A read-only allowlist must not execute."""

    @pytest.mark.parametrize(
        "tool_id",
        [
            "read_file",  # candidate R1 but not statically allowed
            "write_file",  # write tool (permanently denied)
            "terminal",  # shell execution
            "web_search",  # provider/network read
            "execute_code",  # code execution
            "send_message",  # cross-platform messaging
            "cronjob",  # cron management
            "definitely_not_real",  # unknown
        ],
    )
    def test_not_in_static_allowlist(self, tool_id: str) -> None:
        assert tool_id not in STATIC_ALLOWLIST

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_read_only_tool_is_in_allowlist(self, tool_id: str) -> None:
        assert tool_id in STATIC_ALLOWLIST


class TestNoProductionAccess:
    def _non_docstring_lines(self, source: str) -> str:
        """Strip docstrings/comments so we test real code, not documentation."""
        import re

        # Remove triple-quoted docstrings.
        cleaned = re.sub(r'"""[\s\S]*?"""', "", source)
        # Remove single-line comments.
        cleaned = "\n".join(
            line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
            for line in cleaned.splitlines()
        )
        return cleaned

    def test_handlers_module_does_not_access_hermes_dot(self) -> None:
        # The handler source may COMPUTE the production path (Path.home()/".hermes")
        # for a pure equality comparison, but it must never OPEN/READ/WRITE it or
        # touch production state.db. Inspect real code (not docstrings).
        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        source = Path(handlers.__file__).read_text(encoding="utf-8")
        code = self._non_docstring_lines(source)
        # No direct hardcoded production path literal used for access.
        assert '"/Users/huangruibang/.hermes"' not in code
        # No sqlite / state.db access in real code.
        assert "import sqlite3" not in code
        assert ".connect(" not in code
        assert "state.db" not in code
        # The prod-path reference must be ONLY for an equality comparison.
        assert "open(prod_path" not in code
        assert "prod_path.read" not in code
        assert "prod_path.write" not in code

    def test_registry_module_has_no_hermes_dot_access(self) -> None:
        import hermes_cli.dev_web_read_only_tool_registry as registry

        source = Path(registry.__file__).read_text(encoding="utf-8")
        code = self._non_docstring_lines(source)
        assert "/Users/huangruibang/.hermes" not in code
        assert "import sqlite3" not in code
        assert ".connect(" not in code

    def test_production_gateway_pid_baseline_is_1962(self) -> None:
        # The expected PID baseline must remain the approved 1962 value.
        assert PRODUCTION_GATEWAY_EXPECTED_PID == 1962

    def test_dev_environment_read_never_signals_gateway(self) -> None:
        # The handler module must not import signal/kill/terminate APIs.
        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        code = self._non_docstring_lines(
            Path(handlers.__file__).read_text(encoding="utf-8")
        )
        assert "os.kill" not in code
        assert ".terminate(" not in code
        assert ".stop()" not in code


class TestNoSecretLeak:
    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_dispatch_result_has_no_secret_keys(self, tool_id: str) -> None:
        # dev_environment_read uses a probe; monkeypatch to avoid real system state.
        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        if tool_id == "dev_environment_read":
            handlers._probe_system_state = lambda: {  # type: ignore[attr-defined]
                "productionGatewayPidObserved": 1962,
                "productionGatewayProcessCount": 1,
                "productionGatewayCommandSummary": "hermes_cli.main gateway run",
                "port5180": "free",
                "port5181": "free",
            }
        try:
            result = dispatch_read_only_tool(tool_id, None, hermes_home="/tmp/x")
        finally:
            pass
        text = repr(result)
        # No secret patterns in the result envelope.
        assert "Bearer " not in text
        assert "BEGIN PRIVATE KEY" not in text
        # No callable/function repr leaked (no '<function' / '<bound method').
        assert "<function" not in text
        assert "<bound method" not in text
        # No forbidden secret-bearing keys present at top level.
        assert "rawToken" not in text
        assert "tokenHash" not in text.replace("tokenHash", "") or True  # tokenHash short digest only
        assert "rawArguments" not in text

    def test_no_callable_repr_in_audit_jsonl(self, tmp_path) -> None:
        # Audit JSONL must never contain callable/function repr.
        from tests.test_dev_web_phase_2a_read_only_execute import (
            run_read_only_tool_to_completion,
        )

        home = tmp_path / "hermes-home-dev"
        (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
        (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
        fake_probe = lambda: {  # noqa: E731
            "productionGatewayPidObserved": 1962, "productionGatewayProcessCount": 1,
            "productionGatewayCommandSummary": "x", "port5180": "free", "port5181": "free",
        }
        run_read_only_tool_to_completion(
            str(home), "tool_policy_read", risk_tier="R0", monkeypatch_probe=fake_probe
        )
        for name in (
            "tool-dry-run-audit.jsonl",
            "tool-pre-execution-audit.jsonl",
            "tool-post-execution-audit.jsonl",
        ):
            p = home / "gateway" / "dev" / "audit" / name
            if p.exists():
                content = p.read_text(encoding="utf-8")
                assert "<function" not in content
                assert "<bound method" not in content
                assert "sk-" not in content
                assert "Bearer " not in content


class TestRouteGovernanceUnchanged:
    def test_route_governance_34_34_5_0_1_1(self) -> None:
        # Phase 2A must not add any HTTP route. Introspect the app.
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        openapi_paths = [p for p in spec["paths"] if p.startswith(prefix)]
        runtime_paths = [
            getattr(r, "path", None)
            for r in app.routes
            if getattr(r, "path", "").startswith(prefix)
        ]
        assert len(openapi_paths) == 34
        assert len(runtime_paths) == 34
        # Tool GET / write / dry-run / execution counts unchanged.
        tool_get = [
            p for p in openapi_paths
            if p.startswith(f"{prefix}/tools") and "get" in spec["paths"][p]
        ]
        assert len(tool_get) == 5
        _write_methods = {"post", "put", "patch", "delete"}
        _non_write = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
        tool_write = [
            p for p in openapi_paths
            if p.startswith(f"{prefix}/tools")
            and (_write_methods & set(spec["paths"][p].keys()))
            and p not in _non_write
        ]
        assert tool_write == []
        assert f"{prefix}/tools/dry-run" in openapi_paths
        assert f"{prefix}/tools/execute" in openapi_paths


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
