#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI — Execute / Audit Smoke Harness (Phase 1G-06)
#
# Dev-only, repeatable smoke harness for the clarify controlled-execution +
# audit-viewer chain. Replaces the ad-hoc /tmp harness used during earlier
# phases with a committed, self-cleaning runner.
#
# Usage:
#   ./scripts/run-dev-webui-execute-audit-smoke.sh blocked     # Profile A
#   ./scripts/run-dev-webui-execute-audit-smoke.sh completed   # Profile B
#   ./scripts/run-dev-webui-execute-audit-smoke.sh all         # A then B
#   ./scripts/run-dev-webui-execute-audit-smoke.sh --help
#
# Smoke profiles (the gate env vars are inherited by the Dev API process at
# start; the EXECUTE_EXPECTED var is inherited by the Playwright process):
#
#   blocked   -> HERMES_TOOL_EXECUTION_ENABLED=true
#                HERMES_AGENT_TOOLS_ENABLED=true
#                HERMES_TOOL_HANDLER_CALL_ENABLED  unset
#                EXECUTE_EXPECTED=blocked_tool_handler_call_not_enabled
#                (upstream gates on, handler-call gate off)
#
#   completed -> all three gates =true
#                EXECUTE_EXPECTED=clarify_execution_completed
#
#   Profile C (fully-disabled -> blocked_by_kill_switch) is an optional manual
#   variant documented in docs/webui/phase-1g-06-smoke-harness-runbook.md; it
#   is not a harness mode because the smoke spec's named expectation targets
#   Profiles A and B.
#
# Safety guarantees:
#   - set -euo pipefail
#   - Binds to 127.0.0.1 only (ports 5180 WebUI, 5181 Dev API)
#   - Refuses production HERMES_HOME (~/.hermes) or anything under it
#   - Refuses to touch production state.db
#   - Pre-checks 5180 / 5181 are free before starting
#   - Never starts / stops / restarts / replaces the Production Gateway
#   - Only kills PIDs it started (tracked explicitly)
#   - trap cleanup on EXIT / INT / TERM
#   - Cleans its own /tmp log files; never commits runtime artifacts
#   - Never exports real provider keys / never prints secrets
# ---------------------------------------------------------------------------
set -euo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Constants ─────────────────────────────────────────────────────────────
DEV_API_HOST="127.0.0.1"
DEV_API_PORT=5181
WEBUI_HOST="127.0.0.1"
WEBUI_PORT=5180
HEALTH_TIMEOUT=40
HEALTH_INTERVAL=1
PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
# Phase 1G-10A refresh: host reboot changed the sealed production gateway PID from 69355 to 1962.
# Phase 2C authorized refresh: an external gateway restart during the Phase 2C session moved
# the live PID from 1962 to 28428 (1 process, healthy, not caused by Phase 2C work). Baseline
# refreshed under user authorization (task sanctions an authorized PID refresh on drift).
# Keep this value pinned so the dev-only smoke harness fails closed on future PID drift.
PRODUCTION_GATEWAY_PID=28428
SMOKE_SPEC_REL="tests/smoke/phase-1g-04-30-execute-audit-smoke.spec.ts"

# PIDs tracked by this script (only these are ever killed)
API_PID=""
WEBUI_PID=""
API_LOG=""
WEBUI_LOG=""

# Aggregated results
GLOBAL_RESULT=0

# ── Parse args ────────────────────────────────────────────────────────────
PROFILE="all"
for arg in "$@"; do
  case "$arg" in
    blocked|completed|phase2a|phase2b_provider_fake_roundtrip|phase2c_write_sandbox|phase2c_h1_rollback_and_token_ttl|phase2d_audit_store_indexing|phase2e_frontend_ux_polish|phase2e_h1_frontend_ux_hardening|phase3a_workflow_mvp|phase3a_h1_workflow_hardening|phase3b_provider_readonly_boundary|all) PROFILE="$arg" ;;
    --help|-h)
      echo "Usage: $0 [blocked|completed|phase2a|phase2b_provider_fake_roundtrip|phase2c_write_sandbox|phase2c_h1_rollback_and_token_ttl|phase2d_audit_store_indexing|phase2e_frontend_ux_polish|phase2e_h1_frontend_ux_hardening|phase3a_workflow_mvp|phase3a_h1_workflow_hardening|phase3b_provider_readonly_boundary|all] [--help]"
      echo ""
      echo "  blocked                              Profile A — blocked_tool_handler_call_not_enabled"
      echo "  completed                            Profile B — clarify_execution_completed"
      echo "  phase2a                              Profile C — Phase 2A read-only multi-tool execution"
      echo "  phase2b_provider_fake_roundtrip      Profile D — Phase 2B provider fake round-trip"
      echo "  phase2c_write_sandbox                Profile E — Phase 2C controlled dev-sandbox write"
      echo "  phase2c_h1_rollback_and_token_ttl    Profile F — Phase 2C-H1 rollback execution + token TTL"
      echo "  phase2d_audit_store_indexing         Profile G — Phase 2D durable audit store + cursor query"
      echo "  phase2e_frontend_ux_polish           Profile H — Phase 2E unified developer console UX"
      echo "  phase2e_h1_frontend_ux_hardening     Profile I — Phase 2E-H1 console hardening invariants"
      echo "  phase3a_workflow_mvp                 Profile J — Phase 3A dev-only Agent Workflow MVP"
      echo "  phase3a_h1_workflow_hardening        Profile K — Phase 3A-H1 workflow hardening invariants"
      echo "  phase3b_provider_readonly_boundary   Profile L — Phase 3B real-provider read-only boundary"
      echo "  all                                  Run Profile A, B, C, D, E, F, G, H, I, J, K, then L (default)"
      echo "  --help                               Show this help message"
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $arg" >&2
      echo "Run '$0 --help' for usage." >&2
      exit 1
      ;;
  esac
done

# ── Logging helpers ───────────────────────────────────────────────────────
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*" >&2; }

section() {
  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "  $*"
  echo "───────────────────────────────────────────────────────────────"
}

# ── Cleanup (only processes started by this script) ───────────────────────
cleanup() {
  local exit_code=$?
  section "Cleanup"

  # Stop Dev API (started by this script only)
  if [ -n "$API_PID" ]; then
    if kill -0 "$API_PID" 2>/dev/null; then
      info "Stopping Dev API (PID $API_PID)..."
      kill "$API_PID" 2>/dev/null || true
      wait "$API_PID" 2>/dev/null || true
      info "Dev API stopped."
    else
      info "Dev API (PID $API_PID) already exited."
    fi
    API_PID=""
  fi

  # Stop WebUI + its child/grandchild processes (pnpm -> node -> vite)
  if [ -n "$WEBUI_PID" ]; then
    if kill -0 "$WEBUI_PID" 2>/dev/null; then
      info "Stopping WebUI (PID $WEBUI_PID and children)..."
      local child grandchild
      for child in $(pgrep -P "$WEBUI_PID" 2>/dev/null); do
        for grandchild in $(pgrep -P "$child" 2>/dev/null); do
          kill "$grandchild" 2>/dev/null || true
        done
        kill "$child" 2>/dev/null || true
      done
      kill "$WEBUI_PID" 2>/dev/null || true
      wait "$WEBUI_PID" 2>/dev/null || true
      info "WebUI stopped."
    else
      info "WebUI (PID $WEBUI_PID) already exited."
    fi
    WEBUI_PID=""
  fi

  # Warn (never kill) if ports are still held — could be a process we did not start
  local port5180 port5181
  port5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
  port5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$port5180" ]; then
    warn "Port 5180 still occupied after cleanup (do NOT kill blindly):"
    echo "$port5180" | sed 's/^/    /'
  fi
  if [ -n "$port5181" ]; then
    warn "Port 5181 still occupied after cleanup (do NOT kill blindly):"
    echo "$port5181" | sed 's/^/    /'
  fi

  # Remove this script's own /tmp log files
  if [ -n "${API_LOG:-}" ] && [ -f "$API_LOG" ]; then rm -f "$API_LOG"; fi
  if [ -n "${WEBUI_LOG:-}" ] && [ -f "$WEBUI_LOG" ]; then rm -f "$WEBUI_LOG"; fi

  # Production Gateway sanity — informational, never acted upon
  local gw
  gw="$(ps -p "$PRODUCTION_GATEWAY_PID" -o pid= 2>/dev/null | tr -d ' ' || true)"
  if [ "$gw" = "$PRODUCTION_GATEWAY_PID" ]; then
    info "Production Gateway PID $PRODUCTION_GATEWAY_PID: still running (untouched)."
  else
    warn "Production Gateway PID $PRODUCTION_GATEWAY_PID not found via ps — investigate, do NOT 'fix'."
  fi

  info "Cleanup complete."
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

# ── Banner ────────────────────────────────────────────────────────────────
section "Hermes Dev WebUI — Execute / Audit Smoke Harness (Phase 1G-06)"
info "Source root:   $REPO_ROOT"
info "Script:        $0"
info "Profile:       $PROFILE"

# ── 1. Environment safety ────────────────────────────────────────────────
section "Environment Safety"

HERMES_HOME="${HERMES_HOME:-$DEFAULT_DEV_HERMES_HOME}"
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
if [ ! -f "$REPO_ROOT/hermes_cli/main.py" ]; then
  error "Cannot find hermes_cli/main.py in REPO_ROOT=$REPO_ROOT"
  exit 1
fi
info "Environment:   SAFE (dev home confirmed; production ~/.hermes refused)"

# ── 2. Prerequisites ─────────────────────────────────────────────────────
section "Prerequisites"

VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
  error "Python venv not found at $VENV_PYTHON"
  exit 1
fi
info "Python:        $VENV_PYTHON ($("$VENV_PYTHON" --version 2>&1))"

if ! command -v pnpm &>/dev/null; then
  error "pnpm not found in PATH"
  exit 1
fi
info "pnpm:          $(pnpm --version 2>/dev/null)"

WEBUI_DIR="$REPO_ROOT/apps/hermes-dev-webui"
SMOKE_SPEC="$WEBUI_DIR/$SMOKE_SPEC_REL"
if [ ! -f "$SMOKE_SPEC" ]; then
  error "Smoke spec not found: $SMOKE_SPEC"
  exit 1
fi
if [ ! -d "$WEBUI_DIR/node_modules/@playwright/test" ]; then
  error "@playwright/test not installed. Run 'cd $WEBUI_DIR && pnpm install' first."
  exit 1
fi
info "Smoke spec:    $SMOKE_SPEC"
info "Playwright:    installed"

# ── 3. Production Gateway check (read-only) ──────────────────────────────
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
info "Production Gateway PID $PRODUCTION_GATEWAY_PID confirmed. Will not touch it."

# ── Helpers: port check, health, start/stop ──────────────────────────────
assert_port_free() {
  local port="$1" result
  result="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$result" ]; then
    error "Port $port is already occupied:"
    echo "$result" | sed 's/^/    /'
    error "Refusing to start. Free the port (only processes you own) before retrying."
    exit 1
  fi
}

wait_for_url() {
  local url="$1" label="$2" elapsed=0
  info "Waiting for $label ($url)..."
  while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    if curl -sf -o /dev/null "$url" 2>/dev/null; then
      info "$label: ready (${elapsed}s)"
      return 0
    fi
    sleep "$HEALTH_INTERVAL"
    elapsed=$((elapsed + HEALTH_INTERVAL))
  done
  error "$label: NOT ready within ${HEALTH_TIMEOUT}s"
  return 1
}

# Configure gate env vars for a profile (exports for child processes).
# IMPORTANT: gates are read by the Dev API process at startup, so they must be
# set BEFORE launching the API. We always unset first so profiles do not bleed.
configure_gates() {
  local profile="$1"
  # Always reset to a known baseline first
  unset HERMES_TOOL_EXECUTION_ENABLED
  unset HERMES_AGENT_TOOLS_ENABLED
  unset HERMES_TOOL_HANDLER_CALL_ENABLED
  unset HERMES_POST_EXECUTION_AUDIT_ENABLED
  unset HERMES_PROVIDER_API_ENABLED
  unset HERMES_PROVIDER_MODE
  unset HERMES_TOOL_WRITE_EXECUTION_ENABLED
  unset EXECUTE_EXPECTED
  # Never carry real provider keys into the smoke run
  unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
  unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY
  unset GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY
  unset HERMES_PROVIDER_API_KEY

  case "$profile" in
    blocked)
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      # HERMES_TOOL_HANDLER_CALL_ENABLED intentionally UNSET
      export EXECUTE_EXPECTED=blocked_tool_handler_call_not_enabled
      ;;
    completed)
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export EXECUTE_EXPECTED=clarify_execution_completed
      ;;
    phase2a)
      # Phase 2A: read-only multi-tool execution. All gates on; the handler-
      # call gate enables the bounded read-only dispatcher. EXECUTE_EXPECTED
      # is a profile marker (the per-tool decision varies as <toolId>_execution_completed).
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export EXECUTE_EXPECTED=phase2a_read_only
      ;;
    phase2b_provider_fake_roundtrip)
      # Phase 2B: provider fake round-trip. All controlled-execution gates on
      # (so provider-requested tool calls flow through the full chain) plus the
      # fake provider mode. Real provider stays disabled (HERMES_PROVIDER_API_ENABLED
      # unset). No real provider key is exported.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export EXECUTE_EXPECTED=phase2b_provider_fake_roundtrip
      ;;
    phase2c_write_sandbox)
      # Phase 2C: controlled dev-sandbox write. All controlled-execution gates
      # on plus the Phase 2C write-enablement gate. The smoke enables write
      # execution ONLY for this dev smoke profile; the script trap / finalize
      # unsets it on exit. No production rollout, no ~/.hermes access.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase2c_write_sandbox
      ;;
    phase2c_h1_rollback_and_token_ttl)
      # Phase 2C-H1: rollback execution + file-backed confirmation token TTL.
      # Same gates as the write profile (rollback reuses the write gate) plus
      # write enablement. Dev-only; the script process exit cleans the export.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase2c_h1_rollback_and_token_ttl
      ;;
    phase2d_audit_store_indexing)
      # Phase 2D: durable audit store indexing. Read-only execution + fake
      # provider + write enablement so the dual-write bridge flows every
      # audit kind (dry-run / pre / post / provider / write / rollback /
      # confirmation) into the durable store, then the smoke queries the
      # store via filters + cursor pagination. Dev-only; no production
      # rollout, no ~/.hermes access.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase2d_audit_store_indexing
      ;;
    phase2e_frontend_ux_polish)
      # Phase 2E: unified developer console UX. Frontend-only polish; the gate
      # set mirrors phase2d (read-only execution + fake provider + write
      # enablement) so every console section — Tool Execution, Provider
      # Round-trip, Sandbox Write & Rollback, Audit Viewer — is demonstrable
      # end-to-end. No production rollout, no ~/.hermes access, no new route.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase2e_frontend_ux_polish
      ;;
    phase2e_h1_frontend_ux_hardening)
      # Phase 2E-H1: console hardening (frontend-only). The gate set mirrors
      # phase2e (read-only execution + fake provider + write enablement) so the
      # hardened console invariants — phase status, keyboard nav, no-leak DOM —
      # are demonstrable end-to-end. No production rollout, no ~/.hermes access,
      # no new route.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase2e_h1_frontend_ux_hardening
      ;;
    phase3a_workflow_mvp)
      # Phase 3A: dev-only Agent Workflow MVP. Manual, approval-gated workflow
      # that chains read-only tool + fake provider + sandbox write preview +
      # rollback reference into an audited plan. The gate set mirrors phase2e
      # (read-only execution + fake provider + write enablement) so the
      # workflow can demonstrate read-only + fake-provider steps AND generate
      # write previews (preview-only; the workflow never executes writes or
      # rollbacks). No production rollout, no ~/.hermes access, no new route.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase3a_workflow_mvp
      ;;
    phase3a_h1_workflow_hardening)
      # Phase 3A-H1: workflow hardening. The gate set mirrors phase3a
      # (read-only execution + fake provider + write enablement) so the
      # hardened workflow invariants — route governance, forbidden-step
      # blocking, write/rollback never-execute, single-use approval, no-leak —
      # are demonstrable end-to-end. No production rollout, no ~/.hermes
      # access, no new route.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
      export EXECUTE_EXPECTED=phase3a_h1_workflow_hardening
      ;;
    phase3b_provider_readonly_boundary)
      # Phase 3B: real-provider read-only boundary. Read-only execution gates on
      # + the FAKE provider only. The real provider is intentionally NOT enabled
      # (HERMES_PROVIDER_API_ENABLED unset) and NO provider key is exported, so
      # the real path stays blocked (externalNetworkCalled=false). The profile
      # verifies the disabled / blocked-real states, the /status providerBoundary
      # block, and the read-only tool allowlist — never a real network call and
      # never real spend. No production rollout, no ~/.hermes access, no new route.
      export HERMES_TOOL_EXECUTION_ENABLED=true
      export HERMES_AGENT_TOOLS_ENABLED=true
      export HERMES_TOOL_HANDLER_CALL_ENABLED=true
      export HERMES_PROVIDER_MODE=fake
      export EXECUTE_EXPECTED=phase3b_provider_readonly_boundary
      ;;
  esac
}

start_services() {
  local profile="$1"
  section "Start servers (profile=$profile)"

  assert_port_free "$WEBUI_PORT"
  assert_port_free "$DEV_API_PORT"
  info "Ports $WEBUI_PORT / $DEV_API_PORT: free"

  API_LOG="/tmp/hermes-p1g06-smoke-api.$$.log"
  WEBUI_LOG="/tmp/hermes-p1g06-smoke-vite.$$.log"

  info "Dev API gate env:"
  info "  HERMES_TOOL_EXECUTION_ENABLED=${HERMES_TOOL_EXECUTION_ENABLED:-<unset>}"
  info "  HERMES_AGENT_TOOLS_ENABLED=${HERMES_AGENT_TOOLS_ENABLED:-<unset>}"
  info "  HERMES_TOOL_HANDLER_CALL_ENABLED=${HERMES_TOOL_HANDLER_CALL_ENABLED:-<unset>}"
  info "  EXECUTE_EXPECTED=${EXECUTE_EXPECTED:-<unset>}"
  info "Starting Dev API on ${DEV_API_HOST}:${DEV_API_PORT} ..."
  HERMES_HOME="$HERMES_HOME" \
    "$VENV_PYTHON" -m hermes_cli.main dev-webui-api \
      --host "$DEV_API_HOST" \
      --port "$DEV_API_PORT" \
    > "$API_LOG" 2>&1 &
  API_PID=$!
  info "Dev API PID:   $API_PID"

  info "Starting WebUI on ${WEBUI_HOST}:${WEBUI_PORT} ..."
  (
    cd "$WEBUI_DIR"
    pnpm dev --host "$WEBUI_HOST" --port "$WEBUI_PORT" > /dev/null 2>&1
  ) < /dev/null > "$WEBUI_LOG" 2>&1 &
  WEBUI_PID=$!
  info "WebUI PID:     $WEBUI_PID"

  local health_ok=true
  if ! wait_for_url "http://${DEV_API_HOST}:${DEV_API_PORT}/api/dev/v1/status" "Dev API"; then
    health_ok=false
    error "Dev API log tail:"
    tail -20 "$API_LOG" 2>/dev/null | sed 's/^/    /'
  fi
  if ! wait_for_url "http://${WEBUI_HOST}:${WEBUI_PORT}" "WebUI"; then
    health_ok=false
    error "WebUI log tail:"
    tail -20 "$WEBUI_LOG" 2>/dev/null | sed 's/^/    /'
  fi
  if [ "$health_ok" = false ]; then
    error "Health check failed for profile=$profile. Aborting profile."
    return 1
  fi
  info "All services healthy for profile=$profile."
  return 0
}

stop_services() {
  local profile="$1"
  section "Stop servers (profile=$profile)"

  if [ -n "$API_PID" ]; then
    if kill -0 "$API_PID" 2>/dev/null; then
      info "Stopping Dev API (PID $API_PID)..."
      kill "$API_PID" 2>/dev/null || true
      wait "$API_PID" 2>/dev/null || true
      info "Dev API stopped."
    fi
    API_PID=""
  fi

  if [ -n "$WEBUI_PID" ]; then
    if kill -0 "$WEBUI_PID" 2>/dev/null; then
      info "Stopping WebUI (PID $WEBUI_PID and children)..."
      local child grandchild
      for child in $(pgrep -P "$WEBUI_PID" 2>/dev/null); do
        for grandchild in $(pgrep -P "$child" 2>/dev/null); do
          kill "$grandchild" 2>/dev/null || true
        done
        kill "$child" 2>/dev/null || true
      done
      kill "$WEBUI_PID" 2>/dev/null || true
      wait "$WEBUI_PID" 2>/dev/null || true
      info "WebUI stopped."
    fi
    WEBUI_PID=""
  fi

  # Brief drain then confirm ports released
  sleep 1
  local p5180 p5181
  p5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
  p5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$p5180" ]; then info "Port 5180: free"; else warn "Port 5180 still held"; fi
  if [ -z "$p5181" ]; then info "Port 5181: free"; else warn "Port 5181 still held"; fi
}

run_smoke_for_profile() {
  local profile="$1"
  section "Smoke profile: $profile"

  # Phase 2A / 2B use their own specs; blocked/completed use the 1G spec.
  local spec_rel="$SMOKE_SPEC_REL"
  if [ "$profile" = "phase2a" ]; then
    spec_rel="tests/smoke/phase-2a-read-only-tools-smoke.spec.ts"
  elif [ "$profile" = "phase2b_provider_fake_roundtrip" ]; then
    spec_rel="tests/smoke/phase-2b-provider-fake-roundtrip-smoke.spec.ts"
  elif [ "$profile" = "phase2c_write_sandbox" ]; then
    spec_rel="tests/smoke/phase-2c-write-sandbox-smoke.spec.ts"
  elif [ "$profile" = "phase2c_h1_rollback_and_token_ttl" ]; then
    spec_rel="tests/smoke/phase-2c-h1-rollback-and-token-ttl-smoke.spec.ts"
  elif [ "$profile" = "phase2d_audit_store_indexing" ]; then
    spec_rel="tests/smoke/phase-2d-audit-store-indexing-smoke.spec.ts"
  elif [ "$profile" = "phase2e_frontend_ux_polish" ]; then
    spec_rel="tests/smoke/phase-2e-frontend-ux-polish-smoke.spec.ts"
  elif [ "$profile" = "phase2e_h1_frontend_ux_hardening" ]; then
    spec_rel="tests/smoke/phase-2e-h1-console-hardening-smoke.spec.ts"
  elif [ "$profile" = "phase3a_workflow_mvp" ]; then
    spec_rel="tests/smoke/phase-3a-workflow-mvp-smoke.spec.ts"
  elif [ "$profile" = "phase3a_h1_workflow_hardening" ]; then
    spec_rel="tests/smoke/phase-3a-h1-workflow-hardening-smoke.spec.ts"
  elif [ "$profile" = "phase3b_provider_readonly_boundary" ]; then
    spec_rel="tests/smoke/phase-3b-provider-readonly-boundary-smoke.spec.ts"
  fi
  local spec_path="$WEBUI_DIR/$spec_rel"
  if [ ! -f "$spec_path" ]; then
    error "Smoke spec not found for profile=$profile: $spec_path"
    GLOBAL_RESULT=1
    return 1
  fi

  configure_gates "$profile"
  if ! start_services "$profile"; then
    stop_services "$profile"
    GLOBAL_RESULT=1
    return 1
  fi

  info "Running Playwright smoke spec ($EXECUTE_EXPECTED)..."
  info "  $spec_path"
  local smoke_rc=0
  (
    cd "$WEBUI_DIR"
    npx playwright test \
      --config "$WEBUI_DIR/playwright.config.ts" \
      "$spec_path"
  ) || smoke_rc=$?

  section "Profile result: $profile"
  echo "  Profile:          $profile"
  echo "  Expected decision:$EXECUTE_EXPECTED"
  echo "  Dev API PID:      (started this run)"
  echo "  Smoke exit code:  $smoke_rc"
  if [ "$smoke_rc" -eq 0 ]; then
    echo "  Result:           PASS"
  else
    echo "  Result:           FAIL"
    GLOBAL_RESULT=1
  fi

  stop_services "$profile"
  return 0
}

# ── 4. Run the requested profile(s) ──────────────────────────────────────
case "$PROFILE" in
  blocked|completed|phase2a|phase2b_provider_fake_roundtrip|phase2c_write_sandbox|phase2c_h1_rollback_and_token_ttl|phase2d_audit_store_indexing|phase2e_frontend_ux_polish|phase2e_h1_frontend_ux_hardening|phase3a_workflow_mvp|phase3a_h1_workflow_hardening|phase3b_provider_readonly_boundary)
    run_smoke_for_profile "$PROFILE"
    ;;
  all)
    run_smoke_for_profile "blocked"
    run_smoke_for_profile "completed"
    run_smoke_for_profile "phase2a"
    run_smoke_for_profile "phase2b_provider_fake_roundtrip"
    run_smoke_for_profile "phase2c_write_sandbox"
    run_smoke_for_profile "phase2c_h1_rollback_and_token_ttl"
    run_smoke_for_profile "phase2d_audit_store_indexing"
    run_smoke_for_profile "phase2e_frontend_ux_polish"
    run_smoke_for_profile "phase2e_h1_frontend_ux_hardening"
    run_smoke_for_profile "phase3a_workflow_mvp"
    run_smoke_for_profile "phase3a_h1_workflow_hardening"
    run_smoke_for_profile "phase3b_provider_readonly_boundary"
    ;;
esac

# ── 5. Final summary ─────────────────────────────────────────────────────
section "Final Summary"
echo "  Harness:          run-dev-webui-execute-audit-smoke.sh"
echo "  Profiles run:     $PROFILE"
echo "  Dev HERMES_HOME:  $HERMES_HOME"
echo "  Bind:             127.0.0.1 only (5180 WebUI / 5181 Dev API)"

final_5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
final_5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"
echo "  Port 5180 final:  ${final_5180:-free}"
echo "  Port 5181 final:  ${final_5181:-free}"

final_gw="$(ps -p "$PRODUCTION_GATEWAY_PID" -o pid= 2>/dev/null | tr -d ' ' || true)"
if [ "$final_gw" = "$PRODUCTION_GATEWAY_PID" ]; then
  echo "  Prod Gateway PID: $PRODUCTION_GATEWAY_PID (unchanged)"
else
  echo "  Prod Gateway PID: $PRODUCTION_GATEWAY_PID MISSING — investigate"
  GLOBAL_RESULT=1
fi

if [ "$GLOBAL_RESULT" -eq 0 ]; then
  echo "  Overall:          PASS"
else
  echo "  Overall:          FAIL"
fi

# Normal exit — trap cleanup will run, but servers already stopped.
exit "$GLOBAL_RESULT"
