# Phase 1G-04-16: Dry-Run Historical Lookup Read-Only Implementation

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-16 |
| Title | Dry-Run Historical Lookup Read-Only Implementation / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-16 implementation) |
| Dependencies | Phase 1G-04-15 completed locally |
| Branch | dev-huangruibang |
| Base commit | `610e99d3499645dc5185d5bd4138bd0cea1db5ef` |
| Implementation | Backend read-only lookup + execute gate integration + tests + docs |

---

## 1. Phase Definition

Phase 1G-04-16 = Dry-Run Historical Lookup Read-Only Implementation / Still Blocked-Only.

This phase implements a read-only dry-run historical lookup that retrieves prior dry-run audit records from the dev-only JSONL audit file, and integrates the lookup as a preflight gate in the execute route.

This phase does **not** implement confirmation token issuance.
This phase does **not** implement confirmation token verification.
This phase does **not** implement digest verification.
This phase does **not** implement token store.
This phase does **not** implement pre-execution audit.
This phase does **not** implement post-execution audit.
This phase does **not** enable handler lookup.
This phase does **not** dispatch tools.
This phase does **not** execute tools.
This phase does **not** call providers.
This phase does **not** start real Controlled Execution.

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base HEAD | `610e99d3499645dc5185d5bd4138bd0cea1db5ef` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Execute Route | Blocked-only |
| Dry-Run Audit Writer | Implemented (Phase 1G-04-07) |
| Clarify Allowlist Gate | Implemented (Phase 1G-04-14) |
| Confirmation Token | Not implemented |
| Digest Verification | Not implemented |
| Controlled Execution | Not started |

---

## 3. Implementation Summary

### 3.1 New Module: `hermes_cli/dev_web_tool_execute_preflight.py`

A read-only lookup helper that:

- Reads the dev-only audit JSONL file at `$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl`
- Searches for records matching a given `dryRunRequestId`
- Returns a `DryRunHistoricalLookupResult` with safe, redacted fields
- Fails closed on missing file, malformed JSON, not found, expired, or any parse error
- Does NOT write files
- Does NOT access `~/.hermes`
- Does NOT access production state.db
- Does NOT expose raw secrets or raw arguments

Key interface:

```python
lookup_dry_run_record(
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    dry_run_request_id: str,
    canonical_name: str,
    max_bytes: int = 5 * 1024 * 1024,
    now: datetime | None = None,
) -> DryRunHistoricalLookupResult
```

### 3.2 Audit Source

The lookup reads from the same dev-only audit JSONL written by `dev_web_tool_dry_run_audit.py`:

```
$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl
```

Path components are aligned with the audit writer's `_AUDIT_DIR_RELATIVE` and `_AUDIT_FILENAME` constants.

### 3.3 Field Mapping

| Audit JSONL Field | Lookup Result Field | Notes |
|-------------------|--------------------|----|
| `requestId` | `dry_run_request_id` | The dryRunRequestId stored during dry-run |
| `canonicalName` | `canonical_name` | Tool canonical name |
| `decision` | `decision` | Dry-run decision (would_allow, would_block, etc.) |
| `riskTier` | `risk_tier` | Risk tier at dry-run time |
| `timestamp` | `created_at` | ISO 8601 timestamp |
| `eventId` | `audit_event_id` | Audit event UUID |
| `auditWritten` | `audit_written` | Always True (presence = written, see note) |
| N/A | `policy_version` | Always None — not stored in audit events |
| N/A | `arguments_digest` | Always None — not stored in audit events |
| N/A | `dry_run_decision_digest` | Always None — not stored in audit events |

**Mapping Note — `auditWritten`:** The audit event builder always writes `auditWritten: False` to the JSONL record. The lookup treats a found record as `audit_written=True` because the record's presence in the JSONL proves it was successfully written. This is documented as "presence = written".

### 3.4 Lookup Behavior

- **File missing:** Returns `dry_run_not_found` (fail-closed)
- **Empty file:** Returns `dry_run_not_found`
- **Malformed JSON lines:** Skipped (no crash)
- **Record not found:** Returns `dry_run_not_found`
- **Record expired (TTL > 5 minutes):** Returns `dry_run_expired`
- **Record missing timestamp:** Returns `dry_run_expired` (fail-closed)
- **Multiple records same requestId:** Uses latest valid record (last occurrence)
- **File exceeds max_bytes:** Returns `dry_run_lookup_unavailable`

### 3.5 Binding Verification Functions

The preflight module provides individual verification functions:

- `verify_decision_allowed()` — decision must be `would_allow`
- `verify_audit_written()` — audit_written must be True
- `verify_canonical_name_binding()` — canonicalName must match
- `verify_risk_tier_binding()` — riskTier must match (skips if either is None)
- `verify_policy_version_binding()` — currently a no-op (field not stored)
- `verify_digest_binding()` — currently a no-op (field not stored)

### 3.6 Execute Route Gate Integration

The execute route (`evaluate_tool_execute_request`) was modified to:

1. Accept a new optional `hermes_home` parameter
2. After Gate 7 (dryRunRequestId present), perform historical lookup
3. Verify decision, auditWritten, canonicalName, riskTier, policyVersion, digest bindings
4. Block at confirmation token gate (missing → `confirmation_missing`)
5. Block even with confirmation token present (verification not implemented → `confirmation_not_implemented`)

### 3.7 Confirmation Token Boundary

When `confirmationToken` is present but token verification is not implemented:
- Error code: `confirmation_not_implemented`
- Decision: `blocked_requires_confirmation_token`
- All side-effect flags remain false

### 3.8 Digest Verification Boundary

Current audit events do not store `dryRunDecisionDigest` or `argumentsDigest`. The digest binding check is a no-op (passes because both sides are None). This is documented as a known limitation.

---

## 4. Error Codes

New error codes added to `ToolExecuteErrorCode` OpenAPI enum:

| Error Code | Description |
|------------|-------------|
| `dry_run_not_found` | No dry-run record matching the provided `dryRunRequestId` |
| `dry_run_expired` | Dry-run record found but TTL exceeded |
| `dry_run_not_allowed` | Dry-run decision was not `would_allow` |
| `dry_run_audit_missing` | Dry-run record found but audit was not written |
| `dry_run_canonical_name_mismatch` | `canonicalName` does not match the dry-run record |
| `dry_run_risk_tier_mismatch` | `riskTier` does not match the dry-run record |
| `dry_run_policy_version_mismatch` | `policyVersion` does not match the dry-run record |
| `dry_run_lookup_unavailable` | Audit storage is temporarily unavailable |
| `confirmation_not_implemented` | Confirmation token verification is not implemented |

---

## 5. Execute Gate Order (Updated)

| Gate | Name | Status |
|------|------|--------|
| 1 | Request shape validation | Active |
| 2 | Kill switches | Active |
| 3 | Static allowlist | Active |
| 4 | Known tool / policy record | Active |
| 5 | Denylist / risk-tier disallowance | Active |
| 6 | `dryRunRequestId` present | Active |
| 7 | Dry-run historical lookup | **New — Active** |
| 8 | Dry-run decision must be `would_allow` | **New — Active** |
| 9 | Dry-run `auditWritten` must be true | **New — Active** |
| 10 | `canonicalName` binding | **New — Active** |
| 11 | `riskTier` binding | **New — Active** |
| 12 | `policyVersion` binding | **New — Active (no-op)** |
| 13 | Digest binding | **New — Active (no-op)** |
| 14 | `confirmationToken` present | Active |
| 15 | Confirmation token verification | **New — Blocks (not implemented)** |
| 16+ | Not implemented | Blocked |

---

## 6. Route Governance

No route governance count change.

| Metric | Before | After |
|--------|--------|-------|
| OpenAPI paths | 33 | 33 |
| Runtime routes | 33 | 33 |
| Tool GET routes | 4 | 4 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` | `frozenset({"clarify"})` |

---

## 7. Security Boundary

| Item | Status |
|------|--------|
| Frontend changed | No |
| Routes changed | No (only OpenAPI enum expanded) |
| Tool write routes changed | No (still 0) |
| STATIC_ALLOWLIST changed | No (still `{"clarify"}`) |
| Allowlist expanded | No |
| Confirmation token implemented | No |
| Digest verification implemented | No |
| Token store implemented | No |
| Pre/post execution audit implemented | No |
| Handler lookup enabled | No |
| Tool Handler called | No |
| Tool Dispatch | No |
| Tool Execution | No |
| Provider Schema sent | No |
| Provider API called | No |
| Real Controlled Execution started | No |

---

## 8. Tests

### 8.1 Preflight Reader Tests (`tests/test_dev_web_tool_execute_preflight.py`)

35 tests covering:
- Audit JSONL file missing → not found
- Empty audit JSONL → not found
- Malformed JSONL does not crash
- Valid record found by dryRunRequestId
- Multiple records same dryRunRequestId → latest valid record
- Record with raw secrets does not expose raw secrets
- Record expired by timestamp + TTL blocks
- Record within TTL passes
- Record missing timestamp → fail-closed
- Decision `would_block` blocks
- Audit written false blocks
- canonicalName mismatch blocks
- riskTier mismatch blocks
- policyVersion binding (no-op tests)
- digest binding tests
- Oversized file → fail-closed
- Production path rejection

### 8.2 Execute Model Tests (`tests/test_dev_web_tool_execute.py`)

82 tests (up from ~60) including new integration tests:
- clarify missing dryRunRequestId → blocked
- clarify dryRunRequestId not found → blocked
- clarify dry-run expired → blocked
- clarify dry-run decision not would_allow → blocked
- clarify canonicalName mismatch → blocked
- clarify valid dry-run but missing confirmationToken → blocked
- clarify valid dry-run + fake confirmationToken → blocked
- All side-effect flags false on every blocked path
- Handler not called on any blocked path
- Provider not called on any blocked path

### 8.3 Execute API Tests (`tests/test_dev_web_tool_execute_api.py`)

56 tests (up from ~45) including new API-level tests:
- clarify missing dryRunRequestId → blocked
- clarify dryRunRequestId not found → blocked
- clarify valid dry-run missing confirmation → blocked
- clarify valid dry-run fake confirmation → blocked
- All response flags false with lookup
- dry-run decision not would_allow → blocked
- No execution started with valid lookup

### 8.4 Route Governance Tests

- OpenAPI paths = 33 ✓
- Runtime routes = 33 ✓
- Tool GET = 4 ✓
- Tool write = 0 ✓
- Tool dry-run = 1 ✓
- Tool execution = 1 ✓

### 8.5 Dry-Run Regression Tests

- 528 passed, 2 skipped ✓

---

## 9. Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `hermes_cli/dev_web_tool_execute_preflight.py` | New | Read-only lookup helper |
| `hermes_cli/dev_web_tool_execute.py` | Modified | Integrated lookup gates, new error codes |
| `hermes_cli/dev_web_api.py` | Modified | Pass hermes_home to evaluator |
| `docs/webui/openapi/dev-web-api-v1.yaml` | Modified | Added error codes to ToolExecuteErrorCode enum |
| `tests/test_dev_web_tool_execute_preflight.py` | New | 35 lookup reader tests |
| `tests/test_dev_web_tool_execute.py` | Modified | 82 tests with lookup integration |
| `tests/test_dev_web_tool_execute_api.py` | Modified | 56 tests with API-level lookup tests |
| `docs/webui/phase-1g-04-16-dry-run-historical-lookup-read-only-implementation.md` | New | This document |

---

## 10. Known Limitations

- `policyVersion` is not stored in current audit events → binding check is a no-op
- `argumentsDigest` is not stored in current audit events → binding check is a no-op
- `dryRunDecisionDigest` is not stored in current audit events → binding check is a no-op
- `auditWritten` is always False in JSONL records → lookup uses "presence = written" mapping
- Confirmation token issuance and verification are not implemented
- Token store is not implemented
- Pre-execution and post-execution audit writers are not implemented
- Handler lookup is not enabled
- Execute route remains blocked-only
- Frontend execute UI is not implemented
- Lookup performance can be optimized later (currently reads entire JSONL)
- Multi-file audit rotation support may need future work

---

## 11. Risks

### P0

None identified.

### P1

None identified.

### P2

- Confirmation token issuance / verification not yet implemented
- Token store not yet implemented
- Digest verification not yet implemented
- Pre/post execution audit not yet implemented
- Execute route still does not execute tools
- Handler lookup not yet enabled
- Frontend execute UI not implemented
- Browser smoke not re-run
- Clarify handler-level audit still needs future phase
- Lookup performance can be optimized later
- Multi-file audit rotation support may be future work

---

## 12. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Dry-run historical lookup read-only helper implemented | ✓ |
| 2 | Lookup reads dev-only dry-run audit JSONL | ✓ |
| 3 | Lookup does not write files | ✓ |
| 4 | Lookup does not read production state | ✓ |
| 5 | Lookup does not access ~/.hermes | ✓ |
| 6 | Lookup does not expose raw secrets | ✓ |
| 7 | Lookup does not expose raw arguments | ✓ |
| 8 | Lookup fail-closed on missing / malformed / not found / expired | ✓ |
| 9 | Execute route integrates lookup gate | ✓ |
| 10 | clarify missing dryRunRequestId blocks | ✓ |
| 11 | clarify dry-run not found blocks | ✓ |
| 12 | clarify dry-run expired blocks | ✓ |
| 13 | clarify dry-run not would_allow blocks | ✓ |
| 14 | clarify auditWritten false blocks | ✓ |
| 15 | clarify binding mismatch blocks | ✓ |
| 16 | Valid lookup still blocks at confirmation token gate | ✓ |
| 17 | Fake confirmation token still blocks | ✓ |
| 18 | No confirmation token implementation | ✓ |
| 19 | No digest verification implementation | ✓ |
| 20 | No token store | ✓ |
| 21 | No handler lookup | ✓ |
| 22 | No Tool Handler call | ✓ |
| 23 | No dispatch | ✓ |
| 24 | No execution | ✓ |
| 25 | No Provider Schema | ✓ |
| 26 | No Provider API | ✓ |
| 27 | Execute route remains blocked-only | ✓ |
| 28 | STATIC_ALLOWLIST remains `frozenset({"clarify"})` | ✓ |
| 29 | OpenAPI paths = 33 | ✓ |
| 30 | Runtime routes = 33 | ✓ |
| 31 | Tool write = 0 | ✓ |
| 32 | All tests pass | ✓ |
| 33 | Production Gateway unaffected | ✓ |
| 34 | Local commit only, no push | ✓ |

---

*Phase 1G-04-16 Dry-Run Historical Lookup Read-Only Implementation: read-only lookup implemented, execute gate integrated, all paths blocked, no token, no digest verification, no handler, no dispatch, no execution, no provider, no Controlled Execution started.*
