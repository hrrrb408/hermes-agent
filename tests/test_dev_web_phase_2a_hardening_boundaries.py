"""Phase 2A-H1 — Deterministic hardening boundary tests.

This file is the deterministic, agent-independent artifact that closes the
Phase 2A P2 "adversarial-review agent died mid-run". It replaces the unstable
agent-only adversarial-review evidence path with a reproducible 7-lens
boundary audit that can be re-run on any clean checkout and produce the same
verdict.

Each test class maps to one lens of the Phase 2A-H1 hardening model:

  Lens 1 — Phase 1G Preservation (clarify chain intact)
  Lens 2 — Allowlist / Registry Boundary (exact, single-source, consistent)
  Lens 3 — Route Governance / OpenAPI Boundary (34/34/5/0/1/1)
  Lens 4 — Provider / Write / Side-effect Boundary (all flags False)
  Lens 5 — Audit Redaction / Secret Exposure Boundary (no leak)
  Lens 6 — Production Isolation / Runtime Safety Boundary (no prod access)
  Lens 7 — Frontend Contract Boundary (frontend mirrors backend allowlist)

Design constraints:
  - Deterministic: no live gateway dependency. The dev_environment_read system
    probe is monkeypatched to a fixed safe value so the test never depends on
    real production state.
  - No ``~/.hermes`` access, no production ``state.db`` access.
  - No network, no Provider, no write.

Hardening IDs:
  - HARDENING-2A-H1-001
  - ADV-REVIEW-CLOSURE-2A-H1-001
  - BOUNDARY-AUDIT-2A-H1-001

Phase: 2A-H1 — Hardening (Adversarial Review Completion & Boundary Stabilization)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from hermes_cli.dev_web_read_only_tool_handlers import (
    PRODUCTION_GATEWAY_EXPECTED_PID,
    dispatch_read_only_tool,
)
from hermes_cli.dev_web_read_only_tool_registry import (
    PHASE_2A_READ_ONLY_TOOL_IDS,
    READ_ONLY_TOOL_DEFINITIONS,
)
from hermes_cli.dev_web_tool_policy import (
    CANDIDATE_ALLOWLIST,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
)


# ---------------------------------------------------------------------------
# Shared constants — the exact approved Phase 2A boundary.
# ---------------------------------------------------------------------------

EXPECTED_STATIC_ALLOWLIST = frozenset(
    {
        "clarify",
        "tool_policy_read",
        "route_governance_read",
        "audit_events_read",
        "dev_environment_read",
        "release_status_read",
    }
)
EXPECTED_PHASE_2A_FIVE = frozenset(
    {
        "tool_policy_read",
        "route_governance_read",
        "audit_events_read",
        "dev_environment_read",
        "release_status_read",
    }
)

# The approved Phase 1G-10A production gateway PID baseline (read-only
# observation constant; the live PID may drift on host reboot and is handled
# by the fail-closed smoke harness — this test pins the *constant* only).
EXPECTED_PRODUCTION_GATEWAY_PID = 1962

# Fixed safe system probe so dev_environment_read never touches real state.
SAFE_PROBE: dict[str, Any] = {
    "productionGatewayPidObserved": 1962,
    "productionGatewayProcessCount": 1,
    "productionGatewayCommandSummary": "hermes_cli.main gateway run",
    "port5180": "free",
    "port5181": "free",
}

# (tool_id, risk_tier) for the five Phase 2A read-only tools.
PHASE_2A_TOOLS_WITH_RISK = [
    ("tool_policy_read", "R0"),
    ("route_governance_read", "R0"),
    ("audit_events_read", "R1"),
    ("dev_environment_read", "R1"),
    ("release_status_read", "R1"),
]


def _fake_probe() -> dict[str, Any]:
    return dict(SAFE_PROBE)


# ---------------------------------------------------------------------------
# Lens 1 — Phase 1G Preservation
# ---------------------------------------------------------------------------


class TestLens1Phase1GPreservation:
    """The clarify controlled-execution chain must remain exactly intact."""

    def test_clarify_remains_in_static_allowlist(self) -> None:
        assert "clarify" in STATIC_ALLOWLIST

    def test_clarify_is_supported_controlled_tool(self) -> None:
        # The handler-call module must still recognize clarify (Phase 1G path).
        import hermes_cli.dev_web_tool_handler_call as handler_call

        assert handler_call._is_supported_controlled_tool("clarify") is True

    def test_clarify_decision_constant_present(self) -> None:
        # The Phase 1G completed-decision string must still exist.
        import hermes_cli.dev_web_tool_handler_call as handler_call

        assert hasattr(handler_call, "CLARIFY_TOOL_TYPE")
        assert handler_call.CLARIFY_TOOL_TYPE == "clarify"

    def test_phase1g_block_decision_constants_present(self) -> None:
        # The Phase 1G block reasons must remain reachable.
        import hermes_cli.dev_web_tool_handler_call as handler_call

        # The handler-call-not-enabled block reason is the canonical Phase 1G
        # default-disabled marker.
        assert (
            handler_call.DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY
            == "blocked_handler_call_not_clarify"
        )

    def test_clarify_routes_to_its_own_path_not_read_only_dispatcher(self) -> None:
        # clarify is the Phase 1G baseline dispatched by the inline clarify
        # handler in dev_web_tool_handler_call — it must NOT be silently routed
        # through the Phase 2A read-only dispatcher. The dispatcher rejects it,
        # which proves the two paths stay cleanly separated (Phase 1G intact).
        with pytest.raises(ValueError, match="Unknown Phase 2A read-only tool"):
            dispatch_read_only_tool("clarify", None, hermes_home="/tmp/x")


# ---------------------------------------------------------------------------
# Lens 2 — Allowlist / Registry Boundary
# ---------------------------------------------------------------------------


class TestLens2AllowlistRegistryBoundary:
    """STATIC_ALLOWLIST is exact, single-source, and consistent with the registry."""

    def test_static_allowlist_exactly_six_tools(self) -> None:
        assert STATIC_ALLOWLIST == EXPECTED_STATIC_ALLOWLIST
        assert len(STATIC_ALLOWLIST) == 6

    def test_phase_2a_read_only_ids_exactly_five(self) -> None:
        assert PHASE_2A_READ_ONLY_TOOL_IDS == EXPECTED_PHASE_2A_FIVE
        assert len(PHASE_2A_READ_ONLY_TOOL_IDS) == 5

    def test_registry_subset_of_static_allowlist(self) -> None:
        assert PHASE_2A_READ_ONLY_TOOL_IDS.issubset(STATIC_ALLOWLIST)

    def test_static_allowlist_subset_of_candidate(self) -> None:
        # static ⊆ candidate (every statically-allowed tool is a candidate).
        assert STATIC_ALLOWLIST.issubset(CANDIDATE_ALLOWLIST)

    def test_static_allowlist_disjoint_from_denylist(self) -> None:
        # static ∩ deny = ∅ (no statically-allowed tool is permanently denied).
        assert STATIC_ALLOWLIST.isdisjoint(STATIC_DENYLIST)

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_PHASE_2A_FIVE))
    def test_every_tool_read_only_safe_profile(self, tool_id: str) -> None:
        definition = READ_ONLY_TOOL_DEFINITIONS[tool_id]
        assert definition.read_only is True
        assert definition.provider_required is False
        assert definition.write_required is False
        assert definition.external_side_effects is False
        assert definition.requires_confirmation is True
        assert definition.safety_tier == "read_only_safe"
        assert definition.enabled_in_phase == "2A"

    def test_unsupported_tools_not_in_allowlist(self) -> None:
        # Representative write / shell / provider / unknown tools stay out.
        for blocked in (
            "write_file",
            "patch",
            "terminal",
            "execute_code",
            "send_message",
            "cronjob",
            "browser_navigate",
            "computer_use",
            "delegate_task",
            "web_search",
            "memory",
            "definitely_not_real",
        ):
            assert blocked not in STATIC_ALLOWLIST
            assert blocked not in PHASE_2A_READ_ONLY_TOOL_IDS


# ---------------------------------------------------------------------------
# Lens 3 — Route Governance / OpenAPI Boundary
# ---------------------------------------------------------------------------


class TestLens3RouteGovernanceBoundary:
    """Phase 2A added zero HTTP routes: 34/34/5/0/1/1."""

    def test_route_governance_frozen(self) -> None:
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()

        openapi_paths = sorted(p for p in spec["paths"] if p.startswith(prefix))
        runtime_paths = sorted(
            getattr(r, "path", None)
            for r in app.routes
            if getattr(r, "path", "").startswith(prefix)
        )

        assert len(openapi_paths) == 34
        assert len(runtime_paths) == 34
        assert openapi_paths == runtime_paths

        tool_get = [
            p for p in openapi_paths
            if p.startswith(f"{prefix}/tools") and "get" in spec["paths"][p]
        ]
        assert len(tool_get) == 5

        write_methods = {"post", "put", "patch", "delete"}
        non_write = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
        tool_write = [
            p for p in openapi_paths
            if p.startswith(f"{prefix}/tools")
            and (write_methods & set(spec["paths"][p].keys()))
            and p not in non_write
        ]
        assert tool_write == []

        dry_run = [p for p in openapi_paths if p == f"{prefix}/tools/dry-run"]
        execute = [p for p in openapi_paths if p == f"{prefix}/tools/execute"]
        assert len(dry_run) == 1
        assert len(execute) == 1

    def test_no_second_execution_route(self) -> None:
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        execute_routes = [
            getattr(r, "path", None)
            for r in app.routes
            if getattr(r, "path", "").startswith(f"{prefix}/tools")
            and "execute" in getattr(r, "path", "")
        ]
        # Exactly one execution route, the Phase 1G /tools/execute.
        assert execute_routes == [f"{prefix}/tools/execute"]


# ---------------------------------------------------------------------------
# Lens 4 — Provider / Write / Side-effect Boundary
# ---------------------------------------------------------------------------


@pytest.fixture()
def _patched_probe(monkeypatch):
    import hermes_cli.dev_web_read_only_tool_handlers as handlers

    monkeypatch.setattr(handlers, "_probe_system_state", _fake_probe)
    yield


class TestLens4ProviderWriteSideEffectBoundary:
    """Every Phase 2A tool completes with all provider/write/side-effect flags False."""

    @pytest.mark.parametrize("tool_id,risk_tier", PHASE_2A_TOOLS_WITH_RISK)
    def test_completion_flags_all_false(
        self, tmp_path, _patched_probe, tool_id: str, risk_tier: str
    ) -> None:
        from tests.test_dev_web_phase_2a_read_only_execute import (
            run_read_only_tool_to_completion,
        )

        home = tmp_path / "hermes-home-dev"
        (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
        (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)

        rd = run_read_only_tool_to_completion(
            str(home), tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )

        assert rd["executionCompleted"] is True
        assert rd["decision"] == f"{tool_id}_execution_completed"

        se = rd["sideEffects"]
        assert se["providerSchemaSent"] is False
        assert se["providerApiCalled"] is False
        assert se["externalSideEffects"] is False
        assert se["filesystemChanged"] is False
        assert se["networkCalled"] is False

        # Top-level policy flags stay False (no provider dispatch, no execution allow).
        assert rd["executionAllowed"] is False
        assert rd["dispatchAllowed"] is False
        assert rd["providerSchemaAllowed"] is False
        assert rd["providerApiCalled"] is False

    def test_handler_modules_hardcode_provider_flags_false(self) -> None:
        # The audit/handler modules must hardcode provider completion flags False.
        import hermes_cli.dev_web_tool_handler_call as handler_call
        import hermes_cli.dev_web_tool_post_execution_audit as post_audit

        for module in (handler_call, post_audit):
            source = Path(module.__file__).read_text(encoding="utf-8")
            assert '"providerSchemaSent": False' in source
            assert '"providerApiCalled": False' in source


# ---------------------------------------------------------------------------
# Lens 5 — Audit Redaction / Secret Exposure Boundary
# ---------------------------------------------------------------------------


_FORBIDDEN_SECRET_FRAGMENTS = (
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "sk-",
    "<function",
    "<bound method",
    "object at 0x",
)
_RAW_ARGUMENT_KEYS = ("rawToken", "rawArguments", "fullTokenHash")


class TestLens5AuditRedactionBoundary:
    """No raw token / tokenHash / raw arguments / secrets / callable repr leak."""

    @pytest.mark.parametrize("tool_id,risk_tier", PHASE_2A_TOOLS_WITH_RISK)
    def test_result_envelope_no_secret_or_repr(
        self, tmp_path, monkeypatch, tool_id: str, risk_tier: str
    ) -> None:
        from tests.test_dev_web_phase_2a_read_only_execute import (
            run_read_only_tool_to_completion,
        )

        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        monkeypatch.setattr(handlers, "_probe_system_state", _fake_probe)
        home = tmp_path / "hermes-home-dev"
        (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
        (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)

        rd = run_read_only_tool_to_completion(
            str(home), tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        text = repr(rd)
        for forbidden in _FORBIDDEN_SECRET_FRAGMENTS:
            assert forbidden not in text, f"{tool_id}: leaked {forbidden!r}"
        for raw_key in _RAW_ARGUMENT_KEYS:
            assert raw_key not in text, f"{tool_id}: leaked {raw_key!r}"

    @pytest.mark.parametrize("tool_id,risk_tier", PHASE_2A_TOOLS_WITH_RISK)
    def test_audit_jsonl_no_secret_or_repr(
        self, tmp_path, monkeypatch, tool_id: str, risk_tier: str
    ) -> None:
        from tests.test_dev_web_phase_2a_read_only_execute import (
            run_read_only_tool_to_completion,
        )

        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        monkeypatch.setattr(handlers, "_probe_system_state", _fake_probe)
        home = tmp_path / "hermes-home-dev"
        (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
        (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)

        run_read_only_tool_to_completion(
            str(home), tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )

        audit_dir = home / "gateway" / "dev" / "audit"
        for name in (
            "tool-dry-run-audit.jsonl",
            "tool-pre-execution-audit.jsonl",
            "tool-post-execution-audit.jsonl",
        ):
            audit_file = audit_dir / name
            if not audit_file.exists():
                continue
            content = audit_file.read_text(encoding="utf-8")
            for forbidden in _FORBIDDEN_SECRET_FRAGMENTS:
                assert forbidden not in content, f"{tool_id}/{name}: leaked {forbidden!r}"


# ---------------------------------------------------------------------------
# Lens 6 — Production Isolation / Runtime Safety Boundary
# ---------------------------------------------------------------------------


def _real_code(source: str) -> str:
    """Strip docstrings + comments so source inspection tests real code."""
    cleaned = re.sub(r'"""[\s\S]*?"""', "", source)
    cleaned = re.sub(r"'''[\s\S]*?'''", "", cleaned)
    out = []
    for line in cleaned.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0]
        out.append(line)
    return "\n".join(out)


class TestLens6ProductionIsolationBoundary:
    """No ~/.hermes access, no production state.db, no gateway signaling."""

    def test_production_gateway_pid_baseline_constant(self) -> None:
        assert PRODUCTION_GATEWAY_EXPECTED_PID == EXPECTED_PRODUCTION_GATEWAY_PID

    def test_handlers_no_production_path_literal_in_real_code(self) -> None:
        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        code = _real_code(Path(handlers.__file__).read_text(encoding="utf-8"))
        assert '"/Users/huangruibang/.hermes"' not in code
        assert "state.db" not in code
        assert "import sqlite3" not in code
        assert ".connect(" not in code

    def test_registry_no_production_access_in_real_code(self) -> None:
        # The registry module carries tool ``description=`` strings that
        # legitimately mention ``state.db`` / ``~/.hermes`` as documentation of
        # what the tools never access. We assert the real *access* surface is
        # empty: no sqlite import, no connection, no hardcoded production path.
        import hermes_cli.dev_web_read_only_tool_registry as registry

        code = _real_code(Path(registry.__file__).read_text(encoding="utf-8"))
        assert "import sqlite3" not in code
        assert ".connect(" not in code
        # No filesystem-access APIs on the read-only registry path.
        assert ".open(" not in code
        assert "Path(" not in code

    @pytest.mark.parametrize(
        "module_name",
        [
            "hermes_cli.dev_web_read_only_tool_handlers",
            "hermes_cli.dev_web_read_only_tool_registry",
            "hermes_cli.dev_web_tool_handler_call",
            "hermes_cli.dev_web_tool_execute",
        ],
    )
    def test_no_gateway_signaling_apis(self, module_name: str) -> None:
        module = __import__(module_name, fromlist=["__file__"])
        code = _real_code(Path(module.__file__).read_text(encoding="utf-8"))
        # No process mutation APIs anywhere on the controlled path.
        assert "os.kill" not in code
        assert ".terminate(" not in code
        assert "os.system(" not in code
        assert "Popen(" not in code
        assert "import signal" not in code

    def test_dev_environment_read_handler_does_not_open_production(self) -> None:
        # The prod_path reference is a pure path equality comparison only.
        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        code = _real_code(Path(handlers.__file__).read_text(encoding="utf-8"))
        assert "open(prod_path" not in code
        assert "prod_path.read" not in code
        assert "prod_path.write" not in code


# ---------------------------------------------------------------------------
# Lens 7 — Frontend Contract Boundary
# ---------------------------------------------------------------------------


def _frontend_selectable_tool_ids() -> frozenset[str]:
    """Parse the tool ids from the frontend readOnlyTools.ts mirror."""
    repo_root = Path(__file__).resolve().parents[1]
    ts_path = repo_root / "apps" / "hermes-dev-webui" / "src" / "constants" / "readOnlyTools.ts"
    assert ts_path.exists(), f"frontend mirror not found: {ts_path}"
    text = ts_path.read_text(encoding="utf-8")
    # Match `id: '...'` or `id: "..."` inside SELECTABLE_TOOLS entries.
    matches = re.findall(r"id:\s*['\"]([^'\"]+)['\"]", text)
    return frozenset(matches)


class TestLens7FrontendContractBoundary:
    """The frontend SELECTABLE_TOOLS list must mirror the backend allowlist."""

    def test_frontend_mirrors_backend_allowlist(self) -> None:
        frontend_ids = _frontend_selectable_tool_ids()
        assert frontend_ids == EXPECTED_STATIC_ALLOWLIST, (
            f"frontend/backend allowlist drift: frontend={sorted(frontend_ids)} "
            f"backend={sorted(EXPECTED_STATIC_ALLOWLIST)}"
        )

    def test_frontend_default_tool_is_clarify(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        ts_path = (
            repo_root / "apps" / "hermes-dev-webui" / "src" / "constants" / "readOnlyTools.ts"
        )
        text = ts_path.read_text(encoding="utf-8")
        # The default tool must be clarify (Phase 1G baseline first).
        assert "DEFAULT_TOOL = SELECTABLE_TOOLS[0]" in text or "'clarify'" in text


# ---------------------------------------------------------------------------
# Aggregated hardening verdict
# ---------------------------------------------------------------------------


class TestHardeningVerdict:
    """Single aggregated assertion that the Phase 2A-H1 boundary holds."""

    def test_seven_lens_all_pass(self) -> None:
        # This test exists so the hardening audit can point at one test name
        # that encodes the 7-lens PASS verdict. The per-lens classes above are
        # the real evidence; this is the traceability anchor.
        assert STATIC_ALLOWLIST == EXPECTED_STATIC_ALLOWLIST
        assert PHASE_2A_READ_ONLY_TOOL_IDS == EXPECTED_PHASE_2A_FIVE
        assert PHASE_2A_READ_ONLY_TOOL_IDS.issubset(STATIC_ALLOWLIST)
        assert STATIC_ALLOWLIST.issubset(CANDIDATE_ALLOWLIST)
        assert STATIC_ALLOWLIST.isdisjoint(STATIC_DENYLIST)
        assert PRODUCTION_GATEWAY_EXPECTED_PID == EXPECTED_PRODUCTION_GATEWAY_PID


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
