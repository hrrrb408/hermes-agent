# Phase 1G-04-12: Confirmation Token / Digest Backend Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-12 |
| Title | Confirmation Token / Digest Backend Scope Freeze |
| Status | Frozen (confirmation token and digest binding backend scope definition only, no implementation) |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-12 confirmation token / digest backend scope freeze) |
| Dependencies | Phase 1G-04-11 completed and committed locally |
| Branch | dev-huangruibang |
| Base commit | `3c9220978448d5c5f728f3bf51764378654065ab` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future confirmation token backend scope
2. Freezes the future argument-digest binding backend scope
3. Defines the confirmation token goal
4. Defines the digest binding goal
5. Defines the future token lifecycle
6. Defines the future token payload draft
7. Defines the future token storage strategy
8. Defines the future token expiry and replay-prevention strategy
9. Defines the future digest canonicalization strategy
10. Defines the digest mismatch contract
11. Defines the dry-run preflight binding contract
12. Defines the audit binding contract
13. Defines the future execute route behavior delta
14. Defines the future API / OpenAPI strategy
15. Defines the future allowed files
16. Defines the future forbidden files
17. Defines the future test matrix
18. Defines the entry criteria for future token / digest implementation
19. Defines the exit criteria for future token / digest implementation
20. Does **not** implement confirmation token issuance
21. Does **not** implement confirmation token verification
22. Does **not** implement a token store
23. Does **not** implement digest verification
24. Does **not** modify execute route behavior
25. Does **not** modify OpenAPI
26. Does **not** add runtime routes
27. Does **not** implement real Controlled Execution
28. Does **not** call tool handlers
29. Does **not** call providers
30. Does **not** execute tools

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-12 = **Confirmation Token / Digest Backend Scope Freeze**

- This phase freezes the future confirmation token and digest binding backend scope.
- This phase does **not** implement confirmation token issuance.
- This phase does **not** implement confirmation token verification.
- This phase does **not** implement digest verification.
- This phase does **not** modify execute route behavior.
- This phase does **not** modify OpenAPI.
- This phase does **not** add runtime routes.
- This phase does **not** implement real Controlled Execution.
- This phase does **not** call tool handlers.
- This phase does **not** call providers.
- This phase does **not** execute tools.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `3c9220978448d5c5f728f3bf51764378654065ab` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| Dry-Run API | Implemented (`POST /api/dev/v1/tools/dry-run`) |
| Dry-Run Audit Writer | Implemented (`dev_web_tool_dry_run_audit.py`) |
| Execute Route | Implemented as blocked-only (`dev_web_tool_execute.py`, Phase 1G-04-11) |
| Execute gate skeleton | Blocked-only; every request blocks before handler lookup |
| Confirmation token issuance | Not implemented (gate checks presence only) |
| Confirmation token verification | Not implemented |
| Token store | Not implemented |
| Digest verification | Not implemented (gate accepts any non-empty digest) |
| Dry-run historical lookup | Not implemented |
| Pre-execution audit | Not implemented (skeleton `auditAttempted=false`) |
| Post-execution audit | Not implemented |
| STATIC_ALLOWLIST | Empty (empty frozenset) |
| Provider Schema Sending | Not sent |
| Tool Dispatch | 0 |
| Tool Handler Invocation | None |
| Tool Execution | Disabled |
| Kill Switches | All disabled (unset) |
| Controlled Execution implementation | Not really started |
| Production Gateway PID | 80468 |

### 2.1 Current Execute Gate Behavior (Phase 1G-04-11 baseline)

The execute gate evaluates the following ordered gates and returns a blocked result at the
first failure. None of these gates may invoke a tool handler.

| Gate | Current Phase 1G-04-11 Behavior |
|------|----------------------------------|
| `kill_switch` | Unset → `blocked_by_kill_switch` |
| `agent_tools` | Unset → `blocked_by_kill_switch` |
| `static_allowlist` | Empty → `blocked_by_allowlist` |
| `known_tool` | Unknown → `blocked` (`tool_unknown`) |
| `denylist` | Denylisted → `blocked_by_denylist` |
| `risk_tier` | R2+ → `blocked_by_risk_tier` |
| `dry_run_preflight` | Missing `dryRunRequestId` / `dryRunDecisionDigest` → `blocked_requires_dry_run` |
| `digest` | **Skeleton** — accepts any non-empty digest; real verification deferred |
| `confirmation` | **Skeleton** — checks presence only; no issuance, no verification |

Even when every gate passes, the skeleton still blocks with `decision=blocked`,
`errorCode=execution_not_implemented`, and **all** execution flags false.

| Invariant Flag | Phase 1G-04-11 Value |
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

The confirmation token is the **human-confirmation proof** required before any future tool
handler lookup. It is the cryptographic receipt that a human reviewed and approved a specific
dry-run outcome.

### 3.1 Core Goals

1. **Proof of human confirmation.** The token proves a human explicitly confirmed a reviewed dry-run outcome.
2. **Generated only after dry-run preflight.** A token must never be issued before a successful dry-run preflight.
3. **Strongly bound.** The token must bind to `canonicalName`, arguments digest, risk tier, dry-run decision, dry-run audit event, `requestId`, and a timestamp.
4. **Single-use.** A token may authorize at most one execute attempt.
5. **Short-lived.** A token must expire quickly (recommended ≤ 5 minutes).
6. **Secret-free.** A token must never contain raw secrets.
7. **Never sufficient.** A token must never enable execution by itself.

### 3.2 Necessary but Never Sufficient

A confirmation token is **necessary but never sufficient**. Even with a valid token, the
following still apply on every execute request:

| Control | Still Applies |
|---------|---------------|
| Kill switches | Yes — must be exactly `"true"` |
| STATIC_ALLOWLIST | Yes — tool must be present |
| STATIC_DENYLIST | Yes — tool must not be present |
| Risk tier | Yes — tier must be eligible |
| Dry-run preflight | Yes — must reference valid `would_allow` |
| Dry-run audit | Yes — `auditWritten` must be `true` |
| Digest match | Yes — arguments digest must match |
| Pre-execution audit | Yes — must succeed (blocks on failure) |
| Handler lookup | Yes — handler must be available |

A valid token only proves human confirmation. It does **not** bypass any gate, does **not**
populate the allowlist, and does **not** authorize a tool that any other gate rejects.

---

## 4. Digest Binding Goal

The argument digest binds a future execute request to a previously reviewed dry-run request.
It is the anti-substitution guarantee between confirmation and execution.

### 4.1 Core Goals

| Goal | Description |
|------|-------------|
| Bind to dry-run | Digest binds the execute request to a previously reviewed dry-run request |
| Prevent argument swapping | Arguments cannot be changed after human confirmation |
| Prevent canonicalName substitution | Tool name cannot be swapped after confirmation |
| Prevent stale dry-run reuse | An expired or superseded dry-run cannot authorize execution |
| Prevent confirmation hijack | A token issued for one request cannot authorize a different request |

### 4.2 Digest Properties

1. **Computed from normalized and sanitized data.** Raw arguments are never digested directly.
2. **Never includes raw secrets.** Secret-looking values are redacted before digesting.
3. **Stable for semantically identical safe arguments.** Canonical JSON produces a deterministic digest.
4. **Rejects mismatches before handler lookup.** A mismatch blocks before any handler, provider, or dispatch call.

---

## 5. Non-Goals

The following are explicitly **not** part of Phase 1G-04-12:

1. No confirmation token issuance implemented
2. No confirmation token verification implemented
3. No token store implemented
4. No digest verification implemented
5. No dry-run historical lookup implemented
6. No pre-execution audit implemented
7. No post-execution audit implemented
8. No execute route behavior change
9. No OpenAPI change
10. No new route added
11. No route governance modification
12. No Tool Handler call
13. No tool execution
14. No Provider API call
15. No Provider Schema sent
16. No STATIC_ALLOWLIST modification
17. No frontend UI added
18. No audit read API added
19. No audit viewer added
20. No code changes of any kind

---

## 6. Future Token Lifecycle

The following lifecycle is **frozen** as the future flow. **No step is implemented in this phase.**

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Performs a dry-run request |
| 2 | Backend | Dry-run returns sanitized arguments and `auditWritten` status |
| 3 | Backend | Computes the dry-run decision digest |
| 4 | UI | Displays `canonicalName`, risk tier, sanitized arguments, policy notes, and digest summary |
| 5 | User | Explicitly confirms |
| 6 | Backend | Issues a confirmation token |
| 7 | Backend | Token is bound to the dry-run digest and audit event |
| 8 | User | Submits execute request carrying the token and digest |
| 9 | Backend | Verifies the token |
| 10 | Backend | Verifies the digest |
| 11 | Backend | Verifies all gates again |
| 12 | Backend | Only after all gates pass may future handler lookup occur |

### 6.1 Lifecycle Declaration

Phase 1G-04-12 only **freezes** this lifecycle. No lifecycle step is implemented in this phase.
Steps 6–12 are all future work and require explicit user approval before implementation.

---

## 7. Token Payload Draft

The following is the future `ConfirmationTokenPayload` draft. It is a design draft only.

### 7.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Token payload schema version |
| `tokenId` | string | Unique token identifier (opaque, non-secret) |
| `requestId` | string | Original dry-run request correlation ID |
| `canonicalName` | string | Exact tool canonical name |
| `riskTier` | string | Tool risk tier (e.g. `R0`, `R1`) |
| `policyVersion` | string | Policy version the decision was made against |
| `dryRunRequestId` | string | Dry-run request correlation ID |
| `dryRunDecision` | string | Must be `would_allow` |
| `dryRunDecisionDigest` | string | SHA-256 digest of the dry-run decision input |
| `dryRunAuditEventId` | string | Audit event ID from the dry-run audit write |
| `argumentsDigest` | string | SHA-256 digest of sanitized arguments |
| `issuedAt` | string | ISO 8601 UTC issuance timestamp |
| `expiresAt` | string | ISO 8601 UTC expiry timestamp |
| `singleUse` | boolean | Must be `true` |
| `issuer` | string | Issuing component identifier |

> `policyVersion` is a **future** field. No `policyVersion` constant exists in the codebase
> today; introducing it is part of the future token / digest implementation, not this phase.

### 7.2 Prohibited Token Content

The token payload must **never** include:

- Raw arguments
- Raw secrets
- Provider keys
- Cookies
- Authorization headers
- Stack traces
- Internal file paths
- Callable references

The token is an opaque, non-secret proof. It carries binding metadata only. The raw token
secret (if any signing material is used) must never be persisted, logged, or audited.

---

## 8. Token Storage Strategy

The future token store must be **dev-only and ephemeral**. The following strategy is frozen.

### 8.1 Storage Constraints

| Constraint | Requirement |
|------------|-------------|
| Scope | Dev-only |
| Lifetime | Ephemeral — restart invalidates outstanding tokens |
| Production state.db | **Must not** use production `state.db` |
| `~/.hermes` | **Must not** use `~/.hermes` |
| Git | **Must not** be committed to git |
| Persistence of raw secrets | Forbidden |
| Persistence of raw arguments | Forbidden |

### 8.2 Recommended Location

If file-backed, the store may use a dev-only path such as:

```
$HERMES_HOME/gateway/dev/runtime/controlled-execution-confirmations.jsonl
```

or an **in-memory** dev-only store in a later phase.

### 8.3 Storage Selection Principle

| Option | Rule |
|--------|------|
| File-backed | Store only hashed token identifiers and metadata — never the raw token secret |
| In-memory | Restart invalidates all outstanding tokens |
| Either | No raw token secrets, no raw arguments, no raw secrets persisted |

### 8.4 Phase 1G-04-12 Declaration

**No token store file is created in Phase 1G-04-12.** The path above is a future
recommendation only. No file under `$HERMES_HOME/gateway/dev/runtime/` is created, read, or
written by this phase.

---

## 9. Token Expiry and Replay Prevention

### 9.1 Expiry and Single-Use Rules

| Rule | Value |
|------|-------|
| Recommended expiry | ≤ 5 minutes |
| Use count | Single-use only |
| Token reuse result | `confirmation_reused` |
| Expired token result | `confirmation_expired` |
| Invalid token result | `confirmation_invalid` |
| Missing token result | `confirmation_missing` |
| After successful execute attempt | Token invalidated |
| After failed verification | May be invalidated per future implementation policy |

### 9.2 Replay Prevention Ordering

**Replay prevention must happen before Tool Handler lookup.** A reused, expired, or invalid
token must block at the confirmation gate — before digest verification, before handler lookup,
before dispatch, and before any provider call.

### 9.3 Error Code Mapping

| Condition | Error Code | Decision |
|-----------|------------|----------|
| No token provided | `confirmation_missing` | `blocked_requires_confirmation` |
| Token does not match | `confirmation_invalid` | `blocked_requires_confirmation` |
| Token past expiry | `confirmation_expired` | `blocked_requires_confirmation` |
| Token already used | `confirmation_reused` | `blocked_requires_confirmation` |

> `confirmation_expired` and `confirmation_reused` are **future** error codes. They are not
> present in the current `ToolExecuteErrorCode` enum. Adding them is part of the future
> implementation, not this phase. See Section 15.

---

## 10. Digest Canonicalization Strategy

### 10.1 Normalized Digest Input

The future digest is computed over a normalized input object:

```
NormalizedExecuteDigestInput:
  - canonicalName
  - riskTier
  - policyVersion
  - dryRunDecision
  - sanitizedArgumentsPreview
  - dryRunRequestId
  - dryRunAuditEventId
```

### 10.2 Digest Algorithm

```
sha256(canonical_json(NormalizedExecuteDigestInput))
```

### 10.3 `canonical_json` Requirements

| Requirement | Description |
|-------------|-------------|
| Encoding | UTF-8 |
| Object keys | Sorted |
| Number representation | Stable |
| Whitespace | No insignificant whitespace |
| List ordering | Stable (insertion-preserving) |
| Redacted values | Remain redacted |
| Forbidden fields | Excluded or replaced with redaction markers |

### 10.4 Canonicalization Invariants

1. **Raw arguments are never used directly.** The sanitized / redacted argument preview is used.
2. **Secret-looking values are redacted before digesting.** The digest never spans a raw secret.
3. **The digest is deterministic.** Semantically identical safe inputs produce identical digests.
4. **`policyVersion` participates in the digest.** A policy change invalidates prior digests.

---

## 11. Digest Mismatch Contract

### 11.1 Hard Contract

A digest mismatch **blocks before handler lookup**.

| Field | Value on Mismatch |
|-------|-------------------|
| `decision` | `blocked_by_digest_mismatch` |
| `errorCode` | `digest_mismatch` |
| `toolHandlerCalled` | `false` |
| `executionStarted` | `false` |
| `executionAttempted` | `false` |
| `providerApiCalled` | `false` |
| `dispatchAllowed` | `false` |

### 11.2 Common Mismatch Causes

A digest mismatch is returned when any bound field changed between the reviewed dry-run and
the execute request:

| Cause | Description |
|------|-------------|
| `canonicalName` changed | Tool name swapped |
| `arguments` changed | Sanitized arguments differ |
| `riskTier` changed | Risk tier differs |
| `dryRunDecision` changed | Decision differs |
| `dryRunRequestId` changed | Referenced a different dry-run |
| `dryRunAuditEventId` changed | Referenced a different audit event |
| `policyVersion` changed | Policy was updated |
| Expired dry-run reference | Dry-run preflight is stale |

### 11.3 No Side Effects on Mismatch

A digest mismatch performs **no** handler call, **no** provider call, **no** dispatch, and
**no** execution. It returns a JSON-safe blocked response.

---

## 12. Dry-Run Preflight Binding

### 12.1 Binding Requirements

Every future execute request must reference a prior dry-run decision.

| Requirement | Description |
|-------------|-------------|
| `dryRunRequestId` | Must reference a valid prior dry-run request |
| Dry-run decision | Must be `would_allow` |
| `auditWritten` | Must be `true` |
| Forbidden argument fields | Dry-run result must have none |
| Sanitized arguments match digest | Dry-run sanitized arguments must match digest input |
| Dry-run reference not expired | Recommended ≤ 5 minutes |

### 12.2 Current Boundary Preserved

- The current execute route remains **blocked-only**.
- The current **dry-run historical lookup is not implemented** in Phase 1G-04-12. The execute
  gate requires `dryRunRequestId` and `dryRunDecisionDigest` to be present, but does not look
  up or verify the referenced dry-run.

---

## 13. Audit Binding

### 13.1 Binding Rules

| Rule | Description |
|------|-------------|
| Token binds to audit event | The confirmation token must bind to the dry-run audit event ID (`dryRunAuditEventId`) |
| Pre-execution audit includes token id/hash | Future pre-execution audit must include the confirmation token id or token hash |
| Pre-execution audit includes digest | Future pre-execution audit must include the digest |
| Post-execution audit includes token id/hash | Future post-execution audit must include the token id or token hash |
| No raw token secret in audit | Audit must never store the raw token secret |
| No raw arguments in audit | Audit must never store raw arguments |

### 13.2 Phase 1G-04-12 Declaration

**No audit changes are implemented in this phase.** Pre-execution and post-execution audit
remain unimplemented (`auditAttempted=false`). Only the binding contract is frozen here.

---

## 14. Future Execute Route Behavior Delta

### 14.1 Current Phase 1G-04-11 Behavior

| Aspect | Phase 1G-04-11 |
|--------|----------------|
| Default decision | Blocked |
| Kill switches unset | Blocked |
| Exact lowercase `"true"` + empty allowlist | Blocked |
| Unknown tool | Blocked |
| Missing dry-run | Blocked |
| Missing confirmation | Blocked |
| Digest verification | Not fully implemented (accepts any non-empty digest) |
| Dry-run historical lookup | Not implemented |
| Token issuance | Not implemented |
| `executionAllowed` | `false` |
| `dispatchAllowed` | `false` |
| `providerSchemaAllowed` | `false` |
| `toolHandlerCalled` | `false` |
| `providerApiCalled` | `false` |
| `executionStarted` | `false` |

### 14.2 Future Token / Digest Backend Behavior

After a future token / digest implementation phase, the execute route **may**:

| Capability | Future |
|------------|--------|
| Validate `confirmationToken` shape | Yes |
| Validate token expiry | Yes |
| Validate token single-use | Yes |
| Validate digest match | Yes |

### 14.3 Still Blocked Even After Token / Digest Implementation

Even after token / digest implementation:

- The route **may remain blocked-only**.
- Token / digest implementation **does not imply handler call**.
- Token / digest implementation **does not imply real execution**.
- All other gates (kill switch, allowlist, denylist, risk tier, dry-run preflight, pre-execution
  audit) still apply independently.

A token / digest backend is a verification layer over the existing blocked-only gate stack. It
does not unlock execution by itself.

---

## 15. Future API / OpenAPI Strategy

### 15.1 Phase 1G-04-12 Declaration

**No OpenAPI change is made in Phase 1G-04-12.** The OpenAPI file is not modified.

### 15.2 Future OpenAPI Refinements

Future token / digest implementation **may** refine the existing execute schemas. No new path
is required. Potential refinements:

| Schema | Possible Refinement |
|--------|---------------------|
| `ToolExecuteRequest.confirmationToken` | Description tightened to reflect real single-use semantics |
| `ToolExecuteRequest.dryRunDecisionDigest` | Description tightened to reflect canonical-JSON SHA-256 |
| `ToolExecuteData.gateStatus` | Confirm / digest gate richer status |
| `ToolExecuteData.auditStatus` | Pre/post execution audit fields when implemented |
| `ToolExecuteErrorCode` | Add `confirmation_expired`, `confirmation_reused` |

### 15.3 Path Count Invariant

- Any future OpenAPI schema change requires route governance checks.
- The OpenAPI path count should **remain 33** unless a genuinely new path is added. Refining
  existing schemas does **not** change the path count.

---

## 16. Future Allowed Files

The following files **may** be modified in a future token / digest implementation phase. They
are **not** modified in Phase 1G-04-12.

| File | Future Action |
|------|---------------|
| `hermes_cli/dev_web_tool_execute.py` | Modify — add token / digest verification before handler lookup |
| `hermes_cli/dev_web_api.py` | Modify — wire token issuance endpoint if added |
| `docs/webui/openapi/dev-web-api-v1.yaml` | Modify — refine execute schemas (no new path) |
| `tests/test_dev_web_tool_execute.py` | Modify — token / digest unit tests |
| `tests/test_dev_web_tool_execute_api.py` | Modify — token / digest API tests |
| `tests/test_dev_check_webui.py` | Modify — only if route governance expectations change |
| `tests/test_dev_web_0c06_closure.py` | Modify — only if route governance expectations change |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Modify — completion records |
| `docs/webui/phase-1-implementation-plan.md` | Modify — phase status |

If a future phase needs an independent token module, it may add:

| File | Future Action |
|------|---------------|
| `hermes_cli/dev_web_tool_execute_confirmation.py` | New — token issuance / verification module |
| `tests/test_dev_web_tool_execute_confirmation.py` | New — token module tests |

### 16.1 Declaration

These are **future allowed files only.** They are not modified in Phase 1G-04-12.

---

## 17. Future Forbidden Files

The following files must **not** be modified during future token / digest implementation:

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

## 18. Test Matrix for Future Token / Digest Backend

The following tests must pass when token / digest implementation arrives. **None are added in
this phase.**

### 18.1 Token Issuance Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Token not issued before dry-run | No token |
| 2 | Token not issued when dry-run decision is not `would_allow` | No token |
| 3 | Token not issued when dry-run `auditWritten` is `false` | No token |
| 4 | Token payload excludes raw arguments | No raw arguments |
| 5 | Token payload excludes secrets | No secrets |

### 18.2 Token Lifecycle Tests

| # | Test | Expected |
|---|------|----------|
| 6 | Token expires within configured TTL | `confirmation_expired` |
| 7 | Expired token blocks | `blocked_requires_confirmation` |
| 8 | Missing token blocks | `confirmation_missing` |
| 9 | Invalid token blocks | `confirmation_invalid` |
| 10 | Reused token blocks | `confirmation_reused` |

### 18.3 Token Binding Tests

| # | Test | Expected |
|---|------|----------|
| 11 | Token bound to `canonicalName` | Swap blocks |
| 12 | Token bound to `riskTier` | Swap blocks |
| 13 | Token bound to `dryRunRequestId` | Swap blocks |
| 14 | Token bound to `dryRunDecisionDigest` | Swap blocks |
| 15 | Token bound to `dryRunAuditEventId` | Swap blocks |

### 18.4 Digest Tests

| # | Test | Expected |
|---|------|----------|
| 16 | Argument digest stable for canonical JSON | Identical digests |
| 17 | Digest changes when sanitized arguments change | `digest_mismatch` |
| 18 | Digest changes when `canonicalName` changes | `digest_mismatch` |
| 19 | Digest changes when `policyVersion` changes | `digest_mismatch` |
| 20 | Digest mismatch blocks before handler lookup | `blocked_by_digest_mismatch` |

### 18.5 No-Side-Effect Tests

| # | Test | Expected |
|---|------|----------|
| 21 | Handler not called on token failure | `toolHandlerCalled=false` |
| 22 | Handler not called on digest failure | `toolHandlerCalled=false` |
| 23 | Provider not called on token failure | `providerApiCalled=false` |
| 24 | Dispatch not called on token failure | `dispatchAllowed=false` |
| 25 | Execution not started on token failure | `executionStarted=false` |

### 18.6 Audit Safety Tests

| # | Test | Expected |
|---|------|----------|
| 26 | Audit never stores raw token secret | No raw token secret |
| 27 | Audit never stores raw arguments | No raw arguments |

### 18.7 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 28 | OpenAPI route count remains 33 | No new path |
| 29 | Tool execution route count remains 1 | No new execution route |
| 30 | Tool write route count remains 0 | No write route |

---

## 19. Entry Criteria for Future Token / Digest Implementation

The following conditions must be met before any token / digest implementation phase begins:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-12 docs pushed |
| 2 | No P0/P1 open risks |
| 3 | User explicitly approves token / digest implementation |
| 4 | Execute route remains blocked-only |
| 5 | Route governance green |
| 6 | Execute tests green |
| 7 | Dry-run regressions green |
| 8 | Audit writer tests green |
| 9 | Production gateway stable |
| 10 | compileall PASS |
| 11 | ruff PASS |
| 12 | memory-check PASS |
| 13 | dev-check PASS |

---

## 20. Exit Criteria for Future Token / Digest Implementation

The following conditions must be met for token / digest implementation to be considered complete:

| # | Criterion |
|---|-----------|
| 1 | Token issuance implemented only after dry-run `would_allow` |
| 2 | Token verification implemented before handler lookup |
| 3 | Digest verification implemented before handler lookup |
| 4 | Expired / missing / invalid / reused token blocks |
| 5 | Digest mismatch blocks |
| 6 | No blocked path calls handler |
| 7 | No blocked path calls provider |
| 8 | No blocked path dispatches |
| 9 | No blocked path executes |
| 10 | STATIC_ALLOWLIST remains explicit and unchanged unless a separate phase |
| 11 | OpenAPI path count remains 33 unless a new path is added |
| 12 | Tool write routes remain 0 |
| 13 | Tool execution routes remain 1 |
| 14 | Production gateway unaffected |

---

## 21. Acceptance Criteria for Phase 1G-04-12

| # | Criterion |
|---|-----------|
| 1 | docs-only |
| 2 | New confirmation token / digest scope doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | No code changes |
| 6 | No OpenAPI file changes |
| 7 | No tests changed |
| 8 | No frontend changes |
| 9 | No routes changed |
| 10 | OpenAPI paths still 33 |
| 11 | Runtime routes still 33 |
| 12 | Tool GET 4 |
| 13 | Tool write 0 |
| 14 | Tool dry-run 1 |
| 15 | Tool execution 1 |
| 16 | STATIC_ALLOWLIST empty |
| 17 | Execute route remains blocked-only |
| 18 | Tool Handler not called |
| 19 | Tool Dispatch 0 |
| 20 | Tool Execution 0 |
| 21 | Provider Schema not sent |
| 22 | Provider API not called |
| 23 | Controlled Execution not really started |
| 24 | Local docs-only commit created |
| 25 | Not pushed |

---

## 22. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code changes introduced | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Execute route behavior changed | Verify diff; reject if execute runtime changed |
| 6 | Token implementation introduced | Verify diff; reject if token code added |
| 7 | Digest verification implemented | Verify diff; reject if digest code added |
| 8 | Audit read API / viewer added | Verify diff; reject if added |
| 9 | Tool Handler called | Verify no handler invocation; reject if found |
| 10 | Provider API called / Schema sent | Verify no provider calls; reject if found |
| 11 | STATIC_ALLOWLIST modified | Verify empty; reject if populated |
| 12 | Real secret leaked | Content search; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-12 Failed."**

---

## 23. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Scope doc missing confirmation token goal | Verify Section 3 completeness |
| 2 | Scope doc missing digest binding goal | Verify Section 4 completeness |
| 3 | Scope doc missing token lifecycle | Verify Section 6 completeness |
| 4 | Scope doc missing token fields | Verify Section 7 completeness |
| 5 | Scope doc missing token storage strategy | Verify Section 8 completeness |
| 6 | Scope doc missing token expiry / replay prevention | Verify Section 9 completeness |
| 7 | Scope doc missing digest canonicalization strategy | Verify Section 10 completeness |
| 8 | Scope doc missing digest mismatch contract | Verify Section 11 completeness |
| 9 | Scope doc missing dry-run preflight binding | Verify Section 12 completeness |
| 10 | Scope doc missing audit binding | Verify Section 13 completeness |
| 11 | Scope doc missing future execute route behavior delta | Verify Section 14 completeness |
| 12 | Scope doc missing future OpenAPI strategy | Verify Section 15 completeness |
| 13 | Scope doc missing future allowed files | Verify Section 16 completeness |
| 14 | Scope doc missing future forbidden files | Verify Section 17 completeness |
| 15 | Scope doc missing test matrix | Verify Section 18 completeness |
| 16 | Scope doc falsely claims token implemented | Content review |
| 17 | Scope doc falsely claims digest verification implemented | Content review |
| 18 | Route governance failure | Run tests; verify counts |
| 19 | OpenAPI paths not 33 | Verify count |
| 20 | Runtime routes not 33 | Verify count |
| 21 | Tool GET not 4 | Verify count |
| 22 | Tool write not 0 | Verify count |
| 23 | Tool dry-run not 1 | Verify count |
| 24 | Tool execution not 1 | Verify count |
| 25 | memory-check failure | Run memory-check |
| 26 | dev-check failure | Run dev-check |
| 27 | compileall failure | Run compileall |
| 28 | Worktree contains out-of-scope files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 24. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Confirmation token issuance not yet implemented | Expected — scope freeze only |
| 2 | Confirmation token verification not yet implemented | Expected — scope freeze only |
| 3 | Token store not yet implemented | Deferred to future implementation phase |
| 4 | Digest verification not yet implemented | Expected — scope freeze only |
| 5 | Dry-run historical lookup not yet implemented | Deferred to future phase |
| 6 | Pre/post execution audit not yet implemented | Deferred to future phase |
| 7 | Execute route still does not execute tools | Expected — blocked-only skeleton |
| 8 | First executable tool not yet selected | Deferred to Phase 1G-04-13 |
| 9 | STATIC_ALLOWLIST still empty | Expected — requires separate phase |
| 10 | Frontend execute UI not implemented | Deferred to future phase |
| 11 | Browser smoke not re-run | Not required for docs-only change |

---

*Phase 1G-04-12 Confirmation Token / Digest Backend Scope Freeze: confirmation token and digest binding backend scope definition only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no token implementation, no digest verification implementation, no execute route behavior change, no audit read API, no audit viewer, no tool handler call, no provider schema send, no allowlist change, no Controlled Execution started.*
