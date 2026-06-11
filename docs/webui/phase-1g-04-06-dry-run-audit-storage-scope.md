# Phase 1G-04-06: Dry-Run Audit Storage Scope / Design

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-06 |
| Title | Dry-Run Audit Storage Scope / Design Freeze |
| Status | Frozen (scope/design-only, no implementation) |
| Date | 2026-06-11 |
| Author | Dev Agent (Phase 1G-04-06 scope/design freeze) |
| Dependencies | Phase 1G-04-05 completed locally |
| Branch | dev-huangruibang |
| Base commit | 6b4de050e7c296e3189535c09abbdd5b753caa1e |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Defines the audit storage goal, non-goals, and scope boundaries
2. Designs the future audit event data model (not implemented)
3. Defines the sensitive data redaction / sanitization policy for audit events
4. Designs the future local dev-only storage location (not implemented)
5. Designs retention, rotation, and size limit policies
6. Defines failure modes and failure-mode safety guarantees
7. Freezes future allowed files and forbidden files for audit implementation
8. Defines the test plan for future audit implementation
9. Confirms route governance is unchanged
10. Does **not** implement any audit storage, audit API, audit UI, or runtime file

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-06 = **Dry-Run Audit Storage Scope / Design**

- This phase freezes the audit storage scope and design only.
- This phase does **not** implement audit storage.
- This phase does **not** write audit events.
- This phase does **not** modify the Dry-Run API.
- This phase does **not** modify OpenAPI.
- This phase does **not** add routes.
- This phase does **not** start Controlled Execution.

---

## 2. Audit Goal

The Dry-Run Audit Storage exists to:

1. Record local, non-mutating, already-redacted Dry-Run decision results.
2. Help future review of which tool dry-run requests were simulated in the WebUI.
3. Support future security regression analysis and debugging.
4. Build traceability before Controlled Execution begins.
5. Provide a historical record of policy decisions for post-hoc analysis.

**The audit storage does not represent permission to execute tools.** Recording a dry-run decision does not enable, authorize, or imply tool execution.

---

## 3. Non-Goals

The following are explicitly **not** part of audit storage:

1. No recording of real Tool Execution events
2. No recording of Tool Handler invocations
3. No recording of Provider Schema sending events
4. No recording of Provider API responses
5. No recording of real sensitive parameters (raw arguments)
6. No recording of complete raw arguments
7. No recording of raw prompt text
8. No recording of raw session transcript
9. No recording of production state
10. No implementation of audit viewer UI
11. No implementation of audit search API
12. No implementation of audit export functionality
13. No implementation of Controlled Execution
14. No modification of STATIC_ALLOWLIST
15. No enabling of STATIC_ALLOWLIST
16. No addition of Tool write routes
17. No addition of Tool execution routes

---

## 4. Audit Event Model (Future Design, Not Implemented)

### 4.1 Event Schema

The following fields define the future audit event structure:

| Field | Type | Description |
|-------|------|-------------|
| `eventId` | string | Unique identifier (UUID4) |
| `eventType` | string | Event type: `TOOL_DRY_RUN_DECISION` |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `schemaVersion` | string | Schema version: `1` |
| `phase` | string | Phase identifier: `1G-04` |
| `requestId` | string or null | Client-provided request correlation ID |
| `canonicalName` | string | Tool canonical name |
| `toolExists` | boolean | Whether the tool exists in inventory |
| `riskTier` | string or null | Risk tier (R0–R5) or null if unknown |
| `decision` | string | Dry-run decision enum value |
| `reasonCodes` | list[string] | Machine-readable reason codes |
| `policyNotes` | list[string] | Human-readable policy notes |
| `forbiddenFields` | list[string] | Fields that were redacted |
| `missingRequiredFields` | list[string] | Required fields not present |
| `redactionApplied` | boolean | Whether argument redaction was applied |
| `redactionReasonCodes` | list[string] | Reason codes for any redaction |
| `redactedArgumentsPreview` | object | Sanitized arguments preview (already redacted) |
| `sourceContext` | string or null | Source context from request |
| `uiOrigin` | string or null | UI origin from request |
| `executionAllowed` | boolean | **Must always be `false`** |
| `dispatchAllowed` | boolean | **Must always be `false`** |
| `providerSchemaAllowed` | boolean | **Must always be `false`** |
| `auditWritten` | boolean | Whether audit write succeeded (for this event) |
| `staticAllowlistSize` | integer | Size of STATIC_ALLOWLIST at event time (for tracking) |
| `candidateAllowlistMatched` | boolean | Whether tool was on candidate allowlist |
| `denylistMatched` | boolean | Whether tool was on denylist |
| `durationMs` | float | Dry-run evaluation duration in milliseconds |
| `resultStatus` | string | `success` or `error` |
| `errorCode` | string or null | Error code if result was error |
| `errorClass` | string or null | Error class if result was error |

### 4.2 Invariant Guarantees for Audit Events

Every audit event must satisfy:

| Field | Value | Must Not Change Until |
|-------|-------|---------------------|
| `executionAllowed` | `false` | Controlled Execution phase |
| `dispatchAllowed` | `false` | Controlled Execution phase |
| `providerSchemaAllowed` | `false` | Provider Schema Sending phase |

### 4.3 auditWritten Semantics

- In the current API (Phase 1G-04-04), `auditWritten` is always `false` because no audit storage exists.
- In the future implementation, `auditWritten` in the API response may become `true` only after a successful internal audit write.
- `auditWritten = true` means "the audit event was recorded locally" — it does **not** mean "the tool was executed" or "the tool was dispatched."
- `auditWritten` in an audit event refers to whether that specific audit event was successfully written, not to any tool execution.

### 4.4 Size Constraints for Audit Events

- Each serialized audit event must not exceed 32 KiB.
- The `redactedArgumentsPreview` field is already sanitized by the existing `sanitize_arguments_preview()` function (max depth 4, max string 160 chars, max list 20 items, max fields 100).
- If an event exceeds 32 KiB after serialization, it must be truncated or the write must fail gracefully.

---

## 5. Sensitive Data Policy

### 5.1 Absolute Prohibitions

Audit storage must **never** store:

1. Raw secrets, API keys, tokens, or credentials
2. Secret-like values matching known secret patterns
3. Raw request body (only `redactedArgumentsPreview` is stored)
4. Raw response body (unless already a safe dict from `to_safe_dict()`)
5. Stack traces
6. Provider keys (read or stored)
7. Authorization headers
8. Full unredacted argument payloads
9. File system paths beyond dev-home redacted form
10. Callable objects or function references

### 5.2 Forbidden Raw Field Names

The following field names must be redacted if they appear in any data stored to audit:

```
api_key
apikey
authorization
bearer
token
access_token
refresh_token
password
secret
cookie
credential
private_key
client_secret
access_key
auth_header
passwd
session
```

These match the existing `_FORBIDDEN_ARG_FIELD_NAMES` from `dev_web_tool_dry_run.py`.

### 5.3 Secret Value Patterns

The following patterns must be redacted if detected in any value:

- `sk-[a-zA-Z0-9_-]{8,}` (API keys)
- `Bearer\s+\S+` (Bearer tokens)
- `Authorization\s*:\s*\S+` (Authorization headers)
- `-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----` (Private keys)

These match the existing `_SECRET_VALUE_PATTERNS` from `dev_web_tool_dry_run.py`.

### 5.4 Redaction Guarantee

The audit writer must use the **same sanitizer** as the API endpoint — `sanitize_arguments_preview()` from `dev_web_tool_dry_run.py`. This means:

1. Arguments stored in audit events are **already redacted** by the policy engine before reaching the audit writer.
2. The audit writer must not store the pre-redaction raw arguments.
3. The audit writer must not bypass or weaken the existing redaction.

---

## 6. Storage Location Design (Future, Not Implemented)

### 6.1 Principles

1. Audit storage must be **dev-only and local-only**.
2. Storage must be under `HERMES_HOME` (dev), never under `~/.hermes` (production).
3. Storage must **not** use the production `state.db`.
4. Storage must not be written during this scope phase (1G-04-06).
5. Storage path must be explicit and documented before implementation.

### 6.2 Recommended Future Path

```
$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl
```

Alternative (if sub-directory is preferred):

```
$HERMES_HOME/gateway/dev/tool-dry-run-audit.jsonl
```

### 6.3 Path Finalization

The exact future path may be finalized during implementation, but it must satisfy:

- Under `/Users/huangruibang/Code/hermes-home-dev` only
- Never under `/Users/huangruibang/.hermes`
- Must be a dedicated file, not mixed into existing state.db or other JSONL files
- Must be under a directory that exists or can be created by the audit writer

### 6.4 Format

- Append-only JSONL (one JSON object per line)
- Each line is one audit event
- Lines are separated by `\n`
- No BOM, no wrapping array

---

## 7. Retention / Rotation / Size Limits

### 7.1 Limits

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_event_bytes` | 32 KiB | Maximum size of a single serialized audit event |
| `max_line_bytes` | 34 KiB | Maximum line size (event + newline + safety margin) |
| `max_file_bytes` | 5 MiB | Maximum size of a single audit file |
| `max_retained_files` | 3 | Maximum number of rotated audit files to retain |
| `max_retained_events` | No hard limit (file rotation handles) | Events are bounded by file size limits |

### 7.2 Rotation Behavior

1. When the current audit file reaches `max_file_bytes`, rotate it.
2. Rotation: rename current file to `tool-dry-run-audit.jsonl.1`, shift `.1` → `.2`, `.2` → `.3`, delete `.3` if it exists.
3. Create a new empty `tool-dry-run-audit.jsonl` for new events.
4. Maximum 3 files retained: current + 2 rotated copies.

### 7.3 Corrupt Line Handling

1. If a line cannot be parsed as JSON, skip it during reads.
2. Do not attempt to repair or rewrite corrupt lines.
3. Log a warning (best-effort, must not crash).
4. Continue writing new events after the corrupt line.

### 7.4 Write Failure Behavior

1. Write failures must **not** crash the Dry-Run API.
2. Write failures must **not** enable tool execution.
3. Write failures must **not** cause the API to return an error (audit is best-effort).
4. Write failures should be logged (best-effort).
5. The `auditWritten` field in the API response remains `false` if the write failed.

---

## 8. Failure Modes

### 8.1 Failure Safety Guarantees

| Failure Scenario | System Response |
|-----------------|-----------------|
| Audit file write fails | Return safe dry-run response; `auditWritten = false` |
| Audit directory does not exist | Attempt to create directory; if fails, skip audit |
| Audit file is corrupted on read | Skip corrupt lines; continue writing |
| Disk full | Skip audit write; return safe dry-run response |
| Permission denied on audit file | Skip audit write; return safe dry-run response |
| Event exceeds max size | Truncate or skip; never write oversized events |
| Unexpected exception in audit writer | Catch, log, skip; return safe dry-run response |

### 8.2 Hard Invariants Under Failure

Regardless of any audit failure:

1. `executionAllowed` must remain `false`
2. `dispatchAllowed` must remain `false`
3. `providerSchemaAllowed` must remain `false`
4. No tool handler is called
5. No provider API is called
6. No raw arguments are logged
7. No stack traces appear in API responses
8. No secrets are leaked to logs or audit files

### 8.3 Error Representation

If the audit writer encounters an error that it wants to surface internally:

- Use a safe `errorCode` / `policyNote` in the audit event itself (e.g., `AUDIT_WRITE_FAILED`)
- Never include stack traces in the audit event
- Never include raw arguments in error logs

---

## 9. Future Implementation Scope

### 9.1 Allowed Files for Future Audit Implementation

| File | Action | Scope |
|------|--------|-------|
| `hermes_cli/dev_web_tool_dry_run_audit.py` | **New** | Audit writer module: JSONL append, rotation, redaction verification |
| `tests/test_dev_web_tool_dry_run_audit.py` | **New** | Audit writer unit tests |
| `hermes_cli/dev_web_api.py` | **Modify** | Integrate audit writer call into dry-run route handler |
| `tests/test_dev_web_tool_dry_run_api.py` | **Modify** | Add audit-related API tests |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | **Modify** | Add Phase 1G-04-07 completion record |
| `docs/webui/phase-1-implementation-plan.md` | **Modify** | Update Phase 1G-04-07 status |

### 9.2 Implementation Phase Designation

Future implementation should be designated **Phase 1G-04-07** (Internal Audit Writer).

### 9.3 Implementation Approach

1. The audit writer is an **internal module** — it does not expose new API routes.
2. The audit writer is called from the existing dry-run route handler after the policy decision is computed.
3. The audit writer writes to local JSONL file only.
4. The `auditWritten` field in the API response changes from `false` to `true` only after successful write.
5. No new API route, OpenAPI path, or frontend route is required.

### 9.4 Deferred Items

The following are **explicitly deferred** to later phases:

| Item | Reason |
|------|--------|
| Audit viewer UI | Requires separate design and scope freeze |
| Audit search/list API | Requires separate design and OpenAPI changes |
| Audit export functionality | Requires separate design |
| Audit read route | Requires new API route and OpenAPI path |
| Real-time audit streaming | Not needed for dry-run audit |

---

## 10. Future Forbidden Files

The following files must **not** be modified during audit implementation:

```
apps/hermes-dev-webui/src/
apps/hermes-dev-webui/tests/
apps/hermes-dev-webui/e2e/
apps/hermes-dev-webui/playwright/
docs/webui/openapi/dev-web-api-v1.yaml
hermes_cli/main.py
hermes_cli/dev_web_tool_dry_run.py       # Policy model is frozen
hermes_cli/dev_web_tool_policy.py         # Static policy is frozen
hermes_cli/dev_web_tool_policy_service.py # Policy query service is frozen
hermes_cli/dev_web_tool_schema_preview.py # Schema preview model is frozen
hermes_cli/dev_web_tool_schema_preview_service.py # Schema preview service is frozen
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
```

**Note:** `docs/webui/openapi/dev-web-api-v1.yaml` and `hermes_cli/main.py` remain forbidden unless a later phase explicitly introduces an audit read API route, which would require separate scope freeze and approval.

---

## 11. Route Governance

### 11.1 Before Phase 1G-04-06

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

### 11.2 After Phase 1G-04-06

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

### 11.3 Declaration

**No routes are added, modified, or removed in Phase 1G-04-06.**

- No audit route is added.
- No write route is added.
- No execution route is added.
- No provider schema route is added.
- Audit is an internal implementation detail of the existing dry-run route, not a new route.

---

## 12. Test Plan (Future, Not Implemented)

### 12.1 Audit Event Model Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Audit event is JSON-serializable | Event serializes to valid JSON |
| 2 | Audit event model is JSON-safe | No non-serializable types |
| 3 | Audit event redacts secrets | No raw secrets in any field |
| 4 | Audit event never stores raw arguments | Only redactedArgumentsPreview stored |
| 5 | Audit event invariant: executionAllowed is false | Always false |
| 6 | Audit event invariant: dispatchAllowed is false | Always false |
| 7 | Audit event invariant: providerSchemaAllowed is false | Always false |

### 12.2 Audit Writer Tests

| # | Test | Expected |
|---|------|----------|
| 8 | Audit writer uses HERMES_HOME dev path only | Path under dev HERMES_HOME |
| 9 | Audit writer rejects ~/.hermes | Raises or refuses |
| 10 | Audit writer does not touch production state.db | No production DB access |
| 11 | Audit writer appends JSONL safely | Valid JSONL output |
| 12 | Audit writer handles write failure | Returns safe response, no crash |
| 13 | Audit writer handles corrupt lines | Skips on read, continues writing |
| 14 | Audit writer enforces max event size | Oversized events handled gracefully |
| 15 | Audit writer enforces retention / rotation | Old files rotated, max 3 retained |

### 12.3 Dry-Run API Integration Tests

| # | Test | Expected |
|---|------|----------|
| 16 | Dry-run API sets auditWritten=true only on successful audit write | After integration |
| 17 | Dry-run API keeps executionAllowed=false | Always false |
| 18 | Dry-run API keeps dispatchAllowed=false | Always false |
| 19 | Dry-run API keeps providerSchemaAllowed=false | Always false |

### 12.4 Security Boundary Tests

| # | Test | Expected |
|---|------|----------|
| 20 | No tool handler called during audit write | Verified |
| 21 | No provider called during audit write | Verified |
| 22 | No dispatch called during audit write | Verified |
| 23 | No execution called during audit write | Verified |
| 24 | Route governance unchanged after audit integration | Same counts |

---

## 13. Acceptance Criteria

### 13.1 Phase 1G-04-06 Acceptance

| # | Criterion |
|---|-----------|
| 1 | Docs-only changes |
| 2 | New scope/design doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | No code changes |
| 6 | No OpenAPI changes |
| 7 | No tests changed |
| 8 | No frontend changes |
| 9 | No routes changed |
| 10 | OpenAPI paths = 32 |
| 11 | Runtime routes = 32 |
| 12 | Tool GET routes = 4 |
| 13 | Tool write routes = 0 |
| 14 | Tool dry-run routes = 1 |
| 15 | Tool execution routes = 0 |
| 16 | STATIC_ALLOWLIST empty |
| 17 | Tool Execution disabled |
| 18 | Provider Schema not sent |
| 19 | Tool Audit still absent (not implemented) |
| 20 | Audit Storage not implemented |
| 21 | Controlled Execution not started |
| 22 | Local commit created |
| 23 | Not pushed |

### 13.2 Scope Completeness

| # | Required Section | Present |
|---|-----------------|---------|
| 1 | Phase Definition | Yes |
| 2 | Audit Goal | Yes |
| 3 | Non-Goals | Yes |
| 4 | Audit Event Model | Yes |
| 5 | Sensitive Data Policy | Yes |
| 6 | Storage Location Design | Yes |
| 7 | Retention / Rotation / Size Limits | Yes |
| 8 | Failure Modes | Yes |
| 9 | Future Implementation Scope | Yes |
| 10 | Future Forbidden Files | Yes |
| 11 | Route Governance | Yes |
| 12 | Test Plan | Yes |
| 13 | Acceptance Criteria | Yes |

---

*Phase 1G-04-06 Dry-Run Audit Storage Scope / Design: scope/design-only, docs-only, no audit implementation, no audit file creation, no API code changes, no OpenAPI changes, no frontend changes, no route changes, no provider schema sending, no tool dispatch, no tool execution, no allowlist change.*

---

## 14. Implementation Status

**Phase 1G-04-07 has implemented the audit writer based on this design.**

Implementation details:

| Design Element | Implementation Status |
|----------------|----------------------|
| Audit event model (30 fields) | ✅ Implemented in `build_dry_run_audit_event()` |
| Sensitive data policy | ✅ Defensive sanitization in `_sanitize_event_value()` |
| Forbidden field names (18) | ✅ `_FORBIDDEN_FIELD_STEMS` matches design |
| Secret value patterns (4) | ✅ `_SECRET_VALUE_PATTERNS` matches design |
| Storage path | ✅ `$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl` |
| Append-only JSONL | ✅ UTF-8, single-line JSON per event |
| Max event size (32 KiB) | ✅ `_MAX_EVENT_BYTES = 32 * 1024` |
| Max file size (5 MiB) | ✅ `_MAX_FILE_BYTES = 5 * 1024 * 1024` |
| Max retained files (3) | ✅ `_MAX_RETAINED_FILES = 3` (current + 2 rotated) |
| Rotation behavior | ✅ `.1`, `.2` naming, oldest deleted |
| Write failure safety | ✅ Never enables execution, never calls provider |
| HERMES_HOME validation | ✅ Rejects missing, rejects production, rejects state.db |
| Dry-Run API integration | ✅ `auditWritten` reflects write success, not execution |
| Deferred: Audit viewer UI | ❌ Not implemented |
| Deferred: Audit read/search API | ❌ Not implemented |
| Deferred: Audit export | ❌ Not implemented |
