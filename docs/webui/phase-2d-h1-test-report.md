# Phase 2D-H1 — Test Report

## Commands run

All backend tests via the hermetic wrapper `scripts/run_tests.sh` (clean env,
TZ=UTC, no leaked credentials). Frontend via `pnpm`. Smoke via
`scripts/run-dev-webui-execute-audit-smoke.sh`. `HERMES_HOME` is the dev home
(`/Users/huangruibang/Code/hermes-home-dev`); no `~/.hermes` access.

## New hardening tests (Phase 2D-H1)

Three new test files, all passing:

| File | Tests | Focus |
|------|------:|-------|
| `test_dev_web_phase_2d_h1_audit_store_hardening.py` | 32 | Lens 3/6/7: 32-thread concurrency, sequence flooring, append recovery, large batch, oversized-line guard, writer-lock location, rotation by size/count, segment recovery, all corruption classes, quarantine non-destructive, query-skips-corrupt, 5× repeated-run stability |
| `test_dev_web_phase_2d_h1_audit_consistency.py` | 32 | Lens 4/5/8: index build/repair, index==scan for all 9 fields, cursor asc/desc/tamper/mismatch, validation rejections, all filters, offset compat, cursor token whitelist, dual-write all 7 kinds |
| `test_dev_web_phase_2d_h1_audit_security.py` | 70 | Lens 1/2/9/10: schema rejections, sanitizer no-str-fallback + full secret/field matrix, validate_sanitized_event, strip_forbidden_keys, API no-leak across 7 kinds, index/quarantine no secrets, cursor whitelist, gitignore, minimal-safe-event fallback |

**New hardening tests: 134, 0 failed.**

## Phase 2D + 2D-H1 backend (audit)

```
scripts/run_tests.sh tests/test_dev_web_phase_2d_audit_*.py
                      tests/test_dev_web_phase_2d_h1_*.py  -- -q
```

**Result: 13 files, 330 tests passed, 0 failed.**

## Full related backend regression (Phase 1G / 2A / 2B / 2C / 2C-H1 / 2D / 2D-H1)

60 files spanning the read-only registry, dry-run, execute, handler chain,
provider round-trip, controlled write, rollback + confirmation token, and the
full durable audit store + hardening surface.

**Result: 60 files, 2458 tests passed, 0 failed.**

## Route governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |

No new HTTP route, no Tool write HTTP route. The audit-events route remains
GET-only.

## Compile / Ruff

```
python -m compileall hermes_cli/dev_web_audit_*.py hermes_cli/dev_web_tool_audit_read.py  → OK
python -m py_compile toolsets.py                                                         → OK
ruff check hermes_cli/dev_web_audit_*.py tests/test_dev_web_phase_2d_h1_*.py              → All checks passed
```

## Frontend gates

| Gate | Result |
|------|--------|
| `pnpm type-check` (`vue-tsc --noEmit`) | pass |
| `pnpm lint` (`eslint .`) | pass |
| `pnpm test` (Vitest) | 737 tests pass (37 files) |
| `pnpm build` (`vite build`) | pass |

No frontend change was required for the hardening phase; the existing store-mode
coverage continues to pass.

## Smoke / E2E

```
./scripts/run-dev-webui-execute-audit-smoke.sh all
```

All profiles PASS, including `phase2d_audit_store_indexing` (9 Playwright
tests). Production Gateway PID 28428 unchanged; ports 5180 / 5181 free at end.

## Hardening audit script

```
./scripts/run-dev-webui-phase2d-hardening-audit.sh
```

10 conceptual lenses + preservation + repeated-run (5/5) + memory/dev-check +
frontend + smoke + production safety → **15 lens checks PASS, 0 FAIL**.
`Overall: PASS`.

## Hermes gates

| Gate | Result |
|------|--------|
| `run-dev-hermes.sh memory-check` | PASS |
| `run-dev-hermes.sh dev-check` | PASS |
| Production isolation | PASS |
| Avoids `~/.hermes` | yes |

## Production safety

- Production Gateway PID before / after: **28428** (unchanged).
- Production Gateway process count: **1**.
- Not stopped / restarted / replaced / signaled.
- Dev Gateway stopped; Dashboard not started.
- Ports 5180 / 5181 free at end.
- No `~/.hermes` access; no production `state.db` access.

## Boundary searches

- No runtime artifacts (audit-store / token / rollback / JSONL) staged.
- Secret terms appear only in security docs, sanitizer rules, negative
  assertions, and test names.
- No shell command execution / database mutation / external service write
  introduced.
- No production `~/.hermes` or `state.db` access.
- `.claude/` not committed.

## Final gate conclusion

**PASS.** 0 P0, 0 P1. Backend (2458) + frontend (737) + smoke (all profiles) +
memory/dev-check + route governance + production safety all green. The durable
audit store is hardened; Phase 2E remains not started.
