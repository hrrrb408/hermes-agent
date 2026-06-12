# Phase 1G-04-19: Confirmation Token Minimal Backend Implementation Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-19 |
| Title | Confirmation Token Minimal Backend Implementation Scope Freeze |
| Status | Frozen (minimal backend implementation boundary freeze only, no implementation) |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-19 implementation scope freeze) |
| Dependencies | Phase 1G-04-18 completed locally |
| Branch | dev-huangruibang |
| Base commit | `6967822f7a6e0c0780eb9861027a197bcd30f013` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the exact minimal backend implementation boundaries for a future confirmation token implementation phase
2. Defines the future token issuance helper scope
3. Defines the future token verification helper scope
4. Defines the future token hash / token ID scope
5. Defines the future dev-only token JSONL store scope
6. Defines the future token TTL scope
7. Defines the future token single-use / consumed state scope
8. Defines the future token binding with dry-run records
9. Defines the future execute route token verification gate integration
10. Defines the future failure contract
11. Defines the future module boundary
12. Defines future allowed files and forbidden files
13. Defines the future test matrix
14. Defines entry and exit criteria for future implementation
15. Defines route governance strategy for future implementation
16. Defines future OpenAPI strategy
17. Defines future audit / logging redaction
18. Defines acceptance criteria for Phase 1G-04-19
19. Does **not** implement confirmation token issuance
20. Does **not** implement confirmation token verification
21. Does **not** implement token storage
22. Does **not** implement token hashing
23. Does **not** implement token TTL
24. Does **not** implement token single-use consumption
25. Does **not** implement digest verification
26. Does **not** modify execute route behavior
27. Does **not** modify OpenAPI
28. Does **not** add runtime routes
29. Does **not** enable handler lookup
30. Does **not** dispatch tools
31. Does **not** execute tools
32. Does **not** call providers
33. Does **not** start real Controlled Execution

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-19 = **Confirmation Token Minimal Backend Implementation Scope Freeze**.

This phase freezes the exact minimal backend implementation boundaries for a future confirmation token implementation phase.

This phase does **not** implement confirmation token issuance.
This phase does **not** implement confirmation token verification.
This phase does **not** implement token storage.
This phase does **not** implement token hashing.
This phase does **not** implement token TTL.
This phase does **not** implement token single-use consumption.
This phase does **not** implement digest verification.
This phase does **not** modify execute route behavior.
This phase does **not** modify OpenAPI.
This phase does **not** add runtime routes.
This phase does **not** enable handler lookup.
This phase does **not** dispatch tools.
This phase does **not** execute tools.
This phase does **not** call providers.
This phase does **not** start real Controlled Execution.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `6967822f7a6e0c0780eb9861027a197bcd30f013` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Allowlisted canonicalName | `clarify` |
| Execute Route | Blocked-only |
| Dry-Run Historical Lookup | Implemented read-only (Phase 1G-04-16) |
| Production Path Guard | Containment-based (Phase 1G-04-17) |
| Confirmation Token Scope | Frozen in Phase 1G-04-18 |
| Confirmation Token Implementation | Not implemented |
| Token Verification | Not implemented |
| Token Store | Not implemented |
| Token TTL | Not implemented |
| Token Single-Use | Not implemented |
| Digest Verification | Not implemented |
| Handler Lookup | Not enabled |
| Dispatch | Not enabled |
| Execution | Disabled |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

---

## 3. Future Minimal Backend Implementation Goal

The future minimal backend implementation should only make the confirmation token subsystem real enough to:

1. Issue a short-lived dev-only token after an eligible dry-run
2. Store only a token hash and binding metadata in a dev-only store
3. Verify token existence, expiry, single-use status, and binding metadata
4. Consume a token exactly once
5. Keep the execute route blocked after successful token verification until digest verification and pre-execution audit readiness are implemented

The future implementation must **not**:

- Enable handler lookup
- Dispatch tools
- Execute tools
- Call providers
- Start real Controlled Execution

### 3.1 Key Principle

**A valid token is necessary but not sufficient.**

A verified token still does not execute a tool. A verified token still does not permit handler lookup unless a later explicit phase enables it. Token implementation is a gate implementation — not an execution implementation.

---

## 4. Future Module Boundary

### 4.1 Recommended New Module

```
hermes_cli/dev_web_tool_execute_confirmation.py
```

### 4.2 Future Module Responsibilities

The future module should be responsible for:

1. Generate raw token
2. Derive tokenId
3. Hash raw token
4. Build token store record
5. Append token record to dev-only JSONL store
6. Lookup token by hash
7. Verify token TTL
8. Verify token consumed status
9. Verify binding metadata
10. Mark token consumed
11. Return safe verification result
12. Never call handler
13. Never dispatch
14. Never execute
15. Never call provider

### 4.3 Future Module Prohibitions

The future module must **never**:

- Modify STATIC_ALLOWLIST
- Modify tool policy
- Modify OpenAPI path count
- Read `~/.hermes`
- Read production state.db
- Write production files
- Store raw token
- Log raw token
- Store raw arguments
- Store raw secrets
- Call provider
- Call tool handler
- Dispatch tools
- Execute tools

### 4.4 Phase 1G-04-19 Declaration

This file is **not created** in Phase 1G-04-19.

---

## 5. Future Token Issuance Helper Scope

### 5.1 Function Signature

```python
issue_confirmation_token(
    *,
    hermes_home: str | os.PathLike[str],
    dry_run_record: DryRunHistoricalLookupResult,
    canonical_name: str,
    risk_tier: str,
    policy_version: str | None,
    dry_run_request_id: str,
    dry_run_decision_digest: str | None,
    audit_event_id: str | None,
    arguments_digest: str | None,
    redaction_version: str | None,
    now: datetime,
) -> ConfirmationTokenIssueResult
```

### 5.2 Future Issuance Responsibilities

1. Validate dev-only HERMES_HOME
2. Validate token store path containment
3. Validate dry-run decision = `would_allow`
4. Validate `auditWritten = true`
5. Validate `canonicalName` is allowlisted
6. Validate `riskTier` is allowed
7. Validate `dryRunRequestId` is present
8. Validate `dryRunDecisionDigest` is present or explicitly scoped fallback
9. Generate random 256-bit raw token
10. Compute tokenHash
11. Compute tokenId
12. Store only tokenHash + binding metadata
13. Return raw token exactly once to caller
14. Never write raw token to audit
15. Never log raw token
16. Never include raw arguments

### 5.3 Phase 1G-04-19 Declaration

This helper is **not implemented** in Phase 1G-04-19.

---

## 6. Future Token Verification Helper Scope

### 6.1 Function Signature

```python
verify_confirmation_token(
    *,
    hermes_home: str | os.PathLike[str],
    raw_token: str,
    execute_request: ToolExecuteRequest,
    dry_run_lookup_result: DryRunHistoricalLookupResult,
    now: datetime,
) -> ConfirmationTokenVerificationResult
```

### 6.2 Future Verification Responsibilities

1. Validate raw token is present
2. Hash raw token
3. Lookup tokenHash in dev-only store
4. Fail closed if store unavailable
5. Fail closed if token not found
6. Fail closed if token expired
7. Fail closed if token consumed
8. Verify `dryRunRequestId` binding
9. Verify `dryRunDecisionDigest` binding
10. Verify `canonicalName` binding
11. Verify `riskTier` binding
12. Verify `policyVersion` binding
13. Verify `auditEventId` binding when available
14. Verify `argumentsDigest` binding when available
15. Prepare single-use consumption
16. Return safe verification result
17. Never expose raw token
18. Never expose tokenHash fully
19. Never call handler
20. Never dispatch
21. Never execute
22. Never call provider

### 6.3 Phase 1G-04-19 Declaration

This helper is **not implemented** in Phase 1G-04-19.

---

## 7. Future Token Store Scope

### 7.1 Token Store Location

```
$HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl
```

### 7.2 Token Store Path Guard

Future token store path guard must enforce:

1. Resolved HERMES_HOME must not be `~/.hermes`
2. Resolved HERMES_HOME must not be inside `~/.hermes`
3. Resolved token store path must be inside `$HERMES_HOME/gateway/dev/tokens`
4. Resolved token store path must not be inside `~/.hermes`
5. Symlink / path traversal into production home must fail closed
6. Store parent directory creation must be explicit, dev-only, and tested
7. Repo-committed token files are forbidden

### 7.3 Token Store Record Shape

```json
{
  "recordType": "confirmation_token",
  "schemaVersion": 1,
  "tokenId": "...",
  "tokenHash": "...",
  "dryRunRequestId": "...",
  "dryRunDecisionDigest": "...",
  "canonicalName": "clarify",
  "riskTier": "R0",
  "policyVersion": "...",
  "auditEventId": "...",
  "argumentsDigest": "...",
  "redactionVersion": "...",
  "issuedAt": "...",
  "expiresAt": "...",
  "consumedAt": null,
  "status": "issued"
}
```

### 7.4 Token Store Prohibitions

- **Raw token is never stored.**
- **Raw arguments are never stored.**
- **Secrets are never stored.**
- **Provider credentials are never stored.**

### 7.5 Phase 1G-04-19 Declaration

The token store is **not created** in Phase 1G-04-19.

---

## 8. Future Token Hash / Token ID Scope

### 8.1 Token Generation

```
rawToken = base64url(random_256bit_secret)
tokenHash = HMAC-SHA256(dev server secret, rawToken)
tokenId = first 16 or 24 chars of tokenHash or independent random id
```

### 8.2 Fallback (No Dev Server Secret)

```
tokenHash = SHA-256(rawToken)
```

If HMAC key is unavailable, SHA-256 is used with the documented limitation that SHA-256 without a secret is susceptible to rainbow-table attacks on compromised stores. The HMAC option is preferred. This limitation must be documented in the implementation.

### 8.3 Exposure Rules

- `tokenHash` full value should **not** be exposed in user-visible response
- `tokenId` may be safe for audit correlation
- Raw token is returned **once only** to the caller that requested issuance

### 8.4 Phase 1G-04-19 Declaration

Token hashing is **not implemented** in Phase 1G-04-19.

---

## 9. Future Token TTL Scope

### 9.1 TTL Rules

| Rule | Value |
|------|-------|
| Confirmation token TTL | ≤ 5 minutes |
| Token `expiresAt` | Must be ≤ dry-run `expiresAt` |
| Missing `expiresAt` | Fails closed |
| Expired token | Fails closed **before** handler lookup |
| Clock skew handling | Must be explicit in implementation |

### 9.2 Phase 1G-04-19 Declaration

Token TTL is **not implemented** in Phase 1G-04-19.

---

## 10. Future Token Single-Use Scope

### 10.1 Single-Use Rules

| Rule | Description |
|------|-------------|
| Confirmation token is single-use | A token may authorize at most one execute attempt |
| Verification must detect consumed token | Consumed token → `confirmation_reused` |
| Consumption must be atomic | Atomic enough for dev local JSONL constraints |
| Consumed token cannot be reused | Reuse failure = `confirmation_reused` |

### 10.2 Implementation Strategy Options

**Option A — Append-only JSONL event model:**

- Issued record appended as one event
- Consumed record appended as another event
- Latest status derived by scanning records in order
- Advantages: No destructive rewrite, append-only is safe for JSONL
- Disadvantages: Requires scanning on verification

**Option B — Rewrite small dev-only store atomically:**

- Read all records
- Mark target record as consumed
- Write temp file
- fsync if needed
- Atomic replace
- Advantages: Faster lookup (single record has current status)
- Disadvantages: Destructive rewrite of JSONL

### 10.3 Recommended Strategy

**Recommended for minimal implementation: Option A — append-only JSONL event model.**

This avoids destructive rewrite and aligns with the existing audit JSONL pattern already used for dry-run audit storage.

### 10.4 Phase 1G-04-19 Declaration

Token single-use consumption is **not implemented** in Phase 1G-04-19.

---

## 11. Future Execute Route Token Integration Scope

### 11.1 Current Execute Gate Behavior (Phase 1G-04-18 baseline)

The execute gate currently evaluates Gates 1–15 and blocks at Gate 15 with `confirmation_not_implemented`.

| Gate | Name | Current Behavior |
|------|------|------------------|
| 1 | Request shape validation | Active |
| 2 | Kill switches | Blocks if not exact `"true"` |
| 3 | Static allowlist | `clarify` passes; all others blocked |
| 4 | Known tool / policy record | Unknown → blocked |
| 5 | Denylist / risk-tier | Denylisted / R2+ → blocked |
| 6 | `dryRunRequestId` present | Missing → blocked |
| 7 | Dry-run historical lookup | Reads dev-only audit JSONL |
| 8 | Decision must be `would_allow` | Not `would_allow` → blocked |
| 9 | `auditWritten` must be true | Not written → blocked |
| 10 | `canonicalName` binding | Mismatch → blocked |
| 11 | `riskTier` binding | Mismatch → blocked (skips if either None) |
| 12 | `policyVersion` binding | No-op (field not stored) |
| 13 | Digest binding | No-op (field not stored) |
| 14 | `confirmationToken` present | Missing → `confirmation_missing` |
| 15 | Confirmation token verification | **Blocks** — `confirmation_not_implemented` |

### 11.2 Future Token Integration Gate Order

After the future minimal token implementation, the execute route should expand from 15 gates to the following:

| Gate | Name | Description |
|------|------|-------------|
| 1–14 | Existing gates | Unchanged |
| 15 | `confirmationToken` present | Execute request must include a confirmation token |
| 16 | Token store available | Token store must be accessible and dev-only |
| 17 | Token found | Token hash lookup must find a matching record |
| 18 | Token not expired | Token must be within its TTL |
| 19 | Token not consumed | Token must not have been previously used |
| 20 | Token `dryRunRequestId` binding | Token must reference the same dry-run request |
| 21 | Token `dryRunDecisionDigest` binding | Token digest must match |
| 22 | Token `canonicalName` binding | Token canonical name must match |
| 23 | Token `riskTier` binding | Token risk tier must match |
| 24 | Token `policyVersion` binding | Token policy version must match |
| 25 | Token `auditEventId` binding | Token audit event must match (when available) |
| 26 | Token `argumentsDigest` binding | Token arguments digest must match (when available) |
| 27 | Token consume or consume-ready | Token is eligible for consumption |
| 28 | **Block** — digest verification not implemented | Even after valid token, block because digest verification is not yet implemented |
| 29 | **Block** — pre-execution audit not implemented | Even after valid token, block because pre-execution audit is not yet implemented |
| 30 | Handler lookup | **Still not enabled** in minimal token implementation |

### 11.3 Critical Principle

**Even after successful token verification, execute remains blocked.**

The next block reason should be `digest_verification_not_implemented` or `pre_execution_audit_not_implemented`, depending on future phase ordering.

**No handler lookup is allowed in minimal token implementation.** A valid token passes gates 15–27 but still encounters the block at gate 28/29/30.

### 11.4 Phase 1G-04-19 Declaration

The execute route is **not modified** in Phase 1G-04-19.

---

## 12. Future Failure Contract

### 12.1 Error States

| Error Code | Description |
|------------|-------------|
| `confirmation_missing` | No `confirmationToken` provided |
| `confirmation_invalid` | Token does not match any stored token hash |
| `confirmation_store_unavailable` | Token store is temporarily unavailable |
| `confirmation_not_found` | Token hash not found in the token store |
| `confirmation_expired` | Token past its TTL |
| `confirmation_reused` | Token was already consumed |
| `confirmation_dry_run_mismatch` | Token `dryRunRequestId` does not match the execute request |
| `confirmation_digest_mismatch` | Token `dryRunDecisionDigest` does not match |
| `confirmation_canonical_name_mismatch` | Token `canonicalName` does not match |
| `confirmation_risk_tier_mismatch` | Token `riskTier` does not match |
| `confirmation_policy_version_mismatch` | Token `policyVersion` does not match |
| `confirmation_audit_event_mismatch` | Token `auditEventId` does not match (when available) |
| `confirmation_arguments_mismatch` | Token `argumentsDigest` does not match (when available) |
| `confirmation_consume_failed` | Token consumption failed (store write error) |
| `confirmation_verified_but_digest_not_implemented` | Valid token but digest verification not implemented |
| `confirmation_verified_but_pre_execution_audit_not_implemented` | Valid token but pre-execution audit not implemented |

### 12.2 Failure Invariants

All token failures must block **before handler lookup**.

All token failures must keep the following flags `false`:

| Flag | Value |
|------|-------|
| `executionAllowed` | `false` |
| `dispatchAllowed` | `false` |
| `providerSchemaAllowed` | `false` |
| `toolHandlerCalled` | `false` |
| `providerApiCalled` | `false` |
| `executionStarted` | `false` |

---

## 13. Future OpenAPI Scope

### 13.1 Phase 1G-04-19

Phase 1G-04-19 does **not** modify OpenAPI.

### 13.2 Future OpenAPI Refinements

Future token implementation may need schema-only OpenAPI updates:

| Schema | Possible Refinement |
|--------|---------------------|
| `ToolDryRunResponse` | May include optional `confirmationToken` if route strategy chooses issuance through dry-run response (Option A from Phase 1G-04-18 Section 4.2) |
| `ToolExecuteRequest.confirmationToken` | Already has field; may need tightening for real single-use semantics |
| `ToolExecuteErrorCode` | May need `confirmation_expired`, `confirmation_reused`, and other confirmation `_*` error codes |
| `gateStatus` schema | May need token verification gate names (gates 16–27) |

### 13.3 OpenAPI Path Count

**No new OpenAPI path** unless separately approved.

OpenAPI paths should remain **33** in minimal backend token implementation unless a new route is explicitly scoped in a separate scope document.

Tool write routes should remain **0**.

---

## 14. Future Route Governance Scope

### 14.1 Preferred Minimal Implementation

No new route.

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### 14.2 Route Change Policy

If future implementation requires a route change:

1. Must **stop** and create a separate route-governed scope freeze
2. No route change may be smuggled into token implementation
3. Any route count change must be explicitly approved in a new scope document

---

## 15. Future Allowed Files

### 15.1 Future Implementation Allowed Files

The following files may be modified or created in a future token implementation phase. **They are not modified in Phase 1G-04-19.**

#### Backend Source

```
hermes_cli/dev_web_tool_execute_confirmation.py  (new — recommended module)
hermes_cli/dev_web_tool_execute.py
hermes_cli/dev_web_tool_execute_preflight.py
hermes_cli/dev_web_tool_dry_run.py
hermes_cli/dev_web_tool_dry_run_audit.py
hermes_cli/dev_web_api.py
```

#### Test Files

```
tests/test_dev_web_tool_execute_confirmation.py  (new)
tests/test_dev_web_tool_execute.py
tests/test_dev_web_tool_execute_api.py
tests/test_dev_web_tool_execute_preflight.py
tests/test_dev_web_tool_dry_run.py
tests/test_dev_web_tool_dry_run_api.py
tests/test_dev_web_tool_dry_run_audit.py
tests/test_dev_check_webui.py
tests/test_dev_web_0c06_closure.py
```

#### Documentation Files

```
docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md
docs/webui/phase-1-implementation-plan.md
docs/webui/phase-1g-04-19-confirmation-token-implementation-scope.md
```

### 15.2 Declaration

These are **future allowed files only.** They are **not** modified in Phase 1G-04-19, except the docs files explicitly allowed by this phase.

---

## 16. Future Forbidden Files

The following must **not** be modified in any token implementation phase:

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
```

---

## 17. Future Test Matrix

The following tests must pass when token implementation arrives. **None are added in Phase 1G-04-19.**

### 17.1 Token Issuance Tests

| # | Test | Expected |
|---|------|----------|
| 1 | No token issued when dry-run decision is not `would_allow` | No token issued |
| 2 | No token issued when `auditWritten` is false | No token issued |
| 3 | No token issued when `dryRunRequestId` is missing | No token issued |
| 4 | No token issued when `dryRunDecisionDigest` is missing unless explicit fallback scoped | No token issued |
| 5 | Token issued only for `clarify` while `STATIC_ALLOWLIST={"clarify"}` | Token issued |
| 6 | Token raw value returned once only | Single return |
| 7 | `tokenHash` stored, raw token not stored | No raw token in store |
| 8 | `tokenId` stored for correlation | tokenId present |
| 9 | Token store path is dev-only | Dev path only |
| 10 | Token store blocks production home | Blocked |
| 11 | Token store blocks production subtree | Blocked |
| 12 | Token store blocks symlink/path traversal into production | Blocked |
| 13 | Token TTL ≤ 5 minutes | Within bounds |
| 14 | Token `expiresAt` ≤ dry-run `expiresAt` | Within bounds |

### 17.2 Token Verification Tests

| # | Test | Expected |
|---|------|----------|
| 15 | Missing `confirmationToken` blocks | `confirmation_missing` |
| 16 | Malformed token blocks | `confirmation_invalid` |
| 17 | Token store unavailable blocks | `confirmation_store_unavailable` |
| 18 | Token not found blocks | `confirmation_not_found` |
| 19 | Expired token blocks | `confirmation_expired` |
| 20 | Consumed token blocks | `confirmation_reused` |
| 21 | `dryRunRequestId` mismatch blocks | `confirmation_dry_run_mismatch` |
| 22 | `dryRunDecisionDigest` mismatch blocks | `confirmation_digest_mismatch` |
| 23 | `canonicalName` mismatch blocks | `confirmation_canonical_name_mismatch` |
| 24 | `riskTier` mismatch blocks | `confirmation_risk_tier_mismatch` |
| 25 | `policyVersion` mismatch blocks | `confirmation_policy_version_mismatch` |
| 26 | `auditEventId` mismatch blocks when available | `confirmation_audit_event_mismatch` |
| 27 | `argumentsDigest` mismatch blocks when available | `confirmation_arguments_mismatch` |
| 28 | Token consume failure blocks | `confirmation_consume_failed` |

### 17.3 Safety Invariant Tests

| # | Test | Expected |
|---|------|----------|
| 29 | All token failures block before handler lookup | `toolHandlerCalled=false` |
| 30 | All token failures keep side-effect flags false | All flags `false` |
| 31 | Provider is never called on token failure | `providerApiCalled=false` |
| 32 | Dispatch is never called on token failure | `dispatchAllowed=false` |
| 33 | Execution is never started on token failure | `executionStarted=false` |
| 34 | Valid token still blocks when digest verification not implemented | Blocked |
| 35 | Valid token still blocks when pre-execution audit not implemented | Blocked |
| 36 | Valid token does not call handler | `toolHandlerCalled=false` |
| 37 | Valid token does not dispatch | `dispatchAllowed=false` |
| 38 | Valid token does not call provider | `providerApiCalled=false` |

### 17.4 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 39 | OpenAPI paths remain 33 unless separately approved | 33 |
| 40 | Runtime routes remain 33 unless separately approved | 33 |
| 41 | Tool write routes remain 0 | 0 |
| 42 | Tool execution routes remain 1 | 1 |
| 43 | `STATIC_ALLOWLIST` remains `{"clarify"}` | `frozenset({"clarify"})` |

---

## 18. Future Implementation Entry Criteria

Before confirmation token minimal backend implementation may begin, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-19 docs pushed |
| 2 | No P0/P1 open |
| 3 | User explicitly approves minimal token backend implementation |
| 4 | Remote and local branch synchronized |
| 5 | `STATIC_ALLOWLIST` remains exactly `{"clarify"}` |
| 6 | Route governance green |
| 7 | Dry-run historical lookup green |
| 8 | Production path guard green |
| 9 | Execute route blocked-only baseline green |
| 10 | Provider schema not sent |
| 11 | Tool dispatch disabled |
| 12 | Tool execution disabled |
| 13 | Production gateway stable |

---

## 19. Future Implementation Exit Criteria

After confirmation token minimal backend implementation, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Token issuance helper implemented |
| 2 | Token verification helper implemented |
| 3 | Dev-only token store implemented |
| 4 | Raw token returned once only |
| 5 | Raw token not stored |
| 6 | Raw token not logged |
| 7 | `tokenHash` stored |
| 8 | Token TTL enforced |
| 9 | Single-use enforced |
| 10 | Expired token blocks |
| 11 | Reused token blocks |
| 12 | Binding mismatch blocks |
| 13 | Token verification failure blocks before handler lookup |
| 14 | Valid token does not execute tools |
| 15 | Valid token still blocks at digest verification or pre-execution audit readiness boundary |
| 16 | No blocked path calls handler |
| 17 | No blocked path dispatches |
| 18 | No blocked path executes |
| 19 | No blocked path calls provider |
| 20 | OpenAPI paths remain 33 unless separately approved |
| 21 | Runtime routes remain 33 unless separately approved |
| 22 | Tool write routes remain 0 |
| 23 | Tool execution routes remain 1 |
| 24 | `STATIC_ALLOWLIST` remains `{"clarify"}` |
| 25 | Production gateway unaffected |

---

## 20. Acceptance Criteria for Phase 1G-04-19

| # | Criterion |
|---|-----------|
| 1 | Docs-only |
| 2 | New minimal backend implementation scope doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | Phase 1G-04-18 doc updated with next dependency |
| 6 | No code changes |
| 7 | No OpenAPI file changes |
| 8 | No tests changed |
| 9 | No frontend changes |
| 10 | No routes changed |
| 11 | No execute route behavior changes |
| 12 | No `STATIC_ALLOWLIST` changes |
| 13 | `STATIC_ALLOWLIST` remains `frozenset({"clarify"})` |
| 14 | No confirmation token implementation |
| 15 | No confirmation token verification |
| 16 | No token store |
| 17 | No token hash implementation |
| 18 | No token TTL implementation |
| 19 | No token consumption implementation |
| 20 | No digest verification implementation |
| 21 | No pre-execution audit |
| 22 | No post-execution audit |
| 23 | No handler lookup |
| 24 | No Tool Handler call |
| 25 | No dispatch |
| 26 | No execution |
| 27 | No Provider Schema |
| 28 | No Provider API |
| 29 | OpenAPI paths = 33 |
| 30 | Runtime routes = 33 |
| 31 | Tool GET = 4 |
| 32 | Tool write = 0 |
| 33 | Tool dry-run = 1 |
| 34 | Tool execution = 1 |
| 35 | Execute route remains blocked-only |
| 36 | Real Controlled Execution not started |
| 37 | Local docs-only commit created |
| 38 | Not pushed |

---

## 21. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code modified | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Route count changed | Verify route governance; reject if changed |
| 6 | Execute route behavior changed | Verify diff; reject if execute runtime changed |
| 7 | `STATIC_ALLOWLIST` modified | Verify unchanged; reject if modified |
| 8 | Confirmation token implemented | Verify diff; reject if token code added |
| 9 | Token verification implemented | Verify diff; reject if verification code added |
| 10 | Token store implemented | Verify diff; reject if token store created |
| 11 | Digest verification implemented | Verify diff; reject if digest code added |
| 12 | Tool Handler called | Verify no handler invocation; reject if found |
| 13 | Provider API called / Schema sent | Verify no provider calls; reject if found |
| 14 | Tool write routes > 0 | Verify route governance; reject if changed |
| 15 | Tool execution routes ≠ 1 | Verify route governance; reject if changed |
| 16 | Real secret leaked | Content search; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-19 Failed."**

---

## 22. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Future module boundary missing | Verify Section 4 |
| 2 | Future issuance helper scope missing | Verify Section 5 |
| 3 | Future verification helper scope missing | Verify Section 6 |
| 4 | Future token store scope missing | Verify Section 7 |
| 5 | Future token hash / tokenId scope missing | Verify Section 8 |
| 6 | Future TTL scope missing | Verify Section 9 |
| 7 | Future single-use scope missing | Verify Section 10 |
| 8 | Future execute route integration scope missing | Verify Section 11 |
| 9 | Future failure contract missing | Verify Section 12 |
| 10 | Future OpenAPI scope missing | Verify Section 13 |
| 11 | Future route governance scope missing | Verify Section 14 |
| 12 | Future allowed files missing | Verify Section 15 |
| 13 | Future forbidden files missing | Verify Section 16 |
| 14 | Future test matrix missing | Verify Section 17 |
| 15 | Entry criteria missing | Verify Section 18 |
| 16 | Exit criteria missing | Verify Section 19 |
| 17 | Docs incorrectly claim token implemented | Content review |
| 18 | Docs incorrectly claim token verified | Content review |
| 19 | Docs incorrectly claim token store implemented | Content review |
| 20 | Route governance failed | Run tests; verify counts |
| 21 | OpenAPI paths ≠ 33 | Verify count |
| 22 | Runtime routes ≠ 33 | Verify count |
| 23 | Tool GET ≠ 4 | Verify count |
| 24 | Tool write ≠ 0 | Verify count |
| 25 | Tool dry-run ≠ 1 | Verify count |
| 26 | Tool execution ≠ 1 | Verify count |
| 27 | `STATIC_ALLOWLIST` ≠ `{"clarify"}` | Verify value |
| 28 | compileall failed | Run compileall |
| 29 | ruff failed | Run ruff |
| 30 | memory-check failed | Run memory-check |
| 31 | dev-check failed | Run dev-check |
| 32 | Worktree has unexpected files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 23. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Confirmation token issuance / verification not yet implemented | Expected — scope freeze only |
| 2 | Token store not yet implemented | Expected — scope freeze only |
| 3 | Token hash not yet implemented | Expected — scope freeze only |
| 4 | Token TTL not yet implemented | Expected — scope freeze only |
| 5 | Token single-use consumption not yet implemented | Expected — scope freeze only |
| 6 | Digest verification not yet implemented | Expected — scope freeze only |
| 7 | Pre/post execution audit not yet implemented | Expected — scope freeze only |
| 8 | Execute route still does not execute tools | Expected — blocked-only |
| 9 | Handler lookup not yet enabled | Expected — future phase |
| 10 | Frontend execute UI not implemented | Expected — future phase |
| 11 | Browser smoke not re-run | Expected — no frontend changes |
| 12 | Clarify handler-level audit still needs future phase | Expected — future work |
| 13 | Lookup performance can be optimized later | Expected — optimization deferred |
| 14 | Multi-file audit rotation support may be future work | Expected — deferred |
| 15 | Append-only JSONL consumption race conditions need future local-dev handling | Expected — local dev constraints |

---

*Phase 1G-04-19 Confirmation Token Minimal Backend Implementation Scope Freeze: minimal backend implementation boundary frozen, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no token implementation, no token verification, no token store, no digest verification, no handler lookup, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*
