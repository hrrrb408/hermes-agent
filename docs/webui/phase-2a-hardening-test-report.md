# Phase 2A-H1 — Hardening: Test Report

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2A-H1 |
| Title | Hardening Test Report |
| Status | Completed |
| Date | 2026-06-14 |
| Hardening ID | `HARDENING-2A-H1-001` |
| Input HEAD | `0527d6c892b24afde03ff9259a612b2f59ee8018` |
| Branch | `dev-huangruibang` |
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` (dev) |

---

## 1. Commands Run

| Command | Result |
|---------|--------|
| `./scripts/run-dev-webui-phase2a-hardening-audit.sh` | Overall PASS (10/10 checks, exit 0) |
| `./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py -- -q` | 124 passed / 0 failed |
| Phase 2A backend (registry / dry-run / execute / security-boundaries) | 156 passed / 0 failed |
| Phase 2A audit (read-only audit + dry-run-audit + pre/post audit + audit-read + audit-read-api) | 204 passed / 0 failed |
| Phase 1G clarify chain (execute / confirmation / digest / preflight / handler-call / dispatch / handler-lookup / pre/post audit) | 626 passed / 0 failed |
| `tests/test_dev_web_phase_2a_hardening_boundaries.py` (new deterministic 7-lens) | 45 passed / 0 failed |
| Full §24.4 related backend regression (24 files) | 1679 passed / 0 failed |
| `pnpm type-check` | PASS (clean) |
| `pnpm lint` | PASS (clean) |
| `pnpm test` | 692 passed / 0 failed (33 files) |
| `pnpm build` | PASS (1863 modules) |
| `./scripts/run-dev-webui-execute-audit-smoke.sh all` | Overall PASS |
| `./scripts/run-dev-hermes.sh memory-check` | PASS |
| `./scripts/run-dev-hermes.sh dev-check` | PASS |

---

## 2. Backend Test Counts (per lens)

| Lens | Files | Tests passed | Failed |
|------|-------|--------------|--------|
| 1 — Phase 1G Preservation | 10 | 626 | 0 |
| 2 — Allowlist / Registry | (in 4-file group) | — | 0 |
| 3 — Route Governance | 2 | 124 | 0 |
| 4 — Provider / Write / Side-effect | (in 4-file group) | — | 0 |
| 2 + 4 combined group | 4 | 156 | 0 |
| 5 — Audit Redaction | 6 | 204 | 0 |
| 6 + 7 — Hardening Boundary (deterministic) | 1 | 45 | 0 |
| **Full §24.4 regression** | **24** | **1679** | **0** |

> The 24-file §24.4 regression supersedes the per-lens sub-totals (the lens
> files are a subset of the 24). 0 failed across every grouping.

---

## 3. Frontend Test Counts

| Gate | Result |
|------|--------|
| `vue-tsc --noEmit` (type-check) | PASS — clean |
| `eslint .` (lint) | PASS — clean |
| `vitest` (unit) | **692 passed / 0 failed** (33 files) |
| `vite build` (production build) | PASS — 1863 modules |

Frontend test coverage for Phase 2A contract:
`tool-execute-phase-2a.spec.ts` (6 selectable tools, per-tool argument
building, `<toolId>_execution_completed`, blocked on `executionCompleted=false`,
no raw token), `tool-execute-panel-phase-2a.spec.ts` (selector, badges,
structured result, side-effect flags false, clarify legacy preserved).

---

## 4. Smoke / E2E Profile Counts

| Profile | Result |
|---------|--------|
| `blocked` (Profile A — `blocked_tool_handler_call_not_enabled`) | PASS (exit 0) |
| `completed` (Profile B — `clarify_execution_completed`) | PASS (exit 0) |
| `phase2a` (Profile C — read-only multi-tool) | **7 passed / 0 failed** |
| Smoke `all` Overall | **PASS** |

Smoke final state: Production Gateway PID `1962` (unchanged); ports `5180` /
`5181` free; bind `127.0.0.1` only.

---

## 5. Production PID Result

| Check | Value |
|-------|-------|
| Production Gateway expected PID | 1962 |
| Production Gateway observed PID (pre) | 1962 |
| Production Gateway observed PID (post) | 1962 |
| Production Gateway process count | 1 |
| Production Gateway command | `hermes_cli.main gateway run --replace` |
| Production Gateway stopped / restarted / replaced / signaled | no / no / no / no |
| Dev Gateway final | stopped |
| Dashboard final | not started |
| Port 5180 final | free |
| Port 5181 final | free |
| `~/.hermes` access | none |
| Production `state.db` access | none |

---

## 6. Compile / Ruff

| Check | Result |
|-------|--------|
| `python -m compileall` (read-only + tool-execute scope) | PASS |
| `python -m py_compile toolsets.py` | PASS |
| `ruff check` (read-only + Phase 2A + hardening + closure test files) | PASS — clean |

---

## 7. Deviations

None. No gate deviated from its expected result. The Phase 2A seal-time full
backend suite reference count (2149) was the **broader** dev_web suite; the
24-file §24.4 related-regression subset totalled **1679 passed / 0 failed**,
which is the correct, expected count for that file set. The hard invariant is
**0 failed**, which holds.

---

## 8. Final Gate Conclusion

**All gates PASS. 0 P0. 0 P1. 0 failed tests across backend, frontend, smoke,
memory-check, and dev-check.** The deterministic hardening audit script
(`run-dev-webui-phase2a-hardening-audit.sh`) reports **Overall PASS** with a
zero exit code and confirms Production Gateway PID `1962` unchanged, ports
free, and all seven lens boundaries intact.

Phase 2A-H1 Hardening is complete and eligible for commit + push.
