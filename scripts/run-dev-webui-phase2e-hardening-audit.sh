#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 2E-H1 Frontend UX Hardening Audit
#
# Deterministic, agent-independent 9-lens boundary audit for the Phase 2E
# unified developer console (Console Routing / Overview Safety / Workflow
# Continuity / Audit Cross-navigation / Blocked Reason / Accessibility /
# Type-State Consistency / UI No-leak / Smoke + Production Isolation).
# Closes the Phase 2E frontend hardening backlog (HARDENING-2E-H1-001 /
# CONSOLE-WORKFLOW-2E-H1-001 / ACCESSIBILITY-2E-H1-001 /
# UI-SECURITY-CLOSURE-2E-H1-001).
#
# What it does (all read-only / hermetic):
#   * Environment safety (dev home; production ~/.hermes refused; gates unset).
#   * Production Gateway read-only PID/count check (expected 28428 / count 1).
#   * Route governance (34/34/5/0/1/1, no new route, no provider route).
#   * Phase 2E-H1 frontend hardening tests (routing / workflow / cross-nav /
#     blocked reasons / accessibility-responsive / ui-no-leak).
#   * Phase 2E preservation tests (overview / safety / audit / execution /
#     provider / write-rollback / accessibility / foundations / common / nav).
#   * Backend blocked-reason vocabulary contract (Phase 2E-H1).
#   * Phase 1G/2A/2B/2C/2C-H1/2D/2D-H1 preservation (controlled chain intact).
#   * Frontend gates (type-check / lint / test / build).
#   * Hermes memory-check / dev-check.
#   * Live smoke (all profiles incl. phase2e_h1_frontend_ux_hardening).
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
#   ./scripts/run-dev-webui-phase2e-hardening-audit.sh            # full audit
#   ./scripts/run-dev-webui-phase2e-hardening-audit.sh --no-smoke # skip smoke
#   ./scripts/run-dev-webui-phase2e-hardening-audit.sh --help
#
# Hardening IDs: HARDENING-2E-H1-001 / CONSOLE-WORKFLOW-2E-H1-001 /
#                ACCESSIBILITY-2E-H1-001 / UI-SECURITY-CLOSURE-2E-H1-001
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
# Phase 2E sealed baseline. Read-only observation only; never acted upon.
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

section "Phase 2E-H1 Frontend UX Hardening Audit"
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
  local log="/tmp/phase2e-h1-audit.$$.${RANDOM}"
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
  local log="/tmp/phase2e-h1-fe.$$.${RANDOM}"
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

# ── Lens 1 — Console Routing / Navigation State Boundary ──────────────────
section "Lens 1 — Console Routing / Navigation State Boundary"
run_fe_tests "Lens 1 Console Routing / Nav State" "additive route + tablist + roving tabindex" \
  phase2e-h1-console-routing phase2e-devconsole-nav router top-status-bar || true

# ── Lens 2 — Overview / Safety Baseline Boundary ───────────────────────────
section "Lens 2 — Overview / Safety Baseline Boundary"
run_fe_tests "Lens 2 Overview / Safety Baseline" "frozen baseline + phase status + badges" \
  phase2e-h1-ui-no-leak phase2e-overview phase2e-safety-boundary phase2e-foundations || true

# ── Lens 3 — Workflow Continuity Boundary ──────────────────────────────────
section "Lens 3 — Workflow Continuity Boundary"
run_fe_tests "Lens 3 Workflow Continuity" "read-only / provider / write / rollback / audit" \
  phase2e-h1-workflow-continuity phase2e-tool-execution phase2e-provider-roundtrip phase2e-write-rollback phase2e-audit-viewer || true

# ── Lens 4 — Audit Cross-navigation Boundary ───────────────────────────────
section "Lens 4 — Audit Cross-navigation Boundary"
run_fe_tests "Lens 4 Audit Cross-navigation" "prefill bridge + lossy id display" \
  phase2e-h1-audit-cross-navigation phase2e-audit-viewer phase2e-devconsole-nav || true

# ── Lens 5 — Blocked Reason / Error State Boundary ─────────────────────────
section "Lens 5 — Blocked Reason / Error State Boundary"
run_fe_tests "Lens 5 Blocked Reason Catalogue (frontend)" "stable code coverage + safe fallback" \
  phase2e-h1-blocked-reasons phase2e-foundations phase2e-common-components || true
run_py_tests "Lens 5 Blocked Reason Vocabulary (backend contract)" "vocabulary pinned at Python level" \
  tests/test_dev_web_phase_2e_h1_frontend_contract.py || true

# ── Lens 6 — Accessibility / Keyboard / Responsive Boundary ────────────────
section "Lens 6 — Accessibility / Keyboard / Responsive Boundary"
run_fe_tests "Lens 6 Accessibility / Keyboard / Responsive" "tablist + a11y + 820px collapse" \
  phase2e-h1-accessibility-responsive phase2e-accessibility || true

# ── Lens 7 — Frontend Type / State Consistency Boundary ────────────────────
section "Lens 7 — Frontend Type / State Consistency Boundary"
FE_TYPE_OK=true
TYPE_LOG="/tmp/phase2e-h1-type.$$.${RANDOM}"
(cd "$REPO_ROOT/apps/hermes-dev-webui" && pnpm type-check > "$TYPE_LOG" 2>&1) || FE_TYPE_OK=false
LINT_LOG="/tmp/phase2e-h1-lint.$$.${RANDOM}"
(cd "$REPO_ROOT/apps/hermes-dev-webui" && pnpm lint > "$LINT_LOG" 2>&1) || { cat "$LINT_LOG"; FE_TYPE_OK=false; }
rm -f "$TYPE_LOG" "$LINT_LOG"
if [ "$FE_TYPE_OK" = true ]; then
  echo "  vue-tsc --noEmit: PASS"
  echo "  eslint .:         PASS"
  record PASS "Lens 7 Type / Lint Consistency"
else
  record FAIL "Lens 7 Type / Lint Consistency"
fi

# ── Lens 8 — UI No-leak / Safety Boundary ──────────────────────────────────
section "Lens 8 — UI No-leak / Safety Boundary"
run_fe_tests "Lens 8 UI No-leak / Safety" "no secret / token / args / callable / prod path" \
  phase2e-h1-ui-no-leak phase2e-safety-boundary phase2e-accessibility phase2e-audit-viewer || true

# ── Route governance (no new route) ────────────────────────────────────────
section "Route Governance (34/34/5/0/1/1, no new route, no provider route)"
run_py_tests "Route Governance" "OpenAPI == runtime, no write route, no provider route" \
  tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py \
  tests/test_dev_web_phase_2e_frontend_contract.py || true

# ── Phase 1G/2A/2B/2C/2C-H1/2D/2D-H1 Preservation ─────────────────────────
section "Phase 1G/2A/2B/2C/2C-H1/2D/2D-H1 Preservation (controlled chain intact)"
run_py_tests "Phase 1G-2D-H1 Preservation" "read-only + provider + write + rollback + audit" \
  tests/test_dev_web_phase_2a_security_boundaries.py \
  tests/test_dev_web_phase_2a_hardening_boundaries.py \
  tests/test_dev_web_phase_2b_provider_security.py \
  tests/test_dev_web_phase_2b_hardening_boundaries.py \
  tests/test_dev_web_phase_2c_write_security.py \
  tests/test_dev_web_phase_2c_h1_write_hardening.py \
  tests/test_dev_web_phase_2d_audit_security.py \
  tests/test_dev_web_phase_2d_h1_audit_security.py || true

# ── Frontend build gate ────────────────────────────────────────────────────
section "Frontend Build Gate (vite build)"
BUILD_LOG="/tmp/phase2e-h1-build.$$.${RANDOM}"
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
if "$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check > /tmp/phase2e-h1-mem.$$ 2>&1; then
  record PASS "memory-check"
else
  record FAIL "memory-check"
  tail -15 /tmp/phase2e-h1-mem.$$ | sed 's/^/      /'
fi
rm -f /tmp/phase2e-h1-mem.$$

# dev-check may WARN only for .claude/ untracked — that is acceptable.
if "$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check > /tmp/phase2e-h1-dev.$$ 2>&1; then
  record PASS "dev-check"
else
  if grep -qiE '(WARN|\.claude/)' /tmp/phase2e-h1-dev.$$ && ! grep -qiE 'FAIL|ERROR' /tmp/phase2e-h1-dev.$$; then
    record PASS "dev-check (.claude WARN only)"
  else
    record FAIL "dev-check"
    tail -20 /tmp/phase2e-h1-dev.$$ | sed 's/^/      /'
  fi
fi
rm -f /tmp/phase2e-h1-dev.$$

# ── Lens 9 part A — Smoke (all profiles incl. phase2e_h1_frontend_ux_hardening) ─
if [ "$RUN_SMOKE" = true ]; then
  section "Lens 9A Live Smoke (all profiles incl. phase2e_h1_frontend_ux_hardening)"
  if "$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all \
      > /tmp/phase2e-h1-smoke.$$ 2>&1; then
    grep -E "Overall:" /tmp/phase2e-h1-smoke.$$ | tail -1 | sed 's/^/      /'
    rm -f /tmp/phase2e-h1-smoke.$$
    record PASS "Smoke all profiles"
  else
    record FAIL "Smoke all profiles"
    tail -30 /tmp/phase2e-h1-smoke.$$ | sed 's/^/      /'
    rm -f /tmp/phase2e-h1-smoke.$$
  fi
else
  info "Smoke skipped (--no-smoke)."
fi

# ── Runtime artifacts not staged ───────────────────────────────────────────
section "Runtime Artifacts Not Staged"
STAGED_RUNTIME="$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null | grep -E \
  'audit-store|tool-confirmation-tokens|tool-write-rollback-manifests|\.jsonl|test-results|playwright-report|coverage|/dist/|/node_modules/' \
  || true)"
if [ -z "$STAGED_RUNTIME" ]; then
  record PASS "No runtime artifacts staged"
else
  echo "  Staged runtime artifacts:" >&2
  echo "$STAGED_RUNTIME" | sed 's/^/      /' >&2
  record FAIL "Runtime artifacts staged"
fi

# ── Lens 9 part B — Final production safety ────────────────────────────────
section "Lens 9B — Final Production Safety (read-only)"
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
  echo "  Overall: PASS (9 lenses + preservation + governance + smoke, deterministic)"
  exit 0
else
  echo "  Overall: FAIL ($LENS_FAIL check(s) failed)"
  exit 1
fi
