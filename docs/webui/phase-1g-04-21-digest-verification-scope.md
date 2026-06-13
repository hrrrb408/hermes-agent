# Phase 1G-04-21: Digest Verification Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-21 |
| Title | Digest Verification Scope Freeze |
| Status | Frozen (digest verification boundary design only, no implementation) |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-21 digest verification scope freeze) |
| Dependencies | Phase 1G-04-20 completed locally |
| Branch | dev-huangruibang |
| Base commit | `aec3a426fb16e39da11788551ef16a62c358a74c` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future digest verification goal
2. Freezes the future digest input package (canonical digest package)
3. Freezes the future digest canonicalization strategy
4. Freezes the future digest algorithm
5. Freezes the future digest source-of-truth strategy
6. Documents the current `dryRunDecisionDigest` gap
7. Freezes the future relationship between digest verification and confirmation token
8. Freezes the future dry-run behavior delta for digest support
9. Freezes the future execute gate order including digest gates
10. Freezes the future digest failure contract
11. Freezes the future OpenAPI schema-only strategy
12. Freezes the future route governance strategy
13. Defines future allowed files and forbidden files
14. Defines the future test matrix
15. Defines entry criteria and exit criteria for future implementation
16. Defines acceptance criteria for Phase 1G-04-21
17. Does **not** implement digest verification
18. Does **not** compute or persist a new digest
19. Does **not** modify dry-run runtime behavior
20. Does **not** modify execute runtime behavior
21. Does **not** modify confirmation token behavior
22. Does **not** modify OpenAPI
23. Does **not** add runtime routes
24. Does **not** enable pre-execution audit
25. Does **not** enable handler lookup
26. Does **not** dispatch tools
27. Does **not** execute tools
28. Does **not** call providers
29. Does **not** start real Controlled Execution

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-21 = **Digest Verification Scope Freeze**.

This phase freezes the future digest verification boundary.

This phase does not implement digest verification.
This phase does not compute or persist a new digest.
This phase does not modify dry-run runtime behavior.
This phase does not modify execute runtime behavior.
This phase does not modify confirmation token behavior.
This phase does not modify OpenAPI.
This phase does not add runtime routes.
This phase does not enable pre-execution audit.
This phase does not enable handler lookup.
This phase does not dispatch tools.
This phase does not execute tools.
This phase does not call providers.
This phase does not start real Controlled Execution.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `aec3a426fb16e39da11788551ef16a62c358a74c` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Allowlisted canonicalName | `clarify` |
| Confirmation Token Issuance | Implemented (Phase 1G-04-20) |
| Confirmation Token Verification | Implemented (Phase 1G-04-20) |
| Token Store | Implemented (Phase 1G-04-20) |
| Token TTL | Implemented (Phase 1G-04-20) |
| Token Single-Use | Implemented (Phase 1G-04-20) |
| Execute Route Token Gates | Implemented (Gates 15–27, Phase 1G-04-20) |
| Valid Token Final Block | `blocked_digest_verification_not_implemented` |
| Digest Verification | Not implemented |
| Pre-execution Audit | Not implemented |
| Post-execution Audit | Not implemented |
| Handler Lookup | Not enabled |
| Dispatch | Not enabled |
| Execution | Disabled |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

---

## 3. Digest Verification Goal

### 3.1 Core Purpose

The future digest verification implementation should verify that the execute request still corresponds to the exact dry-run decision package that was reviewed and approved by confirmation token issuance.

### 3.2 Threat Model

Digest verification is designed to prevent:

| # | Threat | Description |
|---|--------|-------------|
| 1 | Dry-run replay with altered arguments | Arguments substituted between dry-run and execute |
| 2 | Stale decision reuse | Expired or outdated dry-run decision used for execute |
| 3 | canonicalName substitution | Tool name changed between dry-run and execute |
| 4 | policyVersion substitution | Policy version changed to bypass updated restrictions |
| 5 | riskTier substitution | Risk tier changed to bypass risk-tier gate |
| 6 | auditEventId mismatch | Audit event does not correspond to the dry-run decision |
| 7 | argumentsDigest mismatch | Arguments digest does not match the reviewed arguments |
| 8 | Token binding bypass | Token used with a different dry-run request |
| 9 | Execution request tampering after dry-run | Request fields modified in transit |
| 10 | Accidental use of an unrelated dry-run request | Wrong dry-run request referenced in execute |

### 3.3 Necessary but Not Sufficient

**Digest verification is necessary but not sufficient.**

Passing digest verification must **not** execute a tool.
Passing digest verification must **not** enable handler lookup unless a later explicit phase enables it.
After digest verification, execute must still block at the **pre-execution audit not implemented / not ready** boundary.

---

## 4. Digest Input Package

### 4.1 Canonical Digest Package

The future digest input package is frozen as:

```json
{
  "schemaVersion": 1,
  "digestType": "tool_dry_run_decision",
  "dryRunRequestId": "...",
  "canonicalName": "clarify",
  "riskTier": "R0",
  "policyVersion": "...",
  "policyDecision": "would_allow",
  "allowlisted": true,
  "auditWritten": true,
  "auditEventId": "...",
  "argumentsDigest": "...",
  "redactionVersion": "...",
  "toolPolicyVersion": "...",
  "toolCatalogVersion": "...",
  "createdAt": "...",
  "expiresAt": "..."
}
```

### 4.2 Field Purpose

| Field | Purpose |
|-------|---------|
| `dryRunRequestId` | Binds execute to exact dry-run request |
| `canonicalName` | Prevents tool substitution |
| `riskTier` | Prevents risk substitution |
| `policyVersion` | Prevents policy substitution |
| `policyDecision` | Binds to `would_allow` decision |
| `allowlisted` | Ensures allowlist state was part of decision |
| `auditWritten` | Ensures decision is auditable |
| `auditEventId` | Binds to dry-run audit event when available |
| `argumentsDigest` | Binds to canonicalized redacted arguments |
| `redactionVersion` | Binds to argument redaction/canonicalization version |
| `toolPolicyVersion` | Binds to policy implementation version |
| `toolCatalogVersion` | Binds to catalog version |
| `createdAt` | Supports stale decision protection |
| `expiresAt` | Supports expiry protection |

### 4.3 Current Gap

Phase 1G-04-20 notes that `dryRunDecisionDigest` is not yet stored in audit events. The confirmation token issuance currently binds `dryRunDecisionDigest` as `None` because no digest is generated during dry-run.

Future digest implementation must either:

- **Option A (Preferred):** Persist `dryRunDecisionDigest` during dry-run audit writing. This is the preferred path because it captures the digest at the exact moment of decision, making it a trustworthy source of truth.
- **Option B (Fallback):** Reconstruct the digest from stable audit fields only if all required fields exist and canonicalization is deterministic. This is risky because missing fields or format drift would break reconstruction silently.

**Preferred path: Option A — persist `dryRunDecisionDigest` at dry-run time.**

---

## 5. Canonicalization Strategy

### 5.1 Canonical JSON Rules

The canonical JSON for digest computation must follow these rules:

| # | Rule |
|---|------|
| 1 | UTF-8 encoding |
| 2 | Deterministic object key ordering (sorted) |
| 3 | No insignificant whitespace |
| 4 | Explicit null handling (null values are included) |
| 5 | Stable enum string values |
| 6 | Stable timestamp format (ISO 8601 UTC with trailing `Z`) |
| 7 | No raw secrets included in the digest package |
| 8 | No raw token included in the digest package |
| 9 | No raw provider credentials included in the digest package |
| 10 | No non-deterministic fields unless explicitly included in digest package |

### 5.2 Recommended Implementation

```python
canonical_json = json.dumps(
    digest_package,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
```

### 5.3 Prohibitions

The digest must **never** include:

- Raw `confirmationToken`
- `tokenHash`
- Raw arguments (only `argumentsDigest`)
- Raw secrets
- Raw provider credentials
- Non-deterministic fields (e.g., process IDs, random nonces not part of the digest package)

---

## 6. Digest Algorithm

### 6.1 Preferred Algorithm

```
dryRunDecisionDigest = "sha256:" + hex(SHA-256(canonical_digest_package_json))
```

### 6.2 Encoding

The digest encoding must be stable. The recommended encoding is:

- Prefix: `sha256:`
- Body: lowercase hex string of the SHA-256 hash

### 6.3 Future Implementation Choice

Future implementation must choose one encoding and keep it stable. If the encoding changes in the future, a `digestAlgorithm` version field must accompany the change, and the old encoding must remain verifiable until explicitly deprecated.

### 6.4 Digest Properties

| Property | Value |
|----------|-------|
| Digest is a secret | **No** — digest is an integrity binding value, not a secret |
| Digest can be stored in audit events | **Yes** |
| Digest can be stored in token binding metadata | **Yes** |
| Digest replaces confirmation token | **No** |
| Digest replaces pre-execution audit | **No** |

---

## 7. Source of Truth

### 7.1 Primary Source

```
$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl
```

The dry-run audit event is the primary source of truth for digest verification. It is written at dry-run time and is append-only.

### 7.2 Secondary Binding Source

```
$HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl
```

The confirmation token store binds to the digest when token issuance captures `dryRunDecisionDigest`.

### 7.3 Execute Request Source

The execute request may optionally provide `dryRunDecisionDigest` as an additional cross-check, but **only if** the OpenAPI schema approves this field. The execute request alone is never the sole source of truth.

### 7.4 Recommended Strategy

1. Digest should be generated during dry-run
2. Digest should be persisted in the dry-run audit event
3. Confirmation token issuance should bind to that persisted digest
4. Execute verification should compare:
   - Digest from historical dry-run lookup
   - Digest bound to confirmation token
   - Optional digest provided by execute request, if introduced

### 7.5 Forbidden Sources

The following must **never** be used as a source of truth:

- Frontend cache
- Browser local storage
- Provider logs
- Live provider response
- Production `~/.hermes`
- Production `state.db`
- Untrusted execute request body alone

---

## 8. Relationship With Confirmation Token

### 8.1 Separation of Concerns

| Concern | Responsibility |
|---------|----------------|
| **Confirmation token** | Verifies that the user approved a specific dry-run decision |
| **Digest verification** | Verifies that the current execute request still matches the approved dry-run decision package |

Both are required for future controlled execution. Neither is sufficient to execute a tool by itself.

### 8.2 Current State (Phase 1G-04-20)

The confirmation token may bind `dryRunDecisionDigest` as `None` because `dryRunDecisionDigest` is not yet stored in audit events. This is a known gap documented in Phase 1G-04-20 Section 7 ("Known Limitations").

### 8.3 Future Target

1. Confirmation token issuance must bind **non-null** `dryRunDecisionDigest` once digest generation is implemented.
2. Execute verification must **fail closed** if token digest binding is missing after the digest feature is required.
3. Token verification continues to work independently — digest verification is an additional gate, not a replacement.

---

## 9. Future Dry-Run Behavior Delta

### 9.1 Dry-Run May Add

| # | Addition | Description |
|---|----------|-------------|
| 1 | `dryRunDecisionDigest` in dry-run response | Returned to caller for transparency |
| 2 | `dryRunDecisionDigest` in dry-run audit event | Persisted as source of truth |
| 3 | `digestPackageVersion` | Version of the digest package schema |
| 4 | `canonicalizationVersion` | Version of the canonicalization algorithm |
| 5 | `argumentsDigest` stabilization | Ensure `argumentsDigest` is stable if not already |
| 6 | `digestAlgorithm` | Algorithm identifier (`sha256`) |

### 9.2 Dry-Run Must Not

- Add a new route
- Add a Tool write route
- Call a provider
- Call a Tool Handler
- Execute any tool
- Change its fundamental non-executing nature

---

## 10. Future Execute Gate Order

### 10.1 Current State (Phase 1G-04-20)

| Gate | Name | Status |
|------|------|--------|
| 1–14 | Existing kill switch, allowlist, dry-run lookup, dry-run binding gates | Active |
| 15–27 | Confirmation token verification gates | Active |
| 28 | `blocked_digest_verification_not_implemented` | **Blocks** |

### 10.2 Future Digest Implementation Target

| Gate | Name | Description |
|------|------|-------------|
| 1–27 | Existing gates | Unchanged |
| 28 | Digest package available | Historical dry-run record contains `dryRunDecisionDigest` |
| 29 | Digest canonicalization succeeds | Canonical JSON can be constructed from available fields |
| 30 | Historical dry-run digest present | Audit event contains `dryRunDecisionDigest` |
| 31 | Token-bound digest present | Confirmation token record contains non-null `dryRunDecisionDigest` |
| 32 | Optional request digest matches | If execute request provides `dryRunDecisionDigest`, it matches (if introduced) |
| 33 | Historical digest == token-bound digest | Both sources agree |
| 34 | Current execute-derived digest == historical digest | Reconstructed digest matches stored digest |
| 35 | Digest expiry / staleness check | Digest is not stale based on `createdAt` / `expiresAt` |
| 36 | Block — pre-execution audit not implemented | Even after valid digest, block because pre-execution audit is not ready |
| 37 | Handler lookup | Still disabled |

### 10.3 Critical Principle

After digest verification passes, execute **still blocks**. The next allowed block boundary is `blocked_pre_execution_audit_not_implemented`. No handler lookup is allowed in digest verification implementation.

---

## 11. Future Failure Contract

### 11.1 Error Codes / Decisions

| Error Code | Decision | Description |
|------------|----------|-------------|
| `digest_missing` | `blocked_digest_missing` | Digest field is missing entirely |
| `digest_unavailable` | `blocked_digest_unavailable` | Digest cannot be retrieved from source |
| `digest_canonicalization_failed` | `blocked_digest_canonicalization_failed` | Canonical JSON construction failed |
| `digest_historical_missing` | `blocked_digest_historical_missing` | Historical dry-run record lacks digest |
| `digest_token_binding_missing` | `blocked_digest_token_binding_missing` | Token record lacks digest binding |
| `digest_request_mismatch` | `blocked_digest_request_mismatch` | Execute request digest differs from historical |
| `digest_token_mismatch` | `blocked_digest_token_mismatch` | Token-bound digest differs from historical |
| `digest_execute_mismatch` | `blocked_digest_execute_mismatch` | Reconstructed digest differs from historical |
| `digest_stale` | `blocked_digest_stale` | Digest is stale based on timing |
| `digest_expired` | `blocked_digest_expired` | Digest has expired |
| `digest_policy_version_mismatch` | `blocked_digest_policy_version_mismatch` | Policy version in digest differs from current |
| `digest_arguments_mismatch` | `blocked_digest_arguments_mismatch` | Arguments digest differs |
| `digest_audit_event_mismatch` | `blocked_digest_audit_event_mismatch` | Audit event ID differs |
| `digest_verified_but_pre_execution_audit_not_implemented` | `blocked_pre_execution_audit_not_implemented` | Digest verified but audit not ready |

### 11.2 Failure Invariants

All digest failures must:

| Invariant | Value |
|-----------|-------|
| Block before handler lookup | **Always** |
| `executionAllowed` | `false` |
| `dispatchAllowed` | `false` |
| `providerSchemaAllowed` | `false` |
| `toolHandlerCalled` | `false` |
| `providerApiCalled` | `false` |
| `executionStarted` | `false` |

---

## 12. Future OpenAPI Strategy

### 12.1 Phase 1G-04-21

Phase 1G-04-21 does **not** modify OpenAPI.

### 12.2 Future OpenAPI Refinements

Future digest implementation may require schema-only OpenAPI changes:

| Schema | Possible Refinement |
|--------|---------------------|
| `ToolDryRunResponse.dryRunDecisionDigest` | New optional field for digest value |
| `ToolDryRunResponse.digestAlgorithm` | Algorithm identifier |
| `ToolDryRunResponse.digestPackageVersion` | Digest package schema version |
| `ToolDryRunAudit` event schema | Documentation-only if represented in OpenAPI |
| `ToolExecuteRequest.dryRunDecisionDigest` | Optional field for client-side cross-check |
| `ToolExecuteErrorCode` | New `digest_*` error code values |
| `ToolExecuteDecision` | New `blocked_digest_*` decision values |
| `ToolExecuteGateStatus` | Digest gate names |

### 12.3 Path Count Constraint

No new OpenAPI path unless separately approved. OpenAPI paths should remain **33**. Runtime routes should remain **33**. Tool write routes should remain **0**. Tool execution routes should remain **1**.

---

## 13. Route Governance Strategy

### 13.1 Preferred Future Implementation

No new route.

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### 13.2 Route Change Policy

If future digest implementation requires a route change:

1. Must **stop** and create a separate route-governed scope freeze
2. No route change may be smuggled into digest implementation
3. Any route count change must be explicitly approved in a new scope document

---

## 14. Future Allowed Files

### 14.1 Future Implementation Allowed Files

The following files may be modified or created in a future digest verification implementation phase. **They are not modified in Phase 1G-04-21.**

#### New Backend Module

```
hermes_cli/dev_web_tool_execute_digest.py  (new — recommended digest helper module)
```

#### Existing Backend Files

```
hermes_cli/dev_web_tool_dry_run.py
hermes_cli/dev_web_tool_dry_run_audit.py
hermes_cli/dev_web_tool_execute.py
hermes_cli/dev_web_tool_execute_confirmation.py
hermes_cli/dev_web_tool_execute_preflight.py
hermes_cli/dev_web_api.py
```

#### OpenAPI

```
docs/webui/openapi/dev-web-api-v1.yaml  (schema-only changes if approved)
```

#### Test Files

```
tests/test_dev_web_tool_execute_digest.py  (new)
tests/test_dev_web_tool_dry_run.py
tests/test_dev_web_tool_dry_run_api.py
tests/test_dev_web_tool_dry_run_audit.py
tests/test_dev_web_tool_execute.py
tests/test_dev_web_tool_execute_api.py
tests/test_dev_web_tool_execute_confirmation.py
tests/test_dev_web_tool_execute_preflight.py
tests/test_dev_check_webui.py
tests/test_dev_web_0c06_closure.py
```

#### Documentation Files

```
docs/webui/phase-1g-04-21-digest-verification-scope.md
docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md
docs/webui/phase-1-implementation-plan.md
```

### 14.2 Declaration

These are **future allowed files only.** They are **not** modified in Phase 1G-04-21, except docs files allowed by this docs-only phase.

---

## 15. Future Forbidden Files

The following must **not** be modified in any digest verification implementation phase:

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

## 16. Future Test Matrix

The following tests must pass when digest verification implementation arrives. **None are added in Phase 1G-04-21.**

### 16.1 Digest Package Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Canonical package includes all required fields | All 14 fields present |
| 2 | Canonical package excludes raw token | No `confirmationToken` in package |
| 3 | Canonical package excludes `tokenHash` | No `tokenHash` in package |
| 4 | Canonical package excludes raw arguments | No raw arguments, only `argumentsDigest` |
| 5 | Canonical package excludes secrets | No secrets in package |
| 6 | Canonical JSON is deterministic despite key order | Same digest for equivalent JSON with different key order |
| 7 | Null handling is deterministic | Consistent digest when null values present |
| 8 | Timestamp format is deterministic | ISO 8601 UTC with `Z` suffix |
| 9 | Digest algorithm prefix is stable | `sha256:` prefix |
| 10 | Digest changes when `canonicalName` changes | Different digest |
| 11 | Digest changes when `argumentsDigest` changes | Different digest |
| 12 | Digest changes when `policyVersion` changes | Different digest |
| 13 | Digest changes when `riskTier` changes | Different digest |
| 14 | Digest changes when `auditEventId` changes | Different digest |

### 16.2 Dry-Run Digest Tests

| # | Test | Expected |
|---|------|----------|
| 15 | Dry-run `would_allow` produces `dryRunDecisionDigest` | Digest present in response |
| 16 | Dry-run `blocked` decision does not issue token unless explicitly scoped | No token |
| 17 | Dry-run audit event stores `dryRunDecisionDigest` | Digest in audit JSONL |
| 18 | Dry-run response includes digest only when schema allows | Conditional presence |
| 19 | `digestPackageVersion` stored in audit event | Version present |
| 20 | `digestAlgorithm` stored in audit event | Algorithm present |
| 21 | Dry-run digest is stable across repeated canonicalization | Same digest |
| 22 | Dry-run digest excludes raw secrets | No secrets in digest |

### 16.3 Confirmation Token Binding Tests

| # | Test | Expected |
|---|------|----------|
| 23 | Token issuance binds non-null `dryRunDecisionDigest` | Digest not None |
| 24 | Token verification fails when token digest binding missing after digest required | `blocked_digest_token_binding_missing` |
| 25 | Token verification fails when token digest mismatches historical digest | `blocked_digest_token_mismatch` |
| 26 | Token verification succeeds when digest matches | Pass |
| 27 | Token reuse still blocks before digest re-check if already consumed | `confirmation_reused` |

### 16.4 Execute Digest Gate Tests

| # | Test | Expected |
|---|------|----------|
| 28 | Missing historical digest blocks | `blocked_digest_historical_missing` |
| 29 | Missing token-bound digest blocks | `blocked_digest_token_binding_missing` |
| 30 | Request digest mismatch blocks | `blocked_digest_request_mismatch` |
| 31 | Token digest mismatch blocks | `blocked_digest_token_mismatch` |
| 32 | Execute-derived digest mismatch blocks | `blocked_digest_execute_mismatch` |
| 33 | Stale digest blocks | `blocked_digest_stale` |
| 34 | Expired digest blocks | `blocked_digest_expired` |
| 35 | `policyVersion` mismatch blocks | `blocked_digest_policy_version_mismatch` |
| 36 | `argumentsDigest` mismatch blocks | `blocked_digest_arguments_mismatch` |
| 37 | `auditEventId` mismatch blocks | `blocked_digest_audit_event_mismatch` |
| 38 | Valid token + valid digest still blocks at pre-execution audit boundary | `blocked_pre_execution_audit_not_implemented` |

### 16.5 Safety Invariant Tests

| # | Test | Expected |
|---|------|----------|
| 39 | All digest failures block before handler lookup | `toolHandlerCalled=false` |
| 40 | All digest failures keep side-effect flags false | All flags `false` |
| 41 | Provider is never called on digest failure | `providerApiCalled=false` |
| 42 | Dispatch is never called on digest failure | `dispatchAllowed=false` |
| 43 | Execution is never started on digest failure | `executionStarted=false` |
| 44 | Valid digest does not call handler | `toolHandlerCalled=false` |
| 45 | Valid digest does not dispatch | `dispatchAllowed=false` |
| 46 | Valid digest does not call provider | `providerApiCalled=false` |

### 16.6 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 47 | OpenAPI paths remain 33 unless separately approved | 33 |
| 48 | Runtime routes remain 33 unless separately approved | 33 |
| 49 | Tool write routes remain 0 | 0 |
| 50 | Tool execution routes remain 1 | 1 |
| 51 | `STATIC_ALLOWLIST` remains `{"clarify"}` | `frozenset({"clarify"})` |

---

## 17. Future Implementation Entry Criteria

Before digest verification implementation may begin, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-21 docs pushed |
| 2 | No P0/P1 open |
| 3 | User explicitly approves digest verification implementation |
| 4 | Remote and local branch synchronized |
| 5 | `STATIC_ALLOWLIST` remains exactly `{"clarify"}` |
| 6 | Route governance green |
| 7 | Dry-run audit writer behavior understood and tested |
| 8 | Confirmation token gate green (Gates 15–27) |
| 9 | Valid token currently blocks at digest boundary (Gate 28) |
| 10 | Provider schema not sent |
| 11 | Tool dispatch disabled |
| 12 | Tool execution disabled |
| 13 | Production gateway stable |

---

## 18. Future Implementation Exit Criteria

After digest verification implementation, **all** of the following must be true:

| # | Criterion |
|---|-----------|
| 1 | Digest package builder implemented |
| 2 | Canonicalization implemented |
| 3 | Digest computation implemented (`sha256:` prefix, hex encoding) |
| 4 | `dryRunDecisionDigest` persisted in dry-run audit event |
| 5 | `dryRunDecisionDigest` returned in dry-run response if schema allows |
| 6 | Confirmation token issuance binds non-null digest |
| 7 | Execute digest verification implemented (Gates 28–35) |
| 8 | Digest mismatch blocks |
| 9 | Digest missing blocks |
| 10 | Digest canonicalization failure blocks |
| 11 | Digest stale/expired blocks |
| 12 | Valid token + valid digest still blocks at pre-execution audit boundary |
| 13 | No digest failure calls handler |
| 14 | No digest failure dispatches |
| 15 | No digest failure executes |
| 16 | No digest failure calls provider |
| 17 | OpenAPI paths remain 33 unless separately approved |
| 18 | Runtime routes remain 33 unless separately approved |
| 19 | Tool write routes remain 0 |
| 20 | Tool execution routes remain 1 |
| 21 | `STATIC_ALLOWLIST` remains `{"clarify"}` |
| 22 | Production gateway unaffected |

---

## 19. Acceptance Criteria for Phase 1G-04-21

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only | |
| 2 | New digest verification scope doc added | |
| 3 | Phase 1G-04 scope doc updated | |
| 4 | Implementation plan updated | |
| 5 | Phase 1G-04-20 doc updated with next dependency | |
| 6 | No code changes | |
| 7 | No OpenAPI file changes | |
| 8 | No tests changed | |
| 9 | No frontend changes | |
| 10 | No routes changed | |
| 11 | No execute route behavior changes | |
| 12 | No token behavior changes | |
| 13 | No `STATIC_ALLOWLIST` changes | |
| 14 | `STATIC_ALLOWLIST` remains `frozenset({"clarify"})` | |
| 15 | No digest verification implementation | |
| 16 | No dry-run digest persistence implementation | |
| 17 | No pre-execution audit | |
| 18 | No post-execution audit | |
| 19 | No handler lookup | |
| 20 | No Tool Handler call | |
| 21 | No dispatch | |
| 22 | No execution | |
| 23 | No Provider Schema | |
| 24 | No Provider API | |
| 25 | OpenAPI paths = 33 | |
| 26 | Runtime routes = 33 | |
| 27 | Tool GET = 4 | |
| 28 | Tool write = 0 | |
| 29 | Tool dry-run = 1 | |
| 30 | Tool execution = 1 | |
| 31 | Execute route remains blocked-only | |
| 32 | Real Controlled Execution not started | |
| 33 | Local docs-only commit created | |
| 34 | Not pushed | |

---

## 20. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code modified | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Route count changed | Verify route governance; reject if changed |
| 6 | Execute route behavior changed | Verify diff; reject if execute runtime changed |
| 7 | Token behavior changed | Verify diff; reject if token runtime changed |
| 8 | `STATIC_ALLOWLIST` modified | Verify unchanged; reject if modified |
| 9 | Allowlist expanded | Verify unchanged; reject if expanded |
| 10 | Digest verification implemented | Verify diff; reject if digest code added |
| 11 | Dry-run digest persistence implemented | Verify diff; reject if digest persistence added |
| 12 | Tool Handler called | Verify no handler invocation; reject if found |
| 13 | Provider API called / Schema sent | Verify no provider calls; reject if found |
| 14 | Tool write routes > 0 | Verify route governance; reject if changed |
| 15 | Tool execution routes ≠ 1 | Verify route governance; reject if changed |
| 16 | Real secret leaked | Content search; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-21 Failed."**

---

## 21. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Digest goal missing | Verify Section 3 |
| 2 | Digest input package missing | Verify Section 4 |
| 3 | Canonicalization strategy missing | Verify Section 5 |
| 4 | Digest algorithm missing | Verify Section 6 |
| 5 | Source-of-truth strategy missing | Verify Section 7 |
| 6 | Current `dryRunDecisionDigest` gap missing | Verify Section 4.3 |
| 7 | Confirmation token relationship missing | Verify Section 8 |
| 8 | Future dry-run behavior delta missing | Verify Section 9 |
| 9 | Future execute gate order missing | Verify Section 10 |
| 10 | Future failure contract missing | Verify Section 11 |
| 11 | Future OpenAPI strategy missing | Verify Section 12 |
| 12 | Future route governance missing | Verify Section 13 |
| 13 | Future allowed files missing | Verify Section 14 |
| 14 | Future forbidden files missing | Verify Section 15 |
| 15 | Future test matrix missing | Verify Section 16 |
| 16 | Entry criteria missing | Verify Section 17 |
| 17 | Exit criteria missing | Verify Section 18 |
| 18 | Docs incorrectly claim digest implemented | Content review |
| 19 | Docs incorrectly claim pre-execution audit implemented | Content review |
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

## 22. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Digest verification not yet implemented | Expected — scope freeze only |
| 2 | Dry-run digest persistence not yet implemented | Expected — scope freeze only |
| 3 | Pre-execution audit not yet implemented | Expected — future phase |
| 4 | Post-execution audit not yet implemented | Expected — future phase |
| 5 | Execute route still does not execute tools | Expected — blocked-only |
| 6 | Handler lookup not yet enabled | Expected — future phase |
| 7 | Frontend execute UI not implemented | Expected — future phase |
| 8 | Browser smoke not re-run | Expected — no frontend changes |
| 9 | Clarify handler-level audit still needs future phase | Expected — future work |
| 10 | Lookup performance can be optimized later | Expected — optimization deferred |
| 11 | Multi-file audit rotation support may be future work | Expected — deferred |
| 12 | `dryRunDecisionDigest` not yet written to audit events | Expected — future digest implementation |
| 13 | Confirmation token digest binding currently may be `None` | Expected — future digest implementation |
| 14 | Append-only JSONL token consumption race conditions need future local-dev handling | Expected — local dev constraints |

---

*Phase 1G-04-21 Digest Verification Scope Freeze: digest verification goal, digest input package, canonicalization strategy, digest algorithm, source-of-truth strategy, current dryRunDecisionDigest gap, confirmation token relationship, future dry-run behavior delta, future execute digest gate order, failure contract, OpenAPI strategy, route governance, future allowed/forbidden files, future test matrix, entry/exit criteria frozen. Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no digest verification implementation, no dry-run digest persistence implementation, no pre-execution audit, no handler lookup, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*
