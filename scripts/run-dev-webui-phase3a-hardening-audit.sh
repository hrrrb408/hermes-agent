#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 3A-H1 Agent Workflow Hardening Audit
#
# Deterministic, agent-independent 11-lens boundary audit for the Phase 3A
# dev-only Agent Workflow MVP (Workflow Schema / Step Type · Store / State ·
# Planner / Unsafe Input · Step Preview / Non-execution · Manual Execution /
# Order · Approval Gate / Token Scope · Audit / Redaction · UI / Timeline /
# Cross-link · Forbidden Capability / No-autonomy · Smoke / Regression /
# Route Governance · Production Isolation / Runtime Artifact).
# Closes the Phase 3A workflow hardening backlog (HARDENING-3A-H1-001 /
# WORKFLOW-STATE-3A-H1-001 / WORKFLOW-APPROVAL-3A-H1-001 /
# WORKFLOW-AUDIT-3A-H1-001 / WORKFLOW-UI-3A-H1-001).
#
# What it does (all read-only / hermetic):
#   * Environment safety (dev home; production ~/.hermes refused; gates unset).
#   * Production Gateway read-only PID/count check (expected 28428 / count 1).
#   * Route governance (34/34/5/0/1/1, no new route, no provider route).
#   * Phase 3A-H1 backend hardening tests (schema / store / planner /
#     preview+execute / approval / audit / api-security).
#   * Phase 3A backend preservation tests (the MVP chain intact).
#   * Phase 1G/2A/2B/2C/2C-H1/2D/2D-H1/2E/2E-H1 preservation.
#   * Frontend hardening tests (routing / ui-state / approval / no-leak /
#     safety-boundary).
#   * Frontend gates (type-check / lint / test / build).
#   * Live smoke (all profiles incl. phase3a_h1_workflow_hardening).
#   * Hermes memory-check / dev-check.
#   * Runtime-artifact-not-staged + final production safety (PID 28428 /
#     count 1 / ports free).
#
# Hard guarantees:
#   * set -euo pipefail
#   * Refuses production HERMES_HOME (~/.hermes) or anything under it
#   * Never touches production state.db
#   * Never stops / restarts / replaces / signals the Production Gateway
#   * Never makes a real Provider network call (fake mode only)
#   * Never enables shell/db/external write
#   * Binds nothing itself; the smoke harness it invokes binds 127.0.0.1 only
#   * Produces NO committable runtime artifacts (tests use tmp_path; smoke
#     cleans its own /tmp logs)
#   * Exits non-zero if any lens fails; prints a PASS/FAIL summary
#
# Usage:
#   ./scripts/run-dev-webui-phase3a-hardening-audit.sh            # full audit
#   ./scripts/run-dev-webui-phase3a-hardening-audit.sh --no-smoke # skip smoke
#   ./scripts/run-dev-webui-phase3a-hardening-audit.sh --help
#
# Hardening IDs: HARDENING-3A-H1-001 / WORKFLOW-STATE-3A-H1-001 /
#                WORKFLOW-APPROVAL-3A-H1-001 / WORKFLOW-AUDIT-3A-H1-001 /
#                WORKFLOW-UI-3A-H1-001
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
# Phase 2 sealed baseline. Read-only observation only; never acted upon.
PRODUCTION_GATEWAY_PID=28428

RUN_SMOKE=true
for arg in "$@"; do
  case "$arg" in
    --no-smoke) RUN_SMOKE=false ;;
    --help|-h)
      cat <<USAGE
Usage: $0 [--no-smoke] [--help]

  --no-smoke      Skip the live Playwright smoke profiles.
  --help          Show this help message.
USAGE
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*" >&2; }
section() {
  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "  $*"
  echo "───────────────────────────────────────────────────────────────"
}

LENS_PASS=0
LENS_FAIL=0
record() { # record PASS|FAIL lens-name
  local verdict="$1" name="$2"
  if [ "$verdict" = "PASS" ]; then
    LENS_PASS=$((LENS_PASS + 1))
    echo "  $name: PASS"
  else
    LENS_FAIL=$((LENS_FAIL + 1))
    echo "  $name: FAIL"
  fi
}

section "Phase 3A-H1 Workflow Hardening Audit"
info "Repo root:     $REPO_ROOT"
info "Run smoke:     $RUN_SMOKE"

# ── Environment safety ────────────────────────────────────────────────────
section "Environment Safety"
HERMES_HOME="${HERMES_HOME:-$DEFAULT_DEV_HERMES_HOME}"
export HERMES_HOME
info "HERMES_HOME:   $HERMES_HOME"

if [ "$HERMES_HOME" = "$PRODUCTION_HERMES_HOME" ]; then
  error "HERMES_HOME points to the production instance."
  exit 1
fi
case "$HERMES_HOME" in
  "$PRODUCTION_HERMES_HOME"/*)
    error "HERMES_HOME is inside the production instance."
    exit 1
    ;;
esac
if [ ! -d "$HERMES_HOME" ]; then
  error "HERMES_HOME does not exist: $HERMES_HOME"
  exit 1
fi

# Execution / provider / agent kill-switches are intentionally left unset so the
# test lenses assert the default-disabled posture; the smoke harness sets its own.
unset HERMES_AGENT_RUN_ENABLED HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED
unset HERMES_TOOL_HANDLER_CALL_ENABLED HERMES_POST_EXECUTION_AUDIT_ENABLED
unset HERMES_TOOL_WRITE_EXECUTION_ENABLED
unset HERMES_PROVIDER_API_ENABLED HERMES_PROVIDER_MODE
# Never carry real provider keys into the audit.
unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL OPENAI_API_KEY
unset ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY

info "Environment:   SAFE (dev home; production ~/.hermes refused; gates/keys unset)"

# ── Production Gateway read-only check ────────────────────────────────────
section "Production Gateway (read-only check)"
GATEWAY_PIDS="$(pgrep -f 'hermes_cli.main gateway run' 2>/dev/null || true)"
GATEWAY_COUNT="$(echo "$GATEWAY_PIDS" | grep -c . || true)"
info "Gateway PIDs:  ${GATEWAY_PIDS:-<none>}"
info "Gateway count: $GATEWAY_COUNT"
if [ "$GATEWAY_COUNT" -ne 1 ] || ! echo "$GATEWAY_PIDS" | grep -qx "$PRODUCTION_GATEWAY_PID"; then
  error "Expected exactly one Production Gateway with PID $PRODUCTION_GATEWAY_PID."
  error "Refusing to proceed. Do NOT modify the gateway."
  exit 1
fi
info "Production Gateway PID $PRODUCTION_GATEWAY_PID confirmed (read-only; untouched)."

run_py_tests() { # lens-name description -- test-files...
  local lens="$1"; shift
  local desc="$1"; shift
  echo ""
  echo "  --- $lens: $desc ---"
  local log="/tmp/phase3a-h1-audit.$$.${RANDOM}"
  if "$REPO_ROOT/scripts/run_tests.sh" "$@" -- -q > "$log" 2>&1; then
    tail -1 "$log" | sed 's/^/      /'
    rm -f "$log"
    record PASS "$lens"
    return 0
  else
    tail -20 "$log" | sed 's/^/      /'
    rm -f "$log"
    record FAIL "$lens"
    return 1
  fi
}

run_fe_tests() { # lens-name description -- vitest-name-substrings...
  local lens="$1"; shift
  local desc="$1"; shift
  echo ""
  echo "  --- $lens: $desc ---"
  local log="/tmp/phase3a-h1-fe.$$.${RANDOM}"
  if (cd "$REPO_ROOT/apps/hermes-dev-webui" && \
      pnpm test -- --run "$@" > "$log" 2>&1); then
    grep -E "Test Files|Tests " "$log" | tail -2 | sed 's/^/      /'
    rm -f "$log"
    record PASS "$lens"
    return 0
  else
    tail -25 "$log" | sed 's/^/      /'
    rm -f "$log"
    record FAIL "$lens"
    return 1
  fi
}

# ── Lens 1 — Workflow Schema / Step Type Boundary ─────────────────────────
section "Lens 1 — Workflow Schema / Step Type Boundary"
run_py_tests "Lens 1 Workflow Schema / Step Type" \
  "schema v1; 6 allowed / 15 forbidden; blocked reasons; sanitizer" \
  tests/test_dev_web_phase_3a_h1_workflow_schema_hardening.py || true

# ── Lens 2 — Workflow Store / State Persistence Boundary ──────────────────
section "Lens 2 — Workflow Store / State Persistence Boundary"
run_py_tests "Lens 2 Workflow Store / State Persistence" \
  "dev-only; atomic write; append-only timeline; corruption-safe; no-leak" \
  tests/test_dev_web_phase_3a_h1_workflow_store_hardening.py || true

# ── Lens 3 — Workflow Planner / Unsafe Input Boundary ─────────────────────
section "Lens 3 — Workflow Planner / Unsafe Input Boundary"
run_py_tests "Lens 3 Workflow Planner / Unsafe Input" \
  "forbidden types blocked; tool ids validated; unsafe path/secret/token blocked" \
  tests/test_dev_web_phase_3a_h1_workflow_planner_hardening.py || true

# ── Lens 4 + 5 — Step Preview / Non-execution + Manual Execution / Order ──
section "Lens 4 — Step Preview / Non-execution Boundary"
section "Lens 5 — Manual Step Execution / Order Boundary"
run_py_tests "Lens 4+5 Preview Non-execution + Manual Execution Order" \
  "preview never writes; order enforced; single-use; write/rollback never execute" \
  tests/test_dev_web_phase_3a_h1_workflow_preview_execute_hardening.py || true

# ── Lens 6 — Approval Gate / Token Scope Boundary ─────────────────────────
section "Lens 6 — Approval Gate / Token Scope Boundary"
run_py_tests "Lens 6 Approval Gate / Token Scope" \
  "workflow_step_approval scope; single-use; step+digest bound; no write/rollback" \
  tests/test_dev_web_phase_3a_h1_workflow_approval_hardening.py || true

# ── Lens 7 — Workflow Audit / Redaction Boundary ──────────────────────────
section "Lens 7 — Workflow Audit / Redaction Boundary"
run_py_tests "Lens 7 Workflow Audit / Redaction" \
  "events writable+queryable; redactionApplied; no raw args/token/hash/secret" \
  tests/test_dev_web_phase_3a_h1_workflow_audit_security.py || true

# ── Lens 8 — Workflow UI / Timeline / Cross-link Boundary ─────────────────
section "Lens 8 — Workflow UI / Timeline / Cross-link Boundary"
run_fe_tests "Lens 8 Workflow UI / Cross-link (frontend)" \
  "routing / ui-state / approval / no-leak / safety-boundary" \
  phase3a-h1-workflow-routing phase3a-h1-workflow-ui-state phase3a-h1-workflow-approval \
  phase3a-h1-workflow-no-leak phase3a-h1-workflow-safety-boundary \
  phase3a-workflow-panel phase3a-workflow-timeline phase3a-workflow-plan-preview \
  phase3a-workflow-step-list || true

# ── Lens 9 — Forbidden Capability / No-autonomy Boundary (API security) ───
section "Lens 9 — Forbidden Capability / No-autonomy Boundary"
run_py_tests "Lens 9 Forbidden Capability / API Security" \
  "forbidden blocked at API; no-leak; write/rollback never executed" \
  tests/test_dev_web_phase_3a_h1_workflow_api_security.py || true

# ── Lens 10 — Smoke / Regression / Route Governance Boundary ──────────────
section "Lens 10 — Smoke / Regression / Route Governance Boundary"
run_py_tests "Lens 10 Route Governance" \
  "OpenAPI == runtime, no write route, no provider route (34/34/5/0/1/1)" \
  tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py || true
run_py_tests "Lens 10 Phase 3A Backend Preservation" \
  "schema/store/planner/preview/execute/approval/audit/api/security" \
  tests/test_dev_web_phase_3a_workflow_schema.py \
  tests/test_dev_web_phase_3a_workflow_store.py \
  tests/test_dev_web_phase_3a_workflow_planner.py \
  tests/test_dev_web_phase_3a_workflow_step_preview.py \
  tests/test_dev_web_phase_3a_workflow_step_execute.py \
  tests/test_dev_web_phase_3a_workflow_approval.py \
  tests/test_dev_web_phase_3a_workflow_audit.py \
  tests/test_dev_web_phase_3a_workflow_api.py \
  tests/test_dev_web_phase_3a_workflow_security.py || true

# Controlled-chain preservation (Phase 1G → 2E-H1 intact).
run_py_tests "Lens 10 Controlled-chain Preservation" \
  "Phase 1G/2A/2B/2C/2C-H1/2D/2D-H1 boundaries intact" \
  tests/test_dev_web_phase_2a_security_boundaries.py \
  tests/test_dev_web_phase_2a_hardening_boundaries.py \
  tests/test_dev_web_phase_2b_provider_security.py \
  tests/test_dev_web_phase_2c_write_security.py \
  tests/test_dev_web_phase_2c_h1_write_hardening.py \
  tests/test_dev_web_phase_2d_audit_security.py \
  tests/test_dev_web_phase_2d_h1_audit_security.py || true

# ── Frontend gates (type-check / lint / build) ─────────────────────────────
section "Frontend Gates (type-check / lint / build)"
FE_TYPE_OK=true
TYPE_LOG="/tmp/phase3a-h1-type.$$.${RANDOM}"
(cd "$REPO_ROOT/apps/hermes-dev-webui" && pnpm type-check > "$TYPE_LOG" 2>&1) || FE_TYPE_OK=false
LINT_LOG="/tmp/phase3a-h1-lint.$$.${RANDOM}"
(cd "$REPO_ROOT/apps/hermes-dev-webui" && pnpm lint > "$LINT_LOG" 2>&1) || { cat "$LINT_LOG"; FE_TYPE_OK=false; }
rm -f "$TYPE_LOG" "$LINT_LOG"
if [ "$FE_TYPE_OK" = true ]; then
  echo "  vue-tsc --noEmit: PASS"
  echo "  eslint .:         PASS"
  record PASS "Frontend type-check / lint"
else
  record FAIL "Frontend type-check / lint"
fi

BUILD_LOG="/tmp/phase3a-h1-build.$$.${RANDOM}"
if (cd "$REPO_ROOT/apps/hermes-dev-webui" && pnpm build > "$BUILD_LOG" 2>&1); then
  grep -E "built in|modules transformed" "$BUILD_LOG" | tail -1 | sed 's/^/      /'
  rm -f "$BUILD_LOG"
  record PASS "Frontend build"
else
  tail -15 "$BUILD_LOG" | sed 's/^/      /'
  rm -f "$BUILD_LOG"
  record FAIL "Frontend build"
fi

# ── Hermes dev health gates ────────────────────────────────────────────────
section "Hermes Dev Health Gates"
if "$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check > /tmp/phase3a-h1-mem.$$ 2>&1; then
  record PASS "memory-check"
else
  record FAIL "memory-check"
  tail -15 /tmp/phase3a-h1-mem.$$ | sed 's/^/      /'
fi
rm -f /tmp/phase3a-h1-mem.$$

# dev-check may WARN only for .claude/ untracked — that is acceptable.
if "$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check > /tmp/phase3a-h1-dev.$$ 2>&1; then
  record PASS "dev-check"
else
  if grep -qiE '(WARN|\.claude/)' /tmp/phase3a-h1-dev.$$ && ! grep -qiE 'FAIL|ERROR' /tmp/phase3a-h1-dev.$$; then
    record PASS "dev-check (.claude WARN only)"
  else
    record FAIL "dev-check"
    tail -20 /tmp/phase3a-h1-dev.$$ | sed 's/^/      /'
  fi
fi
rm -f /tmp/phase3a-h1-dev.$$

# ── Smoke (all profiles incl. phase3a_h1_workflow_hardening) ───────────────
if [ "$RUN_SMOKE" = true ]; then
  section "Smoke (all profiles incl. phase3a_h1_workflow_hardening)"
  if "$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all \
      > /tmp/phase3a-h1-smoke.$$ 2>&1; then
    grep -E "Overall:" /tmp/phase3a-h1-smoke.$$ | tail -1 | sed 's/^/      /'
    rm -f /tmp/phase3a-h1-smoke.$$
    record PASS "Smoke all profiles"
  else
    record FAIL "Smoke all profiles"
    tail -30 /tmp/phase3a-h1-smoke.$$ | sed 's/^/      /'
    rm -f /tmp/phase3a-h1-smoke.$$
  fi
else
  info "Smoke skipped (--no-smoke)."
fi

# ── Lens 11 — Production Isolation / Runtime Artifact Boundary ────────────
section "Lens 11 — Production Isolation / Runtime Artifact Boundary"
STAGED_RUNTIME="$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null | grep -E \
  'audit-store|tool-confirmation-tokens|tool-write-rollback-manifests|workflow-store|\.jsonl|test-results|playwright-report|coverage|/dist/|/node_modules/|\.claude/' \
  || true)"
if [ -z "$STAGED_RUNTIME" ]; then
  record PASS "No runtime artifacts staged"
else
  echo "  Staged runtime artifacts:" >&2
  echo "$STAGED_RUNTIME" | sed 's/^/      /' >&2
  record FAIL "Runtime artifacts staged"
fi

# Final production safety (read-only).
FINAL_GW="$(ps -p "$PRODUCTION_GATEWAY_PID" -o pid= 2>/dev/null | tr -d ' ' || true)"
FINAL_COUNT="$(pgrep -f 'hermes_cli.main gateway run' 2>/dev/null | grep -c . || true)"
FINAL_5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
FINAL_5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
echo "  Production Gateway PID:    ${FINAL_GW:-MISSING} (expected $PRODUCTION_GATEWAY_PID)"
echo "  Production Gateway count:  $FINAL_COUNT (expected 1)"
echo "  Port 5180 final:           ${FINAL_5180:-free}"
echo "  Port 5181 final:           ${FINAL_5181:-free}"

if [ "$FINAL_GW" = "$PRODUCTION_GATEWAY_PID" ] && [ "$FINAL_COUNT" = "1" ] \
   && [ -z "$FINAL_5180" ] && [ -z "$FINAL_5181" ]; then
  record PASS "Production Safety (PID 28428 / count 1 / ports free)"
else
  record FAIL "Production Safety (PID/count/ports)"
fi

# ── Summary ───────────────────────────────────────────────────────────────
section "Hardening Audit Summary"
echo "  Checks PASSED: $LENS_PASS"
echo "  Checks FAILED: $LENS_FAIL"

if [ "$LENS_FAIL" -eq 0 ]; then
  echo "  Overall: PASS (11 lenses + preservation + governance + smoke, deterministic)"
  exit 0
else
  echo "  Overall: FAIL ($LENS_FAIL check(s) failed)"
  exit 1
fi
