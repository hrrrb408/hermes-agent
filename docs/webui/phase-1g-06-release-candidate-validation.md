# Phase 1G-06: Release Candidate Validation

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-06 |
| Title | Release Candidate Validation — Dev WebUI Pilot Rehearsal |
| Status | Validated (rehearsal, not a production release) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Candidate | Phase 1G-04 sealed mainline (`94f22f67b`) + Phase 1G-05 readiness (`da5c31a8c`) |
| Scope | Record the actual Phase 1G-06 rehearsal gate results. No code change. |

---

## 1. Git Baseline

| Item | Observed |
|------|----------|
| Branch | `dev-huangruibang` |
| Local HEAD | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` |
| Remote HEAD | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` |
| Merge base | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |

---

## 2. Route Governance

| Metric | Observed | Expected |
|--------|----------|----------|
| OpenAPI paths | 34 | 34 |
| Runtime routes | 34 | 34 |
| Tool GET routes | 5 | 5 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` | `frozenset({"clarify"})` |

Verified by `tests/test_dev_check_webui.py` and `tests/test_dev_web_0c06_closure.py`.

---

## 3. Backend Regression

| Suite | Observed |
|-------|----------|
| Route governance (`test_dev_check_webui.py` + `test_dev_web_0c06_closure.py`) | 124 passed, 5 deselected, 0 failed |
| Related backend regression (18 files) | 1471 passed, 2 skipped, 5 deselected, 0 failed |

All backend suites: **0 failed**. Matches the Phase 1G-05 reference baseline.

---

## 4. Compile / Ruff

| Check | Observed |
|-------|----------|
| `compileall` (14 dev_web modules) | OK (exit 0) |
| `py_compile toolsets.py` | OK |
| `ruff check` (14 files) | All checks passed |

---

## 5. Frontend Type-Check

| Check | Observed |
|-------|----------|
| `pnpm type-check` (`vue-tsc --noEmit`) | pass (exit 0) |

---

## 6. Frontend Lint

| Check | Observed |
|-------|----------|
| `pnpm lint` (`eslint .`) | 0 errors / 0 warnings (exit 0) |

---

## 7. Frontend Unit Tests

| Check | Observed |
|-------|----------|
| `pnpm test` (`vitest run`) | 674 passed (31 files), 0 failed |

Matches the Phase 1G-05 reference baseline (674 passed / 31 files).

---

## 8. Frontend Build

| Check | Observed |
|-------|----------|
| `pnpm build` (`vue-tsc -b && vite build`) | pass (exit 0), 1862 modules transformed |

---

## 9. Browser Smoke — Blocked Profile (A)

| Check | Observed |
|-------|----------|
| Command | `./scripts/run-dev-webui-execute-audit-smoke.sh blocked` |
| Gate env | `HERMES_TOOL_EXECUTION_ENABLED=true`, `HERMES_AGENT_TOOLS_ENABLED=true`, handler-call gate unset |
| `EXECUTE_EXPECTED` | `blocked_tool_handler_call_not_enabled` |
| Smoke result | **6 passed, 1 skipped, 0 failed** |
| Expected decision asserted | `blocked_tool_handler_call_not_enabled` |
| `toolHandlerCalled` | `false` |
| `executionCompleted` | `false` |
| `providerSchemaSent` / `providerApiCalled` / `externalSideEffects` | all `false` |

The 1 skip is the post-execution-audit visibility test, correctly skipped when
execution is blocked (no execution → no post-audit).

---

## 10. Browser Smoke — Completed Profile (B)

| Check | Observed |
|-------|----------|
| Command | `./scripts/run-dev-webui-execute-audit-smoke.sh completed` |
| Gate env | all three gates `=true` (incl. handler-call) |
| `EXECUTE_EXPECTED` | `clarify_execution_completed` |
| Smoke result | **7 passed, 0 failed** |
| Expected decision asserted | `clarify_execution_completed` |
| `canonicalName` | `clarify` |
| `handlerCallId` | present (starts with `thc_`) |
| `postExecutionAuditId` | present (starts with `pexa_`); visible in audit viewer |
| `providerSchemaSent` / `providerApiCalled` / `externalSideEffects` | all `false` |

---

## 11. memory-check

| Check | Observed |
|-------|----------|
| `./scripts/run-dev-hermes.sh memory-check` | PASS |

---

## 12. dev-check

| Check | Observed |
|-------|----------|
| `./scripts/run-dev-hermes.sh dev-check` | PASS (only `.claude/` untracked) |
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET / write / dry-run / execution | 5 / 0 / 1 / 1 |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |
| Provider tool schema | not sent |
| Production isolation | PASS |

---

## 13. Production Gateway PID

| Check | Observed |
|-------|----------|
| Production Gateway expected PID | `69355` |
| Production Gateway PID before rehearsal | `69355` |
| Production Gateway PID after rehearsal | `69355` |
| Production gateway process count | exactly 1 |
| Production Gateway stopped / restarted / replaced | no |

---

## 14. Final Port Status

| Port | Observed |
|------|----------|
| `5180` (WebUI) | free after each profile |
| `5181` (Dev API) | free after each profile |
| Dev API leftover | none |
| WebUI / vite leftover | none |
| `/tmp` harness logs | cleaned on exit |

---

## 15. Go / No-Go Outcome

### 15.1 Go / No-Go rule

| Decision | Condition |
|----------|-----------|
| **GO** | No P0, no P1; all required gates pass; production PID unchanged; route governance unchanged; no forbidden file touched. |
| **NO-GO** | Any P0; any P1; backend regression failed; frontend build failed; smoke failed; route governance changed; production PID changed; provider boundary violated. |

### 15.2 Observed outcome

| Criterion | Result |
|-----------|--------|
| P0 blockers | 0 |
| P1 release blockers | 0 |
| Backend regression | 0 failed |
| Frontend type-check / lint / unit / build | all pass |
| Smoke — blocked (A) | 0 failed |
| Smoke — completed (B) | 0 failed |
| Route governance | unchanged (34 / 34 / 5 / 0 / 1 / 1) |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |
| Provider Schema / API | none |
| Non-clarify execution | none |
| Production Gateway PID | `69355` unchanged |
| Ports `5180` / `5181` | free |
| Forbidden files touched | none |
| Audit JSONL / `.claude/` committed | no |

**Rehearsal outcome: GO (rehearsal pass).**

This is a **rehearsal** result, not a production release authorization. It
confirms the sealed Phase 1G-04 mainline, on the Phase 1G-05 readiness baseline,
passes the full release gate sequence through the committed rehearsal harness.
A real Pilot / release go decision is recorded separately on the go/no-go
template (`docs/webui/phase-1g-06-go-no-go-template.md`).

---

## 16. P0 / P1 / P2 Summary

| Severity | Count | Notes |
|----------|-------|-------|
| P0 | 0 | No boundary violation observed. |
| P1 | 0 | No gate failure observed. |
| P2 | 8 | Carried over from the Phase 1G-05 risk register; non-blocking. |

---

## 17. Non-Reopening Declaration

This validation did **not** reopen Phase 1G-04 and did **not** add any product
capability. No route, allowlist, execute gate, audit behavior, frontend
capability, or test strength was changed. The only artifacts produced are the
Phase 1G-06 rehearsal docs and the optional committed dev-only smoke script.

---

*Phase 1G-06 Release Candidate Validation — rehearsal gate results recorded.
All required gates pass; route governance and `STATIC_ALLOWLIST` unchanged;
Production Gateway PID `69355` unaffected; rehearsal outcome GO.*
