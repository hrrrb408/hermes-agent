# Phase 1G-04-26: Handler Lookup Minimal Implementation / Still Blocked-Only

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-26 |
| Title | Handler Lookup Minimal Implementation / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Dependencies | Phase 1G-04-25 (scope freeze), Phase 1G-04-24 (pre-execution audit) |
| Branch | dev-huangruibang |
| Base commit | `5a52af17fce6614d01395defa8f83518caa9d63e` |

---

## 1. Phase Definition

Phase 1G-04-26 implements minimal safe handler descriptor lookup while preserving the still-blocked-only execution boundary.

This phase implements:
- Handler lookup module (`dev_web_tool_handler_lookup.py`)
- Safe handler descriptor builder with metadata-only fields
- Safe handler registry / catalog metadata lookup
- `handlerLookupId` generation (prefix `hl_`)
- Handler lookup failure contract (fail-closed)
- Handler lookup success contract (safe metadata only)
- Execute route handler lookup gates (Gates 46–56)
- Valid token + valid digest + pre-execution audit written → handler lookup → blocked at dispatch
- Handler lookup success → safe `handlerLookupId` / `handlerDescriptor` in response
- Handler lookup success → final block at `blocked_dispatch_not_enabled`
- OpenAPI schema-only updates
- Backend tests (76 new handler lookup tests)
- Documentation

This phase does NOT implement:
- Tool Handler call
- Tool Dispatch
- Tool Execution
- Post-execution audit
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
| Base commit | `5a52af17fce6614d01395defa8f83518caa9d63e` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Valid token + valid digest + pre-execution audit final block before this phase | `blocked_handler_lookup_not_enabled` |
| Handler lookup | Not enabled |
| Post-execution audit | Not implemented |
| Real Controlled Execution | Not started |

---

## 3. Implementation Summary

### 3.1 New Module: `dev_web_tool_handler_lookup.py`

Pure backend helper module implementing:

- `HandlerLookupResult` — frozen dataclass for lookup results
- `lookup_handler_descriptor(...)` — safe metadata lookup by canonicalName
- `validate_handler_descriptor(...)` — descriptor field validation
- `build_handler_descriptor(...)` — standalone descriptor builder
- `safe_handler_lookup_summary(...)` — safe summary for responses
- `_generate_handler_lookup_id()` — generates `hl_` prefixed IDs
- `_build_side_effect_flags()` — always returns all-false flags
- `_fail_closed(...)` — fail-closed lookup result

Architecture constraints:
- stdlib only (no third-party imports)
- No provider, handler, dispatch, or agent imports
- No network IO, no filesystem mutation, no raw token/arguments/secrets storage
- Deterministic, JSON-serializable output
- Never calls handler / dispatch / provider
- Handler existence is NOT permission
- Handler descriptor is NOT permission
- STATIC_ALLOWLIST remains the permission boundary

### 3.2 Handler Lookup Source Strategy

Uses a minimal static descriptor mapping covering only allowlisted tools:

```python
_SAFE_HANDLER_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "clarify": {
        "canonicalName": "clarify",
        "handlerId": "handler_clarify",
        "registryKey": "clarify",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "clarify",
        "riskTier": "R0",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
}
```

This mapping:
- Only covers tools in `STATIC_ALLOWLIST`
- Contains metadata only — no importable module references
- Does NOT expand permission beyond `STATIC_ALLOWLIST`
- Does NOT trigger handler import side effects

### 3.3 Handler Lookup ID Strategy

- `handlerLookupId` = `hl_` + `secrets.token_urlsafe(16)` (128-bit random)
- ID is correlation-only, never an authorization credential
- ID never contains raw token, full tokenHash, or secrets
- Each lookup generates a unique ID

### 3.4 Handler Descriptor Structure

```json
{
  "canonicalName": "clarify",
  "handlerId": "handler_clarify",
  "registryKey": "clarify",
  "moduleName": "builtin.safe_metadata_only",
  "callableName": "clarify",
  "riskTier": "R0",
  "allowlisted": true,
  "dispatchAllowed": false,
  "executionAllowed": false,
  "providerSchemaAllowed": false,
  "sideEffectFreeLookup": true
}
```

Descriptor contains safe fields only. Must NOT contain:
- Raw arguments, raw token, full tokenHash
- Provider credentials, Provider Schema payload
- Function objects, callable references, secrets

### 3.5 Execute Route Integration

Replaced the final block `blocked_handler_lookup_not_enabled` with Gates 46–56:

| Gate | Description |
|------|-------------|
| 46 | Handler lookup enable gate |
| 47 | Handler registry / metadata source available |
| 48 | Handler descriptor lookup by canonicalName |
| 49 | Handler descriptor validates canonicalName |
| 50 | Handler descriptor matches allowlist / risk tier / policy metadata |
| 51 | Handler descriptor is side-effect-free metadata only |
| 52 | `handlerLookupId` generated |
| 53 | Handler lookup safe response fields available |
| 54 | Block because dispatch is not enabled |
| 55 | Tool Handler still not called |
| 56 | Execution still disabled |

### 3.6 Response Data

When handler lookup succeeds, execute response includes:

```json
{
  "handlerLookupId": "hl_...",
  "handlerLookupStatus": "found",
  "handlerDescriptor": {
    "canonicalName": "clarify",
    "handlerId": "handler_clarify",
    "registryKey": "clarify",
    "moduleName": "builtin.safe_metadata_only",
    "callableName": "clarify",
    "riskTier": "R0",
    "allowlisted": true,
    "dispatchAllowed": false,
    "executionAllowed": false,
    "providerSchemaAllowed": false,
    "sideEffectFreeLookup": true
  },
  "finalBlock": "blocked_dispatch_not_enabled"
}
```

Also preserves existing safe fields:
- `preExecutionAuditId`, `executeRequestId`, `preExecutionAuditStatus`
- `dryRunDecisionDigest`

Must not include: raw confirmationToken, full tokenHash, raw arguments, secrets, authorization headers, cookies, provider credentials, tool execution result, callable object, function repr, dispatch result, provider response.

### 3.7 Failure Contract

| Error Code | Decision |
|------------|----------|
| `handler_lookup_unavailable` | `blocked_handler_lookup_unavailable` |
| `handler_lookup_not_found` | `blocked_handler_lookup_not_found` |
| `handler_lookup_not_allowlisted` | `blocked_handler_lookup_not_allowlisted` |
| `handler_lookup_registry_unavailable` | `blocked_handler_lookup_registry_unavailable` |
| `handler_lookup_descriptor_invalid` | `blocked_handler_lookup_descriptor_invalid` |
| `handler_lookup_side_effect_risk` | `blocked_handler_lookup_side_effect_risk` |
| `handler_lookup_policy_mismatch` | `blocked_handler_lookup_policy_mismatch` |
| `handler_lookup_written_but_dispatch_not_enabled` | `blocked_dispatch_not_enabled` |
| `dispatch_not_enabled` | `blocked_dispatch_not_enabled` |

All failures block before dispatch. All side-effect flags remain false.

### 3.8 Success Contract

If handler lookup succeeds:
- Response includes `handlerLookupId`, `handlerLookupStatus=found`, `handlerDescriptor`
- Final decision is `blocked_dispatch_not_enabled`
- Side-effect flags all remain false
- No dispatch, no Tool Handler call, no execution, no provider call

### 3.9 OpenAPI Schema-Only Changes

Updated `docs/webui/openapi/dev-web-api-v1.yaml`:
- Added `handlerLookupId`, `handlerLookupStatus`, `handlerDescriptor` to `ToolExecuteData`
- Added `ToolHandlerDescriptor` schema with safe metadata fields
- Added `handler_lookup_*` error codes to `ToolExecuteErrorCode`
- Added `dispatch_not_enabled` error code
- Added `blocked_handler_lookup_*` and `blocked_dispatch_not_enabled` decisions to `ToolExecuteDecision`
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
| Handler lookup enabled | Yes — safe metadata only |
| Tool Handler called | No |
| Tool Dispatch | No |
| Tool Execution | No |
| Post-execution audit implemented | No |
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
| `test_dev_web_tool_handler_lookup.py` | 76 | Pass |
| `test_dev_web_tool_execute.py` | — | Pass |
| `test_dev_web_tool_execute_api.py` | — | Pass |
| `test_dev_web_tool_pre_execution_audit.py` | — | Pass |
| `test_dev_web_tool_execute_digest.py` | — | Pass |
| `test_dev_web_tool_execute_confirmation.py` | — | Pass |
| `test_dev_web_tool_execute_preflight.py` | — | Pass |
| `test_dev_web_tool_dry_run.py` | — | Pass |
| `test_dev_web_tool_dry_run_api.py` | — | Pass |
| `test_dev_web_tool_dry_run_audit.py` | — | Pass |
| `test_dev_check_webui.py` | — | Pass |
| `test_dev_web_0c06_closure.py` | — | Pass |
| Full related backend regression | 1221 | Pass (2 skipped, 5 deselected) |

---

## 7. Known Limitations

- Tool Handler call not yet enabled
- Dispatch not yet enabled
- Execution not yet enabled
- Post-execution audit not yet implemented
- Frontend execute UI not implemented
- Audit read API not yet implemented
- Audit viewer not yet implemented
- Handler registry source is minimal static mapping until future registry abstraction
- Only `clarify` has a handler descriptor (matches STATIC_ALLOWLIST)
- Lookup performance can be optimized later
- Pre-existing stale `STATIC_ALLOWLIST` assertions remain in non-gate tests until separate cleanup

---

## 8. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Handler lookup module implemented | ✅ |
| 2 | Safe handler descriptor builder implemented | ✅ |
| 3 | Safe handler metadata lookup implemented | ✅ |
| 4 | `handlerLookupId` generated and returned | ✅ |
| 5 | Handler descriptor returned with safe metadata only | ✅ |
| 6 | Handler lookup failure blocks | ✅ |
| 7 | Handler lookup success still blocks at dispatch boundary | ✅ |
| 8 | Final block = `blocked_dispatch_not_enabled` | ✅ |
| 9 | No Tool Handler call | ✅ |
| 10 | No dispatch | ✅ |
| 11 | No execution | ✅ |
| 12 | No post-execution audit | ✅ |
| 13 | No Provider Schema | ✅ |
| 14 | No Provider API | ✅ |
| 15 | No frontend changes | ✅ |
| 16 | No route count changes | ✅ |
| 17 | No OpenAPI path changes | ✅ |
| 18 | OpenAPI paths = 33 | ✅ |
| 19 | Runtime routes = 33 | ✅ |
| 20 | Tool GET = 4 | ✅ |
| 21 | Tool write = 0 | ✅ |
| 22 | Tool dry-run = 1 | ✅ |
| 23 | Tool execution = 1 | ✅ |
| 24 | STATIC_ALLOWLIST unchanged | ✅ |
| 25 | STATIC_ALLOWLIST remains `frozenset({"clarify"})` | ✅ |
| 26 | Raw token not stored/logged | ✅ |
| 27 | TokenHash full not exposed | ✅ |
| 28 | Raw arguments not stored/logged | ✅ |
| 29 | Secrets not stored | ✅ |
| 30 | Callable object not exposed | ✅ |
| 31 | Function repr not exposed | ✅ |
| 32 | Provider credentials not exposed | ✅ |
| 33 | Tests pass | ✅ |
| 34 | memory-check PASS | ✅ |
| 35 | dev-check PASS (WARN: worktree dirty — expected) | ✅ |
| 36 | Production Gateway unaffected | ✅ |
| 37 | Local commit, not pushed | ✅ |

---

*Phase 1G-04-26 Handler Lookup Minimal Implementation: safe handler descriptor lookup, handlerLookupId generation, handler descriptor validation, execute route handler lookup gates, safe response fields, and OpenAPI schema-only updates implemented. Execute remains blocked-only at the dispatch boundary. No Tool Handler call, dispatch, execution, post-execution audit, Provider Schema sending, Provider API call, frontend execution flow, audit read API, audit viewer, or real Controlled Execution was introduced.*

---

## Next Dependency

Phase 1G-04-27 froze the dispatch boundary.

Phase 1G-04-28 implemented the dispatch boundary frozen by Phase 1G-04-27: the minimal safe dispatch plan / envelope, `dispatchId`, execute route dispatch gates 57–69, and safe dispatch response fields. A valid token + valid digest + pre-execution audit + handler lookup + dispatch success now blocks at `blocked_tool_handler_call_not_enabled`. Tool Handler call, dispatch runtime invocation, execution, provider calls, post-execution audit, and real Controlled Execution remain not implemented.

See `docs/webui/phase-1g-04-27-dispatch-scope.md` for the frozen dispatch scope and `docs/webui/phase-1g-04-28-dispatch-minimal-implementation.md` for the dispatch minimal implementation.
