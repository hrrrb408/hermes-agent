# Phase 1G-04-10: Execute Route Contract / OpenAPI Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-10 |
| Title | Execute Route Contract / OpenAPI Scope Freeze |
| Status | Frozen (route contract and OpenAPI scope definition only, no implementation) |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-10 execute route contract / OpenAPI scope freeze) |
| Dependencies | Phase 1G-04-09 completed locally |
| Branch | dev-huangruibang |
| Base commit | `f5644ccadf61cd557ce743c2e9924db4c81ca54a` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future execute route contract and OpenAPI scope
2. Defines the future route definition for `POST /api/dev/v1/tools/execute`
3. Defines the route governance delta (future only)
4. Defines the Tool write vs Tool execution classification
5. Defines the future request schema draft
6. Defines the future response schema draft
7. Defines the future decision enum draft
8. Defines the future gate status model draft
9. Defines the future audit status model draft
10. Defines the future result preview model draft
11. Defines the future error code draft
12. Defines the blocked-by-default contract
13. Defines the dry-run preflight contract
14. Defines the confirmation token contract
15. Defines the future OpenAPI file strategy
16. Defines the future runtime file strategy
17. Defines the future forbidden files
18. Defines the future test matrix
19. Defines the entry criteria for future implementation
20. Defines the exit criteria for future implementation
21. Does **not** add the execute route
22. Does **not** modify OpenAPI
23. Does **not** modify runtime routes
24. Does **not** implement Controlled Execution
25. Does **not** call tool handlers
26. Does **not** call providers
27. Does **not** execute tools

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-10 = **Execute Route Contract / OpenAPI Scope Freeze**

- This phase freezes the future execute route contract and OpenAPI scope.
- This phase does **not** add the execute route.
- This phase does **not** modify OpenAPI.
- This phase does **not** modify runtime routes.
- This phase does **not** modify route governance.
- This phase does **not** implement Controlled Execution.
- This phase does **not** call tool handlers.
- This phase does **not** call providers.
- This phase does **not** execute tools.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `f5644ccadf61cd557ce743c2e9924db4c81ca54a` |
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |
| Dry-Run API | Implemented (`POST /api/dev/v1/tools/dry-run`) |
| Dry-Run Audit Writer | Implemented (`dev_web_tool_dry_run_audit.py`) |
| `auditWritten` | Audit write success only (not execution) |
| Controlled Execution Gate Design | Frozen (Phase 1G-04-08) |
| Controlled Execution Implementation Scope | Frozen (Phase 1G-04-09) |
| Controlled Execution implementation | Not started |
| STATIC_ALLOWLIST | Empty (empty frozenset) |
| Provider Schema Sending | Not sent |
| Tool Dispatch | 0 |
| Tool Handler Invocation | None |
| Tool Execution | Disabled |
| Kill Switches | All disabled (unset) |
| Production Gateway PID | 80468 |

---

## 3. Execute Route Goal

The future execute route provides a controlled backend entry point for gated tool execution.

### 3.1 Core Goals

1. **Controlled backend entry point:** The execute route is the single entry point for tool execution in the Dev WebUI.
2. **Blocked by default:** The route must be blocked by default — no execution occurs without all gates passing.
3. **Classified as Tool execution route:** The route must be counted separately from Tool dry-run routes and Tool write routes.
4. **Not a generic write route:** The route must not be hidden under a generic write route category.
5. **No handler until gates pass:** The route must not call the Tool Handler until all gates pass.
6. **No Provider Schema:** The route must never send Provider Schema.
7. **No Provider API:** The route must never call Provider API.

### 3.2 Explicit Non-Properties

The future execute route does **not**:

- Enable arbitrary tool execution
- Send tool schemas to providers
- Modify STATIC_ALLOWLIST automatically
- Bypass any gate for any tool
- Execute tools in production
- Execute R4/R5 tools under any circumstance
- Execute denylisted tools under any circumstance
- Call Provider API for any reason

---

## 4. Non-Goals

The following are explicitly **not** part of Phase 1G-04-10:

1. No execute route added
2. No OpenAPI path added
3. No OpenAPI schema added
4. No runtime route modified
5. No route governance modified
6. No Controlled Execution implemented
7. No tool execution
8. No Tool Handler call
9. No Provider API call
10. No Provider Schema sent
11. No STATIC_ALLOWLIST modification
12. No frontend modification
13. No audit read API
14. No audit viewer UI
15. No first executable tool selection
16. No allowlist activation

---

## 5. Future Route Definition

### 5.1 Route

```
POST /api/dev/v1/tools/execute
```

### 5.2 Route Properties

| Property | Value |
|----------|-------|
| Route group | tools |
| Route kind | execution |
| HTTP method | POST |
| Authentication | Same dev web API auth model as existing dev routes |
| Mutation classification | Not generic write route; classified as tool execution route |
| Availability | Dev only |
| Default behavior | Blocked |

### 5.3 Phase 1G-04-10 Declaration

**This route is not added in Phase 1G-04-10.**

---

## 6. Route Governance Delta

### 6.1 Current State

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

### 6.2 Future State (After Execute Route Implementation)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### 6.3 Delta Declaration

- The future delta is **not** applied in Phase 1G-04-10.
- Phase 1G-04-10 keeps OpenAPI paths = 32 and Runtime routes = 32.
- The delta will be applied only when the execute route is added in a future implementation phase.

---

## 7. Tool Write vs Tool Execution Classification

### 7.1 Classification Rules

1. **Tool write routes remain 0.** The execute route must not increase Tool write routes.
2. **Execute route classified as Tool execution route.** The execute route belongs to the execution route bucket.
3. **Dry-run route remains Tool dry-run route.** The existing dry-run route is not reclassified.
4. **Audit writer internal JSONL write does not create a Tool write route.** The audit writer's internal file I/O is not a route.

### 7.2 Classification Rationale

| Classification | Tracks |
|---------------|--------|
| Tool write routes | API routes that mutate tool policy / configuration / state through generic tool write endpoints |
| Tool execution routes | API routes capable of invoking tool handlers |
| Tool dry-run routes | API routes that simulate tool policy decisions without execution |
| Tool GET routes | API routes that read tool information |

### 7.3 Execute Route Classification

The execute route belongs to the **execution route bucket**, even when initially blocked. This is because:

1. The route's purpose is to invoke tool handlers (when all gates pass).
2. The route has the potential to cause side effects.
3. Treating it as a write route would obscure its execution nature.
4. Treating it as a dry-run route would conflate simulation with execution.

---

## 8. Future Request Schema Draft

### 8.1 ToolExecuteRequest

The following schema defines the future request body for the execute endpoint.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `canonicalName` | string | Yes | Tool canonical name |
| `argumentsPreview` | object | Yes | Arguments (sanitized) |
| `dryRunRequestId` | string | Yes | Dry-run request correlation ID |
| `dryRunDecisionDigest` | string | Yes | SHA-256 digest of dry-run decision |
| `confirmationToken` | string | Yes | Human confirmation token |
| `requestId` | string | Conditional | Request correlation ID (required or optional per implementation phase) |
| `sourceContext` | string | No | Source context for the execute request |
| `uiOrigin` | string | No | UI component that initiated the request |
| `clientCreatedAt` | string | No | ISO 8601 client-side timestamp |

### 8.2 Required Fields

- `canonicalName` — **required**: Identifies the tool to execute.
- `argumentsPreview` — **required but sanitized**: Must be the same sanitized arguments used in dry-run preflight.
- `dryRunRequestId` — **required**: Must reference a valid prior dry-run request.
- `dryRunDecisionDigest` — **required**: SHA-256 digest binding the dry-run decision to this execution request.
- `confirmationToken` — **required**: Must be a valid, non-expired, non-reused confirmation token.

### 8.3 Optional Fields

- `sourceContext` — optional string describing the execution context.
- `uiOrigin` — optional string identifying the originating UI component.
- `clientCreatedAt` — optional ISO 8601 timestamp from the client.
- `requestId` — optional or required according to the final implementation phase decision.

### 8.4 Prohibited Request Content

The following must **never** appear in a request:

- Raw secrets (API keys, tokens, passwords)
- Provider API keys
- Raw authorization headers
- Raw cookies
- Raw stack traces
- Internal file paths
- Callable references

---

## 9. Future Response Schema Draft

### 9.1 ToolExecuteResponse

```
ToolExecuteResponse:
  ok: boolean
  data: ToolExecuteData (when ok=true)
  error: ToolExecuteError (when ok=false)
  meta: ResponseMeta
```

### 9.2 ToolExecuteData

| Field | Type | Description |
|-------|------|-------------|
| `canonicalName` | string | Tool canonical name |
| `exists` | boolean | Whether the tool exists in inventory |
| `riskTier` | string or null | Risk tier (R0–R5) or null if unknown |
| `decision` | string | Gate decision result (ToolExecuteDecision enum) |
| `gateStatus` | list[ToolExecuteGateStatus] | Per-gate pass/fail status |
| `auditStatus` | ToolExecuteAuditStatus | Audit write status |
| `executionAttempted` | boolean | Whether handler invocation was attempted |
| `executionStarted` | boolean | Whether handler execution started |
| `executionCompleted` | boolean | Whether handler execution completed |
| `resultPreview` | ToolExecuteResultPreview or null | Sanitized execution result preview |
| `errorCode` | string or null | Error code if blocked or failed |
| `policyNotes` | list[string] | Additional policy notes |
| `executionAllowed` | boolean | **Must be false unless all gates pass** |
| `dispatchAllowed` | boolean | **Must be false unless all gates pass** |
| `providerSchemaAllowed` | boolean | **Must always be false** |
| `toolHandlerCalled` | boolean | Whether the tool handler was actually called |
| `providerApiCalled` | boolean | Whether the provider API was called |

### 9.3 Initial Default Values

| Field | Default | Condition |
|-------|---------|-----------|
| `executionAllowed` | `false` | Unless all gates pass in a future implementation phase |
| `dispatchAllowed` | `false` | Unless all gates pass in a future implementation phase |
| `providerSchemaAllowed` | `false` | Always — no future phase may set this to `true` via the execute route |
| `toolHandlerCalled` | `false` | For all blocked responses |
| `providerApiCalled` | `false` | Always unless a separate future provider phase explicitly allows |

---

## 10. Future Decision Enum Draft

### 10.1 ToolExecuteDecision

The following decision values may be returned by the execute route:

| Value | Description |
|-------|-------------|
| `blocked` | Generic blocked (default) |
| `blocked_requires_dry_run` | No prior dry-run decision found |
| `blocked_requires_audit` | Dry-run audit not written |
| `blocked_requires_confirmation` | No valid confirmation token |
| `blocked_by_kill_switch` | Kill switches not enabled |
| `blocked_by_allowlist` | Tool not in STATIC_ALLOWLIST |
| `blocked_by_denylist` | Tool in STATIC_DENYLIST |
| `blocked_by_risk_tier` | Risk tier not eligible (R2+ initially) |
| `blocked_by_digest_mismatch` | Argument or canonicalName digest mismatch |
| `would_execute` | All gates pass but execution not yet attempted (gate skeleton) |
| `executed` | Handler invoked and completed successfully |
| `execution_failed` | Handler invoked but raised an error |

### 10.2 Phase 1G-04-10 Declaration

**This enum is not added to OpenAPI in Phase 1G-04-10.**

---

## 11. Gate Status Model Draft

### 11.1 ToolExecuteGateStatus

| Field | Type | Description |
|-------|------|-------------|
| `gateName` | string | Name of the gate |
| `passed` | boolean | Whether the gate passed |
| `reasonCode` | string or null | Machine-readable reason if gate failed |
| `message` | string or null | Human-readable message if gate failed |
| `blocking` | boolean | Whether gate failure blocks execution |

### 11.2 Minimum Gates

The following gates must be evaluated in sequence. Failure of any blocking gate stops evaluation and returns a blocked response.

| Gate Name | Description | Blocking |
|-----------|-------------|----------|
| `kill_switch_gate` | Kill switches must be enabled | Yes |
| `agent_tools_gate` | Agent tools switch must be enabled | Yes |
| `static_allowlist_gate` | Tool must be in STATIC_ALLOWLIST | Yes |
| `denylist_gate` | Tool must not be in STATIC_DENYLIST | Yes |
| `risk_tier_gate` | Risk tier must be eligible | Yes |
| `dry_run_preflight_gate` | Valid prior dry-run decision required | Yes |
| `dry_run_audit_gate` | Dry-run audit must be written | Yes |
| `confirmation_token_gate` | Valid confirmation token required | Yes |
| `argument_digest_gate` | Argument digest must match | Yes |
| `pre_execution_audit_gate` | Pre-execution audit write required | Yes |
| `handler_lookup_gate` | Handler must be available | Yes |
| `timeout_gate` | Execution must have timeout configured | Yes |
| `result_sanitization_gate` | Result sanitization must be available | Yes |
| `post_execution_audit_gate` | Post-execution audit attempted (best-effort) | No |

---

## 12. Audit Status Model Draft

### 12.1 ToolExecuteAuditStatus

| Field | Type | Description |
|-------|------|-------------|
| `dryRunAuditWritten` | boolean | Whether the dry-run audit was written before execution |
| `preExecutionAuditWritten` | boolean | Whether the pre-execution audit was written |
| `postExecutionAuditWritten` | boolean | Whether the post-execution audit was written |
| `auditEventId` | string or null | Audit event ID if pre-execution audit succeeded |
| `auditErrorCode` | string or null | Error code if audit write failed |

### 12.2 Audit Failure Semantics

1. **Pre-execution audit failure blocks handler call.** If the pre-execution audit write fails, the handler is never invoked.
2. **Post-execution audit failure is reported safely.** The response is returned, but the audit failure is noted.
3. **Audit status never includes raw secrets.** All audit fields are sanitized.

---

## 13. Result Preview Model Draft

### 13.1 ToolExecuteResultPreview

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `success`, `error`, `timeout`, `too_large`, `sanitization_failed` |
| `contentType` | string | Content type of the result |
| `preview` | string or null | Sanitized preview text |
| `truncated` | boolean | Whether the result was truncated |
| `sizeBytes` | integer | Original result size in bytes |
| `redactionApplied` | boolean | Whether redaction was applied |
| `errorClass` | string or null | Error class if status is error |

### 13.2 Result Preview Constraints

| Constraint | Value |
|-----------|-------|
| Max preview size | 64 KiB |
| Raw stack traces | Prohibited |
| Raw secrets | Prohibited |
| Provider key values | Prohibited |

---

## 14. Error Code Draft

### 14.1 ToolExecuteErrorCode

The following error codes may be returned by the execute route:

| Error Code | Description |
|-----------|-------------|
| `validation_failed` | Request validation failed |
| `unknown_tool` | Tool not in inventory |
| `denied_tool` | Tool in denylist |
| `risk_tier_blocked` | Risk tier not eligible |
| `kill_switch_disabled` | Kill switches not enabled |
| `allowlist_missing` | Tool not in STATIC_ALLOWLIST |
| `dry_run_required` | No prior dry-run decision |
| `dry_run_not_allowed` | Dry-run decision was not `would_allow` |
| `dry_run_audit_missing` | Dry-run audit not written |
| `confirmation_missing` | No confirmation token provided |
| `confirmation_invalid` | Confirmation token does not match |
| `confirmation_expired` | Confirmation token expired |
| `confirmation_reused` | Confirmation token already used |
| `digest_mismatch` | Argument or canonicalName digest mismatch |
| `pre_execution_audit_failed` | Pre-execution audit write failed |
| `handler_not_available` | Tool handler not found or not available |
| `execution_timeout` | Handler exceeded time limit |
| `execution_failed` | Handler raised an exception |
| `result_too_large` | Result exceeded size limit |
| `result_sanitization_failed` | Result failed sanitization |
| `post_execution_audit_failed` | Post-execution audit write failed |
| `internal_error` | Unexpected internal error |

### 14.2 Blocked Error Invariants

Blocked error responses must:

1. **Not call Tool Handler.** No handler invocation on blocked paths.
2. **Not call Provider API.** No provider API call on blocked paths.
3. **Not dispatch.** No dispatch routing on blocked paths.
4. **Not execute.** No tool execution on blocked paths.

---

## 15. Blocked-by-Default Contract

### 15.1 Default Behavior

The first execute route implementation must be **blocked by default**. This means:

1. **All switches unset:** Response must be `blocked_by_kill_switch`.
2. **STATIC_ALLOWLIST empty:** Response must be `blocked_by_allowlist`.
3. **Missing dry-run preflight:** Blocks execution.
4. **Missing confirmation:** Blocks execution.
5. **Digest mismatch:** Blocks execution.

### 15.2 Hard Invariants

| Invariant | Value |
|-----------|-------|
| `executionAllowed` | `false` for all blocked responses |
| `dispatchAllowed` | `false` for all blocked responses |
| `providerSchemaAllowed` | `false` always |
| `toolHandlerCalled` | `false` for all blocked responses |
| `providerApiCalled` | `false` always |
| `executionAttempted` | `false` for all blocked responses |

### 15.3 No Blocked Response May Call Tool Handler

Regardless of which gate fails:

1. No Tool Handler call.
2. No Provider API call.
3. No dispatch routing.
4. No tool execution.

---

## 16. Dry-Run Preflight Contract

### 16.1 Binding Requirements

Every execute request must reference a prior dry-run decision. The following binding rules apply:

| Requirement | Description |
|-------------|-------------|
| `dryRunRequestId` | Must reference a valid dry-run request |
| Dry-run decision | Must be `would_allow` |
| `auditWritten` | Must be `true` |
| `canonicalName` match | Execute `canonicalName` must match dry-run `canonicalName` |
| Argument digest match | Execute argument digest must match dry-run argument digest |
| Risk tier match | Risk tier must match |
| Preflight expiry | Dry-run decision must not be stale (recommended: ≤ 5 minutes) |

### 16.2 Dry-Run Remains Non-Executing

1. Dry-run is and remains a **non-executing simulation**.
2. Dry-run success (`would_allow`) does **not** imply execution.
3. Dry-run audit success (`auditWritten = true`) is a **precondition** for execution, not execution itself.

---

## 17. Confirmation Token Contract

### 17.1 Token Properties

| Property | Description |
|----------|-------------|
| Generation trigger | Generated only after dry-run preflight succeeds |
| Use count | Single-use only — reuse blocks |
| Expiry | Recommended: ≤ 5 minutes |
| Binding | Binds to specific request parameters |

### 17.2 Token Binding Fields

The confirmation token must bind to all of the following:

| Field | Description |
|-------|-------------|
| `requestId` | Original dry-run request correlation ID |
| `canonicalName` | Exact tool name |
| `argumentDigest` | SHA-256 digest of sanitized arguments |
| `riskTier` | Tool risk tier (R0/R1) |
| `dryRunDecision` | Must be `would_allow` |
| `auditEventId` | Audit event ID from dry-run audit write |
| `timestamp` | ISO 8601 UTC when token was generated |

### 17.3 Prohibited Confirmation Patterns

The following are **never** allowed:

1. **No implicit confirmation.** Confirmation must be explicit.
2. **No UI auto-confirm.** The user must explicitly act.
3. **No provider auto-confirm.** No automated confirmation from any provider.
4. **No confirmation bypass.** No code path that skips the confirmation gate.

---

## 18. Future OpenAPI File Strategy

### 18.1 Future Changes

When the execute route is added in a future implementation phase, the following changes must be made to `docs/webui/openapi/dev-web-api-v1.yaml`:

| Change | Description |
|--------|-------------|
| Add `POST /api/dev/v1/tools/execute` path | Execute endpoint |
| Add `ToolExecuteRequest` schema | Request body |
| Add `ToolExecuteResponse` schema | Standard envelope response |
| Add `ToolExecuteData` schema | Data payload on success |
| Add `ToolExecuteDecision` schema | Gate decision result enum |
| Add `ToolExecuteGateStatus` schema | Per-gate pass/fail status |
| Add `ToolExecuteAuditStatus` schema | Audit write status |
| Add `ToolExecuteErrorCode` schema | Error code enum |
| Add `ToolExecuteResultPreview` schema | Sanitized execution result preview |
| Update expected OpenAPI path count | 32 → 33 |

### 18.2 Phase 1G-04-10 Declaration

**None of these changes are performed in Phase 1G-04-10.** The OpenAPI file is not modified.

---

## 19. Future Runtime File Strategy

### 19.1 Future Allowed Files

The following files may be modified in future Controlled Execution implementation phases. They are **not** modified in Phase 1G-04-10.

| File | Action | Future Phase |
|------|--------|-------------|
| `hermes_cli/dev_web_tool_execute.py` | **New** — Execute gate service module | 1G-04-11 |
| `hermes_cli/dev_web_tool_execute_service.py` | **New** — Execute handler orchestration | 1G-04-11 |
| `hermes_cli/dev_web_api.py` | **Modify** — Add execute route registration | 1G-04-11 |
| `hermes_cli/main.py` | **Modify** — Update dev-check route count | 1G-04-10 implementation |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add execute path + schemas | 1G-04-10 implementation |
| `tests/test_dev_web_tool_execute.py` | **New** — Execute gate unit tests | 1G-04-11 |
| `tests/test_dev_web_tool_execute_api.py` | **New** — Execute API integration tests | 1G-04-11 |
| `tests/test_dev_check_webui.py` | **Modify** — Update route governance expectations | 1G-04-10 implementation |
| `tests/test_dev_web_0c06_closure.py` | **Modify** — Update route governance expectations | 1G-04-10 implementation |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | **Modify** — Add completion records | Per phase |
| `docs/webui/phase-1-implementation-plan.md` | **Modify** — Update phase status | Per phase |

### 19.2 Phase 1G-04-10 Declaration

**These are future allowed files only. They are not modified in Phase 1G-04-10.**

---

## 20. Future Forbidden Files

The following files must **not** be modified during future Controlled Execution implementation phases:

```
apps/hermes-dev-webui/src/          # Frontend changes require separate phase
apps/hermes-dev-webui/tests/        # Frontend tests require separate phase
apps/hermes-dev-webui/e2e/          # E2E tests require separate phase
agent/                              # Agent core must not be modified
tools/                              # Tool implementations must not be modified
toolsets.py                         # Toolset definitions must not be modified
runtime files committed to repo     # No runtime file changes
memory files                        # Memory system must not be modified
review files                        # Review system must not be modified
.env                                # Environment variables must not be modified
.claude/                            # Claude configuration must not be modified
~/.hermes                           # Production home must never be accessed
production state.db                 # Production database must never be accessed
```

---

## 21. Test Matrix for Future Route Contract

The following tests must pass when the execute route is added in a future implementation phase:

### 21.1 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 1 | OpenAPI path count = 33 | When execute route phase arrives |
| 2 | Runtime route count = 33 | When execute route phase arrives |
| 3 | Tool execution route count = 1 | Execute route classified as execution |
| 4 | Tool write route count remains 0 | Execute is not a write route |
| 5 | Execute route classified as execution route | Not dry-run, not write |
| 6 | Execute route not classified as dry-run route | Separate bucket |

### 21.2 Blocked-by-Default Tests

| # | Test | Expected |
|---|------|----------|
| 7 | Execute route blocked by default | All requests blocked |
| 8 | Kill switch unset blocks | `blocked_by_kill_switch` |
| 9 | Kill switch false blocks | `blocked_by_kill_switch` |
| 10 | Kill switch exact true only passes kill switch gate | `"true"` required |
| 11 | STATIC_ALLOWLIST empty blocks | `blocked_by_allowlist` |
| 12 | Unknown tool blocks | `unknown_tool` |
| 13 | Denylisted tool blocks | `denied_tool` |
| 14 | R2 blocked initially | `risk_tier_blocked` |
| 15 | R3 blocked initially | `risk_tier_blocked` |
| 16 | R4 blocked | `risk_tier_blocked` |
| 17 | R5 blocked | `risk_tier_blocked` |

### 21.3 Dry-Run Preflight Tests

| # | Test | Expected |
|---|------|----------|
| 18 | Missing dry-run blocks | `dry_run_required` |
| 19 | Dry-run non-allow blocks | `dry_run_not_allowed` |
| 20 | Dry-run `auditWritten` false blocks | `dry_run_audit_missing` |

### 21.4 Confirmation Tests

| # | Test | Expected |
|---|------|----------|
| 21 | Missing confirmation blocks | `confirmation_missing` |
| 22 | Invalid confirmation blocks | `confirmation_invalid` |
| 23 | Expired confirmation blocks | `confirmation_expired` |
| 24 | Reused confirmation blocks | `confirmation_reused` |

### 21.5 Digest Tests

| # | Test | Expected |
|---|------|----------|
| 25 | Digest mismatch blocks | `digest_mismatch` |

### 21.6 Security Boundary Tests

| # | Test | Expected |
|---|------|----------|
| 26 | Handler not called for blocked response | No handler invocation |
| 27 | Provider not called for blocked response | No provider invocation |
| 28 | Dispatch not called for blocked response | No dispatch routing |
| 29 | Execution not started for blocked response | `executionAttempted = false` |
| 30 | Blocked response is JSON-safe | No non-serializable types |
| 31 | Blocked response has no raw secrets | Content search passes |

---

## 22. Entry Criteria for Future Execute Route Implementation

The following conditions must be met before any execute route implementation phase begins:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-10 docs pushed |
| 2 | No P0/P1 open risks |
| 3 | User explicitly approves execute route contract implementation |
| 4 | OpenAPI delta accepted |
| 5 | Route governance delta accepted |
| 6 | Implementation phase states whether route is blocked-only or may execute |
| 7 | Production gateway stable |
| 8 | Dry-Run API regression green |
| 9 | Audit writer tests green |
| 10 | Dry-Run model regression green |
| 11 | compileall PASS |
| 12 | ruff PASS |
| 13 | memory-check PASS |
| 14 | dev-check PASS |

---

## 23. Exit Criteria for Future Execute Route Contract Implementation

The following conditions must be met for the execute route implementation to be considered complete:

| # | Criterion |
|---|-----------|
| 1 | OpenAPI paths updated only if route added |
| 2 | Runtime routes updated only if route added |
| 3 | Tool execution route count increments only if execute route added |
| 4 | Tool write route remains 0 |
| 5 | Route returns blocked by default |
| 6 | No handler called for blocked route |
| 7 | No provider called |
| 8 | No Provider Schema sent |
| 9 | No STATIC_ALLOWLIST auto-population |
| 10 | All route governance tests green |
| 11 | All execute contract tests green |
| 12 | Production gateway unaffected |

---

## 24. Acceptance Criteria for Phase 1G-04-10

| # | Criterion |
|---|-----------|
| 1 | docs-only |
| 2 | New execute route contract / OpenAPI scope doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | No code changes |
| 6 | No OpenAPI file changes |
| 7 | No tests changed |
| 8 | No frontend changes |
| 9 | No routes changed |
| 10 | OpenAPI paths still 32 |
| 11 | Runtime routes still 32 |
| 12 | Tool GET 4 |
| 13 | Tool write 0 |
| 14 | Tool dry-run 1 |
| 15 | Tool execution 0 |
| 16 | STATIC_ALLOWLIST empty |
| 17 | Tool Execution disabled |
| 18 | Provider Schema not sent |
| 19 | Tool Handler not called |
| 20 | Tool Dispatch 0 |
| 21 | Controlled Execution not implemented |
| 22 | Controlled Execution not started |
| 23 | Local docs-only commit created |
| 24 | Not pushed |

---

## 25. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code changes introduced | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Route count changed | Run governance tests; reject if counts differ |
| 6 | Execution route added | Run governance tests; reject if Tool execution > 0 |
| 7 | Tool Handler called | Verify no handler imports; reject if found |
| 8 | Provider API called | Verify no provider calls; reject if found |
| 9 | Provider Schema sent | Verify no schema sending; reject if found |
| 10 | STATIC_ALLOWLIST modified | Verify empty; reject if populated |
| 11 | Real secret leaked | Content search; reject if found |
| 12 | Controlled Execution implemented | Verify no implementation code; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-10 Failed."**

---

## 26. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Scope doc missing future route definition | Verify Section 5 completeness |
| 2 | Scope doc missing route governance delta | Verify Section 6 completeness |
| 3 | Scope doc missing Tool write vs Tool execution classification | Verify Section 7 completeness |
| 4 | Scope doc missing request schema draft | Verify Section 8 completeness |
| 5 | Scope doc missing response schema draft | Verify Section 9 completeness |
| 6 | Scope doc missing decision enum draft | Verify Section 10 completeness |
| 7 | Scope doc missing gate status model | Verify Section 11 completeness |
| 8 | Scope doc missing audit status model | Verify Section 12 completeness |
| 9 | Scope doc missing result preview model | Verify Section 13 completeness |
| 10 | Scope doc missing error code draft | Verify Section 14 completeness |
| 11 | Scope doc missing blocked-by-default contract | Verify Section 15 completeness |
| 12 | Scope doc missing dry-run preflight contract | Verify Section 16 completeness |
| 13 | Scope doc missing confirmation contract | Verify Section 17 completeness |
| 14 | Scope doc missing future OpenAPI file strategy | Verify Section 18 completeness |
| 15 | Scope doc missing future runtime file strategy | Verify Section 19 completeness |
| 16 | Scope doc missing future test matrix | Verify Section 21 completeness |
| 17 | Scope doc falsely claims execute route added | Content review |
| 18 | Scope doc falsely claims OpenAPI modified | Content review |
| 19 | Scope doc falsely claims execution implemented | Content review |
| 20 | Route governance failure | Run tests; verify counts |
| 21 | OpenAPI paths not 32 | Verify count |
| 22 | Runtime routes not 32 | Verify count |
| 23 | Tool GET not 4 | Verify count |
| 24 | Tool write not 0 | Verify count |
| 25 | Tool dry-run not 1 | Verify count |
| 26 | Tool execution not 0 | Verify count |
| 27 | memory-check failure | Run memory-check |
| 28 | dev-check failure | Run dev-check |
| 29 | compileall failure | Run compileall |
| 30 | Worktree contains out-of-scope files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 27. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Execute route not yet implemented | Expected — scope freeze only |
| 2 | Execution OpenAPI not yet implemented | Deferred to implementation phase |
| 3 | Execution UI not yet implemented | Deferred to future phase |
| 4 | Controlled Execution not yet implemented | Expected — scope freeze only |
| 5 | Audit read/search/list API not yet implemented | Deferred to future phase |
| 6 | Audit viewer UI not yet implemented | Deferred to future phase |
| 7 | Provider Schema exposure still not designed as implementation phase | Separate phase required |
| 8 | STATIC_ALLOWLIST still empty | Expected — requires separate phase |
| 9 | First executable tool not yet finally selected | Deferred to Phase 1G-04-13 |
| 10 | Browser smoke not re-run | Not required for docs-only change |

---

*Phase 1G-04-10 Execute Route Contract / OpenAPI Scope Freeze: route contract and OpenAPI scope definition only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no execution implementation, no tool handler call, no provider schema send, no allowlist change, no Controlled Execution started.*
