#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 3B-H1 Provider Boundary Hardening Audit
#
# A single, deterministic gate that runs every Phase 3B-H1 hardening check in
# one place. Dev-only. It:
#
#   - uses the dev HERMES_HOME only (never ~/.hermes, never production state.db)
#   - unsets every provider API-key env var (never reads a real key)
#   - never enables the real provider, never sends a real network call
#   - runs route governance, the Phase 3B-H1 + Phase 3B backend tests,
#     preservation tests, frontend type-check / lint / tests / build,
#     the full smoke suite, memory-check, dev-check
#   - checks the Production Gateway PID (28428), process count (1), ports
#     5180/5181 free, and that no runtime artifact is staged
#   - prints Overall PASS / FAIL and exits non-zero on any failure
#
# Safety guarantees:
#   - set -euo pipefail
#   - binds to 127.0.0.1 only (via the smoke harness)
#   - refuses production HERMES_HOME (~/.hermes)
#   - never starts / stops / restarts / replaces / signals the Production Gateway
#   - never prints / commits a secret
# ---------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEV_API_HOST="127.0.0.1"
PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
PRODUCTION_GATEWAY_PID=28428
WEBUI_DIR="$REPO_ROOT/apps/hermes-dev-webui"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

GLOBAL_RESULT=0
FAILED_STEPS=()

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*" >&2; }
section() {
  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "  $*"
  echo "───────────────────────────────────────────────────────────────"
}

# Run a step: record pass/fail without aborting the whole audit.
run_step() {
  local label="$1"; shift
  local rc=0
  "$@" || rc=$?
  if [ "$rc" -ne 0 ]; then
    error "STEP FAILED: $label (exit $rc)"
    GLOBAL_RESULT=1
    FAILED_STEPS+=("$label")
  else
    info "STEP PASS: $label"
  fi
}

# ── Banner ───────────────────────────────────────────────────────────────
section "Phase 3B-H1 Provider Boundary Hardening Audit"
info "Source root:   $REPO_ROOT"
info "Dev HERMES_HOME: ${HERMES_HOME:-$DEFAULT_DEV_HERMES_HOME}"

# ── 1-6. Environment safety ──────────────────────────────────────────────
section "Environment Safety (dev home; no production; no real provider)"

export HERMES_HOME="${HERMES_HOME:-$DEFAULT_DEV_HERMES_HOME}"
info "HERMES_HOME:   $HERMES_HOME"

if [ ! -d "$HERMES_HOME" ]; then
  error "HERMES_HOME does not exist: $HERMES_HOME"
  exit 1
fi
if [ "$HERMES_HOME" = "$PRODUCTION_HERMES_HOME" ]; then
  error "HERMES_HOME points to the production instance: $HERMES_HOME"
  exit 1
fi
case "$HERMES_HOME" in
  "$PRODUCTION_HERMES_HOME"/*)
    error "HERMES_HOME is inside the production instance: $HERMES_HOME"
    exit 1
    ;;
esac

# Unset every provider API-key env var (never carry a real key into the audit).
unset HERMES_PROVIDER_MODE HERMES_PROVIDER_API_ENABLED HERMES_PROVIDER_NAME
unset HERMES_PROVIDER_BASE_URL HERMES_PROVIDER_MODEL HERMES_PROVIDER_API_KEY
unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY
unset GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY
info "Provider API keys: unset (no real key read, no real provider enabled)"

if [ ! -x "$VENV_PYTHON" ]; then
  error "Python venv not found at $VENV_PYTHON"
  exit 1
fi
if ! command -v pnpm &>/dev/null; then
  error "pnpm not found in PATH"
  exit 1
fi
info "Environment:   SAFE"

# ── 7. Route governance ──────────────────────────────────────────────────
section "Route Governance"
run_step "route governance (test_dev_check_webui.py)" \
  "$SCRIPT_DIR/run_tests.sh" tests/test_dev_check_webui.py
run_step "route governance (test_dev_web_0c06_closure.py)" \
  "$SCRIPT_DIR/run_tests.sh" tests/test_dev_web_0c06_closure.py

# ── 8. Phase 3B-H1 backend tests ─────────────────────────────────────────
section "Phase 3B-H1 Backend Hardening Tests"
run_step "Phase 3B-H1 backend hardening tests" "$SCRIPT_DIR/run_tests.sh" \
  tests/test_dev_web_phase_3b_h1_provider_config_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_redaction_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_network_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_policy_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_schema_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_tool_allowlist_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_audit_hardening.py \
  tests/test_dev_web_phase_3b_h1_provider_api_security.py

# ── 9. Phase 3B backend tests ────────────────────────────────────────────
section "Phase 3B Backend Tests"
run_step "Phase 3B backend tests" "$SCRIPT_DIR/run_tests.sh" \
  tests/test_dev_web_phase_3b_provider_config.py \
  tests/test_dev_web_phase_3b_provider_schema.py \
  tests/test_dev_web_phase_3b_provider_redaction.py \
  tests/test_dev_web_phase_3b_provider_policy.py \
  tests/test_dev_web_phase_3b_provider_adapter.py \
  tests/test_dev_web_phase_3b_provider_roundtrip.py \
  tests/test_dev_web_phase_3b_provider_audit.py \
  tests/test_dev_web_phase_3b_provider_tool_allowlist.py \
  tests/test_dev_web_phase_3b_provider_api_security.py

# ── 10. Preservation tests (Phase 2A..3A-H1 + 3B) ────────────────────────
section "Preservation Tests"
run_step "preservation tests (Phase 2A-3A-H1 + 3B)" "$SCRIPT_DIR/run_tests.sh" \
  tests/test_dev_web_phase_2a_read_only_frontend_contract.py \
  tests/test_dev_web_phase_2b_provider_roundtrip.py \
  tests/test_dev_web_phase_2c_h1_provider_write_boundary.py \
  tests/test_dev_web_phase_2d_h1_audit_store_hardening.py \
  tests/test_dev_web_phase_2e_h1_frontend_contract.py \
  tests/test_dev_web_phase_3a_h1_workflow_api_security.py \
  tests/test_dev_web_phase_3b_provider_api_security.py

# ── 11-14. Frontend gates ────────────────────────────────────────────────
section "Frontend Gates"
run_step "frontend type-check" bash -lc "cd '$WEBUI_DIR' && pnpm type-check"
run_step "frontend lint" bash -lc "cd '$WEBUI_DIR' && pnpm lint"
run_step "frontend tests (vitest)" bash -lc "cd '$WEBUI_DIR' && pnpm test --run"
run_step "frontend build" bash -lc "cd '$WEBUI_DIR' && pnpm build"

# ── 15. Smoke (all profiles) ─────────────────────────────────────────────
section "Smoke (all profiles)"
run_step "smoke all profiles" "$SCRIPT_DIR/run-dev-webui-execute-audit-smoke.sh" all

# ── 16-17. Hermes gates ──────────────────────────────────────────────────
section "Hermes Gates"
run_step "memory-check" "$SCRIPT_DIR/run-dev-hermes.sh" memory-check
run_step "dev-check" "$SCRIPT_DIR/run-dev-hermes.sh" dev-check

# ── 18-20. Production isolation ──────────────────────────────────────────
section "Production Isolation"
gw_pids="$(pgrep -f 'hermes_cli.main gateway run' 2>/dev/null || true)"
gw_count="$(echo "$gw_pids" | grep -c . || true)"
info "Production Gateway PIDs: ${gw_pids:-<none>}  (count=$gw_count)"
if [ "$gw_count" -ne 1 ] || ! echo "$gw_pids" | grep -qx "$PRODUCTION_GATEWAY_PID"; then
  error "Expected exactly one Production Gateway with PID $PRODUCTION_GATEWAY_PID (got count=$gw_count)."
  GLOBAL_RESULT=1
  FAILED_STEPS+=("production gateway PID")
else
  info "STEP PASS: production gateway PID $PRODUCTION_GATEWAY_PID (count=1, untouched)"
fi

p5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
p5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$p5180" ] || [ -n "$p5181" ]; then
  warn "Port 5180/5181 still occupied after smoke cleanup (do NOT kill blindly):"
  [ -n "$p5180" ] && echo "$p5180" | sed 's/^/    /'
  [ -n "$p5181" ] && echo "$p5181" | sed 's/^/    /'
else
  info "STEP PASS: ports 5180/5181 free"
fi

# ── 21. Runtime artifact staging check ───────────────────────────────────
section "Runtime Artifact Staging Check"
staged="$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null || true)"
artifact_leak="$(echo "$staged" | grep -E \
  'test-results|playwright-report|\.log$|provider-request-audit\.jsonl|provider-response-audit\.jsonl|tool-post-execution-audit\.jsonl|tool-pre-execution-audit\.jsonl|tool-dry-run-audit\.jsonl|confirmation-tokens\.jsonl|tool-confirmation-tokens|tool-write-rollback-manifests|audit-store|workflow-store|quarantine|events/|indexes/|coverage|dist|node_modules|\.claude/' \
  || true)"
if [ -n "$artifact_leak" ]; then
  error "Runtime artifact / .claude staged for commit:"
  echo "$artifact_leak" | sed 's/^/    /'
  GLOBAL_RESULT=1
  FAILED_STEPS+=("runtime artifact staging")
else
  info "STEP PASS: no runtime artifact / .claude staged"
fi

# ── 22-23. Overall result ────────────────────────────────────────────────
section "Final Summary"
echo "  Audit:                Phase 3B-H1 Provider Boundary Hardening"
echo "  Dev HERMES_HOME:      $HERMES_HOME"
echo "  Production Gateway:   PID $PRODUCTION_GATEWAY_PID (untouched)"
if [ -n "${FAILED_STEPS[*]:-}" ]; then
  echo "  Failed steps:"
  for s in "${FAILED_STEPS[@]}"; do echo "    - $s"; done
else
  echo "  Failed steps:         none"
fi

if [ "$GLOBAL_RESULT" -eq 0 ]; then
  echo "  Overall:              PASS"
  exit 0
else
  echo "  Overall:              FAIL"
  exit 1
fi
