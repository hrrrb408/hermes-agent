# Phase 3D — Production Isolation Summary

| Field | Value |
|-------|-------|
| Phase | 3D (Closeout) |
| Title | Static Plugin Descriptor Registry — Production Isolation Summary |
| Status | Isolated |
| Date | 2026-06-19 |
| Summary ID | `PHASE-3D-PRODUCTION-ISOLATION-001` |

> Consolidated production-isolation evidence for the Phase 3D Static Plugin
> Descriptor Registry after Implementation and the H1 12-lens hardening.

## 1. Production Gateway

| Check | Value |
|-------|-------|
| Production Gateway PID before Phase 3D Implementation | `28428` |
| Production Gateway PID after Phase 3D Implementation | `28428` |
| Production Gateway PID after Phase 3D-H1 | `28428` |
| Production Gateway PID after closeout | `28428` |
| Production Gateway process count | `1` |
| Stopped / restarted / replaced / signaled / reconfigured | **none** |

## 2. Dev services

| Check | Value |
|-------|-------|
| Dev Gateway final | **stopped** |
| Dashboard final | **not started** |
| Port 5180 final | **free** |
| Port 5181 final | **free** |
| Dev service bind host | `127.0.0.1` only |

## 3. Production data / paths

| Check | Value |
|-------|-------|
| `~/.hermes` access | **none** |
| Production `state.db` access | **none** |
| Production rollout | **none** |
| Runtime artifacts committed | **none** |
| `.claude/` committed | **none** |

## 4. Provider / network

| Check | Value |
|-------|-------|
| Live provider request | **none** |
| Real API-key read | **none** |
| External network call | **none** |

The hardening audit script unsets every provider live flag + API key before any
gate, refuses the production HERMES_HOME categorically, and verifies PID `28428`
(count 1) + ports 5180 / 5181 free at the end of every run.

## 5. How production safety is verified

Production safety is verified by **PID / process / port / route / gate evidence**,
not by reading `~/.hermes`:

- `pgrep -f 'hermes_cli.main gateway run'` → exactly PID `28428`, count `1`.
- `lsof -nP -iTCP:5180 -sTCP:LISTEN` / `-iTCP:5181` → free.
- Route governance gate → 34 / 34 / 5 / 0 / 1 / 1 (no production route added).
- `git diff --cached` staging guard → no runtime artifact / `.claude` staged.

**Production safety is not verified by reading `~/.hermes`.** Future phases must
not access `~/.hermes`.

## 6. Dev WebUI environment guard

The Dev WebUI backend uses a **precise allowlist** (`enforce_dev_environment()`):
source root must resolve to the dev source root; `HERMES_HOME` must resolve to
the dev home; dev services bind `127.0.0.1` only. Any mismatch fails closed
(refuse to start, refuse all API requests).

## 7. Cross-references

- [Closeout](phase-3d-closeout.md)
- [Route governance summary](phase-3d-route-governance-summary.md)
- [Test gate summary after H1](phase-3d-test-gate-summary-after-h1.md)
- [Final security boundary after H1](phase-3d-final-security-boundary-after-h1.md)
- [H1 smoke / preservation / production isolation](phase-3d-h1-smoke-and-preservation-report.md)
