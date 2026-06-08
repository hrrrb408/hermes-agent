# Phase 0E Implementation Plan

**Date:** 2026-06-08
**Status:** Phase 0E-00 through 0E-06 completed; 0E-Release not started
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

## Phase 0E-02: Visual Review Artifact Policy — Completed ✅

**Status:** Completed
**Priority:** P2
**Estimated scope:** Small (`.gitignore` entry + optional dev-check allowlist)
**Date:** 2026-06-08

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

1. ✅ `git status` no longer shows visual-review directories
2. ✅ `dev-check` reports PASS for Git worktree (Plan A sufficient, no dev-check code changes needed)
3. ✅ Existing directories still exist on disk
4. ✅ 0E-01 build artifact rules remain effective
5. ✅ No dev-check code changes required

### Dependencies

- None (can start immediately; independent of 0E-01)

### Push

Only after 0E-Release verification.

---

## Phase 0E-03: Playwright Smoke Matrix — Completed ✅

**Status:** Completed
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

For each of 20 viewport × theme combinations + 4 panel drill-downs (24 total):
- Page loads without JavaScript errors
- `data-theme` attribute matches expected theme ID
- `color-scheme` matches theme's light/dark setting
- Key CSS variables are set (`--color-app-bg`, `--color-text-primary`, `--color-accent`)
- No horizontal overflow
- No forbidden network requests (5182, localhost, 0.0.0.0, write endpoints, reviews, agent/run)
- Console errors = 0, CORS errors = 0, asset 404 = 0
- Read-only UI enforced (Send/Attach disabled, "Read only" visible)
- No raw filesystem paths in page text

Viewports:
- 1440×900 (wide-screen)
- 1280×800 (standard desktop)
- 1024×768 (compressed desktop)
- 768×900 (tablet/narrow)

### Acceptance Criteria

1. ✅ `npx playwright test` runs and reports pass/fail for 24 tests (20 theme + 4 drill-down)
2. ✅ No screenshots or traces saved by default
3. ✅ Test completes in under 60 seconds (49.8s actual)
4. ✅ All existing tests still pass (324 unit tests)
5. ✅ No side-effects on state.db, MEMORY.md, or memory files

### Risks

- **Low:** Playwright installation may require system dependencies
- **Low:** Tests require running Vite dev server — need setup/teardown in test config

### Dependencies

- Requires Vite dev server to be running (or auto-started by Playwright config)
- Can start after 0E-01 (so that build artifact tracking is clean)

### Push

Only after 0E-Release verification.

---

## Phase 0E-04: Dev WebUI Smoke Runner — Completed ✅

**Status:** Completed
**Priority:** P3
**Estimated scope:** Medium (new script with start/status/stop)
**Date:** 2026-06-08

### Goal

Create `scripts/run-dev-webui-smoke.sh` that starts both Dev API and WebUI dev server, waits for health, runs the 0E-03 Playwright smoke matrix, and cleans up.

### Modification Scope

| File | Action |
|------|--------|
| `scripts/run-dev-webui-smoke.sh` | **New** — One-shot smoke runner |
| `apps/hermes-dev-webui/pnpm-lock.yaml` | **Modified** — Updated by `pnpm install` |

### Runner Design

```
./scripts/run-dev-webui-smoke.sh              # Full smoke cycle
./scripts/run-dev-webui-smoke.sh --skip-smoke # Start services only
./scripts/run-dev-webui-smoke.sh --keep-running # Keep services after tests
```

Safety:
- Enforces `HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev`
- Enforces `127.0.0.1` binding (ports 5180, 5181)
- Refuses to start if ports are occupied
- Only kills processes it started (via tracked PIDs + pgrep children)
- Cleans up on EXIT/INT/TERM via trap
- Never kills unknown processes or Production Gateway

### Acceptance Criteria

1. ✅ Runner starts Dev API on 127.0.0.1:5181
2. ✅ Runner starts WebUI on 127.0.0.1:5180
3. ✅ Health checks pass for both services
4. ✅ Playwright smoke matrix runs (24/24 passed in 49.6s)
5. ✅ Cleanup stops all started processes, ports freed
6. ✅ Port-occupied scenario: fail-closed, no kill of holding process
7. ✅ Zero side-effects on state.db, MEMORY.md, memory files
8. ✅ Does not affect Production Gateway PID 1717
9. ✅ All existing tests still pass (324 frontend tests)

### Validation

| Check | Result |
|-------|--------|
| bash -n | PASS |
| Full smoke run | 24/24 passed, 49.6s |
| Port-occupied fail-closed | Exit 1, no kill |
| Side-effect validation | All checksums unchanged |
| pnpm lint | PASS |
| pnpm type-check | PASS |
| pnpm test | 324/324 PASS |
| pnpm build | PASS (artifacts gitignored) |
| memory-check | PASS |
| dev-check | WARN (uncommitted files — expected) |
| compileall | PASS |

### Dependencies

- None (can start immediately; independent of other subphases)

### Push

Only after 0E-Release verification.

---

## Phase 0E-05: dev-check Enhancement — Completed ✅

**Priority:** P3
**Estimated scope:** Medium (add WebUI-specific checks to existing function)
**Date:** 2026-06-08

### Goal

Add Dev WebUI-specific checks to `cmd_dev_check()` in `hermes_cli/main.py`.

### Context

Current `dev-check` checks Hermes dev environment integrity but has no awareness of the Dev WebUI subsystem. It did not verify:
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
| `tests/test_dev_check_webui.py` | **New** — 17 unit tests + 5 integration tests |

### Implemented Checks (15 total)

| Check | Label | Type |
|-------|-------|------|
| WebUI app directory | `WebUI app` | PASS/FAIL |
| package.json | `WebUI package` | PASS/FAIL |
| Build artifact ignore | `Build artifacts` | PASS/FAIL |
| Visual-review ignore | `Visual review` | PASS/FAIL |
| Playwright artifact ignore | `Playwright artifacts` | PASS/FAIL |
| Playwright config | `Playwright config` | PASS/FAIL |
| Smoke spec | `Smoke spec` | PASS/FAIL |
| Smoke runner | `Smoke runner` | PASS/FAIL |
| test:smoke script | `Smoke script` | PASS/FAIL |
| test:smoke:0e03 script | `Smoke 0e03 script` | PASS/WARN |
| OpenAPI path count | `OpenAPI paths` | PASS/FAIL |
| OpenAPI route presence | `OpenAPI routes` | PASS/FAIL |
| Forbidden routes | `Forbidden routes` | PASS/FAIL |
| Dev Web API module | `Dev Web API module` | PASS/FAIL |
| WebUI section marker | `WebUI section` | PASS |

### Non-goals

- No network requests (no service startup)
- No file content hashing (keep fast)
- No modification to production checks
- No new CLI commands

### Acceptance Criteria

1. ✅ `dev-check` reports 15 new WebUI-specific checks
2. ✅ All existing checks still pass
3. ✅ New checks complete in under 2 seconds total
4. ✅ `dev-check` result remains PASS (WARN only for uncommitted changes during development)
5. ✅ 17 new unit tests pass, 5 integration tests available

### Validation

| Check | Result |
|-------|--------|
| compileall | PASS |
| Unit tests (17) | 17/17 PASS |
| dev-check | PASS (all WebUI checks) |
| memory-check | PASS |
| No service startup | Confirmed |

### Push

Only after 0E-Release verification.

---

## Phase 0E-06: Phase 1 Safety Boundary — Completed ✅

**Status:** Completed
**Priority:** P1
**Estimated scope:** Medium (documentation only, no code)
**Date:** 2026-06-08

### Goal

Define the safety boundary document for Phase 1, establishing principles, gates, and capability-specific prerequisites before any write operations are introduced.

### Context

Phase 0C/0D established a strong read-only boundary. Phase 1 will inevitably introduce write operations. Without documented preconditions, there is risk of:
- Write operations introduced without adequate isolation testing
- Agent Run without dry-run capability
- Tool execution without allowlist
- Memory/Review mutation without production isolation verification

### Modification Scope

| File | Action |
|------|--------|
| `docs/webui/phase-0e-06-phase-1-safety-boundary.md` | **New** — Complete safety boundary document |

### Documented Principles

1. **Default deny:** All write operations disabled until explicitly enabled per-phase
2. **Dry-run first:** Every write operation must have a dry-run mode that validates without mutating
3. **Dev-only isolation:** All Phase 1 capabilities restricted to dev-home, production is fail-closed
4. **Explicit confirmation:** All write operations require user confirmation with cancel-default focus
5. **Allowlist enforcement:** Only explicitly listed actions are permitted
6. **Audit trail:** Every real write operation produces an audit event
7. **Kill switch:** Every capability can be immediately disabled via environment variable
8. **No production by design:** Production detection results in refusal, not warning
9. **Test-before-enable:** Comprehensive tests are a prerequisite for each capability
10. **Dual-channel safety:** Backend enforcement is mandatory, frontend hiding is insufficient

### Documented Capability Gates

- Review Queue read-only, dry-run, and execute gates (Phase 1A → 1B → 1C)
- Memory Writer dry-run gate (Phase 1D)
- Agent Run prompt preview and execution gates (Phase 1E → 1F)
- Tool Execution Safety Framework gate (Phase 1G)
- Session/Message/File/Gateway operation boundaries

### Recommended Phase 1 Sequence

```
1A: Review Queue Read-Only → 1B: Review Queue Dry-Run → 1C: Review Queue Execute
1D: Memory Writer Dry-Run (parallel)
1E: Agent Prompt Preview → 1F: Agent Run Without Tools → 1G: Tool Execution
```

### Non-goals

- No code changes
- No Phase 1 implementation
- No new API routes
- No commitment to Phase 1 timeline

### Acceptance Criteria

1. ✅ Document exists at `docs/webui/phase-0e-06-phase-1-safety-boundary.md`
2. ✅ All 10 safety principles documented with rationale and requirements
3. ✅ Phase 1 candidate capabilities listed with risk classification
4. ✅ Capability-specific gates defined for Review Queue, Memory, Agent, Tools, Sessions, Files
5. ✅ Phase 1 recommended sequence provided (1A through 1G)
6. ✅ Existing safety mechanisms inventoried for reuse
7. ✅ Audit trail requirements defined
8. ✅ Kill switch requirements defined
9. ✅ Testing requirements defined
10. ✅ No write operations implemented
11. ✅ No new API routes added
12. ✅ No business code modified
13. ✅ memory-check PASS
14. ✅ dev-check PASS
15. ✅ compileall PASS

### Dependencies

- None (documentation only)

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
| 0E-02 | Visual review artifact policy | ✅ Completed | None |
| 0E-03 | Playwright smoke matrix | ✅ Completed | 0E-01 preferred |
| 0E-04 | Dev WebUI smoke runner | ✅ Completed | None |
| 0E-05 | dev-check enhancement | ✅ Completed | 0E-01, 0E-02 preferred |
| 0E-06 | Phase 1 safety boundary | ✅ Completed | None |
| 0E-Release | Final verification & push | Not started | All above |

---

## Dependency Graph

```
0E-00 ✅
├── 0E-01 ✅ (no deps)
├── 0E-02 ✅ (no deps)
├── 0E-03 ✅ (prefers 0E-01)
├── 0E-04 ✅ (no deps)
├── 0E-05 ✅ (prefers 0E-01 + 0E-02)
├── 0E-06 ✅ (no deps)
└── 0E-Release (requires all)
```

0E-01, 0E-02, 0E-04, and 0E-06 have no dependencies and can be executed in any order. 0E-03 prefers 0E-01 completion. 0E-05 prefers 0E-01 and 0E-02 completion so that expected states are defined. 0E-Release requires all subphases.

---

## Phase 0E Closure

**Phase 0E-00 through 0E-06 are completed.**

**Phase 0E-Release completed.** All Phase 0E commits pushed to `origin/dev-huangruibang` at commit `cc64aa690`.

Phase 0E is formally sealed. Phase 1 planning begins with **Phase 1-00: Planning & Scope Freeze**.

- **Phase 1 planning document:** `docs/webui/phase-1-00-planning-and-scope.md`
- **Phase 1 implementation plan:** `docs/webui/phase-1-implementation-plan.md`

The next subphase is **Phase 1A: Review Queue Read-Only Panel**.
