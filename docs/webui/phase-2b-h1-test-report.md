# Phase 2B-H1 — Test Report

| Field | Value |
|-------|-------|
| Hardening ID | `HARDENING-2B-H1-001` |
| Date | 2026-06-14 |
| Input HEAD | `a3cd3b762e947ba5b93d676557c47ac9487a0649` |
| Status | **PASS** |

---

## 1. Commands run

All backend test commands use `scripts/run_tests.sh` (per-file subprocess
isolation; `env -i`; `TZ=UTC`; `PYTHONHASHSEED=0`). Frontend commands use
`pnpm` in `apps/hermes-dev-webui`. pytest flags are passed after `--`.

---

## 2. Test counts

| Suite | Files | Tests | Failed |
|-------|-------|-------|--------|
| Phase 2B provider backend (schema/request/fake/roundtrip/audit/security) | 6 | 74 | 0 |
| Lens 5 controlled-chain (roundtrip + 2A chain) | 8 | 419 | 0 |
| Phase 2B-H1 hardening boundaries (new) | 1 | 66 | 0 |
| Section 25.6 full related backend regression | 32 | 1864 | 0 |
| Frontend unit tests (Vitest) | 35 | 708 | 0 |

---

## 3. Repeated run counts (flake closure)

| Regime | Cycles | Result |
|--------|--------|--------|
| Isolated flake variant `[audit_events_read]` | 10 | 10/10 pass |
| Full `test_dev_web_phase_2a_hardening_boundaries.py` | 10 | 10/10 pass |
| High-parallelism batch (8 audit+hardening files, `-j 28`) | 10 | 10/10 pass |
| Section 25.4 provider audit + hardening boundaries | 10 | 10/10 pass |
| Hardening audit script internal repeated audit/redaction | 5 | 5/5 pass |
| Hardening boundary test parametrized repeats (3 scenarios ×5) | 15 (within one run) | 15/15 pass |

Total deterministic reruns relevant to the flake: **60+, 0 failures.**

---

## 4. Smoke / E2E

`./scripts/run-dev-webui-execute-audit-smoke.sh all` — **Overall PASS**.

Profiles: `blocked` PASS, `completed` PASS, `phase2a` PASS,
`phase2b_provider_fake_roundtrip` PASS (6/6: API round-trip, tool-write
disabled, real blocked, audit queryable, UI panel visible, UI round-trip
renders).

Final state: Port 5180 free, Port 5181 free, Production Gateway PID 1962
unchanged.

---

## 5. Frontend results

| Gate | Result |
|------|--------|
| `pnpm type-check` (`vue-tsc --noEmit`) | PASS |
| `pnpm lint` (`eslint .`) | PASS |
| `pnpm test` (Vitest) | 35 files / 708 tests PASS |
| `pnpm build` (`vue-tsc -b && vite build`) | PASS (1868 modules) |

No UI API-key input; no non-allowlisted tool selectable; real mode blocked in UI.

---

## 6. Backend results

| Gate | Result |
|------|--------|
| Hardening audit script (full, with smoke) | 14/14 lens checks PASS; Overall PASS; exit 0 |
| Phase 2B provider tests | 74 PASS / 0 failed |
| Phase 2B-H1 hardening boundaries | 66 PASS / 0 failed |
| Phase 1G/2A preservation | PASS |
| Lens 5 controlled chain | 419 PASS / 0 failed |
| Section 25.6 full regression | 1864 PASS / 0 failed |
| `compileall` (provider + tool + registry modules) | OK |
| `py_compile toolsets.py` | OK |
| `ruff check` (provider modules + tests) | All checks passed |

---

## 7. Production safety results

| Check | Result |
|-------|--------|
| Production Gateway PID | 1962 (unchanged before/during/after) |
| Production Gateway count | 1 |
| Dev Gateway | stopped |
| Dashboard | not started |
| Port 5180 | free |
| Port 5181 | free |
| `~/.hermes` access | none performed |
| Production `state.db` access | none performed |
| Real Provider API call | none (fake mode only; real blocked) |
| Tool write | none (Tool write = 0) |

---

## 8. Final gate conclusion

All backend, frontend, smoke/E2E, hardening audit, repeated flake-closure,
memory-check, dev-check, compile/lint, and production-safety gates passed.
**0 P0. 0 P1.** The Phase 2B P2 transient flake is closed as non-reproduced;
the latent provider-audit secret-pattern gap found alongside it is fixed.

Phase 2C was not started.
