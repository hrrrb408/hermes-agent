# Phase 1G-04-27: Dispatch Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-27 |
| Title | Dispatch Scope Freeze |
| Status | Frozen (dispatch boundary design only, no implementation) |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-27 dispatch scope freeze) |
| Dependencies | Phase 1G-04-26 completed locally |
| Branch | dev-huangruibang |
| Base commit | `f9ad2b1ef05cae101b09f902767123669ba9d4f4` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future dispatch goal
2. Documents why dispatch is still not a Tool Handler call
3. Documents why dispatch is still not execution
4. Freezes the relationship between dispatch and handler lookup
5. Freezes the relationship between dispatch and pre-execution audit
6. Freezes the relationship between dispatch and STATIC_ALLOWLIST
7. Freezes the relationship between dispatch and the handler descriptor
8. Freezes the relationship between dispatch and the future Tool Handler call
9. Freezes the future dispatch plan / dispatch envelope structure
10. Freezes the future dispatch input
11. Freezes the future dispatch output
12. Freezes the future dispatch ID strategy
13. Freezes the future dispatch timing
14. Freezes the future dispatch success conditions
15. Freezes the future dispatch failure conditions
16. Freezes the future dispatch failure contract
17. Freezes the future dispatch success contract
18. Freezes the future execute gate order including dispatch gates
19. Freezes the future OpenAPI schema-only strategy
20. Freezes the future route governance strategy
21. Defines future allowed files and forbidden files
22. Defines the future test matrix (58 tests)
23. Defines entry criteria and exit criteria for future implementation
24. Defines acceptance criteria for Phase 1G-04-27
25. Records the existing stale STATIC_ALLOWLIST assertion observation
26. Does **not** implement dispatch
27. Does **not** create a dispatch adapter
28. Does **not** call Tool Handler
29. Does **not** dispatch tools
30. Does **not** execute tools
31. Does **not** implement post-execution audit
32. Does **not** send Provider Schema
33. Does **not** call Provider API
34. Does **not** modify execute runtime behavior
35. Does **not** modify token runtime behavior
36. Does **not** modify digest runtime behavior
37. Does **not** modify pre-execution audit runtime behavior
38. Does **not** modify handler lookup runtime behavior
39. Does **not** modify OpenAPI
40. Does **not** add runtime routes
41. Does **not** start real Controlled Execution

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-27 = **Dispatch Scope Freeze**.

This phase freezes the future dispatch boundary.

This phase does not implement dispatch.
This phase does not call Tool Handler.
This phase does not execute tools.
This phase does not implement post-execution audit.
This phase does not send Provider Schema.
This phase does not call Provider API.
This phase does not modify execute runtime behavior.
This phase does not modify pre-execution audit behavior.
This phase does not modify handler lookup behavior.
This phase does not modify token behavior.
This phase does not modify digest behavior.
This phase does not modify OpenAPI.
This phase does not add runtime routes.
This phase does not start real Controlled Execution.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `f9ad2b1ef05cae101b09f902767123669ba9d4f4` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| allowlisted canonicalName | `clarify` |
| Confirmation token verification | Implemented |
| Digest verification | Implemented |
| Pre-execution audit | Implemented |
| Handler lookup | Implemented as safe metadata lookup |
| Valid token + valid digest + pre-execution audit + handler lookup success final block | `blocked_dispatch_not_enabled` |
| Dispatch | Not implemented |
| Tool Handler call | Not enabled |
| Tool Execution | Disabled |
| Post-execution audit | Not implemented |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

---

## 3. Dispatch Goal

Future dispatch should create a safe dispatch plan / dispatch envelope for an already verified, audited, allowlisted, handler-resolved `canonicalName`.

Dispatch should occur only after:

1. Kill switch gate passed
2. Static allowlist gate passed
3. Dry-run historical lookup passed
4. Confirmation token gate passed
5. Digest verification gate passed
6. Pre-execution audit was written successfully
7. Handler lookup succeeded
8. Explicit later phase enables dispatch

### 3.1 Dispatch Is Not a Tool Handler Call

Dispatch is not a Tool Handler call.
Dispatch is not execution.
Dispatch must not invoke the handler callable.
Dispatch must not run tool code.
Dispatch must not send Provider Schema.
Dispatch must not call Provider API.
Dispatch must only create safe routing metadata needed for a future Tool Handler call gate.

### 3.2 Safe Dispatch Planning Only

Dispatch is **safe dispatch planning only**.

- Dispatch is not runtime invocation
- Dispatch is not queue enqueue
- Dispatch is not a handler call
- Dispatch is not side-effecting execution

### 3.3 Necessary but Not Sufficient

Dispatch is **necessary but not sufficient**.

- Passing dispatch must not call a Tool Handler.
- Passing dispatch must not execute a tool.
- After dispatch succeeds, execute must still block at `blocked_tool_handler_call_not_enabled` or equivalent.

---

## 4. Relationship With Handler Lookup

Handler lookup resolves safe handler metadata.

Dispatch may only be considered after handler lookup succeeds.

### 4.1 Future Dispatch Must Reference

1. `handlerLookupId`
2. `handlerDescriptor`
3. `canonicalName`
4. `preExecutionAuditId`
5. `executeRequestId`
6. `dryRunRequestId`
7. `dryRunDecisionDigest`
8. `confirmationTokenId`

### 4.2 Must Not

Dispatch must not mutate handler lookup results.
Dispatch must not reinterpret the handler descriptor as permission.
Dispatch must not bypass STATIC_ALLOWLIST.
Dispatch must not call the handler callable.

---

## 5. Relationship With Pre-Execution Audit

Pre-execution audit remains the durable pre-handler record.

Dispatch may only be considered after a successful pre-execution audit write **and** a successful handler lookup.

### 5.1 Future Dispatch Result Should Reference

1. `preExecutionAuditId`
2. `executeRequestId`
3. `handlerLookupId`
4. `dryRunRequestId`
5. `dryRunDecisionDigest`
6. `canonicalName`
7. `confirmationTokenId`
8. Pre-execution audit status

### 5.2 Must Not

Dispatch must not mutate pre-execution audit records.
Dispatch must not rewrite dry-run audit records.
Dispatch must not rewrite token records.
Dispatch must not be treated as execution proof.

---

## 6. Relationship With STATIC_ALLOWLIST

Dispatch is allowed only for a `canonicalName` already approved by `STATIC_ALLOWLIST`.

`STATIC_ALLOWLIST` remains the first static policy boundary.
Dispatch must not broaden allowlist policy.
Dispatch must not dynamically allow tools.
Dispatch must not wildcard-match tool names.
Dispatch must not infer permission from handler existence or dispatch plan existence.

### 6.1 Future Behavior

If `canonicalName` is not in `STATIC_ALLOWLIST`, execution must block **before** handler lookup and **before** dispatch.

If a handler exists but `canonicalName` is not allowlisted, it must still block **before** dispatch.

If `canonicalName` is allowlisted and handler lookup succeeds but a dispatch plan cannot be created, it must block at `dispatch_plan_unavailable` or equivalent.

### 6.2 Must Preserve

```python
STATIC_ALLOWLIST = frozenset({"clarify"})
```

---

## 7. Relationship With Handler Descriptor

The handler descriptor resolved during handler lookup is the **input** to dispatch planning, never an authorization credential.

- Dispatch reads safe handler descriptor fields (`canonicalName`, `handlerId`, `registryKey`, `riskTier`, `allowlisted`).
- Dispatch must not treat any descriptor field as permission to call the handler.
- Dispatch must not promote `dispatchAllowed` from the descriptor; dispatch planning decides the field, it does not inherit it.
- Dispatch must not expose or dereference the descriptor's module or callable metadata beyond safe `handlerId` / `registryKey` routing metadata.

---

## 8. Relationship With Future Tool Handler Call

Dispatch is a routing / planning boundary.
A Tool Handler call is a later execution-adjacent boundary.

- Dispatch success must not imply a Tool Handler call.
- Dispatch success must not imply execution.
- Dispatch success must not imply Provider Schema sending.
- Dispatch success must still block at the Tool Handler call boundary.

Future dispatch success final block should be:

```
blocked_tool_handler_call_not_enabled
```

or an equivalent project-approved decision.

---

## 9. Dispatch Plan / Envelope Structure

### 9.1 Recommended Structure

```json
{
  "dispatchStatus": "planned",
  "dispatchId": "dsp_...",
  "dispatchPlan": {
    "canonicalName": "clarify",
    "handlerLookupId": "hl_...",
    "handlerId": "handler_clarify",
    "registryKey": "clarify",
    "toolsetName": "...",
    "routingMode": "metadata_only",
    "dispatchAllowed": false,
    "toolHandlerCallAllowed": false,
    "executionAllowed": false,
    "providerSchemaAllowed": false,
    "sideEffectFreeDispatch": true
  },
  "createdAt": "..."
}
```

### 9.2 Safe Fields Only

Must include safe fields only.

### 9.3 Must Not Include

- Raw arguments
- Raw token
- Full `tokenHash`
- Provider credentials
- Provider Schema payload
- Function object repr
- Actual callable object
- Secret env values
- Authorization headers
- Cookies
- Execution result
- Dispatch execution result
- Provider response

---

## 10. Dispatch ID Strategy

### 10.1 Prefix

```
dispatchId prefix = dsp_
```

### 10.2 Generation

May use:

- `uuid4`
- `ULID`
- `token_urlsafe`
- Safe random

### 10.3 Constraints

`dispatchId` is correlation-only.
`dispatchId` is not an authorization credential.
`dispatchId` must not contain the raw token.
`dispatchId` must not contain the full `tokenHash`.
`dispatchId` must not contain raw arguments.
`dispatchId` must not contain handler callable identity beyond the safe `handlerId` / `registryKey` metadata.

---

## 11. Dispatch Input

Future dispatch input is the already-verified gate context from the execute route. It is **not** a new user-supplied payload and it is **not** a re-statement of raw arguments.

### 11.1 Dispatch Input Includes

1. `canonicalName` (already allowlisted, dry-run-bound, token-bound, digest-verified)
2. `handlerLookupId` + `handlerDescriptor` (from handler lookup)
3. `preExecutionAuditId` + `executeRequestId` (from pre-execution audit)
4. `dryRunRequestId` + `dryRunDecisionDigest` (from dry-run / digest verification)
5. `confirmationTokenId` (from confirmation token verification)
6. `riskTier`, `policyVersion` (from policy evaluation)

### 11.2 Dispatch Input Must Not Include

- Raw user arguments (use digests / redacted previews only)
- Raw confirmation token
- Provider credentials
- Authorization headers / cookies

---

## 12. Dispatch Output

Future dispatch output is a safe dispatch plan / dispatch envelope (Section 9). It is metadata, never a handler call and never an execution result.

### 12.1 Dispatch Output Includes

1. `dispatchId`
2. `dispatchStatus`
3. `dispatchPlan` (safe metadata)
4. Correlation IDs (`handlerLookupId`, `preExecutionAuditId`, `executeRequestId`)

### 12.2 Dispatch Output Must Not Include

- Handler callable result
- Execution result
- Provider response
- Raw arguments / token / secrets

---

## 13. Future Dispatch Timing

### 13.1 Dispatch Should Occur Only After

1. Execute request accepted
2. Kill switch passed
3. `canonicalName` allowlisted
4. Dry-run historical lookup passed
5. Dry-run binding passed
6. Confirmation token verification passed
7. Confirmation token consumed safely
8. Digest verification passed
9. Pre-execution audit written successfully
10. Handler lookup succeeded
11. Explicit dispatch enable gate passed

### 13.2 Dispatch Must Occur Before

1. Tool Handler call
2. Tool execution
3. Post-execution audit
4. Provider Schema sending
5. Provider API call

### 13.3 Post-Dispatch Block Boundary

If dispatch fails, execute blocks.
If dispatch succeeds, execute **still** blocks at `blocked_tool_handler_call_not_enabled` or equivalent.

---

## 14. Failure Contract

### 14.1 Error Codes / Decisions

| Error Code | Decision |
|------------|----------|
| `dispatch_not_enabled` | `blocked_dispatch_not_enabled` |
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

### 14.2 Failure Invariants

All failures must:

- Block before a Tool Handler call
- `executionAllowed` = `false`
- `dispatchAllowed` = `false`
- `toolHandlerCallAllowed` = `false`
- `providerSchemaAllowed` = `false`
- `toolHandlerCalled` = `false`
- `providerApiCalled` = `false`
- `executionStarted` = `false`

---

## 15. Success Contract

If dispatch succeeds:

1. Response may include `dispatchId`
2. Response may include `dispatchStatus`
3. Response may include safe `dispatchPlan`
4. Response may include `handlerLookupId`
5. Response may include `preExecutionAuditId`
6. Response may include `executeRequestId`
7. Response must still be blocked
8. Final decision should be `blocked_tool_handler_call_not_enabled`
9. `dispatchAllowed` = `false` unless the project later defines a separate internal flag
10. `toolHandlerCallAllowed` = `false`
11. `executionAllowed` = `false`
12. `toolHandlerCalled` = `false`
13. `providerApiCalled` = `false`
14. `executionStarted` = `false`

Dispatch success must **not** be interpreted as execution success.

---

## 16. Future Execute Gate Order

### 16.1 Current State

| Gate Range | Description |
|------------|-------------|
| Gates 1–14 | Kill switch, allowlist, dry-run lookup, dry-run binding gates |
| Gates 15–27 | Confirmation token verification gates |
| Gates 28–37 | Digest verification gates |
| Gates 38–45 | Pre-execution audit gates |
| Gates 46–56 | Handler lookup gates |
| Current final block | `blocked_dispatch_not_enabled` |

### 16.2 Future Dispatch Implementation Target

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

### 16.3 Post-Dispatch Block

After dispatch succeeds, execute **still** blocks.

The next allowed block boundary is `blocked_tool_handler_call_not_enabled`.

No Tool Handler call is allowed in the dispatch implementation.

---

## 17. OpenAPI Strategy

### 17.1 Phase 1G-04-27

Phase 1G-04-27 does **not** modify OpenAPI.

### 17.2 Future Schema-Only Changes

Future dispatch implementation may require schema-only OpenAPI changes:

| Schema | Possible Refinement |
|--------|---------------------|
| `ToolExecuteData.dispatchId` | New optional field |
| `ToolExecuteData.dispatchStatus` | New optional field |
| `ToolExecuteData.dispatchPlan` | New optional safe plan object |
| `ToolExecuteErrorCode` | New `dispatch_*` error code values |
| `ToolExecuteDecision` | New `blocked_tool_handler_call_not_enabled` decision value |
| `ToolExecuteGateStatus` | Dispatch gate names |

### 17.3 Path Count Constraint

No new OpenAPI path unless separately approved.

- OpenAPI paths should remain **33**
- Runtime routes should remain **33**
- Tool write routes should remain **0**
- Tool execution routes should remain **1**

---

## 18. Route Governance Strategy

### 18.1 Preferred Future Implementation

No new route.

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### 18.2 If Route Change Required

If future dispatch implementation requires a route change:

1. Must **stop** and create a separate route-governed scope freeze
2. Must **not** bundle route changes into the dispatch implementation

---

## 19. Future Allowed Files

These are future allowed files for the dispatch implementation phase only. They are **not** modified in Phase 1G-04-27, except docs files allowed by this docs-only phase.

### 19.1 Backend

```
hermes_cli/dev_web_tool_dispatch.py  (new — recommended dispatch module)
hermes_cli/dev_web_tool_execute.py
hermes_cli/dev_web_tool_handler_lookup.py
hermes_cli/dev_web_tool_pre_execution_audit.py
hermes_cli/dev_web_tool_execute_digest.py
hermes_cli/dev_web_tool_execute_confirmation.py
hermes_cli/dev_web_tool_execute_preflight.py
hermes_cli/dev_web_tool_policy.py
hermes_cli/dev_web_api.py
```

### 19.2 OpenAPI

```
docs/webui/openapi/dev-web-api-v1.yaml  (schema-only changes if approved)
```

### 19.3 Tests

```
tests/test_dev_web_tool_dispatch.py  (new)
tests/test_dev_web_tool_handler_lookup.py
tests/test_dev_web_tool_execute.py
tests/test_dev_web_tool_execute_api.py
tests/test_dev_web_tool_pre_execution_audit.py
tests/test_dev_web_tool_execute_digest.py
tests/test_dev_web_tool_execute_confirmation.py
tests/test_dev_web_tool_execute_preflight.py
tests/test_dev_check_webui.py
tests/test_dev_web_0c06_closure.py
```

### 19.4 Documentation

```
docs/webui/phase-1g-04-27-dispatch-scope.md
docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md
docs/webui/phase-1-implementation-plan.md
```

### 19.5 Declaration

These are **future allowed files only.** They are **not** modified in Phase 1G-04-27, except docs files allowed by this docs-only phase.

---

## 20. Future Forbidden Files

The following must **not** be modified in any dispatch implementation phase:

```
apps/hermes-dev-webui/src/
apps/hermes-dev-webui/tests/
apps/hermes-dev-webui/e2e/
agent/
tools/
toolsets.py
runtime files committed to repo
memory files
review files
.env
.claude/
~/.hermes
production state.db
setup-hermes.sh
global hermes command
provider config files
production gateway state files
runtime audit JSONL files
```

---

## 21. Future Test Matrix

The following tests must pass when dispatch implementation arrives. **None are added in Phase 1G-04-27.**

### 21.1 Dispatch Plan Tests (17 tests)

| # | Test | Expected |
|---|------|----------|
| 1 | Dispatch plan includes `dispatchId` | Field present |
| 2 | Dispatch plan includes `canonicalName` | Field present |
| 3 | Dispatch plan includes `handlerLookupId` | Field present |
| 4 | Dispatch plan includes `handlerId` | Field present |
| 5 | Dispatch plan includes `registryKey` | Field present |
| 6 | Dispatch plan includes `routingMode` | Field present |
| 7 | Dispatch plan includes `dispatchAllowed=false` | `false` |
| 8 | Dispatch plan includes `toolHandlerCallAllowed=false` | `false` |
| 9 | Dispatch plan includes `executionAllowed=false` | `false` |
| 10 | Dispatch plan includes `providerSchemaAllowed=false` | `false` |
| 11 | Dispatch plan includes `sideEffectFreeDispatch=true` | `true` |
| 12 | Dispatch plan excludes raw arguments | No raw arguments |
| 13 | Dispatch plan excludes raw token | No raw token |
| 14 | Dispatch plan excludes full `tokenHash` | No full `tokenHash` |
| 15 | Dispatch plan excludes provider credentials | No credentials |
| 16 | Dispatch plan excludes Provider Schema | No Provider Schema |
| 17 | Dispatch plan excludes callable object | No callable object |

### 21.2 Dispatch Gate Tests (14 tests)

| # | Test | Expected |
|---|------|----------|
| 18 | Dispatch is not attempted before handler lookup success | Blocks earlier |
| 19 | Non-allowlisted `canonicalName` blocks before dispatch | `dispatch_not_allowlisted` |
| 20 | Missing handler lookup result blocks before dispatch | `dispatch_handler_descriptor_missing` |
| 21 | Invalid handler descriptor blocks before dispatch | `dispatch_handler_descriptor_mismatch` |
| 22 | Dispatch plan unavailable blocks | `dispatch_plan_unavailable` |
| 23 | Dispatch plan invalid blocks | `dispatch_plan_invalid` |
| 24 | Dispatch `canonicalName` mismatch blocks | `dispatch_handler_descriptor_mismatch` |
| 25 | Dispatch `handlerLookupId` mismatch blocks | `dispatch_handler_descriptor_mismatch` |
| 26 | Dispatch risk / policy mismatch blocks | `dispatch_policy_mismatch` |
| 27 | Dispatch side-effect risk blocks | `dispatch_side_effect_risk` |
| 28 | Dispatch success returns `dispatchId` | ID present |
| 29 | Dispatch success returns safe `dispatchPlan` | Plan present |
| 30 | `dispatchId` prefix is `dsp_` | Correct prefix |
| 31 | `dispatchId` is unique / correlation-only | Unique |

### 21.3 Execute Integration Tests (11 tests)

| # | Test | Expected |
|---|------|----------|
| 32 | Valid token + valid digest + pre-execution audit + handler lookup + dispatch failure blocks | Blocked |
| 33 | Valid token + valid digest + pre-execution audit + handler lookup + dispatch success still blocks | Blocked |
| 34 | Final block after dispatch success is `blocked_tool_handler_call_not_enabled` | Correct decision |
| 35 | Response includes `dispatchId` after dispatch success | Field present |
| 36 | Response includes `dispatchStatus` after dispatch success | Field present |
| 37 | Response includes safe `dispatchPlan` after dispatch success | Field present |
| 38 | No Tool Handler call after dispatch success | `toolHandlerCalled=false` |
| 39 | No execution after dispatch success | `executionStarted=false` |
| 40 | No Provider Schema after dispatch success | `providerSchemaAllowed=false` |
| 41 | No Provider API after dispatch success | `providerApiCalled=false` |
| 42 | Side-effect flags remain `false` after dispatch success | All `false` |

### 21.4 Security Invariant Tests (10 tests)

| # | Test | Expected |
|---|------|----------|
| 43 | All dispatch failures block before Tool Handler call | `toolHandlerCalled=false` |
| 44 | All failures keep side-effect flags `false` | All `false` |
| 45 | Raw token never appears in dispatch response | No raw token |
| 46 | Full `tokenHash` never appears in dispatch response | No full `tokenHash` |
| 47 | Raw arguments never appear in dispatch response | No raw arguments |
| 48 | Secrets never appear in dispatch response | No secrets |
| 49 | Provider is never called | `providerApiCalled=false` |
| 50 | Tool Handler is never called | `toolHandlerCalled=false` |
| 51 | Execution is never started | `executionStarted=false` |
| 52 | Dispatch plan existence does not bypass STATIC_ALLOWLIST | `dispatchAllowed=false` for non-allowlisted |

### 21.5 Route Governance Tests (5 tests)

| # | Test | Expected |
|---|------|----------|
| 53 | OpenAPI paths remain 33 unless separately approved | 33 |
| 54 | Runtime routes remain 33 unless separately approved | 33 |
| 55 | Tool write routes remain 0 | 0 |
| 56 | Tool execution routes remain 1 | 1 |
| 57 | `STATIC_ALLOWLIST` remains `{"clarify"}` | `frozenset({"clarify"})` |

### 21.6 Optional Cleanup Test (1 test)

| # | Test | Expected |
|---|------|----------|
| 58 | Stale `STATIC_ALLOWLIST len==0` assertions are removed or updated in a separate approved cleanup phase only | Separate phase required |

---

## 22. Existing Out-of-Scope Observation

Two non-gate, non-committed test files currently contain stale assertions:

- `tests/test_dev_web_tool_policy_service.py`
- `tests/test_dev_web_tool_schema_preview_service.py`

**Issue:**

- Stale assertions expect `len(STATIC_ALLOWLIST) == 0`
- `STATIC_ALLOWLIST` is already `frozenset({"clarify"})`
- This issue existed before Phase 1G-04-24
- It was outside Phase 1G-04-24 / 1G-04-25 / 1G-04-26 gate lists
- It was not caused by commit `f9ad2b1ef05cae101b09f902767123669ba9d4f4`

Phase 1G-04-27 must **not** fix these assertions unless the user explicitly changes this phase scope.

**Recommended future cleanup:**

- Separate docs/code cleanup task
- Update stale assertions to expect `{"clarify"}`
- Run affected tests explicitly

---

## 23. Future Implementation Entry Criteria

Before dispatch implementation may begin, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-27 docs pushed |
| 2 | No P0/P1 open |
| 3 | User explicitly approves dispatch implementation |
| 4 | Remote and local branch synchronized |
| 5 | `STATIC_ALLOWLIST` remains exactly `{"clarify"}` |
| 6 | Route governance green |
| 7 | Confirmation token gate green |
| 8 | Digest verification gate green |
| 9 | Pre-execution audit gate green |
| 10 | Handler lookup gate green |
| 11 | Valid token + valid digest + pre-execution audit + handler lookup currently blocks at the dispatch boundary |
| 12 | Provider schema not sent |
| 13 | Tool Handler call disabled |
| 14 | Tool execution disabled |
| 15 | Production gateway stable |

---

## 24. Future Implementation Exit Criteria

After dispatch implementation, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Dispatch module implemented |
| 2 | Dispatch plan builder implemented |
| 3 | `dispatchId` generated |
| 4 | Dispatch failure blocks |
| 5 | Dispatch success still blocks at the Tool Handler call boundary |
| 6 | Dispatch plan returned with safe metadata only |
| 7 | No Tool Handler call after dispatch success |
| 8 | No execution after dispatch success |
| 9 | No Provider Schema after dispatch success |
| 10 | No Provider API after dispatch success |
| 11 | OpenAPI paths remain 33 unless separately approved |
| 12 | Runtime routes remain 33 unless separately approved |
| 13 | Tool write routes remain 0 |
| 14 | Tool execution routes remain 1 |
| 15 | `STATIC_ALLOWLIST` remains `{"clarify"}` |
| 16 | Production gateway unaffected |

---

## 25. Acceptance Criteria for Phase 1G-04-27

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only | |
| 2 | New dispatch scope doc added | |
| 3 | Phase 1G-04 scope doc updated | |
| 4 | Implementation plan updated | |
| 5 | Phase 1G-04-26 doc updated with next dependency | |
| 6 | No code changes | |
| 7 | No OpenAPI file changes | |
| 8 | No tests changed | |
| 9 | No frontend changes | |
| 10 | No routes changed | |
| 11 | No execute route behavior changes | |
| 12 | No token behavior changes | |
| 13 | No digest behavior changes | |
| 14 | No pre-execution audit behavior changes | |
| 15 | No handler lookup behavior changes | |
| 16 | No `STATIC_ALLOWLIST` changes | |
| 17 | `STATIC_ALLOWLIST` remains `frozenset({"clarify"})` | |
| 18 | No dispatch implementation | |
| 19 | No Tool Handler call | |
| 20 | No Tool Dispatch | |
| 21 | No Tool Execution | |
| 22 | No Provider Schema sent | |
| 23 | No Provider API called | |
| 24 | OpenAPI paths = 33 | |
| 25 | Runtime routes = 33 | |
| 26 | Tool GET = 4 | |
| 27 | Tool write = 0 | |
| 28 | Tool dry-run = 1 | |
| 29 | Tool execution = 1 | |
| 30 | Execute route remains blocked-only | |
| 31 | Real Controlled Execution not started | |
| 32 | Local docs-only commit created | |
| 33 | Not pushed | |

---

## 26. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code modified | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Route count changed | Verify route governance; reject if changed |
| 6 | Execute route behavior changed | Verify diff; reject if execute runtime changed |
| 7 | Token behavior changed | Verify diff; reject if token runtime changed |
| 8 | Digest behavior changed | Verify diff; reject if digest runtime changed |
| 9 | Pre-execution audit behavior changed | Verify diff; reject if audit runtime changed |
| 10 | Handler lookup behavior changed | Verify diff; reject if handler lookup runtime changed |
| 11 | `STATIC_ALLOWLIST` modified | Verify unchanged; reject if modified |
| 12 | Allowlist expanded | Verify unchanged; reject if expanded |
| 13 | Dispatch implemented | Verify diff; reject if dispatch code added |
| 14 | Tool Handler called | Verify no handler invocation; reject if found |
| 15 | Tool Dispatch called | Verify no dispatch; reject if found |
| 16 | Tool executed | Verify no execution; reject if found |
| 17 | Provider API called / Schema sent | Verify no provider calls; reject if found |
| 18 | Blocked response has `executionAllowed=true` | Content search; reject if found |
| 19 | Blocked response has `dispatchAllowed=true` | Content search; reject if found |
| 20 | Blocked response has `toolHandlerCallAllowed=true` | Content search; reject if found |
| 21 | Blocked response has `providerSchemaAllowed=true` | Content search; reject if found |
| 22 | Blocked response has `toolHandlerCalled=true` | Content search; reject if found |
| 23 | Blocked response has `providerApiCalled=true` | Content search; reject if found |
| 24 | Blocked response has `executionStarted=true` | Content search; reject if found |
| 25 | Tool write routes > 0 | Verify route governance; reject if changed |
| 26 | Tool execution routes ≠ 1 | Verify route governance; reject if changed |
| 27 | OpenAPI path count changes unexpectedly | Verify count; reject if changed |
| 28 | Runtime route count changes unexpectedly | Verify count; reject if changed |
| 29 | Frontend modified | Verify diff; reject if found |
| 30 | Agent/tools modified | Verify diff; reject if found |
| 31 | Production Gateway affected | Verify PID; reject if changed |
| 32 | Real secret leaked | Content search; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-27 Failed."**

---

## 27. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Dispatch goal missing | Verify Section 3 |
| 2 | Handler lookup relationship missing | Verify Section 4 |
| 3 | Pre-execution audit relationship missing | Verify Section 5 |
| 4 | STATIC_ALLOWLIST relationship missing | Verify Section 6 |
| 5 | Handler descriptor relationship missing | Verify Section 7 |
| 6 | Future Tool Handler call relationship missing | Verify Section 8 |
| 7 | Dispatch plan / envelope structure missing | Verify Section 9 |
| 8 | Dispatch ID strategy missing | Verify Section 10 |
| 9 | Dispatch timing missing | Verify Section 13 |
| 10 | Failure contract missing | Verify Section 14 |
| 11 | Success contract missing | Verify Section 15 |
| 12 | Future gate order missing | Verify Section 16 |
| 13 | Future OpenAPI strategy missing | Verify Section 17 |
| 14 | Future route governance missing | Verify Section 18 |
| 15 | Future allowed files missing | Verify Section 19 |
| 16 | Future forbidden files missing | Verify Section 20 |
| 17 | Future test matrix missing | Verify Section 21 |
| 18 | Stale STATIC_ALLOWLIST assertion observation missing | Verify Section 22 |
| 19 | Entry criteria missing | Verify Section 23 |
| 20 | Exit criteria missing | Verify Section 24 |
| 21 | Docs incorrectly claim dispatch implemented | Content review |
| 22 | Docs incorrectly claim Tool Handler called | Content review |
| 23 | Docs incorrectly claim execution enabled | Content review |
| 24 | Route governance failed | Run tests; verify counts |
| 25 | OpenAPI paths ≠ 33 | Verify count |
| 26 | Runtime routes ≠ 33 | Verify count |
| 27 | Tool GET ≠ 4 | Verify count |
| 28 | Tool write ≠ 0 | Verify count |
| 29 | Tool dry-run ≠ 1 | Verify count |
| 30 | Tool execution ≠ 1 | Verify count |
| 31 | `STATIC_ALLOWLIST` ≠ `{"clarify"}` | Verify value |
| 32 | compileall failed | Run compileall |
| 33 | ruff failed | Run ruff |
| 34 | memory-check failed | Run memory-check |
| 35 | dev-check failed | Run dev-check |
| 36 | Worktree has unexpected files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 28. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Dispatch not yet implemented | Expected — scope freeze only |
| 2 | Tool Handler call not yet enabled | Expected — future phase |
| 3 | Execution not yet enabled | Expected — future phase |
| 4 | Post-execution audit not yet implemented | Expected — future phase |
| 5 | Frontend execute UI not implemented | Expected — future phase |
| 6 | Browser smoke not re-run | Expected — no frontend changes |
| 7 | Audit read API not yet implemented | Expected — future phase |
| 8 | Audit viewer not yet implemented | Expected — future phase |
| 9 | Clarify handler-level audit still needs future phase | Expected — future work |
| 10 | Lookup performance can be optimized later | Expected — optimization deferred |
| 11 | Dispatch performance can be optimized later | Expected — optimization deferred |
| 12 | Multi-file audit rotation support may be future work | Expected — deferred |
| 13 | Append-only JSONL audit write race conditions need future local-dev handling | Expected — local dev constraints |
| 14 | Pre-existing stale `STATIC_ALLOWLIST` assertions remain in non-gate tests until separate cleanup | Expected — separate cleanup task |

---

*Phase 1G-04-27 Dispatch Scope Freeze: dispatch goal, relationship with handler lookup, relationship with pre-execution audit, relationship with STATIC_ALLOWLIST, relationship with handler descriptor, relationship with future Tool Handler call, dispatch plan / envelope structure, dispatch input, dispatch output, dispatch ID strategy, dispatch timing, failure contract, success contract, future execute gate order, OpenAPI scope, route governance scope, future allowed and forbidden files, future test matrix (58 tests), stale STATIC_ALLOWLIST assertion observation, entry criteria, and exit criteria frozen. Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no dispatch implementation, no Tool Handler call, no dispatch, no execution, no Provider Schema sending, no Provider API call, no allowlist change, no Controlled Execution started.*
