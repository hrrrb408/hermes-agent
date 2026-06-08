# Phase 0E-00: Engineering Governance & Scope Freeze

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 279e27259 (Phase 0D final closure)

---

## 1. Background

Phase 0C and Phase 0D are formally sealed and pushed to `origin/dev-huangruibang`. The Dev WebUI now has:

- 11 read-only API routes connected to real backend data
- Full five-theme system (Obsidian, Paper, Song, Ink, Sakura Night)
- Three-column workbench layout with responsive breakpoints
- Accessibility compliance (ARIA, keyboard nav, reduced motion)
- 479 backend tests, 324 frontend tests — all passing
- Production isolation verified at every stage

Before advancing to any Phase 1 work (write operations, Agent Run, SSE), the engineering governance backlog must be addressed. Phase 0E is a dedicated governance phase that resolves build artifact hygiene, test automation gaps, and developer experience tooling before any functional expansion.

---

## 2. Current Baseline

### 2.1 Repository State

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| HEAD | `279e272599573899ffd5bb88cac2eebecc3dfe59` |
| origin/dev-huangruibang | `279e272599573899ffd5bb88cac2eebecc3dfe59` |
| local == remote | Yes |
| Working tree | 5 untracked visual-review directories only |

### 2.2 Completed Phases

| Phase | Scope | Commit |
|-------|-------|--------|
| 0A | Theme system & project scaffold | `0839d62cf` → `b2e34b83e` |
| 0B | Layout & theme integration (three-column shell) | `e078c18ba` |
| 0C | Read-only API, sessions, messages, memory, context, agent | `4faf8ba0e` → `564c15c98` |
| 0D | Responsive breakpoints, accessibility, reduced motion | `85da94825` → `279e27259` |

### 2.3 Environment State

| Item | Value |
|------|-------|
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway PID | 1717 (running, untouched) |
| Dev Gateway | stopped |
| Port 5180 | free |
| Port 5181 | free |
| memory-check | PASS |
| dev-check | WARN (5 visual-review dirs) |

### 2.4 Current Capabilities

**Backend (9 files, ~3700 LOC):**
- `hermes_cli/dev_web_api.py` — FastAPI app (776 lines)
- `hermes_cli/dev_web_schemas.py` — Pydantic models (304 lines)
- `hermes_cli/dev_web_config.py` — Environment validation (179 lines)
- `hermes_cli/dev_web_errors.py` — Error codes
- `hermes_cli/dev_web_session_service.py` — Session queries
- `hermes_cli/dev_web_message_service.py` — Message queries
- `hermes_cli/dev_web_memory_service.py` — Memory queries
- `hermes_cli/dev_web_agent_service.py` — Agent status
- `hermes_cli/dev_web_middleware.py` — CORS, request ID

**Frontend (Vue 3 + TypeScript + Vite):**
- 21 test files, 324 tests passing
- 5 themes with full CSS variable system
- Pinia stores for sessions, messages, workspace panels
- API client with typed error handling
- Three-column responsive layout (640px–1440px+)

**Test Coverage:**
- 479 backend tests (6 test files)
- 324 frontend tests (21 test files)
- Total: 803 tests, 0 failures

---

## 3. Open Engineering Issues

### Issue Inventory

| ID | Issue | Current Status | Risk | Priority | In 0E? |
|----|-------|---------------|------|----------|--------|
| E-01 | `dist/` and `tsbuildinfo` tracked in Git | 3 dist files + 1 tsbuildinfo committed; `.gitignore` has no `apps/hermes-dev-webui/dist/` or `apps/hermes-dev-webui/*.tsbuildinfo` entries | Medium — every `pnpm build` modifies tracked files; stage closure requires `git restore` | P2 | **Yes (0E-01)** |
| E-02 | `visual-review/` directories untracked | 5 directories in `apps/hermes-dev-webui/visual-review/` are untracked; `dev-check` reports WARN for dirty worktree | Low — cosmetic only, but masks real dirty-tree detection | P2 | **Yes (0E-02)** |
| E-03 | No Playwright viewport × theme automation | Manual spot-checking done in 0C/0D; no automated matrix for 6 viewports × 5 themes = 30 combinations | Low — manual validation sufficient for current scope; essential before Phase 1 | P2 | **Yes (0E-03)** |
| E-04 | No one-command Dev WebUI + API startup | Currently requires 2 separate commands (`python -m hermes_cli.main dev-webui-api` + `pnpm dev`) | Low — DX friction only | P3 | **Yes (0E-04)** |
| E-05 | `dev-check` does not cover WebUI-specific concerns | No checks for: Dev API module existence, OpenAPI validity, route count, forbidden routes, build artifact dirtiness | Low — would catch regressions earlier | P3 | **Yes (0E-05)** |
| E-06 | Phase 1 safety boundary undefined | No documented preconditions for introducing write operations, Agent Run, SSE, or tool execution | High — without boundary, write operations could be introduced without adequate safeguards | P1 | **Yes (0E-06)** |
| E-07 | Vite dev mode `data-vite-dev-id` contains local paths | `<style>` attributes in dev mode include `/Users/...` paths; production build does not have this | P2 — production build is clean; dev-only concern | P2 | **No** |
| E-08 | `apps/hermes-dev-webui/.gitignore` does not exist | No local `.gitignore` in the WebUI app directory | Low — root `.gitignore` covers most cases | P3 | **Deferred to 0E-01** |

---

## 4. Decision Matrix

### 4.1 Build Artifact Policy (E-01)

**Analysis:**

The `.gitignore` at repository root already ignores:
- `hermes_cli/web_dist/` (line 72)
- `apps/desktop/dist/` (line 74)
- `apps/desktop/*.tsbuildinfo` (line 76)

But there are NO entries for:
- `apps/hermes-dev-webui/dist/`
- `apps/hermes-dev-webui/*.tsbuildinfo`

The tracked files are:
```
apps/hermes-dev-webui/dist/assets/index-AxamzU0w.js
apps/hermes-dev-webui/dist/assets/index-CCl_6OPG.css
apps/hermes-dev-webui/dist/index.html
apps/hermes-dev-webui/tsconfig.app.tsbuildinfo
```

**Decision:** Add `.gitignore` entries and `git rm --cached` in Phase 0E-01. No deployment dependency on tracked dist (the dev WebUI runs via `pnpm dev` in development; build verification uses `pnpm build` then `git restore`).

**Risk:** If the Dev WebUI is ever served from `dist/` in a non-dev context, it would need a build step. Current architecture uses Vite dev server → FastAPI API. No static serving from dist in production is planned for Phase 0.

### 4.2 Visual Review Artifact Policy (E-02)

**Analysis:**

5 directories exist:
```
apps/hermes-dev-webui/visual-review/phase-0b/
apps/hermes-dev-webui/visual-review/phase-0b-1/
apps/hermes-dev-webui/visual-review/phase-0b-1-1/
apps/hermes-dev-webui/visual-review/phase-0b-1-2/
apps/hermes-dev-webui/visual-review/phase-0b-1-3/
```

These are local human visual review artifacts from Phase 0B. They contain no sensitive data but cause `dev-check` to report `WARN` (dirty worktree), which masks real dirty-tree issues.

**Decision:** Add `apps/hermes-dev-webui/visual-review/` to `.gitignore`. Do NOT delete existing directories. Optionally enhance `dev-check` to recognize known whitelisted untracked paths.

### 4.3 Playwright Smoke Matrix (E-03)

**Analysis:**

- No `playwright.config.*` exists
- No `@playwright/test` in `package.json` devDependencies
- Previous validation used ad-hoc Playwright scripts
- 6 viewports × 5 themes = 30 combinations

**Decision:** Create a lightweight Playwright test script (not full test framework integration). Default: no screenshots saved. Pass/fail only. Can use either real Dev API + WebUI or a simpler HTTP-based check for initial implementation.

### 4.4 Dev WebUI Smoke Runner (E-04)

**Analysis:**

- Dev API: `python -m hermes_cli.main dev-webui-api`
- WebUI: `pnpm dev --host 127.0.0.1 --port 5180`
- Both require `HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev`

**Decision:** Create `scripts/run-dev-webui.sh` with `start`, `status`, `stop` subcommands. Not a daemon — a convenience wrapper. Must enforce `HERMES_HOME` and `127.0.0.1` binding.

### 4.5 dev-check Enhancement (E-05)

**Analysis:**

Current `dev-check` in `hermes_cli/main.py` (~line 7451) checks:
- Source root, HERMES_HOME, .venv, config, SOUL.md, state.db
- Git branch, Git worktree (dirty/clean)
- Gateway status
- Memory system integrity
- Review queue, auth controls, etc.

Missing checks:
- Dev API module existence (`hermes_cli/dev_web_api.py`)
- OpenAPI spec validity
- Route count verification (11 business routes)
- Forbidden route verification
- Build artifact dirty detection (`dist/`, `tsbuildinfo`)
- Visual-review known whitelist

**Decision:** Add WebUI-specific checks to `dev-check`. Keep them fast, read-only, no service startup. Checks that require running services belong in the smoke runner (0E-04).

### 4.6 Phase 1 Safety Boundary (E-06)

**Analysis:**

Phase 0C/0D established a strong read-only boundary. Phase 1 will inevitably introduce write operations. Without documented preconditions, there is risk of:

- Write operations introduced without adequate isolation testing
- Agent Run without dry-run capability
- Tool execution without allowlist
- Memory/Review mutation without production isolation verification

**Decision:** Draft Phase 1 safety principles document. No code changes. Principles:
1. Default deny — all write operations disabled until explicitly enabled
2. Every write operation requires its own phase
3. Every write operation must have a dry-run mode
4. All mutations must go through an allowlist
5. Production isolation must be verified before and after every write phase
6. Browser + CLI dual confirmation for destructive operations
7. No SSE until Agent Run integration is complete and tested

---

## 5. Phase 0E Scope

### In Scope

1. **0E-01:** Build Artifact Policy — `.gitignore` update, `git rm --cached`, verification
2. **0E-02:** Visual Review Artifact Policy — `.gitignore` entry, dev-check allowlist
3. **0E-03:** Playwright Smoke Matrix — lightweight test script, viewport × theme pass/fail
4. **0E-04:** Dev WebUI Smoke Runner — `scripts/run-dev-webui.sh` with start/status/stop
5. **0E-05:** dev-check Enhancement — WebUI-specific read-only checks
6. **0E-06:** Phase 1 Safety Boundary Draft — documentation only, no code
7. **0E-Release:** Final verification and push

### Strictly Out of Scope

- New business API routes
- Write operations of any kind
- Agent Run / LLM calls / Tool execution
- SSE / WebSocket implementation
- Memory write/update/archive
- Review Queue approve/reject
- Session/message creation
- File browsing/upload/delete
- Gateway or Dashboard integration
- Production environment changes
- Any modification to `~/.hermes`
- Phase 1 implementation

---

## 6. Non-Goals

1. No new functional capabilities
2. No real Agent conversation integration
3. No SSE streaming
4. No write operations
5. No production deployment
6. No public access
7. No dependency upgrades (unless required by Playwright addition)
8. No UI/UX changes

---

## 7. Subphase Plan

### 0E-01: Build Artifact Policy

- **Scope:** Add `apps/hermes-dev-webui/dist/` and `apps/hermes-dev-webui/*.tsbuildinfo` to `.gitignore`; `git rm --cached` the 4 tracked files; verify `pnpm build` no longer dirties the tree
- **Non-goals:** No changes to `apps/desktop/`, `hermes_cli/web_dist/`, or other build artifact paths
- **Acceptance:** `git status` shows no dist/tsbuildinfo changes after `pnpm build`; `dev-check` no longer warns about build artifacts
- **Push:** Yes (after 0E-Release)

### 0E-02: Visual Review Artifact Policy

- **Scope:** Add `apps/hermes-dev-webui/visual-review/` to `.gitignore`; optionally add known-whitelist detection to `dev-check`
- **Non-goals:** Do not delete existing visual-review directories; do not migrate or archive them
- **Acceptance:** `dev-check` no longer reports WARN for visual-review directories; directories still exist on disk
- **Push:** Yes (after 0E-Release)

### 0E-03: Playwright Smoke Matrix

- **Scope:** Add `@playwright/test` to devDependencies; create a lightweight smoke test that validates all 5 themes render at key viewports (mobile 640px, tablet 768px, desktop 1280px, wide 1440px) = 20 combinations
- **Non-goals:** No screenshot saving by default; no CI integration; no visual regression baseline
- **Acceptance:** `pnpm exec playwright test` runs and reports pass/fail for 20 viewport × theme combinations; no real Agent required
- **Push:** Yes (after 0E-Release)

### 0E-04: Dev WebUI Smoke Runner

- **Scope:** Create `scripts/run-dev-webui.sh` with `start`, `status`, `stop` subcommands; enforce HERMES_HOME and 127.0.0.1 binding
- **Non-goals:** Not a long-running daemon; no PID file management beyond process tracking; no auto-restart
- **Acceptance:** `./scripts/run-dev-webui.sh start` launches both Dev API and WebUI dev server; `status` shows both running; `stop` terminates both cleanly
- **Push:** Yes (after 0E-Release)

### 0E-05: dev-check Enhancement

- **Scope:** Add WebUI-specific checks to `cmd_dev_check()` in `hermes_cli/main.py`: Dev API module existence, OpenAPI spec validity, route count, forbidden routes, build artifact dirtiness, visual-review whitelist
- **Non-goals:** No service startup; no network requests; remain fast and read-only
- **Acceptance:** `dev-check` reports WebUI-specific PASS/WARN/FAIL items; no regression in existing checks
- **Push:** Yes (after 0E-Release)

### 0E-06: Phase 1 Safety Boundary Draft

- **Scope:** Document Phase 1 safety principles: default deny, dry-run, allowlist, production isolation, dual confirmation. Define which write operations are candidates and their prerequisites.
- **Non-goals:** No code changes; no implementation; no Phase 1 start
- **Acceptance:** Document exists at `docs/webui/phase-1-safety-boundary.md`; reviewed and approved by user
- **Push:** Yes (after 0E-Release)

### 0E-Release: Final Verification & Push

- **Scope:** Run full gate (memory-check, dev-check, compileall, frontend tests, backend tests); verify clean working tree; push to `origin/dev-huangruibang`
- **Non-goals:** No additional changes
- **Acceptance:** All checks pass; working tree clean (only visual-review dirs); pushed to remote
- **Push:** Yes (this is the only push in Phase 0E)

---

## 8. Acceptance Criteria

Phase 0E-00 is complete when:

1. ✅ Current branch confirmed: `dev-huangruibang`
2. ✅ local == origin confirmed
3. ✅ Phase 0C/0D baseline confirmed
4. ✅ Engineering governance issues listed with priority
5. ✅ Phase 0E subphases frozen with scope/non-goals/acceptance
6. ✅ No new functionality added
7. ✅ No business code changed
8. ✅ memory-check PASS
9. ✅ dev-check WARN only (5 visual-review dirs)
10. ✅ Production environment unaffected
11. ✅ Governance documents committed
12. ✅ Not pushed (pending 0E-Release)
13. ✅ Working tree: only 5 visual-review directories untracked

---

## 9. Safety Constraints

- **Production Gateway PID 1717:** Read-only confirmation. Not stopped, not restarted, not replaced.
- **`~/.hermes`:** Never accessed.
- **`setup-hermes.sh`:** Never run.
- **Global `hermes` command:** Not modified.
- **Dev services:** Bind to `127.0.0.1` only.
- **Ports:** 5180 (WebUI), 5181 (API) — no other ports.
- **No commits containing:** state.db, WAL, SHM, .env, API keys, tokens, cookies, sessions, memory records, events.jsonl, snapshots, reviews, logs, PID files, dist, tsbuildinfo, node_modules, coverage.

---

## 10. Push Policy

- **0E-00 through 0E-06:** Do NOT push. Commit locally only.
- **0E-Release:** Push all Phase 0E commits to `origin/dev-huangruibang` in one batch after final verification.

---

## 11. Risk Assessment

### P0 (Blocker)
None.

### P1 (Must resolve before Phase 1)
- **E-06:** Phase 1 safety boundary must be documented before any write operation is introduced.

### P2 (Should resolve in Phase 0E)
- **E-01:** Build artifact tracking causes friction at every stage closure.
- **E-02:** Visual-review directories mask real dirty-tree issues in `dev-check`.
- **E-07:** Vite dev mode local paths (deferred — production build is clean).

### P3 (Nice to have)
- **E-03:** Playwright matrix — essential for regression prevention, but manual spot-checking is sufficient for Phase 0.
- **E-04:** Smoke runner — DX convenience.
- **E-05:** dev-check enhancement — earlier error detection.

---

## 12. Conclusion

**Phase 0E-00 completed. Phase 0E scope is frozen.**

**Phase 0E-01 completed.** Build artifacts (`dist/` and `*.tsbuildinfo`) are no longer tracked by Git. Dev WebUI `pnpm build` no longer leaves tracked changes. See `docs/webui/phase-0e-01-build-artifact-policy.md` for details.

The next subphase is **0E-02: Visual Review Artifact Policy**. This task does NOT automatically start 0E-02.
