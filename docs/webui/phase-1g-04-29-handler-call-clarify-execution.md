# Phase 1G-04-29: Clarify-only Handler Call + Post-execution Audit

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-29 |
| Title | Tool Handler Call + Clarify-only Minimal Controlled Execution + Post-execution Audit |
| Status | Completed locally / not pushed |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-29 handler call + post-execution audit) |
| Dependencies | Phase 1G-04-28 completed locally (dispatch minimal implementation) |
| Branch | dev-huangruibang |
| Base commit | `bc0e09fe4366814c0303f006b8e4f54b03b4753b` |
| Implementation | Clarify-only handler call gate + post-execution audit + OpenAPI schema-only + tests + docs |

---

## 1. Phase Definition

Phase 1G-04-29 closes the backend execution path for the **clarify-only**
controlled execution while preserving the **default-disabled** runtime safety
boundary. With kill switches unset, execute still blocks **before** a Tool
Handler call. Only an explicit dev gate (`HERMES_TOOL_HANDLER_CALL_ENABLED=true`)
plus a fully-verified clarify request invokes the bounded clarify handler and
returns a safe controlled execution response.

This phase implements:

- A clarify-only handler-call module
- A bounded, deterministic, side-effect-free clarify handler invocation
- A safe handler-call result envelope + normalization
- `handlerCallId` generation (`thc_` prefix)
- A post-execution audit module (append-only JSONL)
- `postExecutionAuditId` generation (`pexa_` prefix)
- Post-execution audit path guard (production home blocked)
- Post-execution audit fail-closed behavior
- Execute route handler-call gates 70–83
- OpenAPI schema-only updates
- Backend tests
- A P2 pre-execution audit metadata label fix
- Documentation

This phase does **not**:

- Enable the handler call by default (it remains kill-switch-gated)
- Allow any tool other than `clarify`
- Import or invoke the real `tools/clarify_tool.py` (bounded safe re-implementation)
- Send Provider Schema
- Call Provider API
- Modify the frontend
- Add a runtime route
- Add a Tool write route
- Add an audit read API / audit viewer
- Expand `STATIC_ALLOWLIST`

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base remote HEAD | `bc0e09fe4366814c0303f006b8e4f54b03b4753b` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Confirmation token verification | Implemented |
| Digest verification | Implemented |
| Pre-execution audit | Implemented |
| Handler lookup | Implemented |
| Dispatch planning | Implemented |
| Final block before this phase | `blocked_tool_handler_call_not_enabled` |
| Tool Handler call (before this phase) | Not enabled |
| Tool Execution (before this phase) | Disabled |
| Post-execution audit (before this phase) | Not implemented |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution (before this phase) | Not started |

---

## 3. Implementation Summary

### Handler call module

New module `hermes_cli/dev_web_tool_handler_call.py` (stdlib only, no
provider/handler/agent/dispatch-runtime imports):

- `HandlerCallPlan` — immutable safe handler-call plan dataclass
- `HandlerCallResult` — immutable handler-call result dataclass
- `attempt_clarify_handler_call(...)` — top-level clarify-only handler call
- `build_handler_call_plan(...)` — safe handler-call plan builder
- `validate_handler_call_plan(...)` — plan safety validation
- `generate_handler_call_id()` — `thc_` correlation ID generation
- `is_handler_call_enabled()` — explicit dev gate check
- `_run_clarify_handler(plan)` — bounded deterministic clarify handler
- `normalize_handler_result(...)` — safe result envelope normalization
- `safe_handler_call_summary(...)` — safe response summary builder
- `_redact_clarify_arguments(...)` — safe argument normalization + redaction

### Bounded clarify handler strategy

The clarify handler implemented here is a **bounded, safe, deterministic**
re-implementation of the clarify tool's *contract* (present a clarifying
question with optional choices) adapted for the non-interactive controlled
backend. It does **not** import `tools/` (which would trigger `registry.register()`
side effects and require a blocking platform callback). This matches the handler
descriptor's declared `moduleName` of `builtin.safe_metadata_only`.

The handler:

- Extracts `question` + `choices` from safe-normalized arguments only
- Redacts secret-looking values defensively
- Bounds choices to `CLARIFY_MAX_CHOICES` (4, mirroring `tools/clarify_tool.py`)
- Produces `{"type": "clarify", "message": <question>, "questions": [...]}`
- Performs **no** shell / file / network / browser / registry side effects

### Handler-call gate conditions

`attempt_clarify_handler_call` only proceeds when **all** hold:

1. `HERMES_TOOL_HANDLER_CALL_ENABLED == "true"` (exact lowercase)
2. `canonicalName == "clarify"` (defense-in-depth; allowlist already gates)
3. Dispatch plan available and consistent
4. Handler descriptor available and consistent
5. `dispatchPlan.canonicalName == canonicalName`
6. `dispatchPlan.handlerLookupId == handlerLookupId`
7. Registry key consistency
8. Dispatch plan side-effect flags safe (`toolHandlerCallAllowed=False`,
   `executionAllowed=False`, `providerSchemaAllowed=False`,
   `sideEffectFreeDispatch=True`)
9. Provider disabled (module never imports a provider)

Default (gate unset) → `blocked_tool_handler_call_not_enabled`, no handler
invoked.

### handlerCallId strategy

- Prefix: `thc_`
- Generation: `secrets.token_urlsafe(16)` (128 bits)
- Correlation-only — not an authorization credential
- Never contains raw token, full tokenHash, raw arguments, or secrets

### Post-execution audit module

New module `hermes_cli/dev_web_tool_post_execution_audit.py` (mirrors the
pre-execution audit module; stdlib only):

- `build_post_execution_audit_package(...)` — safe audit package builder
- `write_post_execution_audit_event(...)` — append-only JSONL writer (fail-closed)
- `get_post_execution_audit_store_path(...)` — containment-based path guard
- `validate_post_execution_audit_path(...)` — path validation without opening
- `safe_post_execution_audit_summary(...)` — safe summary builder

Audit file: `$HERMES_HOME/gateway/dev/audit/tool-post-execution-audit.jsonl`

The audit event contains only safe correlation IDs + a **safe result summary**
(`toolResultType`, `messageLength`, `questionCount`) — never raw message
content, raw arguments, raw token, or full tokenHash.

### postExecutionAuditId strategy

- Prefix: `pexa_`
- Generation: `secrets.token_urlsafe(16)` (128 bits)
- Correlation-only — not an authorization credential

### Fail-closed behavior

If the handler call succeeds but the post-execution audit package build or
write fails:

- Response fails closed — `decision = blocked_post_execution_audit_failed`
- `executionCompleted = False`, `toolHandlerCalled = False`
- `tool_result` / `side_effects` not surfaced
- `postExecutionAuditStatus = "failed"`
- No success-indicating handler-call status is surfaced

Principle: **No successful controlled execution response without a written
post-execution audit.**

---

## 4. Execute Gate Integration

The handler-call phase is integrated into `evaluate_tool_execute_request` in
`hermes_cli/dev_web_tool_execute.py` after dispatch planning succeeds.

Execute gate order (Phase 1G-04-29):

| Gate | Description |
|------|-------------|
| 70 | Tool handler call enable gate (`HERMES_TOOL_HANDLER_CALL_ENABLED`) |
| 71 | `canonicalName == clarify` (clarify-only) |
| 72 | Dispatch plan available |
| 73 | Handler descriptor / dispatch plan consistency |
| 74 | Handler call plan build |
| 75 | Handler call plan validation |
| 76 | Provider disabled invariant |
| 77 | `handlerCallId` generated |
| 78 | Clarify handler invocation |
| 79 | Handler result normalization |
| 80 | Post-execution audit event build |
| 81 | Post-execution audit path guard |
| 82 | Post-execution audit write |
| 83 | Safe controlled execution response |

### Default-disabled path

```
kill switches unset
  OR HERMES_TOOL_HANDLER_CALL_ENABLED unset
  → blocked_tool_handler_call_not_enabled
  → no handler call, no execution, no provider call
```

### Explicit dev/test success path

```
valid token + valid digest + pre-execution audit + handler lookup +
dispatch plan + explicit handler-call gate enabled + canonicalName=clarify
  → clarify handler called
  → result normalized
  → post-execution audit written
  → executionStatus = completed
  → providerSchemaSent = false
  → providerApiCalled = false
  → externalSideEffects = false
```

### Success contract

On the explicit-gated clarify success path:

- `decision = clarify_execution_completed`
- `toolHandlerCalled = true`, `executionStarted = true`, `executionCompleted = true`
- `executionAllowed = false` (policy flag stays false; clarify exception tracked
  by `executionCompleted` + `executionStatus`)
- `dispatchAllowed = false`, `providerSchemaAllowed = false`, `providerApiCalled = false`
- All `sideEffects` external flags `false`
- Response includes `handlerCallId`, `handlerCallStatus`, `executionStatus`,
  `postExecutionAuditId`, `postExecutionAuditStatus`, `toolResult`, `sideEffects`

### P2 fix (pre-execution audit metadata)

The pre-execution audit `_build_gate_status` previously emitted a stale
`"handlerLookup": "blocked_not_enabled"` label. Handler lookup is now enabled
(Phase 1G-04-26), so at pre-execution audit write time the downstream gates are
`"pending"` (not yet evaluated), not `"blocked_not_enabled"`. The label was
updated to `"pending"` for `handlerLookup`, `dispatch`, and `toolHandlerCall`.
This is metadata-only — it does not change the response path, gate behavior, or
route governance.

---

## 5. OpenAPI Schema-Only Changes

`docs/webui/openapi/dev-web-api-v1.yaml` was updated schema-only:

- `ToolExecuteData.handlerCallId` — new optional nullable string field
- `ToolExecuteData.handlerCallStatus` — new optional nullable enum (`completed`, `null`)
- `ToolExecuteData.executionStatus` — new optional nullable enum (`completed`, `null`)
- `ToolExecuteData.postExecutionAuditId` — new optional nullable string field
- `ToolExecuteData.postExecutionAuditStatus` — new optional nullable enum (`written`, `null`)
- `ToolExecuteData.toolResult` — new optional `ClarifyToolResult` field
- `ToolExecuteData.sideEffects` — new optional `ToolExecutionSideEffects` field
- `executionStarted`, `executionCompleted`, `toolHandlerCalled` — relaxed from
  `enum: [false]` to `type: boolean` with descriptions noting they are `true`
  ONLY on the explicit dev-gated clarify success path
- New component schemas: `ClarifyToolResult`, `ToolExecutionSideEffects`,
  `ToolHandlerCallEnvelope`, `ToolPostExecutionAuditSummary`
- `ToolExecuteDecision` — added `clarify_execution_completed`,
  `blocked_handler_call_*`, `blocked_post_execution_audit_*` values
- `ToolExecuteErrorCode` — added `handler_call_*`, `post_execution_audit_*` codes

No new path, no new method, no new route. OpenAPI paths remain **33**.

---

## 6. Route Governance

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 (unchanged) |
| Runtime routes | 33 (unchanged) |
| Tool GET routes | 4 (unchanged) |
| Tool write routes | 0 (unchanged) |
| Tool dry-run routes | 1 (unchanged) |
| Tool execution routes | 1 (unchanged) |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` (unchanged) |

Verified by `tests/test_dev_check_webui.py`, `tests/test_dev_web_0c06_closure.py`,
and `./scripts/run-dev-hermes.sh dev-check`.

---

## 7. Security Boundary

| Item | Status |
|------|--------|
| OpenAPI path count changed | No |
| Runtime route count changed | No |
| Frontend changed | No |
| STATIC_ALLOWLIST changed | No |
| Allowlist expanded | No |
| Raw token stored / logged | No |
| Full tokenHash exposed | No |
| Raw arguments stored / logged | No |
| Secrets stored | No |
| Callable object exposed | No |
| Function repr exposed | No |
| Production home accessed | No |
| Production state.db accessed | No |
| Tool Handler called by default | No (gate unset → blocked) |
| Tool Handler called in explicit clarify path | Yes (bounded safe handler) |
| Non-clarify tool handler called | No |
| Provider Schema sent | No |
| Provider API called | No |
| External side effects | No |
| Post-execution audit required for success | Yes (fail-closed) |

---

## 8. Tests

### New handler-call tests

`tests/test_dev_web_tool_handler_call.py` — 50 tests covering:

- Default-disabled gate (unset / empty / TRUE / 1 / yes / false all block)
- Explicit-enabled clarify-only completion (handlerCallId prefix, uniqueness,
  normalized tool result, open-ended vs choices, choice bounding, default message)
- Clarify-only enforcement (non-clarify never invokes)
- Consistency gates (missing dispatch plan / descriptor, canonicalName /
  handlerLookupId / registryKey mismatch, side-effect risk)
- Side-effect invariants (provider never sent/called, all external flags false)
- Security invariants (raw token / tokenHash / credentials excluded, secret
  redaction, no callable / function repr, no forbidden imports)
- Plan builder + validation
- Result immutability + safe summary + constants
- STATIC_ALLOWLIST unchanged

### New post-execution audit tests

`tests/test_dev_web_tool_post_execution_audit.py` — 38 tests covering:

- Package builder (pexa_ ID, uniqueness, correlation fields, safe result
  summary, exclusion of raw token / tokenHash / arguments / credentials /
  callable, side-effect flags)
- JSONL writer (success, file creation, append-only, correlation fields,
  dev HERMES_HOME path, invalid package fail-closed, summary status)
- Path guard (dev path ok, production home / subtree blocked, none-home no-env,
  production file not created)
- Fail-closed (mkdir failure, open failure, no success on write failure)
- Immutability + constants + safe summary

### Execute integration updates

`tests/test_dev_web_tool_execute.py`:

- Existing dispatch-boundary tests updated to the new precise
  `tool_handler_call_not_enabled` error code (decision unchanged)
- New `TestHandlerCallIntegration` class (10 tests): default-disabled blocks at
  handler call, explicit-gate clarify completes, post-execution audit JSONL
  written, post-audit write failure fails closed, raw token / tokenHash
  excluded, secret arguments redacted, no callable / function repr, success
  safe-dict fields, token consumed on success
- `_issue_valid_token_for` extended with an optional `arguments` parameter for
  digest-consistent argument-bearing success tests

`tests/test_dev_web_tool_execute_api.py`:

- New `TestHandlerCallApiSuccess` class (3 tests): default-disabled blocks at
  handler call via the API, explicit-gate clarify success envelope,
  post-execution audit file written

### P2 fix test

`tests/test_dev_web_tool_pre_execution_audit.py`:

- `test_gate_status_reflects_audit_written` updated to assert the corrected
  `pending` labels for `handlerLookup` / `dispatch` / `toolHandlerCall`

### Gate results

- handler call tests: 50 passed
- post-execution audit tests: 38 passed
- dispatch tests: 89 passed
- execute / API tests: 166 passed
- existing backend gates: 811 passed, 2 skipped
- route governance (dev-check / 0c06 closure): 124 passed, 5 deselected
- related backend regression: 1415 passed, 2 skipped, 5 deselected
- `compileall`: passed
- `toolsets.py` compile: passed
- `ruff check`: all checks passed
- `memory-check`: PASS
- `dev-check`: WARN (only `Git worktree: dirty` from the in-progress commit; all
  WebUI / OpenAPI / route governance / allowlist / provider-schema checks PASS)

---

## 9. Known Limitations

- Tool Handler call is default-disabled (by design — explicit dev gate required).
- Only `clarify` is executable; all other tools remain blocked.
- The clarify handler is a bounded safe re-implementation, not the real
  `tools/clarify_tool.py` invocation (no registry side effects, no blocking
  callback).
- Frontend execute UI is not implemented (by design — future phase).
- Audit read API / audit viewer are not implemented (by design — future phase).
- Browser smoke / E2E not run (no frontend changes).
- Provider integration is a permanent non-goal for this controlled path.

---

## 10. Risks

### P0
- (none) — no allowlist change, no route change, no non-clarify execution, no
  Provider Schema/API, no raw secret exposure, no production access.

### P1
- (none) — handler call tests, post-execution audit tests, default-disabled
  tests, clarify-only tests, fail-closed tests, route governance, compileall,
  ruff, memory-check, dev-check all pass.

### P2
- Frontend execute UI not implemented — expected, future phase.
- Audit read API / audit viewer not implemented — expected, future phase.
- Browser smoke not re-run — expected, no frontend changes.
- Non-clarify tools not enabled — expected, future phase.
- Provider integration not implemented — permanent non-goal.
- Multi-file audit rotation / JSONL race handling — future local-dev work.
- Clarify handler is bounded/safe, not the real tool invocation — by design.

---

## 11. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Clarify-only handler call implemented | ✅ |
| 2 | Default unset gates still block before handler call | ✅ |
| 3 | Explicit dev/test gate can invoke clarify handler | ✅ |
| 4 | Non-clarify never invokes handler | ✅ |
| 5 | Post-execution audit implemented | ✅ |
| 6 | Successful clarify execution requires post-execution audit write | ✅ |
| 7 | Post-audit write failure fails closed | ✅ |
| 8 | No Provider Schema sent | ✅ |
| 9 | No Provider API called | ✅ |
| 10 | No frontend changed | ✅ |
| 11 | No route added | ✅ |
| 12 | No Tool write route added | ✅ |
| 13 | OpenAPI paths remain 33 | ✅ |
| 14 | Runtime routes remain 33 | ✅ |
| 15 | Tool GET/write/dry-run/execution remain 4/0/1/1 | ✅ |
| 16 | STATIC_ALLOWLIST remains `frozenset({"clarify"})` | ✅ |
| 17 | Raw token not stored/logged | ✅ |
| 18 | Full tokenHash not exposed | ✅ |
| 19 | Raw arguments not stored/logged | ✅ |
| 20 | Callable object not exposed | ✅ |
| 21 | Function repr not exposed | ✅ |
| 22 | Production home untouched | ✅ |
| 23 | Production state.db untouched | ✅ |
| 24 | Production Gateway PID 69355 unaffected | ✅ |
| 25 | Tests pass | ✅ |
| 26 | compileall pass | ✅ |
| 27 | ruff pass | ✅ |
| 28 | memory-check PASS | ✅ |
| 29 | dev-check PASS or only dirty-worktree WARN | ✅ |
| 30 | Local commit created | ✅ |
| 31 | No push | ✅ |
| 32 | Phase 1G-04-30 not started | ✅ |

---

*Phase 1G-04-29 Clarify-only Handler Call + Post-execution Audit: clarify-only
Tool Handler call path and post-execution audit path implemented while
preserving default-disabled runtime safety. With gates unset, execute still
blocks before the Tool Handler call. With explicit dev/test gate enabled and
canonicalName=clarify, the backend invokes the bounded clarify handler,
normalizes the safe result, writes post-execution audit, and returns a safe
controlled execution response. No non-clarify tool execution, Provider Schema
sending, Provider API call, frontend execution flow, audit read API, audit
viewer, route expansion, Tool write route, production home access, or production
state.db access was introduced. OpenAPI paths remain 33, runtime routes remain
33, Tool GET/write/dry-run/execution remain 4/0/1/1, and STATIC_ALLOWLIST
remains `frozenset({"clarify"})`. Not pushed. Phase 1G-04-30 not started.*

---

## Phase 1G-04-30 Update — WebUI Closeout + Digest-Binding Fix (completed locally / not pushed)

Phase 1G-04-30 built the WebUI surface around this clarify handler-call path and fixed an end-to-end gap:

- **Digest-binding fix:** the real dry-run API endpoint (this phase's `hermes_cli/dev_web_api.py` change) now computes `dryRunDecisionDigest` bound to the real audit `eventId` / `createdAt` / `expiresAt`, matching what the execute gate recomputes from the historical lookup. Previously the dry-run response/token digest was computed with `audit_event_id=None`, so the real dry-run → execute chain returned `blocked_digest_mismatch`. The synthetic-event unit tests in this file (and `test_dev_web_tool_execute_api.py`) did not catch it; they now also use a relative issuance `now` (the old hardcoded `now=2026-06-13 12:00` pre-expired the 300s-TTL tokens later in the day).
- **Audit read API:** new read-only `GET /api/dev/v1/tools/audit-events` surfaces dry-run / pre-execution / post-execution audit events safely (no raw token / tokenHash / arguments / secrets).
- **Frontend Execute UI + Audit Viewer:** clarify-only controlled execution workbench; default gate unset shows `blocked_tool_handler_call_not_enabled`; explicit dev/test gate shows `clarify_execution_completed` with `postExecutionAuditId` and false Provider side-effect flags. Raw confirmation token is in-memory only.
- **Route governance:** 33/33/4/0/1/1 → 34/34/5/0/1/1. `STATIC_ALLOWLIST` unchanged.
- Browser smoke passes both default-block and completed scenarios.
- See `docs/webui/phase-1g-04-30-accelerated-webui-closeout.md`.
