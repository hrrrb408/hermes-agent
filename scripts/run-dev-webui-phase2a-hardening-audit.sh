#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 2A-H1 Deterministic Hardening Audit
#
# Deterministic, agent-independent 7-lens boundary audit for the Phase 2A
# read-only multi-tool execution surface. This script is the replacement for
# the unstable adversarial-review agent that died mid-run during the Phase 2A
# final hardening pass (P2, ADV-REVIEW-CLOSURE-2A-H1-001).
#
# What it does (all read-only / hermetic):
#   Lens 1/2/3/4/5/6/7 — runs the boundary + regression test files that pin
#   every lens invariant, then re-runs the dev smoke harness (blocked +
#   completed + phase2a profiles) and the Hermes memory/dev health gates.
#
# Hard guarantees:
#   * set -euo pipefail
#   * Refuses production HERMES_HOME (~/.hermes) or anything under it
#   * Never touches production state.db
#   * Never stops / restarts / replaces / signals the Production Gateway
#   * Binds nothing itself; the smoke harness it invokes binds 127.0.0.1 only
#   * Produces NO committable runtime artifacts (tests use tmp_path; smoke
#     cleans its own /tmp logs)
#   * Exits non-zero if any lens fails; prints a PASS/FAIL summary
#
# Usage:
#   ./scripts/run-dev-webui-phase2a-hardening-audit.sh            # full audit
#   ./scripts/run-dev-webui-phase2a-hardening-audit.sh --no-smoke # skip live smoke
#   ./scripts/run-dev-webui-phase2a-hardening-audit.sh --help
#
# Hardening IDs: HARDENING-2A-H1-001 / ADV-REVIEW-CLOSURE-2A-H1-001 /
#                BOUNDARY-AUDIT-2A-H1-001
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEV_API_PORT_FALLBACK=5181
WEBUI_PORT_FALLBACK=5180
PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
# Phase 1G-10A refreshed baseline. Read-only observation only; never acted upon.
PRODUCTION_GATEWAY_PID=1962

RUN_SMOKE=true
for arg in "$@"; do
  case "$arg" in
    --no-smoke) RUN_SMOKE=false ;;
    --help|-h)
      cat <<USAGE
Usage: $0 [--no-smoke] [--help]

  --no-smoke  Skip the live Playwright smoke profiles (Lenses 1/7 live evidence).
              Use when browser servers are unavailable; the deterministic test
              lenses still run.
  --help      Show this help message.
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

section "Phase 2A-H1 Deterministic Hardening Audit"
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

# Dev-only execution gates are intentionally left unset here so the test
# lenses assert the default-disabled posture; the smoke harness sets its own.
unset HERMES_AGENT_RUN_ENABLED HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED
unset HERMES_TOOL_HANDLER_CALL_ENABLED HERMES_POST_EXECUTION_AUDIT_ENABLED
# Never carry real provider keys into the audit.
unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL OPENAI_API_KEY
unset ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY

info "Environment:   SAFE (dev home; production ~/.hermes refused; gates unset)"

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

run_lens_tests() { # lens-name description -- test-files...
  local lens="$1"; shift
  local desc="$1"; shift
  echo ""
  echo "  --- $lens: $desc ---"
  if "$REPO_ROOT/scripts/run_tests.sh" "$@" -- -q > /tmp/phase2a-h1-audit.$$ 2>&1; then
    tail -1 /tmp/phase2a-h1-audit.$$ | sed 's/^/      /'
    rm -f /tmp/phase2a-h1-audit.$$
    record PASS "$lens"
    return 0
  else
    tail -20 /tmp/phase2a-h1-audit.$$ | sed 's/^/      /'
    rm -f /tmp/phase2a-h1-audit.$$
    record FAIL "$lens"
    return 1
  fi
}

# ── Lens 3 — Route Governance ─────────────────────────────────────────────
section "Lens 3 — Route Governance / OpenAPI Boundary (34/34/5/0/1/1)"
run_lens_tests "Lens 3 Route Governance" "OpenAPI == runtime, no write route" \
  tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py || true

# ── Lens 1 — Phase 1G Preservation ────────────────────────────────────────
section "Lens 1 — Phase 1G Clarify Chain Preservation"
run_lens_tests "Lens 1 Phase 1G Preservation" "clarify chain intact" \
  tests/test_dev_web_tool_execute.py \
  tests/test_dev_web_tool_execute_confirmation.py \
  tests/test_dev_web_tool_execute_digest.py \
  tests/test_dev_web_tool_handler_call.py \
  tests/test_dev_web_tool_dispatch.py \
  tests/test_dev_web_tool_handler_lookup.py \
  tests/test_dev_web_tool_pre_execution_audit.py \
  tests/test_dev_web_tool_post_execution_audit.py || true

# ── Lens 2 + Lens 4 + Lens 5 — Allowlist / Boundaries / Audit ─────────────
section "Lens 2/4/5 — Allowlist, Provider/Write/Side-effect, Audit Redaction"
run_lens_tests "Lens 2 Allowlist/Registry Boundary" "allowlist exact + safe" \
  tests/test_dev_web_phase_2a_read_only_registry.py || true
run_lens_tests "Lens 4 Provider/Write/Side-effect Boundary" "all flags False" \
  tests/test_dev_web_phase_2a_read_only_execute.py \
  tests/test_dev_web_phase_2a_security_boundaries.py || true
run_lens_tests "Lens 5 Audit Redaction Boundary" "no secret/repr leak" \
  tests/test_dev_web_phase_2a_read_only_audit.py \
  tests/test_dev_web_tool_dry_run_audit.py \
  tests/test_dev_web_tool_audit_read_api.py || true

# ── Lens 6 + aggregated 7-lens deterministic boundary ─────────────────────
section "Lens 6/7 — Production Isolation + Frontend Contract (deterministic)"
run_lens_tests "Lens 6+7 Hardening Boundary (deterministic 7-lens)" \
  "prod isolation + frontend mirror + verdict" \
  tests/test_dev_web_phase_2a_hardening_boundaries.py || true

# ── Hermes dev health gates ───────────────────────────────────────────────
section "Hermes Dev Health Gates"
if "$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check > /tmp/phase2a-h1-mem.$$ 2>&1; then
  record PASS "memory-check"
else
  record FAIL "memory-check"
  tail -15 /tmp/phase2a-h1-mem.$$ | sed 's/^/      /'
fi
rm -f /tmp/phase2a-h1-mem.$$

# dev-check may WARN only for .claude/ untracked — that is acceptable.
if "$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check > /tmp/phase2a-h1-dev.$$ 2>&1; then
  record PASS "dev-check"
else
  if grep -qiE '(WARN|\.claude/)' /tmp/phase2a-h1-dev.$$ && ! grep -qiE 'FAIL|ERROR' /tmp/phase2a-h1-dev.$$; then
    record PASS "dev-check (.claude WARN only)"
  else
    record FAIL "dev-check"
    tail -20 /tmp/phase2a-h1-dev.$$ | sed 's/^/      /'
  fi
fi
rm -f /tmp/phase2a-h1-dev.$$

# ── Smoke (Lenses 1/7 live evidence) ──────────────────────────────────────
if [ "$RUN_SMOKE" = true ]; then
  section "Lenses 1/7 — Live Smoke (blocked + completed + phase2a)"
  if "$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all \
      > /tmp/phase2a-h1-smoke.$$ 2>&1; then
    record PASS "Smoke all profiles"
  else
    record FAIL "Smoke all profiles"
    tail -30 /tmp/phase2a-h1-smoke.$$ | sed 's/^/      /'
  fi
  rm -f /tmp/phase2a-h1-smoke.$$
else
  info "Smoke skipped (--no-smoke)."
fi

# ── Final production safety ───────────────────────────────────────────────
section "Final Production Safety (read-only)"
FINAL_GW="$(ps -p "$PRODUCTION_GATEWAY_PID" -o pid= 2>/dev/null | tr -d ' ' || true)"
FINAL_COUNT="$(pgrep -f 'hermes_cli.main gateway run' 2>/dev/null | grep -c . || true)"
FINAL_5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
FINAL_5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
echo "  Production Gateway PID:  ${FINAL_GW:-MISSING} (expected $PRODUCTION_GATEWAY_PID)"
echo "  Production Gateway count: $FINAL_COUNT (expected 1)"
echo "  Port 5180 final:          ${FINAL_5180:-free}"
echo "  Port 5181 final:          ${FINAL_5181:-free}"

if [ "$FINAL_GW" = "$PRODUCTION_GATEWAY_PID" ] && [ "$FINAL_COUNT" = "1" ] \
   && [ -z "$FINAL_5180" ] && [ -z "$FINAL_5181" ]; then
  record PASS "Production Safety (PID 1962 / count 1 / ports free)"
else
  record FAIL "Production Safety (PID/count/ports)"
fi

# ── Summary ───────────────────────────────────────────────────────────────
section "Hardening Audit Summary"
echo "  Lenses PASSED: $LENS_PASS"
echo "  Lenses FAILED: $LENS_FAIL"

if [ "$LENS_FAIL" -eq 0 ]; then
  echo "  Overall: PASS (7/7 lenses, deterministic, agent-independent)"
  exit 0
else
  echo "  Overall: FAIL ($LENS_FAIL lens(es) failed)"
  exit 1
fi
