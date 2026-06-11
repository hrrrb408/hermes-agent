# Phase 1G-04-03: Dry-Run API Implementation Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-03 |
| Title | Tool Dry-Run API Implementation Scope Freeze |
| Status | Frozen (scope-only, no implementation) |
| Date | 2026-06-11 |
| Author | Dev Agent (Phase 1G-04-03 implementation scope freeze) |
| Dependencies | Phase 1G-04-01 completed, Phase 1G-04-02 completed |
| Branch | dev-huangruibang |
| Base commit | eca4e2b33464783e23ece310e042c759106dcd03 |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the implementation scope for the future Dry-Run API endpoint
2. Defines exactly which files may be modified when the API is implemented
3. Defines exactly which files must NOT be modified
4. Freezes the request validation, response contract, and error contract
5. Freezes the route governance impact and OpenAPI change plan
6. Freezes the test plan for the implementation phase
7. Freezes network safety and production safety requirements
8. Does **not** implement any API route, OpenAPI path, backend handler, or frontend component

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Overview

Phase 1G-04-03 freezes the implementation scope for the future Dry-Run API.

- This phase does **not** implement the API.
- This phase does **not** modify OpenAPI.
- This phase does **not** add runtime routes.
- This phase does **not** modify backend code.
- This phase does **not** modify frontend code.
- This phase does **not** invoke tools.
- This phase does **not** send Provider Schema.
- This phase does **not** write audit records.

---

## 2. Baseline

### 2.1 Git Baseline

| Field | Value |
|-------|-------|
| Branch | `dev-huangruibang` |
| Base commit | `eca4e2b33464783e23ece310e042c759106dcd03` |
| Commit message | `docs(webui): design dry-run read-only api` |

### 2.2 Route Governance Baseline

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 0 |
| Tool execution routes | 0 |

### 2.3 Safety Baseline

| Metric | Value |
|--------|-------|
| Provider Schema | Not sent |
| Tool Dispatch | 0 |
| Tool Execution | Disabled |
| Tool Audit | Absent |
| STATIC_ALLOWLIST | Empty (`frozenset()`) |
| Dry-Run HTTP API | Not implemented |
| Dry-Run UI | Not implemented |

### 2.4 Existing Dry-Run Assets

| Asset | File | Description |
|-------|------|-------------|
| Policy model | `hermes_cli/dev_web_tool_dry_run.py` | Pure dry-run policy engine: `dry_run_tool_policy()`, `sanitize_arguments_preview()`, `list_tool_dry_run_policies()`, `compute_dry_run_policy_summary()` |
| Policy tests | `tests/test_dev_web_tool_dry_run.py` | 425 unit tests covering models, risk tiers, redaction, no side effects, catalog, summary |
| API design | `docs/webui/phase-1g-04-02-dry-run-read-only-api-design.md` | Endpoint, DTOs, error codes, route governance, security boundary, future tests, future OpenAPI |

---

## 3. Implementation Target

### 3.1 Future Endpoint

```
POST /api/dev/v1/tools/dry-run
```

### 3.2 Purpose

Expose the existing pure dry-run policy model through a local-only API endpoint.

### 3.3 Operation Type

Non-mutating policy decision.

### 3.4 Explicit Non-Properties

- This endpoint does **not** execute tools.
- This endpoint does **not** dispatch tools.
- This endpoint does **not** send Provider Schema.
- This endpoint does **not** call providers.
- This endpoint does **not** write audit records.
- This endpoint does **not** mutate runtime state.

---

## 4. Allowed Files for Future Implementation

### 4.1 Required Backend Files

| File | Action | Scope |
|------|--------|-------|
| `hermes_cli/dev_web_api.py` | **Modify** | Add 1 POST route handler for `/api/dev/v1/tools/dry-run` |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** | Add 1 path entry + 6 schema definitions |

### 4.2 Required Tests

| File | Action | Scope |
|------|--------|-------|
| `tests/test_dev_web_tool_dry_run_api.py` | **New** | API-level tests (request validation, response contract, error codes, security, governance) |
| `tests/test_dev_check_webui.py` | **Modify** | Update route count expectations (31 → 32) |
| `tests/test_dev_web_0c06_closure.py` | **Modify** | Update route governance assertions (if needed) |

### 4.3 Required Docs

| File | Action | Scope |
|------|--------|-------|
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | **Modify** | Add Phase 1G-04-03 implementation completion record |
| `docs/webui/phase-1-implementation-plan.md` | **Modify** | Update Phase 1G-04-03 status |
| `docs/webui/phase-1g-04-03-dry-run-api-implementation-scope.md` | **Modify** | Update status to completed |

### 4.4 Optional Files (Minimal Changes Only)

| File | Action | Condition |
|------|--------|-----------|
| `tests/test_dev_web_tool_policy_api.py` | **Modify** | Only if route governance regression adaptation required |
| `tests/test_dev_web_tool_schema_preview_api.py` | **Modify** | Only if route governance regression adaptation required |

### 4.5 Files That Must NOT Be Modified in Implementation Phase

```
apps/hermes-dev-webui/src/          # Frontend source
apps/hermes-dev-webui/tests/         # Frontend tests
apps/hermes-dev-webui/e2e/           # E2E tests
apps/hermes-dev-webui/playwright/    # Browser smoke tests
agent/                               # Agent runtime
tools/                               # Tool handlers
toolsets.py                          # Toolset definitions
hermes_cli/main.py                   # CLI entry point
hermes_cli/dev_web_tool_dry_run.py   # Policy model (already frozen)
hermes_cli/dev_web_tool_policy.py    # Static policy module (already frozen)
hermes_cli/dev_web_tool_policy_service.py  # Policy query service (already frozen)
hermes_cli/dev_web_tool_schema_preview.py  # Schema preview model (already frozen)
hermes_cli/dev_web_tool_schema_preview_service.py  # Schema preview service (already frozen)
runtime files                        # Any runtime/service files
memory files                         # Memory system files
review files                         # Review queue files
.env                                 # Environment variables
.claude/                             # Claude session files
```

### 4.6 Frontend Restriction

No frontend work in Phase 1G-04-03 implementation. Frontend Dry-Run UI is deferred to Phase 1G-04-04.

---

## 5. Forbidden Files for Future Implementation

### 5.1 Absolutely Forbidden

```
apps/hermes-dev-webui/src/
apps/hermes-dev-webui/tests/
apps/hermes-dev-webui/e2e/
apps/hermes-dev-webui/playwright/
agent/
tools/
toolsets.py
runtime files
memory files
review files
.env
.claude/
```

### 5.2 Also Forbidden

```
hermes_cli/dev_web_tool_dry_run.py        # Policy model is frozen from Phase 1G-04-01
hermes_cli/dev_web_tool_policy.py          # Static policy is frozen from Phase 1G-01
hermes_cli/dev_web_tool_policy_service.py  # Policy query service is frozen from Phase 1G-02
hermes_cli/dev_web_tool_schema_preview.py  # Schema preview model is frozen from Phase 1G-03
hermes_cli/dev_web_tool_schema_preview_service.py  # Schema preview service is frozen from Phase 1G-03
hermes_cli/main.py                         # CLI entry — no dev-check count change needed
```

---

## 6. Request Validation Freeze

### 6.1 Request Body

Request body must be a JSON object.

### 6.2 Field Specifications

#### `canonicalName`

| Property | Value |
|----------|-------|
| Required | Yes |
| Type | string |
| Constraints | Non-empty after trim; max length 256 characters |
| Invalid type | 400 `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` |
| Empty string | 400 `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` |
| Exceeds max length | 400 `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` |

#### `argumentsPreview`

| Property | Value |
|----------|-------|
| Required | No (optional) |
| Type | JSON object (`Mapping`) or `null` |
| Constraints | Must be object if present |
| Non-object values (string, number, bool, array) | 400 `TOOL_DRY_RUN_INVALID_ARGUMENTS` |
| `null` | Treated as absent — success with empty preview |
| Purpose | Passed only as preview into dry-run policy model |
| Safety | Must **never** be executed or dispatched |

#### `sourceContext`

| Property | Value |
|----------|-------|
| Required | No (optional) |
| Type | string or null |
| Max length | 512 characters |
| Invalid type | 400 `TOOL_DRY_RUN_INVALID_REQUEST` |

#### `uiOrigin`

| Property | Value |
|----------|-------|
| Required | No (optional) |
| Type | string or null |
| Max length | 256 characters |
| Invalid type | 400 `TOOL_DRY_RUN_INVALID_REQUEST` |

#### `requestId`

| Property | Value |
|----------|-------|
| Required | No (optional) |
| Type | string or null |
| Max length | 128 characters |
| Invalid type | 400 `TOOL_DRY_RUN_INVALID_REQUEST` |
| Not durable | Not stored, not an audit ID |
| Purpose | Client-side request correlation only |

### 6.3 Body Size Limits

- Request body max: 64 KB
- Nested depth: max 4 (inherited from `MAX_ARGUMENT_DEPTH`)
- Field count: max 100 (inherited from `MAX_ARGUMENT_FIELDS`)
- String length: max 160 chars (inherited from `MAX_ARGUMENT_STRING_CHARS`)
- List items: max 20 (inherited from `MAX_ARGUMENT_LIST_ITEMS`)

---

## 7. Response Contract Freeze

### 7.1 Success Response Structure

```json
{
  "ok": true,
  "data": {
    "canonicalName": "string",
    "exists": true,
    "riskTier": "R0",
    "decision": "would_allow",
    "reasonCodes": [],
    "policyNotes": [],
    "redactedArgumentsPreview": {},
    "forbiddenFields": [],
    "missingRequiredFields": [],
    "executionAllowed": false,
    "dispatchAllowed": false,
    "providerSchemaAllowed": false,
    "auditWritten": false
  },
  "error": null
}
```

### 7.2 Error Response Structure

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "TOOL_DRY_RUN_INVALID_REQUEST",
    "message": "Human-readable error description",
    "details": {}
  }
}
```

### 7.3 Invariant Guarantees

The following fields are **hard-coded invariants** that must NEVER deviate:

| Field | Value | Must Not Change Until |
|-------|-------|---------------------|
| `executionAllowed` | `false` | Controlled Execution phase |
| `dispatchAllowed` | `false` | Controlled Execution phase |
| `providerSchemaAllowed` | `false` | Provider Schema Sending phase |
| `auditWritten` | `false` | Audit Implementation phase |

### 7.4 Decision Values

| Decision | Meaning |
|----------|---------|
| `would_allow` | Tool would be allowed for dry-run simulation (R0/R1) |
| `would_block` | Tool would be blocked (denylist, R4, R5, unknown) |
| `would_redact` | Tool arguments would be redacted (R3 with sensitive args) |
| `requires_review` | Tool requires additional review (R2, R3 without sensitive args) |

---

## 8. Error Contract Freeze

### 8.1 Error Code Registry

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TOOL_DRY_RUN_INVALID_REQUEST` | 400 | Request body missing, malformed, or non-object |
| `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` | 400 | `canonicalName` missing, empty, wrong type, or exceeds length |
| `TOOL_DRY_RUN_INVALID_ARGUMENTS` | 400 | `argumentsPreview` is present but not a JSON object |
| `TOOL_DRY_RUN_TOOL_NOT_FOUND` | N/A | Reserved — not used as HTTP error in initial implementation |
| `TOOL_DRY_RUN_POLICY_UNAVAILABLE` | 503 | Policy inventory cannot be loaded |
| `TOOL_DRY_RUN_INTERNAL_ERROR` | 500 | Unexpected internal error |

### 8.2 `TOOL_DRY_RUN_TOOL_NOT_FOUND` — Reserved

This error code is **reserved but not used as an HTTP error** in the initial implementation. Unknown tools return HTTP 200 with `exists=false` and `decision=would_block`.

Rationale:
- Dry-run is a policy decision service — it should safely describe blocked status.
- Returning 404 would leak inventory information.
- HTTP 200 with `exists=false` is consistent with the Phase 1G-04-01 policy model.

### 8.3 Unknown Tool Behavior — Frozen

| Property | Value |
|----------|-------|
| HTTP Status | 200 |
| `data.exists` | `false` |
| `data.decision` | `would_block` |
| `data.reasonCodes` | Includes `WOULD_BLOCK_UNKNOWN_TOOL` |
| `data.riskTier` | `null` |

---

## 9. Route Governance Freeze

### 9.1 Current Counts

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 0 |
| Tool execution routes | 0 |

### 9.2 Future Counts (After Implementation)

| Metric | Change | New Value |
|--------|--------|-----------|
| OpenAPI paths | +1 | 32 |
| Runtime routes | +1 | 32 |
| Tool GET routes | no change | 4 |
| Tool write routes | no change | 0 |
| Tool dry-run routes | +1 | 1 |
| Tool execution routes | no change | 0 |

### 9.3 Classification Rules

1. **Dry-Run POST must NOT be counted as Tool write.** The POST is non-mutating despite using POST method.
2. **Dry-Run POST must NOT be counted as Tool execution.** Dry-Run is a policy decision endpoint.
3. **Dry-Run must have a separate governance bucket.** Route governance tests must count dry-run routes independently.
4. **Tool write routes must remain 0** after Dry-Run API implementation.
5. **Tool execution routes must remain 0** after Dry-Run API implementation.

---

## 10. OpenAPI Freeze

### 10.1 Future Additions

| Item | Name | Description |
|------|------|-------------|
| Path | `POST /api/dev/v1/tools/dry-run` | Dry-run policy decision endpoint |
| Schema | `ToolDryRunRequest` | Request body schema |
| Schema | `ToolDryRunResponse` | Top-level response envelope |
| Schema | `ToolDryRunData` | Success data payload |
| Schema | `ToolDryRunDecision` | Decision enum values |
| Schema | `ToolDryRunErrorCode` | Error code enum values |
| Schema | `ToolDryRunPolicySummary` | Aggregate summary (for future catalog endpoint) |

### 10.2 Phase 1G-04-03 Scope Freeze Declaration

**No OpenAPI file is modified in Phase 1G-04-03 scope freeze.** The schemas and path above are frozen as the implementation target for the next phase.

---

## 11. Backend Implementation Freeze

### 11.1 Implementation Requirements

The future implementation must:

1. Use existing `dry_run_tool_policy()` from `dev_web_tool_dry_run.py` — the pure policy engine
2. Use existing `sanitize_arguments_preview()` from `dev_web_tool_dry_run.py` — argument sanitizer
3. Never call any tool handler
4. Never call any provider API
5. Never dispatch any tool
6. Never write any audit record
7. Never mutate `STATIC_ALLOWLIST`
8. Never mutate runtime state
9. Never read `~/.hermes`
10. Never read production `state.db`
11. Return safe JSON only (all output via `to_safe_dict()`)

### 11.2 Implementation Pattern

The route handler should:

1. Parse and validate the JSON request body
2. Validate `canonicalName` (required, non-empty string, max 256 chars)
3. Validate `argumentsPreview` (optional, must be object if present)
4. Call `dry_run_tool_policy(canonical_name, arguments_preview)` — pure function
5. Wrap the result in the standard response envelope
6. Return JSON response

### 11.3 Error Handling Pattern

1. Missing or non-object body → 400 `TOOL_DRY_RUN_INVALID_REQUEST`
2. Invalid `canonicalName` → 400 `TOOL_DRY_RUN_INVALID_CANONICAL_NAME`
3. Invalid `argumentsPreview` → 400 `TOOL_DRY_RUN_INVALID_ARGUMENTS`
4. Unexpected exception → 500 `TOOL_DRY_RUN_INTERNAL_ERROR`
5. Policy inventory unavailable → 503 `TOOL_DRY_RUN_POLICY_UNAVAILABLE` (defensive, unlikely)

---

## 12. Test Plan Freeze

### 12.1 New Test File

`tests/test_dev_web_tool_dry_run_api.py`

### 12.2 Decision Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Valid R0 request | Returns 200, `would_allow`, `executionAllowed=false` |
| 2 | Valid R1 request | Returns 200, `would_allow`, `executionAllowed=false` |
| 3 | Valid R2 request | Returns 200, `requires_review` |
| 4 | Valid R3 request (no sensitive args) | Returns 200, `requires_review` |
| 5 | Valid R3 request (sensitive args) | Returns 200, `would_redact`, redacted values |
| 6 | Valid R4 request | Returns 200, `would_block` |
| 7 | Valid R5 request | Returns 200, `would_block` |
| 8 | Denylisted tool request | Returns 200, `would_block` |
| 9 | Unknown tool request | Returns 200, `exists=false`, `would_block` |

### 12.3 Validation Tests

| # | Test | Expected |
|---|------|----------|
| 10 | Missing request body | Returns 400 |
| 11 | Non-object request body | Returns 400 |
| 12 | Missing `canonicalName` | Returns 400 |
| 13 | Empty `canonicalName` | Returns 400 |
| 14 | Non-string `canonicalName` | Returns 400 |
| 15 | Non-object `argumentsPreview` (string) | Returns 400 |
| 16 | Non-object `argumentsPreview` (array) | Returns 400 |
| 17 | Non-object `argumentsPreview` (number) | Returns 400 |
| 18 | Invalid `sourceContext` type | Returns 400 |
| 19 | Invalid `uiOrigin` type | Returns 400 |
| 20 | Invalid `requestId` type | Returns 400 |

### 12.4 Security Tests

| # | Test | Expected |
|---|------|----------|
| 21 | Request with secret arguments | Response redacts secrets, no raw secrets returned |
| 22 | Provider schema not sent | Verified — no provider call |
| 23 | Tool handler not called | Verified — no handler invocation |
| 24 | Dispatch not called | Verified — no dispatch |
| 25 | Audit not written | Verified — no audit storage |
| 26 | STATIC_ALLOWLIST remains empty | Verified after request |

### 12.5 Governance Tests

| # | Test | Expected |
|---|------|----------|
| 27 | Route governance counts updated | OpenAPI=32, Runtime=32, Dry-Run=1 |
| 28 | Tool write routes remains 0 | Confirmed |
| 29 | Tool execution routes remains 0 | Confirmed |

### 12.6 Existing Regression

| Test File | Expected |
|-----------|----------|
| `tests/test_dev_web_tool_dry_run.py` | 425 passed, 0 failed (unchanged) |
| Route governance tests | Updated intentionally for new route count |
| OpenAPI path count tests | Updated intentionally in implementation phase only |

---

## 13. Network Safety Freeze

### 13.1 Network Safety Requirements

The future implementation must prove:

1. **No external network calls.** The endpoint makes zero outbound HTTP/WebSocket/DNS requests.
2. **No provider requests.** No LLM provider API is called.
3. **No `/execute` route.** No tool execution endpoint exists.
4. **No `/dispatch` route.** No tool dispatch endpoint exists.
5. **No `/audit` write route.** No audit write endpoint exists.
6. **No runtime mutation.** No runtime state is modified.
7. **Only local dry-run API call.** The endpoint operates entirely within the local process using static policy data.

### 13.2 Verification Method

Network safety must be verified by:

1. Inspecting the route handler code — no network imports, no HTTP client calls
2. Inspecting the dependency chain — only `dev_web_tool_dry_run.py` (stdlib-only module)
3. Running security tests that assert no provider/handler/dispatch/audit calls
4. Checking `STATIC_ALLOWLIST` before and after the request (must remain empty)

---

## 14. Acceptance Criteria

### 14.1 Phase 1G-04-03 Scope Freeze Acceptance

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only changes | Must pass |
| 2 | No code changes | Must pass |
| 3 | No OpenAPI changes | Must pass |
| 4 | No API route changes | Must pass |
| 5 | No runtime route changes | Must pass |
| 6 | No frontend changes | Must pass |
| 7 | No provider schema sending | Must pass |
| 8 | No dispatch | Must pass |
| 9 | No execution | Must pass |
| 10 | No audit write | Must pass |
| 11 | `STATIC_ALLOWLIST` empty | Must pass |
| 12 | Route counts unchanged (31/31/4/0) | Must pass |
| 13 | Production Gateway PID 1717 unaffected | Must pass |
| 14 | Local docs-only commit created | Must pass |
| 15 | No push | Must pass |
| 16 | Phase 1G-04-03 implementation not started | Must pass |
| 17 | Phase 1G-04-04 not started | Must pass |
| 18 | Controlled Execution not started | Must pass |

### 14.2 Future Implementation Acceptance (For Next Phase)

| # | Criterion |
|---|-----------|
| 1 | 1 POST route added (`/api/dev/v1/tools/dry-run`) |
| 2 | OpenAPI path count: 31 → 32 |
| 3 | Runtime route count: 31 → 32 |
| 4 | Tool dry-run routes: 0 → 1 |
| 5 | Tool write routes remains 0 |
| 6 | Tool execution routes remains 0 |
| 7 | `executionAllowed` always `false` in response |
| 8 | `dispatchAllowed` always `false` in response |
| 9 | `providerSchemaAllowed` always `false` in response |
| 10 | `auditWritten` always `false` in response |
| 11 | Unknown tool returns 200 with `exists=false` |
| 12 | All validation tests pass |
| 13 | All security tests pass |
| 14 | `STATIC_ALLOWLIST` remains empty |
| 15 | No provider schema sent |
| 16 | No tool handler called |
| 17 | No dispatch occurred |
| 18 | No audit written |
| 19 | Production Gateway unaffected |
| 20 | All quality gates pass |

---

*Phase 1G-04-03 Dry-Run API Implementation Scope Freeze: scope-only, docs-only, no API implementation, no OpenAPI modification, no runtime route change, no frontend implementation, no provider schema sending, no tool dispatch, no tool execution, no tool audit, no allowlist change.*
