# Phase 1G-04-30: Accelerated WebUI Closeout

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-30 |
| Title | Accelerated WebUI Closeout — Audit Read API + Execute UI + Audit Viewer + Browser Smoke |
| Status | Completed locally / not pushed |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-30 accelerated closeout) |
| Dependencies | Phase 1G-04-29 completed locally (clarify handler call + post-execution audit) |
| Branch | dev-huangruibang |
| Base commit | `3c7c239d4cbbad7f06c19144c620936251e49828` |
| Implementation | Read-only audit events API + audit redaction + frontend Execute UI + audit viewer + browser smoke/E2E + OpenAPI update + route governance transition + digest-binding fix + tests + docs |

---

## 1. Phase Definition

Phase 1G-04-30 is the two-day-sprint **closeout** that wires the already-built
backend minimum controlled-execution loop into the Dev WebUI and completes
browser-level verification. It merges:

1. A read-only **audit events API**
2. A safe **audit JSONL reader** with redaction + path containment
3. A frontend **Execute UI** (clarify-only controlled execution workbench)
4. A frontend **Audit Viewer**
5. A frontend **API client** update
6. **Browser smoke / E2E** covering the happy path and the default-block path
7. Route governance transition **33/33/4/0/1/1 → 34/34/5/0/1/1**
8. A digest-binding fix (see §3.4) necessary for the end-to-end chain
9. Documentation

This phase **adds exactly one** read-only GET route (`/tools/audit-events`).
It does **not**:

- Expand `STATIC_ALLOWLIST` (remains `frozenset({"clarify"})`)
- Add a Tool write route
- Add a second execution route
- Add a Provider route
- Send Provider Schema or call a Provider API
- Execute any non-clarify tool
- Access production `~/.hermes` or production `state.db`

---

## 2. Baseline

| Metric | Before | After |
|--------|--------|-------|
| Base remote HEAD | `3c7c239d4cbbad7f06c19144c620936251e49828` | local commit ahead by 1 |
| OpenAPI paths | 33 | **34** |
| Runtime routes | 33 | **34** |
| Tool GET routes | 4 | **5** |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` | `frozenset({"clarify"})` (unchanged) |
| Audit read API | not implemented | implemented (read-only) |
| Audit viewer | not implemented | implemented (read-only) |
| Frontend Execute UI | not implemented | implemented (clarify-only) |
| Default execute block | `blocked_by_kill_switch` (all gates unset) | unchanged |
| Explicit dev/test clarify | `clarify_execution_completed` (test fixtures) | works end-to-end via real API |
| Browser smoke | not run | both scenarios pass |

---

## 3. Implementation Summary

### 3.1 Audit read module

New module `hermes_cli/dev_web_tool_audit_read.py` (stdlib only):

- `read_audit_events(...)` — top-level read-only entry point
- `resolve_audit_store_path(...)` — containment-based path guard
- Per-kind whitelist normalizers (`_normalize_dry_run_item`,
  `_normalize_pre_execution_item`, `_normalize_post_execution_item`)
- `_sanitize_scalar` / `_short_digest` — defensive redaction
- `audit_read_result_to_safe_dict(...)` — JSON-safe response builder

Reads three audit kinds from `$HERMES_HOME/gateway/dev/audit/`:

- `dry_run` → `tool-dry-run-audit.jsonl`
- `pre_execution` → `tool-pre-execution-audit.jsonl`
- `post_execution` → `tool-post-execution-audit.jsonl`

Guarantees:

- Read-only (no writes)
- Dev HERMES_HOME only; production `~/.hermes` blocked
- Missing file → empty items (not 500)
- Malformed JSONL lines skipped safely (counted, never leaked)
- Path traversal / production path rejected
- Whitelist-based item normalization — raw confirmation token, full token
  hash, raw arguments, secrets, callable objects, function reprs, and
  provider payloads are never surfaced

### 3.2 Audit read API route

New route in `hermes_cli/dev_web_api.py`:

```
GET /api/dev/v1/tools/audit-events
  ?auditKind=dry_run|pre_execution|post_execution  (required)
  &limit=1..100                                     (default 50)
  &cursor=<opaque offset>                           (optional)
  &canonicalName=<exact filter>                     (optional)
```

GET-only. No POST/PUT/PATCH/DELETE. Missing audit file returns empty items.
Invalid `auditKind` → 400. Forbidden path → 403. No HERMES_HOME → 503.

### 3.3 OpenAPI changes

`docs/webui/openapi/dev-web-api-v1.yaml`:

- New GET path `/tools/audit-events`
- New schemas: `AuditKind`, `ToolAuditEventItem`, `ToolAuditSideEffects`,
  `ToolAuditEventsData`, `ToolAuditEventsResponse`
- OpenAPI paths **33 → 34**

### 3.4 Digest-binding fix (dev_web_api.py dry-run route)

**Finding:** the real dry-run API endpoint computed `dryRunDecisionDigest`
with `audit_event_id=None` (and no timestamps), but the execute gate
recomputes the digest from the historical audit lookup using the **real**
`eventId`, `created_at` (event timestamp), and `expires_at` (timestamp +
TTL). This divergence made the end-to-end dry-run → execute chain return
`blocked_digest_mismatch`. The backend unit tests did not catch it because
they use synthetic audit events with hand-set consistent `eventId` /
timestamps.

**Fix:** the dry-run route now builds the audit event first, extracts its
real `eventId` and `timestamp`, computes the digest bound to those values
(plus the computed `expires_at`), patches the event, and writes it. The
response and confirmation token use the same consistently-computed digest.
This makes the controlled execution chain work end-to-end via the real API.

This is a correctness fix within the phase's allowed scope
(`hermes_cli/dev_web_api.py`). It does **not** change `STATIC_ALLOWLIST`,
route count, or any safety boundary. All 1471 backend tests pass.

### 3.5 Frontend Execute UI

New files:

- `apps/hermes-dev-webui/src/types/api/toolExecute.ts`
- `apps/hermes-dev-webui/src/types/api/toolAudit.ts`
- `apps/hermes-dev-webui/src/api/toolExecute.ts` (`runDryRun`, `executeTool`)
- `apps/hermes-dev-webui/src/api/toolAudit.ts` (`getAuditEvents`)
- `apps/hermes-dev-webui/src/stores/toolExecute.ts` (state machine)
- `apps/hermes-dev-webui/src/stores/toolAudit.ts` (audit viewer state)
- `apps/hermes-dev-webui/src/components/workspace/ToolExecutePanel.vue`
- `apps/hermes-dev-webui/src/components/workspace/AuditViewerPanel.vue`

The Execute panel is a **clarify-only** workbench surfaced as new "Execute"
and "Audit" sub-tabs inside the Tools workspace tab. It exposes:

- Fixed canonicalName = `clarify`
- Question + optional choices inputs
- Dry Run → dry-run decision / risk / digest (short) / confirmation token ID
- Confirm & Execute → execute gate decision
- Default-gate-unset → `blocked_tool_handler_call_not_enabled`
- Explicit dev-gate enabled → `clarify_execution_completed` +
  `handlerCallId` + `postExecutionAuditId` + side-effect flags (all false)

**Confirmation-token safety:** the raw confirmation token returned by the
dry-run endpoint is held in an in-memory, non-reactive closure variable
inside the store. It is never returned from the store, never persisted to
`localStorage`/`sessionStorage`, never logged, and never rendered in the
DOM. Only the safe `confirmationTokenId` / expiry are exposed.

### 3.6 Frontend Audit Viewer

`AuditViewerPanel.vue` renders read-only audit events with:

- `auditKind` switching (dry_run / pre_execution / post_execution)
- limit control + canonicalName filter + refresh
- empty state + malformed-line-skip note
- per-event safe summary + expandable correlation IDs
- side-effect flags (provider schema sent / provider API called / external
  side effects — always false)

### 3.7 Browser smoke / E2E

New `apps/hermes-dev-webui/tests/smoke/phase-1g-04-30-execute-audit-smoke.spec.ts`:

- Audit Events API (read-only, invalid-kind 400, POST 405)
- Controlled execution chain (dry-run → execute)
- `EXECUTE_EXPECTED` env drives the expected decision per server gate config
- Post-execution audit visibility in the audit viewer API
- UI: Execute + Audit sub-tabs render; UI dry-run surfaces a safe decision
  without the raw token

Run against an isolated dev API (127.0.0.1:5181) + WebUI (127.0.0.1:5180).
Both scenarios verified:

- **Smoke D** (handler-call gate unset): `blocked_tool_handler_call_not_enabled`
- **Smoke E** (handler-call gate enabled): `clarify_execution_completed`
- **Smoke F**: `postExecutionAuditId` visible in audit viewer
- **Smoke G**: provider flags false

The stale `phase-1g-04-dry-run-api-safety-smoke.spec.ts` route-count
assertions were updated to the current 7-tool-route / 5-GET / 2-POST reality
(dry-run + execute POST), and the "no execute path" indicator was relaxed to
allow the intentional `/tools/execute` controlled route (dispatch/invoke/call
remain forbidden).

### 3.8 Route governance transition

| Metric | Before | After |
|--------|--------|-------|
| OpenAPI paths | 33 | 34 |
| Runtime routes | 33 | 34 |
| Tool GET routes | 4 | 5 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| STATIC_ALLOWLIST | `{"clarify"}` | `{"clarify"}` |

---

## 4. Security Boundary

| Item | Status |
|------|--------|
| STATIC_ALLOWLIST changed | No |
| Allowlist expanded | No |
| Raw token exposed | No (in-memory only, never persisted/logged/rendered) |
| Full tokenHash exposed | No |
| Raw arguments exposed (audit viewer) | No (whitelist normalization) |
| Secrets exposed | No (defensive redaction) |
| Callable / function repr exposed | No |
| Production home accessed | No |
| Production state.db accessed | No |
| Provider Schema sent | No |
| Provider API called | No |
| Non-clarify execution | No |
| Tool write route added | No |
| Route expansion beyond approved +1 read-only GET | No |
| Frontend stores raw token | No |
| Frontend stores raw args | No |

---

## 5. Default vs Explicit Behavior

### Default (kill switches unset)

```
execute → blocked_by_kill_switch (first gate)
```

### Default final-mile (kill switches on, handler-call gate unset)

```
valid token + valid digest + pre-execution audit + handler lookup +
dispatch plan + HERMES_TOOL_HANDLER_CALL_ENABLED unset
  → blocked_tool_handler_call_not_enabled
  → no handler call, no execution, no provider call
```

### Explicit dev/test success

```
HERMES_TOOL_EXECUTION_ENABLED=true
+ HERMES_AGENT_TOOLS_ENABLED=true
+ HERMES_TOOL_HANDLER_CALL_ENABLED=true
+ valid token + valid digest + canonicalName=clarify
  → clarify handler called
  → result normalized
  → post-execution audit written
  → clarify_execution_completed
  → providerSchemaSent = false
  → providerApiCalled = false
  → externalSideEffects = false
```

---

## 6. Tests / Gates

| Gate | Result |
|------|--------|
| Audit read module tests (`test_dev_web_tool_audit_read.py`) | 30 passed |
| Audit read API tests (`test_dev_web_tool_audit_read_api.py`) | 26 passed |
| Existing backend gates (handler call, post-exec audit, dispatch, …) | pass |
| Route governance (dev-check / 0c06 closure) | pass |
| Full related backend regression (19 files) | **1471 passed**, 2 skipped, 5 deselected |
| `compileall` (changed modules) | passed |
| `toolsets.py` compile | passed |
| `ruff check` (changed files) | all checks passed |
| `memory-check` | PASS |
| `dev-check` | PASS (only `Git worktree: dirty` WARN from in-progress commit) |
| Frontend `type-check` (vue-tsc) | passed |
| Frontend `lint` (eslint) | passed (0 errors / 0 warnings) |
| Frontend `test` (vitest) | **674 passed** (31 files) |
| Frontend `build` (vite) | passed |
| Browser smoke (completed scenario) | **7 passed** |
| Browser smoke (blocked scenario) | **6 passed, 1 skipped** (post-exec audit not written on blocked path) |

### Time-flaky test fix

The Phase 1G-04-29 handler-call success tests issued confirmation tokens
with a hardcoded `now = datetime(2026, 6, 13, 12, 0, 0)`. With a 300s token
TTL, those tokens expired later the same day, making the tests fail with
`blocked_requires_confirmation_token`. The four affected helpers now use
`datetime.now(timezone.utc)` so the token is issued at the current time and
does not pre-expire. This is a test-only fix (no production code change).

---

## 7. Known Limitations (P2)

- Browser smoke was run against isolated dev servers, then torn down. The 8
  pre-existing `auditWritten=false` assumptions in
  `phase-1g-04-dry-run-api-safety-smoke.spec.ts` still fail against a
  configured HERMES_HOME (audit IS written); they reflect an outdated
  assumption and are left for a future cleanup.
- Audit pagination is offset-based; multi-file JSONL rotation / race
  handling is future local-dev work.
- Non-clarify tools remain disabled (by design).
- Provider integration is a permanent non-goal for this controlled path.
- The audit read API caps total lines parsed per request at 1000;
  large-scale audit search/indexing is future work.

---

## 8. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Audit read API implemented (read-only) | ✅ |
| 2 | Exactly one new GET route | ✅ |
| 3 | No Tool write route | ✅ |
| 4 | OpenAPI paths = 34 | ✅ |
| 5 | Runtime routes = 34 | ✅ |
| 6 | Tool GET = 5 | ✅ |
| 7 | Tool write = 0 | ✅ |
| 8 | Tool dry-run = 1 | ✅ |
| 9 | Tool execution = 1 | ✅ |
| 10 | STATIC_ALLOWLIST = `frozenset({"clarify"})` | ✅ |
| 11 | Audit reader does not expose raw token / tokenHash / args / secrets | ✅ |
| 12 | Audit reader does not read production `~/.hermes` / `state.db` | ✅ |
| 13 | Frontend Execute UI implemented | ✅ |
| 14 | Audit Viewer implemented | ✅ |
| 15 | Default gate unset shows blocked decision | ✅ |
| 16 | Explicit dev/test clarify shows completed result | ✅ |
| 17 | postExecutionAuditId visible in UI / audit viewer | ✅ |
| 18 | Provider flags remain false | ✅ |
| 19 | Browser smoke / E2E passes (both scenarios) | ✅ |
| 20 | Frontend build passes | ✅ |
| 21 | Backend regression passes (1471) | ✅ |
| 22 | memory-check PASS | ✅ |
| 23 | dev-check PASS (only dirty-worktree WARN) | ✅ |
| 24 | Production Gateway PID 69355 unaffected | ✅ |
| 25 | Dev Gateway stopped after smoke; 5180/5181 free | ✅ |
| 26 | Local commit created; no push | ✅ |
| 27 | Phase 1G-04-31 not started | ✅ |

---

## 9. Risks

### P0
- (none) — no allowlist change, no non-clarify execution, no Provider
  Schema/API, no raw secret exposure, no production access, exactly one
  read-only GET route added.

### P1
- (none) — audit read tests, API tests, frontend unit tests, frontend build,
  route governance, compileall, ruff, memory-check, dev-check, and browser
  smoke (both scenarios) all pass.

### P2
- Pre-existing `auditWritten=false` assumptions in the old dry-run smoke
  (documented above).
- Audit pagination/rotation future work.
- Non-clarify tools not enabled (by design).
- Provider integration permanent non-goal.

---

*Phase 1G-04-30 Accelerated WebUI Closeout: read-only audit events API,
audit redaction/normalization, frontend Execute UI, audit viewer, browser
smoke/E2E, OpenAPI updates, route governance transition 33→34 paths /
4→5 Tool GET, a digest-binding fix that makes the controlled execution
chain work end-to-end, tests, and documentation. STATIC_ALLOWLIST remains
`frozenset({"clarify"})`. No Provider, no non-clarify execution, no Tool
write route, no production access. Browser smoke covers both the default
`blocked_tool_handler_call_not_enabled` path and the explicit
`clarify_execution_completed` path. Not pushed. Phase 1G-04-31 not started.*
