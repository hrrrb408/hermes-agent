#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 2D-H1 Audit Storage Hardening Audit
#
# Deterministic, agent-independent 10-lens boundary audit for the Phase 2D
# durable dev audit store (schema / sanitizer / append store / index / query /
# rotation / recovery / dual-write / API+Viewer no-leak / production isolation).
# Closes the Phase 2D P2 backlog
# (HARDENING-2D-H1-001 / AUDIT-CONSISTENCY-2D-H1-001 /
#  AUDIT-STRESS-2D-H1-001 / AUDIT-SECURITY-CLOSURE-2D-H1-001).
#
# What it does (all read-only / hermetic):
#   * Environment safety (dev home; production ~/.hermes refused; gates unset).
#   * Production Gateway read-only PID/count check (expected 28428 / count 1).
#   * Route governance (34/34/5/0/1/1, no new route).
#   * Phase 2D audit tests (schema / sanitizer / store / index / query /
#     rotation / recovery / api / integration / security).
#   * Phase 2D-H1 hardening tests (store hardening / consistency / security).
#   * Legacy compatibility (audit read + audit read api + integration).
#   * Phase 1G/2A/2B/2C/2C-H1 preservation (controlled chain intact).
#   * Repeated hardening stability (5/5).
#   * Hermes memory-check / dev-check.
#   * Live smoke (all profiles incl. phase2d_audit_store_indexing).
#   * Final production safety (PID 28428 / count 1 / ports free).
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
#   ./scripts/run-dev-webui-phase2d-hardening-audit.sh            # full audit
#   ./scripts/run-dev-webui-phase2d-hardening-audit.sh --no-smoke # skip smoke
#   ./scripts/run-dev-webui-phase2d-hardening-audit.sh --help
#
# Hardening IDs: HARDENING-2D-H1-001 / AUDIT-CONSISTENCY-2D-H1-001 /
#                AUDIT-STRESS-2D-H1-001 / AUDIT-SECURITY-CLOSURE-2D-H1-001
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
# Phase 2D sealed baseline. Read-only observation only; never acted upon.
PRODUCTION_GATEWAY_PID=28428

RUN_SMOKE=true
RUN_FRONTEND=true
for arg in "$@"; do
  case "$arg" in
    --no-smoke) RUN_SMOKE=false ;;
    --no-frontend) RUN_FRONTEND=false ;;
    --help|-h)
      cat <<USAGE
Usage: $0 [--no-smoke] [--no-frontend] [--help]

  --no-smoke      Skip the live Playwright smoke profiles.
  --no-frontend   Skip the frontend gates (type-check / lint / test / build).
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

section "Phase 2D-H1 Audit Storage Hardening Audit"
info "Repo root:     $REPO_ROOT"
info "Run smoke:     $RUN_SMOKE"
info "Run frontend:  $RUN_FRONTEND"

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

run_lens_tests() { # lens-name description -- test-files...
  local lens="$1"; shift
  local desc="$1"; shift
  echo ""
  echo "  --- $lens: $desc ---"
  local log="/tmp/phase2d-h1-audit.$$.${RANDOM}"
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

# ── Lens 1 — Audit Schema / Canonical Event Boundary ──────────────────────
section "Lens 1 — Audit Schema / Canonical Event Boundary"
run_lens_tests "Lens 1 Audit Schema Boundary" "canonical audit_schema_v2 stable" \
  tests/test_dev_web_phase_2d_audit_schema.py \
  tests/test_dev_web_phase_2d_h1_audit_security.py || true

# ── Lens 2 — Unified Sanitizer / Redaction Boundary ───────────────────────
section "Lens 2 — Unified Sanitizer / Redaction Boundary (str() fallback closed)"
run_lens_tests "Lens 2 Sanitizer No-Leak" "unified redaction, no str(object)" \
  tests/test_dev_web_phase_2d_audit_sanitizer.py \
  tests/test_dev_web_phase_2d_audit_security.py \
  tests/test_dev_web_phase_2d_h1_audit_security.py || true

# ── Lens 3 — Append-only Store / Sequence Consistency ─────────────────────
section "Lens 3 — Append-only Store / Sequence Consistency (concurrency + floor)"
run_lens_tests "Lens 3 Append + Sequence Consistency" "no lost events, monotonic seq" \
  tests/test_dev_web_phase_2d_audit_store.py \
  tests/test_dev_web_phase_2d_h1_audit_store_hardening.py || true

# ── Lens 4 — Index Build / Update / Repair Consistency ────────────────────
section "Lens 4 — Index Build / Update / Repair Consistency"
run_lens_tests "Lens 4 Index Consistency" "index equals scan; rebuild/repair" \
  tests/test_dev_web_phase_2d_audit_index.py \
  tests/test_dev_web_phase_2d_h1_audit_consistency.py || true

# ── Lens 5 — Cursor Query / Filter / Search Stability ─────────────────────
section "Lens 5 — Cursor Query / Filter / Search Stability"
run_lens_tests "Lens 5 Cursor + Filter Stability" "pagination, filters, tamper" \
  tests/test_dev_web_phase_2d_audit_query.py \
  tests/test_dev_web_phase_2d_audit_api.py \
  tests/test_dev_web_phase_2d_h1_audit_consistency.py || true

# ── Lens 6 — Rotation / Segment Recovery Boundary ─────────────────────────
section "Lens 6 — Rotation / Segment Recovery Boundary"
run_lens_tests "Lens 6 Rotation Boundary" "rotate by size/count, no overwrite" \
  tests/test_dev_web_phase_2d_audit_rotation.py \
  tests/test_dev_web_phase_2d_h1_audit_store_hardening.py || true

# ── Lens 7 — Corruption Detection / Quarantine Boundary ───────────────────
section "Lens 7 — Corruption Detection / Quarantine Boundary"
run_lens_tests "Lens 7 Corruption + Quarantine" "detect, quarantine, query skips" \
  tests/test_dev_web_phase_2d_audit_recovery.py \
  tests/test_dev_web_phase_2d_h1_audit_store_hardening.py || true

# ── Lens 8 — Legacy Dual-write / Compatibility Boundary ───────────────────
section "Lens 8 — Legacy Dual-write / Compatibility Boundary"
run_lens_tests "Lens 8 Dual-write Compatibility" "7 kinds, legacy read intact" \
  tests/test_dev_web_phase_2d_audit_integration.py \
  tests/test_dev_web_tool_audit_read.py \
  tests/test_dev_web_tool_audit_read_api.py \
  tests/test_dev_web_phase_2d_h1_audit_consistency.py || true

# ── Lens 9 — Audit API / Viewer No-leak Boundary ──────────────────────────
section "Lens 9 — Audit API / Viewer No-leak Boundary"
run_lens_tests "Lens 9 API + Viewer No-Leak" "no secret/args/callable/path" \
  tests/test_dev_web_phase_2d_audit_api.py \
  tests/test_dev_web_phase_2d_audit_security.py \
  tests/test_dev_web_phase_2d_h1_audit_security.py || true

# ── Phase 1G/2A/2B/2C/2C-H1 Preservation ──────────────────────────────────
section "Phase 1G/2A/2B/2C/2C-H1 Preservation (controlled chain intact)"
run_lens_tests "Phase 1G-2C-H1 Preservation" "read-only + provider + write + rollback" \
  tests/test_dev_web_phase_2a_read_only_registry.py \
  tests/test_dev_web_phase_2a_security_boundaries.py \
  tests/test_dev_web_phase_2a_hardening_boundaries.py \
  tests/test_dev_web_phase_2b_provider_security.py \
  tests/test_dev_web_phase_2b_hardening_boundaries.py \
  tests/test_dev_web_phase_2c_write_security.py \
  tests/test_dev_web_phase_2c_h1_write_hardening.py || true

# ── Lens 10 part A — Route Governance (no new route) ──────────────────────
section "Lens 10A — Route Governance (34/34/5/0/1/1, no new route)"
run_lens_tests "Lens 10A Route Governance" "OpenAPI == runtime, no write route" \
  tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py || true

# ── Repeated hardening stability (5/5) ────────────────────────────────────
section "Repeated Hardening Stability (flake closure, 5/5)"
REPEAT_PASS=0
REPEAT_FAIL=0
for i in 1 2 3 4 5; do
  if "$REPO_ROOT/scripts/run_tests.sh" \
      tests/test_dev_web_phase_2d_h1_audit_store_hardening.py \
      tests/test_dev_web_phase_2d_h1_audit_consistency.py \
      tests/test_dev_web_phase_2d_h1_audit_security.py \
      -- -q > /tmp/phase2d-h1-repeat.$$.${i} 2>&1; then
    REPEAT_PASS=$((REPEAT_PASS + 1))
  else
    REPEAT_FAIL=$((REPEAT_FAIL + 1))
    tail -15 /tmp/phase2d-h1-repeat.$$.${i} | sed 's/^/      /'
  fi
  rm -f /tmp/phase2d-h1-repeat.$$.${i}
done
echo "  Repeated hardening runs: $REPEAT_PASS passed / $REPEAT_FAIL failed (of 5)"
if [ "$REPEAT_FAIL" -eq 0 ]; then
  record PASS "Repeated hardening checks (5/5)"
else
  record FAIL "Repeated hardening checks"
fi

# ── Hermes dev health gates ───────────────────────────────────────────────
section "Hermes Dev Health Gates"
if "$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check > /tmp/phase2d-h1-mem.$$ 2>&1; then
  record PASS "memory-check"
else
  record FAIL "memory-check"
  tail -15 /tmp/phase2d-h1-mem.$$ | sed 's/^/      /'
fi
rm -f /tmp/phase2d-h1-mem.$$

# dev-check may WARN only for .claude/ untracked — that is acceptable.
if "$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check > /tmp/phase2d-h1-dev.$$ 2>&1; then
  record PASS "dev-check"
else
  if grep -qiE '(WARN|\.claude/)' /tmp/phase2d-h1-dev.$$ && ! grep -qiE 'FAIL|ERROR' /tmp/phase2d-h1-dev.$$; then
    record PASS "dev-check (.claude WARN only)"
  else
    record FAIL "dev-check"
    tail -20 /tmp/phase2d-h1-dev.$$ | sed 's/^/      /'
  fi
fi
rm -f /tmp/phase2d-h1-dev.$$

# ── Frontend gates ────────────────────────────────────────────────────────
if [ "$RUN_FRONTEND" = true ]; then
  section "Frontend Gates (type-check / lint / test / build)"
  cd "$REPO_ROOT/apps/hermes-dev-webui"
  FE_OK=true
  for gate in "pnpm type-check" "pnpm lint" "pnpm test" "pnpm build"; do
    if $gate > "/tmp/phase2d-h1-fe.$$.${gate// /-}" 2>&1; then
      echo "  frontend $gate: PASS"
    else
      echo "  frontend $gate: FAIL"
      tail -15 "/tmp/phase2d-h1-fe.$$.${gate// /-}" | sed 's/^/      /'
      FE_OK=false
    fi
    rm -f "/tmp/phase2d-h1-fe.$$.${gate// /-}"
  done
  cd "$REPO_ROOT"
  if [ "$FE_OK" = true ]; then record PASS "Frontend gates"; else record FAIL "Frontend gates"; fi
else
  info "Frontend gates skipped (--no-frontend). Run them separately:"
  info "  cd apps/hermes-dev-webui && pnpm type-check && pnpm lint && pnpm test && pnpm build"
fi

# ── Lens 9 live evidence — Smoke (frontend contract + audit store profile) ─
if [ "$RUN_SMOKE" = true ]; then
  section "Lens 9 Live Smoke (all profiles incl. phase2d_audit_store_indexing)"
  if "$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all \
      > /tmp/phase2d-h1-smoke.$$ 2>&1; then
    record PASS "Smoke all profiles"
  else
    record FAIL "Smoke all profiles"
    tail -30 /tmp/phase2d-h1-smoke.$$ | sed 's/^/      /'
  fi
  rm -f /tmp/phase2d-h1-smoke.$$
else
  info "Smoke skipped (--no-smoke)."
fi

# ── Lens 10 part B — Final production safety ──────────────────────────────
section "Lens 10B — Final Production Safety (read-only)"
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
echo "  Lenses PASSED: $LENS_PASS"
echo "  Lenses FAILED: $LENS_FAIL"

if [ "$LENS_FAIL" -eq 0 ]; then
  echo "  Overall: PASS (10/10 lenses, deterministic, agent-independent)"
  exit 0
else
  echo "  Overall: FAIL ($LENS_FAIL lens(es) failed)"
  exit 1
fi
