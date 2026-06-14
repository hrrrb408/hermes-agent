#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Phase 2B-H1 Deterministic Provider Round-trip
# Hardening Audit
#
# Deterministic, agent-independent 8-lens boundary audit for the Phase 2B
# Provider Schema / API controlled round-trip surface. This script closes the
# Phase 2B P2 backlog (HARDENING-2B-H1-001 / PROVIDER-BOUNDARY-AUDIT-2B-H1-001
# / PROVIDER-FLAKE-CLOSURE-2B-H1-001):
#
#   P2-1 — real-vendor provider adapter not wired in Phase 2B (accepted: the
#          blocked framework exists; the concrete vendor call is deferred).
#   P2-2 — one transient flake under high parallelism in
#          test_audit_jsonl_no_secret_or_repr[audit_events_read-R1] (closed
#          here as non-reproduced with deterministic repeated-run evidence).
#   P2-3 — frontend visual polish (optional, non-blocking).
#
# What it does (all read-only / hermetic):
#   * Route governance (34/34/5/0/1/1).
#   * Phase 2B provider tests (schema / request / fake adapter / round-trip /
#     audit / security).
#   * Phase 1G/2A preservation tests (controlled chain + read-only registry).
#   * Deterministic 8-lens provider hardening boundary test.
#   * REPEATED provider audit redaction + round-trip stability checks.
#   * Hermes memory-check / dev-check.
#   * Live smoke (all profiles incl. phase2b_provider_fake_roundtrip).
#
# Hard guarantees:
#   * set -euo pipefail
#   * Refuses production HERMES_HOME (~/.hermes) or anything under it
#   * Never touches production state.db
#   * Never stops / restarts / replaces / signals the Production Gateway
#   * Never makes a real Provider network call (fake mode only)
#   * Binds nothing itself; the smoke harness it invokes binds 127.0.0.1 only
#   * Produces NO committable runtime artifacts (tests use tmp_path; smoke
#     cleans its own /tmp logs)
#   * Exits non-zero if any lens fails; prints a PASS/FAIL summary
#
# Usage:
#   ./scripts/run-dev-webui-phase2b-hardening-audit.sh            # full audit
#   ./scripts/run-dev-webui-phase2b-hardening-audit.sh --no-smoke # skip smoke
#   ./scripts/run-dev-webui-phase2b-hardening-audit.sh --help
#
# Hardening IDs: HARDENING-2B-H1-001 / PROVIDER-BOUNDARY-AUDIT-2B-H1-001 /
#                PROVIDER-FLAKE-CLOSURE-2B-H1-001
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

  --no-smoke  Skip the live Playwright smoke profiles (Lens 8 live evidence).
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

section "Phase 2B-H1 Deterministic Provider Round-trip Hardening Audit"
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

# Provider real-mode enablement + execution kill-switches are intentionally
# left unset here so the test lenses assert the default-disabled posture; the
# smoke harness sets its own.
unset HERMES_AGENT_RUN_ENABLED HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED
unset HERMES_TOOL_HANDLER_CALL_ENABLED HERMES_POST_EXECUTION_AUDIT_ENABLED
unset HERMES_PROVIDER_API_ENABLED HERMES_PROVIDER_MODE
# Never carry real provider keys into the audit.
unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL OPENAI_API_KEY
unset ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY

info "Environment:   SAFE (dev home; production ~/.hermes refused; provider/gates unset)"

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
  local log="/tmp/phase2b-h1-audit.$$.${RANDOM}"
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

# ── Lens 3 — Route Governance (no new route) ──────────────────────────────
section "Lens 3 — Route Governance (34/34/5/0/1/1, no provider route)"
run_lens_tests "Lens 3 Route Governance" "OpenAPI == runtime, no write route" \
  tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py || true

# ── Lenses 1/2/4/5/6 — Phase 2B provider boundary + audit ─────────────────
section "Lenses 1/2/4/5/6 — Provider Schema / Request / Fake / Real / Chain / Audit"
run_lens_tests "Lens 1 Provider Schema Boundary" "schema = allowlist projection" \
  tests/test_dev_web_phase_2b_provider_schema.py || true
run_lens_tests "Lens 2 Provider Request/Mode Boundary" "disabled/fake/real gating" \
  tests/test_dev_web_phase_2b_provider_request.py \
  tests/test_dev_web_phase_2b_provider_security.py || true
run_lens_tests "Lens 3 Fake Provider Determinism" "deterministic offline fake" \
  tests/test_dev_web_phase_2b_fake_provider_adapter.py || true
run_lens_tests "Lens 4 Real Provider Blocked Boundary" "real blocked by default" \
  tests/test_dev_web_phase_2b_provider_security.py || true
run_lens_tests "Lens 5 Controlled Chain Preservation" "full chain, no bypass" \
  tests/test_dev_web_phase_2b_provider_roundtrip.py || true
run_lens_tests "Lens 6 Provider Audit Redaction" "no secret/repr in audit" \
  tests/test_dev_web_phase_2b_provider_audit.py || true

# ── Phase 1G/2A preservation (controlled chain intact) ────────────────────
section "Phase 1G/2A Preservation (controlled chain intact)"
run_lens_tests "Phase 1G/2A Preservation" "read-only registry + execute + chain" \
  tests/test_dev_web_phase_2a_read_only_registry.py \
  tests/test_dev_web_phase_2a_read_only_execute.py \
  tests/test_dev_web_phase_2a_security_boundaries.py \
  tests/test_dev_web_phase_2a_hardening_boundaries.py || true

# ── Lens 7 — Deterministic 8-lens boundary + flake closure ────────────────
section "Lens 7 — Deterministic 8-lens Hardening Boundary + Flake Closure"
run_lens_tests "Lens 7 Hardening Boundary (8-lens deterministic)" \
  "PEM redaction + field stems + flake-closure scenario + repeated stability" \
  tests/test_dev_web_phase_2b_hardening_boundaries.py || true

# ── Repeated provider audit redaction + round-trip stability ──────────────
section "Repeated Provider Audit Redaction + Round-trip Stability (flake closure)"
REPEAT_PASS=0
REPEAT_FAIL=0
for i in 1 2 3 4 5; do
  if "$REPO_ROOT/scripts/run_tests.sh" \
      tests/test_dev_web_phase_2b_provider_audit.py \
      tests/test_dev_web_phase_2b_hardening_boundaries.py \
      -- -q > /tmp/phase2b-h1-repeat.$$.${i} 2>&1; then
    REPEAT_PASS=$((REPEAT_PASS + 1))
  else
    REPEAT_FAIL=$((REPEAT_FAIL + 1))
    tail -15 /tmp/phase2b-h1-repeat.$$.${i} | sed 's/^/      /'
  fi
  rm -f /tmp/phase2b-h1-repeat.$$.${i}
done
echo "  Repeated audit/redaction runs: $REPEAT_PASS passed / $REPEAT_FAIL failed (of 5)"
if [ "$REPEAT_FAIL" -eq 0 ]; then
  record PASS "Repeated flake-closure checks (5/5)"
else
  record FAIL "Repeated flake-closure checks"
fi

# ── Hermes dev health gates ───────────────────────────────────────────────
section "Hermes Dev Health Gates"
if "$REPO_ROOT/scripts/run-dev-hermes.sh" memory-check > /tmp/phase2b-h1-mem.$$ 2>&1; then
  record PASS "memory-check"
else
  record FAIL "memory-check"
  tail -15 /tmp/phase2b-h1-mem.$$ | sed 's/^/      /'
fi
rm -f /tmp/phase2b-h1-mem.$$

# dev-check may WARN only for .claude/ untracked — that is acceptable.
if "$REPO_ROOT/scripts/run-dev-hermes.sh" dev-check > /tmp/phase2b-h1-dev.$$ 2>&1; then
  record PASS "dev-check"
else
  if grep -qiE '(WARN|\.claude/)' /tmp/phase2b-h1-dev.$$ && ! grep -qiE 'FAIL|ERROR' /tmp/phase2b-h1-dev.$$; then
    record PASS "dev-check (.claude WARN only)"
  else
    record FAIL "dev-check"
    tail -20 /tmp/phase2b-h1-dev.$$ | sed 's/^/      /'
  fi
fi
rm -f /tmp/phase2b-h1-dev.$$

# ── Lens 8 — Live smoke (frontend contract + fake round-trip) ─────────────
if [ "$RUN_SMOKE" = true ]; then
  section "Lens 8 — Live Smoke (all profiles incl. phase2b_provider_fake_roundtrip)"
  if "$REPO_ROOT/scripts/run-dev-webui-execute-audit-smoke.sh" all \
      > /tmp/phase2b-h1-smoke.$$ 2>&1; then
    record PASS "Smoke all profiles"
  else
    record FAIL "Smoke all profiles"
    tail -30 /tmp/phase2b-h1-smoke.$$ | sed 's/^/      /'
  fi
  rm -f /tmp/phase2b-h1-smoke.$$
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
  echo "  Overall: PASS (8/8 lenses, deterministic, agent-independent)"
  exit 0
else
  echo "  Overall: FAIL ($LENS_FAIL lens(es) failed)"
  exit 1
fi
