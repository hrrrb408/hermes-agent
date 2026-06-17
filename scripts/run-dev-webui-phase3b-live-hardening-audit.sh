#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 3B-Live-Enablement H1 Live Gate Hardening Audit
#
# Deterministic hardening audit for the strict manual one-shot real-provider
# live enablement gate (HARDENING-3B-LIVE-H1-001). Dev-only, repeatable.
#
# Safety guarantees:
#   - set -euo pipefail
#   - Binds nothing of its own (the smoke harness binds 127.0.0.1 only)
#   - HERMES_HOME pinned to the dev home; production home (~/.hermes) refused
#   - Never reads OPENAI_API_KEY; unsets every provider live flag
#   - Never executes the manual one-shot live profile
#   - Never starts / stops / restarts / replaces / signals the Production Gateway
#   - Verifies Production Gateway PID 28428 + count 1 + 5180/5181 free
#   - Verifies no runtime artifact / .claude is staged
#   - Non-zero exit on any failure
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEBUI_DIR="$REPO_ROOT/apps/hermes-dev-webui"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
PRODUCTION_GATEWAY_PID=28428

RESULT=0

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*" >&2; }
section() {
  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "  $*"
  echo "───────────────────────────────────────────────────────────────"
}
pass() { echo "  [PASS] $*"; }
fail() { echo "  [FAIL] $*"; RESULT=1; }

# ── 0. Pre-flight: dev home + production isolation ────────────────────────
section "Pre-flight: dev home + production isolation"

# Pin HERMES_HOME to the dev home. Refuse the production home categorically.
export HERMES_HOME="$DEV_HERMES_HOME"
if [ "$HERMES_HOME" = "$PRODUCTION_HERMES_HOME" ]; then
  error "Refusing production HERMES_HOME ($HERMES_HOME). Aborting."
  exit 1
fi
# Never read a real provider key; unset every provider live flag.
unset OPENAI_API_KEY
unset HERMES_PROVIDER_MODE HERMES_PROVIDER_API_ENABLED HERMES_PROVIDER_API_KEY
unset HERMES_PROVIDER_LIVE_APPROVAL HERMES_PROVIDER_LIVE_ONE_SHOT
unset HERMES_PROVIDER_LIVE_BUDGET_CENTS HERMES_PROVIDER_LIVE_MAX_TOTAL_TOKENS
unset HERMES_PROVIDER_LIVE_MAX_OUTPUT_TOKENS
unset XAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY

if [ ! -x "$VENV_PYTHON" ]; then
  error "Python venv not found at $VENV_PYTHON"
  exit 1
fi
info "HERMES_HOME:   $HERMES_HOME"
info "Python:        $VENV_PYTHON ($("$VENV_PYTHON" --version 2>&1))"
pass "Provider live flags unset; OPENAI_API_KEY unset; production home refused"

# ── 1. Route governance ───────────────────────────────────────────────────
section "Route governance (expect 34/34/5/0/1/1)"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_check_webui.py \
  tests/test_dev_web_0c06_closure.py \
  >/tmp/phase3b-live-h1-route-gov.$$ 2>&1 && pass "route governance tests" || {
  fail "route governance tests"
  tail -20 /tmp/phase3b-live-h1-route-gov.$$ >&2 || true
}

# ── 2. Phase 3B Live H1 backend hardening tests ───────────────────────────
section "Phase 3B Live H1 backend hardening tests"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_web_phase_3b_live_h1_approval_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_secret_gate_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_network_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_budget_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_kill_switch_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_roundtrip_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_audit_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_api_security.py \
  >/tmp/phase3b-live-h1-backend.$$ 2>&1 && pass "H1 backend hardening tests" || {
  fail "H1 backend hardening tests"
  tail -20 /tmp/phase3b-live-h1-backend.$$ >&2 || true
}

# ── 3. Phase 3B Live backend tests ────────────────────────────────────────
section "Phase 3B Live backend tests"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_web_phase_3b_live_approval.py \
  tests/test_dev_web_phase_3b_live_secret_policy.py \
  tests/test_dev_web_phase_3b_live_network_allowlist.py \
  tests/test_dev_web_phase_3b_live_budget_policy.py \
  tests/test_dev_web_phase_3b_live_audit_policy.py \
  tests/test_dev_web_phase_3b_live_kill_switch.py \
  tests/test_dev_web_phase_3b_live_roundtrip.py \
  tests/test_dev_web_phase_3b_live_api_security.py \
  >/tmp/phase3b-live-backend.$$ 2>&1 && pass "Live backend tests" || {
  fail "Live backend tests"
  tail -20 /tmp/phase3b-live-backend.$$ >&2 || true
}

# ── 4. Preservation: Phase 3B / 3B-H1 provider tests ──────────────────────
section "Preservation: Phase 3B / 3B-H1 provider tests"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_web_phase_3b_provider_adapter.py \
  tests/test_dev_web_phase_3b_provider_api_security.py \
  tests/test_dev_web_phase_3b_provider_audit.py \
  tests/test_dev_web_phase_3b_provider_config.py \
  tests/test_dev_web_phase_3b_provider_policy.py \
  tests/test_dev_web_phase_3b_provider_redaction.py \
  tests/test_dev_web_phase_3b_provider_roundtrip.py \
  tests/test_dev_web_phase_3b_provider_schema.py \
  tests/test_dev_web_phase_3b_provider_tool_allowlist.py \
  tests/test_dev_web_phase_3b_h1_provider_api_security.py \
  tests/test_dev_web_phase_3b_h1_provider_audit_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_config_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_network_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_policy_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_redaction_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_schema_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_tool_allowlist_hardening.py \
  >/tmp/phase3b-live-preserve.$$ 2>&1 && pass "preservation tests" || {
  fail "preservation tests"
  tail -20 /tmp/phase3b-live-preserve.$$ >&2 || true
}

# ── 5. Compile + ruff ─────────────────────────────────────────────────────
section "Compile + ruff"
"$VENV_PYTHON" -m compileall hermes_cli >/tmp/phase3b-live-compileall.$$ 2>&1 \
  && pass "compileall hermes_cli" || { fail "compileall hermes_cli"; tail -10 /tmp/phase3b-live-compileall.$$ >&2 || true; }
"$VENV_PYTHON" -m py_compile toolsets.py && pass "py_compile toolsets.py" || fail "py_compile toolsets.py"
ruff check \
  hermes_cli/dev_web_provider_live_approval.py \
  hermes_cli/dev_web_provider_live_secret.py \
  hermes_cli/dev_web_provider_live_network.py \
  hermes_cli/dev_web_provider_live_budget.py \
  hermes_cli/dev_web_provider_live_audit.py \
  hermes_cli/dev_web_provider_live_kill_switch.py \
  hermes_cli/dev_web_provider_live_roundtrip.py \
  hermes_cli/dev_web_api.py \
  tests/test_dev_web_phase_3b_live_h1_approval_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_secret_gate_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_network_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_budget_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_kill_switch_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_roundtrip_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_audit_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_api_security.py \
  >/tmp/phase3b-live-ruff.$$ 2>&1 && pass "ruff check (live modules + H1 tests)" || {
  fail "ruff check (live modules + H1 tests)"
  tail -20 /tmp/phase3b-live-ruff.$$ >&2 || true
}

# ── 6. Frontend gates ─────────────────────────────────────────────────────
section "Frontend gates (type-check / lint / test / build)"
(
  cd "$WEBUI_DIR"
  pnpm type-check >/tmp/phase3b-live-tc.$$ 2>&1 && pass "frontend type-check" || { fail "frontend type-check"; tail -15 /tmp/phase3b-live-tc.$$ >&2 || true; }
  pnpm lint >/tmp/phase3b-live-lint.$$ 2>&1 && pass "frontend lint" || { fail "frontend lint"; tail -15 /tmp/phase3b-live-lint.$$ >&2 || true; }
  pnpm test >/tmp/phase3b-live-ftest.$$ 2>&1 && pass "frontend unit tests" || { fail "frontend unit tests"; tail -15 /tmp/phase3b-live-ftest.$$ >&2 || true; }
  pnpm build >/tmp/phase3b-live-build.$$ 2>&1 && pass "frontend build" || { fail "frontend build"; tail -15 /tmp/phase3b-live-build.$$ >&2 || true; }
)

# ── 7. Smoke all (includes phase3b_live_h1_hardening; excludes manual one-shot)
section "Smoke all (must include phase3b_live_h1_hardening; must NOT include manual one-shot)"
SMOKE_OUT=/tmp/phase3b-live-smoke-all.$$
"$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all >"$SMOKE_OUT" 2>&1 \
  && pass "smoke all" || { fail "smoke all"; tail -25 "$SMOKE_OUT" >&2 || true; }
# Verify the manual one-shot profile is never executed by `all`.
if grep -q "phase3b_live_enablement_manual_one_shot" "$SMOKE_OUT" 2>/dev/null; then
  # Only acceptable as a comment / exclusion note, not as a run. Check it never
  # appears as a "Smoke profile:" run line.
  if grep -E "^  Smoke profile: phase3b_live_enablement_manual_one_shot" "$SMOKE_OUT" >/dev/null 2>&1; then
    fail "manual one-shot live profile was executed by all"
  else
    pass "manual one-shot live profile not executed by all"
  fi
else
  pass "manual one-shot live profile not executed by all"
fi

# ── 8. Hermes gates ───────────────────────────────────────────────────────
section "Hermes gates (memory-check / dev-check)"
"$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check >/tmp/phase3b-live-mem.$$ 2>&1 \
  && pass "memory-check" || { fail "memory-check"; tail -15 /tmp/phase3b-live-mem.$$ >&2 || true; }
"$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check >/tmp/phase3b-live-devcheck.$$ 2>&1 \
  && pass "dev-check" || { fail "dev-check"; tail -15 /tmp/phase3b-live-devcheck.$$ >&2 || true; }

# ── 9. Production safety ──────────────────────────────────────────────────
section "Production safety (PID 28428 / count 1 / ports free)"
gw_count="$(pgrep -f 'hermes_cli.main gateway run' | wc -l | tr -d ' ')"
gw_pid="$(pgrep -f 'hermes_cli.main gateway run' | head -1 || true)"
if [ "$gw_count" = "1" ] && [ "$gw_pid" = "$PRODUCTION_GATEWAY_PID" ]; then
  pass "Production Gateway PID $PRODUCTION_GATEWAY_PID (count 1, unchanged)"
else
  fail "Production Gateway PID drifted (expected $PRODUCTION_GATEWAY_PID / count 1; got '$gw_pid' / count $gw_count)"
fi
p5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
p5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
if [ -z "$p5180" ] && [ -z "$p5181" ]; then
  pass "Ports 5180 / 5181 free"
else
  fail "Ports 5180 / 5181 not free (5180='${p5180:-free}' 5181='${p5181:-free}')"
fi

# ── 10. Runtime artifact / .claude staging guard ───────────────────────────
section "Runtime artifact / .claude staging guard"
staged="$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null || true)"
if echo "$staged" | grep -Eq "(^|/)\.claude/|test-results|playwright-report|\.log$|provider-request-audit\.jsonl|provider-response-audit\.jsonl|tool-post-execution-audit\.jsonl|tool-pre-execution-audit\.jsonl|tool-dry-run-audit\.jsonl|confirmation-tokens\.jsonl|tool-confirmation-tokens|tool-write-rollback-manifests|audit-store|workflow-store|provider-live-approvals|provider-live-budget|provider-live-kill-switch|quarantine|events/|indexes/|coverage|/dist/|node_modules"; then
  fail "runtime artifact or .claude appears staged"
else
  pass "no runtime artifact or .claude staged"
fi

# Cleanup tmp logs
rm -f /tmp/phase3b-live-*.$$ 2>/dev/null || true

# ── 11. Overall ───────────────────────────────────────────────────────────
section "Overall"
if [ "$RESULT" -eq 0 ]; then
  echo "  Overall: PASS"
else
  echo "  Overall: FAIL"
fi
exit "$RESULT"
