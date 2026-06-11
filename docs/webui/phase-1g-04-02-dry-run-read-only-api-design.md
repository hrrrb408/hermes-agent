# Phase 1G-04-02: Dry-Run Read-Only API Design

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-02 |
| Title | Tool Dry-Run Read-Only API Design Scope Freeze |
| Status | Frozen (design-only, no implementation) |
| Date | 2026-06-11 |
| Author | Dev Agent (Phase 1G-04-02 API design freeze) |
| Dependencies | Phase 1G-04-01 completed (policy model) |
| Branch | dev-huangruibang |
| Base commit | 821716bf5e95678a666a1b77ab5812b3ad81b8cc |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Designs the future Tool Dry-Run Read-Only API endpoint, request/response DTOs, and error codes
2. Defines route governance impact expectations for the future implementation phase
3. Defines security boundaries, input sanitization requirements, and network safety expectations
4. Defines future test scope and future OpenAPI schema structure
5. Does **not** implement any API route, OpenAPI path, backend handler, or frontend component

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Overview

Phase 1G-04-02 designs the future Tool Dry-Run Read-Only API.

- This phase does **not** implement the API.
- This phase does **not** modify OpenAPI.
- This phase does **not** add runtime routes.
- This phase does **not** invoke tools.
- This phase does **not** send Provider Schema.
- This phase does **not** write audit records.

---

## 2. Relationship to Phase 1G-04-01

Phase 1G-04-01 provided the pure no-side-effect dry-run policy model:

- `ToolDryRunRequest` — immutable request DTO
- `ToolDryRunResult` — immutable result DTO with frozen guarantees
- `ToolDryRunPolicySummary` — aggregate summary across all tools
- `dry_run_tool_policy()` — core policy engine (pure function)
- `list_tool_dry_run_policies()` — catalog of all 71 tools
- `compute_dry_run_policy_summary()` — aggregate counts
- `sanitize_arguments_preview()` — argument sanitizer with secret redaction

Phase 1G-04-02 defines how a future API could expose that model safely.

The API must **not** weaken the guarantees of the policy model:

| Guarantee | Value | Must Not Change |
|-----------|-------|----------------|
| `execution_allowed` | `false` | Yes |
| `dispatch_allowed` | `false` | Yes |
| `provider_schema_allowed` | `false` | Yes |
| `audit_written` | `false` | Yes |

---

## 3. Proposed Endpoint

### 3.1 Recommended API

```
POST /api/dev/v1/tools/dry-run
```

### 3.2 Rationale

- Dry-run request includes proposed arguments, so POST is appropriate even though the operation is non-mutating.
- The route is a dry-run decision endpoint, not a write/execution endpoint.
- It must be explicitly tracked as a **tool dry-run route**, not a tool execution route.

### 3.3 Explicit Non-Properties

- This POST does **not** execute a tool.
- This POST does **not** mutate runtime state.
- This POST does **not** send Provider Schema.
- This POST does **not** call any Tool Handler.
- This POST does **not** write audit in the initial API implementation.

### 3.4 GET Variant Considered and Rejected as Primary

A GET variant was considered:

```
GET /api/dev/v1/tools/dry-run/{canonicalName}
```

Limitations:

- GET cannot safely carry structured proposed arguments (object body).
- GET variant may only support no-argument policy lookup.
- No-argument policy lookup can be achieved via the existing `GET /api/dev/v1/tools/policy` endpoint.

**Decision:** The GET variant is rejected as the primary endpoint. The `POST /api/dev/v1/tools/dry-run` is the sole recommended API.

---

## 4. Route Governance Impact

### 4.1 Current Baseline

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 0 |
| Tool execution routes | 0 |

### 4.2 Future Impact (When Implemented in Phase 1G-04-03)

| Metric | Change | New Value |
|--------|--------|-----------|
| OpenAPI paths | +1 | 32 |
| Runtime routes | +1 | 32 |
| Tool GET routes | no change | 4 |
| Tool write routes | no change | 0 |
| Tool dry-run routes | +1 | 1 |
| Tool execution routes | no change | 0 |

### 4.3 Classification Rules

1. **Do NOT classify Dry-Run as Tool Execution.** Dry-Run routes are a separate governance bucket.
2. **Do NOT classify Dry-Run as Tool Write.** The POST is non-mutating despite using POST method.
3. **Dry-Run must have a separate governance bucket** in route governance tests.
4. Existing governance tests must be updated in the implementation phase to count dry-run routes separately.
5. `Tool write routes` must remain 0 after dry-run API implementation.

---

## 5. Request DTO Design

### 5.1 Structure

```json
{
  "canonicalName": "string",
  "argumentsPreview": {},
  "sourceContext": "string | null",
  "uiOrigin": "string | null",
  "requestId": "string | null"
}
```

### 5.2 Field Specifications

#### `canonicalName`

- **Required**: yes
- **Type**: string
- **Constraints**:
  - Must not be empty
  - Must not exceed 256 characters
  - Must match the static canonical name format used in `TOOL_POLICY_INVENTORY`
  - Invalid format returns `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` error
- **Purpose**: Identifies the tool to evaluate

#### `argumentsPreview`

- **Required**: no (optional)
- **Type**: object (JSON object only)
- **Constraints**:
  - Must be a JSON object (`Mapping` type) if provided
  - Non-object values (string, number, array, boolean) return `TOOL_DRY_RUN_INVALID_ARGUMENTS` error
  - `null` is treated as absent (no arguments)
  - Must be sanitized before inclusion in response
  - Must never be executed or dispatched
- **Purpose**: Proposed arguments for the dry-run evaluation

#### `sourceContext`

- **Required**: no (optional)
- **Type**: string or null
- **Constraints**:
  - Max length: 512 characters
  - Used for policy notes only
  - **Not trusted** — must not influence security decisions
- **Purpose**: Describes the origin context (e.g., "workspace-panel", "tool-catalog")

#### `uiOrigin`

- **Required**: no (optional)
- **Type**: string or null
- **Constraints**:
  - Max length: 256 characters
  - Used for traceability only
  - **Not trusted** — must not influence security decisions
- **Purpose**: Identifies the UI component that initiated the request

#### `requestId`

- **Required**: no (optional)
- **Type**: string or null
- **Constraints**:
  - Max length: 128 characters
  - Client-generated correlation ID
  - **Not an audit ID** — not durable, not stored
  - Returned as-is in response for client correlation
- **Purpose**: Client-side request tracking

### 5.3 Input Safety Constraints

The following constraints must be enforced in the implementation phase:

1. **No raw secrets accepted intentionally.** If secrets appear in input, they must be redacted in response.
2. **Request body size must be capped** (recommended: 64 KB maximum).
3. **Nested depth must be capped** (inherited from `MAX_ARGUMENT_DEPTH = 4`).
4. **Field count must be capped** (inherited from `MAX_ARGUMENT_FIELDS = 100`).
5. **String length must be capped** (inherited from `MAX_ARGUMENT_STRING_CHARS = 160`).
6. **List items must be capped** (inherited from `MAX_ARGUMENT_LIST_ITEMS = 20`).

---

## 6. Response DTO Design

### 6.1 Success Response Structure

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

### 6.2 Field Specifications

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Always `true` for success |
| `data.canonicalName` | string | The requested tool canonical name |
| `data.exists` | boolean | Whether the tool exists in the policy inventory |
| `data.riskTier` | string or null | Risk tier (e.g., "R0") or null if unknown |
| `data.decision` | string | One of: `would_allow`, `would_block`, `would_redact`, `requires_review` |
| `data.reasonCodes` | string[] | Machine-readable reason codes |
| `data.policyNotes` | string[] | Human-readable policy notes |
| `data.redactedArgumentsPreview` | object | Sanitized arguments with secrets redacted |
| `data.forbiddenFields` | string[] | Field paths that were redacted |
| `data.missingRequiredFields` | string[] | Required fields not present (future: schema validation) |
| `data.executionAllowed` | boolean | **Must always be `false`** in initial Dry-Run API |
| `data.dispatchAllowed` | boolean | **Must always be `false`** |
| `data.providerSchemaAllowed` | boolean | **Must always be `false`** |
| `data.auditWritten` | boolean | **Must always be `false`** unless a separate audit phase is approved |
| `error` | null | Null for success responses |

### 6.3 Invariant Guarantees

The following fields are **hard-coded invariants** in the initial Dry-Run API:

| Field | Value | Must Not Change |
|-------|-------|----------------|
| `executionAllowed` | `false` | Until Controlled Execution phase |
| `dispatchAllowed` | `false` | Until Controlled Execution phase |
| `providerSchemaAllowed` | `false` | Until Provider Schema Sending phase |
| `auditWritten` | `false` | Until Audit Implementation phase |

### 6.4 Error Response Structure

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

---

## 7. Error Codes

### 7.1 Error Code Registry

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TOOL_DRY_RUN_INVALID_REQUEST` | 400 | Request body is missing, malformed, or contains invalid JSON |
| `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` | 400 | `canonicalName` is missing, empty, or exceeds length limit |
| `TOOL_DRY_RUN_INVALID_ARGUMENTS` | 400 | `argumentsPreview` is present but is not a JSON object |
| `TOOL_DRY_RUN_TOOL_NOT_FOUND` | N/A | Not used as error — unknown tools return HTTP 200 with `exists=false` |
| `TOOL_DRY_RUN_POLICY_UNAVAILABLE` | 503 | Policy inventory cannot be loaded (internal failure) |
| `TOOL_DRY_RUN_INTERNAL_ERROR` | 500 | Unexpected internal error during dry-run evaluation |

### 7.2 Error Categories

| Category | HTTP Status Range | Codes |
|----------|-------------------|-------|
| HTTP validation error | 400 | `INVALID_REQUEST`, `INVALID_CANONICAL_NAME`, `INVALID_ARGUMENTS` |
| Known tool policy block | 200 (success with decision) | N/A — returned as `would_block` decision |
| Unknown tool result | 200 (success with decision) | N/A — returned as `would_block` with `exists=false` |
| Internal failure | 500–503 | `POLICY_UNAVAILABLE`, `INTERNAL_ERROR` |

### 7.3 Unknown Tool Behavior — Frozen Decision

**Decision:** Unknown tool returns HTTP 200 with `exists=false` and `decision=would_block`.

**Rationale:**

- Dry-run is a **policy decision service** — it should safely describe blocked status without leaking stack behavior.
- Returning 404 for unknown tools would leak inventory information (tools that exist vs. don't exist).
- Returning 200 with `exists=false` is consistent with the policy model's behavior (Phase 1G-04-01).
- The response includes `WOULD_BLOCK_UNKNOWN_TOOL` in reason codes.

### 7.4 Error Response Semantics

| Scenario | HTTP Status | Response |
|----------|-------------|----------|
| Missing request body | 400 | `TOOL_DRY_RUN_INVALID_REQUEST` |
| Empty `canonicalName` | 400 | `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` |
| `canonicalName` exceeds 256 chars | 400 | `TOOL_DRY_RUN_INVALID_CANONICAL_NAME` |
| `argumentsPreview` is a string | 400 | `TOOL_DRY_RUN_INVALID_ARGUMENTS` |
| `argumentsPreview` is an array | 400 | `TOOL_DRY_RUN_INVALID_ARGUMENTS` |
| `argumentsPreview` is a number | 400 | `TOOL_DRY_RUN_INVALID_ARGUMENTS` |
| `argumentsPreview` is `null` | 200 | Treated as absent — success with empty preview |
| Unknown tool | 200 | `exists=false`, `decision=would_block`, `WOULD_BLOCK_UNKNOWN_TOOL` |
| Denylisted tool | 200 | `exists=true`, `decision=would_block`, `WOULD_BLOCK_DENYLISTED` |
| Valid R0 tool | 200 | `exists=true`, `decision=would_allow` |
| Valid R1 tool | 200 | `exists=true`, `decision=would_allow` |
| Valid R2 tool | 200 | `exists=true`, `decision=requires_review` |
| Valid R3 tool (no sensitive args) | 200 | `exists=true`, `decision=requires_review` |
| Valid R3 tool (sensitive args) | 200 | `exists=true`, `decision=would_redact` |
| Valid R4 tool | 200 | `exists=true`, `decision=would_block` |
| Valid R5 tool | 200 | `exists=true`, `decision=would_block` |
| Policy inventory failure | 503 | `TOOL_DRY_RUN_POLICY_UNAVAILABLE` |
| Unexpected error | 500 | `TOOL_DRY_RUN_INTERNAL_ERROR` |

---

## 8. Security Boundary

### 8.1 The Dry-Run API Must Never

| # | Prohibition |
|---|-------------|
| 1 | Call tool handlers |
| 2 | Dispatch tools |
| 3 | Execute tools |
| 4 | Send Provider Schema |
| 5 | Call provider APIs |
| 6 | Read provider keys |
| 7 | Write audit records in initial implementation |
| 8 | Write files |
| 9 | Read production `state.db` |
| 10 | Read `~/.hermes` |
| 11 | Mutate runtime state |
| 12 | Modify `STATIC_ALLOWLIST` |
| 13 | Return raw secrets |
| 14 | Return raw unredacted arguments |

### 8.2 Network Safety Expectations

1. The Dry-Run API endpoint must not make any outbound network requests.
2. The Dry-Run API must not connect to any external service.
3. The Dry-Run API must not resolve DNS for any domain.
4. The Dry-Run API must not send data to any LLM provider.
5. The Dry-Run API operates entirely within the local process using static policy data.

### 8.3 Allowed Request Semantics

The Dry-Run API accepts a tool name and proposed arguments. It returns a policy decision. It does **not**:

- Execute the tool
- Validate against the real tool handler
- Confirm the tool is currently available in the runtime
- Check runtime environment state

### 8.4 Forbidden Request Semantics

The Dry-Run API must reject or safely handle:

- Requests with executable code in arguments
- Requests with file paths in arguments (paths are redacted, not resolved)
- Requests with URLs in arguments (URLs are preserved as-is, not fetched)
- Requests with environment variable references (not expanded)
- Requests with template expressions (not evaluated)
- Requests exceeding body size limits
- Requests with excessive nesting depth
- Requests with excessive field count

---

## 9. Input Sanitization

### 9.1 Sanitization Rules

The future API must reuse the Phase 1G-04-01 sanitizer semantics from `dev_web_tool_dry_run.py`:

| Rule | Implementation |
|------|---------------|
| Secret-like keys redacted | `_is_secret_key()` + `_FORBIDDEN_ARG_FIELD_NAMES` |
| Secret-like values redacted | `_is_secret_value()` + `_SECRET_VALUE_PATTERNS` |
| Large strings truncated | `MAX_ARGUMENT_STRING_CHARS = 160` |
| Deep objects truncated | `MAX_ARGUMENT_DEPTH = 4` |
| Large lists truncated | `MAX_ARGUMENT_LIST_ITEMS = 20` |
| Field count limited | `MAX_ARGUMENT_FIELDS = 100` |
| Forbidden fields tracked | Returned in `forbiddenFields` response |
| Non-mapping arguments rejected | `INVALID_ARGUMENT_SHAPE` reason code |
| JSON-safe response only | `to_safe_dict()` serialization |

### 9.2 Response Sanitization

All response data must be JSON-serializable. The following must not appear in responses:

- Raw secret values (replaced with `[REDACTED]`)
- Callable objects or function references
- File system paths (unless redacted)
- Internal Python objects

---

## 10. Future API Tests

### 10.1 Test Scope for Implementation Phase (1G-04-03)

The following tests must be implemented when the API route is added:

#### Decision Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Valid R0 tool request | Returns `would_allow`, `executionAllowed=false` |
| 2 | Valid R1 tool request | Returns `would_allow`, `executionAllowed=false` |
| 3 | Valid R2 tool request | Returns `requires_review` |
| 4 | Valid R3 tool request (no sensitive args) | Returns `requires_review` |
| 5 | Valid R3 tool request (sensitive args) | Returns `would_redact` |
| 6 | Valid R4 tool request | Returns `would_block` |
| 7 | Valid R5 tool request | Returns `would_block` |
| 8 | Denylisted tool request | Returns `would_block` |
| 9 | Unknown tool request | Returns `exists=false`, `would_block` |

#### Validation Tests

| # | Test | Expected |
|---|------|----------|
| 10 | Invalid request (empty body) | Returns 400 |
| 11 | Non-object `argumentsPreview` | Returns 400 |
| 12 | Missing `canonicalName` | Returns 400 |
| 13 | Empty `canonicalName` | Returns 400 |
| 14 | Oversized `canonicalName` | Returns 400 |

#### Security Tests

| # | Test | Expected |
|---|------|----------|
| 15 | Request with secret arguments | Response redacts secrets |
| 16 | No Provider Schema sent | Verified (no provider call) |
| 17 | No Tool Handler called | Verified (no handler call) |
| 18 | No Dispatch occurred | Verified (no dispatch) |
| 19 | No Audit written | Verified (no audit storage) |

#### Governance Tests

| # | Test | Expected |
|---|------|----------|
| 20 | Route count increments only in dry-run bucket | Dry-Run: +1, Write: 0 |
| 21 | Tool write routes remains 0 | Confirmed |
| 22 | Tool execution routes remains 0 | Confirmed |
| 23 | OpenAPI paths increases by 1 | 31 → 32 |

---

## 11. Future OpenAPI Design

### 11.1 Schema Name Recommendations

The following schema names should be used when the API is added to OpenAPI in Phase 1G-04-03:

| Schema Name | Purpose |
|-------------|---------|
| `ToolDryRunRequest` | Request body schema |
| `ToolDryRunResponse` | Top-level response envelope |
| `ToolDryRunData` | Success data payload |
| `ToolDryRunDecision` | Decision enum values |
| `ToolDryRunErrorCode` | Error code enum values |
| `ToolDryRunPolicySummary` | Aggregate summary (for future catalog endpoint) |

### 11.2 OpenAPI Path Entry (Future)

```yaml
/api/dev/v1/tools/dry-run:
  post:
    summary: Evaluate dry-run policy for a proposed tool call
    description: >
      Returns a policy decision (would_allow, would_block, would_redact,
      requires_review) without executing the tool. No tool handler is called,
      no provider schema is sent, and no audit record is written.
    operationId: toolDryRun
    tags:
      - Tools
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ToolDryRunRequest'
    responses:
      '200':
        description: Dry-run policy decision
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolDryRunResponse'
      '400':
        description: Invalid request
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolDryRunResponse'
      '503':
        description: Policy unavailable
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolDryRunResponse'
      '500':
        description: Internal error
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolDryRunResponse'
```

### 11.3 Phase 1G-04-02 Declaration

**No OpenAPI file is changed in Phase 1G-04-02.** The schema and path above are design-only recommendations for the future implementation phase.

---

## 12. Future UI Design Notes

### 12.1 Phase 1G-04-02 Declaration

**No UI is implemented in Phase 1G-04-02.**

### 12.2 Future UI Requirements

When the Dry-Run UI is designed in a future sub-phase (1G-04-04):

1. **Future UI must display "No tool was executed."** prominently in the results panel.
2. **Future UI must not use Execute terminology.** Buttons and labels must say "Simulate", "Preview", or "Dry-Run" — never "Run" or "Execute".
3. **Future UI must not show provider schema sending.** No indication that schemas are being sent to any provider.
4. **Future UI must not expose raw arguments.** All arguments must be shown after sanitization/redaction.
5. **Future UI must display redaction clearly.** Redacted fields must be visually marked (e.g., `[REDACTED]` badge).
6. **Future UI must separate Dry-Run results from tool schema preview.** These are distinct panels with distinct purposes.
7. **Future UI must show the decision matrix context:** risk tier, decision, reason codes, and policy notes.

---

## 13. Audit Behavior

### 13.1 Phase 1G-04-02 Declaration

**This phase does not implement audit.** The initial Dry-Run API (when implemented in Phase 1G-04-03) will not write audit records.

### 13.2 Future Audit Design

Audit storage for Dry-Run requests is deferred to Phase 1G-04-06 (Audit Design). When implemented:

1. Dry-Run audit must not contain raw secrets or unredacted arguments.
2. Dry-Run audit must be separate from Execution audit.
3. Dry-Run audit must not be enabled by default in the initial API.
4. Audit must require explicit configuration to enable.

---

## 14. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only changes | ✅ |
| 2 | No code changes | ✅ |
| 3 | No OpenAPI changes | ✅ |
| 4 | No API route changes | ✅ |
| 5 | No runtime route changes | ✅ |
| 6 | No frontend changes | ✅ |
| 7 | No provider schema sending | ✅ |
| 8 | No dispatch | ✅ |
| 9 | No execution | ✅ |
| 10 | No audit write | ✅ |
| 11 | `STATIC_ALLOWLIST` empty | ✅ |
| 12 | Route counts unchanged | ✅ |
| 13 | Production Gateway PID 1717 unaffected | ✅ |
| 14 | Local docs-only commit created | ✅ |
| 15 | No push | ✅ |
| 16 | Phase 1G-04-03 not started | ✅ |
| 17 | Controlled Execution not started | ✅ |

---

*Phase 1G-04-02 Dry-Run Read-Only API Design: design-only, docs-only, no API implementation, no OpenAPI modification, no runtime route change, no frontend implementation, no provider schema sending, no tool dispatch, no tool execution, no tool audit, no allowlist change.*
