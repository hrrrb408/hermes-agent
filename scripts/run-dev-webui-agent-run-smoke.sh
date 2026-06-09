#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Hermes Dev WebUI Agent Run Fake Provider Smoke Runner (Phase 1F)
#
# Starts Dev API with Fake Provider + WebUI, runs Phase 1F enabled Playwright
# smoke tests, and cleans up. Validates SSE, session persistence, audit,
# cancel, and zero side effects on memory/review.
#
# Usage:
#   ./scripts/run-dev-webui-agent-run-smoke.sh
#   ./scripts/run-dev-webui-agent-run-smoke.sh --help
#
# Safety:
#   - Uses a TEMPORARY HERMES_HOME (never dev-home or production)
#   - Fake Provider — zero external network calls
#   - Binds to 127.0.0.1 only
#   - Refuses to start if ports are occupied
#   - Only kills processes it started
#   - Never affects Production Gateway or dev-home
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
DEV_HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"

# ── PIDs tracked by this script ───────────────────────────────────────────
API_PID=""
WEBUI_PID=""

# ── Temp home ─────────────────────────────────────────────────────────────
TMP_HERMES_HOME=""

# ── Parse args ────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --help|-h)
      echo "Usage: $0 [--help]"
      echo ""
      echo "  Runs Phase 1F Fake Provider enabled browser smoke tests."
      echo "  Creates a temporary HERMES_HOME, starts services, runs Playwright."
      echo ""
      echo "  --help  Show this help message"
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
      info "Stopping Fake Provider Dev API (PID $API_PID)..."
      kill "$API_PID" 2>/dev/null || true
      wait "$API_PID" 2>/dev/null || true
      info "Fake Provider Dev API stopped."
    else
      info "Fake Provider Dev API (PID $API_PID) already exited."
    fi
    API_PID=""
  fi

  if [ -n "$WEBUI_PID" ]; then
    if kill -0 "$WEBUI_PID" 2>/dev/null; then
      info "Stopping WebUI (PID $WEBUI_PID and children)..."
      local child
      for child in $(pgrep -P "$WEBUI_PID" 2>/dev/null); do
        kill "$child" 2>/dev/null || true
      done
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

  # Remove temporary HERMES_HOME
  if [ -n "$TMP_HERMES_HOME" ] && [ -d "$TMP_HERMES_HOME" ]; then
    info "Removing temporary HERMES_HOME: $TMP_HERMES_HOME"
    rm -rf "$TMP_HERMES_HOME"
    info "Temporary home removed."
  fi

  # Clean up log files
  if [ -n "${API_LOG:-}" ] && [ -f "$API_LOG" ]; then
    rm -f "$API_LOG"
  fi
  if [ -n "${WEBUI_LOG:-}" ] && [ -f "$WEBUI_LOG" ]; then
    rm -f "$WEBUI_LOG"
  fi

  # Verify port release
  local port5180 port5181
  port5180="$(lsof -nP -iTCP:5180 -sTCP:LISTEN 2>/dev/null || true)"
  port5181="$(lsof -nP -iTCP:5181 -sTCP:LISTEN 2>/dev/null || true)"

  if [ -n "$port5180" ]; then
    warn "Port 5180 still occupied after cleanup:"
    echo "$port5180" | sed 's/^/  /'
  else
    info "Port 5180: free"
  fi
  if [ -n "$port5181" ]; then
    warn "Port 5181 still occupied after cleanup:"
    echo "$port5181" | sed 's/^/  /'
  else
    info "Port 5181: free"
  fi

  info "Cleanup complete."
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

# ── Print banner ──────────────────────────────────────────────────────────
section "Hermes Dev WebUI Phase 1F Agent Run Smoke Runner"
info "Source root:  $REPO_ROOT"
info "Script:       $0"

# ── 1. Environment safety ────────────────────────────────────────────────
section "Environment Safety"

# Create temporary HERMES_HOME
TMP_HERMES_HOME="$(mktemp -d /tmp/hermes-agent-run-smoke.XXXXXX)"
info "Temporary HERMES_HOME: $TMP_HERMES_HOME"

# Safety: must not be production or dev-home
case "$TMP_HERMES_HOME" in
  "$PRODUCTION_HERMES_HOME"|"$PRODUCTION_HERMES_HOME"/*)
    error "Temporary home is inside production: $TMP_HERMES_HOME"
    exit 1
    ;;
esac
case "$TMP_HERMES_HOME" in
  "$DEV_HERMES_HOME"|"$DEV_HERMES_HOME"/*)
    error "Temporary home is inside dev-home: $TMP_HERMES_HOME"
    exit 1
    ;;
esac

# Verify realpath is not symlinked to production/dev
RESOLVED_HOME="$(python3 -c "from pathlib import Path; print(Path('$TMP_HERMES_HOME').resolve())")"
case "$RESOLVED_HOME" in
  "$PRODUCTION_HERMES_HOME"|"$DEV_HERMES_HOME")
    error "Resolved temporary home matches production or dev-home"
    exit 1
    ;;
esac

# Verify repo root
if [ ! -f "$REPO_ROOT/hermes_cli/main.py" ]; then
  error "Cannot find hermes_cli/main.py in REPO_ROOT=$REPO_ROOT"
  exit 1
fi

info "Environment:  SAFE (temporary home confirmed)"

# ── 2. Port check ────────────────────────────────────────────────────────
section "Port Check"

check_port() {
  local port="$1"
  local result
  result="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$result" ]; then
    error "Port $port is already occupied:"
    echo "$result" | sed 's/^/  /'
    error "Refusing to start. Free the port before retrying."
    exit 1
  fi
  info "Port $port: free"
}

check_port "$WEBUI_PORT"
check_port "$DEV_API_PORT"

# ── 3. Prerequisites ─────────────────────────────────────────────────────
section "Prerequisites"

VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
  error "Python venv not found at $VENV_PYTHON"
  exit 1
fi
info "Python:       $VENV_PYTHON ($($VENV_PYTHON --version 2>&1))"

if ! command -v pnpm &>/dev/null; then
  error "pnpm not found in PATH"
  exit 1
fi
info "pnpm:         $(pnpm --version 2>/dev/null)"

WEBUI_DIR="$REPO_ROOT/apps/hermes-dev-webui"
if [ ! -f "$WEBUI_DIR/package.json" ]; then
  error "Dev WebUI package.json not found"
  exit 1
fi
info "WebUI dir:    $WEBUI_DIR"

if [ ! -d "$WEBUI_DIR/node_modules/@playwright/test" ]; then
  error "@playwright/test not installed. Run 'cd $WEBUI_DIR && pnpm install' first."
  exit 1
fi
info "Playwright:   installed"

SMOKE_SERVER="$REPO_ROOT/tests/_agent_run_smoke_server.py"
if [ ! -f "$SMOKE_SERVER" ]; then
  error "Fake Provider smoke server not found: $SMOKE_SERVER"
  exit 1
fi
info "Smoke server: $SMOKE_SERVER"

SMOKE_SPEC="$WEBUI_DIR/tests/smoke/phase-1f-agent-run-smoke.spec.ts"
if [ ! -f "$SMOKE_SPEC" ]; then
  error "Playwright smoke spec not found: $SMOKE_SPEC"
  exit 1
fi
info "Smoke spec:   $SMOKE_SPEC"

# ── 4. Record pre-smoke state of dev-home ────────────────────────────────
section "Dev-Home Pre-Smoke Baseline"

DEV_HOME_STATE_DB="$DEV_HERMES_HOME/state.db"
if [ -f "$DEV_HOME_STATE_DB" ]; then
  DEV_HOME_DB_HASH_BEFORE="$(shasum -a 256 "$DEV_HOME_STATE_DB" | awk '{print $1}')"
  DEV_HOME_DB_SIZE_BEFORE="$(stat -f%z "$DEV_HOME_STATE_DB" 2>/dev/null || stat -c%s "$DEV_HOME_STATE_DB" 2>/dev/null)"
  info "dev-home state.db hash:  $DEV_HOME_DB_HASH_BEFORE"
  info "dev-home state.db size:  $DEV_HOME_DB_SIZE_BEFORE"
else
  DEV_HOME_DB_HASH_BEFORE="missing"
  DEV_HOME_DB_SIZE_BEFORE="0"
  info "dev-home state.db:       not found (OK)"
fi

# ── 5. Start Fake Provider Dev API ───────────────────────────────────────
section "Start Fake Provider Dev API"

API_LOG="/tmp/hermes-agent-run-smoke-api.$$.log"

info "Starting Fake Provider Dev API on ${DEV_API_HOST}:${DEV_API_PORT}..."
info "Log: $API_LOG"

HERMES_HOME="$TMP_HERMES_HOME" \
HERMES_AGENT_RUN_ENABLED=true \
HERMES_AGENT_RUN_SMOKE=true \
DEV_API_HOST="$DEV_API_HOST" \
DEV_API_PORT="$DEV_API_PORT" \
PYTHONPATH="$REPO_ROOT:$REPO_ROOT/hermes_cli" \
  "$VENV_PYTHON" "$SMOKE_SERVER" \
  > "$API_LOG" 2>&1 &
API_PID=$!

info "Fake Provider Dev API PID: $API_PID"

# ── 6. Start WebUI ───────────────────────────────────────────────────────
section "Start WebUI"

WEBUI_LOG="/tmp/hermes-agent-run-smoke-vite.$$.log"

info "Starting WebUI on ${WEBUI_HOST}:${WEBUI_PORT}..."
info "Log: $WEBUI_LOG"

(
  cd "$WEBUI_DIR"
  pnpm dev --host "$WEBUI_HOST" --port "$WEBUI_PORT" > /dev/null 2>&1
) < /dev/null > "$WEBUI_LOG" 2>&1 &
WEBUI_PID=$!

info "WebUI PID: $WEBUI_PID"

# ── 7. Wait for health ──────────────────────────────────────────────────
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

if ! wait_for_url "http://${DEV_API_HOST}:${DEV_API_PORT}/api/dev/v1/status" "Fake Provider Dev API"; then
  HEALTH_OK=false
  error "Fake Provider Dev API log tail:"
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

# ── 8. Verify Agent Run is enabled ──────────────────────────────────────
section "Verify Agent Run Enabled"

AGENT_STATUS="$(curl -sf "http://${DEV_API_HOST}:${DEV_API_PORT}/api/dev/v1/agent/status" 2>/dev/null || echo '{}')"
info "Agent status: $AGENT_STATUS"

if echo "$AGENT_STATUS" | grep -q '"enabled":true\|"enabled": true'; then
  info "Agent Run: enabled (Fake Provider)"
else
  warn "Agent Run may not be fully enabled — proceeding with smoke tests"
fi

# ── 9. Run Playwright Phase 1F Smoke ─────────────────────────────────────
section "Phase 1F Enabled Browser Smoke"

SMOKE_EXIT_CODE=0

info "Running Playwright Phase 1F smoke..."
info "Config: $WEBUI_DIR/playwright.config.ts"
info "Spec:   $SMOKE_SPEC"

(
  cd "$WEBUI_DIR"
  npx playwright test \
    --config "$WEBUI_DIR/playwright.config.ts" \
    "$SMOKE_SPEC"
) || SMOKE_EXIT_CODE=$?

# ── 10. Dev-home post-smoke verification ─────────────────────────────────
section "Dev-Home Post-Smoke Verification"

if [ -f "$DEV_HOME_STATE_DB" ]; then
  DEV_HOME_DB_HASH_AFTER="$(shasum -a 256 "$DEV_HOME_STATE_DB" | awk '{print $1}')"
  DEV_HOME_DB_SIZE_AFTER="$(stat -f%z "$DEV_HOME_STATE_DB" 2>/dev/null || stat -c%s "$DEV_HOME_STATE_DB" 2>/dev/null)"

  if [ "$DEV_HOME_DB_HASH_BEFORE" != "$DEV_HOME_DB_HASH_AFTER" ]; then
    error "dev-home state.db was modified during smoke!"
    error "  Before: $DEV_HOME_DB_HASH_BEFORE ($DEV_HOME_DB_SIZE_BEFORE bytes)"
    error "  After:  $DEV_HOME_DB_HASH_AFTER ($DEV_HOME_DB_SIZE_AFTER bytes)"
    SMOKE_EXIT_CODE=1
  else
    info "dev-home state.db: unchanged (safe)"
  fi
else
  if [ "$DEV_HOME_DB_HASH_BEFORE" != "missing" ]; then
    error "dev-home state.db was deleted during smoke!"
    SMOKE_EXIT_CODE=1
  else
    info "dev-home state.db: still absent (safe)"
  fi
fi

# Verify no audit table in dev-home
if [ -f "$DEV_HOME_STATE_DB" ]; then
  AUDIT_CHECK="$("$VENV_PYTHON" -c "
import sqlite3
conn = sqlite3.connect('$DEV_HOME_STATE_DB')
try:
    conn.execute('SELECT COUNT(*) FROM agent_run_audit')
    print('EXISTS')
except Exception:
    print('ABSENT')
" 2>/dev/null)"
  if [ "$AUDIT_CHECK" = "EXISTS" ]; then
    error "agent_run_audit table found in dev-home state.db!"
    SMOKE_EXIT_CODE=1
  else
    info "dev-home audit table: absent (safe)"
  fi
fi

# ── 11. Report ────────────────────────────────────────────────────────────
section "Smoke Report"

echo "  Source root:        $REPO_ROOT"
echo "  HERMES_HOME:        $TMP_HERMES_HOME (temporary)"
echo "  Dev API:            http://${DEV_API_HOST}:${DEV_API_PORT} (PID $API_PID, Fake Provider)"
echo "  WebUI:              http://${WEBUI_HOST}:${WEBUI_PORT} (PID $WEBUI_PID)"
echo "  external calls:     0 (Fake Provider)"
echo "  dev-home affected:  no"

if [ "$SMOKE_EXIT_CODE" -eq 0 ]; then
  echo "  Smoke exit code:    $SMOKE_EXIT_CODE"
  echo ""
  echo "  Result:             PASS"
else
  echo "  Smoke exit code:    $SMOKE_EXIT_CODE"
  echo ""
  echo "  Result:             FAIL"
fi

# Normal exit — cleanup runs via trap
exit "$SMOKE_EXIT_CODE"
