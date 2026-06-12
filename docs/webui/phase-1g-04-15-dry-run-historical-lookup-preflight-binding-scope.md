# Phase 1G-04-15: Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-15 |
| Title | Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-15 scope freeze) |
| Dependencies | Phase 1G-04-14 completed locally |
| Branch | dev-huangruibang |
| Base commit | `2e60523ecf7d13a845e765c01609aae67d4f74b9` |
| Implementation | Documentation only — no business code modified |

---

## 1. Phase Definition

Phase 1G-04-15 = Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze.

This phase freezes the future dry-run historical lookup and confirmation/digest preflight binding backend scope.

This phase does **not** implement dry-run historical lookup.
This phase does **not** implement confirmation token issuance.
This phase does **not** implement confirmation token verification.
This phase does **not** implement digest verification.
This phase does **not** implement token store.
This phase does **not** modify execute route behavior.
This phase does **not** modify OpenAPI.
This phase does **not** add runtime routes.
This phase does **not** implement real Controlled Execution.
This phase does **not** call tool handlers.
This phase does **not** dispatch tools.
This phase does **not** call providers.
This phase does **not** execute tools.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `2e60523ecf7d13a845e765c01609aae67d4f74b9` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Allowlisted canonicalName | `clarify` |
| Execute Route | Implemented as blocked-only |
| Clarify allowlist gate | Implemented |
| Confirmation Token Scope | Frozen (Phase 1G-04-12) |
| Digest Scope | Frozen (Phase 1G-04-12) |
| Controlled Execution implementation | Not really started |
| Provider Schema | Not sent |
| Tool Handler | Not called |
| Tool Execution | Disabled |

---

## 3. Dry-Run Historical Lookup Goal

Dry-run historical lookup allows the execute preflight gate to retrieve a prior dry-run decision using `dryRunRequestId`.

The lookup must be **read-only**.
The lookup must happen **before handler lookup**.
The lookup must **never execute tools**.
The lookup must **never call providers**.
The lookup must **never mutate audit history**.
The lookup must **never read production state**.

**Lookup is necessary but never sufficient.** A found dry-run record does not enable execution by itself. The record must pass all subsequent binding and token gates before any handler is considered.

---

## 4. Historical Record Source

### 4.1 Primary Future Source

Dev-only dry-run audit JSONL written by the existing audit writer (implemented in Phase 1G-04-07).

**Allowed future path:**

```
$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl
```

Or rotated variants within the same dev-only audit directory, as defined in Phase 1G-04-06 audit storage scope.

### 4.2 Forbidden Sources

- `~/.hermes` (production home)
- Production `state.db`
- Committed runtime files
- Frontend `localStorage`
- Browser cache
- Provider logs
- Any path outside `$HERMES_HOME/gateway/dev/`

### 4.3 Phase 1G-04-15 Does Not

- Implement this reader.
- Create new runtime files.
- Read actual audit records.

---

## 5. Lookup Input Contract

The future lookup function accepts the following inputs:

| Field | Required | Description |
|-------|----------|-------------|
| `dryRunRequestId` | Yes | Unique identifier of the prior dry-run request |
| `canonicalName` | Yes | Tool canonical name — must match the dry-run record |
| `dryRunDecisionDigest` | Yes | SHA-256 digest of the dry-run decision — must match |
| `auditEventId` | No | Optional audit event identifier for cross-referencing |
| `argumentsDigest` | No | Current execute request sanitized arguments digest — for binding verification |
| `policyVersion` | No | Current policy version — must match or fail closed |
| `riskTier` | No | Current risk tier — must match |

### 5.1 Input Rules

- `dryRunRequestId` is **required** for future lookup.
- `dryRunDecisionDigest` is **required** for future binding.
- `canonicalName` must match the dry-run record exactly.
- `riskTier` must match the dry-run record exactly.
- `policyVersion` must match the dry-run record or **fail closed**.

---

## 6. Lookup Output Contract

### 6.1 Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `found` | boolean | Whether a matching dry-run record was found |
| `dryRunRequestId` | string or null | The matched request ID |
| `canonicalName` | string or null | The matched tool canonical name |
| `decision` | string or null | The dry-run decision (`would_allow`, `would_block`, etc.) |
| `riskTier` | string or null | The risk tier at dry-run time |
| `policyVersion` | string or null | The policy version at dry-run time |
| `sanitizedArgumentsPreview` | object or null | Redacted argument preview from the dry-run |
| `argumentsDigest` | string or null | SHA-256 digest of the sanitized arguments |
| `dryRunDecisionDigest` | string or null | SHA-256 digest of the dry-run decision payload |
| `auditWritten` | boolean or null | Whether the dry-run audit was successfully written |
| `auditEventId` | string or null | The audit event identifier |
| `createdAt` | string or null | ISO 8601 timestamp of the dry-run |
| `expiresAt` | string or null | ISO 8601 timestamp when this reference expires |
| `lookupSource` | string or null | Which file/storage the record was retrieved from |
| `redactionStatus` | string or null | Redaction status of the retrieved record |

### 6.2 Output Must Not Contain

- Raw arguments
- Raw secrets
- Provider credentials
- Authorization headers
- Cookies
- Raw token secret
- Any unredacted user content

---

## 7. Lookup Failure Contract

### 7.1 Failure States

| Error Code | Description |
|------------|-------------|
| `dry_run_missing` | `dryRunRequestId` not provided in execute request |
| `dry_run_not_found` | No dry-run record matching the provided `dryRunRequestId` |
| `dry_run_expired` | Dry-run record found but TTL exceeded |
| `dry_run_not_allowed` | Dry-run decision was not `would_allow` |
| `dry_run_audit_missing` | Dry-run record found but `auditWritten` is `false` |
| `dry_run_digest_missing` | Dry-run record found but `dryRunDecisionDigest` is missing |
| `dry_run_digest_mismatch` | Provided digest does not match the dry-run record digest |
| `dry_run_canonical_name_mismatch` | `canonicalName` does not match the dry-run record |
| `dry_run_policy_version_mismatch` | `policyVersion` does not match the dry-run record |
| `dry_run_risk_tier_mismatch` | `riskTier` does not match the dry-run record |
| `dry_run_arguments_mismatch` | Arguments digest does not match the dry-run record |
| `dry_run_lookup_unavailable` | Audit storage is temporarily unavailable |

### 7.2 Failure Invariants

All failures block **before handler lookup**.
All failures keep `executionAllowed=false`.
All failures keep `toolHandlerCalled=false`.
All failures keep `providerApiCalled=false`.
All failures keep `executionStarted=false`.

---

## 8. Preflight Gate Order

The following gate order is frozen for future execute route implementation:

| Gate | Name | Description |
|------|------|-------------|
| 1 | Request shape validation | Validate request JSON structure and required fields |
| 2 | Kill switches | `HERMES_TOOL_EXECUTION_ENABLED` and `HERMES_AGENT_TOOLS_ENABLED` must be exact lowercase `"true"` |
| 3 | Static allowlist | `canonicalName` must be in `STATIC_ALLOWLIST` |
| 4 | Known tool / policy record | Tool must exist in the 71-tool inventory |
| 5 | Denylist / risk-tier disallowance | Tool must not be on STATIC_DENYLIST; risk tier must be eligible |
| 6 | `dryRunRequestId` present | Execute request must reference a prior dry-run |
| 7 | Dry-run historical lookup | Retrieve the prior dry-run decision from dev-only audit storage |
| 8 | Dry-run decision must be `would_allow` | The referenced dry-run must have decided `would_allow` |
| 9 | Dry-run `auditWritten` must be `true` | The referenced dry-run must have a written audit event |
| 10 | `canonicalName` binding | Execute `canonicalName` must match the dry-run `canonicalName` |
| 11 | `riskTier` binding | Execute `riskTier` must match the dry-run `riskTier` |
| 12 | `policyVersion` binding | Execute `policyVersion` must match the dry-run `policyVersion` |
| 13 | Sanitized arguments digest binding | Execute arguments digest must match the dry-run arguments digest |
| 14 | `confirmationToken` present | Execute request must include a confirmation token |
| 15 | Confirmation token verification | Token must be validly signed/structured |
| 16 | Confirmation token not expired | Token must be within its TTL |
| 17 | Confirmation token not reused | Token must not have been previously consumed |
| 18 | Confirmation token binds to `dryRunDecisionDigest` | Token must reference the same dry-run decision |
| 19 | Digest verification | Full digest chain must be consistent |
| 20 | Pre-execution audit readiness | Pre-execution audit must be writable |
| 21 | Handler lookup eligibility | All previous gates passed; handler may be looked up |

**Phase 1G-04-15 only freezes this order. No new gates are implemented in this phase.**

---

## 9. Confirmation Token Binding Goal

A future `confirmationToken` must bind to:

1. The exact `dryRunRequestId`
2. The exact `dryRunDecisionDigest`
3. The exact `canonicalName`
4. The sanitized arguments digest
5. The `auditEventId` (if available)
6. The `policyVersion` and `riskTier`

Token binding is verified **before handler lookup**.
Token binding failure **blocks**.
Token binding failure **never calls provider**.

---

## 10. Digest Binding Goal

Digest binding ensures:

1. The execute request uses the **same reviewed sanitized arguments** as the dry-run.
2. **Argument substitution** is prevented.
3. **`canonicalName` substitution** is prevented.
4. **Stale dry-run reuse** is prevented (via expiry).
5. **Policy-version drift** is prevented.
6. **Risk-tier drift** is prevented.

### 10.1 Digest Input

The digest is computed over the following canonical fields:

| Field | Description |
|-------|-------------|
| `canonicalName` | Tool canonical name |
| `riskTier` | Risk tier at decision time |
| `policyVersion` | Policy version at decision time |
| `dryRunRequestId` | Unique dry-run request identifier |
| `dryRunDecision` | The dry-run decision string |
| `dryRunAuditEventId` | Audit event identifier |
| `sanitizedArgumentsPreview` | Redacted argument preview |
| `redactionVersion` | Version of the redaction algorithm used |

### 10.2 Digest Algorithm

```
sha256(canonical_json(input))
```

Where `canonical_json` sorts keys deterministically and uses compact serialization.

---

## 11. Expiry Strategy

- Dry-run references should expire **quickly**.
- **Recommended dry-run reference TTL ≤ 5 minutes.**
- Confirmation token TTL should be **≤ dry-run reference TTL**.
- Expired dry-run **blocks before token verification**.
- Expired token **blocks before digest verification**.

**Expiry implementation is future work. No expiry code is implemented in Phase 1G-04-15.**

---

## 12. Replay Prevention Strategy

- `dryRunRequestId` should **not be reusable indefinitely**.
- `confirmationToken` must be **single-use**.
- A consumed confirmation token must **block on reuse**.
- Replay prevention must happen **before handler lookup**.

**Replay prevention implementation is future work. No token store is implemented in Phase 1G-04-15.**

---

## 13. Audit Binding Strategy

- Historical dry-run lookup must reference a dry-run audit event.
- Future execute preflight must record whether dry-run lookup passed.
- Future pre-execution audit must include `dryRunRequestId`, `dryRunDecisionDigest`, token id/hash, and digest.
- Future post-execution audit must include execution outcome if execution is ever enabled.
- Audit must **never store raw secrets**.
- Audit must **never store raw token secret**.

**Phase 1G-04-15 does not implement audit changes.**

---

## 14. Execute Route Behavior Delta

### 14.1 Current Baseline

- `clarify` is allowlisted (`STATIC_ALLOWLIST = frozenset({"clarify"})`)
- Execute route is blocked-only
- Dry-run historical lookup not implemented
- Confirmation token not implemented
- Digest verification not implemented
- No handler lookup
- No dispatch
- No execution

### 14.2 Future Implementation

- Execute route can look up prior dry-run record
- Execute route can verify dry-run decision and digest binding
- Execute route can verify confirmation token binding
- Execute route **may still remain blocked-only**
- Handler lookup remains forbidden unless later explicit phase enables it

### 14.3 Key Principle

**Dry-run lookup does not imply execution.**
**Confirmation token verification does not imply execution.**
**Digest match does not imply execution.**

---

## 15. Route Governance Strategy

No route governance count change in Phase 1G-04-15.

No route governance count change expected for dry-run historical lookup if implemented inside existing execute route.

| Metric | Current Value | Expected After 1G-04-15 |
|--------|---------------|------------------------|
| OpenAPI paths | 33 | 33 |
| Runtime routes | 33 | 33 |
| Tool GET routes | 4 | 4 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |

---

## 16. Future OpenAPI Strategy

No OpenAPI change in Phase 1G-04-15.

Future OpenAPI may refine existing execute schemas:

- `ToolExecuteRequest.dryRunRequestId`
- `ToolExecuteRequest.dryRunDecisionDigest`
- `ToolExecuteRequest.confirmationToken`
- `ToolExecuteData.gateStatus`
- `ToolExecuteData.auditStatus`
- `ToolExecuteErrorCode.dry_run_not_found`
- `ToolExecuteErrorCode.dry_run_expired`
- `ToolExecuteErrorCode.dry_run_digest_mismatch`
- `ToolExecuteErrorCode.confirmation_invalid`
- `ToolExecuteErrorCode.confirmation_expired`
- `ToolExecuteErrorCode.confirmation_reused`

**Any future OpenAPI schema change requires route governance checks. OpenAPI path count should remain 33 unless a new path is explicitly added.**

---

## 17. Future Allowed Files

The following files may be modified in future implementation phases. **They are not modified in Phase 1G-04-15.**

### 17.1 Existing Backend Files

```
hermes_cli/dev_web_tool_execute.py
hermes_cli/dev_web_tool_dry_run_audit.py
hermes_cli/dev_web_api.py
tests/test_dev_web_tool_execute.py
tests/test_dev_web_tool_execute_api.py
tests/test_dev_web_tool_dry_run_audit.py
tests/test_dev_check_webui.py
tests/test_dev_web_0c06_closure.py
docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md
docs/webui/phase-1-implementation-plan.md
```

### 17.2 Optional New Modules (Future Only)

```
hermes_cli/dev_web_tool_execute_preflight.py
hermes_cli/dev_web_tool_execute_confirmation.py
tests/test_dev_web_tool_execute_preflight.py
tests/test_dev_web_tool_execute_confirmation.py
```

These are future allowed files only. They are **not** created in Phase 1G-04-15.

---

## 18. Future Forbidden Files

The following must **never** be modified for dry-run historical lookup or preflight binding:

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
```

---

## 19. Future Test Matrix

The following tests must pass in future implementation phases:

### 19.1 Dry-Run Lookup Tests

| # | Test | Expected |
|---|------|----------|
| 1 | `dryRunRequestId` missing blocks before handler lookup | blocked |
| 2 | `dryRunRequestId` not found blocks before handler lookup | blocked |
| 3 | Dry-run expired blocks before handler lookup | blocked |
| 4 | Dry-run decision not `would_allow` blocks | blocked |
| 5 | Dry-run `auditWritten` false blocks | blocked |
| 6 | Dry-run `canonicalName` mismatch blocks | blocked |
| 7 | Dry-run `riskTier` mismatch blocks | blocked |
| 8 | Dry-run `policyVersion` mismatch blocks | blocked |
| 9 | Dry-run arguments digest mismatch blocks | blocked |
| 10 | `dryRunDecisionDigest` missing blocks | blocked |
| 11 | `dryRunDecisionDigest` mismatch blocks | blocked |

### 19.2 Confirmation Token Tests

| # | Test | Expected |
|---|------|----------|
| 12 | `confirmationToken` missing blocks | blocked |
| 13 | `confirmationToken` invalid blocks | blocked |
| 14 | `confirmationToken` expired blocks | blocked |
| 15 | `confirmationToken` reused blocks | blocked |
| 16 | `confirmationToken` dryRunRequestId mismatch blocks | blocked |
| 17 | `confirmationToken` digest mismatch blocks | blocked |
| 18 | `confirmationToken` canonicalName mismatch blocks | blocked |

### 19.3 Combined Path Tests

| # | Test | Expected |
|---|------|----------|
| 19 | `clarify` with valid allowlist but missing dry-run blocks | blocked |
| 20 | `clarify` with valid dry-run but missing token blocks | blocked |
| 21 | `clarify` with valid token but digest mismatch blocks | blocked |
| 22 | Non-`clarify` remains `blocked_by_allowlist` | blocked |

### 19.4 Safety Invariant Tests

| # | Test | Expected |
|---|------|----------|
| 23 | Kill switches unset still block before dry-run lookup | blocked |
| 24 | Handler not called on lookup failure | `toolHandlerCalled=false` |
| 25 | Handler not called on token failure | `toolHandlerCalled=false` |
| 26 | Handler not called on digest failure | `toolHandlerCalled=false` |
| 27 | Provider not called on any blocked path | `providerApiCalled=false` |
| 28 | Dispatch not called on any blocked path | `dispatchAllowed=false` |
| 29 | Execution not started on any blocked path | `executionStarted=false` |

### 19.5 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 30 | Tool write routes remain 0 | 0 |
| 31 | Tool execution routes remain 1 | 1 |
| 32 | OpenAPI paths remain 33 | 33 |
| 33 | Runtime routes remain 33 | 33 |

---

## 20. Entry Criteria for Future Implementation

Before dry-run historical lookup implementation begins, all of the following must be true:

1. Phase 1G-04-15 docs pushed.
2. No P0/P1 issues open.
3. User explicitly approves dry-run historical lookup implementation.
4. `STATIC_ALLOWLIST` remains exactly `{"clarify"}`.
5. Execute route remains blocked-only before implementation.
6. Route governance green.
7. Execute tests green.
8. Dry-run audit writer tests green.
9. Production gateway stable.
10. All scope docs reviewed and consistent.
11. Gate order (Section 8) confirmed.
12. Digest algorithm (Section 10) confirmed.
13. Failure semantics (Section 7) confirmed.

---

## 21. Exit Criteria for Future Implementation

After dry-run historical lookup implementation:

1. Dry-run historical lookup implemented read-only.
2. Lookup source is dev-only.
3. Dry-run not found blocks.
4. Dry-run expired blocks.
5. Dry-run not `would_allow` blocks.
6. Dry-run `auditWritten` false blocks.
7. `canonicalName` mismatch blocks.
8. `riskTier` mismatch blocks.
9. `policyVersion` mismatch blocks.
10. Arguments digest mismatch blocks.
11. `confirmationToken` missing/invalid/expired/reused blocks.
12. No blocked path calls handler.
13. No blocked path dispatches.
14. No blocked path executes.
15. No blocked path calls provider.
16. OpenAPI paths remain 33 unless explicitly changed.
17. Tool write routes remain 0.
18. Tool execution routes remain 1.
19. Production gateway unaffected.

---

## 22. Acceptance Criteria for Phase 1G-04-15

| # | Criterion |
|---|-----------|
| 1 | Docs-only |
| 2 | New dry-run historical lookup / preflight binding scope doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | No code changes |
| 6 | No OpenAPI file changes |
| 7 | No tests changed |
| 8 | No frontend changes |
| 9 | No routes changed |
| 10 | No execute route behavior changes |
| 11 | No `STATIC_ALLOWLIST` changes |
| 12 | `STATIC_ALLOWLIST` remains `frozenset({"clarify"})` |
| 13 | No dry-run historical lookup implementation |
| 14 | No confirmation token implementation |
| 15 | No digest verification implementation |
| 16 | No token store |
| 17 | No Tool Handler call |
| 18 | No Tool Dispatch |
| 19 | No Tool Execution |
| 20 | No Provider Schema sent |
| 21 | No Provider API called |
| 22 | OpenAPI paths still 33 |
| 23 | Runtime routes still 33 |
| 24 | Tool GET 4 |
| 25 | Tool write 0 |
| 26 | Tool dry-run 1 |
| 27 | Tool execution 1 |
| 28 | Execute route remains blocked-only |
| 29 | Real Controlled Execution not started |
| 30 | Local docs-only commit created |
| 31 | Not pushed |

---

*Phase 1G-04-15 Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze: scope definition only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no dry-run historical lookup implementation, no token implementation, no digest verification implementation, no handler call, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*

> **Update (Phase 1G-04-16):** The dry-run historical lookup defined in this scope document has been implemented as a read-only lookup in Phase 1G-04-16. See `docs/webui/phase-1g-04-16-dry-run-historical-lookup-read-only-implementation.md` for implementation details.
