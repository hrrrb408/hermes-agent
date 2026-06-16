# Phase 3B Test Report

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | All gates PASS |
| Date | 2026-06-16 |

## Backend unit / contract tests (188 cases)

| File | Coverage |
|------|----------|
| `test_dev_web_phase_3b_provider_config.py` | default disabled; real requires enable; missing key → env_missing (no value); base-URL allowlist + https-only; name/model allowlist; timeout/budget/retry clamping; dev-home vs `~/.hermes` |
| `test_dev_web_phase_3b_provider_schema.py` | request/response frozen field sets; forbidden fields excluded; size bounds; blocked/failed builders; token counts surfaced as ints |
| `test_dev_web_phase_3b_provider_redaction.py` | sk-/Bearer/Authorization/PEM detection; secret-field redaction; token counts preserved; callable → placeholder; depth cap; secret → block |
| `test_dev_web_phase_3b_provider_policy.py` | every gating reason; read-only allowlist; write/rollback/shell/db/external/production/plugin blocked with precise reasons; retry classification (auth/policy/budget never retry) |
| `test_dev_web_phase_3b_provider_adapter.py` | OpenAI request shape; response normalization; mock client only; auth-failure no-retry; oversize/malformed/schema-mismatch; 5xx retry exhaustion; mock records no key value |
| `test_dev_web_phase_3b_provider_roundtrip.py` | blocked when disabled/not-enabled/missing-key/bad-url/unsupported-name; completed when enabled; write tool blocked (not executed); secret → block (no network); auth-failure no-retry; budget/rate-limit blocked; preview redacted |
| `test_dev_web_phase_3b_provider_audit.py` | `provider_real_*` written; phase=3B; value-free safeMetadata; no key/auth/raw-token/callable in audit; stray secret re-redacted; production home rejected; dual-write exercised |
| `test_dev_web_phase_3b_provider_tool_allowlist.py` | allowlist == Phase 2A STATIC_ALLOWLIST (immutable); read-only tools pass; write/rollback/shell/db/external/production/plugin/send_message/execute_code/delegate_task blocked; unknown → blocked (never falls back to write) |
| `test_dev_web_phase_3b_provider_api_security.py` | route governance 34/34/5/0/1/1; no provider route; no-leak sweep across response + audit file; token counts preserved; no real network (mock-only) |

## Frontend unit tests (20 cases across 5 files)

`phase3b-provider-boundary`, `phase3b-provider-disabled`,
`phase3b-provider-blocked-reasons`, `phase3b-provider-no-leak`,
`phase3b-provider-readonly-tools`. Plus the full frontend suite (938 tests)
remains green after the panel change.

## Smoke

New additive profile `phase3b_provider_readonly_boundary` wired into `all`.
Fake + blocked-real only — **never** a real network call, **never** real spend.
Asserts: real blocked without enablement; fake still works; `/status`
providerBoundary surfaces (disabled / apiEnabled=false / realReachable=false /
write-blocked) with no secret; route governance unchanged (34 paths, no
provider-real route); UI boundary section + read-only allowlist visible; no
API-key input / Authorization / Bearer in the DOM.

## Gates

- route governance: 34 / 34 / 5 / 0 / 1 / 1 (PASS)
- `python -m compileall hermes_cli` (PASS)
- `ruff check` on all new modules (PASS)
- frontend `pnpm type-check`, `pnpm lint`, `pnpm test`, `pnpm build` (PASS)
- `scripts/run-dev-hermes.sh memory-check`, `dev-check` (PASS)
- Production Gateway PID `28428` unchanged; ports 5180/5181 free.
