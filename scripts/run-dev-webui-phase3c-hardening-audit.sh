#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 3C-H1 Capability Registry Hardening Audit
#
# Deterministic hardening audit for the static dev-only Capability Registry
# (HARDENING-3C-H1-001). Dev-only, repeatable.
#
# Safety guarantees:
#   - set -euo pipefail
#   - Binds nothing of its own (the smoke harness binds 127.0.0.1 only)
#   - HERMES_HOME pinned to the dev home; production home (~/.hermes) refused
#   - Never reads OPENAI_API_KEY; unsets every provider live flag + API key
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
# Never read a real provider key; unset every provider live flag + API key.
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
unset OPENROUTER_API_KEY XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
unset HERMES_PROVIDER_MODE HERMES_PROVIDER_API_ENABLED HERMES_PROVIDER_API_KEY
unset HERMES_PROVIDER_LIVE_APPROVAL HERMES_PROVIDER_LIVE_ONE_SHOT
unset HERMES_PROVIDER_LIVE_BUDGET_CENTS HERMES_PROVIDER_LIVE_MAX_TOTAL_TOKENS
unset HERMES_PROVIDER_LIVE_MAX_OUTPUT_TOKENS
unset HERMES_AGENT_RUN_ENABLED HERMES_AGENT_TOOLS_ENABLED

if [ ! -x "$VENV_PYTHON" ]; then
  error "Python venv not found at $VENV_PYTHON"
  exit 1
fi
info "HERMES_HOME:   $HERMES_HOME"
info "Python:        $VENV_PYTHON ($("$VENV_PYTHON" --version 2>&1))"
pass "Provider live flags + API keys unset; production home refused"

# ── 1. Route governance (expect 34/34/5/0/1/1) ────────────────────────────
section "Route governance (expect 34/34/5/0/1/1)"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_check_webui.py \
  tests/test_dev_web_0c06_closure.py \
  >/tmp/phase3c-h1-route-gov.$$ 2>&1 && pass "route governance tests" || {
  fail "route governance tests"
  tail -20 /tmp/phase3c-h1-route-gov.$$ >&2 || true
}

# ── 2. Phase 3C-H1 backend hardening tests ────────────────────────────────
section "Phase 3C-H1 backend hardening tests"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_web_phase_3c_h1_manifest_consistency.py \
  tests/test_dev_web_phase_3c_h1_forbidden_fields.py \
  tests/test_dev_web_phase_3c_h1_permission_non_grant.py \
  tests/test_dev_web_phase_3c_h1_permission_trust_coherence.py \
  tests/test_dev_web_phase_3c_h1_tool_provider_workflow_mapping.py \
  tests/test_dev_web_phase_3c_h1_no_dynamic_loading.py \
  tests/test_dev_web_phase_3c_h1_audit_no_leak.py \
  tests/test_dev_web_phase_3c_h1_status_api_security.py \
  >/tmp/phase3c-h1-backend.$$ 2>&1 && pass "Phase 3C-H1 backend hardening tests" || {
  fail "Phase 3C-H1 backend hardening tests"
  tail -25 /tmp/phase3c-h1-backend.$$ >&2 || true
}

# ── 3. Phase 3C backend tests (preservation) ──────────────────────────────
section "Phase 3C backend tests (preservation)"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_web_phase_3c_capability_schema.py \
  tests/test_dev_web_phase_3c_capability_manifest.py \
  tests/test_dev_web_phase_3c_capability_validation.py \
  tests/test_dev_web_phase_3c_capability_policy.py \
  tests/test_dev_web_phase_3c_capability_status_api.py \
  tests/test_dev_web_phase_3c_capability_audit.py \
  tests/test_dev_web_phase_3c_capability_no_dynamic_loading.py \
  tests/test_dev_web_phase_3c_capability_security.py \
  >/tmp/phase3c-h1-3c-backend.$$ 2>&1 && pass "Phase 3C backend tests" || {
  fail "Phase 3C backend tests"
  tail -25 /tmp/phase3c-h1-3c-backend.$$ >&2 || true
}

# ── 4. Preservation: Phase 2A / 2B / 2C / 2D / 2E / 3A / 3A-H1 / 3B / 3B-H1 / Live ──
section "Preservation: Phase 2A–2E / 3A / 3A-H1 / 3B / 3B-H1 / Live / Live-H1"
"$REPO_ROOT/scripts/run_tests.sh" \
  tests/test_dev_web_phase_2a_hardening_boundaries.py \
  tests/test_dev_web_phase_2a_security_boundaries.py \
  tests/test_dev_web_phase_2b_hardening_boundaries.py \
  tests/test_dev_web_phase_2b_provider_security.py \
  tests/test_dev_web_phase_2c_h1_write_hardening.py \
  tests/test_dev_web_phase_2c_h1_rollback_execute.py \
  tests/test_dev_web_phase_2c_write_security.py \
  tests/test_dev_web_phase_2d_audit_security.py \
  tests/test_dev_web_phase_2d_h1_audit_security.py \
  tests/test_dev_web_phase_2e_h1_frontend_contract.py \
  tests/test_dev_web_phase_3a_workflow_security.py \
  tests/test_dev_web_phase_3a_h1_workflow_approval_hardening.py \
  tests/test_dev_web_phase_3a_h1_workflow_store_hardening.py \
  tests/test_dev_web_phase_3b_provider_api_security.py \
  tests/test_dev_web_phase_3b_h1_provider_boundary_hardening.py \
  tests/test_dev_web_phase_3b_live_secret_policy.py \
  tests/test_dev_web_phase_3b_live_h1_roundtrip_hardening.py \
  tests/test_dev_web_phase_3b_live_h1_secret_gate_hardening.py \
  >/tmp/phase3c-h1-preserve.$$ 2>&1 && pass "preservation tests" || {
  fail "preservation tests"
  tail -25 /tmp/phase3c-h1-preserve.$$ >&2 || true
}

# ── 5. Compile + ruff ─────────────────────────────────────────────────────
section "Compile + ruff"
"$VENV_PYTHON" -m compileall hermes_cli >/tmp/phase3c-h1-compileall.$$ 2>&1 \
  && pass "compileall hermes_cli" || { fail "compileall hermes_cli"; tail -10 /tmp/phase3c-h1-compileall.$$ >&2 || true; }
"$VENV_PYTHON" -m py_compile toolsets.py && pass "py_compile toolsets.py" || fail "py_compile toolsets.py"
ruff check \
  hermes_cli/dev_web_capability_registry_schema.py \
  hermes_cli/dev_web_capability_registry_manifest.py \
  hermes_cli/dev_web_capability_registry.py \
  hermes_cli/dev_web_capability_registry_policy.py \
  hermes_cli/dev_web_capability_registry_audit.py \
  hermes_cli/dev_web_api.py \
  tests/test_dev_web_phase_3c_h1_manifest_consistency.py \
  tests/test_dev_web_phase_3c_h1_forbidden_fields.py \
  tests/test_dev_web_phase_3c_h1_permission_non_grant.py \
  tests/test_dev_web_phase_3c_h1_permission_trust_coherence.py \
  tests/test_dev_web_phase_3c_h1_tool_provider_workflow_mapping.py \
  tests/test_dev_web_phase_3c_h1_no_dynamic_loading.py \
  tests/test_dev_web_phase_3c_h1_audit_no_leak.py \
  tests/test_dev_web_phase_3c_h1_status_api_security.py \
  >/tmp/phase3c-h1-ruff.$$ 2>&1 && pass "ruff check (capability modules + H1 tests)" || {
  fail "ruff check (capability modules + H1 tests)"
  tail -20 /tmp/phase3c-h1-ruff.$$ >&2 || true
}

# ── 6. Frontend gates ─────────────────────────────────────────────────────
section "Frontend gates (type-check / lint / test / build)"
(
  cd "$WEBUI_DIR"
  pnpm type-check >/tmp/phase3c-h1-tc.$$ 2>&1 && pass "frontend type-check" || { fail "frontend type-check"; tail -15 /tmp/phase3c-h1-tc.$$ >&2 || true; }
  pnpm lint >/tmp/phase3c-h1-lint.$$ 2>&1 && pass "frontend lint" || { fail "frontend lint"; tail -15 /tmp/phase3c-h1-lint.$$ >&2 || true; }
  pnpm test >/tmp/phase3c-h1-ftest.$$ 2>&1 && pass "frontend unit tests" || { fail "frontend unit tests"; tail -15 /tmp/phase3c-h1-ftest.$$ >&2 || true; }
  pnpm build >/tmp/phase3c-h1-build.$$ 2>&1 && pass "frontend build" || { fail "frontend build"; tail -15 /tmp/phase3c-h1-build.$$ >&2 || true; }
)

# ── 7. Smoke all (must include phase3c_h1; must NOT include manual live / dynamic / remote / marketplace) ──
section "Smoke all (must include phase3c_h1_capability_registry_hardening; must NOT run manual live / dynamic plugin / remote registry / marketplace)"
SMOKE_OUT=/tmp/phase3c-h1-smoke-all.$$
"$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all >"$SMOKE_OUT" 2>&1 \
  && pass "smoke all" || { fail "smoke all"; tail -25 "$SMOKE_OUT" >&2 || true; }
# Verify the H1 hardening profile ran.
if grep -E "^  Smoke profile: phase3c_h1_capability_registry_hardening" "$SMOKE_OUT" >/dev/null 2>&1; then
  pass "phase3c_h1_capability_registry_hardening ran in all"
else
  fail "phase3c_h1_capability_registry_hardening did NOT run in all"
fi
# Verify the manual one-shot / dynamic / remote / marketplace profiles never run.
for forbidden_profile in \
  "phase3b_live_enablement_manual_one_shot" \
  "phase3c_h1_capability_registry_hardening_dynamic" \
  "remote_registry" \
  "marketplace"; do
  if grep -E "^  Smoke profile: ${forbidden_profile}" "$SMOKE_OUT" >/dev/null 2>&1; then
    fail "forbidden profile ran in all: ${forbidden_profile}"
  fi
done
pass "no manual-live / dynamic / remote-registry / marketplace profile ran in all"

# ── 8. Hermes gates ───────────────────────────────────────────────────────
section "Hermes gates (memory-check / dev-check)"
"$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check >/tmp/phase3c-h1-mem.$$ 2>&1 \
  && pass "memory-check" || { fail "memory-check"; tail -15 /tmp/phase3c-h1-mem.$$ >&2 || true; }
"$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check >/tmp/phase3c-h1-devcheck.$$ 2>&1 \
  && pass "dev-check" || { fail "dev-check"; tail -15 /tmp/phase3c-h1-devcheck.$$ >&2 || true; }

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
if echo "$staged" | grep -Eq "(^|/)\.claude/|test-results|playwright-report|\.log$|provider-request-audit\.jsonl|provider-response-audit\.jsonl|tool-post-execution-audit\.jsonl|tool-pre-execution-audit\.jsonl|tool-dry-run-audit\.jsonl|confirmation-tokens\.jsonl|tool-confirmation-tokens|tool-write-rollback-manifests|audit-store|workflow-store|provider-live-approvals|provider-live-budget|provider-live-kill-switch|capability-registry-store|quarantine|events/|indexes/|coverage|/dist/|node_modules"; then
  fail "runtime artifact or .claude appears staged"
else
  pass "no runtime artifact or .claude staged"
fi

# Cleanup tmp logs
rm -f /tmp/phase3c-h1-*.$$ 2>/dev/null || true

# ── 11. Overall ───────────────────────────────────────────────────────────
section "Overall"
if [ "$RESULT" -eq 0 ]; then
  echo "  Overall: PASS"
else
  echo "  Overall: FAIL"
fi
exit "$RESULT"
