# Phase 1G-04-25: Handler Lookup Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-25 |
| Title | Handler Lookup Scope Freeze |
| Status | Frozen (handler lookup boundary design only, no implementation) |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-25 handler lookup scope freeze) |
| Dependencies | Phase 1G-04-24 completed locally |
| Branch | dev-huangruibang |
| Base commit | `e21c56450a94141ba2731661dc25a53865a143ed` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future handler lookup goal
2. Documents why handler lookup is still not execution
3. Freezes the relationship between handler lookup and pre-execution audit
4. Freezes the relationship between handler lookup and STATIC_ALLOWLIST
5. Freezes the relationship between handler lookup and tool registry / catalog
6. Freezes the future handler descriptor structure
7. Freezes the future handler lookup ID strategy
8. Freezes the future handler lookup timing
9. Freezes the future handler lookup failure contract
10. Freezes the future handler lookup success contract
11. Freezes the future execute gate order including handler lookup gates
12. Freezes the future OpenAPI schema-only strategy
13. Freezes the future route governance strategy
14. Defines future allowed files and forbidden files
15. Defines the future test matrix (47 tests)
16. Defines entry criteria and exit criteria for future implementation
17. Defines acceptance criteria for Phase 1G-04-25
18. Records the existing stale STATIC_ALLOWLIST assertion observation
19. Does **not** implement handler lookup
20. Does **not** create a handler registry adapter
21. Does **not** call Tool Handler
22. Does **not** dispatch tools
23. Does **not** execute tools
24. Does **not** implement post-execution audit
25. Does **not** send Provider Schema
26. Does **not** call Provider API
27. Does **not** modify execute runtime behavior
28. Does **not** modify token runtime behavior
29. Does **not** modify digest runtime behavior
30. Does **not** modify pre-execution audit runtime behavior
31. Does **not** modify OpenAPI
32. Does **not** add runtime routes
33. Does **not** start real Controlled Execution

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-25 = **Handler Lookup Scope Freeze**.

This phase freezes the future handler lookup boundary.

This phase does not implement handler lookup.
This phase does not call Tool Handler.
This phase does not dispatch tools.
This phase does not execute tools.
This phase does not implement post-execution audit.
This phase does not send Provider Schema.
This phase does not call Provider API.
This phase does not modify execute runtime behavior.
This phase does not modify pre-execution audit behavior.
This phase does not modify token behavior.
This phase does not modify digest behavior.
This phase does not modify OpenAPI.
This phase does not add runtime routes.
This phase does not start real Controlled Execution.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Remote HEAD | `e21c56450a94141ba2731661dc25a53865a143ed` |
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
| Valid token + valid digest + pre-execution audit written final block | `blocked_handler_lookup_not_enabled` |
| Handler lookup | Not enabled |
| Tool Handler call | Not enabled |
| Dispatch | Not enabled |
| Execution | Disabled |
| Post-execution audit | Not implemented |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

---

## 3. Handler Lookup Goal

Future handler lookup should resolve a safe handler descriptor for an already approved, audited, allowlisted `canonicalName`.

Handler lookup should occur only after:

1. Kill switch gate passed
2. Static allowlist gate passed
3. Dry-run historical lookup passed
4. Confirmation token gate passed
5. Digest verification gate passed
6. Pre-execution audit was written successfully
7. Explicit later phase enables handler lookup

### 3.1 Handler Lookup Is Not Execution

Handler lookup is not execution.
Handler lookup is not dispatch.
Handler lookup must not call the handler.
Handler lookup must not run tool code.
Handler lookup must not send Provider Schema.
Handler lookup must not call Provider API.
Handler lookup must only resolve metadata needed for a future dispatch gate.

### 3.2 Necessary but Not Sufficient

Handler lookup is **necessary but not sufficient**.

- Passing handler lookup must not execute a tool.
- Passing handler lookup must not dispatch a tool.
- After handler lookup succeeds, execute must still block at `blocked_dispatch_not_enabled` or equivalent.

---

## 4. Relationship With Pre-Execution Audit

Pre-execution audit is the durable record that an execute attempt passed all pre-handler gates.

Handler lookup may only be considered after a successful pre-execution audit write.

### 4.1 Future Handler Lookup Event Should Reference

1. `preExecutionAuditId`
2. `executeRequestId`
3. `dryRunRequestId`
4. `dryRunDecisionDigest`
5. `canonicalName`
6. `confirmationTokenId`
7. Pre-execution audit status

### 4.2 Must Not

Handler lookup must not mutate pre-execution audit records.
Handler lookup must not rewrite dry-run audit records.
Handler lookup must not rewrite token records.
Handler lookup must not be treated as execution proof.

---

## 5. Relationship With STATIC_ALLOWLIST

Handler lookup is allowed only for `canonicalName` already approved by `STATIC_ALLOWLIST`.

`STATIC_ALLOWLIST` remains the first static policy boundary.
Handler lookup must not broaden allowlist policy.
Handler lookup must not dynamically allow tools.
Handler lookup must not wildcard-match tool names.
Handler lookup must not infer permission from handler existence.

### 5.1 Future Behavior

If `canonicalName` is not in `STATIC_ALLOWLIST`, execution must block before handler lookup.

If handler exists but `canonicalName` is not allowlisted, it must still block.

If `canonicalName` is allowlisted but handler is missing, it must block at `handler_lookup_not_found`.

### 5.2 Must Preserve

```python
STATIC_ALLOWLIST = frozenset({"clarify"})
```

---

## 6. Relationship With Tool Registry / Catalog

### 6.1 Preferred Source

Existing in-process tool registry / catalog metadata already used by Hermes, but only through safe metadata lookup.

### 6.2 Handler Lookup May Inspect

1. `canonicalName`
2. Handler existence
3. Handler identifier
4. Handler module path or registry key
5. Static capability metadata
6. Expected risk tier
7. Expected input schema metadata reference
8. `dispatchEligible` = false in this phase

### 6.3 Handler Lookup Must Not

- Import arbitrary modules dynamically from user input
- `eval` or `exec`
- Load plugins from untrusted paths
- Read provider credentials
- Instantiate provider clients
- Call handler functions
- Call dispatch
- Execute tools
- Change tool policy
- Change allowlist

### 6.4 Registry Abstraction Gap

If the current registry cannot expose safe metadata without side effects:

Future handler lookup implementation must **fail closed** and document the missing registry abstraction.

---

## 7. Handler Descriptor Structure

### 7.1 Recommended Structure

```json
{
  "handlerLookupStatus": "found",
  "handlerDescriptor": {
    "canonicalName": "clarify",
    "handlerId": "handler_clarify",
    "registryKey": "clarify",
    "moduleName": "safe.module.path",
    "callableName": "clarify",
    "riskTier": "R0",
    "allowlisted": true,
    "dispatchAllowed": false,
    "executionAllowed": false,
    "providerSchemaAllowed": false,
    "sideEffectFreeLookup": true
  },
  "handlerLookupId": "hl_...",
  "createdAt": "..."
}
```

### 7.2 Safe Fields Only

Must include safe fields only.

### 7.3 Must Not Include

- Raw arguments
- Raw token
- Full `tokenHash`
- Provider credentials
- Provider Schema payload
- Function object repr if it leaks memory/path details
- Actual callable object
- Secret env values
- Authorization headers
- Cookies
- Execution result

---

## 8. Handler Lookup ID Strategy

### 8.1 Prefix

```
handlerLookupId prefix = hl_
```

### 8.2 Generation

May use:

- `uuid4`
- `ULID`
- `token_urlsafe`
- Safe random

### 8.3 Constraints

`handlerLookupId` is correlation-only.
`handlerLookupId` is not an authorization credential.
`handlerLookupId` must not contain raw token.
`handlerLookupId` must not contain full `tokenHash`.
`handlerLookupId` must not contain raw arguments.

---

## 9. Future Handler Lookup Timing

### 9.1 Handler Lookup Should Occur Only After

1. Execute request accepted
2. Kill switch passed
3. `canonicalName` allowlisted
4. Dry-run historical lookup passed
5. Dry-run binding passed
6. Confirmation token verification passed
7. Confirmation token consumed safely
8. Digest verification passed
9. Pre-execution audit written successfully
10. Explicit handler lookup enable gate passed

### 9.2 Handler Lookup Must Occur Before

1. Dispatch
2. Tool Handler call
3. Tool execution
4. Post-execution audit
5. Provider Schema sending
6. Provider API call

### 9.3 Post-Lookup Block Boundary

If handler lookup fails, execute blocks.
If handler lookup succeeds, execute **still** blocks at `blocked_dispatch_not_enabled` or equivalent boundary.

---

## 10. Failure Contract

### 10.1 Error Codes / Decisions

| Error Code | Decision |
|------------|----------|
| `handler_lookup_not_enabled` | `blocked_handler_lookup_not_enabled` |
| `handler_lookup_unavailable` | `blocked_handler_lookup_unavailable` |
| `handler_lookup_not_found` | `blocked_handler_lookup_not_found` |
| `handler_lookup_not_allowlisted` | `blocked_handler_lookup_not_allowlisted` |
| `handler_lookup_registry_unavailable` | `blocked_handler_lookup_registry_unavailable` |
| `handler_lookup_descriptor_invalid` | `blocked_handler_lookup_descriptor_invalid` |
| `handler_lookup_side_effect_risk` | `blocked_handler_lookup_side_effect_risk` |
| `handler_lookup_policy_mismatch` | `blocked_handler_lookup_policy_mismatch` |
| `handler_lookup_written_but_dispatch_not_enabled` | `blocked_dispatch_not_enabled` |
| `dispatch_not_enabled` | `blocked_dispatch_not_enabled` |

### 10.2 Failure Invariants

All failures must:

- Block before dispatch
- `executionAllowed` = `false`
- `dispatchAllowed` = `false`
- `providerSchemaAllowed` = `false`
- `toolHandlerCalled` = `false`
- `providerApiCalled` = `false`
- `executionStarted` = `false`

---

## 11. Success Contract

If handler lookup succeeds:

1. Response may include `handlerLookupId`
2. Response may include safe `handlerDescriptor`
3. Response may include `preExecutionAuditId`
4. Response may include `executeRequestId`
5. Response must still be blocked
6. Final decision should be `blocked_dispatch_not_enabled`
7. `dispatchAllowed` = `false`
8. `executionAllowed` = `false`
9. `toolHandlerCalled` = `false`
10. `providerApiCalled` = `false`
11. `executionStarted` = `false`

Handler lookup success must **not** be interpreted as execution success.

---

## 12. Future Execute Gate Order

### 12.1 Current State

| Gate Range | Description |
|------------|-------------|
| Gates 1–14 | Kill switch, allowlist, dry-run lookup, dry-run binding gates |
| Gates 15–27 | Confirmation token verification gates |
| Gates 28–37 | Digest verification gates |
| Gates 38–45 | Pre-execution audit gates |
| Current final block | `blocked_handler_lookup_not_enabled` |

### 12.2 Future Handler Lookup Implementation Target

| Gate | Description |
|------|-------------|
| 46 | Handler lookup enable gate |
| 47 | Handler registry available |
| 48 | Handler descriptor lookup by `canonicalName` |
| 49 | Handler descriptor validates `canonicalName` |
| 50 | Handler descriptor matches allowlist / risk tier / policy metadata |
| 51 | Handler descriptor is side-effect-free metadata only |
| 52 | `handlerLookupId` generated |
| 53 | Handler lookup safe response fields available |
| 54 | Block because dispatch is not enabled |
| 55 | Tool Handler still not called |
| 56 | Execution still disabled |

### 12.3 Post-Lookup Block

After handler lookup succeeds, execute **still** blocks.

The next allowed block boundary is `blocked_dispatch_not_enabled`.

No Tool Handler call is allowed in handler lookup implementation.

---

## 13. OpenAPI Strategy

### 13.1 Phase 1G-04-25

Phase 1G-04-25 does **not** modify OpenAPI.

### 13.2 Future Schema-Only Changes

Future handler lookup implementation may require schema-only OpenAPI changes:

| Schema | Possible Refinement |
|--------|---------------------|
| `ToolExecuteData.handlerLookupId` | New optional field |
| `ToolExecuteData.handlerLookupStatus` | New optional field |
| `ToolExecuteData.handlerDescriptor` | New optional safe descriptor object |
| `ToolExecuteErrorCode` | New `handler_lookup_*` error code values |
| `ToolExecuteDecision` | New `blocked_dispatch_not_enabled` decision value |
| `ToolExecuteGateStatus` | Handler lookup gate names |

### 13.3 Path Count Constraint

No new OpenAPI path unless separately approved.

- OpenAPI paths should remain **33**
- Runtime routes should remain **33**
- Tool write routes should remain **0**
- Tool execution routes should remain **1**

---

## 14. Route Governance Strategy

### 14.1 Preferred Future Implementation

No new route.

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### 14.2 If Route Change Required

If future handler lookup implementation requires a route change:

1. Must **stop** and create a separate route-governed scope freeze
2. Must **not** bundle route changes into handler lookup implementation

---

## 15. Future Allowed Files

These are future allowed files for the handler lookup implementation phase only. They are **not** modified in Phase 1G-04-25, except docs files allowed by this docs-only phase.

### 15.1 Backend

```
hermes_cli/dev_web_tool_handler_lookup.py  (new — recommended handler lookup module)
hermes_cli/dev_web_tool_execute.py
hermes_cli/dev_web_tool_pre_execution_audit.py
hermes_cli/dev_web_tool_execute_digest.py
hermes_cli/dev_web_tool_execute_confirmation.py
hermes_cli/dev_web_tool_execute_preflight.py
hermes_cli/dev_web_tool_policy.py
hermes_cli/dev_web_api.py
```

### 15.2 OpenAPI

```
docs/webui/openapi/dev-web-api-v1.yaml  (schema-only changes if approved)
```

### 15.3 Tests

```
tests/test_dev_web_tool_handler_lookup.py  (new)
tests/test_dev_web_tool_execute.py
tests/test_dev_web_tool_execute_api.py
tests/test_dev_web_tool_pre_execution_audit.py
tests/test_dev_web_tool_execute_digest.py
tests/test_dev_web_tool_execute_confirmation.py
tests/test_dev_web_tool_execute_preflight.py
tests/test_dev_check_webui.py
tests/test_dev_web_0c06_closure.py
```

### 15.4 Documentation

```
docs/webui/phase-1g-04-25-handler-lookup-scope.md
docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md
docs/webui/phase-1-implementation-plan.md
```

### 15.5 Declaration

These are **future allowed files only.** They are **not** modified in Phase 1G-04-25, except docs files allowed by this docs-only phase.

---

## 16. Future Forbidden Files

The following must **not** be modified in any handler lookup implementation phase:

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

## 17. Future Test Matrix

The following tests must pass when handler lookup implementation arrives. **None are added in Phase 1G-04-25.**

### 17.1 Handler Descriptor Tests (12 tests)

| # | Test | Expected |
|---|------|----------|
| 1 | Handler descriptor includes `canonicalName` | Field present |
| 2 | Handler descriptor includes `handlerId` | Field present |
| 3 | Handler descriptor includes `registryKey` | Field present |
| 4 | Handler descriptor includes `riskTier` | Field present |
| 5 | Handler descriptor includes `allowlisted=true` for `clarify` | `true` |
| 6 | Handler descriptor includes `dispatchAllowed=false` | `false` |
| 7 | Handler descriptor includes `executionAllowed=false` | `false` |
| 8 | Handler descriptor excludes raw arguments | No raw arguments |
| 9 | Handler descriptor excludes raw token | No raw token |
| 10 | Handler descriptor excludes full `tokenHash` | No full `tokenHash` |
| 11 | Handler descriptor excludes provider credentials | No credentials |
| 12 | Handler descriptor excludes Provider Schema | No Provider Schema |

### 17.2 Handler Lookup Gate Tests (10 tests)

| # | Test | Expected |
|---|------|----------|
| 13 | Lookup is not attempted before pre-execution audit success | Blocks earlier |
| 14 | Non-allowlisted `canonicalName` blocks before lookup | `blocked_handler_lookup_not_allowlisted` |
| 15 | Missing handler blocks at `handler_lookup_not_found` | `blocked_handler_lookup_not_found` |
| 16 | Registry unavailable blocks | `blocked_handler_lookup_registry_unavailable` |
| 17 | Descriptor invalid blocks | `blocked_handler_lookup_descriptor_invalid` |
| 18 | Descriptor `canonicalName` mismatch blocks | `blocked_handler_lookup_policy_mismatch` |
| 19 | Descriptor risk tier mismatch blocks | `blocked_handler_lookup_policy_mismatch` |
| 20 | Side-effect risk blocks | `blocked_handler_lookup_side_effect_risk` |
| 21 | Lookup success returns `handlerLookupId` | ID present |
| 22 | Lookup success returns safe `handlerDescriptor` | Descriptor present |

### 17.3 Execute Integration Tests (9 tests)

| # | Test | Expected |
|---|------|----------|
| 23 | Valid token + valid digest + pre-execution audit + lookup failure blocks | Blocked |
| 24 | Valid token + valid digest + pre-execution audit + lookup success still blocks | Blocked |
| 25 | Final block after lookup success is `blocked_dispatch_not_enabled` | Correct decision |
| 26 | No dispatch after lookup success | `dispatchAllowed=false` |
| 27 | No Tool Handler call after lookup success | `toolHandlerCalled=false` |
| 28 | No execution after lookup success | `executionStarted=false` |
| 29 | No Provider Schema after lookup success | `providerSchemaAllowed=false` |
| 30 | No Provider API after lookup success | `providerApiCalled=false` |
| 31 | Side-effect flags remain `false` after lookup success | All `false` |

### 17.4 Security Invariant Tests (10 tests)

| # | Test | Expected |
|---|------|----------|
| 32 | All handler lookup failures block before dispatch | `dispatchAllowed=false` |
| 33 | All failures keep side-effect flags `false` | All `false` |
| 34 | Raw token never appears in handler lookup response | No raw token |
| 35 | Full `tokenHash` never appears in handler lookup response | No full `tokenHash` |
| 36 | Raw arguments never appear in handler lookup response | No raw arguments |
| 37 | Secrets never appear in handler lookup response | No secrets |
| 38 | Provider is never called | `providerApiCalled=false` |
| 39 | Tool Handler is never called | `toolHandlerCalled=false` |
| 40 | Dispatch is never called | `dispatchAllowed=false` |
| 41 | Execution is never started | `executionStarted=false` |

### 17.5 Route Governance Tests (5 tests)

| # | Test | Expected |
|---|------|----------|
| 42 | OpenAPI paths remain 33 unless separately approved | 33 |
| 43 | Runtime routes remain 33 unless separately approved | 33 |
| 44 | Tool write routes remain 0 | 0 |
| 45 | Tool execution routes remain 1 | 1 |
| 46 | `STATIC_ALLOWLIST` remains `{"clarify"}` | `frozenset({"clarify"})` |

### 17.6 Optional Cleanup Test (1 test)

| # | Test | Expected |
|---|------|----------|
| 47 | Stale `STATIC_ALLOWLIST len==0` assertions are removed or updated in a separate approved cleanup phase only | Separate phase required |

---

## 18. Existing Out-of-Scope Observation

Two non-gate, non-committed test files currently contain stale assertions:

- `tests/test_dev_web_tool_policy_service.py`
- `tests/test_dev_web_tool_schema_preview_service.py`

**Issue:**

- Stale assertions expect `len(STATIC_ALLOWLIST) == 0`
- `STATIC_ALLOWLIST` is already `frozenset({"clarify"})`
- This issue existed before Phase 1G-04-24
- It was outside Phase 1G-04-24 gate list
- It was not caused by commit `e21c56450a94141ba2731661dc25a53865a143ed`

Phase 1G-04-25 must **not** fix these assertions unless user explicitly changes this phase scope.

**Recommended future cleanup:**

- Separate docs/code cleanup task
- Update stale assertions to expect `{"clarify"}`
- Run affected tests explicitly

---

## 19. Future Implementation Entry Criteria

Before handler lookup implementation may begin, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-25 docs pushed |
| 2 | No P0/P1 open |
| 3 | User explicitly approves handler lookup implementation |
| 4 | Remote and local branch synchronized |
| 5 | `STATIC_ALLOWLIST` remains exactly `{"clarify"}` |
| 6 | Route governance green |
| 7 | Confirmation token gate green |
| 8 | Digest verification gate green |
| 9 | Pre-execution audit gate green |
| 10 | Valid token + valid digest + pre-execution audit currently blocks at handler lookup boundary |
| 11 | Provider schema not sent |
| 12 | Tool dispatch disabled |
| 13 | Tool execution disabled |
| 14 | Production gateway stable |

---

## 20. Future Implementation Exit Criteria

After handler lookup implementation, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Handler lookup module implemented |
| 2 | Handler descriptor builder implemented |
| 3 | Handler registry metadata lookup implemented |
| 4 | `handlerLookupId` generated |
| 5 | Handler lookup failure blocks |
| 6 | Handler lookup success still blocks at dispatch boundary |
| 7 | Handler descriptor returned with safe metadata only |
| 8 | No Tool Handler call after lookup success |
| 9 | No dispatch after lookup success |
| 10 | No execution after lookup success |
| 11 | No Provider Schema after lookup success |
| 12 | No Provider API after lookup success |
| 13 | OpenAPI paths remain 33 unless separately approved |
| 14 | Runtime routes remain 33 unless separately approved |
| 15 | Tool write routes remain 0 |
| 16 | Tool execution routes remain 1 |
| 17 | `STATIC_ALLOWLIST` remains `{"clarify"}` |
| 18 | Production gateway unaffected |

---

## 21. Acceptance Criteria for Phase 1G-04-25

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only | |
| 2 | New handler lookup scope doc added | |
| 3 | Phase 1G-04 scope doc updated | |
| 4 | Implementation plan updated | |
| 5 | Phase 1G-04-24 doc updated with next dependency | |
| 6 | No code changes | |
| 7 | No OpenAPI file changes | |
| 8 | No tests changed | |
| 9 | No frontend changes | |
| 10 | No routes changed | |
| 11 | No execute route behavior changes | |
| 12 | No token behavior changes | |
| 13 | No digest behavior changes | |
| 14 | No pre-execution audit behavior changes | |
| 15 | No `STATIC_ALLOWLIST` changes | |
| 16 | `STATIC_ALLOWLIST` remains `frozenset({"clarify"})` | |
| 17 | No handler lookup implementation | |
| 18 | No Tool Handler call | |
| 19 | No Tool Dispatch | |
| 20 | No Tool Execution | |
| 21 | No Provider Schema sent | |
| 22 | No Provider API called | |
| 23 | OpenAPI paths = 33 | |
| 24 | Runtime routes = 33 | |
| 25 | Tool GET = 4 | |
| 26 | Tool write = 0 | |
| 27 | Tool dry-run = 1 | |
| 28 | Tool execution = 1 | |
| 29 | Execute route remains blocked-only | |
| 30 | Real Controlled Execution not started | |
| 31 | Local docs-only commit created | |
| 32 | Not pushed | |

---

## 22. P0 Risks (Blocking)

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
| 10 | `STATIC_ALLOWLIST` modified | Verify unchanged; reject if modified |
| 11 | Allowlist expanded | Verify unchanged; reject if expanded |
| 12 | Handler lookup implemented | Verify diff; reject if handler lookup code added |
| 13 | Tool Handler called | Verify no handler invocation; reject if found |
| 14 | Tool Dispatch called | Verify no dispatch; reject if found |
| 15 | Tool executed | Verify no execution; reject if found |
| 16 | Provider API called / Schema sent | Verify no provider calls; reject if found |
| 17 | Blocked response has `executionAllowed=true` | Content search; reject if found |
| 18 | Blocked response has `dispatchAllowed=true` | Content search; reject if found |
| 19 | Blocked response has `providerSchemaAllowed=true` | Content search; reject if found |
| 20 | Blocked response has `toolHandlerCalled=true` | Content search; reject if found |
| 21 | Blocked response has `providerApiCalled=true` | Content search; reject if found |
| 22 | Blocked response has `executionStarted=true` | Content search; reject if found |
| 23 | Tool write routes > 0 | Verify route governance; reject if changed |
| 24 | Tool execution routes ≠ 1 | Verify route governance; reject if changed |
| 25 | OpenAPI path count changes unexpectedly | Verify count; reject if changed |
| 26 | Runtime route count changes unexpectedly | Verify count; reject if changed |
| 27 | Frontend modified | Verify diff; reject if found |
| 28 | Agent/tools modified | Verify diff; reject if found |
| 29 | Production Gateway affected | Verify PID; reject if changed |
| 30 | Real secret leaked | Content search; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-25 Failed."**

---

## 23. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Handler lookup goal missing | Verify Section 3 |
| 2 | Pre-execution audit relationship missing | Verify Section 4 |
| 3 | STATIC_ALLOWLIST relationship missing | Verify Section 5 |
| 4 | Tool registry relationship missing | Verify Section 6 |
| 5 | Handler descriptor structure missing | Verify Section 7 |
| 6 | Handler lookup ID strategy missing | Verify Section 8 |
| 7 | Handler lookup timing missing | Verify Section 9 |
| 8 | Failure contract missing | Verify Section 10 |
| 9 | Success contract missing | Verify Section 11 |
| 10 | Future gate order missing | Verify Section 12 |
| 11 | Future OpenAPI strategy missing | Verify Section 13 |
| 12 | Future route governance missing | Verify Section 14 |
| 13 | Future allowed files missing | Verify Section 15 |
| 14 | Future forbidden files missing | Verify Section 16 |
| 15 | Future test matrix missing | Verify Section 17 |
| 16 | Stale STATIC_ALLOWLIST assertion observation missing | Verify Section 18 |
| 17 | Entry criteria missing | Verify Section 19 |
| 18 | Exit criteria missing | Verify Section 20 |
| 19 | Docs incorrectly claim handler lookup implemented | Content review |
| 20 | Docs incorrectly claim Tool Handler called | Content review |
| 21 | Docs incorrectly claim dispatch enabled | Content review |
| 22 | Route governance failed | Run tests; verify counts |
| 23 | OpenAPI paths ≠ 33 | Verify count |
| 24 | Runtime routes ≠ 33 | Verify count |
| 25 | Tool GET ≠ 4 | Verify count |
| 26 | Tool write ≠ 0 | Verify count |
| 27 | Tool dry-run ≠ 1 | Verify count |
| 28 | Tool execution ≠ 1 | Verify count |
| 29 | `STATIC_ALLOWLIST` ≠ `{"clarify"}` | Verify value |
| 30 | compileall failed | Run compileall |
| 31 | ruff failed | Run ruff |
| 32 | memory-check failed | Run memory-check |
| 33 | dev-check failed | Run dev-check |
| 34 | Worktree has unexpected files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 24. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Handler lookup not yet implemented | Expected — scope freeze only |
| 2 | Tool Handler call not yet enabled | Expected — future phase |
| 3 | Dispatch not yet enabled | Expected — future phase |
| 4 | Execution not yet enabled | Expected — future phase |
| 5 | Post-execution audit not yet implemented | Expected — future phase |
| 6 | Frontend execute UI not implemented | Expected — future phase |
| 7 | Browser smoke not re-run | Expected — no frontend changes |
| 8 | Audit read API not yet implemented | Expected — future phase |
| 9 | Audit viewer not yet implemented | Expected — future phase |
| 10 | Clarify handler-level audit still needs future phase | Expected — future work |
| 11 | Lookup performance can be optimized later | Expected — optimization deferred |
| 12 | Multi-file audit rotation support may be future work | Expected — deferred |
| 13 | Append-only JSONL audit write race conditions need future local-dev handling | Expected — local dev constraints |
| 14 | Pre-existing stale `STATIC_ALLOWLIST` assertions remain in non-gate tests until separate cleanup | Expected — separate cleanup task |

---

*Phase 1G-04-25 Handler Lookup Scope Freeze: handler lookup goal, relationship with pre-execution audit, relationship with STATIC_ALLOWLIST, relationship with tool registry / catalog, handler descriptor structure, handler lookup ID strategy, lookup timing, failure contract, success contract, future execute gate order, OpenAPI scope, route governance scope, future allowed and forbidden files, future test matrix (47 tests), stale STATIC_ALLOWLIST assertion observation, entry criteria, and exit criteria frozen. Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no handler lookup implementation, no Tool Handler call, no dispatch, no execution, no Provider Schema sending, no Provider API call, no audit read API, no audit viewer, no allowlist change, no Controlled Execution started.*

---

## Implementation Record (Phase 1G-04-26)

**Implemented in Phase 1G-04-26:**
- Minimal safe handler lookup module (`dev_web_tool_handler_lookup.py`)
- Safe handler descriptor builder with metadata-only fields
- Safe handler metadata lookup (minimal static descriptor mapping for `clarify`)
- `handlerLookupId` generation (prefix `hl_`)
- Handler descriptor validation
- Execute route handler lookup gates 46–56
- Safe handler descriptor response fields
- OpenAPI schema-only updates

**Still not implemented:**
- Tool Handler call
- dispatch
- execution
- post-execution audit
- provider call
- Provider Schema sending
- real Controlled Execution
