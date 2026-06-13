# Phase 1G-09: Pilot Evidence Index — `PILOT-EXEC-1G-09-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-09 |
| Title | Pilot Evidence Index |
| Status | Filled (Pilot executed) |
| Date | 2026-06-14 |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Scope | Text-summary evidence index for the Pilot run. No raw logs / screenshots / audit JSONL committed. |

---

## 1. Evidence Policy

- Evidence is captured as **text summaries only**: command, summary, result,
  stored-artifact status, related scenario.
- No raw log file, `test-results/`, `playwright-report/`, screenshot, runtime
  JSONL, or audit JSONL is committed. Build / test / smoke artifacts are either
  gitignored (`dist/`, `test-results/`, `*.tsbuildinfo`, caches) or
  self-cleaned by the committed smoke harness (`/tmp/hermes-p1g06-smoke-*.log`).
- No evidence entry contains a secret, an API key, the raw confirmation token,
  the full token hash, or raw arguments.

---

## 2. Evidence Index

### EV-1G09-001 — Route governance tests

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-001 |
| Source command | `./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py -- -q` |
| Summary | Route governance + closure tests. OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 / dry-run 1 / execution 1; `STATIC_ALLOWLIST = frozenset({"clarify"})`. |
| Result | 124 passed / 0 failed (2 files). |
| Stored artifact | none committed. |
| Related scenario | C, L, M. |

### EV-1G09-002 — Related backend regression (19 files)

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-002 |
| Source command | `./scripts/run_tests.sh <19 dev_web tool / closure test files> -- -q` |
| Summary | Dry-run, confirmation token, digest, pre/post-execution audit, handler lookup, dispatch, handler call, policy API, schema preview, audit read — all dev WebUI controlled-execution chain tests. |
| Result | 1471 passed / 0 failed (19 files). |
| Stored artifact | none committed. |
| Related scenario | C, D, G, H, I, L, M. |

### EV-1G09-003 — Backend compileall

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-003 |
| Source command | `python -m compileall <14 dev_web_*.py modules>` |
| Summary | Byte-compile of the dev WebUI controlled-execution modules. |
| Result | exit 0 (all compiled). |
| Stored artifact | none committed (`.pyc` under gitignored `__pycache__/`). |
| Related scenario | M. |

### EV-1G09-004 — toolsets.py compile

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-004 |
| Source command | `python -m py_compile toolsets.py` |
| Summary | Confirm `toolsets.py` (allowlist / toolset surface) compiles. |
| Result | OK (exit 0). |
| Stored artifact | none committed. |
| Related scenario | C, L, M. |

### EV-1G09-005 — Backend ruff

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-005 |
| Source command | `ruff check <8 dev_web_*.py + 6 test files>` |
| Summary | Lint the dev WebUI controlled-execution modules and their tests. |
| Result | All checks passed. |
| Stored artifact | none committed. |
| Related scenario | M. |

### EV-1G09-006 — Git baseline evidence

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-006 |
| Source command | `git rev-parse HEAD` / `git rev-parse origin/dev-huangruibang` / `git status --short --branch` |
| Summary | Baseline at execution: local == remote == `9812c069e`; ahead/behind 0/0; tracked worktree clean; only `.claude/` untracked. |
| Result | baseline confirmed. |
| Stored artifact | none committed. |
| Related scenario | M, N. |

### EV-1G09-007 — Smoke Profile A (blocked)

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-007 |
| Source command | `./scripts/run-dev-webui-execute-audit-smoke.sh all` (Profile A) |
| Summary | Profile A — `blocked_tool_handler_call_not_enabled`. `toolHandlerCalled=false`; `executionCompleted=false`; provider / external flags false; WebUI + Dev API started on 127.0.0.1; UI Execute + Audit sub-tabs render; UI dry-run safe decision (no raw token). |
| Result | 6 passed / 1 skipped / 0 failed. |
| Stored artifact | none committed (harness self-cleans `/tmp` logs; `test-results/` gitignored). |
| Related scenario | A, B, C, D, E, G, H, J, K, L, O. |

### EV-1G09-008 — Smoke Profile B (completed)

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-008 |
| Source command | `./scripts/run-dev-webui-execute-audit-smoke.sh all` (Profile B) |
| Summary | Profile B — `clarify_execution_completed`; `canonicalName=clarify`; `handlerCallId` present (`thc_`); `postExecutionAuditId` present (`pexa_`); provider / external flags false; post-execution audit visible in audit viewer API; UI dry-run safe decision (no raw token). |
| Result | 7 passed / 0 failed. |
| Stored artifact | none committed. |
| Related scenario | A, B, C, D, F, G, H, I, J, K, L, O. |

### EV-1G09-009 — Frontend type-check

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-009 |
| Source command | `pnpm type-check` (in `apps/hermes-dev-webui`) |
| Summary | `vue-tsc --noEmit` over the Vue 3 + TypeScript workbench. |
| Result | pass (exit 0). |
| Stored artifact | none committed. |
| Related scenario | A, B. |

### EV-1G09-010 — Frontend lint

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-010 |
| Source command | `pnpm lint` (in `apps/hermes-dev-webui`) |
| Summary | `eslint .` over the workbench source. |
| Result | 0 errors / 0 warnings. |
| Stored artifact | none committed. |
| Related scenario | A, B. |

### EV-1G09-011 — Production Gateway PID before / after

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-011 |
| Source command | `ps aux \| grep '[h]ermes_cli.main gateway run'` |
| Summary | Production Gateway process read-only check before and after the Pilot. |
| Result | PID `69355` before and after; exactly one production gateway process; not stopped / restarted / replaced. |
| Stored artifact | none committed. |
| Related scenario | N. |

### EV-1G09-012 — Final ports

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-012 |
| Source command | `lsof -nP -iTCP:5180 -sTCP:LISTEN` / `lsof -nP -iTCP:5181 -sTCP:LISTEN` |
| Summary | Final dev port state after server teardown. |
| Result | 5180 free; 5181 free (empty lsof output). |
| Stored artifact | none committed. |
| Related scenario | O, N. |

### EV-1G09-013 — dev-check

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-013 |
| Source command | `./scripts/run-dev-hermes.sh dev-check` |
| Summary | Full dev WebUI gate. OpenAPI 34; runtime 34; Tool policy 5; Tool write 0; dry-run 1; execution 1; `Static allowlist: clarify`; `Provider tool schema: not sent`; `Tool execution: disabled`; production isolation PASS; avoids `~/.hermes`. |
| Result | WARN (only `Git worktree: dirty` from `.claude/` untracked — the expected acceptable state). |
| Stored artifact | none committed. |
| Related scenario | C, J, L, M. |

### EV-1G09-014 — memory-check + environment scrub

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-014 |
| Source command | `./scripts/run-dev-hermes.sh memory-check`; environment scrub (`unset` Provider keys + execute gates). |
| Summary | Dev memory store integrity; `HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev`; all Provider keys and execute gates unset; smoke harness refused production `~/.hermes`. |
| Result | memory-check PASS; environment SAFE. |
| Stored artifact | none committed. |
| Related scenario | K, N. |

### EV-1G09-015 — Frontend unit + build

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-015 |
| Source command | `pnpm test` / `pnpm build` (in `apps/hermes-dev-webui`) |
| Summary | Vitest unit suite + Vite production build. |
| Result | unit 674 passed / 31 files; build 1862 modules transformed (exit 0). |
| Stored artifact | none committed (`dist/` gitignored). |
| Related scenario | A, B. |

### EV-1G09-016 — Artifact cleanup

| Field | Value |
|------|-------|
| Evidence ID | EV-1G09-016 |
| Source command | `git status --short --branch`; `git status --ignored --short` |
| Summary | Confirm no raw log / screenshot / audit JSONL / runtime artifact is staged or committed after the Pilot; `dist/`, `test-results/`, `*.tsbuildinfo`, caches are gitignored; `playwright-report/` absent; harness `/tmp` logs self-cleaned. |
| Result | tracked worktree clean; only `.claude/` untracked; no audit JSONL / runtime artifact committed. |
| Stored artifact | none committed. |
| Related scenario | N, O. |

---

## 3. Cross-References

- Per-scenario results: `docs/webui/phase-1g-09-pilot-acceptance-record.md`.
- Defect / feedback log: `docs/webui/phase-1g-09-pilot-defect-feedback-log.md`.
- Final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.
- Smoke harness runbook: `docs/webui/phase-1g-06-smoke-harness-runbook.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

*Phase 1G-09 Pilot Evidence Index — `PILOT-EXEC-1G-09-001`. Text summaries
only; no raw logs / screenshots / audit JSONL / secrets committed.*
