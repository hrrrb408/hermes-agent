#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI Smoke Runner (Phase 0E-04)
#
# One-command smoke test: starts Dev API + WebUI, waits for health,
# runs the Phase 0E-03 Playwright smoke matrix, and cleans up.
#
# Usage:
#   ./scripts/run-dev-webui-smoke.sh              # full smoke cycle
#   ./scripts/run-dev-webui-smoke.sh --skip-smoke # start services only
#   ./scripts/run-dev-webui-smoke.sh --keep-running  # do not stop services
#   ./scripts/run-dev-webui-smoke.sh --help
#
# Safety:
#   - Binds to 127.0.0.1 only (ports 5180, 5181)
#   - Refuses to use production HERMES_HOME (~/.hermes)
#   - Refuses to start if ports are occupied
#   - Only kills processes it started
#   - Never affects Production Gateway
#   - Never starts Dev Gateway or Dashboard
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
HEALTH_TIMEOUT=30
HEALTH_INTERVAL=1
PRODUCTION_HERMES_HOME="/Users/huangruibang/.hermes"
DEFAULT_DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"

# ── PIDs tracked by this script ───────────────────────────────────────────
API_PID=""
WEBUI_PID=""

# ── Parse args ────────────────────────────────────────────────────────────
SKIP_SMOKE=false
KEEP_RUNNING=false

for arg in "$@"; do
  case "$arg" in
    --skip-smoke)    SKIP_SMOKE=true ;;
    --keep-running)  KEEP_RUNNING=true ;;
    --help|-h)
      echo "Usage: $0 [--skip-smoke] [--keep-running] [--help]"
      echo ""
      echo "  --skip-smoke     Start services but skip Playwright smoke tests"
      echo "  --keep-running   Keep services running after smoke tests pass"
      echo "  --help           Show this help message"
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $arg"
      echo "Run '$0 --help' for usage."
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

  if [ -n "$WEBUI_PID" ]; then
    if kill -0 "$WEBUI_PID" 2>/dev/null; then
      info "Stopping WebUI (PID $WEBUI_PID and children)..."
      # Kill child processes first (pnpm → node → vite)
      local child
      for child in $(pgrep -P "$WEBUI_PID" 2>/dev/null); do
        kill "$child" 2>/dev/null || true
      done
      # Also kill grandchildren (node spawns vite worker)
      for child in $(pgrep -P "$WEBUI_PID" 2>/dev/null); do
        local grandchild
        for grandchild in $(pgrep -P "$child" 2>/dev/null); do
          kill "$grandchild" 2>/dev/null || true
        done
      done
      kill "$WEBUI_PID" 2>/dev/null || true
      wait "$WEBUI_PID" 2>/dev/null || true
      info "WebUI stopped."
    else
      info "WebUI (PID $WEBUI_PID) already exited."
    fi
    WEBUI_PID=""
  fi

  # Verify port release — warn only, never kill unknown processes
  local port5180 port5181
  port5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
  port5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"

  if [ -n "$port5180" ]; then
    warn "Port 5180 still occupied after cleanup:"
    echo "$port5180" | sed 's/^/  /'
  fi
  if [ -n "$port5181" ]; then
    warn "Port 5181 still occupied after cleanup:"
    echo "$port5181" | sed 's/^/  /'
  fi

  # Clean up log files
  if [ -n "${API_LOG:-}" ] && [ -f "$API_LOG" ]; then
    rm -f "$API_LOG"
  fi
  if [ -n "${WEBUI_LOG:-}" ] && [ -f "$WEBUI_LOG" ]; then
    rm -f "$WEBUI_LOG"
  fi

  info "Cleanup complete."
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

# ── Print banner ──────────────────────────────────────────────────────────
section "Hermes Dev WebUI Smoke Runner"
info "Source root:  $REPO_ROOT"
info "Script:       $0"

# ── 1. Environment safety ────────────────────────────────────────────────
section "Environment Safety"

HERMES_HOME="${HERMES_HOME:-$DEFAULT_DEV_HERMES_HOME}"
info "HERMES_HOME:  $HERMES_HOME"

# Must exist
if [ ! -d "$HERMES_HOME" ]; then
  error "HERMES_HOME does not exist: $HERMES_HOME"
  exit 1
fi

# Must not be production
if [ "$HERMES_HOME" = "$PRODUCTION_HERMES_HOME" ]; then
  error "HERMES_HOME points to the production instance: $HERMES_HOME"
  error "The Dev WebUI Smoke Runner must use a development home."
  exit 1
fi

# Must not be inside production
case "$HERMES_HOME" in
  "$PRODUCTION_HERMES_HOME"/*)
    error "HERMES_HOME is inside the production instance: $HERMES_HOME"
    exit 1
    ;;
esac

# Verify repo root is the dev source
if [ ! -f "$REPO_ROOT/hermes_cli/main.py" ]; then
  error "Cannot find hermes_cli/main.py in REPO_ROOT=$REPO_ROOT"
  error "This script must be run from the Hermes dev repository."
  exit 1
fi

info "Environment:  SAFE (dev home confirmed)"

# ── 2. Port check ────────────────────────────────────────────────────────
section "Port Check"

check_port() {
  local port="$1"
  local result
  result="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$result" ]; then
    error "Port $port is already occupied:"
    echo "$result" | sed 's/^/  /'
    error "Refusing to start. Free the port or investigate before retrying."
    exit 1
  fi
  info "Port $port: free"
}

check_port "$WEBUI_PORT"
check_port "$DEV_API_PORT"

# ── 3. Prerequisites ─────────────────────────────────────────────────────
section "Prerequisites"

# Python venv
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
  error "Python venv not found at $VENV_PYTHON"
  exit 1
fi
info "Python:       $VENV_PYTHON ($($VENV_PYTHON --version 2>&1))"

# pnpm
if ! command -v pnpm &>/dev/null; then
  error "pnpm not found in PATH"
  exit 1
fi
info "pnpm:         $(pnpm --version 2>/dev/null)"

# Dev WebUI package
WEBUI_DIR="$REPO_ROOT/apps/hermes-dev-webui"
if [ ! -f "$WEBUI_DIR/package.json" ]; then
  error "Dev WebUI package.json not found at $WEBUI_DIR/package.json"
  exit 1
fi
info "WebUI dir:    $WEBUI_DIR"

# Playwright
if [ ! -d "$WEBUI_DIR/node_modules/@playwright/test" ]; then
  error "@playwright/test not installed. Run 'cd $WEBUI_DIR && pnpm install' first."
  exit 1
fi
info "Playwright:   installed"

# Smoke test files
SMOKE_SPEC="$WEBUI_DIR/tests/smoke/phase-0e-03-smoke.spec.ts"
TOOL_POLICY_SMOKE_SPEC="$WEBUI_DIR/tests/smoke/phase-1g-tool-policy-smoke.spec.ts"

if [ ! -f "$SMOKE_SPEC" ]; then
  error "Smoke test not found: $SMOKE_SPEC"
  exit 1
fi
info "Smoke spec:   $SMOKE_SPEC"

if [ ! -f "$TOOL_POLICY_SMOKE_SPEC" ]; then
  error "Tool Policy smoke test not found: $TOOL_POLICY_SMOKE_SPEC"
  exit 1
fi
info "Tool Policy:  $TOOL_POLICY_SMOKE_SPEC"

# ── 4. Start Dev API ─────────────────────────────────────────────────────
section "Start Dev API"

API_LOG="/tmp/hermes-dev-webui-smoke-api.$$.log"

info "Starting Dev API on ${DEV_API_HOST}:${DEV_API_PORT}..."
info "Log: $API_LOG"

HERMES_HOME="$HERMES_HOME" \
  "$VENV_PYTHON" -m hermes_cli.main dev-webui-api \
    --host "$DEV_API_HOST" \
    --port "$DEV_API_PORT" \
  > "$API_LOG" 2>&1 &
API_PID=$!

info "Dev API PID:  $API_PID"

# ── 5. Start WebUI ───────────────────────────────────────────────────────
section "Start WebUI"

WEBUI_LOG="/tmp/hermes-dev-webui-smoke-vite.$$.log"

info "Starting WebUI on ${WEBUI_HOST}:${WEBUI_PORT}..."
info "Log: $WEBUI_LOG"

# Start pnpm dev in a background job.
# We track the subshell PID and on cleanup we kill the subshell's
# children (the actual pnpm/node/vite processes) by finding them
# via pgrep -P.
(
  cd "$WEBUI_DIR"
  pnpm dev --host "$WEBUI_HOST" --port "$WEBUI_PORT" > /dev/null 2>&1
) < /dev/null > "$WEBUI_LOG" 2>&1 &
WEBUI_PID=$!

info "WebUI PID:    $WEBUI_PID"

# ── 6. Wait for health ──────────────────────────────────────────────────
section "Health Check"

wait_for_url() {
  local url="$1"
  local label="$2"
  local elapsed=0

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

HEALTH_OK=true

if ! wait_for_url "http://${DEV_API_HOST}:${DEV_API_PORT}/api/dev/v1/status" "Dev API"; then
  HEALTH_OK=false
  error "Dev API log tail:"
  tail -20 "$API_LOG" 2>/dev/null | sed 's/^/  /'
fi

if ! wait_for_url "http://${WEBUI_HOST}:${WEBUI_PORT}" "WebUI"; then
  HEALTH_OK=false
  error "WebUI log tail:"
  tail -20 "$WEBUI_LOG" 2>/dev/null | sed 's/^/  /'
fi

if [ "$HEALTH_OK" = false ]; then
  error "Health check failed. Aborting."
  exit 1
fi

info "All services healthy."

# ── 7. Run Playwright Smoke Matrix ──────────────────────────────────────
SMOKE_EXIT_CODE=0

if [ "$SKIP_SMOKE" = true ]; then
  section "Smoke Tests (skipped)"
  info "--skip-smoke flag provided. Services are running."
  info "Dev API:   http://${DEV_API_HOST}:${DEV_API_PORT}"
  info "WebUI:     http://${WEBUI_HOST}:${WEBUI_PORT}"
else
  section "Smoke Tests (Phase 0E-03 + Phase 1G-02E)"

  info "Running Playwright smoke matrix..."
  info "Config: $WEBUI_DIR/playwright.config.ts"
  info "Specs:  $SMOKE_SPEC"
  info "       $TOOL_POLICY_SMOKE_SPEC"

  # Use npx from the WebUI dir so Playwright finds browsers,
  # but pass --config with absolute path for repo-root portability.
  # Run both smoke specs in sequence; capture overall exit code.
  if [ "$KEEP_RUNNING" = true ]; then
    # Keep services running — don't let trap cleanup run on normal exit
    (
      cd "$WEBUI_DIR"
      npx playwright test \
        --config "$WEBUI_DIR/playwright.config.ts" \
        "$SMOKE_SPEC" \
        "$TOOL_POLICY_SMOKE_SPEC"
    ) || SMOKE_EXIT_CODE=$?
  else
    (
      cd "$WEBUI_DIR"
      npx playwright test \
        --config "$WEBUI_DIR/playwright.config.ts" \
        "$SMOKE_SPEC" \
        "$TOOL_POLICY_SMOKE_SPEC"
    ) || SMOKE_EXIT_CODE=$?
  fi
fi

# ── 8. Report ────────────────────────────────────────────────────────────
section "Smoke Report"

echo "  Source root:      $REPO_ROOT"
echo "  HERMES_HOME:      $HERMES_HOME"
echo "  Dev API:          http://${DEV_API_HOST}:${DEV_API_PORT} (PID $API_PID)"
echo "  WebUI:            http://${WEBUI_HOST}:${WEBUI_PORT} (PID $WEBUI_PID)"
echo "  Skip smoke:       $SKIP_SMOKE"
echo "  Keep running:     $KEEP_RUNNING"

if [ "$SKIP_SMOKE" = true ]; then
  echo ""
  echo "  Result:           SERVICES_RUNNING (smoke skipped)"
elif [ "$SMOKE_EXIT_CODE" -eq 0 ]; then
  echo "  Smoke exit code:  $SMOKE_EXIT_CODE"
  echo ""
  echo "  Result:           PASS"
else
  echo "  Smoke exit code:  $SMOKE_EXIT_CODE"
  echo ""
  echo "  Result:           FAIL"
fi

# ── 9. Keep-running or cleanup ───────────────────────────────────────────
if [ "$KEEP_RUNNING" = true ]; then
  info "Services kept running (--keep-running)."
  info "Dev API:   http://${DEV_API_HOST}:${DEV_API_PORT} (PID $API_PID)"
  info "WebUI:     http://${WEBUI_HOST}:${WEBUI_PORT} (PID $WEBUI_PID)"
  info "Press Ctrl+C to stop, or run: kill $API_PID $WEBUI_PID"
  # Disable the EXIT trap so it doesn't clean up on script exit
  trap - EXIT INT TERM
  exit "$SMOKE_EXIT_CODE"
fi

# Normal exit — cleanup runs via trap
exit "$SMOKE_EXIT_CODE"
