# Phase 1G-04-24: Pre-Execution Audit Minimal Implementation / Still Blocked-Only

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-24 |
| Title | Pre-Execution Audit Minimal Implementation / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Dependencies | Phase 1G-04-23 (scope freeze), Phase 1G-04-22 (digest verification) |
| Branch | dev-huangruibang |
| Base commit | `17521b3572f5864414022d57b20173a1d8564619` |

---

## 1. Phase Definition

Phase 1G-04-24 implements minimal pre-execution audit writing while preserving the still-blocked-only execution boundary.

This phase implements:
- Pre-execution audit module (`dev_web_tool_pre_execution_audit.py`)
- Pre-execution audit package builder with required field validation
- Pre-execution audit containment-based path guard
- Pre-execution audit append-only JSONL writer
- `preExecutionAuditId` generation (prefix `pea_`)
- `executeRequestId` generation (prefix `exe_`)
- Execute route pre-execution audit gates (Gates 38–45)
- Valid token + valid digest → pre-execution audit written → blocked at handler lookup
- Pre-execution audit write failure fail-closed
- Safe audit identifiers in response (`preExecutionAuditId`, `executeRequestId`, `preExecutionAuditStatus`)
- OpenAPI schema-only updates
- Backend tests (49 new tests)
- Documentation

This phase does NOT implement:
- Post-execution audit
- Handler lookup
- Tool Handler call
- Tool Dispatch
- Tool Execution
- Provider Schema sending
- Provider API call
- Frontend execute flow
- Audit read API
- Audit viewer
- Real Controlled Execution

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base commit | `17521b3572f5864414022d57b20173a1d8564619` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Valid token + valid digest final block before this phase | `blocked_pre_execution_audit_not_implemented` |
| Pre-execution audit | Not implemented |
| Post-execution audit | Not implemented |
| Handler lookup | Not enabled |
| Real Controlled Execution | Not started |

---

## 3. Implementation Summary

### 3.1 New Module: `dev_web_tool_pre_execution_audit.py`

Pure backend helper module implementing:

- `PreExecutionAuditPackageResult` — frozen dataclass for package build results
- `PreExecutionAuditWriteResult` — frozen dataclass for write results
- `build_pre_execution_audit_package()` — builds audit event from safe execute context
- `write_pre_execution_audit_event()` — validates path, serializes, appends JSONL
- `get_pre_execution_audit_store_path()` — resolves and validates audit store path
- `validate_pre_execution_audit_path()` — path-only validation without file open
- `safe_pre_execution_audit_summary()` — safe summary for responses
- `_generate_pre_execution_audit_id()` — generates `pea_` prefixed IDs
- `_generate_execute_request_id()` — generates `exe_` prefixed IDs
- `_validate_required_fields()` — checks all 24 required fields
- `_build_side_effect_flags()` — always returns all-false flags
- `_build_gate_status()` — gate status map for audit event

Architecture constraints:
- stdlib only (no third-party imports)
- No provider, handler, dispatch, or agent imports
- No network IO, no raw token/arguments/secrets storage
- Deterministic, JSON-serializable output
- Never calls handler / dispatch / provider

### 3.2 Pre-Execution Audit Store Path

```
$HERMES_HOME/gateway/dev/audit/tool-pre-execution-audit.jsonl
```

### 3.3 Path Guard (Containment-Based)

Uses `Path.resolve(strict=False)` + `Path.relative_to()` for containment:
1. HERMES_HOME must not equal production home `~/.hermes`
2. HERMES_HOME must not be inside production subtree
3. Resolved audit_dir must be inside `$HERMES_HOME/gateway/dev/audit`
4. Resolved audit_file must be inside `$HERMES_HOME/gateway/dev/audit`
5. No path may be inside `~/.hermes`
6. Symlink / path traversal into production → fail closed
7. `.hermes-dev` sibling paths NOT falsely blocked
8. No file opened if any containment check fails

### 3.4 Audit ID Strategy

- `preExecutionAuditId` = `pea_` + `secrets.token_urlsafe(16)` (128-bit random)
- `executeRequestId` = `exe_` + `secrets.token_urlsafe(16)` (128-bit random)
- IDs are correlation-only, never authorization credentials
- IDs never contain raw token, full tokenHash, or secrets

### 3.5 Append-Only JSONL Write

- Creates parent directory if safe (`mkdir(parents=True, exist_ok=True)`)
- Opens file in append mode only
- Writes one canonical JSON line per event (sorted keys, no whitespace)
- Adds trailing newline
- Never rewrites or deletes existing records
- Never mutates dry-run audit or token store
- Write failure → fail-closed result, no unhandled exception

### 3.6 Execute Route Integration

Replaced the final block `blocked_pre_execution_audit_not_implemented` with Gates 38–45:

| Gate | Description |
|------|-------------|
| 38 | Pre-execution audit package available |
| 39 | Pre-execution audit path guard passes |
| 40 | Pre-execution audit serialization succeeds |
| 41 | Pre-execution audit write succeeds |
| 42 | Pre-execution audit ID returned |
| 43 | Block because handler lookup is not enabled |
| 44 | Dispatch still disabled |
| 45 | Execution still disabled |

### 3.7 Response Data

When pre-execution audit write succeeds, execute response includes:

```json
{
  "preExecutionAuditId": "pea_...",
  "executeRequestId": "exe_...",
  "preExecutionAuditStatus": "written"
}
```

Must not include: raw confirmationToken, full tokenHash, raw arguments, secrets, authorization headers, cookies, provider credentials, tool execution result.

### 3.8 Failure Contract

| Error Code | Decision |
|------------|----------|
| `pre_execution_audit_unavailable` | `blocked_pre_execution_audit_unavailable` |
| `pre_execution_audit_path_forbidden` | `blocked_pre_execution_audit_path_forbidden` |
| `pre_execution_audit_write_failed` | `blocked_pre_execution_audit_write_failed` |
| `pre_execution_audit_invalid_state` | `blocked_pre_execution_audit_invalid_state` |
| `pre_execution_audit_missing_required_field` | `blocked_pre_execution_audit_missing_required_field` |
| `pre_execution_audit_serialization_failed` | `blocked_pre_execution_audit_serialization_failed` |
| `pre_execution_audit_written_but_handler_lookup_not_enabled` | `blocked_handler_lookup_not_enabled` |
| `handler_lookup_not_enabled` | `blocked_handler_lookup_not_enabled` |

All failures block before handler lookup. All side-effect flags remain false.

### 3.9 Success Contract

If pre-execution audit write succeeds:
- Response includes `preExecutionAuditId`, `executeRequestId`, `preExecutionAuditStatus=written`
- Final decision is `blocked_handler_lookup_not_enabled`
- Side-effect flags all remain false
- No handler lookup, no dispatch, no execution, no provider call

### 3.10 OpenAPI Schema-Only Changes

Updated `docs/webui/openapi/dev-web-api-v1.yaml`:
- Added `preExecutionAuditId`, `executeRequestId`, `preExecutionAuditStatus` to `ToolExecuteData`
- Added `pre_execution_audit_*` error codes to `ToolExecuteErrorCode`
- Added `handler_lookup_not_enabled` error code
- Added `blocked_handler_lookup_not_enabled` decision to `ToolExecuteDecision`
- No new paths, no new methods, no new routes
- OpenAPI paths remain 33

---

## 4. Security Boundary

| Item | Status |
|------|--------|
| OpenAPI path count changed | No — remains 33 |
| Runtime route count changed | No — remains 33 |
| Frontend changed | No |
| STATIC_ALLOWLIST changed | No — remains `frozenset({"clarify"})` |
| Allowlist expanded | No |
| Raw token stored | No |
| Raw token logged | No |
| TokenHash full exposed | No |
| Raw arguments stored | No |
| Raw arguments logged | No |
| Secrets stored | No |
| Production home accessed | No |
| Production state.db accessed | No |
| Post-execution audit implemented | No |
| Handler lookup enabled | No |
| Tool Handler called | No |
| Tool Dispatch | No |
| Tool Execution | No |
| Provider Schema sent | No |
| Provider API called | No |
| Real Controlled Execution started | No |

---

## 5. Route Governance

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |

---

## 6. Tests

| Test Suite | Count | Status |
|------------|-------|--------|
| `test_dev_web_tool_pre_execution_audit.py` | 49 | Pass |
| `test_dev_web_tool_execute.py` | — | Pass |
| `test_dev_web_tool_execute_api.py` | — | Pass |
| `test_dev_web_tool_execute_digest.py` | — | Pass |
| `test_dev_web_tool_execute_confirmation.py` | — | Pass |
| `test_dev_web_tool_execute_preflight.py` | — | Pass |
| `test_dev_web_tool_dry_run.py` | — | Pass |
| `test_dev_web_tool_dry_run_api.py` | — | Pass |
| `test_dev_web_tool_dry_run_audit.py` | — | Pass |
| `test_dev_check_webui.py` | — | Pass |
| `test_dev_web_0c06_closure.py` | — | Pass |

---

## 7. Known Limitations

- Post-execution audit not yet implemented
- Execute route still does not execute tools
- Handler lookup not yet enabled
- Frontend execute UI not implemented
- Audit read API not yet implemented
- Audit viewer not yet implemented
- Append-only JSONL audit write race conditions need future local-dev handling
- Historical records before Phase 1G-04-24 may not contain `preExecutionAuditId`
- Pre-execution audit records are dev-only and not exposed via read API yet

---

## 8. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Pre-execution audit module implemented | ✅ |
| 2 | Audit package builder implemented | ✅ |
| 3 | Audit store path implemented | ✅ |
| 4 | Path guard implemented (containment-based) | ✅ |
| 5 | Audit ID strategy implemented | ✅ |
| 6 | Append-only JSONL writer implemented | ✅ |
| 7 | preExecutionAuditId generated and returned | ✅ |
| 8 | executeRequestId generated and returned | ✅ |
| 9 | Write after valid token + valid digest implemented | ✅ |
| 10 | Write failure blocks | ✅ |
| 11 | Write success still blocks at handler lookup | ✅ |
| 12 | No handler lookup after audit success | ✅ |
| 13 | No dispatch after audit success | ✅ |
| 14 | No execution after audit success | ✅ |
| 15 | No Provider Schema after audit success | ✅ |
| 16 | No Provider API after audit success | ✅ |
| 17 | Side-effect flags remain false | ✅ |
| 18 | Raw token not stored/logged | ✅ |
| 19 | TokenHash full not exposed | ✅ |
| 20 | Raw arguments not stored/logged | ✅ |
| 21 | Secrets not stored | ✅ |
| 22 | OpenAPI paths = 33 | ✅ |
| 23 | Runtime routes = 33 | ✅ |
| 24 | STATIC_ALLOWLIST unchanged | ✅ |
| 25 | Production gateway unaffected | ✅ |
| 26 | Local commit, not pushed | ✅ |

---

*Phase 1G-04-24 Pre-Execution Audit Minimal Implementation: pre-execution audit package building, containment-based path guard, dev-only append-only JSONL audit writing, preExecutionAuditId generation, executeRequestId generation, execute route pre-execution audit gates, safe response fields, and OpenAPI schema-only updates implemented. Execute remains blocked-only at the handler lookup boundary. No post-execution audit, handler lookup, Tool Handler call, dispatch, execution, Provider Schema sending, Provider API call, frontend execution flow, audit read API, audit viewer, or real Controlled Execution was introduced.*
