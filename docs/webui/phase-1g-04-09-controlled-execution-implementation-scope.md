# Phase 1G-04-09: Controlled Execution Implementation Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-09 |
| Title | Controlled Execution Implementation Scope Freeze |
| Status | Frozen (implementation scope definition only, no implementation) |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-09 implementation scope freeze) |
| Dependencies | Phase 1G-04-08 completed locally |
| Branch | dev-huangruibang |
| Base commit | `945361d473d67a930ca5345093ead9348b39630d` |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the implementation scope for a future Controlled Execution implementation
2. Defines the future phase split for Controlled Execution implementation
3. Defines the first implementation target (gate skeleton, not execution)
4. Defines the execute route strategy (not added in this phase)
5. Defines the OpenAPI strategy (not modified in this phase)
6. Defines the first tool candidate policy
7. Defines the allowlist activation rule
8. Defines the kill switch implementation scope
9. Defines the dry-run preflight binding
10. Defines the confirmation token scope
11. Defines the audit preconditions
12. Defines the tool handler lookup scope
13. Defines the execution runtime boundary
14. Defines the failure response contract
15. Defines the route governance future delta
16. Defines future allowed and forbidden files
17. Defines the test matrix
18. Defines entry and exit criteria for future implementation
19. Does **not** implement Controlled Execution
20. Does **not** enable Tool Execution
21. Does **not** add execution routes
22. Does **not** modify OpenAPI
23. Does **not** modify STATIC_ALLOWLIST

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-09 = **Controlled Execution Implementation Scope Freeze**

- This phase freezes the implementation scope for a future Controlled Execution implementation.
- This phase does **not** implement Controlled Execution.
- This phase does **not** enable Tool Execution.
- This phase does **not** add execution routes.
- This phase does **not** modify OpenAPI.
- This phase does **not** modify frontend.
- This phase does **not** modify STATIC_ALLOWLIST.
- This phase does **not** call tool handlers.
- This phase does **not** call providers.
- This phase does **not** add audit read APIs.
- This phase does **not** add audit viewer UI.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Current remote HEAD | `945361d473d67a930ca5345093ead9348b39630d` |
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |
| Dry-Run API | Implemented (`POST /api/dev/v1/tools/dry-run`) |
| Dry-Run Audit Writer | Implemented (`dev_web_tool_dry_run_audit.py`) |
| `auditWritten` | Audit write success only (not execution) |
| Controlled Execution Gate Design | Frozen (Phase 1G-04-08) |
| Controlled Execution implementation | Not started |
| STATIC_ALLOWLIST | Empty (empty frozenset) |
| Provider Schema Sending | Not sent |
| Tool Dispatch | 0 |
| Tool Handler Invocation | None |
| Tool Execution | Disabled |
| Kill Switches | All disabled (unset) |
| Production Gateway PID | 80468 |

---

## 3. Implementation Philosophy

Controlled Execution must be introduced incrementally. The following principles govern all future implementation phases:

1. **Incremental gate introduction:** The first implementation phase must prefer gate skeletons and blocked responses over real execution.
2. **No tool may execute until all gates are implemented and tested.** Every gate must have passing tests before any handler invocation occurs.
3. **Execution must remain disabled by default.** Even after all gates are implemented, execution requires explicit enablement via environment variables and allowlist population.
4. **Every enabling step requires a separate explicit phase.** No phase may combine route addition, OpenAPI modification, frontend changes, allowlist activation, and real execution.
5. **Blocked responses are safe responses.** Any gate failure must return a structured blocked response without calling any handler, provider, or dispatch.
6. **The implementation sequence must follow the gate stack order:** kill switches first, then allowlist, then dry-run preflight, then confirmation, then audit, then handler.

---

## 4. Future Phase Split

The following phase split is frozen for future Controlled Execution implementation:

| Phase | Name | Scope |
|-------|------|-------|
| 1G-04-10 | Execute Route Contract / OpenAPI Scope Freeze | Define and freeze the `POST /api/dev/v1/tools/execute` request/response contracts in a scope document; add OpenAPI path; no handler logic |
| 1G-04-11 | Backend Execute Gate Skeleton | Implement the execute route handler with all gates returning blocked responses by default; no handler invocation |
| 1G-04-12 | Confirmation Token / Digest Backend | Implement confirmation token generation, validation, expiry, single-use enforcement, and argument digest computation |
| 1G-04-13 | Allowlist Staged Activation Scope | Scope document defining which R0/R1 tools may be added to STATIC_ALLOWLIST; no actual activation |
| 1G-04-14 | First R0/R1 Candidate Execution POC | Controlled execution of one or more allowlisted R0/R1 tools with all gates passing; audit trail verified |
| 1G-04-15 | Browser / Network / A11y Safety Verification | Playwright smoke tests and safety verification for the execute route and frontend integration |

### Phase Split Principles

1. No single phase may combine route addition with handler invocation.
2. No single phase may combine allowlist activation with real execution.
3. OpenAPI changes must happen in their own phase (1G-04-10).
4. Frontend execute UI must happen in its own phase, after backend gates are verified.
5. Each phase must have its own scope freeze document before implementation begins.

---

## 5. First Implementation Target

### Target

The first implementation target is the **backend execute gate skeleton only**.

### Behavior

The first implementation phase (1G-04-11) must implement the execute route handler with the following behavior:

- **All execution requests blocked by default** — every request receives a structured blocked response.
- **Kill switches default false** — `HERMES_TOOL_EXECUTION_ENABLED`, `HERMES_AGENT_TOOLS_ENABLED` unset or non-`"true"` blocks execution.
- **STATIC_ALLOWLIST empty blocks** — empty allowlist means no tool is eligible.
- **Denylist blocks** — denylisted tools always block.
- **Unknown tool blocks** — tools not in inventory always block.
- **Risk tier > R1 blocks** — R2/R3/R4/R5 blocked initially.
- **Missing dry-run decision blocks** — no prior `would_allow` blocks execution.
- **Missing confirmation blocks** — no confirmation token blocks execution.
- **Audit precondition failure blocks** — pre-execution audit write failure blocks execution.

### What Phase 1G-04-09 Does NOT Do

- No tool execution in Phase 1G-04-09.
- No handler call in Phase 1G-04-09.
- No route added in Phase 1G-04-09.
- No code change in Phase 1G-04-09.
- No OpenAPI change in Phase 1G-04-09.
- No test change in Phase 1G-04-09.
- No frontend change in Phase 1G-04-09.

---

## 6. Execute Route Strategy

### Future Route

```
POST /api/dev/v1/tools/execute
```

### Route Classification

| Classification | Route | Phase Added |
|---------------|-------|-------------|
| Tool dry-run | `POST /api/dev/v1/tools/dry-run` | 1G-04-04 |
| Tool execution | `POST /api/dev/v1/tools/execute` | 1G-04-10 (scope) / 1G-04-11 (handler) |

### Classification Rules

1. Future `/tools/execute` must be counted separately as a **Tool execution route**.
2. It must **not** be counted as a Tool dry-run route.
3. It must **not** be hidden under a generic write route.
4. It must make Tool execution routes > 0 only in the explicit implementation phase.
5. Route governance must update expected path count explicitly when the route is added.

### Current State (Phase 1G-04-09)

- This route is **not** added in Phase 1G-04-09.
- OpenAPI paths remain 32.
- Runtime routes remain 32.
- Tool write routes remain 0.
- Tool execution routes remain 0.

---

## 7. OpenAPI Strategy

### Future Schema Names

The following OpenAPI schema names should be defined in Phase 1G-04-10:

| Schema Name | Purpose |
|-------------|---------|
| `ToolExecuteRequest` | Request body for execute endpoint |
| `ToolExecuteResponse` | Standard envelope response |
| `ToolExecuteData` | Data payload on success |
| `ToolExecuteDecision` | Gate decision result |
| `ToolExecuteGateStatus` | Individual gate pass/fail status |
| `ToolExecuteAuditStatus` | Audit write status |
| `ToolExecuteErrorCode` | Error code enum for blocked responses |
| `ToolExecuteResultPreview` | Sanitized execution result preview |

### Phase 1G-04-09 State

- No OpenAPI changes in Phase 1G-04-09.
- No new schema in Phase 1G-04-09.
- No new path in Phase 1G-04-09.
- Future OpenAPI must be added in its own phase (1G-04-10) and route governance must update expected path count explicitly.

---

## 8. First Tool Candidate Policy

### Current State

- STATIC_ALLOWLIST remains **empty** in Phase 1G-04-09.
- Candidate allowlist remains **advisory**.
- No tool is promoted in Phase 1G-04-09.

### Future Candidate Strategy

Only tools meeting **all** of the following criteria may be considered for first execution candidate:

| Criterion | Requirement |
|-----------|-------------|
| Risk tier | R0 or R1 only |
| Locality | Local-only operation |
| Determinism | Deterministic or read-only if possible |
| Network IO | Must not perform network IO |
| Production state | Must not mutate production state |
| Secrets | Must not access secrets |
| Dry-run coverage | Must have existing dry-run test coverage |
| Audit coverage | Must have existing audit test coverage |
| Timeout bounds | Must have timeout and output-size bounds |
| Failure mode | Must have a safe failure mode |

### Blocked Categories

The following categories are **blocked** for initial Controlled Execution:

| Category | Blocked Tools | Reason |
|----------|--------------|--------|
| Unknown tools | Any tool not in inventory | Always blocked |
| Denylisted tools | 26 permanently denied tools | Always blocked |
| R2 tools | 19 external network tools | Blocked until explicit review |
| R3 tools | 26 controlled-write tools | Blocked for initial implementation |
| R4 tools | 17 process/execution tools | Blocked |
| R5 tools | 3 high-risk system tools | Blocked |
| Provider-facing tools | Any tool calling external API | Blocked |
| Network tools | Any tool making network requests | Blocked |
| Credential/auth tools | Tools using credentials | Blocked unless separately reviewed |
| Shell/execution tools | `terminal`, `process`, `execute_code` | Blocked |
| Filesystem mutation tools | `write_file`, `patch`, `memory`, `skill_manage` | Blocked |
| Browser/subagent tools | All browser, `delegate_task`, `computer_use` | Blocked |

---

## 9. Allowlist Activation Rule

### Current State

- STATIC_ALLOWLIST is **empty** (empty frozenset in `dev_web_tool_policy.py`).
- Phase 1G-04-09 does **not** modify STATIC_ALLOWLIST.

### Future Activation Requirements

Each future allowlist entry requires **all** of the following:

| Requirement | Description |
|-------------|-------------|
| Canonical name | The exact registered tool name |
| Risk tier | Must be R0 or R1 |
| Justification | Written justification for inclusion |
| Dry-run test coverage | Existing dry-run tests passing |
| Audit test coverage | Existing audit tests passing |
| Failure-mode test coverage | Tests for timeout, output-size, and error handling |
| Explicit approval note | Documented approval in scope document |

### Prohibited Activation Patterns

- No **wildcard** allowlist.
- No **category-level** allowlist.
- No **automatic promotion** from candidate allowlist.
- No promotion based **solely on risk tier**.
- Each tool must be individually reviewed and approved.

---

## 10. Kill Switch Implementation Scope

### Kill Switch Inventory

| Switch | Purpose | Default State |
|--------|---------|--------------|
| `HERMES_TOOL_EXECUTION_ENABLED` | Master switch for tool execution in Dev WebUI | Unset / disabled |
| `HERMES_AGENT_TOOLS_ENABLED` | Agent tool loop enable switch | Unset / disabled |
| `HERMES_AGENT_RUN_ENABLED` | Agent run enable switch (existing from Phase 1F) | Unset / disabled |

Future additional switch:

| Switch | Purpose | Default State |
|--------|---------|--------------|
| `HERMES_PROVIDER_SCHEMA_ENABLED` | Provider schema exposure control | Unset / disabled (future) |

### Kill Switch Contract (Frozen)

1. **Unset = false** — if the environment variable is not set, the capability is disabled.
2. **Empty = false** — if set to an empty string, disabled.
3. **Only exact lowercase `"true"` enables.** All other values block.
   - `"false"` → disabled
   - `"1"` → disabled
   - `"yes"` → disabled
   - `"on"` → disabled
   - `"True"` → disabled (case-sensitive)
   - `"TRUE"` → disabled (case-sensitive)
4. **Production default = false.**
5. **Dev default = false.**

### Kill Switch Limitation

Even if all kill switches are `true`, execution is still blocked by:

- STATIC_ALLOWLIST (must contain the tool)
- Denylist (must not contain the tool)
- Risk tier eligibility (R0/R1 only initially)
- Dry-run decision (must be `would_allow`)
- Audit precondition (must succeed)
- Human confirmation (must match and be non-expired)
- Argument digest (must match preflight)

Kill switches are **necessary but not sufficient** for execution.

---

## 11. Dry-Run Preflight Binding

### Binding Requirements

Future execution **must reference a prior dry-run decision**. The following binding rules apply:

| Requirement | Description |
|-------------|-------------|
| Dry-run decision | Must be `would_allow` |
| `auditWritten` | Must be `true` |
| `canonicalName` match | Execution canonicalName must match dry-run canonicalName |
| Argument digest match | Execution argument digest must match dry-run argument digest |
| Risk tier match | Risk tier must match |
| Decision freshness | Dry-run decision must not be stale (expiry enforced) |
| Dry-run preflight expiry | Recommended: 5 minutes from dry-run to execution |

### Argument Digest Design

Recommended digest algorithm:

```
sha256(canonicalName + normalized redacted/safe arguments + policy version + risk tier)
```

Constraints:

- **Must not store raw arguments** in the digest comparison.
- Only the digest is stored and compared.
- Digest comparison must be timing-safe.

---

## 12. Confirmation Token Scope

### Token Properties

| Property | Description |
|----------|-------------|
| Generation trigger | Generated only after dry-run preflight succeeds |
| Use count | Single-use only |
| Expiry | Recommended: ≤ 5 minutes |
| Binding | Binds to specific request parameters |

### Token Binding Fields

The confirmation token must bind to all of the following:

| Field | Description |
|-------|-------------|
| `requestId` | Original dry-run request correlation ID |
| `canonicalName` | Exact tool name |
| `argumentDigest` | SHA-256 digest of sanitized arguments |
| `riskTier` | Tool risk tier (R0/R1) |
| `dryRunDecision` | Must be `would_allow` |
| `auditEventId` | Audit event ID from dry-run audit write |
| `timestamp` | ISO 8601 UTC when token was generated |

### Blocked Responses for Confirmation Failures

| Failure Mode | Blocked Response |
|-------------|-----------------|
| Token missing | `blocked_by_confirmation_missing` |
| Token invalid | `blocked_by_confirmation_invalid` |
| Token expired | `blocked_by_confirmation_expired` |
| Token reused | `blocked_by_confirmation_expired` (single-use) |
| Digest mismatch | `blocked_by_digest_mismatch` |
| canonicalName mismatch | `blocked_by_digest_mismatch` |

---

## 13. Audit Preconditions

### Pre-Execution Audit

| Requirement | Description |
|-------------|-------------|
| Must succeed | Pre-execution audit write must succeed **before** handler lookup |
| Must include | canonicalName, riskTier, decision, confirmation token reference, timestamp |
| Must not include | Raw arguments, secrets, provider keys |
| Failure behavior | **Blocks execution** — handler is never invoked |

### Post-Execution Audit

| Requirement | Description |
|-------------|-------------|
| Must be attempted | Post-execution audit event attempted after handler returns or fails |
| Must include | Execution result summary, duration, success/failure status |
| Must not include | Raw result content, stack traces, secrets |
| Failure behavior | **Reported safely** — does not block response, logged internally |

### Audit Content Restrictions

All audit records (pre and post execution) must **never** contain:

- Raw secrets, API keys, tokens, or credentials
- Provider keys or authorization headers
- Full unredacted argument payloads or result content
- Handler references, callable objects, or internal file paths
- Stack traces from handler execution

### Phase 1G-04-09 Status

- No execution audit implemented in Phase 1G-04-09.
- Existing dry-run audit writer records dry-run decisions only.

---

## 14. Tool Handler Lookup Scope

### Lookup Conditions

Handler lookup happens **only after all pre-execution gates pass**:

| Condition | Description |
|-----------|-------------|
| Kill switches enabled | Both `HERMES_TOOL_EXECUTION_ENABLED` and `HERMES_AGENT_TOOLS_ENABLED` are `"true"` |
| Allowlist match | Tool is in STATIC_ALLOWLIST |
| Not denylisted | Tool is not in STATIC_DENYLIST |
| Risk tier eligible | Risk tier is R0 or R1 |
| Dry-run decision | Prior dry-run returned `would_allow` |
| Audit precondition | Pre-execution audit write succeeded |
| Confirmation valid | Confirmation token is valid, non-expired, non-reused |
| Argument digest | Digest matches preflight dry-run |

### Handler Isolation Requirements

1. Handler lookup must be **isolated from provider schema generation** — no provider schema is sent during handler lookup.
2. Handler lookup must **not happen for blocked requests** — if any gate fails, the handler is never looked up.
3. Handler lookup must be **unit-test observable** — the lookup result (found/not-found/error) must be testable independently.

### Phase 1G-04-09 Status

- No Tool Handler lookup in Phase 1G-04-09.
- No handler call in Phase 1G-04-09.

---

## 15. Execution Runtime Boundary

### Per-Execution Limits

| Parameter | Recommended Value |
|-----------|-------------------|
| Max result preview | 64 KiB |
| Default timeout | 5 seconds |
| Hard timeout | 15 seconds |
| R0 timeout | 2 seconds |
| R1 timeout | 5 seconds |

### Sanitization Requirements

| Requirement | Description |
|-------------|-------------|
| No stack trace leak | Stack traces must not appear in any response |
| No secret leak | Secrets must not appear in any response field |
| No provider calls | Unless the tool is explicitly reviewed for network access |
| No production state mutation | Unless the tool is explicitly reviewed for state mutation |
| Result preview sanitized | Only sanitized preview returned to frontend |

---

## 16. Failure Response Contract

### Blocked Response Types

The following failure response types must be supported:

| Response Type | Gate / Condition |
|--------------|-----------------|
| `blocked_by_kill_switch` | Kill switches not enabled |
| `blocked_by_allowlist` | Tool not in STATIC_ALLOWLIST |
| `blocked_by_denylist` | Tool in STATIC_DENYLIST |
| `blocked_by_risk_tier` | Risk tier not eligible (R2+ initially) |
| `blocked_by_dry_run_decision` | Prior dry-run decision not `would_allow` |
| `blocked_by_audit_precondition` | Pre-execution audit write failed |
| `blocked_by_confirmation_missing` | No confirmation token provided |
| `blocked_by_confirmation_invalid` | Confirmation token does not match |
| `blocked_by_confirmation_expired` | Confirmation token expired or already used |
| `blocked_by_digest_mismatch` | Argument digest or canonicalName mismatch |
| `blocked_by_timeout` | Handler execution exceeded time limit |
| `blocked_by_handler_error` | Handler raised an exception |
| `blocked_by_result_sanitization` | Result failed sanitization checks |

### Blocked Response Invariants

Regardless of which gate fails, the response must:

1. **Not call the handler** — the tool's registered function is never invoked.
2. **Not call the provider** — no LLM provider API is called.
3. **Not dispatch** — no dispatch routing occurs.
4. **Not execute** — no tool execution occurs.
5. **Include the blocked reason** — structured error with the specific gate failure type.

---

## 17. Route Governance Future Delta

### Current State

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

### Future Delta (After Execute Route Added)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### Declaration

- The future delta is **not** applied in Phase 1G-04-09.
- Route governance counts remain unchanged.
- The delta will be applied in Phase 1G-04-10 (OpenAPI) / 1G-04-11 (runtime handler).

---

## 18. Future Allowed Files

The following files may be modified in future Controlled Execution implementation phases. They are **not** modified in Phase 1G-04-09.

| File | Action | Phase |
|------|--------|-------|
| `hermes_cli/dev_web_tool_execute.py` | **New** — Execute gate service module | 1G-04-11 |
| `hermes_cli/dev_web_tool_execute_service.py` | **New** — Execute handler orchestration | 1G-04-11 |
| `hermes_cli/dev_web_api.py` | **Modify** — Add execute route registration | 1G-04-11 |
| `hermes_cli/main.py` | **Modify** — Update dev-check route count | 1G-04-10 |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add execute path + schemas | 1G-04-10 |
| `tests/test_dev_web_tool_execute.py` | **New** — Execute gate unit tests | 1G-04-11 |
| `tests/test_dev_web_tool_execute_api.py` | **New** — Execute API integration tests | 1G-04-11 |
| `tests/test_dev_check_webui.py` | **Modify** — Update route governance expectations | 1G-04-10 |
| `tests/test_dev_web_0c06_closure.py` | **Modify** — Update route governance expectations | 1G-04-10 |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | **Modify** — Add completion records | Per phase |
| `docs/webui/phase-1-implementation-plan.md` | **Modify** — Update phase status | Per phase |

---

## 19. Future Forbidden Files

The following files must **not** be modified during future Controlled Execution implementation phases:

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

If a future frontend phase is needed (execute UI), it must be a **separate phase**, not combined with backend execution gates.

---

## 20. Test Matrix

The following tests must pass before Controlled Execution is considered complete:

### Kill Switch Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Kill switches default to false | All disabled by default |
| 2 | Kill switches require exact `"true"` | `"false"`, `""`, `"1"`, `"yes"`, unset all = disabled |
| 3 | Kill switches enabled but allowlist empty | Still blocked |
| 4 | Kill switches enabled but denylist match | Still blocked |

### Allowlist Tests

| # | Test | Expected |
|---|------|----------|
| 5 | STATIC_ALLOWLIST empty blocks all execution | No tool executes |
| 6 | Tool in STATIC_ALLOWLIST passes allowlist gate | Gate passes |
| 7 | Tool not in STATIC_ALLOWLIST fails allowlist gate | Gate fails |
| 8 | Denylist blocks execution even if in allowlist | Always blocked |

### Risk Tier Tests

| # | Test | Expected |
|---|------|----------|
| 9 | R0 eligible after all gates | Can execute if all gates pass |
| 10 | R1 eligible after all gates | Can execute if all gates pass |
| 11 | R2 blocked initially | Cannot execute initially |
| 12 | R3/R4/R5 blocked | Cannot execute |
| 13 | Unknown tool blocked | Cannot execute |

### Dry-Run Preflight Tests

| # | Test | Expected |
|---|------|----------|
| 14 | Dry-run decision required | No execution without prior dry-run |
| 15 | Dry-run `would_block` blocks execution | Cannot proceed |
| 16 | Dry-run `auditWritten` false blocks execution | Cannot proceed |
| 17 | Dry-run arguments digest must match | Mismatch blocks execution |
| 18 | `canonicalName` mismatch blocks execution | Cannot proceed |

### Confirmation Tests

| # | Test | Expected |
|---|------|----------|
| 19 | Confirmation required | No execution without confirmation |
| 20 | Token mismatch blocks execution | `blocked_by_confirmation_invalid` |
| 21 | Token expired blocks execution | `blocked_by_confirmation_expired` |
| 22 | Token reused blocks execution | `blocked_by_confirmation_expired` |
| 23 | Argument digest mismatch blocks execution | `blocked_by_digest_mismatch` |

### Security Boundary Tests

| # | Test | Expected |
|---|------|----------|
| 24 | Tool Handler not called when blocked | No handler invocation |
| 25 | Provider not called when blocked | No provider invocation |
| 26 | Dispatch not called when blocked | No dispatch routing |
| 27 | Execution timeout enforced | Timeout kills handler |
| 28 | Result size limit enforced | Oversized results truncated |
| 29 | Result sanitization enforced | No secrets in result |

### Audit Tests

| # | Test | Expected |
|---|------|----------|
| 30 | Pre-execution audit failure blocks execution | Handler not called |
| 31 | Post-execution audit failure reported safely | Response returned, error logged |
| 32 | Audit never stores raw secrets | Redacted in all events |

### Route Governance Tests

| # | Test | Expected |
|---|------|----------|
| 33 | Route governance counts correct after execute route | OpenAPI=33, Runtime=33, Tool execution=1 |
| 34 | OpenAPI schema contract correct | All schemas defined and valid |

### Frontend Safety Tests

| # | Test | Expected |
|---|------|----------|
| 35 | No frontend Execute button before backend gates | UI does not show execute controls |

---

## 21. Entry Criteria for Future Implementation

The following conditions must be met before any Controlled Execution implementation phase begins:

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04-09 docs pushed |
| 2 | No open P0/P1 risks |
| 3 | Production gateway stable |
| 4 | Route governance green (OpenAPI=32, Runtime=32) |
| 5 | Dry-Run API regression green |
| 6 | Audit writer tests green |
| 7 | Dry-Run model regression green |
| 8 | compileall PASS |
| 9 | ruff PASS |
| 10 | memory-check PASS |
| 11 | dev-check PASS |
| 12 | Explicit user approval to start implementation |
| 13 | Implementation phase must specify its type: route contract / gate skeleton / confirmation / allowlist activation / first real execution POC |

---

## 22. Exit Criteria for Future Implementation

The following conditions must be met for any Controlled Execution implementation phase to be considered complete:

| # | Criterion |
|---|-----------|
| 1 | No execution by default |
| 2 | All blocked paths return safe responses |
| 3 | No handler called on blocked paths |
| 4 | No provider called |
| 5 | No Provider Schema sent |
| 6 | STATIC_ALLOWLIST remains explicit (empty or intentionally populated) |
| 7 | Route governance updated only when route added |
| 8 | OpenAPI updated only when route added |
| 9 | Audit precondition enforced |
| 10 | Confirmation enforced |
| 11 | Tests cover all gates |
| 12 | Production gateway unaffected |
| 13 | All quality gates PASS |

---

## 23. Acceptance Criteria for Phase 1G-04-09

| # | Criterion |
|---|-----------|
| 1 | docs-only |
| 2 | New implementation scope doc added |
| 3 | Phase 1G-04 scope doc updated |
| 4 | Implementation plan updated |
| 5 | No code changes |
| 6 | No OpenAPI changes |
| 7 | No tests changed |
| 8 | No frontend changes |
| 9 | No routes changed |
| 10 | OpenAPI paths still 32 |
| 11 | Runtime routes still 32 |
| 12 | Tool GET 4 |
| 13 | Tool write 0 |
| 14 | Tool dry-run 1 |
| 15 | Tool execution 0 |
| 16 | STATIC_ALLOWLIST empty |
| 17 | Tool Execution disabled |
| 18 | Provider Schema not sent |
| 19 | Tool Handler not called |
| 20 | Tool Dispatch 0 |
| 21 | Controlled Execution not implemented |
| 22 | Controlled Execution not started |
| 23 | Local docs-only commit created |
| 24 | Not pushed |

---

## 24. P0 Risks (Blocking)

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

**Stop immediately. Do not commit. Do not push. Report "Phase 1G-04-09 Failed."**

---

## 25. P1 Risks (Blocking)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Scope doc missing future phase split | Verify Section 4 completeness |
| 2 | Scope doc missing first implementation target | Verify Section 5 completeness |
| 3 | Scope doc missing execute route strategy | Verify Section 6 completeness |
| 4 | Scope doc missing OpenAPI strategy | Verify Section 7 completeness |
| 5 | Scope doc missing first tool candidate policy | Verify Section 8 completeness |
| 6 | Scope doc missing allowlist activation rule | Verify Section 9 completeness |
| 7 | Scope doc missing kill switch implementation scope | Verify Section 10 completeness |
| 8 | Scope doc missing dry-run preflight binding | Verify Section 11 completeness |
| 9 | Scope doc missing confirmation token scope | Verify Section 12 completeness |
| 10 | Scope doc missing audit preconditions | Verify Section 13 completeness |
| 11 | Scope doc missing tool handler lookup scope | Verify Section 14 completeness |
| 12 | Scope doc missing execution runtime boundary | Verify Section 15 completeness |
| 13 | Scope doc missing failure response contract | Verify Section 16 completeness |
| 14 | Scope doc missing route governance future delta | Verify Section 17 completeness |
| 15 | Scope doc falsely claims execution implemented | Content review |
| 16 | Route governance failure | Run tests; verify counts |
| 17 | OpenAPI paths not 32 | Verify count |
| 18 | Runtime routes not 32 | Verify count |
| 19 | Tool GET not 4 | Verify count |
| 20 | Tool write not 0 | Verify count |
| 21 | Tool dry-run not 1 | Verify count |
| 22 | Tool execution not 0 | Verify count |
| 23 | memory-check failure | Run memory-check |
| 24 | dev-check failure | Run dev-check |
| 25 | compileall failure | Run compileall |
| 26 | Worktree contains out-of-scope files | Verify diff |

### P1 Response

**Do not claim completion. Do not push. Fix the deficiency.**

---

## 26. P2 Risks (Acceptable, Recorded)

The following are acceptable P2 risks that do not block this phase:

| # | Risk | Notes |
|---|------|-------|
| 1 | Controlled Execution not yet implemented | Expected — scope freeze only |
| 2 | Execute route not yet implemented | Deferred to Phase 1G-04-10 |
| 3 | Execution OpenAPI not yet implemented | Deferred to Phase 1G-04-10 |
| 4 | Execution UI not yet implemented | Deferred to future phase |
| 5 | Audit read/search/list API not yet implemented | Deferred to future phase |
| 6 | Audit viewer UI not yet implemented | Deferred to future phase |
| 7 | Provider Schema exposure still not designed as implementation phase | Separate phase required |
| 8 | STATIC_ALLOWLIST still empty | Expected — requires separate phase |
| 9 | First executable tool not yet finally selected | Deferred to Phase 1G-04-13 |
| 10 | Browser smoke not re-run | Not required for docs-only change |

---

*Phase 1G-04-09 Controlled Execution Implementation Scope Freeze: implementation scope definition only, docs-only, no code changes, no OpenAPI changes, no route changes, no frontend changes, no test changes, no execution implementation, no tool handler call, no provider schema send, no allowlist change, no Controlled Execution started.*
