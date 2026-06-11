# Phase 1G-03-06: Schema Preview Browser Smoke, A11y, Network Safety & Theme Verification

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-03-06 |
| Title | Schema Preview Panel Browser Smoke, A11y, Network Safety & Theme Verification |
| Status | Completed |
| Date | 2026-06-11 |
| Author | Dev Agent (Phase 1G-03-06 verification) |
| Dependencies | Phase 1G-03-05 completed and pushed |
| Branch | dev-huangruibang |
| Base commit | ebbc97b900446a7e3c1df574834189ef5a8c73f8 |
| Implementation | Test files and documentation only — no backend API, OpenAPI, router, or source modifications |

---

## 1. Execution Summary

Phase 1G-03-06 verified the read-only Schema Preview Panel through:

1. **Playwright browser smoke tests** — 44 automated tests against real Dev API
2. **Network safety verification** — confirmed GET-only, no forbidden requests
3. **A11y smoke verification** — ARIA roles, labels, keyboard navigation
4. **Theme/viewport matrix** — 5 themes × 4 viewports (20 combinations)
5. **Read-only boundary** — no execution CTAs, no mutation controls
6. **Backend governance regression** — 261 tests pass, all counts verified

---

## 2. Dev-only Runtime

| Service | PID | URL | Status |
|---------|-----|-----|--------|
| Dev Gateway | 69540 | 127.0.0.1:18080 | Started then stopped |
| Dev Web API | 70629 | 127.0.0.1:5181 | Started then stopped |
| Frontend Vite | 71429 | 127.0.0.1:5180 | Started then stopped |
| Production Gateway | 1717 | — | Running, unaffected |

All dev-only services were shut down after verification. Ports 5180 and 5181 confirmed free.

---

## 3. Browser Smoke Results

| Category | Tests | Passed | Failed | Duration |
|----------|-------|--------|--------|----------|
| Full Integration | 8 | 8 | 0 | ~32s |
| HTTP Method Safety | 2 | 2 | 0 | ~8s |
| Network Safety | 2 | 2 | 0 | ~8s |
| Read-Only Boundary | 2 | 2 | 0 | ~7s |
| Error and Retry | 1 | 1 | 0 | ~5s |
| Theme/Viewport Matrix | 20 | 20 | 0 | ~66s |
| Accessibility | 9 | 9 | 0 | ~25s |
| **Total** | **44** | **44** | **0** | **2.5m** |

### Verified Behaviors

- ✅ Schema Preview sub-tab renders under Tools tab
- ✅ Read-only notice visible ("Schema Preview is read-only")
- ✅ Summary cards show Total tools (71), Available, Unavailable
- ✅ Tool list items with risk badges and availability status
- ✅ Search filters by canonicalName and capability
- ✅ Availability filter (all/available/unavailable) works correctly
- ✅ Risk filter (R0–R5) works correctly
- ✅ Tool selection shows detail panel with schema info
- ✅ Field list renders for tools with input schemas
- ✅ Empty field state ("No input fields") for tools without schemas
- ✅ Keyboard navigation (ArrowUp/Down, Home/End, Enter/Space)
- ✅ Error state with retry button
- ✅ Catalog loads 71 tools from real API

---

## 4. Network Safety Results

| Check | Result |
|-------|--------|
| Schema API requests are GET-only | ✅ PASS |
| Tool write requests = 0 | ✅ PASS |
| POST/PUT/PATCH/DELETE to /tools/schemas | ✅ 0 found |
| POST/PUT/PATCH/DELETE to /tools/* | ✅ 0 found |
| External business requests | ✅ 0 found |
| Provider requests (openai, anthropic, xai, zai, gemini, openrouter) | ✅ 0 found |
| Forbidden patterns (/execute, /dry-run, /provider, /dispatch, /audit, /allowlist) | ✅ 0 found |

---

## 5. A11y Smoke Results

| Check | Result |
|-------|--------|
| Schema Preview tab has role="tab" | ✅ PASS |
| Tabpanel has role="tabpanel" | ✅ PASS |
| Section has aria-label="Tool Schema Preview" | ✅ PASS |
| Tool list has role="listbox" | ✅ PASS |
| Items have role="option" | ✅ PASS |
| Detail panel has role="region" | ✅ PASS |
| Search input has label (label[for="sp-search"]) | ✅ PASS |
| Availability select has label | ✅ PASS |
| Risk select has label | ✅ PASS |
| Read-only notice has role="status" | ✅ PASS |
| Sub-tab keyboard navigation (ArrowRight/Left, End) | ✅ PASS |
| List keyboard navigation (ArrowUp/Down, Home/End, Enter) | ✅ PASS |
| Loading state has aria-busy | ✅ PASS |

**No A11y violations detected. No P1 issues.**

---

## 6. Theme Verification Results

| Theme | 1440×900 | 1280×800 | 1024×768 | 768×900 |
|-------|----------|----------|----------|---------|
| obsidian | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| paper | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| song | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| ink | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| sakura-night | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |

Per-theme checks (all PASS):
- Schema Preview tab visible
- Read-only warning readable
- Summary cards readable
- Risk badges readable
- Available/unavailable status readable
- Search/filter controls readable
- Detail panel readable
- Field cards readable
- No text overlap
- 768px: no document-level horizontal overflow
- Buttons/inputs have visible boundaries
- Error/empty state colors readable

---

## 7. Read-Only Boundary

| Check | Result |
|-------|--------|
| No "Run" button | ✅ PASS |
| No "Execute" button | ✅ PASS |
| No "Dry Run" button | ✅ PASS |
| No "Send to Provider" button | ✅ PASS |
| No "Generate Args" button | ✅ PASS |
| No "Call Tool" button | ✅ PASS |
| No "Test Tool" button | ✅ PASS |
| No "Enable Tool" button | ✅ PASS |
| No "Save Allowlist" button | ✅ PASS |
| No "Dispatch" button | ✅ PASS |
| No "Audit" button | ✅ PASS |
| No raw schema text | ✅ PASS |
| No handler/callable/path/secret | ✅ PASS |

---

## 8. Files Changed

| File | Change Type |
|------|-------------|
| `apps/hermes-dev-webui/tests/smoke/phase-1g-03-schema-preview-smoke.spec.ts` | New — 44 Playwright browser smoke tests |
| `docs/webui/phase-1g-03-06-schema-preview-browser-smoke.md` | New — This report |
| `docs/webui/phase-1g-03-tool-schema-preview-scope.md` | Modified — Phase 1G-03-06 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Modified — Phase status update |

**No backend API, OpenAPI, router, source, or runtime files modified.**

---

## 9. Quality Gates

### Frontend Unit Tests

| Metric | Value |
|--------|-------|
| Command | `npx vitest run` |
| Files | 27 |
| Tests | 649 passed |
| Duration | 2.29s |

### Browser Smoke Tests

| Metric | Value |
|--------|-------|
| Command | `npx playwright test tests/smoke/phase-1g-03-schema-preview-smoke.spec.ts` |
| Tests | 44 passed |
| Duration | 2.5m |
| Browser | Chromium |

### Existing Smoke Regression

| Metric | Value |
|--------|-------|
| Command | `npx playwright test tests/smoke/phase-1g-tool-policy-smoke.spec.ts` |
| Tests | 39 passed |
| Duration | 3.0m |

### Type Check / Lint / Build

| Gate | Result |
|------|--------|
| TypeScript type-check (`vue-tsc --noEmit`) | ✅ PASS |
| ESLint | ✅ PASS |
| Production build (`vite build`) | ✅ PASS (1852 modules, 1.07s) |

### Backend Governance

| Metric | Value |
|--------|-------|
| Command | `pytest tests/test_dev_web_tool_schema_preview_api.py tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py tests/test_dev_web_tool_policy_api.py` |
| Tests | 261 passed, 5 deselected |
| Duration | 7.68s |
| OpenAPI paths | 31 ✅ |
| Runtime routes | 31 ✅ |
| Tool GET routes | 4 ✅ |
| Tool write routes | 0 ✅ |

### Static Gates

| Gate | Result |
|------|--------|
| compileall (dev_web_api, schema preview modules) | ✅ PASS |
| toolsets.py compile | ✅ PASS |
| memory-check | ✅ PASS (all 19 checks) |
| dev-check | WARN only (dirty worktree — expected) |

---

## 10. Boundary Verification

| Metric | Value | Status |
|--------|-------|--------|
| Backend API modified | No | ✅ |
| OpenAPI modified | No | ✅ |
| hermes_cli/main.py modified | No | ✅ |
| Router modified | No | ✅ |
| Provider Schema sent | No | ✅ |
| Tool handler called | No | ✅ |
| Tool dispatch | 0 | ✅ |
| Tool execution | disabled | ✅ |
| Tool audit | absent | ✅ |
| STATIC_ALLOWLIST | empty | ✅ |
| Tool write routes | 0 | ✅ |
| Execution CTA | absent | ✅ |
| Raw schema exposed | No | ✅ |
| Handler/callable/path/secret exposed | No | ✅ |

---

## 11. Production Safety

| Check | Result |
|-------|--------|
| Production Gateway PID 1717 running | ✅ Affirmed |
| Dev Gateway stopped | ✅ Confirmed |
| Frontend dev server stopped | ✅ Confirmed |
| Port 5180 free | ✅ Confirmed |
| Port 5181 free | ✅ Confirmed |
| No ~/.hermes access | ✅ Confirmed |
| No production state.db access | ✅ Confirmed |

---

## 12. Risks

### P0
None.

### P1
None.

### P2

| Risk | Mitigation |
|------|-----------|
| Browser smoke is automated (Playwright) but not CI-integrated | Test can be run locally via `npm run test:smoke` |
| No separate screenshot artifacts captured | Visual verification covered by 20 theme/viewport automated checks |
| Some tools show UNAVAILABLE_EMPTY_SCHEMA for `schemaPreviewAvailable=true` items | This is expected backend behavior when schema source returns None; catalog counts are correct |

---

## 13. Acceptance Conclusion

Phase 1G-03-06 completed successfully.

Browser smoke, a11y smoke, network safety verification, and theme verification were all completed for the read-only Schema Preview Panel across 5 themes and 4 viewports. No backend API, OpenAPI, router, provider schema sending, tool dispatch, tool execution, tool audit, or allowlist changes were introduced. All 44 new Playwright smoke tests pass. All existing 39 tool policy smoke tests pass without regression.

A local commit was created. Push was not performed. Phase 1G-03-07 was not started.
