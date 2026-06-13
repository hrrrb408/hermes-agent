# Phase 1G-07: Release Candidate Validation Report

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-07 |
| Title | Release Candidate Validation Report — `RC-1G-07-001` |
| Status | Validated (dry run, not a production release) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| RC ID | `RC-1G-07-001` |
| Candidate | Phase 1G-04 sealed mainline (`94f22f67b`) + Phase 1G-05 readiness (`da5c31a8c`) + Phase 1G-06 release rehearsal (`311221e0d`) |
| Scope | Record the actual Phase 1G-07 RC dry-run gate results. No code change. |

---

## 1. Git Baseline

| Item | Observed |
|------|----------|
| Branch | `dev-huangruibang` |
| Local HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| Remote HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| Merge base | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
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

Verified by `tests/test_dev_check_webui.py`, `tests/test_dev_web_0c06_closure.py`,
and `./scripts/run-dev-hermes.sh dev-check` (`PASS Static allowlist: clarify`,
`PASS Tool write routes: absent`, `PASS Provider tool schema: not sent`).

---

## 3. Backend Regression

| Suite | Observed |
|-------|----------|
| Route governance (`test_dev_check_webui.py` + `test_dev_web_0c06_closure.py`) | 124 passed, 0 failed |
| Related backend regression (19 files) | 1471 passed, 0 failed |

All backend suites: **0 failed**. Matches the Phase 1G-05 / Phase 1G-06 reference
baselines. (Deselected / skipped counts are absorbed by the parallel wrapper and
do not count as failures; the regression contains 2 skipped integration cases,
unchanged from prior baselines.)

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

Matches the Phase 1G-05 / Phase 1G-06 reference baseline (674 passed / 31 files).

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
| `./scripts/run-dev-hermes.sh memory-check` | PASS (all 12 invariants ok) |

---

## 12. dev-check

| Check | Observed |
|-------|----------|
| `./scripts/run-dev-hermes.sh dev-check` | WARN (only `Git worktree: dirty` from untracked `.claude/`) |
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET / write / dry-run / execution | 5 / 0 / 1 / 1 |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |
| Provider tool schema | not sent |
| Production isolation | PASS |

The single WARN is `Git worktree: dirty` caused solely by the untracked
`.claude/` directory — the accepted, non-blocking state for every prior phase.

---

## 13. Production Gateway PID

| Check | Observed |
|-------|----------|
| Production Gateway expected PID | `69355` |
| Production Gateway PID before dry run | `69355` |
| Production Gateway PID after dry run | `69355` |
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

## 15. Forbidden-File / Secret / Boundary Checks

| Check | Observed |
|-------|----------|
| Forbidden files touched | none |
| Code files changed | none |
| OpenAPI files changed | none |
| Test files changed | none |
| Frontend files changed | none |
| Runtime artifacts committed | none |
| `.claude/` committed | no |
| Audit JSONL committed | no |
| Secrets / raw token / full tokenHash / raw arguments / callable exposed | none |
| Provider Schema sent | no |
| Provider API called | no |
| Non-clarify execution | no |
| Production `~/.hermes` accessed | no (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime) |
| Production `state.db` accessed | no |

The diff scope is `docs/webui/` only (see the boundary verification in the
release-commit step).

---

## 16. Go / No-Go Outcome

### 16.1 Go / No-Go rule

| Decision | Condition |
|----------|-----------|
| **GO** | No P0, no P1; all required gates pass; production PID unchanged; route governance unchanged; no forbidden file touched. |
| **NO-GO** | Any P0; any P1; backend regression failed; frontend build failed; smoke failed; route governance changed; production PID changed; provider boundary violated; production access. |

### 16.2 Observed outcome

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

**RC dry-run outcome: GO (`RC-1G-07-001`).**

This is a **release-candidate dry-run** result, not a production release
authorization. It confirms the current `dev-huangruibang` branch — the sealed
Phase 1G-04 mainline on the Phase 1G-05 readiness baseline and the Phase 1G-06
release rehearsal baseline — passes the full release gate sequence through the
committed rehearsal harness, and is eligible to enter Pilot acceptance. The
formal Go / No-Go decision is recorded in
`docs/webui/phase-1g-07-go-no-go-decision.md`.

---

## 17. P0 / P1 / P2 Summary

| Severity | Count | Notes |
|----------|-------|-------|
| P0 | 0 | No boundary violation observed. |
| P1 | 0 | No gate failure observed. |
| P2 | 8 | Carried over from the Phase 1G-05 risk register; non-blocking. |

---

## 18. Non-Reopening Declaration

This validation did **not** reopen Phase 1G-04, Phase 1G-05, or Phase 1G-06, and
did **not** add any product capability. No route, allowlist, execute gate, audit
behavior, frontend capability, or test strength was changed. The only artifacts
produced are the Phase 1G-07 RC docs, the implementation plan update, the risk
register addendum, and consistency updates to the Phase 1G-06 docs' push status.

---

## 19. Phase 1G-08 Addendum — Pilot Acceptance Preparation

Phase 1G-08 (Pilot Acceptance Preparation, Pilot `PILOT-1G-08-001`) re-verified
the current `dev-huangruibang` branch (HEAD `6f9176953…`) through the full
release gate sequence after the RC was pushed. The risk picture is unchanged.

- **No new P0. No new P1.** Phase 1G-08 produced 0 P0 and 0 P1 findings.
- `RC-1G-07-001` remains the GO RC; no supplemental RC was produced.
- Observed Phase 1G-08 gate results: route governance 124 passed / 0 failed;
  related backend regression 19 files 1471 passed / 0 failed; compile /
  `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / unit /
  build pass; smoke A 6 passed / 1 skipped / 0 failed; smoke B 7 passed / 0
  failed; memory-check PASS; dev-check WARN only for `.claude/`; Production
  Gateway PID `69355` unchanged; ports `5180` / `5181` free.
- Pilot pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`; Pilot exit
  criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.

---

*Phase 1G-07 Release Candidate Validation — `RC-1G-07-001`. All required gates
pass; route governance and `STATIC_ALLOWLIST` unchanged; Production Gateway PID
`69355` unaffected; RC dry-run outcome GO.*
