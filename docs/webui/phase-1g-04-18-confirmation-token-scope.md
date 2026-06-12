# Phase 1G-04-18: Confirmation Token Issuance / Verification Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-18 |
| Title | Confirmation Token Issuance / Verification Scope Freeze |
| Status | Frozen (confirmation token issuance, verification, storage, TTL, single-use, and binding design only, no implementation) |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-18 confirmation token scope freeze) |
| Dependencies | Phase 1G-04-17 completed locally |
| Branch | dev-huangruibang |
| Base commit | `fc9676555319ca5a52c0cc3d054f7f0f19f176fd` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future confirmation token issuance design
2. Freezes the future confirmation token verification design
3. Freezes the future token storage model
4. Freezes the future token TTL strategy
5. Freezes the future token single-use consumption strategy
6. Freezes the future token binding contract with dry-run records
7. Freezes the future token hash / token id / raw token separation strategy
8. Freezes the future token verification gate order
9. Freezes the future token failure contract
10. Freezes the future token audit strategy
11. Defines the digest verification boundary
12. Defines the execute route behavior delta
13. Defines route governance strategy
14. Defines future OpenAPI strategy
15. Defines future allowed files and forbidden files
16. Defines future test matrix
17. Defines entry criteria and exit criteria for future implementation
18. Defines acceptance criteria for Phase 1G-04-18
19. Does **not** implement confirmation token issuance
20. Does **not** implement confirmation token verification
21. Does **not** implement token storage
22. Does **not** implement digest verification
23. Does **not** modify execute route behavior
24. Does **not** modify OpenAPI
25. Does **not** add runtime routes
26. Does **not** enable handler lookup
27. Does **not** dispatch tools
28. Does **not** execute tools
29. Does **not** call providers
30. Does **not** start real Controlled Execution

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-18 = **Confirmation Token Issuance / Verification Scope Freeze**.

This phase freezes the future confirmation token issuance, storage, verification, TTL, single-use, and dry-run binding design.

This phase does **not** implement confirmation token issuance.
This phase does **not** implement confirmation token verification.
This phase does **not** implement token storage.
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
| Current remote HEAD | `fc9676555319ca5a52c0cc3d054f7f0f19f176fd` |
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
| Confirmation Token | Not implemented |
| Digest Verification | Not implemented |
| Token Store | Not implemented |
| Handler Lookup | Not enabled |
| Dispatch | Not enabled |
| Execution | Disabled |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

### 2.1 Current Execute Gate Behavior (Phase 1G-04-17 baseline)

The execute gate evaluates the following ordered gates and returns a blocked result at the first failure:

| Gate | Name | Current Phase 1G-04-17 Behavior |
|------|------|----------------------------------|
| 1 | Request shape validation | Active |
| 2 | Kill switches | Unset → `blocked_by_kill_switch` |
| 3 | Static allowlist | `clarify` passes; all others → `blocked_by_allowlist` |
| 4 | Known tool / policy record | Unknown → `blocked` (`tool_unknown`) |
| 5 | Denylist / risk-tier | Denylisted / R2+ → blocked |
| 6 | `dryRunRequestId` present | Missing → `blocked_requires_dry_run` |
| 7 | Dry-run historical lookup | Reads dev-only audit JSONL; fail-closed |
| 8 | Decision must be `would_allow` | Not `would_allow` → blocked |
| 9 | `auditWritten` must be true | Not written → blocked |
| 10 | `canonicalName` binding | Mismatch → blocked |
| 11 | `riskTier` binding | Mismatch → blocked (skips if either None) |
| 12 | `policyVersion` binding | No-op (field not stored) |
| 13 | Digest binding | No-op (field not stored) |
| 14 | `confirmationToken` present | Missing → `confirmation_missing` |
| 15 | Confirmation token verification | **Blocks** — `confirmation_not_implemented` |

Even when `clarify` passes all dry-run lookup and binding gates, it is blocked at the confirmation token boundary because token verification is not implemented.

All execution flags remain `false` on every path:

| Invariant Flag | Phase 1G-04-17 Value |
|----------------|----------------------|
| `executionAllowed` | `false` |
| `dispatchAllowed` | `false` |
| `providerSchemaAllowed` | `false` |
| `toolHandlerCalled` | `false` |
| `providerApiCalled` | `false` |
| `executionStarted` | `false` |
| `executionAttempted` | `false` |

---

## 3. Confirmation Token Goal

A confirmation token is a **short-lived, single-use, dev-only approval artifact**.

It proves that a user has reviewed a successful dry-run and explicitly confirmed the exact reviewed request.

### 3.1 Core Properties

1. **Proof of human confirmation.** The token proves a human explicitly confirmed a reviewed dry-run outcome.
2. **Generated only after successful dry-run.** A token must never be issued unless the dry-run decision is `would_allow` and the audit was successfully written.
3. **Strongly bound.** The token must bind to `dryRunRequestId`, `dryRunDecisionDigest`, `canonicalName`, `riskTier`, `policyVersion`, `auditEventId`, and the sanitized arguments digest.
4. **Short-lived.** Recommended TTL ≤ 5 minutes.
5. **Single-use.** A token may authorize at most one execute attempt.
6. **Secret-free.** A token must never contain raw secrets, raw arguments, or provider credentials.
7. **Necessary but never sufficient.** A valid confirmation token does not enable execution by itself.
8. **Verified before handler lookup.** Token verification must happen before any tool handler is looked up.
9. **Fail closed.** Any token failure blocks before dispatch, execution, or provider calls.

### 3.2 Necessary but Never Sufficient

A valid confirmation token does **not**:

- Enable execution by itself
- Imply handler lookup is allowed
- Imply dispatch is allowed
- Imply provider calls are allowed
- Bypass any other gate (kill switches, allowlist, denylist, risk tier, dry-run preflight, audit, digest verification)

All other gates continue to apply independently regardless of token validity.

---

## 4. Token Issuance Source

### 4.1 Issuance Preconditions

Future token issuance should be produced only after a successful dry-run where **all** of the following are true:

| Condition | Description |
|-----------|-------------|
| dry-run decision = `would_allow` | The dry-run decided the tool call would be allowed |
| dry-run `auditWritten` = true | The audit event was successfully written |
| `dryRunRequestId` exists | A unique dry-run request identifier is available |
| `dryRunDecisionDigest` exists or derivable | The digest can be computed or was recorded safely |
| `canonicalName` is allowlisted | The tool passes the STATIC_ALLOWLIST gate |
| `riskTier` is allowed | The risk tier is eligible for execution consideration |
| `policyVersion` is recorded | The policy version at decision time is available |
| Sanitized arguments digest recorded or derivable | The arguments digest can be derived without raw secrets |

### 4.2 Issuance Entry Options

**Preferred future design:**

Token issuance is part of the dev-only dry-run confirmation flow, not part of real execution.

| Option | Description | Trade-off |
|--------|-------------|-----------|
| **Option A** | Extend existing dry-run response with a `confirmationToken` only when the user explicitly requests token issuance (e.g., via a request flag like `issueConfirmationToken: true`) | No new route; reuses existing dry-run endpoint; clear user intent signal |
| **Option B** | Add a future explicit confirmation-token issuance endpoint (e.g., `POST /api/dev/v1/tools/confirm`) | Separates dry-run from confirmation; requires new route governance approval |

**Phase 1G-04-18 does not choose implementation finality.** Phase 1G-04-18 documents the preferred strategy (Option A) and identifies the future decision point. If route governance or user preference later requires Option B, a separate scope document must be created.

### 4.3 Issuance Declaration

- No token is issued in Phase 1G-04-18.
- No dry-run response is changed in Phase 1G-04-18.
- No new endpoint is added in Phase 1G-04-18.

---

## 5. Token Binding Contract

A `confirmationToken` must bind to the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `dryRunRequestId` | Yes | The dry-run request that was reviewed and confirmed |
| `dryRunDecisionDigest` | Yes | The digest of the dry-run decision input |
| `canonicalName` | Yes | The exact tool canonical name |
| `riskTier` | Yes | The risk tier at decision time |
| `policyVersion` | Yes | The policy version at decision time |
| `auditEventId` | If available | The audit event ID from the dry-run audit write |
| `argumentsDigest` | If available | SHA-256 digest of the sanitized arguments |
| `redactionVersion` | If available | Version of the redaction algorithm used |
| `issuedAt` | Yes | Token issuance timestamp |
| `expiresAt` | Yes | Token expiry timestamp |
| `nonce` / `tokenId` | Yes | Unique token identifier (random, opaque) |

### 5.1 Binding Verification

Token binding must be checked **before handler lookup**.

Token binding mismatch **blocks**.

Token binding mismatch keeps all side-effect flags `false`:
- `executionAllowed=false`
- `dispatchAllowed=false`
- `providerSchemaAllowed=false`
- `toolHandlerCalled=false`
- `providerApiCalled=false`
- `executionStarted=false`

---

## 6. Token Payload Strategy

### 6.1 Raw Token Form

The raw token should be **opaque and random**.

```
confirmationToken = base64url(random_256bit_secret)
```

Recommended: `secrets.token_urlsafe(32)` (produces a 43-character base64url string from 256 bits of entropy).

### 6.2 Payload Prohibitions

The raw token must **never**:

- Contain user-readable JSON claims
- Expose dry-run details
- Expose raw arguments
- Expose secrets
- Be predictable or sequential

### 6.3 Token Store Record

The token store should contain the following fields (the raw token is NOT stored):

| Field | Type | Description |
|-------|------|-------------|
| `tokenId` | string | Unique opaque identifier (not the raw token) |
| `tokenHash` | string | Hash of the raw token for lookup |
| `dryRunRequestId` | string | Bound dry-run request ID |
| `dryRunDecisionDigest` | string | Bound dry-run decision digest |
| `canonicalName` | string | Bound tool canonical name |
| `riskTier` | string | Bound risk tier |
| `policyVersion` | string | Bound policy version |
| `auditEventId` | string or null | Bound audit event ID |
| `argumentsDigest` | string or null | Bound arguments digest |
| `issuedAt` | string | ISO 8601 UTC issuance timestamp |
| `expiresAt` | string | ISO 8601 UTC expiry timestamp |
| `consumedAt` | string or null | When the token was consumed (null = unused) |
| `status` | string | Token status: `active`, `consumed`, `expired` |
| `redactionVersion` | string or null | Redaction algorithm version |

### 6.4 Raw Token Storage Prohibition

The raw `confirmationToken` must **never** be stored in any persistent store.

---

## 7. Token Hash Strategy

### 7.1 Hash Algorithm

Store only a hash of the raw token for lookup:

**Recommended:**

```
tokenHash = HMAC-SHA256(server-side dev secret, raw token)
```

Or, if no server-side dev secret is available:

```
tokenHash = SHA-256(raw token)
```

with the clear limitation that SHA-256 without a secret is susceptible to rainbow-table attacks on compromised stores. The HMAC option is preferred.

### 7.2 Token ID Separation

The `tokenId` is an opaque, non-secret identifier included in the token store and audit logs. It is NOT derived from the raw token. The `tokenHash` is used for lookup and is NOT the same as `tokenId`.

### 7.3 Raw Token Exposure Prohibitions

The raw `confirmationToken` must **never** be:

- Written to audit logs
- Committed to any repository
- Printed in server logs
- Exposed through audit read APIs
- Included in any persistent store

---

## 8. Token Store Strategy

### 8.1 Storage Constraints

| Constraint | Requirement |
|------------|-------------|
| Scope | Dev-only |
| Location | Under HERMES_HOME dev area only |
| Lifetime | Ephemeral — restart may invalidate outstanding tokens |
| Production state.db | **Must not** use |
| `~/.hermes` | **Must not** use |
| Git | **Must not** be committed to git |
| Raw token storage | Forbidden |
| Raw argument storage | Forbidden |
| Secret storage | Forbidden |

### 8.2 Recommended Location

If file-backed, the store may use a dev-only path:

```
$HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl
```

### 8.3 Forbidden Store Locations

- `~/.hermes` (production home)
- Production `state.db`
- Repo committed files
- Frontend `localStorage`
- Browser cache
- Provider logs

### 8.4 Phase 1G-04-18 Declaration

- No token store is created in Phase 1G-04-18.
- No token records are written in Phase 1G-04-18.
- No token records are read in Phase 1G-04-18.

---

## 9. Token TTL Strategy

### 9.1 TTL Rules

| Rule | Value |
|------|-------|
| Recommended TTL | ≤ 5 minutes |
| Token `expiresAt` | Must be ≤ dry-run reference `expiresAt` |
| Expired token result | `confirmation_expired` |
| TTL check ordering | Before digest verification, before handler lookup |

### 9.2 TTL Declaration

- No token expiry code is implemented in Phase 1G-04-18.
- The TTL rule is a design constraint for future implementation only.

---

## 10. Token Single-Use Strategy

### 10.1 Single-Use Rules

| Rule | Description |
|------|-------------|
| Token consumption | A token is consumed before or atomically with pre-execution audit readiness |
| Reuse prevention | A consumed token cannot be reused |
| Reuse result | `confirmation_reused` |
| Reuse blocks before | Handler lookup |

### 10.2 Failure State

| State | Error Code | Decision |
|-------|------------|----------|
| Token reused after consumption | `confirmation_reused` | `blocked_requires_confirmation_token` |

### 10.3 Phase 1G-04-18 Declaration

- No token consumption code is implemented in Phase 1G-04-18.
- No token store mutation is implemented in Phase 1G-04-18.

---

## 11. Token Verification Gate Order

The following gate order is frozen for the future execute route after the Phase 1G-04-17 baseline:

| Gate | Name | Description |
|------|------|-------------|
| 1 | Request shape validation | Validate request JSON structure and required fields |
| 2 | Kill switches | `HERMES_TOOL_EXECUTION_ENABLED` and `HERMES_AGENT_TOOLS_ENABLED` must be exact lowercase `"true"` |
| 3 | Static allowlist | `canonicalName` must be in `STATIC_ALLOWLIST` |
| 4 | Known tool / policy record | Tool must exist in the tool inventory |
| 5 | Denylist / risk-tier disallowance | Tool must not be on STATIC_DENYLIST; risk tier must be eligible |
| 6 | `dryRunRequestId` present | Execute request must reference a prior dry-run |
| 7 | Dry-run historical lookup | Retrieve the prior dry-run decision from dev-only audit storage |
| 8 | Dry-run decision must be `would_allow` | The referenced dry-run must have decided `would_allow` |
| 9 | Dry-run `auditWritten` must be true | The referenced dry-run must have a written audit event |
| 10 | `canonicalName` binding | Execute `canonicalName` must match the dry-run `canonicalName` |
| 11 | `riskTier` binding | Execute `riskTier` must match the dry-run `riskTier` |
| 12 | `policyVersion` binding | Execute `policyVersion` must match the dry-run `policyVersion` |
| 13 | `dryRunDecisionDigest` / arguments digest binding | Digest must match when available |
| 14 | `confirmationToken` present | Execute request must include a confirmation token |
| 15 | Token lookup by `tokenHash` | Hash the raw token and look up the token record |
| 16 | Token exists | Token record must be found in the token store |
| 17 | Token not expired | Token must be within its TTL |
| 18 | Token not consumed | Token must not have been previously used |
| 19 | Token `dryRunRequestId` binding | Token must reference the same dry-run request |
| 20 | Token `dryRunDecisionDigest` binding | Token digest must match |
| 21 | Token `canonicalName` binding | Token canonical name must match |
| 22 | Token `riskTier` binding | Token risk tier must match |
| 23 | Token `policyVersion` binding | Token policy version must match |
| 24 | Token `auditEventId` binding | Token audit event must match (when available) |
| 25 | Token `argumentsDigest` binding | Token arguments digest must match (when available) |
| 26 | Token consume readiness | Token is eligible for consumption |
| 27 | Digest verification readiness | Full digest chain is consistent |
| 28 | Pre-execution audit readiness | Pre-execution audit is writable |
| 29 | Handler lookup eligibility | All previous gates passed; handler may be looked up |

### 11.1 Gate Order Declaration

Phase 1G-04-18 **only freezes this order**. No new gates are implemented in this phase.

---

## 12. Token Failure Contract

### 12.1 Failure States

| Error Code | Description |
|------------|-------------|
| `confirmation_missing` | No `confirmationToken` provided |
| `confirmation_not_implemented` | Token verification is not yet implemented (current baseline) |
| `confirmation_invalid` | Token does not match any stored token hash |
| `confirmation_not_found` | Token hash not found in the token store |
| `confirmation_expired` | Token past its TTL |
| `confirmation_reused` | Token was already consumed |
| `confirmation_dry_run_mismatch` | Token `dryRunRequestId` does not match the execute request |
| `confirmation_digest_mismatch` | Token `dryRunDecisionDigest` does not match |
| `confirmation_canonical_name_mismatch` | Token `canonicalName` does not match |
| `confirmation_risk_tier_mismatch` | Token `riskTier` does not match |
| `confirmation_policy_version_mismatch` | Token `policyVersion` does not match |
| `confirmation_audit_event_mismatch` | Token `auditEventId` does not match |
| `confirmation_arguments_mismatch` | Token `argumentsDigest` does not match |
| `confirmation_store_unavailable` | Token store is temporarily unavailable |
| `confirmation_consume_failed` | Token consumption failed (store write error) |

### 12.2 Failure Invariants

All token failures block **before handler lookup**.

All token failures keep:

| Flag | Value |
|------|-------|
| `executionAllowed` | `false` |
| `dispatchAllowed` | `false` |
| `providerSchemaAllowed` | `false` |
| `toolHandlerCalled` | `false` |
| `providerApiCalled` | `false` |
| `executionStarted` | `false` |

---

## 13. Token Audit Strategy

### 13.1 Token Issuance Audit

Future token issuance audit should record:

| Field | Description |
|-------|-------------|
| `tokenId` | Unique token identifier |
| `tokenHash` prefix or hash id only | Never the raw token |
| `dryRunRequestId` | Bound dry-run request |
| `dryRunDecisionDigest` | Bound digest |
| `canonicalName` | Bound tool name |
| `riskTier` | Bound risk tier |
| `policyVersion` | Bound policy version |
| `auditEventId` | Bound audit event |
| `argumentsDigest` | Bound arguments digest |
| `issuedAt` | Issuance timestamp |
| `expiresAt` | Expiry timestamp |
| `status` | Token status at issuance |

### 13.2 Token Verification Audit

Future token verification audit should record:

| Field | Description |
|-------|-------------|
| `tokenId` | Token identifier |
| `result` | Verification result (pass / fail) |
| `failure reason` | Error code if failed |
| `consumedAt` | Consumption timestamp if consumed |

### 13.3 Audit Prohibitions

The following must **never** appear in any audit record:

- Raw `confirmationToken`
- Raw secrets
- Raw arguments
- Provider credentials
- Cookies
- Authorization headers

### 13.4 Phase 1G-04-18 Declaration

- No token audit implementation in Phase 1G-04-18.

---

## 14. Digest Verification Boundary

### 14.1 Token vs. Digest Separation

Confirmation token verification and digest verification are **separate concerns**:

| Concern | Responsibility |
|---------|----------------|
| **Token verification** | Checks that the token belongs to the same dry-run and recorded digest fields |
| **Digest verification** | Independently verifies that the current execute request still matches the reviewed sanitized request |

### 14.2 Ordering

Token verification happens before digest verification in the gate order (Gates 14–26 vs. Gate 27).

### 14.3 Independence

A valid confirmation token does **not** replace digest verification. Digest verification remains future work after token scope.

### 14.4 Phase 1G-04-18 Declaration

- No digest verification implementation in Phase 1G-04-18.

---

## 15. Execute Route Behavior Delta

### 15.1 Current Baseline

- Dry-run historical lookup implemented (Phase 1G-04-16)
- Production path guard hardened (Phase 1G-04-17)
- Confirmation token not implemented
- Execute route blocked at `confirmation_not_implemented` / token boundary
- No handler lookup
- No dispatch
- No execution

### 15.2 Future Implementation

- Confirmation token may be issued by a dev-only confirmation flow (Option A or B from Section 4.2)
- Execute route may verify token existence, TTL, single-use, and bindings
- Execute route may **still remain blocked** after token verification until digest and audit readiness are implemented
- Handler lookup remains forbidden unless a later explicit phase enables it

### 15.3 Key Principle

**Token implementation does not imply real execution.**

**Token verification does not imply real execution.**

A valid token is one more gate passed — not a green light for handler lookup, dispatch, or execution.

---

## 16. Route Governance Strategy

### 16.1 Phase 1G-04-18

No route governance count change.

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### 16.2 Future Route Strategy

**Preferred future strategy:** Avoid adding routes if token issuance can be modeled within the existing dry-run flow (Option A from Section 4.2).

If a new token issuance endpoint is later required (Option B), it must be:
- Separately scoped in a new scope document
- Route-governed with explicit count change approval
- Tool write routes must remain 0 unless explicitly approved in a future phase

---

## 17. Future OpenAPI Strategy

### 17.1 Phase 1G-04-18

No OpenAPI change.

### 17.2 Future OpenAPI Refinements

Future token implementation may refine existing schemas:

| Schema | Possible Refinement |
|--------|---------------------|
| `ToolDryRunRequest` | Add `issueConfirmationToken` flag (Option A) |
| `ToolDryRunResponse` | Add `confirmationToken` field when issued |
| `ToolExecuteRequest.confirmationToken` | Tighten description for real single-use semantics |
| `ToolExecuteData.gateStatus` | Token gate richer status |
| `ToolExecuteErrorCode` | Add `confirmation_expired`, `confirmation_reused`, and other token error codes |

Any future OpenAPI change must keep path count stable at **33** unless a new route is explicitly approved.

---

## 18. Future Allowed Files

The following files may be modified in future token implementation phases. **They are not modified in Phase 1G-04-18.**

### 18.1 Existing Backend Files

```
hermes_cli/dev_web_tool_execute.py
hermes_cli/dev_web_tool_execute_preflight.py
hermes_cli/dev_web_tool_dry_run.py
hermes_cli/dev_web_tool_dry_run_audit.py
hermes_cli/dev_web_api.py
```

### 18.2 Optional New Modules

```
hermes_cli/dev_web_tool_execute_confirmation.py
```

### 18.3 Test Files

```
tests/test_dev_web_tool_execute.py
tests/test_dev_web_tool_execute_api.py
tests/test_dev_web_tool_execute_preflight.py
tests/test_dev_web_tool_execute_confirmation.py
tests/test_dev_web_tool_dry_run.py
tests/test_dev_web_tool_dry_run_api.py
tests/test_dev_web_tool_dry_run_audit.py
tests/test_dev_check_webui.py
tests/test_dev_web_0c06_closure.py
```

### 18.4 Documentation Files

```
docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md
docs/webui/phase-1-implementation-plan.md
```

### 18.5 Declaration

These are **future allowed files only.** They are **not** modified in Phase 1G-04-18.

---

## 19. Future Forbidden Files

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
```

---

## 20. Future Test Matrix

The following tests must pass when token implementation arrives. **None are added in this phase.**

### 20.1 Token Issuance Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Token not issued when dry-run decision is not `would_allow` | No token issued |
| 2 | Token not issued when `auditWritten` is false | No token issued |
| 3 | Token not issued when `dryRunRequestId` missing | No token issued |
| 4 | Token not issued when `dryRunDecisionDigest` missing | No token issued |
| 5 | Token issued only for `clarify` when allowlisted and gate-eligible | Token issued |
| 6 | Raw token returned once only | Single return |
| 7 | Token store contains `tokenHash` not raw token | No raw token in store |
| 8 | Token store is dev-only | Dev path only |
| 9 | Token store path cannot be production | Blocked |
| 10 | Token TTL ≤ dry-run TTL | Within bounds |

### 20.2 Token Verification Tests

| # | Test | Expected |
|---|------|----------|
| 11 | Missing token blocks | `confirmation_missing` |
| 12 | Invalid token blocks | `confirmation_invalid` |
| 13 | Token not found blocks | `confirmation_not_found` |
| 14 | Expired token blocks | `confirmation_expired` |
| 15 | Reused token blocks | `confirmation_reused` |
| 16 | `dryRunRequestId` mismatch blocks | `confirmation_dry_run_mismatch` |
| 17 | `dryRunDecisionDigest` mismatch blocks | `confirmation_digest_mismatch` |
| 18 | `canonicalName` mismatch blocks | `confirmation_canonical_name_mismatch` |
| 19 | `riskTier` mismatch blocks | `confirmation_risk_tier_mismatch` |
| 20 | `policyVersion` mismatch blocks | `confirmation_policy_version_mismatch` |
| 21 | `auditEventId` mismatch blocks | `confirmation_audit_event_mismatch` |
| 22 | `argumentsDigest` mismatch blocks | `confirmation_arguments_mismatch` |
| 23 | Token store unavailable blocks | `confirmation_store_unavailable` |
| 24 | Consume failure blocks | `confirmation_consume_failed` |

### 20.3 Safety Invariant Tests

| # | Test | Expected |
|---|------|----------|
| 25 | All token failures block before handler lookup | `toolHandlerCalled=false` |
| 26 | All token failures keep side-effect flags false | All flags `false` |
| 27 | Provider never called on token failure | `providerApiCalled=false` |
| 28 | Dispatch never called on token failure | `dispatchAllowed=false` |
| 29 | Execution never started on token failure | `executionStarted=false` |
| 30 | Valid token still blocks if digest verification not implemented | Blocked |
| 31 | Valid token still blocks if pre-execution audit not implemented | Blocked |

### 20.4 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 32 | OpenAPI paths remain 33 unless explicitly changed | 33 |
| 33 | Runtime routes remain 33 unless explicitly changed | 33 |
| 34 | Tool write routes remain 0 | 0 |
| 35 | Tool execution routes remain 1 | 1 |
| 36 | STATIC_ALLOWLIST remains `{"clarify"}` | `frozenset({"clarify"})` |

---

## 21. Entry Criteria for Future Token Implementation

Before confirmation token implementation may begin, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-18 docs pushed |
| 2 | No P0/P1 open |
| 3 | User explicitly approves token implementation |
| 4 | `STATIC_ALLOWLIST` remains exactly `{"clarify"}` |
| 5 | Execute route remains blocked-only before implementation |
| 6 | Dry-run historical lookup is stable |
| 7 | Production path guard is containment-based |
| 8 | Route governance green |
| 9 | Execute tests green |
| 10 | Dry-run tests green |
| 11 | Production gateway stable |
| 12 | compileall PASS |
| 13 | ruff PASS |
| 14 | memory-check PASS |
| 15 | dev-check PASS |

---

## 22. Exit Criteria for Future Token Implementation

After confirmation token implementation, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Confirmation token issued only after eligible dry-run |
| 2 | Raw token returned once |
| 3 | Raw token is not stored |
| 4 | `tokenHash` is stored dev-only |
| 5 | Token TTL enforced |
| 6 | Token single-use enforced |
| 7 | Expired token blocks |
| 8 | Reused token blocks |
| 9 | Token binding mismatch blocks |
| 10 | Token verification failure blocks before handler lookup |
| 11 | Valid token does not execute tools by itself |
| 12 | Valid token still requires digest verification and pre-execution audit readiness |
| 13 | No blocked path calls handler |
| 14 | No blocked path dispatches |
| 15 | No blocked path executes |
| 16 | No blocked path calls provider |
| 17 | OpenAPI paths remain governed |
| 18 | Tool write routes remain 0 unless explicitly approved |
| 19 | Tool execution routes remain 1 |
| 20 | Production gateway unaffected |

---

## 23. Acceptance Criteria for Phase 1G-04-18

| # | Criterion |
|---|-----------|
| 1 | Docs-only |
| 2 | New confirmation token scope doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | Phase 1G-04-17 doc optionally cross-referenced |
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
| 17 | No token TTL implementation |
| 18 | No token single-use consumption implementation |
| 19 | No digest verification implementation |
| 20 | No pre-execution audit |
| 21 | No post-execution audit |
| 22 | No handler lookup |
| 23 | No Tool Handler call |
| 24 | No dispatch |
| 25 | No execution |
| 26 | No Provider Schema |
| 27 | No Provider API |
| 28 | OpenAPI paths = 33 |
| 29 | Runtime routes = 33 |
| 30 | Tool GET = 4 |
| 31 | Tool write = 0 |
| 32 | Tool dry-run = 1 |
| 33 | Tool execution = 1 |
| 34 | Execute route remains blocked-only |
| 35 | Real Controlled Execution not started |
| 36 | Local docs-only commit created |
| 37 | Not pushed |

---

## 24. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code changes introduced | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Execute route behavior changed | Verify diff; reject if execute runtime changed |
| 6 | Confirmation token implemented | Verify diff; reject if token code added |
| 7 | Token verification implemented | Verify diff; reject if verification code added |
| 8 | Token store implemented | Verify diff; reject if token store created |
| 9 | Digest verification implemented | Verify diff; reject if digest code added |
| 10 | Tool Handler called | Verify no handler invocation; reject if found |
| 11 | Provider API called / Schema sent | Verify no provider calls; reject if found |
| 12 | STATIC_ALLOWLIST modified | Verify unchanged; reject if modified |
| 13 | Real secret leaked | Content search; reject if found |
| 14 | Tool write routes > 0 | Verify route governance; reject if changed |
| 15 | Tool execution routes ≠ 1 | Verify route governance; reject if changed |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-18 Failed."**

---

## 25. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Confirmation token goal missing | Verify Section 3 |
| 2 | Issuance source missing | Verify Section 4 |
| 3 | Token binding contract missing | Verify Section 5 |
| 4 | Token payload strategy missing | Verify Section 6 |
| 5 | Token hash strategy missing | Verify Section 7 |
| 6 | Token store strategy missing | Verify Section 8 |
| 7 | TTL strategy missing | Verify Section 9 |
| 8 | Single-use strategy missing | Verify Section 10 |
| 9 | Verification gate order missing | Verify Section 11 |
| 10 | Failure contract missing | Verify Section 12 |
| 11 | Audit strategy missing | Verify Section 13 |
| 12 | Digest boundary missing | Verify Section 14 |
| 13 | Route governance strategy missing | Verify Section 16 |
| 14 | Future OpenAPI strategy missing | Verify Section 17 |
| 15 | Future allowed files missing | Verify Section 18 |
| 16 | Future forbidden files missing | Verify Section 19 |
| 17 | Future test matrix missing | Verify Section 20 |
| 18 | Entry criteria missing | Verify Section 21 |
| 19 | Exit criteria missing | Verify Section 22 |
| 20 | Docs incorrectly claim token implemented | Content review |
| 21 | Docs incorrectly claim token verified | Content review |
| 22 | Docs incorrectly claim token store implemented | Content review |
| 23 | Route governance failed | Run tests; verify counts |
| 24 | OpenAPI paths ≠ 33 | Verify count |
| 25 | Runtime routes ≠ 33 | Verify count |
| 26 | Tool GET ≠ 4 | Verify count |
| 27 | Tool write ≠ 0 | Verify count |
| 28 | Tool dry-run ≠ 1 | Verify count |
| 29 | Tool execution ≠ 1 | Verify count |
| 30 | STATIC_ALLOWLIST ≠ `{"clarify"}` | Verify value |
| 31 | compileall failed | Run compileall |
| 32 | ruff failed | Run ruff |
| 33 | memory-check failed | Run memory-check |
| 34 | dev-check failed | Run dev-check |
| 35 | Worktree has unexpected files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 26. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Confirmation token issuance / verification not yet implemented | Expected — scope freeze only |
| 2 | Token store not yet implemented | Expected — scope freeze only |
| 3 | Token TTL not yet implemented | Expected — scope freeze only |
| 4 | Token single-use consumption not yet implemented | Expected — scope freeze only |
| 5 | Digest verification not yet implemented | Expected — scope freeze only |
| 6 | Pre/post execution audit not yet implemented | Expected — scope freeze only |
| 7 | Execute route still does not execute tools | Expected — blocked-only |
| 8 | Handler lookup not yet enabled | Expected — future phase |
| 9 | Frontend execute UI not implemented | Expected — future phase |
| 10 | Browser smoke not re-run | Expected — no frontend changes |
| 11 | Clarify handler-level audit still needs future phase | Expected — future work |
| 12 | Lookup performance can be optimized later | Expected — optimization deferred |
| 13 | Multi-file audit rotation support may be future work | Expected — deferred |

---

*Phase 1G-04-18 Confirmation Token Issuance / Verification Scope Freeze: confirmation token issuance, verification, storage, TTL, single-use, and dry-run binding design only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no token implementation, no token verification, no token store, no digest verification, no handler lookup, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*
