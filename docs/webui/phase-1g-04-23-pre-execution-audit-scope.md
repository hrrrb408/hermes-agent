# Phase 1G-04-23: Pre-Execution Audit Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-23 |
| Title | Pre-Execution Audit Scope Freeze |
| Status | Frozen (pre-execution audit boundary design only, no implementation) |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-23 pre-execution audit scope freeze) |
| Dependencies | Phase 1G-04-22 completed locally |
| Branch | dev-huangruibang |
| Base commit | `ab2c0387d42ef99fcb9ce24a2c8572b4e4c6c793` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future pre-execution audit goal
2. Documents why pre-execution audit is necessary but not sufficient
3. Freezes the difference between pre-execution audit and dry-run audit
4. Freezes the relationship between pre-execution audit and confirmation token
5. Freezes the relationship between pre-execution audit and digest verification
6. Freezes the relationship between pre-execution audit and handler lookup
7. Freezes the future pre-execution audit write timing
8. Freezes the future pre-execution audit event structure
9. Freezes the future pre-execution audit field set
10. Freezes the future pre-execution audit JSONL storage path
11. Freezes the future pre-execution audit path guard strategy
12. Freezes the future pre-execution audit ID strategy
13. Freezes the future pre-execution audit idempotency strategy
14. Freezes the future pre-execution audit retry / duplicate strategy
15. Freezes the future pre-execution audit failure contract
16. Freezes the future pre-execution audit success contract
17. Freezes the future execute gate order
18. Freezes the future OpenAPI schema-only strategy
19. Freezes the future route governance strategy
20. Defines future allowed files and forbidden files
21. Defines the future test matrix (55 tests)
22. Defines entry criteria and exit criteria for future implementation
23. Defines acceptance criteria for Phase 1G-04-23
24. Does **not** implement pre-execution audit
25. Does **not** write pre-execution audit events
26. Does **not** modify dry-run runtime behavior
27. Does **not** modify execute runtime behavior
28. Does **not** modify confirmation token behavior
29. Does **not** modify digest verification behavior
30. Does **not** modify OpenAPI
31. Does **not** add runtime routes
32. Does **not** enable handler lookup
33. Does **not** dispatch tools
34. Does **not** execute tools
35. Does **not** call providers
36. Does **not** start real Controlled Execution

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-23 = **Pre-Execution Audit Scope Freeze**.

This phase freezes the future pre-execution audit boundary.

This phase does not implement pre-execution audit.
This phase does not write pre-execution audit events.
This phase does not modify dry-run runtime behavior.
This phase does not modify execute runtime behavior.
This phase does not modify confirmation token behavior.
This phase does not modify digest verification behavior.
This phase does not modify OpenAPI.
This phase does not add runtime routes.
This phase does not enable handler lookup.
This phase does not dispatch tools.
This phase does not execute tools.
This phase does not call providers.
This phase does not start real Controlled Execution.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Remote HEAD | `ab2c0387d42ef99fcb9ce24a2c8572b4e4c6c793` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Confirmation token issuance | Implemented |
| Confirmation token verification | Implemented |
| Token store | Implemented |
| Token TTL | Implemented |
| Token single-use | Implemented |
| Digest verification | Implemented |
| Dry-run decision digest persistence | Implemented |
| Execute digest gates | Implemented |
| Valid token + valid digest final block | `blocked_pre_execution_audit_not_implemented` |
| Pre-execution audit | Not implemented |
| Post-execution audit | Not implemented |
| Handler lookup | Not enabled |
| Dispatch | Not enabled |
| Execution | Disabled |
| Provider Schema | Not sent |
| Provider API | Not called |
| Real Controlled Execution | Not started |

---

## 3. Pre-Execution Audit Goal

The future pre-execution audit implementation should write a durable dev-only audit event immediately after the request has passed all prior gates and immediately before any future handler lookup / dispatch / execution boundary.

The audit exists to prove that a specific execute attempt passed:

1. Kill switch gate
2. Static allowlist gate
3. Dry-run historical lookup gate
4. Dry-run binding gate
5. Confirmation token gate
6. Confirmation token TTL gate
7. Confirmation token single-use gate
8. Confirmation token binding gate
9. Digest verification gate
10. Staleness / expiry gate
11. Blocked-only safety boundary before handler lookup

### Necessary But Not Sufficient

Pre-execution audit is **necessary but not sufficient**.

- Passing / writing pre-execution audit must not execute a tool.
- Passing / writing pre-execution audit must not call handler lookup unless a later explicit phase enables it.
- After pre-execution audit is written, execute must still block at `blocked_handler_lookup_not_enabled` or equivalent.

Pre-execution audit proves that an attempt reached the pre-handler boundary with valid credentials and matching digests. It does not authorize execution.

---

## 4. Difference From Dry-Run Audit

### Dry-Run Audit

Dry-run audit records a **non-executing policy simulation**.

- Written during dry-run phase
- Records the hypothetical decision (`would_allow`, `would_block`, etc.)
- No tool handler is consulted
- No confirmation token is involved
- No digest verification is performed
- Source: `$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl`

Dry-run audit answers:
> "What would happen if this tool were executed?"

### Pre-Execution Audit

Pre-execution audit records a **later execute attempt** that passed confirmation token verification and digest verification.

- Written during execute phase (after all prior gates pass)
- Records that a real execution attempt reached the pre-handler boundary
- Tool handler is still not consulted
- Confirmation token was verified and consumed
- Digest was verified against historical, token-bound, and execute-derived sources
- Source: `$HERMES_HOME/gateway/dev/audit/tool-pre-execution-audit.jsonl` (future)

Pre-execution audit answers:
> "An execution attempt was made, all pre-execution gates passed, and the system still stopped before handler lookup / dispatch."

### Separation Requirements

- Pre-execution audit must not replace dry-run audit.
- Pre-execution audit must not mutate dry-run audit records.
- Pre-execution audit must not rewrite the confirmation token store.
- Pre-execution audit must not act as execution proof.

---

## 5. Relationship With Confirmation Token

Confirmation token proves the user approved a specific eligible dry-run decision.

Pre-execution audit records that a later execute attempt used that approved token and reached the pre-handler boundary.

### Future Pre-Execution Audit Event Should Reference

1. `confirmationTokenId`
2. `confirmationIssuedAt` (token issued timestamp)
3. `confirmationConsumedAt` (token consumed timestamp)
4. `dryRunRequestId`
5. `dryRunDecisionDigest`
6. Token-bound digest
7. Token verification result

### Must NOT Record

- Raw `confirmationToken`
- `tokenHash` full value
- Raw secrets
- Raw authorization headers
- Raw cookies
- Raw provider credentials

---

## 6. Relationship With Digest Verification

Digest verification proves that the execute request still matches the approved dry-run decision package.

Pre-execution audit records that digest verification passed for this execute attempt.

### Future Pre-Execution Audit Event Should Reference

1. `dryRunDecisionDigest`
2. `digestAlgorithm`
3. `digestPackageVersion`
4. `canonicalizationVersion`
5. Historical digest
6. Token-bound digest
7. Execute-derived digest
8. Digest verification result

### Must NOT Record

- Raw digest package if it contains sensitive values
- Raw arguments
- `tokenHash` full value
- Raw token

---

## 7. Relationship With Handler Lookup

Pre-execution audit is the **final durable record** before any future handler lookup.

In the future, handler lookup may only be considered after:

1. Dry-run historical lookup passed
2. Confirmation token passed
3. Digest verification passed
4. Pre-execution audit was written successfully
5. Explicit later phase enables handler lookup

### Post-Audit Block Boundary

Neither Phase 1G-04-23 nor the future pre-execution audit implementation phase may enable handler lookup unless the user explicitly approves a new phase.

Future post-audit block decision:

```
blocked_handler_lookup_not_enabled
```

Or equivalent item-approved blocked decision.

---

## 8. Future Write Timing

### Pre-execution audit should be written only after

1. Execute request accepted by route
2. Kill switch allows execute
3. `canonicalName` is allowlisted
4. Dry-run historical lookup succeeds
5. Dry-run binding succeeds
6. Confirmation token verification succeeds
7. Confirmation token is consumed or consumption is safely recorded
8. Digest verification succeeds
9. Staleness / expiry checks pass

### Pre-execution audit must be written before

1. Handler lookup
2. Tool Handler call
3. Dispatch
4. Execution
5. Provider Schema sending
6. Provider API call

### Failure Behavior

If pre-execution audit write fails, execute must block.

If pre-execution audit write succeeds, execute still blocks at handler lookup not enabled.

---

## 9. Future Audit Store Path

### Path

```
$HERMES_HOME/gateway/dev/audit/tool-pre-execution-audit.jsonl
```

### Path Guard Strategy (Containment-Based)

The path guard must enforce:

1. Resolved `HERMES_HOME` must not equal production home `~/.hermes`
2. Resolved `HERMES_HOME` must not be inside production home `~/.hermes`
3. Resolved pre-execution audit directory must be inside `$HERMES_HOME/gateway/dev/audit`
4. Resolved pre-execution audit file must be inside `$HERMES_HOME/gateway/dev/audit`
5. Resolved pre-execution audit directory/file must not be inside `~/.hermes`
6. Symlink / path traversal into production home must fail closed
7. Path validation must happen before file read/write
8. Production containment violation must not open the audit file
9. Failure must return fail-closed result, not unhandled exception

### Implementation Method

Must use `Path.resolve(strict=False)` + `Path.relative_to()` or equivalent containment helper.

Must NOT use string prefix matching (which would falsely block `/Users/huangruibang/.hermes-dev` as a sibling of production home).

Must NOT use equality-only path comparison.

---

## 10. Future Pre-Execution Audit Event Structure

### Recommended Structure

```json
{
  "recordType": "tool_pre_execution_audit",
  "schemaVersion": 1,
  "eventType": "pre_execution_gate_passed",
  "preExecutionAuditId": "pea_...",
  "executeRequestId": "exe_...",
  "dryRunRequestId": "...",
  "dryRunDecisionDigest": "sha256:...",
  "canonicalName": "clarify",
  "riskTier": "R0",
  "policyVersion": "...",
  "argumentsDigest": "sha256:...",
  "redactionVersion": "...",
  "auditEventId": "...",
  "confirmationTokenId": "ctok_...",
  "confirmationIssuedAt": "...",
  "confirmationConsumedAt": "...",
  "digestAlgorithm": "sha256",
  "digestPackageVersion": "1",
  "canonicalizationVersion": "json-sort-v1",
  "historicalDigest": "sha256:...",
  "tokenBoundDigest": "sha256:...",
  "executeDerivedDigest": "sha256:...",
  "gateStatus": {
    "killSwitch": "passed",
    "allowlist": "passed",
    "dryRunLookup": "passed",
    "confirmationToken": "passed",
    "digestVerification": "passed",
    "preExecutionAudit": "written",
    "handlerLookup": "blocked_not_enabled"
  },
  "sideEffectFlags": {
    "executionAllowed": false,
    "dispatchAllowed": false,
    "providerSchemaAllowed": false,
    "toolHandlerCalled": false,
    "providerApiCalled": false,
    "executionStarted": false
  },
  "createdAt": "...",
  "expiresAt": "...",
  "status": "written"
}
```

### Required Field Exclusions

- No raw `confirmationToken`
- No full `tokenHash`
- No raw arguments
- No secrets
- No provider credentials
- No authorization headers
- No cookies
- No Provider Schema
- No Provider response
- No tool execution result

---

## 11. Future Audit ID Strategy

### ID Generation

- `preExecutionAuditId` should be safe for correlation
- `executeRequestId` should be safe for correlation
- IDs must not contain raw token or `tokenHash`
- IDs may be random UUID / ULID / stable hash of safe correlation fields

### Recommended Prefixes

- `preExecutionAuditId` = `pea_` + random or digest prefix
- `executeRequestId` = `exe_` + random or digest prefix

### Authorization Scope

- `preExecutionAuditId` is not an authorization credential
- `executeRequestId` is not an authorization credential

---

## 12. Future Idempotency Strategy

### Append-Only

Pre-execution audit writes should be append-only.

### Token Single-Use Interaction

A repeated execute attempt with a consumed confirmation token should fail before writing a new pre-execution audit event (because confirmation token single-use blocks at an earlier gate).

### Retry Scenario

If an execute attempt retries after pre-execution audit write succeeded but before response returned, implementation must:

- Avoid double-writing indistinguishable records, OR
- Include explicit retry metadata in the duplicate record

### Recommended Strategy (Minimal Implementation)

Append-only JSONL with unique `preExecutionAuditId` per execute attempt.

- No overwrite
- No mutation
- Duplicate attempts are allowed as separate records only if they use separate valid confirmation tokens

### Natural Deduplication

Because confirmation tokens are single-use, normal duplicate execution using the same token should block before a second pre-execution audit event.

---

## 13. Future Failure Contract

### Error Codes / Decisions

| Error Code | Description |
|------------|-------------|
| `pre_execution_audit_unavailable` | Audit store not available |
| `pre_execution_audit_path_forbidden` | Path guard violation |
| `pre_execution_audit_write_failed` | Write I/O error |
| `pre_execution_audit_invalid_state` | Internal state inconsistency |
| `pre_execution_audit_missing_required_field` | Required field missing from audit package |
| `pre_execution_audit_serialization_failed` | JSON serialization error |
| `pre_execution_audit_written_but_handler_lookup_not_enabled` | Audit written, still blocked |
| `handler_lookup_not_enabled` | Handler lookup not yet approved |

### Failure Invariants

All failures must:

- Block before handler lookup
- `executionAllowed = false`
- `dispatchAllowed = false`
- `providerSchemaAllowed = false`
- `toolHandlerCalled = false`
- `providerApiCalled = false`
- `executionStarted = false`

---

## 14. Future Success Contract

If pre-execution audit write succeeds:

1. Response may include `preExecutionAuditId`
2. Response may include `executeRequestId`
3. Response must still be blocked
4. Final decision should be `blocked_handler_lookup_not_enabled`
5. Side-effect flags must remain `false`
6. No handler lookup
7. No dispatch
8. No execution
9. No provider call

Pre-execution audit success must not be interpreted as execution success.

---

## 15. Future Execute Gate Order

### Current State

| Gate Range | Description |
|------------|-------------|
| Gates 1–14 | Existing: kill switch, allowlist, dry-run lookup, dry-run binding gates |
| Gates 15–27 | Confirmation token verification gates |
| Gates 28–37 | Digest verification gates |
| Current final block | `blocked_pre_execution_audit_not_implemented` |

### Future Pre-Execution Audit Implementation Target

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

### Post-Audit Block

After pre-execution audit succeeds, execute still blocks.

The next allowed block boundary is `blocked_handler_lookup_not_enabled`.

No Tool Handler call is allowed in pre-execution audit implementation.

---

## 16. Future OpenAPI Strategy

### Phase 1G-04-23

Phase 1G-04-23 does not modify OpenAPI.

### Future Schema-Only Changes

Future pre-execution audit implementation may require schema-only OpenAPI changes:

- `ToolExecuteData.preExecutionAuditId`
- `ToolExecuteData.executeRequestId`
- `ToolExecuteData.preExecutionAuditStatus`
- `ToolExecuteErrorCode.pre_execution_audit_*` values
- `ToolExecuteDecision.blocked_handler_lookup_not_enabled`
- Gate status pre-execution audit gate names

### Route Constraints

- No new OpenAPI path unless separately approved
- OpenAPI paths should remain 33
- Runtime routes should remain 33
- Tool write routes should remain 0
- Tool execution routes should remain 1

---

## 17. Future Route Governance Strategy

### Preferred

No new route.

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 (unchanged) |
| Runtime routes | 33 (unchanged) |
| Tool GET routes | 4 (unchanged) |
| Tool write routes | 0 (unchanged) |
| Tool dry-run routes | 1 (unchanged) |
| Tool execution routes | 1 (unchanged) |

### If Route Change Required

If future pre-execution audit implementation requires a route change:

- Must stop and create a separate route-governed scope freeze
- Must not bundle route changes into pre-execution audit implementation

---

## 18. Future Allowed Files

These are future allowed files for the pre-execution audit implementation phase only. They are **not** modified in Phase 1G-04-23, except docs files allowed by this docs-only phase.

### Backend

- `hermes_cli/dev_web_tool_pre_execution_audit.py` (new)
- `hermes_cli/dev_web_tool_execute.py` (modify)
- `hermes_cli/dev_web_tool_execute_digest.py` (modify)
- `hermes_cli/dev_web_tool_execute_confirmation.py` (modify)
- `hermes_cli/dev_web_tool_execute_preflight.py` (modify)
- `hermes_cli/dev_web_api.py` (modify)

### OpenAPI

- `docs/webui/openapi/dev-web-api-v1.yaml` (schema-only)

### Tests

- `tests/test_dev_web_tool_pre_execution_audit.py` (new)
- `tests/test_dev_web_tool_execute.py` (modify)
- `tests/test_dev_web_tool_execute_api.py` (modify)
- `tests/test_dev_web_tool_execute_digest.py` (modify)
- `tests/test_dev_web_tool_execute_confirmation.py` (modify)
- `tests/test_dev_web_tool_execute_preflight.py` (modify)
- `tests/test_dev_check_webui.py` (modify)
- `tests/test_dev_web_0c06_closure.py` (modify)

### Docs

- `docs/webui/phase-1g-04-23-pre-execution-audit-scope.md` (this document)
- `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` (modify)
- `docs/webui/phase-1-implementation-plan.md` (modify)

---

## 19. Future Forbidden Files

The following files must not be modified during future pre-execution audit implementation:

- `apps/hermes-dev-webui/src/`
- `apps/hermes-dev-webui/tests/`
- `apps/hermes-dev-webui/e2e/`
- `agent/`
- `tools/`
- `toolsets.py`
- Runtime files committed to repo
- Memory files
- Review files
- `.env`
- `.claude/`
- `~/.hermes`
- Production `state.db`
- `setup-hermes.sh`
- Global hermes command
- Provider config files
- Production gateway state files

---

## 20. Future Test Matrix

### Audit Package Tests (12 tests)

| # | Test |
|---|------|
| 1 | Pre-execution audit package includes required fields |
| 2 | Package includes `dryRunRequestId` |
| 3 | Package includes `dryRunDecisionDigest` |
| 4 | Package includes `confirmationTokenId` |
| 5 | Package includes digest metadata |
| 6 | Package includes side-effect flags (all `false`) |
| 7 | Package excludes raw token |
| 8 | Package excludes `tokenHash` full value |
| 9 | Package excludes raw arguments |
| 10 | Package excludes secrets |
| 11 | Package excludes provider credentials |
| 12 | Package excludes Provider Schema |

### Path Guard Tests (7 tests)

| # | Test |
|---|------|
| 13 | Dev audit path allowed under `$HERMES_HOME/gateway/dev/audit` |
| 14 | Exact production home blocks before write |
| 15 | Production subtree blocks before write |
| 16 | Symlink into production blocks before write |
| 17 | Path traversal into production blocks before write |
| 18 | `.hermes-dev` sibling path is not falsely blocked |
| 19 | Path guard failure does not open audit file |

### Write Behavior Tests (7 tests)

| # | Test |
|---|------|
| 20 | Write succeeds after valid token + valid digest |
| 21 | Write fails closed when audit directory unavailable |
| 22 | Write fails closed on serialization error |
| 23 | Missing required field blocks |
| 24 | Append-only write does not mutate previous records |
| 25 | `preExecutionAuditId` returned only after successful write |
| 26 | `executeRequestId` returned only after successful write |

### Execute Gate Tests (9 tests)

| # | Test |
|---|------|
| 27 | Valid token + valid digest + audit write failure blocks |
| 28 | Valid token + valid digest + audit write success still blocks |
| 29 | Final block is `blocked_handler_lookup_not_enabled` |
| 30 | No handler lookup after audit success |
| 31 | No dispatch after audit success |
| 32 | No execution after audit success |
| 33 | No Provider Schema after audit success |
| 34 | No Provider API after audit success |
| 35 | Side-effect flags remain `false` after audit success |

### Idempotency / Retry Tests (5 tests)

| # | Test |
|---|------|
| 36 | Reused token blocks before second audit write |
| 37 | Duplicate request with consumed token does not write second pre-execution audit |
| 38 | Second valid token can write a separate audit record |
| 39 | `preExecutionAuditId` uniqueness |
| 40 | `executeRequestId` uniqueness |

### Security Invariant Tests (10 tests)

| # | Test |
|---|------|
| 41 | All pre-execution audit failures block before handler lookup |
| 42 | All failures keep side-effect flags `false` |
| 43 | Raw token never appears in audit JSONL |
| 44 | `tokenHash` full never appears in audit JSONL |
| 45 | Raw arguments never appear in audit JSONL |
| 46 | Secrets never appear in audit JSONL |
| 47 | Provider is never called |
| 48 | Tool Handler is never called |
| 49 | Dispatch is never called |
| 50 | Execution is never started |

### Route Governance Tests (5 tests)

| # | Test |
|---|------|
| 51 | OpenAPI paths remain 33 unless separately approved |
| 52 | Runtime routes remain 33 unless separately approved |
| 53 | Tool write routes remain 0 |
| 54 | Tool execution routes remain 1 |
| 55 | `STATIC_ALLOWLIST` remains `{"clarify"}` |

---

## 21. Future Implementation Entry Criteria

1. Phase 1G-04-23 docs pushed
2. No P0/P1 open issues
3. User explicitly approves pre-execution audit implementation
4. Remote and local branch synchronized
5. `STATIC_ALLOWLIST` remains exactly `{"clarify"}`
6. Route governance green
7. Confirmation token gate green
8. Digest verification gate green
9. Valid token + valid digest currently blocks at pre-execution audit boundary
10. Provider schema not sent
11. Tool dispatch disabled
12. Tool execution disabled
13. Production gateway stable

---

## 22. Future Implementation Exit Criteria

1. Pre-execution audit package builder implemented
2. Pre-execution audit path guard implemented
3. Pre-execution audit writer implemented
4. Pre-execution audit JSONL store implemented
5. Pre-execution audit write after valid token + valid digest implemented
6. Pre-execution audit failure blocks
7. Pre-execution audit success still blocks at handler lookup boundary
8. `preExecutionAuditId` returned after successful write
9. `executeRequestId` returned after successful write
10. No handler lookup after audit success
11. No Tool Handler call after audit success
12. No dispatch after audit success
13. No execution after audit success
14. No Provider Schema after audit success
15. No Provider API after audit success
16. OpenAPI paths remain 33 unless separately approved
17. Runtime routes remain 33 unless separately approved
18. Tool write routes remain 0
19. Tool execution routes remain 1
20. `STATIC_ALLOWLIST` remains `{"clarify"}`
21. Production gateway unaffected

---

## 23. Acceptance Criteria for Phase 1G-04-23

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only | ✅ |
| 2 | New pre-execution audit scope doc added | ✅ |
| 3 | Phase 1G-04 scope doc updated | ✅ |
| 4 | Implementation plan updated | ✅ |
| 5 | Phase 1G-04-22 doc updated with next dependency | ✅ |
| 6 | No code changes | ✅ |
| 7 | No OpenAPI file changes | ✅ |
| 8 | No tests changed | ✅ |
| 9 | No frontend changes | ✅ |
| 10 | No routes changed | ✅ |
| 11 | No execute route behavior changes | ✅ |
| 12 | No token behavior changes | ✅ |
| 13 | No digest behavior changes | ✅ |
| 14 | No `STATIC_ALLOWLIST` changes | ✅ |
| 15 | `STATIC_ALLOWLIST` remains `frozenset({"clarify"})` | ✅ |
| 16 | No pre-execution audit implementation | ✅ |
| 17 | No post-execution audit | ✅ |
| 18 | No Tool Handler call | ✅ |
| 19 | No Tool Dispatch | ✅ |
| 20 | No Tool Execution | ✅ |
| 21 | No Provider Schema sent | ✅ |
| 22 | No Provider API called | ✅ |
| 23 | OpenAPI paths still 33 | ✅ |
| 24 | Runtime routes still 33 | ✅ |
| 25 | Tool GET 4 | ✅ |
| 26 | Tool write 0 | ✅ |
| 27 | Tool dry-run 1 | ✅ |
| 28 | Tool execution 1 | ✅ |
| 29 | Execute route remains blocked-only | ✅ |
| 30 | Real Controlled Execution not started | ✅ |
| 31 | Local docs-only commit created | ✅ |
| 32 | Not pushed | ✅ |

---

## 24. P0 / P1 / P2 Risk

### P0 (Block Immediately)

- Code modified
- OpenAPI modified
- Tests modified
- Frontend modified
- Route count changed
- Execute route behavior changed
- `STATIC_ALLOWLIST` changed
- Allowlist expanded
- Pre-execution audit implemented (premature)
- Post-execution audit implemented
- Handler lookup enabled
- Tool Handler called
- Tool Dispatch called
- Tool executed
- Provider API called
- Provider Schema sent
- Production Gateway affected
- Real secret leaked

### P1 (Block, Do Not Claim Complete)

- Pre-execution audit goal missing from docs
- Dry-run audit difference missing from docs
- Confirmation token relationship missing from docs
- Digest relationship missing from docs
- Handler lookup relationship missing from docs
- Write timing missing from docs
- Audit store path missing from docs
- Path guard strategy missing from docs
- Event structure missing from docs
- ID strategy missing from docs
- Idempotency strategy missing from docs
- Failure contract missing from docs
- Success contract missing from docs
- Future gate order missing from docs
- Future OpenAPI strategy missing from docs
- Future route governance missing from docs
- Future allowed files missing from docs
- Future forbidden files missing from docs
- Future test matrix missing from docs
- Entry criteria missing from docs
- Exit criteria missing from docs
- Docs incorrectly claim pre-execution audit implemented
- Docs incorrectly claim handler lookup enabled
- Route governance test failed
- `OpenAPI paths != 33`
- `Runtime routes != 33`
- `STATIC_ALLOWLIST != {"clarify"}`

### P2 (Acceptable, Record Only)

- Pre-execution audit not yet implemented
- Post-execution audit not yet implemented
- Execute route still does not execute tools
- Handler lookup not yet enabled
- Frontend execute UI not implemented
- Browser smoke not re-run
- Audit read API not yet implemented
- Audit viewer not yet implemented
- Clarify handler-level audit requires future phase
- Lookup performance can be optimized later
- Multi-file audit rotation support may be future work
- Append-only JSONL audit write race conditions need future local-dev handling

---

*Phase 1G-04-23 Pre-Execution Audit Scope Freeze: pre-execution audit goal, dry-run audit difference, confirmation token relationship, digest verification relationship, handler lookup relationship, write timing, event structure, store path, path guard, ID strategy, idempotency strategy, failure contract, success contract, future execute gate order, future OpenAPI strategy, future route governance, future allowed/forbidden files, future test matrix, entry/exit criteria frozen. Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no pre-execution audit implementation, no post-execution audit, no handler lookup, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*

---

## Implementation Status (Phase 1G-04-24)

The following items from this scope document were implemented in Phase 1G-04-24:

- Minimal pre-execution audit package builder implemented
- Pre-execution audit containment-based path guard implemented
- Pre-execution audit append-only JSONL writer implemented
- Pre-execution audit store implemented (`$HERMES_HOME/gateway/dev/audit/tool-pre-execution-audit.jsonl`)
- `preExecutionAuditId` generation and return implemented
- `executeRequestId` generation and return implemented
- Execute route pre-execution audit gates (Gates 38–45) implemented
- Valid token + valid digest + pre-execution audit written still blocks at `blocked_handler_lookup_not_enabled`
- Pre-execution audit write failure fail-closed implemented
- Safe audit identifiers in response implemented
- OpenAPI schema-only updates applied
- Backend tests (49 new tests) implemented

Still not implemented:
- Post-execution audit
- Handler lookup
- Dispatch
- Execution
- Provider call
- Real Controlled Execution
