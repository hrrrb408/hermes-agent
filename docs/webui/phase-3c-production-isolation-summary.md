# Phase 3C — Production Isolation Summary

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Production Isolation Summary |
| Status | Verified |
| Date | 2026-06-18 |

## 1. Production Gateway

| Check | Value |
|-------|-------|
| Production Gateway PID before Phase 3C-H1 | 28428 |
| Production Gateway PID after Phase 3C-H1 | 28428 |
| Production Gateway count | 1 |
| Stopped / restarted / replaced / signaled | **no** |

The Production Gateway was never touched by any Phase 3C / 3C-H1 / closeout
step.

## 2. Dev services

| Check | Value |
|-------|-------|
| Dev Gateway final | stopped |
| Dashboard final | not started |
| Bind address | `127.0.0.1` only (5180 WebUI / 5181 Dev API) |
| Port 5180 final | free |
| Port 5181 final | free |

## 3. Production data access

| Check | Value |
|-------|-------|
| `~/.hermes` access | **none** |
| Production `state.db` access | **none** |
| Production rollout | **none** |

All development runtime data used `/Users/huangruibang/Code/hermes-home-dev`.

## 4. How production safety is verified

Production safety is verified by **process / PID / route / gate evidence**:

- `pgrep -f 'hermes_cli.main gateway run'` → PID 28428, count 1.
- `lsof -nP -iTCP:5180 -sTCP:LISTEN` / `5181` → free.
- Route governance tests → 34 / 34 / 5 / 0 / 1 / 1.
- The hardening audit script's production-safety section → PASS.

Production safety is **not** verified by reading `~/.hermes`. The production
home is categorically refused by the dev environment guard and the audit store
root guard.

## 5. Forward commitment

Future phases must not access `~/.hermes` or production `state.db`. Any phase
that would touch production requires a separately authorized safety phase and
explicit human approval.

## 6. Cross-references

- [Smoke + preservation report](phase-3c-h1-smoke-and-preservation-report.md)
- [Final acceptance](phase-3c-final-acceptance.md)
- [Route governance summary](phase-3c-route-governance-summary.md)
