# Phase 1G-04-08: Controlled Execution Scope / Gate Design Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-08 |
| Title | Controlled Execution Scope / Gate Design Freeze |
| Status | Frozen (scope/gate design only, no implementation) |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-08 scope/gate design freeze) |
| Dependencies | Phase 1G-04-07 completed locally |
| Branch | dev-huangruibang |
| Base commit | 5bed1369b3d2927a304ea094e16d516d8f639ee7 |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Defines the future Controlled Execution gate stack and scope boundaries
2. Freezes the gate design for all future execution pathways
3. Defines kill switch design, allowlist strategy, and human confirmation requirements
4. Defines dry-run preflight requirements and audit preconditions
5. Defines provider schema, tool handler, and execution result boundaries
6. Defines future API, OpenAPI, frontend, and test strategies
7. Defines risk tier eligibility for future execution
8. Records acceptance criteria and P0/P1/P2 risk classification
9. Does **not** implement Controlled Execution
10. Does **not** add execution routes, audit read APIs, or audit viewer UI

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-08 = **Controlled Execution Scope / Gate Design Freeze**

- This phase freezes the future Controlled Execution gate design only.
- This phase does **not** implement Controlled Execution.
- This phase does **not** enable Tool Execution.
- This phase does **not** add execution routes.
- This phase does **not** modify OpenAPI paths.
- This phase does **not** modify STATIC_ALLOWLIST.
- This phase does **not** call tool handlers.
- This phase does **not** call providers.
- This phase does **not** add audit read APIs.
- This phase does **not** add audit viewer UI.
- This phase does **not** modify frontend source.
- This phase does **not** modify tests.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `5bed1369b3d2927a304ea094e16d516d8f639ee7` |
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |
| Dry-Run API | Implemented (`POST /api/dev/v1/tools/dry-run`) |
| Dry-Run Audit Writer | Implemented (`dev_web_tool_dry_run_audit.py`) |
| `auditWritten` | Audit write success only (not execution) |
| Controlled Execution | Not started |
| STATIC_ALLOWLIST | Empty (empty frozenset) |
| Provider Schema Sending | Not sent |
| Tool Dispatch | 0 |
| Tool Execution | Disabled |
| Tool Handler Invocation | None |
| Kill Switches | All disabled (unset) |

---

## 3. Controlled Execution Goal

The future Controlled Execution capability, if implemented, would allow certain low-risk, local-development, safety-eligible tools to execute under extremely strict gate controls.

### 3.1 Core Goals

1. **Gated execution only:** Execution requires passing a multi-layer gate stack before any tool handler is invoked.
2. **Dry-run first:** Every execution must originate from a prior dry-run that returned `would_allow`.
3. **Audit precondition:** Dry-run audit write must succeed before execution proceeds.
4. **Human confirmation:** Every execution requires explicit human confirmation bound to the exact request.
5. **Static allowlist:** Only tools in STATIC_ALLOWLIST may be eligible for execution; the allowlist is populated by explicit review only.
6. **Kill switches:** Execution is disabled by default and must be explicitly enabled via environment variables.
7. **Risk tier eligibility:** Only R0 and R1 tools are considered for initial execution eligibility; R4/R5 are permanently blocked.
8. **Audit trail:** Every execution must produce a pre-execution and post-execution audit event.
9. **Timeout and size limits:** Execution must have configurable timeout and output size limits.
10. **Result sanitization:** Execution results must be sanitized before response.
11. **Failure safety:** Any gate failure must block execution without calling tool handlers or providers.
12. **Rollback guarantee:** Execution failure must not mutate policy state, allowlist, or audit records.

### 3.2 Explicit Non-Properties

Controlled Execution does **not**:

- Enable arbitrary tool execution
- Send tool schemas to providers
- Modify STATIC_ALLOWLIST automatically
- Bypass any gate for any tool
- Execute tools in production
- Execute R4/R5 tools under any circumstance
- Execute denylisted tools under any circumstance

---

## 4. Non-Goals

The following are explicitly **not** part of Phase 1G-04-08:

1. No implementation of Controlled Execution
2. No tool execution
3. No new execution route
4. No new Tool Dispatch
5. No new Tool Handler invocation
6. No Provider Schema sending
7. No Provider API call
8. No new audit viewer UI
9. No new audit read/search/export API
10. No frontend modification
11. No OpenAPI modification
12. No STATIC_ALLOWLIST modification
13. No allowlist population
14. No risk tier changes
15. No Dry-Run policy decision changes
16. No audit writer modification
17. No production runtime modification
18. No route count changes
19. No code changes of any kind
20. No test changes

---

## 5. Future Execution Gate Stack

The following gate stack defines the required sequence of checks that must all pass before any tool handler invocation occurs. **Failure of any single gate blocks execution entirely.**

### 5.1 Gate Definitions

| Gate | Name | Description | Failure Behavior |
|------|------|-------------|-----------------|
| Gate 0 | Build-time capability | Tool execution capability exists only in `dev_web_api.py` under a controlled execution section; not available in production builds | Feature absent — no route registered |
| Gate 1 | Runtime kill switch | `HERMES_TOOL_EXECUTION_ENABLED` must be explicitly set to `"true"` | Return `EXECUTION_DISABLED` |
| Gate 2 | Agent/tool switch | `HERMES_AGENT_TOOLS_ENABLED` must be explicitly set to `"true"` | Return `AGENT_TOOLS_DISABLED` |
| Gate 3 | Provider schema switch | Provider/tool schema exposure must remain separately controlled (future switch, currently always disabled) | Return `PROVIDER_SCHEMA_DISABLED` |
| Gate 4 | Static allowlist | `STATIC_ALLOWLIST` must contain the canonical tool name | Return `NOT_IN_ALLOWLIST` |
| Gate 5 | Denylist check | Tool must **not** be in `STATIC_DENYLIST` | Return `DENYLISTED` |
| Gate 6 | Risk tier eligibility | Tool risk tier must be R0 or R1 (initial implementation); R2 requires explicit review; R3/R4/R5 blocked | Return `RISK_TIER_INELIGIBLE` |
| Gate 7 | Dry-run decision | Dry-run result must be `would_allow` | Return `DRY_RUN_DECISION_NOT_ALLOW` |
| Gate 8 | Dry-run audit write | Dry-run audit event write must have succeeded (precondition) | Return `AUDIT_PRECONDITION_FAILED` |
| Gate 9 | Human confirmation | Confirmation token/nonce must match request, be non-expired, and bound to correct tool | Return `CONFIRMATION_INVALID` |
| Gate 10 | Canonical name match | Request `canonicalName` must match the confirmed tool exactly | Return `CANONICAL_NAME_MISMATCH` |
| Gate 11 | Argument digest match | Request arguments must match the preflight dry-run arguments digest | Return `ARGUMENT_DIGEST_MISMATCH` |
| Gate 12 | Timeout and size limits | Execution must have configured timeout and max output size | Return `EXECUTION_CONFIG_INVALID` |
| Gate 13 | Result sanitization | Execution result must be sanitized before response | Internal — result filtered |
| Gate 14 | Post-execution audit | Post-execution audit event must be attempted (best-effort, does not block response) | Internal — logged |

### 5.2 Gate Failure Invariants

Regardless of which gate fails:

1. **No Tool Handler call** — the tool's registered function is never invoked
2. **No Provider call** — no LLM provider API is called
3. **No Tool Dispatch** — no dispatch routing occurs
4. **Safe blocked response** — a structured error response is returned with the gate failure reason
5. **No state mutation** — no policy, allowlist, audit, or configuration state is modified
6. **Audit record** — gate failure is recorded as an audit event (pre-execution audit)

---

## 6. Kill Switch Design

### 6.1 Kill Switch Inventory

| Switch | Purpose | Default State |
|--------|---------|--------------|
| `HERMES_TOOL_EXECUTION_ENABLED` | Master switch for tool execution in Dev WebUI | Unset / disabled |
| `HERMES_AGENT_TOOLS_ENABLED` | Agent tool loop enable switch | Unset / disabled |
| `HERMES_AGENT_RUN_ENABLED` | Agent run enable switch (existing from Phase 1F) | Unset / disabled |

Future additional switches may include:

| Switch | Purpose | Default State |
|--------|---------|--------------|
| `HERMES_PROVIDER_SCHEMA_ENABLED` | Provider schema exposure control | Unset / disabled (future) |

### 6.2 Kill Switch Contract

1. **Unset = false** — if the environment variable is not set, the capability is disabled
2. **Empty = false** — if the environment variable is set to an empty string, the capability is disabled
3. **Any value except explicit `"true"` = false** — only the literal string `"true"` enables the capability
4. **Production default = false** — production environments must never have these switches set to `"true"`
5. **Dev default = false** — even in development, the switches default to disabled
6. **Tests must verify false by default** — all tests must confirm the default-off behavior

### 6.3 Kill Switch Limitation

**Even if all kill switches are `true`, execution is still blocked by:**

- STATIC_ALLOWLIST (must contain the tool)
- Denylist (must not contain the tool)
- Risk tier eligibility (R0/R1 only initially)
- Dry-run decision (must be `would_allow`)
- Audit precondition (must succeed)
- Human confirmation (must match and be non-expired)
- Argument digest (must match preflight)

Kill switches are **necessary but not sufficient** for execution.

---

## 7. Allowlist Strategy

### 7.1 Current State

- `STATIC_ALLOWLIST` is currently an empty frozenset
- Phase 1G-04-08 must **not** modify `STATIC_ALLOWLIST`
- Future allowlist activation must be a **separate phase** with explicit review

### 7.2 Future Activation Principles

1. **One-by-one review:** Each tool added to STATIC_ALLOWLIST must be individually reviewed
2. **Risk-tier gated:** Only R0/R1 tools may be considered for initial allowlisting
3. **Audit trail required:** Each allowlist addition must be recorded in an audit trail
4. **Separate commit:** Allowlist population requires a separate, reviewed commit
5. **No automatic promotion:** No tool is automatically promoted from CANDIDATE_ALLOWLIST to STATIC_ALLOWLIST

### 7.3 Risk Tier Eligibility

| Risk Tier | Future Execution Eligibility | Notes |
|-----------|------------------------------|-------|
| R0 (Pure Computation) | Eligible after all gates pass | Lowest risk — 1 tool (`skill_match`) |
| R1 (Read-Only Local Query) | Eligible after all gates pass | Local read only — 5 tools |
| R2 (Read-Only External Network) | Requires explicit review; not first execution target | Network-dependent — 19 tools |
| R3 (Controlled Write) | Blocked for Controlled Execution initial implementation | Side effects — 26 tools |
| R4 (Process/Execution) | Blocked | Shell/browser/subagent — 17 tools |
| R5 (High-Risk System) | Blocked | Cron/admin/IoT — 3 tools |
| Denylist (26 tools) | Permanently blocked | Always blocked regardless of risk tier |
| Unknown tool | Always blocked | Not in inventory |

### 7.4 Candidate Allowlist Remains Advisory

- `CANDIDATE_ALLOWLIST` (6 tools) remains advisory only
- Candidate status does **not** imply execution approval
- Candidate status does **not** imply STATIC_ALLOWLIST membership
- Candidate status does **not** permit provider schema sending

---

## 8. Human Confirmation Design

### 8.1 Confirmation Token

Future execution requests must include a human confirmation token that is:

1. **Generated after dry-run preflight:** The token is created only after a successful dry-run that returned `would_allow`
2. **Bound to specific request parameters:**
   - `canonicalName` — the exact tool name
   - `sanitizedArgumentDigest` — SHA-256 digest of the sanitized arguments
   - `riskTier` — the tool's risk tier
   - `decision` — the dry-run decision (`would_allow`)
   - `requestId` — the original dry-run request correlation ID
   - `timestamp` — when the token was generated (ISO 8601 UTC)
   - `expiry` — token expiration time (recommended: 5 minutes from generation)

### 8.2 Confirmation Failure Modes

| Failure Mode | Behavior |
|-------------|----------|
| Token mismatch | Block execution; return `CONFIRMATION_INVALID` |
| Token expired | Block execution; return `CONFIRMATION_EXPIRED` |
| Argument digest mismatch | Block execution; return `ARGUMENT_DIGEST_MISMATCH` |
| Different canonicalName | Block execution; return `CANONICAL_NAME_MISMATCH` |
| Different risk tier | Block execution; return `RISK_TIER_MISMATCH` |
| Token missing | Block execution; return `CONFIRMATION_REQUIRED` |
| Token reuse | Block execution; return `CONFIRMATION_ALREADY_USED` (tokens are single-use) |

### 8.3 Prohibited Confirmation Patterns

The following are **never** allowed:

- UI auto-confirmation — the user must explicitly click/confirm
- Provider auto-confirmation — no automated confirmation from any provider
- Implicit confirmation — no confirmation inferred from user behavior
- Confirmation bypass — no code path that skips the confirmation gate
- Batch confirmation — each execution requires its own confirmation token

---

## 9. Dry-Run Preflight Requirement

### 9.1 Dry-Run First Policy

Future execution **must always originate from a dry-run**:

1. A dry-run request is submitted first via `POST /api/dev/v1/tools/dry-run`
2. The dry-run result must have `decision = would_allow`
3. The dry-run result must have `executionAllowed = false` (dry-run never enables execution)
4. The dry-run audit event must be written successfully (audit precondition)
5. A confirmation token is generated from the dry-run result
6. The future execute request must reference the dry-run `requestId` or argument digest
7. Execution arguments must match the dry-run arguments digest exactly

### 9.2 Dry-Run Remains Non-Executing

- Dry-run is and remains a **non-executing simulation**
- Dry-run audit success is a **precondition** for execution, not execution itself
- `auditWritten = true` in a dry-run response means the audit event was recorded — it does **not** mean the tool was executed
- No amount of dry-run calls enables execution without passing all subsequent gates

---

## 10. Audit Preconditions

### 10.1 Pre-Execution Audit

1. Pre-execution audit event must be written **before** any Tool Handler call
2. Pre-execution audit must include: canonicalName, riskTier, decision, confirmation token reference, timestamp
3. Pre-execution audit must **not** include: raw arguments, secrets, provider keys
4. Pre-execution audit failure **blocks execution** — the handler is never invoked

### 10.2 Post-Execution Audit

1. Post-execution audit event must be attempted **after** handler completion (success or failure)
2. Post-execution audit must include: execution result summary, duration, success/failure status
3. Post-execution audit must **not** include: raw result content, stack traces, secrets
4. Post-execution audit failure is **reported safely** — does not block the response, but is logged

### 10.3 Audit Content Restrictions

All audit records (pre and post execution) must **never** contain:

- Raw secrets, API keys, tokens, or credentials
- Provider keys or authorization headers
- Full unredacted argument payloads or result content
- Handler references, callable objects, or internal file paths
- Stack traces from handler execution

### 10.4 Current Phase Status

- **Pre-execution audit design only** — no execution audit implemented in Phase 1G-04-08
- Existing dry-run audit writer (`dev_web_tool_dry_run_audit.py`) records dry-run decisions only
- Execution audit requires separate implementation phase

---

## 11. Provider Schema Boundary

### 11.1 Provider Schema Sending Remains Disabled

1. **Controlled Execution does not imply Provider Schema Sending.**
2. Tool execution route, if implemented later, must **not** automatically expose tool schemas to providers.
3. Provider schema exposure requires a **separate phase** with:
   - Separate scope freeze document
   - Separate kill switch (`HERMES_PROVIDER_SCHEMA_ENABLED` or equivalent)
   - Separate audit trail
   - Separate human confirmation
   - Separate risk analysis

### 11.2 Separation Principle

| Capability | Separate Phase Required | Separate Kill Switch |
|-----------|------------------------|---------------------|
| Tool Dry-Run | Already implemented (1G-04-04) | N/A (non-executing) |
| Dry-Run Audit | Already implemented (1G-04-07) | N/A (internal) |
| Controlled Execution | Required (future) | `HERMES_TOOL_EXECUTION_ENABLED` |
| Provider Schema Sending | Required (future) | `HERMES_PROVIDER_SCHEMA_ENABLED` |

---

## 12. Tool Handler Boundary

### 12.1 Handler Invocation Conditions

Future Tool Handler invocation is only allowed **after all gates pass**:

1. Kill switches must be enabled
2. Tool must be in STATIC_ALLOWLIST
3. Tool must not be in STATIC_DENYLIST
4. Risk tier must be eligible
5. Dry-run must have returned `would_allow`
6. Audit preconditions must have succeeded
7. Human confirmation must be valid and non-expired
8. Argument digest must match

### 12.2 Handler Isolation Requirements

1. **Policy decision and handler lookup must be isolated** — the policy engine that decides `would_allow` must be independent of the handler invocation mechanism
2. **Handler invocation must be guarded** — the handler is called only from the execution path, never from the dry-run path
3. **Safe audit logging** — safe audit events must be logged before and after handler call (no raw content)

### 12.3 Phase 1G-04-08 Status

- This phase does **not** call any Tool Handler
- This phase does **not** import any Tool Handler module
- This phase does **not** reference any handler function

---

## 13. Execution Result Boundary

### 13.1 Result Sanitization

Future execution results must be:

1. **Sanitized** — all secrets, paths, and internal references redacted
2. **Size-limited** — maximum serialized response size (recommended: 64 KiB)
3. **Timeout-limited** — maximum execution time per risk tier (R0: 2s, R1: 5s, hard max: 30s)
4. **Stack-trace-free** — no stack traces in responses to the frontend
5. **Secret-free** — no raw secrets in any response field

### 13.2 Failure Safety

1. **Execution failure must not mutate policy state** — allowlist, denylist, and risk tiers remain unchanged
2. **Execution failure must not modify STATIC_ALLOWLIST** — no automatic addition or removal
3. **Execution failure must not modify audit records** — existing audit events are append-only and immutable
4. **Execution timeout must be enforced** — timeout kills the handler execution and returns a safe error
5. **Output size overflow must be handled** — oversized results are truncated with a warning, not rejected entirely

---

## 14. Future API Strategy

### 14.1 No New API in Phase 1G-04-08

No new API route is added in this phase. All existing routes remain unchanged.

### 14.2 Future Execution API Design

If Controlled Execution is implemented in a future phase, the recommended route is:

```
POST /api/dev/v1/tools/execute
```

**This route is NOT added in Phase 1G-04-08.**

Future execution route must:

1. Accept: `canonicalName`, `arguments`, `confirmationToken`, `dryRunRequestId`
2. Process all gates in sequence (Gate 0 through Gate 14)
3. Return structured result on success or structured error on gate failure
4. Maintain separation from the existing dry-run route

### 14.3 OpenAPI Impact

- OpenAPI remains unchanged in Phase 1G-04-08
- Runtime routes remain unchanged in Phase 1G-04-08
- Future OpenAPI additions require separate scope freeze and implementation phase

---

## 15. Future OpenAPI Strategy

### 15.1 No OpenAPI Changes

No OpenAPI paths, schemas, or properties are added or modified in Phase 1G-04-08.

### 15.2 Future Execution OpenAPI Schemas

Future execution OpenAPI schemas must distinguish the following response types:

| Response Type | Description |
|--------------|-------------|
| `preflight_blocked` | Dry-run precondition failed |
| `confirmation_failed` | Human confirmation invalid/expired/mismatched |
| `audit_failed` | Pre-execution audit write failed |
| `handler_failed` | Tool handler raised an exception |
| `execution_succeeded` | All gates passed, handler returned successfully |
| `execution_timeout` | Handler exceeded time limit |
| `output_too_large` | Result exceeded size limit |

### 15.3 Schema Naming Convention

Future OpenAPI schema names should follow the established pattern:

- `ToolExecuteRequest`
- `ToolExecuteResponse`
- `ToolExecuteData`
- `ToolExecuteError`
- `ToolExecuteConfirmation`

---

## 16. Future Frontend Strategy

### 16.1 No Frontend Changes

No frontend source, components, stores, routes, or styles are modified in Phase 1G-04-08.

### 16.2 Future Execute Button Requirements

When Controlled Execution is implemented in a future phase:

1. **No Execute button until all backend gates exist** — the UI must not display an Execute button until the backend execution route is fully implemented and tested
2. **Explicit confirmation required** — the Execute button must require a deliberate user action (e.g., hold-to-confirm, or explicit "I understand this will execute the tool" acknowledgment)
3. **Information display** — the UI must display:
   - Risk tier of the tool
   - Denylist / allowlist status
   - Dry-run decision
   - Audit precondition status
   - Confirmation digest
4. **Visual distinction** — the Execute button must be visually distinct from the Dry-Run button (different color, different label, different icon)
5. **No auto-execute** — no code path that automatically executes without explicit user action
6. **Disabled by default** — the Execute button must be disabled until the user has completed dry-run and received `would_allow`

---

## 17. Test Plan (Future, Not Implemented)

The following tests must pass before Controlled Execution is considered complete:

### 17.1 Kill Switch Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Kill switches default to false | All disabled by default |
| 2 | Kill switches require explicit `"true"` | `"false"`, `""`, unset all = disabled |
| 3 | Kill switch `HERMES_TOOL_EXECUTION_ENABLED = true` does not bypass allowlist | Still blocked |

### 17.2 Allowlist Tests

| # | Test | Expected |
|---|------|----------|
| 4 | STATIC_ALLOWLIST empty blocks all execution | No tool executes |
| 5 | Tool in STATIC_ALLOWLIST passes allowlist gate | Gate passes |
| 6 | Tool not in STATIC_ALLOWLIST fails allowlist gate | Gate fails |
| 7 | Denylist blocks execution even if in allowlist | Always blocked |

### 17.3 Risk Tier Tests

| # | Test | Expected |
|---|------|----------|
| 8 | R0 eligible after all gates | Can execute if all gates pass |
| 9 | R1 eligible after all gates | Can execute if all gates pass |
| 10 | R2 requires review / blocked initially | Cannot execute initially |
| 11 | R3/R4/R5 blocked | Cannot execute |
| 12 | Unknown tool blocked | Cannot execute |

### 17.4 Dry-Run Preflight Tests

| # | Test | Expected |
|---|------|----------|
| 13 | Dry-run decision required | No execution without dry-run |
| 14 | Dry-run `would_block` blocks execution | Cannot proceed |
| 15 | Dry-run audit write required | Blocks if audit not written |
| 16 | Dry-run arguments digest must match | Mismatch blocks execution |

### 17.5 Human Confirmation Tests

| # | Test | Expected |
|---|------|----------|
| 17 | Confirmation required | No execution without confirmation |
| 18 | Token mismatch blocks execution | `CONFIRMATION_INVALID` |
| 19 | Token expiry blocks execution | `CONFIRMATION_EXPIRED` |
| 20 | Argument digest mismatch blocks execution | `ARGUMENT_DIGEST_MISMATCH` |
| 21 | canonicalName mismatch blocks execution | `CANONICAL_NAME_MISMATCH` |

### 17.6 Security Boundary Tests

| # | Test | Expected |
|---|------|----------|
| 22 | Tool Handler not called when blocked | No handler invocation |
| 23 | Provider not called when blocked | No provider invocation |
| 24 | Dispatch not called when blocked | No dispatch routing |
| 25 | Execution timeout enforced | Timeout kills handler |
| 26 | Execution result sanitized | No secrets in result |
| 27 | Execution result size limit enforced | Oversized results truncated |

### 17.7 Audit Tests

| # | Test | Expected |
|---|------|----------|
| 28 | Pre-execution audit failure blocks execution | Handler not called |
| 29 | Post-execution audit failure reported safely | Response returned, error logged |
| 30 | Audit never stores raw secrets | Redacted in all events |

### 17.8 Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 31 | Route governance counts controlled | No unexpected route additions |
| 32 | OpenAPI path count controlled | No unexpected path additions |

---

## 18. Acceptance Criteria

### 18.1 Documentation

| # | Criterion |
|---|-----------|
| 1 | Controlled execution gate scope doc added |
| 2 | Phase 1G-04 scope doc updated |
| 3 | Implementation plan updated |
| 4 | Gate stack defined with 15 gates |
| 5 | Kill switch design defined |
| 6 | Allowlist strategy defined |
| 7 | Human confirmation design defined |
| 8 | Dry-run preflight requirement defined |
| 9 | Audit preconditions defined |
| 10 | Provider schema boundary defined |
| 11 | Tool handler boundary defined |
| 12 | Execution result boundary defined |
| 13 | Future API strategy defined |
| 14 | Future OpenAPI strategy defined |
| 15 | Future frontend strategy defined |
| 16 | Test plan defined (32 tests) |

### 18.2 Security Boundary

| # | Criterion |
|---|-----------|
| 17 | docs-only changes |
| 18 | no code changes |
| 19 | no OpenAPI changes |
| 20 | no tests changed |
| 21 | no frontend changes |
| 22 | no routes changed |
| 23 | no execution route added |
| 24 | no audit read API added |
| 25 | no audit viewer added |
| 26 | no Tool Handler called |
| 27 | no Tool Dispatch |
| 28 | no Tool Execution |
| 29 | no Provider Schema sent |
| 30 | no Provider API called |
| 31 | STATIC_ALLOWLIST unchanged (empty) |
| 32 | Controlled Execution not implemented |
| 33 | Controlled Execution not started |

### 18.3 Route Governance

| # | Criterion |
|---|-----------|
| 34 | OpenAPI paths = 32 |
| 35 | Runtime routes = 32 |
| 36 | Tool GET routes = 4 |
| 37 | Tool write routes = 0 |
| 38 | Tool dry-run routes = 1 |
| 39 | Tool execution routes = 0 |

### 18.4 Git and Release

| # | Criterion |
|---|-----------|
| 40 | local docs-only commit created |
| 41 | not pushed |
| 42 | Phase 1G-04-09 not started |
| 43 | Controlled Execution not started |

---

## 19. P0 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Code changes introduced | Review diff; reject if any non-docs file changed |
| 2 | OpenAPI modified | Verify diff; reject if OpenAPI YAML changed |
| 3 | Tests modified | Verify diff; reject if test files changed |
| 4 | Frontend modified | Verify diff; reject if frontend source changed |
| 5 | Route count changed | Run governance tests; reject if counts differ |
| 6 | Execution route added | Run governance tests; reject if Tool execution > 0 |
| 7 | Tool Handler called | Verify no handler imports; reject if found |
| 8 | Provider API called | Verify no provider calls; reject if found |
| 9 | Provider Schema sent | Verify no schema sending; reject if found |
| 10 | STATIC_ALLOWLIST modified | Verify empty; reject if populated |
| 11 | Real secret leaked | Content search; reject if found |
| 12 | Controlled Execution implemented | Verify no implementation code; reject if found |

### P0 Response

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-08 Failed."**

---

## 20. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Scope doc missing gate stack | Verify Section 5 completeness |
| 2 | Scope doc missing kill switch design | Verify Section 6 completeness |
| 3 | Scope doc missing allowlist strategy | Verify Section 7 completeness |
| 4 | Scope doc missing human confirmation design | Verify Section 8 completeness |
| 5 | Scope doc missing dry-run preflight requirement | Verify Section 9 completeness |
| 6 | Scope doc missing audit precondition | Verify Section 10 completeness |
| 7 | Scope doc missing provider schema boundary | Verify Section 11 completeness |
| 8 | Scope doc missing tool handler boundary | Verify Section 12 completeness |
| 9 | Scope doc missing execution result boundary | Verify Section 13 completeness |
| 10 | Scope doc falsely claims execution implemented | Content review |
| 11 | Route governance failure | Run tests; verify counts |
| 12 | OpenAPI paths not 32 | Verify count |
| 13 | Runtime routes not 32 | Verify count |
| 14 | Tool GET not 4 | Verify count |
| 15 | Tool write not 0 | Verify count |
| 16 | Tool dry-run not 1 | Verify count |
| 17 | Tool execution not 0 | Verify count |
| 18 | memory-check failure | Run memory-check |
| 19 | dev-check failure | Run dev-check |
| 20 | compileall failure | Run compileall |
| 21 | Worktree contains out-of-scope files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 21. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Controlled Execution not yet implemented | Expected — design freeze only |
| 2 | Execution API not yet designed to OpenAPI level | Deferred to implementation phase |
| 3 | Execution UI not yet implemented | Deferred to implementation phase |
| 4 | Audit read/search/list API not yet implemented | Deferred to future phase |
| 5 | Audit viewer UI not yet implemented | Deferred to future phase |
| 6 | Provider Schema exposure still not designed | Separate phase required |
| 7 | STATIC_ALLOWLIST still empty | Expected — requires separate phase |
| 8 | Browser smoke not re-run | Not required for docs-only change |

---

*Phase 1G-04-08 Controlled Execution Scope / Gate Design Freeze: scope/gate design only, docs-only, no implementation, no execution, no provider schema send, no tool dispatch, no tool handler call, no allowlist change, no route change, no OpenAPI change, no frontend change, no test change.*
