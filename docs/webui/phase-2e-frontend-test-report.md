# Phase 2E — Frontend Test Report

## Summary

Phase 2E is frontend UX polish. All frontend gates pass with **zero regressions**
to the existing 40-file suite, and a new suite of Phase 2E tests covers the
unified developer console, the reusable state components, the cross-navigation
bridge, and the no-leak invariants.

## Frontend gates

| Gate | Command | Result |
|---|---|---|
| Type check | `pnpm type-check` (`vue-tsc --noEmit`) | PASS |
| Lint | `pnpm lint` (eslint) | PASS (0 errors, 0 warnings) |
| Unit tests | `pnpm test` (vitest, jsdom) | **807 passed** / 0 failed (47 files) |
| Production build | `pnpm build` (`vue-tsc -b && vite build`) | PASS |

## New Phase 2E vitest files

| File | Tests | Covers |
|---|---|---|
| `src/tests/phase2e-foundations.spec.ts` | 19 | formatters, safetyBadges, blockedReasons (known + unknown fallback + no-bypass), frozenBaseline (34/34/5/0/1/1, PID 28428, phase timeline) |
| `src/tests/phase2e-common-components.spec.ts` | 10 | LoadingState / EmptyState / ErrorState (retry emit) / BlockedReasonPanel (known + unknown) / AuditIdLink (lossy + emits full id) |
| `src/tests/phase2e-devconsole-nav.spec.ts` | 6 | section persistence + restore + invalid fallback + `prefillAuditSearch` (switches section, enables store mode, sets filter, **fires load**) + clear |
| `src/tests/phase2e-overview.spec.ts` | 7 | phase status, frozen route governance, safety badges, live policy + audit cards, next actions, **no execution POST**, no API-key/shell input |
| `src/tests/phase2e-tool-execution.spec.ts` | 3 | reused panel renders 6-tool selector, no API-key input, cross-nav strip appears after execute |
| `src/tests/phase2e-provider-roundtrip.spec.ts` | 3 | mode selector + real-blocked messaging, no API-key input, BlockedReasonPanel on blocked result |
| `src/tests/phase2e-write-rollback.spec.ts` | 4 | write surface + sandbox flags + rollback id, no production path, BlockedReasonPanel on blocked write |
| `src/tests/phase2e-audit-viewer.spec.ts` | 4 | store toggle + filters + pagination, prefill marker + clear, no raw token/hash/callable |
| `src/tests/phase2e-safety-boundary.spec.ts` | 5 | invariant badges, frozen 34/34/5/0/1/1, PID 28428, grouped surfaces, "do not bypass" present |
| `src/tests/phase2e-accessibility.spec.ts` | 5 | nav rail tablist + roving tabindex, ArrowDown/Home/End keyboard nav, no API-key/shell across sections, no leak markers |

Updated existing tests: `src/tests/router.spec.ts` (+4 cases for `/console`),
`src/tests/top-status-bar.spec.ts` (RouterLink stub lets the real class fall
through; +1 Dev Console link case).

## Test-file location note

The Phase 2E spec listed the vitest paths as
`apps/hermes-dev-webui/tests/phase2e-*.test.ts`. They are placed at
`apps/hermes-dev-webui/src/tests/phase2e-*.spec.ts` instead, to match the
established 40-file `src/tests/*.spec.ts` convention (same vitest config, same
jsdom setup, same `pnpm test` runner). The Playwright smoke spec is at
`apps/hermes-dev-webui/tests/smoke/phase-2e-frontend-ux-polish-smoke.spec.ts`
(matching the `tests/smoke/` convention). Functionally equivalent; documented
here for traceability.

## Backend contract test

`tests/test_dev_web_phase_2e_frontend_contract.py` — **9 passed**:
- GET /tools/policy shape + safety invariants (readOnly true, writeEnabled false, execution.enabled false)
- GET /tools/policy + /tools/audit-events bodies leak-free (no `sk-`, `Bearer`, `<function`, `object at 0x`, `/Users/huangruibang/.hermes`, raw args/token/hash)
- Route governance unchanged: OpenAPI 34, tool GET 5, no dedicated tool-write HTTP route, dry-run + execute present, no provider route

## Smoke / E2E

`tests/smoke/phase-2e-frontend-ux-polish-smoke.spec.ts` (Playwright) +
`scripts/run-dev-webui-execute-audit-smoke.sh phase2e_frontend_ux_polish`. The
`all` sequence now runs blocked → completed → phase2a → phase2b → phase2c →
phase2c_h1 → phase2d → **phase2e**. The phase2e profile enables all execution
gates + `HERMES_PROVIDER_MODE=fake` + `HERMES_TOOL_WRITE_EXECUTION_ENABLED=true`
so every console section is demonstrable end-to-end. PID baseline stays 28428.

## Preservation

All pre-existing frontend tests (40 files) and backend preservation tests
(Section 28.4/28.5 of the runbook) continue to pass unchanged — Phase 2E is
additive and touches no existing behavior.
