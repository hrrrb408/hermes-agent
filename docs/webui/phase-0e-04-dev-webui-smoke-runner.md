# Phase 0E-04: Dev WebUI Smoke Runner

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 796dea9a1 (Phase 0E-03)

---

## 1. Problem

Running the Dev WebUI smoke tests (Phase 0E-03) requires manually starting two services in separate terminals:

```bash
# Terminal 1: Dev API
HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev python -m hermes_cli.main dev-webui-api

# Terminal 2: WebUI (must be in apps/hermes-dev-webui/)
cd apps/hermes-dev-webui && pnpm dev

# Terminal 3: Run smoke tests (from apps/hermes-dev-webui/)
cd apps/hermes-dev-webui && pnpm test:smoke:0e03
```

This three-terminal manual workflow is friction-heavy. A one-command smoke runner would:

1. Start both services automatically
2. Wait for both to become healthy
3. Run the Playwright smoke matrix
4. Clean up processes regardless of success or failure
5. Report clear results

---

## 2. Audit Result

### 2.1 Existing Startup Commands

| Service | Command | Default Host | Default Port |
|---------|---------|-------------|-------------|
| Dev API | `python -m hermes_cli.main dev-webui-api` | `127.0.0.1` | `5181` |
| WebUI | `pnpm dev` (from `apps/hermes-dev-webui/`) | `127.0.0.1` | `5180` |

Both already enforce `127.0.0.1` binding by default.

### 2.2 Smoke Test Commands

| Method | Command | Working Directory Required |
|--------|---------|---------------------------|
| From app dir | `pnpm test:smoke:0e03` | `apps/hermes-dev-webui/` |
| From repo root | `npx playwright test --config <path> <spec>` | Any |

The runner uses the app-dir approach (via subshell `cd`) for reliability.

### 2.3 Existing Runner Infrastructure

No existing smoke runner or service management scripts found in `scripts/`. The `run-dev-hermes.sh` script is a simple `exec` wrapper — no PID management, no cleanup, no background process handling.

---

## 3. Decision

**Decision:** Create `scripts/run-dev-webui-smoke.sh` — a one-shot smoke runner.

- Not a daemon — starts services, runs smoke, cleans up, exits
- Uses `trap cleanup EXIT INT TERM` for guaranteed cleanup
- Tracks only its own PIDs — never kills unknown processes
- Reports clear PASS/FAIL status

---

## 4. Runner Command

```bash
./scripts/run-dev-webui-smoke.sh              # Full smoke cycle (default)
./scripts/run-dev-webui-smoke.sh --skip-smoke # Start services only, skip tests
./scripts/run-dev-webui-smoke.sh --keep-running # Keep services after tests
./scripts/run-dev-webui-smoke.sh --help       # Show usage
```

---

## 5. Startup Behavior

1. **Environment safety check:** Validates HERMES_HOME is a dev home, not production
2. **Port check:** Verifies ports 5180 and 5181 are free; fails if occupied
3. **Prerequisites check:** Validates Python venv, pnpm, node_modules, Playwright, smoke spec
4. **Start Dev API:** Launches `python -m hermes_cli.main dev-webui-api` with HERMES_HOME set
5. **Start WebUI:** Launches `pnpm dev` in a subshell from `apps/hermes-dev-webui/`
6. **Health check:** Waits up to 30s for both services to respond
7. **Run smoke matrix:** Executes Playwright smoke tests via `npx playwright test`
8. **Cleanup:** Stops all started processes (trap on EXIT/INT/TERM)
9. **Report:** Prints clear PASS/FAIL result

---

## 6. Port Safety

- Runner checks both ports before starting
- If a port is occupied, runner prints the PID/command and **exits with code 1**
- Runner **never kills** processes it did not start
- After cleanup, runner warns if ports remain occupied but does not force-kill

---

## 7. Environment Safety

- `HERMES_HOME` defaults to `/Users/huangruibang/Code/hermes-home-dev`
- Validates: HERMES_HOME exists, is a directory, is not `~/.hermes`, is not inside `~/.hermes`
- Validates: repo root contains `hermes_cli/main.py`
- Fail-closed on any mismatch

---

## 8. Health Checks

| Service | Health URL | Method |
|---------|-----------|--------|
| Dev API | `http://127.0.0.1:5181/api/dev/v1/status` | HTTP GET 200 |
| WebUI | `http://127.0.0.1:5180` | HTTP GET 200 |

- Timeout: 30 seconds per service
- Retry interval: 1 second
- On failure: prints log tail and aborts

---

## 9. Smoke Execution

The runner runs the 0E-03 Playwright smoke matrix:

```bash
cd "$WEBUI_DIR" && npx playwright test \
  --config "$WEBUI_DIR/playwright.config.ts" \
  "$SMOKE_SPEC"
```

- 24 tests: 20 viewport×theme + 4 panel drill-down
- No screenshots, traces, videos, or HAR
- Runner exits with the Playwright exit code

---

## 10. Cleanup Behavior

```bash
trap cleanup EXIT INT TERM
```

Cleanup only kills PIDs tracked by the runner:

- **API_PID:** Direct Python process — `kill $API_PID`
- **WEBUI_PID:** Subshell — kills children via `pgrep -P`, then kills subshell

Cleanup does **NOT** kill:

- Production Gateway PID 1717
- Unknown processes on ports 5180/5181
- Dev Gateway
- Dashboard

After cleanup, runner verifies port release and warns (without killing) if ports remain occupied.

---

## 11. Failure Behavior

| Scenario | Behavior |
|----------|----------|
| Unsafe HERMES_HOME | Exit 1, no services started |
| Port occupied | Exit 1, prints occupier info, no kill |
| Health check timeout | Exit 1, prints log tail, cleanup runs |
| Smoke test failure | Exit non-zero, cleanup runs |
| Ctrl+C (SIGINT) | Trap triggers cleanup |
| SIGTERM | Trap triggers cleanup |

Cleanup always runs regardless of failure mode.

---

## 12. Side-Effect Validation

### Before Runner

| File | SHA-256 |
|------|---------|
| `state.db` | `6bccb704...` |
| `MEMORY.md` | `44be12a0...` |
| All memory files | Matched baseline |
| All review files | Matched baseline |

### After Runner

| File | SHA-256 | Changed? |
|------|---------|----------|
| `state.db` | `6bccb704...` | No |
| `MEMORY.md` | `44be12a0...` | No |
| All memory files | Matched baseline | No |
| All review files | Matched baseline | No |

**Conclusion:** Zero side-effects. The runner is read-only with respect to dev-home data.

---

## 13. Artifact Policy

| Artifact | Generated? | Committed? |
|----------|-----------|------------|
| Screenshots | No | No |
| Videos | No | No |
| Traces | No | No |
| HAR | No | No |
| playwright-report/ | No | No (gitignored) |
| test-results/ | No | No (gitignored) |
| Smoke logs | Written to `/tmp/`, auto-deleted on cleanup | No |
| dist/ | Not generated by runner | No (gitignored) |

---

## 14. Validation Result

| Metric | Value |
|--------|-------|
| Runner command | `./scripts/run-dev-webui-smoke.sh` |
| bash -n | PASS |
| Services started | Dev API (5181) + WebUI (5180) |
| Health check | Both ready in <2s |
| Smoke matrix | 24/24 passed in 49.6s |
| Cleanup | Both processes stopped, ports freed |
| Port-occupied test | Exit 1, no kill of holding process |
| Side-effects | state.db, MEMORY.md, memory files all unchanged |
| Production Gateway | PID 1717 untouched |

---

## 15. Files Created/Modified

| File | Action |
|------|--------|
| `scripts/run-dev-webui-smoke.sh` | New — Smoke runner script |
| `docs/webui/phase-0e-04-dev-webui-smoke-runner.md` | New — This document |
| `docs/webui/phase-0e-implementation-plan.md` | Modified — Mark 0E-04 as completed |
| `docs/webui/phase-0e-00-governance-scope.md` | Modified — Add 0E-04 result summary |
| `apps/hermes-dev-webui/pnpm-lock.yaml` | Modified — Updated by `pnpm install` |

---

## 16. How to Run

```bash
# From repo root:
./scripts/run-dev-webui-smoke.sh

# Or with options:
./scripts/run-dev-webui-smoke.sh --skip-smoke     # Start services only
./scripts/run-dev-webui-smoke.sh --keep-running   # Keep services after tests
```

The runner can be invoked from any directory — it auto-locates the repo root.

---

## 17. Non-goals

- Not a daemon or long-running service
- No PID file persistence
- No auto-restart
- No log file management beyond `/tmp/` auto-cleanup
- No system service integration (launchd/systemd)
- No CI integration (local execution only)
- No port auto-switching

---

## 18. Follow-up

- **0E-05:** dev-check Enhancement — add WebUI-specific checks
- **0E-03 update:** Runner now provides repo-root execution entry for the smoke matrix
