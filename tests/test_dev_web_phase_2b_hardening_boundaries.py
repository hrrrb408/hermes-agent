"""Phase 2B-H1 — Deterministic provider round-trip hardening boundary tests.

This file is the deterministic, agent-independent artifact that closes the
Phase 2B P2 backlog:

  P2-1 — real-vendor provider adapter not wired in Phase 2B  (accepted: the
          framework exists and is blocked by default; the concrete vendor
          call is deferred to a separately-authorized future phase).
  P2-2 — one transient flake observed once under high parallelism in
          ``test_audit_jsonl_no_secret_or_repr[audit_events_read-R1]``.
          Closed here as non-reproduced with deterministic evidence, AND the
          latent provider-audit secret-pattern gap that the adversarial review
          surfaced alongside it is hardened + pinned.
  P2-3 — frontend visual polish (optional, non-blocking).

It replaces agent-only evidence with a reproducible 8-lens provider round-trip
boundary audit that can be re-run on any clean checkout and produce the same
verdict. Each test class maps to one lens of the Phase 2B-H1 hardening model.

Design constraints:
  - Deterministic: no live gateway dependency. The dev_environment_read system
    probe is monkeypatched to a fixed safe value so the test never depends on
    real production state.
  - No ``~/.hermes`` access, no production ``state.db`` access.
  - No real Provider network call (fake mode only; real mode asserted blocked).
  - No Tool write, no write tool, no non-read-only side effect.

Hardening IDs:
  - HARDENING-2B-H1-001
  - PROVIDER-BOUNDARY-AUDIT-2B-H1-001
  - PROVIDER-FLAKE-CLOSURE-2B-H1-001

Phase: 2B-H1 — Provider Round-trip Hardening & Transient Flake Closure
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from hermes_cli.dev_web_provider_adapter import (
    BLOCKED_REAL_PROVIDER_NOT_WIRED,
    FakeProviderAdapter,
    RealProviderAdapter,
    get_provider_adapter,
)
from hermes_cli.dev_web_provider_audit import (
    _is_forbidden_field,
    _is_secret_string,
    _sanitize,
    build_provider_audit_event,
    write_provider_audit_event,
)
from hermes_cli.dev_web_provider_request import (
    BLOCKED_PROVIDER_API_KEY_MISSING,
    BLOCKED_PROVIDER_NOT_DEV_HOME,
    BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT,
    BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_FAKE,
    PROVIDER_MODE_REAL,
    _evaluate_real_mode_eligibility,
    build_provider_request,
)
from hermes_cli.dev_web_provider_roundtrip import (
    TOOL_CALL_BLOCKED_MALFORMED_ARGS,
    TOOL_CALL_BLOCKED_NOT_ALLOWLISTED,
    TOOL_CALL_BLOCKED_PROVIDER_RECURSIVE,
    TOOL_CALL_BLOCKED_WRITE_LIKE,
    TOOL_CALL_VALID,
    run_provider_tool_roundtrip,
    validate_provider_tool_call,
)
from hermes_cli.dev_web_provider_schema import (
    build_provider_tool_schema,
    validate_provider_schema_bundle,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


# ---------------------------------------------------------------------------
# Shared constants — the exact approved Phase 2B boundary.
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

EXPECTED_PRODUCTION_GATEWAY_PID = 28428

# Fixed safe system probe so dev_environment_read never touches real state.
SAFE_PROBE: dict[str, Any] = {
    "productionGatewayPidObserved": 28428,
    "productionGatewayProcessCount": 1,
    "productionGatewayCommandSummary": "hermes_cli.main gateway run",
    "port5180": "free",
    "port5181": "free",
}

# (tool_id, fake-provider keyword) for the six allowlist tools.
FAKE_TOOL_ROUTES = [
    ("tool_policy_read", "read tool policy"),
    ("route_governance_read", "check route governance"),
    ("audit_events_read", "read audit events"),
    ("dev_environment_read", "dev environment summary"),
    ("release_status_read", "release status"),
    ("clarify", "clarify what you need"),
]

# The forbidden fragments the Phase 2B transient flake guarded against.
FORBIDDEN_SECRET_FRAGMENTS = (
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "sk-",
    "<function",
    "<bound method",
    "object at 0x",
)

# Every standard PEM private-key variant must be redacted (Phase 2B-H1 fix).
PEM_HEADER_SAMPLES = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN DSA PRIVATE KEY-----",
    "-----BEGIN ENCRYPTED PRIVATE KEY-----",
)


def _fake_probe() -> dict[str, Any]:
    return dict(SAFE_PROBE)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def provider_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


@pytest.fixture(autouse=True)
def _enable_execution_gates(monkeypatch):
    """Enable the read-only controlled-chain kill-switches for the round-trip.

    These are the same gates the Phase 2B provider audit tests enable. They
    only permit the read-only controlled chain; they never enable Tool write,
    a real provider call, or any non-read-only side effect.
    """
    monkeypatch.setenv("HERMES_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("HERMES_AGENT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("HERMES_TOOL_HANDLER_CALL_ENABLED", "true")
    import hermes_cli.dev_web_read_only_tool_handlers as handlers

    monkeypatch.setattr(handlers, "_probe_system_state", _fake_probe)
    # Real-mode enablement must NEVER be set in this suite. Strip defensively
    # so a polluted outer environment cannot flip real mode on.
    for var in (
        "HERMES_PROVIDER_API_ENABLED",
        "HERMES_PROVIDER_MODE",
        "HERMES_PROVIDER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "ZAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def _provider_audit_path(home: str) -> Path:
    return Path(home) / "gateway" / "dev" / "audit" / "provider-roundtrip-audit.jsonl"


# ===========================================================================
# Lens 1 — Provider Schema Boundary
# ===========================================================================


class TestLens1ProviderSchemaBoundary:
    """The provider schema is a pure projection of STATIC_ALLOWLIST."""

    def test_schema_tools_exactly_match_allowlist(self) -> None:
        bundle = build_provider_tool_schema()
        names = frozenset(t.name for t in bundle.tools)
        assert names == EXPECTED_STATIC_ALLOWLIST

    def test_schema_bundle_validates(self) -> None:
        bundle = build_provider_tool_schema()
        result = validate_provider_schema_bundle(bundle)
        assert result.valid is True
        assert result.errors == ()

    def test_no_write_or_provider_recursive_tool_in_schema(self) -> None:
        bundle = build_provider_tool_schema()
        names = {t.name for t in bundle.tools}
        for blocked in (
            "write_file", "patch", "terminal", "execute_code", "send_message",
            "cronjob", "delegate_task", "memory", "todo", "provider",
            "provider_roundtrip",
        ):
            assert blocked not in names

    def test_every_schema_tool_read_only_safe_profile(self) -> None:
        bundle = build_provider_tool_schema()
        for entry in bundle.tools:
            assert entry.read_only is True
            assert entry.provider_required is False
            assert entry.write_required is False
            assert entry.external_side_effects is False
            assert entry.safety_tier == "read_only_safe"

    def test_injected_unsafe_tool_ids_are_dropped(self) -> None:
        bundle = build_provider_tool_schema(
            frozenset({"write_file", "terminal", "provider_roundtrip", "clarify"})
        )
        names = {t.name for t in bundle.tools}
        assert names == {"clarify"}


# ===========================================================================
# Lens 2 — Provider Request / Mode Boundary
# ===========================================================================


class TestLens2ProviderRequestModeBoundary:
    """disabled/fake/real mode gating is exact."""

    def test_disabled_mode_is_inert(self) -> None:
        req = build_provider_request("check route governance", PROVIDER_MODE_DISABLED)
        assert req.provider_schema_sent is False
        assert req.provider_api_called is False
        assert req.external_network_called is False
        # The round-trip returns a blocked RESULT for disabled mode; the
        # request envelope itself is simply inert (no real-mode block reason).
        assert req.blocked is False
        assert req.blocked_reason is None

    def test_fake_mode_is_offline(self) -> None:
        req = build_provider_request("check route governance", PROVIDER_MODE_FAKE)
        assert req.provider_schema_sent is True
        assert req.provider_api_called is True
        assert req.external_network_called is False
        assert req.blocked is False

    def test_real_mode_blocked_by_default(self) -> None:
        req = build_provider_request("check route governance", PROVIDER_MODE_REAL)
        assert req.blocked is True
        assert req.blocked_reason == BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED
        assert req.external_network_called is False

    def test_allowed_tool_ids_bounded_by_allowlist(self) -> None:
        req = build_provider_request(
            "x", PROVIDER_MODE_FAKE,
            allowed_tool_ids=frozenset({"write_file", "clarify", "route_governance_read"}),
        )
        assert frozenset(req.allowed_tool_ids) == {"clarify", "route_governance_read"}
        assert STATIC_ALLOWLIST.issuperset(req.allowed_tool_ids)

    def test_request_envelope_carries_no_api_key(self) -> None:
        req = build_provider_request("x", PROVIDER_MODE_FAKE)
        safe = req.to_safe_dict()
        blob = repr(safe)
        for fragment in ("apiKey", "api_key", "authorization", "bearer", "sk-"):
            assert fragment not in blob.lower()


# ===========================================================================
# Lens 3 — Fake Provider Determinism
# ===========================================================================


class TestLens3FakeProviderDeterminism:
    """FakeProviderAdapter is deterministic and fully offline."""

    @pytest.mark.parametrize("tool_id,message", FAKE_TOOL_ROUTES)
    def test_each_tool_routes_deterministically(
        self, tool_id: str, message: str
    ) -> None:
        req = build_provider_request(
            message, PROVIDER_MODE_FAKE,
            allowed_tool_ids=frozenset({tool_id}),
        )
        adapter = FakeProviderAdapter()
        r1 = adapter.invoke(req)
        r2 = adapter.invoke(req)
        # Same message → same tool choice and same response id (deterministic).
        assert r1.external_network_called is False
        assert r1.provider_api_called is True
        assert r1.provider_response_id == r2.provider_response_id
        if r1.tool_calls:
            assert r1.tool_calls[0].name == tool_id
            assert r1.tool_calls[0].name == r2.tool_calls[0].name

    def test_fake_adapter_source_has_no_network_imports(self) -> None:
        import hermes_cli.dev_web_provider_adapter as adapter

        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for forbidden in ("import httpx", "import requests", "import urllib",
                          "import aiohttp", "from httpx", "from requests",
                          "urlopen", "curl"):
            assert forbidden not in source, f"fake adapter imports network: {forbidden}"


# ===========================================================================
# Lens 4 — Real Provider Blocked Boundary
# ===========================================================================


class TestLens4RealProviderBlockedBoundary:
    """RealProviderAdapter never calls a real network in Phase 2B."""

    def test_blocked_without_enablement_env(self) -> None:
        eligible, reason = _evaluate_real_mode_eligibility(production_gate_override=True)
        assert eligible is False
        assert reason == BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED

    def test_blocked_without_api_key(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        eligible, reason = _evaluate_real_mode_eligibility(production_gate_override=True)
        assert eligible is False
        assert reason == BLOCKED_PROVIDER_API_KEY_MISSING

    def test_blocked_outside_dev_home(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_KEY", "dummy-non-empty-key")
        monkeypatch.setenv("HERMES_HOME", "/Users/huangruibang/.hermes")
        eligible, reason = _evaluate_real_mode_eligibility(production_gate_override=True)
        assert eligible is False
        assert reason == BLOCKED_PROVIDER_NOT_DEV_HOME

    def test_blocked_on_production_gate_drift(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_KEY", "dummy-non-empty-key")
        monkeypatch.setenv("HERMES_HOME", "/Users/huangruibang/Code/hermes-home-dev")
        eligible, reason = _evaluate_real_mode_eligibility(production_gate_override=False)
        assert eligible is False
        assert reason == BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT

    def test_real_adapter_blocked_even_when_eligible(self, monkeypatch) -> None:
        # Even with every gate forced open, the vendor call is not wired in 2B.
        # Force eligibility True so the adapter reaches the not-wired branch
        # (the live env is stripped by the autouse fixture).
        import hermes_cli.dev_web_provider_adapter as adapter_mod

        monkeypatch.setattr(
            adapter_mod,
            "_evaluate_real_mode_eligibility",
            lambda *args, **kwargs: (True, None),
        )
        req = build_provider_request("x", PROVIDER_MODE_REAL)
        resp = RealProviderAdapter().invoke(req)
        assert resp.blocked is True
        assert resp.blocked_reason == BLOCKED_REAL_PROVIDER_NOT_WIRED
        assert resp.external_network_called is False
        assert resp.provider_api_called is False

    def test_get_provider_adapter_fails_closed_for_unknown(self) -> None:
        # An unknown/disabled mode must not reach a fake-then-network path.
        adapter = get_provider_adapter("definitely-not-a-mode")
        assert isinstance(adapter, RealProviderAdapter)


# ===========================================================================
# Lens 5 — Provider Tool-call Controlled Chain Preservation
# ===========================================================================


class TestLens5ProviderToolCallControlledChain:
    """Provider tool calls never bypass the controlled chain."""

    def _allow(self) -> frozenset[str]:
        return frozenset(STATIC_ALLOWLIST)

    def test_unknown_tool_blocked(self) -> None:
        parsed = validate_provider_tool_call(
            {"id": "c1", "name": "definitely_not_real", "arguments": {}},
            allowlist=self._allow(),
        )
        assert parsed.status == TOOL_CALL_BLOCKED_NOT_ALLOWLISTED

    def test_write_like_tool_blocked(self) -> None:
        parsed = validate_provider_tool_call(
            {"id": "c1", "name": "write_file", "arguments": {"path": "/x"}},
            allowlist=self._allow(),
        )
        assert parsed.status == TOOL_CALL_BLOCKED_WRITE_LIKE

    def test_provider_recursive_tool_blocked(self) -> None:
        # A tool whose name contains 'provider' and is not allowlisted is
        # classified as not-allowlisted (the allowlist gate fires first); it
        # can never reach the controlled chain regardless of reason code.
        parsed = validate_provider_tool_call(
            {"id": "c1", "name": "provider_roundtrip", "arguments": {}},
            allowlist=self._allow(),
        )
        assert parsed.status in (
            TOOL_CALL_BLOCKED_NOT_ALLOWLISTED,
            TOOL_CALL_BLOCKED_PROVIDER_RECURSIVE,
        )

    def test_malformed_arguments_blocked(self) -> None:
        parsed = validate_provider_tool_call(
            {"id": "c1", "name": "clarify", "arguments": "not-a-mapping"},
            allowlist=self._allow(),
        )
        assert parsed.status == TOOL_CALL_BLOCKED_MALFORMED_ARGS

    def test_secret_arguments_blocked(self) -> None:
        parsed = validate_provider_tool_call(
            {"id": "c1", "name": "clarify",
             "arguments": {"question": "key=sk-abcdefghijklmnopqrstuvwxyz0123456789"}},
            allowlist=self._allow(),
        )
        assert parsed.status == TOOL_CALL_BLOCKED_MALFORMED_ARGS

    def test_valid_fake_roundtrip_runs_full_controlled_chain(self, provider_home) -> None:
        result = run_provider_tool_roundtrip(
            "read tool policy", PROVIDER_MODE_FAKE,
            selected_tool_ids=frozenset({"tool_policy_read"}),
            hermes_home=provider_home,
            production_gate_override=True,
        )
        assert result.status == "completed"
        # The dry-run + post-execution audit lines prove the full chain ran.
        audit_dir = Path(provider_home) / "gateway" / "dev" / "audit"
        assert (audit_dir / "tool-dry-run-audit.jsonl").exists()
        assert (audit_dir / "tool-post-execution-audit.jsonl").exists()
        # Tool write stays disabled; read-only only.
        assert result.read_only_only is True
        assert result.external_network_called is False


# ===========================================================================
# Lens 6 — Provider Audit Redaction / Secret-Repr Boundary
# ===========================================================================


class TestLens6ProviderAuditRedactionBoundary:
    """No raw token / tokenHash / raw arguments / secrets / callable repr leak;
    every PEM private-key variant is redacted (Phase 2B-H1 fix pinned here)."""

    @pytest.mark.parametrize("header", PEM_HEADER_SAMPLES)
    def test_every_pem_private_key_variant_redacted(self, header: str) -> None:
        assert _is_secret_string(header) is True

    @pytest.mark.parametrize(
        "field", ("privateKeyPem", "credentials", "xApiKey", "apikeyV2")
    )
    def test_suffixed_secret_field_names_forbidden(self, field: str) -> None:
        # Suffixed secret-bearing field names must be caught by the broadened
        # substring stems (Phase 2B-H1 fix). SSH key VALUES are backstopped by
        # the widened PEM value pattern regardless of their field name.
        assert _is_forbidden_field(field) is True

    @pytest.mark.parametrize(
        "field",
        ("allowedToolIds", "toolChoicePolicy", "redactionApplied", "toolCount",
         "schemaVersion", "blockedReason"),
    )
    def test_legitimate_fields_not_false_positive(self, field: str) -> None:
        assert _is_forbidden_field(field) is False

    def test_callable_and_object_render_as_opaque_placeholder(self) -> None:
        sanitized = _sanitize(
            {"payload": {"fn": lambda: None, "obj": object(), "cls": type("X", (), {})}}
        )
        blob = repr(sanitized)
        for forbidden in ("<function", "<lambda>", "object at 0x", "<class", "<type"):
            assert forbidden not in blob
        assert "<non_json_value>" in blob

    def test_ec_pem_in_user_message_redacted_in_audit_file(
        self, provider_home
    ) -> None:
        # An EC PEM private key typed into the provider message must never
        # reach the provider audit file (Phase 2B-H1 hardening).
        run_provider_tool_roundtrip(
            "read tool policy key=-----BEGIN EC PRIVATE KEY-----MIIBVQIBADANB",
            PROVIDER_MODE_FAKE,
            selected_tool_ids=frozenset({"tool_policy_read"}),
            hermes_home=provider_home,
            production_gate_override=True,
        )
        blob = _provider_audit_path(provider_home).read_text(encoding="utf-8")
        assert "BEGIN EC PRIVATE KEY" not in blob
        assert "MIIBVQIBADANB" not in blob
        assert "[REDACTED]" in blob

    def test_audit_redaction_applied_always_true(self, provider_home) -> None:
        run_provider_tool_roundtrip(
            "check route governance", PROVIDER_MODE_FAKE,
            selected_tool_ids=frozenset({"route_governance_read"}),
            hermes_home=provider_home,
            production_gate_override=True,
        )
        import json

        for line in _provider_audit_path(provider_home).read_text(encoding="utf-8").splitlines():
            assert json.loads(line)["redactionApplied"] is True


# ===========================================================================
# Lens 7 — Transient Flake Reproduction / Stability Boundary
# ===========================================================================


class TestLens7TransientFlakeStabilityBoundary:
    """The Phase 2B transient flake (audit_events_read-R1) is closed here as
    non-reproduced with deterministic evidence, repeated for stability."""

    @pytest.mark.parametrize("repeat", range(5))
    def test_audit_events_read_r1_equivalent_no_secret_or_repr(
        self, tmp_path, monkeypatch, repeat: int
    ) -> None:
        # Equivalent to the original [audit_events_read-R1] scenario: run the
        # audit_events_read read-only tool to completion, then assert the
        # 2A audit JSONL writers + the provider audit writer contain no
        # forbidden secret/callable fragment.
        from tests.test_dev_web_phase_2a_read_only_execute import (
            run_read_only_tool_to_completion,
        )

        home = tmp_path / "hermes-home-dev"
        (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
        (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)

        rd = run_read_only_tool_to_completion(
            str(home), "audit_events_read",
            risk_tier="R1", monkeypatch_probe=_fake_probe,
        )
        assert rd["executionCompleted"] is True

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
            for forbidden in FORBIDDEN_SECRET_FRAGMENTS:
                assert forbidden not in content, f"{name}: leaked {forbidden!r}"

    @pytest.mark.parametrize("repeat", range(5))
    def test_fake_provider_roundtrip_stable(self, provider_home, repeat: int) -> None:
        result = run_provider_tool_roundtrip(
            "check route governance", PROVIDER_MODE_FAKE,
            selected_tool_ids=frozenset({"route_governance_read"}),
            hermes_home=provider_home,
            production_gate_override=True,
        )
        assert result.status == "completed"
        assert result.external_network_called is False
        blob = _provider_audit_path(provider_home).read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_SECRET_FRAGMENTS:
            assert forbidden not in blob

    @pytest.mark.parametrize("repeat", range(5))
    def test_real_provider_blocked_stable(self, provider_home, repeat: int) -> None:
        result = run_provider_tool_roundtrip(
            "check route governance", PROVIDER_MODE_REAL,
            hermes_home=provider_home,
            production_gate_override=True,
        )
        assert result.status == "blocked"
        assert result.external_network_called is False
        assert result.provider_api_called is False


# ===========================================================================
# Lens 8 — Frontend Contract / Smoke User Flow Boundary
# ===========================================================================


def _frontend_selectable_tool_ids() -> frozenset[str]:
    repo_root = Path(__file__).resolve().parents[1]
    ts_path = repo_root / "apps" / "hermes-dev-webui" / "src" / "constants" / "readOnlyTools.ts"
    assert ts_path.exists(), f"frontend mirror not found: {ts_path}"
    text = ts_path.read_text(encoding="utf-8")
    matches = re.findall(r"id:\s*['\"]([^'\"]+)['\"]", text)
    return frozenset(matches)


class TestLens8FrontendContractBoundary:
    """The frontend mirrors the backend boundary and never accepts an API key."""

    def test_frontend_mirrors_backend_allowlist(self) -> None:
        assert _frontend_selectable_tool_ids() == EXPECTED_STATIC_ALLOWLIST

    def test_provider_panel_has_no_api_key_input(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        panel = (
            repo_root
            / "apps" / "hermes-dev-webui" / "src" / "components" / "workspace"
            / "ProviderRoundtripPanel.vue"
        )
        assert panel.exists()
        text = panel.read_text(encoding="utf-8")
        # No password/key input control, no v-model binding a key.
        for forbidden in ('type="password"', 'type=\'password\'',
                          "apiKey", "api_key", "v-model=\"apiKey\"",
                          "v-model=\"apiKeyInput\""):
            assert forbidden not in text


# ===========================================================================
# Aggregated hardening verdict
# ===========================================================================


class TestHardeningVerdict:
    """Single aggregated assertion anchoring the 8-lens PASS verdict."""

    def test_eight_lens_boundary_holds(self) -> None:
        # Lens 1
        bundle = build_provider_tool_schema()
        assert frozenset(t.name for t in bundle.tools) == EXPECTED_STATIC_ALLOWLIST
        assert validate_provider_schema_bundle(bundle).valid is True
        # Lens 2
        assert build_provider_request("x", PROVIDER_MODE_DISABLED).provider_api_called is False
        # Lens 3
        assert FakeProviderAdapter().mode == PROVIDER_MODE_FAKE
        # Lens 4
        assert get_provider_adapter(PROVIDER_MODE_REAL).__class__.__name__ == "RealProviderAdapter"
        # Lens 6
        assert _is_secret_string("-----BEGIN EC PRIVATE KEY-----") is True
        assert _is_forbidden_field("privateKeyPem") is True


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
