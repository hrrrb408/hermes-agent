# Phase 1G-04-20: Confirmation Token Minimal Backend Implementation / Still Blocked-Only

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-20 |
| Title | Confirmation Token Minimal Backend Implementation / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Dependencies | Phase 1G-04-19 completed locally |
| Branch | dev-huangruibang |

### Summary

This phase implements the minimal backend confirmation token subsystem while preserving the still-blocked-only execution boundary. Confirmation token issuance, verification, dev-only token JSONL storage, token hashing / tokenId, TTL, single-use consumption, dry-run token issuance integration, and execute route token verification gate were implemented.

A valid token can pass the confirmation token verification gate, but execute remains blocked at the digest verification / pre-execution audit boundary. No handler lookup, Tool Handler call, dispatch, execution, Provider Schema sending, Provider API call, frontend execution flow, audit read API, audit viewer, or real Controlled Execution was introduced.

---

## 1. Baseline

| Metric | Value |
|--------|-------|
| Base commit | `e4279fe1708f040b4040cf76da17c8328594d2c7` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Execute Route | Blocked-only |
| Confirmation Token Issuance | Not implemented |
| Confirmation Token Verification | Not implemented |
| Token Store | Not implemented |
| Digest Verification | Not implemented |

---

## 2. Implementation Summary

### 2.1 Confirmation Module

**New file:** `hermes_cli/dev_web_tool_execute_confirmation.py`

This module is a pure backend dev-only helper that does not register routes. It contains:

- `ConfirmationTokenIssueResult` — frozen dataclass for issuance results
- `ConfirmationTokenVerificationResult` — frozen dataclass for verification results
- `issue_confirmation_token()` — issues a short-lived, single-use confirmation token after an eligible dry-run
- `verify_confirmation_token()` — verifies token presence, shape, expiry, single-use status, and all binding fields

The module uses only stdlib imports. It never calls handlers, dispatches tools, calls providers, or accesses `~/.hermes`.

### 2.2 Token Issuance

Token issuance validates:
1. `canonicalName` is on STATIC_ALLOWLIST (currently only `clarify`)
2. Dry-run decision is `would_allow`
3. `auditWritten` is `True`
4. `dryRunRequestId` is present
5. Dev-only HERMES_HOME (production path guard)

Then generates:
- 256-bit random raw token (`secrets.token_urlsafe`)
- HMAC-SHA256 hash of raw token (deterministic dev key)
- Derived tokenId (`ctok_` prefix + hash prefix)
- TTL ≤ 5 minutes, capped at dry-run expiresAt

Returns raw token exactly once. Never stores raw token, raw arguments, or secrets.

### 2.3 Token Verification

Token verification checks:
1. Raw token present and valid shape
2. Dev-only HERMES_HOME path containment
3. Token found in store (hash lookup)
4. Not expired
5. Not consumed (single-use)
6. All binding fields match: dryRunRequestId, dryRunDecisionDigest, canonicalName, riskTier, policyVersion, auditEventId, argumentsDigest

On success with `consume=True`, appends a consumed event to the JSONL store.

### 2.4 Token Store

**Location:** `$HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl`

Append-only JSONL event model (issued + consumed events). Path containment guard:
- HERMES_HOME must not be production home or inside production subtree
- Token directory must be inside `$HERMES_HOME/gateway/dev/tokens`
- Symlink/path traversal into production blocked via `Path.relative_to()`
- `.hermes-dev` paths are NOT falsely blocked

### 2.5 Token Hash / TokenId

- Hash: HMAC-SHA256 with deterministic dev namespace key
- TokenId: `ctok_` + first 24 hex chars of hash
- Full tokenHash never exposed in user-facing responses (only 8-char prefix)
- Raw token returned once on issuance, never stored

### 2.6 TTL

- Maximum 5 minutes
- Token expiresAt capped at dry-run expiresAt when available
- Expired tokens fail closed before handler lookup

### 2.7 Single-Use

- Append-only JSONL event model: issued event + consumed event
- Consumed status derived by scanning events
- Reuse attempts block with `confirmation_reused`
- Race condition documented as P2 limitation

### 2.8 Dry-Run Integration

The dry-run endpoint (`POST /tools/dry-run`) now accepts optional `issueConfirmationToken: boolean`.

Token is only issued when:
- `issueConfirmationToken == true`
- Dry-run decision is `would_allow`
- Audit is written (`auditWritten == true`)
- `canonicalName` is on STATIC_ALLOWLIST

Response includes `confirmationToken`, `confirmationTokenId`, `confirmationTokenExpiresAt` when token is issued.

No new route was added. OpenAPI path count remains 33.

### 2.9 Execute Route Integration

The execute route (`POST /tools/execute`) now verifies confirmation tokens:
- Gate 15: Confirmation token must be present
- Gates 16–27: Token verification (store available, found, not expired, not consumed, all bindings match)
- Gate 28: **Block** — digest verification not implemented

Even after successful token verification, execute remains blocked with:
- `decision: blocked_digest_verification_not_implemented`
- `errorCode: digest_verification_not_implemented`
- All side-effect flags remain false

### 2.10 OpenAPI Schema-Only Changes

Updated `docs/webui/openapi/dev-web-api-v1.yaml`:
- Added `issueConfirmationToken` to `ToolDryRunRequest`
- Added `confirmationToken`, `confirmationTokenId`, `confirmationTokenExpiresAt` to `ToolDryRunData`
- Added new error codes to `ToolExecuteErrorCode` (confirmation_*, digest_verification_not_implemented)
- Added new decisions to `ToolExecuteDecision` (blocked_requires_confirmation_token, blocked_digest_verification_not_implemented)
- No new paths, no new methods, no new routes

---

## 3. Security Boundary

| Check | Status |
|-------|--------|
| OpenAPI path count changed | No — remains 33 |
| Runtime route count changed | No — remains 33 |
| Frontend changed | No |
| STATIC_ALLOWLIST changed | No — remains `frozenset({"clarify"})` |
| Allowlist expanded | No |
| Raw token stored | No |
| Raw token logged | No |
| Raw arguments stored | No |
| Secrets stored | No |
| Production home accessed | No |
| Production state.db accessed | No |
| Digest verification implemented | No |
| Pre-execution audit implemented | No |
| Handler lookup enabled | No |
| Tool Handler called | No |
| Tool Dispatch | No |
| Tool Execution | No |
| Provider Schema sent | No |
| Provider API called | No |
| Real Controlled Execution started | No |

---

## 4. Route Governance

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

## 5. Tests

### 5.1 New Tests

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_dev_web_tool_execute_confirmation.py` | 50 | Token issuance (15), verification (16), safety invariants (7), path guard (5), hash/ID (7) |

### 5.2 Updated Tests

| File | Description |
|------|-------------|
| `tests/test_dev_web_tool_execute.py` | Updated 3 existing tests for new token verification behavior; added 2 new tests for valid-token-still-blocks and token-reuse |

### 5.3 Test Results

- Confirmation tests: 50 passed
- Dry-run tests: 528 passed, 2 skipped
- Execute/preflight tests: 146 passed
- Route governance: 124 passed, 5 deselected
- Full backend regression: 1045 passed, 2 skipped, 5 deselected

---

## 6. Blocked-Only Guarantee

Even after a valid confirmation token passes all verification gates, the execute route returns:

```json
{
  "executionAllowed": false,
  "dispatchAllowed": false,
  "providerSchemaAllowed": false,
  "toolHandlerCalled": false,
  "providerApiCalled": false,
  "executionStarted": false,
  "executionAttempted": false,
  "executionCompleted": false,
  "decision": "blocked_digest_verification_not_implemented",
  "errorCode": "digest_verification_not_implemented"
}
```

---

## 7. Known Limitations

- Digest verification not yet implemented
- Pre-execution audit not yet implemented
- Post-execution audit not yet implemented
- Execute route still does not execute tools
- Handler lookup not yet enabled
- Frontend execute UI not implemented
- Append-only JSONL consumption race conditions (P2)
- SHA-256 fallback for tokenHash if HMAC key unavailable (using deterministic dev HMAC currently)
- dryRunDecisionDigest not yet stored in audit events (binding field may be None)

---

## 8. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Confirmation token module implemented | ✓ |
| Token issuance implemented | ✓ |
| Token verification implemented | ✓ |
| Dev-only token JSONL store implemented | ✓ |
| Token hash / tokenId implemented | ✓ |
| TTL implemented (≤ 5 min) | ✓ |
| Single-use consumption implemented | ✓ |
| Dry-run token issuance integration implemented | ✓ |
| Execute token verification gate implemented | ✓ |
| Valid token still blocks at digest boundary | ✓ |
| No handler lookup | ✓ |
| No dispatch | ✓ |
| No execution | ✓ |
| No Provider Schema / API | ✓ |
| OpenAPI paths = 33 | ✓ |
| STATIC_ALLOWLIST unchanged | ✓ |
| Raw token not stored / logged | ✓ |
| Production path guard for token store | ✓ |
| All tests pass | ✓ |
| memory-check PASS | ✓ |
| dev-check PASS (WARN only for .claude/) | ✓ |
| Production Gateway PID 69355 unaffected | ✓ |
| No push | ✓ |

---

*Phase 1G-04-20 Confirmation Token Minimal Backend Implementation / Still Blocked-Only: minimal backend token issuance, verification, dev-only token JSONL storage, token hashing/tokenId, TTL, single-use consumption, dry-run integration, execute token verification gate implemented. Execute route remains blocked-only at the digest verification boundary. No handler lookup, no dispatch, no execution, no provider schema, no provider API, no frontend changes, no route count changes, no real Controlled Execution started.*

---

## Next Dependency

Phase 1G-04-21 freezes the digest verification boundary. See `docs/webui/phase-1g-04-21-digest-verification-scope.md` for the frozen digest verification scope.

Phase 1G-04-21 still does not implement digest verification, dry-run digest persistence, pre-execution audit, post-execution audit, handler lookup, dispatch, execution, provider calls, or real Controlled Execution.
