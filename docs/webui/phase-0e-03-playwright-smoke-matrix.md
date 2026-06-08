# Phase 0E-03: Playwright Smoke Matrix

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** d7c931db0 (Phase 0E-02)

---

## 1. Problem

Phase 0C and 0D validated the Dev WebUI manually via ad-hoc browser testing. There was no automated test matrix to verify that all five themes render correctly across multiple viewports, that the network boundary is respected (no write requests, no forbidden endpoints, no localhost/5182), and that the read-only UI is enforced. Without automated smoke tests, regressions in theme rendering, layout stability, or network safety would only be caught by manual inspection.

---

## 2. Audit Result

Before this phase:

| Item | Status |
|------|--------|
| `@playwright/test` in package.json | Not present |
| `playwright.config.ts` | Not present |
| Smoke test scripts | Not present |
| Playwright artifact ignore rules | Not present |
| Chromium browser binary | Available (`~/Library/Caches/ms-playwright/chromium-1223/`) |

---

## 3. Dependency Decision

**Decision:** Add `@playwright/test` as a dev dependency.

- Package: `@playwright/test@1.60.0`
- Added to `apps/hermes-dev-webui/package.json` devDependencies
- Chromium was already installed in the user's Playwright cache
- No additional browser installation required
- No Percy, Chromatic, Applitools, or visual regression dependencies added

---

## 4. Matrix Definition

### Viewports

| Name | Width | Height | Rationale |
|------|-------|--------|-----------|
| 1440x900 | 1440 | 900 | Wide-screen full three-column |
| 1280x800 | 1280 | 800 | Standard desktop three-column |
| 1024x768 | 1024 | 768 | Compressed three-column / right panel collapse critical |
| 768x900 | 768 | 900 | Tablet / narrow-width responsive strategy |

### Themes

| ID | Color Scheme | Category |
|----|-------------|----------|
| obsidian | dark | modern |
| paper | light | modern |
| song | dark | eastern |
| ink | light | eastern |
| sakura-night | dark | eastern |

### Total Combinations

- **20 viewport × theme smoke tests** + **4 panel drill-down tests** = **24 total tests**

---

## 5. Network Safety Checks

Each test monitors all HTTP requests and asserts:

- **No port 5182** — requests to port 5182 are forbidden
- **No bare localhost** — only `127.0.0.1` is allowed (string `localhost` is rejected)
- **No `0.0.0.0`** — any binding to 0.0.0.0 is forbidden
- **No `/reviews`** — review queue endpoints are forbidden
- **No POST to `/memory`** (except read-only `/memory/status`, `/memory/categories`, `/memory/items`)
- **No PATCH/DELETE to `/memory`** — memory mutation is forbidden
- **No `/agent/run`** — agent execution is forbidden
- **No POST to `/tools`** — tool execution is forbidden
- **No POST to `/sessions` or `/messages`** — write operations forbidden
- **No POST/DELETE to `/files`** — file operations forbidden
- **Only allowed POST:** `POST /api/dev/v1/context/preview`

---

## 6. Console/CORS Checks

Each test collects:

- **console.error** — filtered for known acceptable errors (Vite HMR, network failures when API offline)
- **pageerror** — must be 0
- **CORS errors** — must be 0
- **Asset 404s** — must be 0 for `/assets/` paths
- **API failures** — filtered to exclude expected offline responses

---

## 7. Overflow Checks

Each test checks:

```javascript
document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2
```

Tolerance of 2px for sub-pixel rendering.

---

## 8. Read-only Checks

Each test verifies:

- Send button is **disabled**
- Attach button is **disabled**
- Composer textarea exists
- "Read only" or "Read-only" text is visible in the UI
- No path redaction failures (no `/Users/`, `/home/`, or `file://` in page text)

---

## 9. Artifact Policy

**Default: no artifacts saved.**

| Artifact | Setting |
|----------|---------|
| Screenshots | `off` |
| Video | `off` |
| Trace | `off` |
| HAR | not configured (not generated) |

`.gitignore` rules added:

```gitignore
/apps/hermes-dev-webui/playwright-report/
/apps/hermes-dev-webui/test-results/
/apps/hermes-dev-webui/blob-report/
```

---

## 10. How to Run

### Prerequisites

Start Dev API and WebUI:

```bash
# Terminal 1: Dev API
HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev python -m hermes_cli.main dev-webui-api

# Terminal 2: WebUI (must be in apps/hermes-dev-webui/)
cd apps/hermes-dev-webui && pnpm dev
```

### Run Smoke Tests

```bash
# From repo root:
npx playwright test --config apps/hermes-dev-webui/playwright.config.ts tests/smoke/phase-0e-03-smoke.spec.ts

# Or from apps/hermes-dev-webui/:
pnpm test:smoke:0e03
```

### Important Note

The `pnpm test:smoke` and `pnpm test:smoke:0e03` scripts must be run from `apps/hermes-dev-webui/` so Playwright finds the config file. The `npx playwright test --config` variant works from the repo root.

---

## 11. Validation Result

| Metric | Value |
|--------|-------|
| Total combinations | 24 (20 viewport×theme + 4 drill-down) |
| Passed | 24 |
| Failed | 0 |
| Duration | 49.8s |
| Side-effects | state.db unchanged, MEMORY.md unchanged, memory files unchanged |
| Production Gateway | PID 1717 untouched |

---

## 12. Files Created/Modified

| File | Action |
|------|--------|
| `apps/hermes-dev-webui/package.json` | Modified — added `@playwright/test`, smoke scripts |
| `apps/hermes-dev-webui/playwright.config.ts` | New — Playwright configuration |
| `apps/hermes-dev-webui/tests/smoke/phase-0e-03-smoke.spec.ts` | New — 24 smoke tests |
| `apps/hermes-dev-webui/vite.config.ts` | Modified — exclude `tests/smoke/` from Vitest |
| `.gitignore` | Modified — Playwright artifact ignore rules |
| `docs/webui/phase-0e-03-playwright-smoke-matrix.md` | New — this document |
| `docs/webui/phase-0e-implementation-plan.md` | Modified — mark 0E-03 as completed |
| `docs/webui/phase-0e-00-governance-scope.md` | Modified — add 0E-03 result summary |

---

## 13. Non-goals

- No CI integration (local execution only)
- No visual regression baseline or screenshot comparison
- No Percy / Chromatic / Applitools integration
- No test video/trace/HAR recording
- No automated service startup (0E-04 scope)
- No dev-check enhancement (0E-05 scope)

---

## 14. Follow-up

- **0E-04:** Dev WebUI Smoke Runner — one-command service startup + smoke test execution
- **0E-05:** dev-check Enhancement — add WebUI-specific checks (Playwright binary, config existence, test count)
