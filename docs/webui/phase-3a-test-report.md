# Phase 3A — Test Report

## Summary

| Suite | Files | Tests | Result |
|-------|-------|-------|--------|
| Backend Phase 3A | 9 | 104 | PASS |
| Frontend Phase 3A | 7 | (part of 887) | PASS |
| Full frontend suite | 60 | 887 | PASS |
| Route governance | 2 | 124 | PASS |
| Preservation (Phase 2) | 18 | — | PASS |
| Smoke `phase3a_workflow_mvp` | 1 spec | — | PASS (skip-if-down) |

## Backend coverage

`workflow_schema_v1`; allowed/forbidden step types + blocked reasons; status
lifecycle; frozen safety boundary; input sanitizer (secrets / tokens / paths /
callables); definition validation.

Store: dev-home confinement; not under repo / `~/.hermes` / production;
definition + execution + timeline round-trip; corruption skipped safely;
persisted documents contain no secrets.

Planner: builds a plan with all six allowed step types; blocks every forbidden
type; blocks real provider, provider write, unsafe path, secret-like input, raw
token.

Step preview: read-only dry-run, fake-provider schema preview (no API call),
sandbox write preview (no write), rollback reference (no execute), manual-note
display, audit query (read-only).

Step execution: manual + approval-gated; step ordering enforced; approval
required + single-use; read-only + fake-provider execute; write/rollback never
execute (preview/reference only).

Approval: scope registered; cannot authorize write/rollback; step + digest +
single-use + TTL enforced.

Audit: events written to the durable store; sanitized (no secrets / raw args /
callable repr); queryable by `eventType=workflow_*`; links preserved.

API: four modes on existing routes (no new route); full HTTP lifecycle;
response shape correct.

Security: no API key / raw token / full hash / raw args / callable repr /
production path in any response; forbidden steps blocked at the API; write +
rollback never executed.

## Frontend coverage

Workflow section renders + nav registration; plan preview (ids, planned +
blocked steps); step list (status tones, cursor, selection); approval gate
(required / ready / none; Execute disabled before approval; write/rollback
preview-only); timeline (events, audit-link navigation, blocked badge); safety
boundary (Blocked/Allowed/Required/Enabled); no-leak across every component.

## Route governance

OpenAPI paths **34**, runtime routes **34**, Tool GET **5**, Tool write HTTP
route **0**, dry-run route **1**, execution route **1**. No new path.

## Production safety

Production Gateway PID `28428` unchanged (1 process); Dev Gateway stopped;
Dashboard not started; 5180/5181 free; no `~/.hermes` access; no production
`state.db` access.
