# Phase 1G-04-28: Dispatch Minimal Implementation / Still Blocked-Only

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-28 |
| Title | Dispatch Minimal Implementation / Still Blocked-Only |
| Status | Completed locally / not pushed |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-28 dispatch minimal implementation) |
| Dependencies | Phase 1G-04-27 completed locally (dispatch scope frozen) |
| Branch | dev-huangruibang |
| Base commit | `0984a47abec67252f80335b57192b1238fd7b522` |
| Implementation | Minimal backend dispatch planning + OpenAPI schema-only + tests + docs |

---

## 1. Phase Definition

Phase 1G-04-28 implements the **minimal safe dispatch plan / envelope** backend capability while preserving the **still-blocked-only** execution boundary.

This phase implements:

- A safe dispatch planning module
- A safe dispatch plan / dispatch envelope builder
- `dispatchId` generation
- Dispatch plan validation
- Execute route dispatch gates 57–69
- Safe dispatch response fields
- OpenAPI schema-only updates
- Backend tests
- Documentation

This phase does **not**:

- Call the Tool Handler
- Invoke the dispatch runtime
- Execute tools
- Implement post-execution audit
- Send Provider Schema
- Call Provider API
- Modify the frontend
- Add a runtime route
- Start real Controlled Execution

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base remote HEAD | `0984a47abec67252f80335b57192b1238fd7b522` |
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
| Dispatch (before this phase) | Not implemented |
| Valid token + valid digest + pre-execution audit + handler lookup final block (before) | `blocked_dispatch_not_enabled` |
| Tool Handler call | Not enabled |
| Tool Execution | Disabled |
| Post-execution audit | Not implemented |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

---

## 3. Implementation Summary

### Dispatch module

New module `hermes_cli/dev_web_tool_dispatch.py` (stdlib only, no provider/handler/agent/dispatch-runtime imports):

- `DispatchPlan` — immutable safe dispatch plan dataclass
- `DispatchResult` — immutable dispatch build result dataclass
- `build_dispatch_plan(...)` — safe dispatch plan / envelope builder
- `create_dispatch_plan(...)` — public alias for `build_dispatch_plan`
- `validate_dispatch_plan(...)` — dispatch plan safety validation
- `generate_dispatch_id()` — `dsp_` correlation ID generation
- `safe_dispatch_summary(...)` — safe response summary builder
- Helpers: `_dispatch_now()`, `_build_side_effect_flags()`, `_fail_closed(...)`

### Dispatch plan / envelope

The dispatch plan / envelope is metadata-only:

```json
{
  "dispatchStatus": "planned",
  "dispatchId": "dsp_...",
  "dispatchPlan": {
    "canonicalName": "clarify",
    "handlerLookupId": "hl_...",
    "handlerId": "handler_clarify",
    "registryKey": "clarify",
    "toolsetName": "builtin",
    "routingMode": "metadata_only",
    "dispatchAllowed": false,
    "toolHandlerCallAllowed": false,
    "executionAllowed": false,
    "providerSchemaAllowed": false,
    "sideEffectFreeDispatch": true,
    "dispatchPlanVersion": 1
  },
  "finalBlock": "blocked_tool_handler_call_not_enabled"
}
```

### Dispatch source strategy

The dispatch plan is built only from safe handler descriptor fields. It never uses:

- callable objects
- function repr
- raw arguments
- raw confirmation token
- full tokenHash
- provider credentials
- Provider Schema payload

`routingMode` is always `metadata_only`. All side-effect flags are always `false` (or `sideEffectFreeDispatch=true`).

### Dispatch ID strategy

- Prefix: `dsp_`
- Generation: `secrets.token_urlsafe(16)` (128 bits)
- Correlation-only — not an authorization credential
- Never contains raw token, full tokenHash, raw arguments, or secrets

### Dispatch plan validation

`build_dispatch_plan` validates, in order:

1. `handlerLookupId` present (else `dispatch_plan_unavailable`)
2. `canonicalName` non-empty (else `dispatch_plan_invalid`)
3. handler descriptor present (else `dispatch_handler_descriptor_missing`)
4. `canonicalName` allowlisted (else `dispatch_not_allowlisted`)
5. descriptor `canonicalName` matches (else `dispatch_handler_descriptor_mismatch`)
6. `handlerId` present (else `dispatch_plan_invalid`)
7. `registryKey` consistent (else `dispatch_registry_mismatch`)
8. `riskTier` consistent (else `dispatch_policy_mismatch`)
9. descriptor side-effect flags safe (else `dispatch_side_effect_risk`)
10. built plan passes `validate_dispatch_plan`

---

## 4. Execute Gate Integration

The dispatch phase is integrated into `evaluate_tool_execute_request` in `hermes_cli/dev_web_tool_execute.py` after handler lookup succeeds.

Future execute gate order target (frozen in Phase 1G-04-27):

| Gate | Description |
|------|-------------|
| 57 | Dispatch enable gate |
| 58 | Handler lookup result available |
| 59 | Dispatch plan source available |
| 60 | Dispatch plan created by `canonicalName` / `handlerLookupId` |
| 61 | Dispatch plan validates `canonicalName` |
| 62 | Dispatch plan validates handler descriptor consistency |
| 63 | Dispatch plan validates allowlist / policy metadata |
| 64 | Dispatch plan is side-effect-free metadata only |
| 65 | `dispatchId` generated |
| 66 | Dispatch safe response fields available |
| 67 | Block because Tool Handler call is not enabled |
| 68 | Tool Handler still not called |
| 69 | Execution still disabled |

All dispatch failures block before a Tool Handler call. All dispatch successes still block before a Tool Handler call.

### Failure contract

Dispatch failures map to blocked decisions:

| Error Code | Decision |
|------------|----------|
| `dispatch_unavailable` | `blocked_dispatch_unavailable` |
| `dispatch_plan_unavailable` | `blocked_dispatch_plan_unavailable` |
| `dispatch_plan_invalid` | `blocked_dispatch_plan_invalid` |
| `dispatch_handler_descriptor_missing` | `blocked_dispatch_handler_descriptor_missing` |
| `dispatch_handler_descriptor_mismatch` | `blocked_dispatch_handler_descriptor_mismatch` |
| `dispatch_not_allowlisted` | `blocked_dispatch_not_allowlisted` |
| `dispatch_policy_mismatch` | `blocked_dispatch_policy_mismatch` |
| `dispatch_side_effect_risk` | `blocked_dispatch_side_effect_risk` |
| `dispatch_registry_mismatch` | `blocked_dispatch_registry_mismatch` |
| `dispatch_written_but_tool_handler_call_not_enabled` | `blocked_tool_handler_call_not_enabled` |
| `tool_handler_call_not_enabled` | `blocked_tool_handler_call_not_enabled` |

All failures keep every side-effect flag `false`.

### Success contract

If dispatch succeeds:

- Response may include `dispatchId`, `dispatchStatus`, `dispatchPlan`
- Response preserves existing safe fields (`preExecutionAuditId`, `executeRequestId`, `preExecutionAuditStatus`, `handlerLookupId`, `handlerLookupStatus`, `handlerDescriptor`)
- Response must still be blocked
- Final decision is `blocked_tool_handler_call_not_enabled`
- `dispatchAllowed` = `false`, `toolHandlerCallAllowed` = `false`, `executionAllowed` = `false`
- `toolHandlerCalled` = `false`, `providerApiCalled` = `false`, `executionStarted` = `false`

Dispatch success is **not** interpreted as execution success.

### Final blocked-only boundary

The final boundary is:

```
blocked_tool_handler_call_not_enabled
```

---

## 5. OpenAPI Schema-Only Changes

`docs/webui/openapi/dev-web-api-v1.yaml` was updated schema-only:

- `ToolExecuteData.dispatchId` — new optional nullable string field
- `ToolExecuteData.dispatchStatus` — new optional nullable enum field (`planned`, `null`)
- `ToolExecuteData.dispatchPlan` — new optional `ToolDispatchPlan` field
- `ToolDispatchPlan` — new safe schema (metadata-only, all side-effect flags `false`/`sideEffectFreeDispatch=true`)
- `ToolExecuteDecision` — added `blocked_dispatch_*` values and `blocked_tool_handler_call_not_enabled`
- `ToolExecuteErrorCode` — added `dispatch_*` codes and `tool_handler_call_not_enabled`

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

Verified by `tests/test_dev_check_webui.py`, `tests/test_dev_web_0c06_closure.py`, and `./scripts/run-dev-hermes.sh dev-check`.

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
| Tool Handler called | No |
| Tool Execution | Disabled |
| Post-execution audit implemented | No |
| Provider Schema sent | No |
| Provider API called | No |
| Real Controlled Execution started | No |

---

## 8. Tests

### New dispatch tests

`tests/test_dev_web_tool_dispatch.py` — 89 tests covering:

- Dispatch plan structure (all required safe fields; exclusion of raw arguments / token / tokenHash / credentials / Provider Schema / callable / function repr)
- Dispatch gate behavior (missing handlerLookupId, non-allowlisted, missing descriptor, canonicalName mismatch, registry mismatch, risk/policy mismatch, side-effect risk, dispatch plan invalid, success path, `dsp_` prefix, unique IDs, plan existence does not bypass STATIC_ALLOWLIST)
- Security invariants (raw token / tokenHash / raw arguments / secrets never in result; provider never called; Tool Handler never called; dispatch runtime never invoked; execution never started; no callable object; STATIC_ALLOWLIST unchanged)
- Dispatch plan validation (valid/invalid/mismatch paths)
- Result dataclass immutability + safe summary
- Constants + no-side-effects (no tool/provider/subprocess/socket imports; idempotent)

### Execute integration updates

`tests/test_dev_web_tool_execute.py`:

- `test_valid_confirmation_token_still_blocks_at_dispatch_boundary` now asserts the dispatch success path: `dispatchId`, `dispatchStatus="planned"`, safe `dispatchPlan`, final block `blocked_tool_handler_call_not_enabled`, all side-effect flags `false`.
- `test_valid_token_is_consumed_and_reuse_blocks` updated to the new final block.
- New `TestDispatchIntegration` class: dispatch success fields in `to_safe_dict`, dispatch success keeps all side-effect flags false, dispatch failure blocks at a `dispatch_*` code, no raw token in dispatch response.

### Gate results

- dispatch tests: 89 passed
- handler lookup tests: passed
- pre-execution audit tests: passed
- digest tests: passed
- confirmation tests: passed
- execute / preflight tests: passed
- execute API tests: passed
- dry-run tests: passed
- route governance (dev-check / 0c06 closure): passed
- related backend regression: 1314 passed, 2 skipped, 5 deselected
- `compileall`: passed
- `toolsets.py` compile: passed
- `ruff check`: all checks passed
- `memory-check`: PASS
- `dev-check`: WARN (only `Git worktree: dirty` from the in-progress commit; all WebUI / OpenAPI / route governance / allowlist checks PASS)

---

## 9. Known Limitations

- Tool Handler call is not yet enabled (by design — future phase).
- Execution is not yet enabled (by design — future phase).
- Post-execution audit is not yet implemented (by design — future phase).
- Frontend execute UI is not implemented (by design — future phase).
- Audit read API / audit viewer are not yet implemented (by design — future phase).
- Dispatch plan is metadata-only and not runtime queueing.
- Clarify handler-level audit still needs a future phase.

---

## 10. Risks

### P0
- (none) — no Tool Handler call, no execution, no Provider Schema/API, no allowlist change, no route change, no raw secret exposure.

### P1
- (none) — dispatch tests, dispatch plan tests, dispatchId tests, dispatch safety tests, blocks-before-dispatch tests, dispatch success final block test, Tool Handler not called test, execution not called test, provider not called test, side-effect flags false test, raw token / raw arguments exclusion tests, route governance, compileall, ruff, memory-check, dev-check all pass.

### P2
- Tool Handler call not yet enabled — expected, future phase.
- Execution not yet enabled — expected, future phase.
- Post-execution audit not yet implemented — expected, future phase.
- Frontend execute UI not implemented — expected, future phase.
- Browser smoke not re-run — expected, no frontend changes.
- Audit read API / audit viewer not yet implemented — expected, future phase.
- Clarify handler-level audit still needs a future phase.
- Dispatch plan is metadata-only and not runtime queueing.
- Dispatch performance can be optimized later.
- Multi-file audit rotation support may be future work.
- Append-only JSONL audit write race conditions need future local-dev handling.
- Pre-existing stale `STATIC_ALLOWLIST` assertions remain in non-gate tests until a separate approved cleanup.

---

## 11. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Dispatch module implemented | ✅ |
| 2 | Safe dispatch plan / envelope builder implemented | ✅ |
| 3 | Safe dispatch metadata planning implemented | ✅ |
| 4 | `dispatchId` generated and returned | ✅ |
| 5 | `dispatchPlan` returned with safe metadata only | ✅ |
| 6 | Dispatch failure blocks | ✅ |
| 7 | Dispatch success still blocks at the Tool Handler call boundary | ✅ |
| 8 | Final block = `blocked_tool_handler_call_not_enabled` | ✅ |
| 9 | No Tool Handler call | ✅ |
| 10 | No execution | ✅ |
| 11 | No post-execution audit | ✅ |
| 12 | No Provider Schema | ✅ |
| 13 | No Provider API | ✅ |
| 14 | No frontend changes | ✅ |
| 15 | No route count changes | ✅ |
| 16 | No OpenAPI path changes | ✅ |
| 17 | OpenAPI paths = 33 | ✅ |
| 18 | Runtime routes = 33 | ✅ |
| 19 | Tool GET = 4 | ✅ |
| 20 | Tool write = 0 | ✅ |
| 21 | Tool dry-run = 1 | ✅ |
| 22 | Tool execution = 1 | ✅ |
| 23 | STATIC_ALLOWLIST unchanged | ✅ |
| 24 | STATIC_ALLOWLIST remains `frozenset({"clarify"})` | ✅ |
| 25 | Raw token not stored / logged | ✅ |
| 26 | Full tokenHash not exposed | ✅ |
| 27 | Raw arguments not stored / logged | ✅ |
| 28 | Secrets not stored | ✅ |
| 29 | Callable object not exposed | ✅ |
| 30 | Function repr not exposed | ✅ |
| 31 | Provider credentials not exposed | ✅ |
| 32 | Tests pass | ✅ |
| 33 | memory-check PASS | ✅ |
| 34 | dev-check PASS or only `.claude/` / dirty-worktree WARN | ✅ |
| 35 | Production Gateway PID 69355 unaffected | ✅ |
| 36 | Local commit created | ✅ |
| 37 | Not pushed | ✅ |

---

*Phase 1G-04-28 Dispatch Minimal Implementation / Still Blocked-Only: dispatch module, safe dispatch plan / envelope builder, dispatchId generation, dispatch plan validation, execute route dispatch gates 57–69, safe dispatch response fields, and OpenAPI schema-only updates implemented. A valid token + valid digest + pre-execution audit + handler lookup + dispatch success still blocks at the Tool Handler call boundary (`blocked_tool_handler_call_not_enabled`). No Tool Handler call, dispatch runtime invocation, execution, post-execution audit, Provider Schema sending, Provider API call, frontend execution flow, audit read API, audit viewer, or real Controlled Execution was introduced. OpenAPI paths remain 33, runtime routes remain 33, Tool GET/write/dry-run/execution remain 4/0/1/1, and STATIC_ALLOWLIST remains `frozenset({"clarify"})`. Not pushed. Real Controlled Execution not started.*
