# Phase 0E Implementation Plan

**Date:** 2026-06-08
**Status:** Phase 0E-00, 0E-01 completed; 0E-02 through 0E-Release not started
**Depends on:** Phase 0D final closure (279e27259)
**Governance scope:** `docs/webui/phase-0e-00-governance-scope.md`

---

## Overview

Phase 0E is an engineering governance phase. It resolves build artifact hygiene, test automation gaps, developer experience tooling, and Phase 1 safety prerequisites. No new business functionality is introduced.

---

## Phase 0E-00: Governance Scope & Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-08

### Deliverables

- `docs/webui/phase-0e-00-governance-scope.md` — Governance scope document with issue inventory, decision matrix, subphase plan
- `docs/webui/phase-0e-implementation-plan.md` — This document
- Updated `docs/webui/phase-0d-final-closure.md` — Next phase pointer

### Acceptance

- ✅ Repository state verified (branch, HEAD, remote sync)
- ✅ Environment checks passed (memory-check PASS, dev-check WARN)
- ✅ Engineering governance issues identified (8 issues: E-01 through E-08)
- ✅ Phase 0E subphases frozen (0E-01 through 0E-Release)
- ✅ No code changes
- ✅ Production environment unaffected

---

## Phase 0E-01: Build Artifact Policy — Completed ✅

**Priority:** P2
**Estimated scope:** Small (`.gitignore` + `git rm --cached` + verification)
**Date:** 2026-06-08

### Goal

Remove `dist/` and `tsconfig.app.tsbuildinfo` from Git tracking for the Dev WebUI and add them to `.gitignore`.

### Context

Currently tracked (before 0E-01):
```
apps/hermes-dev-webui/dist/assets/index-AxamzU0w.js
apps/hermes-dev-webui/dist/assets/index-CCl_6OPG.css
apps/hermes-dev-webui/dist/index.html
apps/hermes-dev-webui/tsconfig.app.tsbuildinfo
apps/hermes-dev-webui/tsconfig.node.tsbuildinfo
```

All 5 files removed from Git tracking via `git rm --cached`. `.gitignore` updated with precise rules.

The `.gitignore` already has patterns for `apps/desktop/dist/`, `apps/desktop/*.tsbuildinfo`, and `hermes_cli/web_dist/` but NOT for `apps/hermes-dev-webui/`.

### Modification Scope

| File | Action |
|------|--------|
| `.gitignore` | **Modify** — Add `apps/hermes-dev-webui/dist/` and `apps/hermes-dev-webui/*.tsbuildinfo` |
| `apps/hermes-dev-webui/dist/*` | `git rm --cached` (4 files) |
| `apps/hermes-dev-webui/tsconfig.app.tsbuildinfo` | `git rm --cached` (1 file) |

### Non-goals

- No changes to `apps/desktop/` or other workspace build artifacts
- No changes to frontend or backend source code
- No changes to build process or Vite configuration
- No local `.gitignore` file creation (root `.gitignore` is sufficient)

### Risks

- **Low:** If any process depends on dist being tracked, it will break. Current architecture uses Vite dev server; no static serving from dist.
- **Low:** `git rm --cached` will delete dist from the repo on next checkout. This is intentional — dist is a build artifact.

### Acceptance Criteria

1. ✅ `git ls-files apps/hermes-dev-webui/dist` returns empty
2. ✅ `git ls-files apps/hermes-dev-webui/tsconfig.app.tsbuildinfo` returns empty
3. ✅ `pnpm build` produces dist locally without `git status` showing changes
4. ✅ `dev-check` does not report build artifact issues
5. ✅ All existing tests still pass (324 frontend tests, 0 failures)

### Dependencies

- None (can start immediately after 0E-00)

### Push

Only after 0E-Release verification.

---

## Phase 0E-02: Visual Review Artifact Policy — Not Started

**Priority:** P2
**Estimated scope:** Small (`.gitignore` entry + optional dev-check allowlist)

### Goal

Add `apps/hermes-dev-webui/visual-review/` to `.gitignore` so that `dev-check` no longer reports WARN for the 5 pre-existing directories.

### Context

5 directories exist:
```
apps/hermes-dev-webui/visual-review/phase-0b/
apps/hermes-dev-webui/visual-review/phase-0b-1/
apps/hermes-dev-webui/visual-review/phase-0b-1-1/
apps/hermes-dev-webui/visual-review/phase-0b-1-2/
apps/hermes-dev-webui/visual-review/phase-0b-1-3/
```

These must NOT be deleted. They are local human visual review artifacts.

### Modification Scope

| File | Action |
|------|--------|
| `.gitignore` | **Modify** — Add `apps/hermes-dev-webui/visual-review/` |
| `hermes_cli/main.py` | **Optional** — Add known-whitelist detection to `cmd_dev_check()` so untracked visual-review dirs don't trigger WARN |

### Non-goals

- Do not delete existing visual-review directories
- Do not migrate or archive them
- Do not create new review directories

### Acceptance Criteria

1. `git status` no longer shows visual-review directories
2. `dev-check` reports PASS for Git worktree (or WARN only with clear "known whitelisted paths" message)
3. Existing directories still exist on disk
4. All existing tests still pass

### Dependencies

- None (can start immediately; independent of 0E-01)

### Push

Only after 0E-Release verification.

---

## Phase 0E-03: Playwright Smoke Matrix — Not Started

**Priority:** P2
**Estimated scope:** Medium (new test infrastructure + 20 test cases)

### Goal

Create a lightweight Playwright test script that validates all 5 themes render correctly at key viewports.

### Context

- No `playwright.config.*` exists
- No `@playwright/test` in `package.json`
- Manual spot-checking done in 0C/0D
- Target: 4 viewports × 5 themes = 20 combinations

### Modification Scope

| File | Action |
|------|--------|
| `apps/hermes-dev-webui/package.json` | **Modify** — Add `@playwright/test` to devDependencies |
| `apps/hermes-dev-webui/playwright.config.ts` | **New** — Playwright configuration |
| `apps/hermes-dev-webui/e2e/smoke.spec.ts` | **New** — 20 viewport × theme smoke tests |
| `.gitignore` | **Modify** — Add Playwright artifacts (`test-results/`, `playwright-report/`) |

### Non-goals

- No screenshot saving by default
- No visual regression baseline
- No CI integration (local execution only)
- No real Agent required (uses Vite dev server only)
- No test video/trace recording

### Test Requirements

For each of 20 viewport × theme combinations:
- Page loads without JavaScript errors
- `data-theme` attribute matches expected theme ID
- `color-scheme` matches theme's light/dark setting
- Key CSS variables are set (`--color-app-bg`, `--color-text-primary`, `--color-accent`)
- No horizontal overflow

Viewports:
- Mobile: 640×800
- Tablet: 768×1024
- Desktop: 1280×900
- Wide: 1440×900

### Acceptance Criteria

1. `pnpm exec playwright test` runs and reports pass/fail for 20 combinations
2. No screenshots or traces saved by default
3. Test completes in under 60 seconds
4. All existing tests still pass

### Risks

- **Low:** Playwright installation may require system dependencies
- **Low:** Tests require running Vite dev server — need setup/teardown in test config

### Dependencies

- Requires Vite dev server to be running (or auto-started by Playwright config)
- Can start after 0E-01 (so that build artifact tracking is clean)

### Push

Only after 0E-Release verification.

---

## Phase 0E-04: Dev WebUI Smoke Runner — Not Started

**Priority:** P3
**Estimated scope:** Medium (new script with start/status/stop)

### Goal

Create `scripts/run-dev-webui.sh` that starts both Dev API and WebUI dev server with correct environment.

### Context

Currently requires two manual commands:
```bash
# Terminal 1: Dev API
HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev python -m hermes_cli.main dev-webui-api

# Terminal 2: WebUI
cd apps/hermes-dev-webui && pnpm dev
```

### Modification Scope

| File | Action |
|------|--------|
| `scripts/run-dev-webui.sh` | **New** — Smoke runner with start/status/stop |

### Non-goals

- Not a daemon or service manager
- No auto-restart on crash
- No log file management
- No PID file persistence across reboots
- No system service integration

### Script Design

```
./scripts/run-dev-webui.sh start   # Start both Dev API and WebUI
./scripts/run-dev-webui.sh status  # Check if both are running
./scripts/run-dev-webui.sh stop    # Stop both
```

Safety:
- Enforces `HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev`
- Enforces `127.0.0.1` binding
- Refuses to start if ports are occupied
- Cleans up child processes on stop

### Acceptance Criteria

1. `start` launches both processes; both report healthy
2. `status` shows both running with PIDs
3. `stop` terminates both cleanly (no orphan processes)
4. Refuses to start if 5180 or 5181 is occupied
5. Does not affect production Gateway
6. All existing tests still pass

### Dependencies

- None (can start immediately; independent of other subphases)

### Push

Only after 0E-Release verification.

---

## Phase 0E-05: dev-check Enhancement — Not Started

**Priority:** P3
**Estimated scope:** Medium (add WebUI-specific checks to existing function)

### Goal

Add Dev WebUI-specific checks to `cmd_dev_check()` in `hermes_cli/main.py`.

### Context

Current `dev-check` checks Hermes dev environment integrity but has no awareness of the Dev WebUI subsystem. It does not verify:
- Dev API module existence
- OpenAPI spec validity
- Route count (11 business routes expected)
- Forbidden routes not registered
- Build artifact dirtiness
- Visual-review whitelist

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/main.py` | **Modify** — Add WebUI-specific checks to `cmd_dev_check()` |

### Proposed Checks

| Check | Type | Description |
|-------|------|-------------|
| Dev API module | PASS/FAIL | `hermes_cli/dev_web_api.py` exists and is importable |
| Dev WebUI package | PASS/FAIL | `apps/hermes-dev-webui/package.json` exists |
| OpenAPI spec | PASS/FAIL | `docs/webui/openapi/dev-web-api-v1.yaml` exists and is valid YAML |
| Build artifacts | PASS/WARN | dist/ and tsbuildinfo not tracked or not dirty |
| Visual-review whitelist | PASS/WARN | untracked visual-review dirs are known whitelisted |
| WebUI deps installed | PASS/WARN | `apps/hermes-dev-webui/node_modules` exists |

### Non-goals

- No network requests (no service startup)
- No file content hashing (keep fast)
- No modification to production checks
- No new CLI commands

### Acceptance Criteria

1. `dev-check` reports 4–6 new WebUI-specific checks
2. All existing checks still pass
3. New checks complete in under 2 seconds total
4. `dev-check` result remains PASS (or WARN for known visual-review dirs only)
5. All existing tests still pass

### Dependencies

- Preferably after 0E-01 and 0E-02 (so expected states are defined)

### Push

Only after 0E-Release verification.

---

## Phase 0E-06: Phase 1 Safety Boundary Draft — Not Started

**Priority:** P1
**Estimated scope:** Medium (documentation only, no code)

### Goal

Draft the safety principles and prerequisites document for Phase 1, which will introduce write operations.

### Context

Phase 0C/0D established a strong read-only boundary. Phase 1 will need to introduce:
- Agent conversation (SSE streaming)
- Session creation
- Message sending
- Potentially tool execution and Memory writes

Without documented safety principles, there is risk of introducing write operations without adequate safeguards.

### Modification Scope

| File | Action |
|------|--------|
| `docs/webui/phase-1-safety-boundary.md` | **New** — Safety principles document |

### Proposed Principles

1. **Default deny:** All write operations disabled until explicitly enabled per-phase
2. **Dry-run first:** Every write operation must have a dry-run mode that validates without mutating
3. **Allowlist enforcement:** All mutations must go through a verified allowlist, not a denylist
4. **Production isolation verification:** Before and after every write phase, verify `~/.hermes` is untouched
5. **Dual confirmation:** Browser + CLI confirmation for destructive operations
6. **Incremental enablement:** Each write capability is its own phase with independent acceptance criteria
7. **No SSE before Agent Run:** Streaming must not be introduced before Agent Run is complete and tested
8. **No automatic memory operations:** Memory write/update/archive remain disabled in WebUI

### Non-goals

- No code changes
- No Phase 1 implementation
- No commitment to Phase 1 timeline
- No API route design

### Acceptance Criteria

1. Document exists at `docs/webui/phase-1-safety-boundary.md`
2. All 8 proposed principles are documented with rationale
3. Phase 1 candidate capabilities are listed with prerequisites
4. Document reviewed and acknowledged by user

### Dependencies

- None (can start immediately; documentation only)

### Push

Only after 0E-Release verification.

---

## Phase 0E-Release: Final Verification & Push — Not Started

**Priority:** P0 (release gate)
**Estimated scope:** Small (verification only)

### Goal

Run full quality gate, verify clean working tree, and push all Phase 0E commits to `origin/dev-huangruibang`.

### Verification Checklist

1. `memory-check` — PASS
2. `dev-check` — PASS (no WARN except known items)
3. `python -m compileall hermes_cli hermes_state.py agent` — PASS
4. `pnpm --filter @hermes/dev-webui test` — PASS
5. `./scripts/run_tests.sh` — PASS
6. `git status --short --branch` — Clean (only visual-review dirs)
7. `git log --oneline -10` — All 0E commits present
8. Production Gateway PID 1717 still running

### Acceptance Criteria

1. All quality gates pass
2. Working tree has no unexpected changes
3. Production environment is unchanged
4. All Phase 0E commits are on `dev-huangruibang`
5. Successfully pushed to `origin/dev-huangruibang`

### Dependencies

- All other Phase 0E subphases completed

---

## Summary Timeline

| Phase | Goal | Status | Dependencies |
|-------|------|--------|-------------|
| 0E-00 | Governance scope & freeze | ✅ Completed | None |
| 0E-01 | Build artifact policy | ✅ Completed | None |
| 0E-02 | Visual review artifact policy | Not started | None |
| 0E-03 | Playwright smoke matrix | Not started | 0E-01 preferred |
| 0E-04 | Dev WebUI smoke runner | Not started | None |
| 0E-05 | dev-check enhancement | Not started | 0E-01, 0E-02 preferred |
| 0E-06 | Phase 1 safety boundary | Not started | None |
| 0E-Release | Final verification & push | Not started | All above |

---

## Dependency Graph

```
0E-00 ✅
├── 0E-01 ✅ (no deps)
├── 0E-02 (no deps)
├── 0E-03 (prefers 0E-01)
├── 0E-04 (no deps)
├── 0E-05 (prefers 0E-01 + 0E-02)
├── 0E-06 (no deps)
└── 0E-Release (requires all)
```

0E-01, 0E-02, 0E-04, and 0E-06 have no dependencies and can be executed in any order. 0E-03 prefers 0E-01 completion. 0E-05 prefers 0E-01 and 0E-02 completion so that expected states are defined. 0E-Release requires all subphases.

---

## Phase 0E Closure

**Phase 0E is NOT yet started (beyond 0E-00 scope freeze).**

See individual subphase sections for status.
