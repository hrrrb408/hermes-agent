# Phase 1G-04: Tool Dry-Run / Controlled Execution — Design Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-00 |
| Title | Tool Dry-Run / Controlled Execution Design Scope Freeze |
| Status | Frozen (design-only, no implementation) |
| Date | 2026-06-11 |
| Author | Dev Agent (Phase 1G-04-00 scope freeze) |
| Dependencies | Phase 1G-03 completed, closed, and pushed |
| Branch | dev-huangruibang |
| Base commit | 512a6c6c222581f95cf059197fb2d55a2237a2e2 |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Records the Phase 1G-03 completion baseline
2. Defines Tool Dry-Run semantics (design only, not implemented)
3. Defines Controlled Execution semantics and preconditions (design only, not implemented)
4. Defines Risk Tier R0–R5 future admission rules for Dry-Run and Execution
5. Defines the relationship between denylist, candidate allowlist, and STATIC_ALLOWLIST
6. Defines the Phase 1G-04 sub-phase roadmap (design only)
7. Defines API roadmap, UI roadmap, audit roadmap, and kill switch contracts
8. Records absolute prohibitions and safety gates
9. Records acceptance criteria for the design freeze
10. Does **not** implement any API, service, frontend component, or test

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Overview

Phase 1G-04 is a **planning and controlled safety transition phase** after the read-only Tool Schema Preview phase (1G-03).

### Core Principles

1. **Phase 1G-04 does not automatically enable tool execution.**
2. **Phase 1G-04 must remain split into design, dry-run, audit, allowlist, UI, and controlled execution sub-phases.**
3. **Each sub-phase requires separate scope freeze, review, and approval before implementation begins.**
4. **Provider Schema Sending is not part of Phase 1G-04 and requires separate approval.**

### Current Baseline (from Phase 1G-03 Closure)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool inventory | 71 |
| STATIC_DENYLIST | 26 tools |
| CANDIDATE_ALLOWLIST | 6 tools |
| STATIC_ALLOWLIST | 0 (empty frozenset) |
| Provider Schema Sending | Not implemented / Not sent |
| Tool Dispatch | 0 |
| Tool Execution | Disabled |
| Tool Audit | Absent |

---

## 2. Definitions

### 2.1 Schema Preview

Read-only, sanitized metadata presentation. Already completed in Phase 1G-03.

- Displays tool schema fields, types, descriptions, constraints
- Applies redaction and sanitization rules
- Risk-based availability (R0–R3 available, R4–R5 unavailable, denylist unavailable)
- **No handler invocation, no provider schema send, no execution**

### 2.2 Tool Dry-Run

A **non-executing simulation** that validates whether a proposed tool call would be allowed, blocked, redacted, or require additional review, **without invoking the tool handler** and **without provider-side tool execution**.

Key properties:
- Validates tool canonical name against policy
- Validates proposed arguments against schema
- Returns a decision without executing the tool
- No handler call, no provider call, no mutation, no filesystem write
- No network access, no credential access, no secrets exposure

### 2.3 Controlled Execution

A **future explicitly gated execution path** for a tiny allowlisted subset of low-risk tools, with audit, kill switches, local-only constraints, and no provider schema auto-send unless separately approved.

Key properties:
- Requires all Dry-Run preconditions to be satisfied first
- Requires STATIC_ALLOWLIST to be intentionally populated in a separate commit
- Only R0/R1 low-risk tools considered initially
- Full audit trail required
- Kill switches must be tested and functional
- Production must be unaffected
- No provider schema sending unless separately approved

### 2.4 Provider Schema Sending

Supplying tool schemas to a model/provider. **Out of scope** for Phase 1G-04 unless separately frozen and approved.

Key properties:
- Triggers provider-side tool use contract
- Creates prompt injection surface
- Requires full safety chain (Schema Preview + Dry-Run + Controlled Execution + Audit)
- Requires separate phase freeze and approval

### 2.5 Tool Dispatch

Routing a validated call to an internal tool handler. **Out of scope** until the Controlled Execution phase. Dry-Run does NOT dispatch.

### 2.6 Tool Audit

A durable record of dry-run or execution decisions. **Design-only in 1G-04-00.** No audit storage is implemented.

---

## 3. Non-Goals

The following are explicitly **not** part of Phase 1G-04-00:

1. No backend route implementation
2. No OpenAPI implementation
3. No frontend implementation
4. No provider schema sending
5. No tool handler invocation
6. No tool dispatch
7. No tool execution
8. No tool audit storage
9. No allowlist activation
10. No STATIC_ALLOWLIST population
11. No dry-run endpoint
12. No execution endpoint
13. No UI execute button
14. No UI dry-run button
15. No provider integration
16. No production Gateway changes
17. No code changes of any kind

---

## 4. Risk Tier Rules (R0–R5) — Future Admission Policy

This section defines the future admission principles for each risk tier. These rules govern how tools at each tier interact with Dry-Run and Controlled Execution in future sub-phases.

### 4.1 R0 — Pure Computation (1 tool)

| Aspect | Rule |
|--------|------|
| Dry-Run | Eligible for future dry-run simulation |
| Execution | Not automatically eligible — requires explicit allowlist entry and separate phase approval |
| Risk | No I/O, no network, no state — lowest risk tier |
| Notes | `skill_match` is the sole R0 tool |

### 4.2 R1 — Read-Only Local Query (5 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | Eligible for future dry-run simulation |
| Execution | Requires explicit allowlist entry and separate phase approval |
| Risk | Local filesystem read or local DB read only |
| Notes | Candidate allowlist contains all 5 R1 tools |

### 4.3 R2 — Read-Only External Network (19 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | Eligible for future dry-run simulation with stricter warnings |
| Execution | Deferred unless separately approved |
| Risk | API calls, web search, external analysis — network-dependent |
| Notes | Arguments may contain URLs, API targets; enhanced redaction required |

### 4.4 R3 — Controlled Write (26 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | Eligible for future dry-run simulation with redaction and warning |
| Execution | Blocked by default |
| Risk | File/message/state mutation — side effects possible |
| Notes | Enhanced argument redaction in dry-run; execution requires separate approval |

### 4.5 R4 — Process/Execution (17 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | May explain blocked status only |
| Execution | Blocked |
| Risk | Shell, browser, subagent — full process control |
| Notes | Dry-run returns `would_block` with risk-tier reason |

### 4.6 R5 — High-Risk System (3 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | May explain blocked status only |
| Execution | Permanently blocked |
| Risk | Cron, admin, IoT device control |
| Notes | Dry-run returns `would_block` with risk-tier reason |

### 4.7 Permanent Denylist (26 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | Can return blocked reason only |
| Execution | Always blocked |
| Risk | Tools with capabilities that must never be available via WebUI |
| Notes | Denylist takes priority over risk tier |

### 4.8 Candidate Allowlist (6 tools)

| Aspect | Rule |
|--------|------|
| Dry-Run | Can be considered for dry-run modeling |
| Execution | Does not imply execution approval |
| Risk | R0/R1 only — lowest risk candidates |
| Notes | Advisory only — does not permit provider schema sending, dispatch, or execution |

### 4.9 STATIC_ALLOWLIST

| Aspect | Rule |
|--------|------|
| Current | Must remain empty in 1G-04-00 |
| Future | Any population requires separate phase and review |
| Risk | Only tools in STATIC_ALLOWLIST may be eligible for execution |
| Notes | Currently enforced as empty frozenset with validation |

---

## 5. Candidate Allowlist Policy

The CANDIDATE_ALLOWLIST is **advisory only**. It identifies tools that *could* be considered for future Dry-Run modeling, but it does not grant any execution capability.

### Policy Rules

1. **Candidate allowlist is advisory only.** It signals which tools are candidates for future evaluation.
2. **Candidate allowlist is not executable.** A tool on the candidate list cannot be executed.
3. **Candidate allowlist does not permit provider schema sending.** No tool schemas are sent to any LLM provider based on candidate status.
4. **Candidate allowlist does not permit dispatch.** No tool handler is invoked based on candidate status.
5. **Candidate allowlist does not modify STATIC_ALLOWLIST.** The STATIC_ALLOWLIST remains empty until a separate phase explicitly populates it.

### Current Composition

| Tool | Risk Tier | Candidate Status |
|------|-----------|-----------------|
| `skill_match` | R0 | Candidate |
| `clarify` | R1 | Candidate |
| `todo` | R1 | Candidate |
| `read_file` | R1 | Candidate |
| `search_files` | R1 | Candidate |
| `session_search` | R1 | Candidate |

---

## 6. Dry-Run Semantics (Design Only, Not Implemented)

### 6.1 Input

| Field | Type | Description |
|-------|------|-------------|
| `canonicalName` | string | Tool canonical name |
| `proposedArguments` | object | Proposed arguments (may be partial or empty) |
| `sourceContext` | string (optional) | Source context for the dry-run request |
| `uiOrigin` | string (optional) | UI component that initiated the request |

### 6.2 Output

| Field | Type | Description |
|-------|------|-------------|
| `decision` | enum | One of: `would_allow`, `would_block`, `would_redact`, `would_require_review` |
| `riskTier` | string | R0–R5 risk tier of the tool |
| `reasonCode` | string | Machine-readable reason for the decision |
| `reasonMessage` | string | Human-readable reason for the decision |
| `redactedArgumentPreview` | object or null | Redacted preview of what arguments would look like after sanitization |
| `missingRequiredFields` | list[string] | Required fields not present in proposed arguments |
| `forbiddenFields` | list[string] | Fields that would be redacted or rejected |
| `policyNotes` | list[string] | Additional policy notes |
| `auditPreviewId` | string or null | Preview audit ID (if audit design exists) |

### 6.3 Decision Matrix

| Tool Status | `decision` | Reason |
|-------------|-----------|--------|
| STATIC_ALLOWLIST (future) | `would_allow` | Tool is explicitly allowlisted |
| CANDIDATE_ALLOWLIST | `would_require_review` | Tool is a candidate but not yet approved |
| R0/R1 (not denied) | `would_allow` or `would_require_review` | Depends on argument validation |
| R2 (not denied) | `would_allow` with warnings | External network — enhanced caution |
| R3 (not denied) | `would_redact` | Controlled write — arguments redacted |
| R4 | `would_block` | Process/execution — blocked |
| R5 | `would_block` | High-risk system — blocked |
| STATIC_DENYLIST | `would_block` | Permanently denied |
| Unlisted | `would_block` | Not in inventory |

### 6.4 Guarantees

A Dry-Run operation guarantees the following:

1. **No tool handler call** — the tool's registered function is never invoked
2. **No provider call** — no LLM provider API is called
3. **No mutation** — no filesystem, database, or state mutation occurs
4. **No filesystem write** — no files are created, modified, or deleted
5. **No network** — no outbound network requests
6. **No credential access** — no API keys, tokens, or secrets are accessed
7. **No secrets** — no secret values are included in the response
8. **No production state access** — only dev-home paths are accessible
9. **No audit storage** — no durable audit records are created (design only)

---

## 7. Controlled Execution Preconditions

Controlled Execution **must not start** until **all** of the following are true:

| # | Precondition | Description |
|---|-------------|-------------|
| 1 | Dry-Run API designed and implemented | Full dry-run system is functional in a separate sub-phase |
| 2 | Audit design completed | Audit schema, storage, and access patterns are designed |
| 3 | Kill switch behavior tested | All kill switches are tested and confirmed functional |
| 4 | STATIC_ALLOWLIST intentionally populated | Allowlist is populated in a separate, reviewed commit |
| 5 | Only R0/R1 low-risk tools considered | Initial execution scope is limited to R0/R1 |
| 6 | No R4/R5 execution | R4 and R5 tools are permanently excluded from execution |
| 7 | No permanent denylist execution | Denylisted tools cannot be executed |
| 8 | No provider schema sending | Provider schema sending requires separate approval |
| 9 | UI clearly separates Dry-Run from Execute | Visual and functional separation between the two actions |
| 10 | Browser/network tests prove no accidental execution | Safety verified by automated tests |
| 11 | Production Gateway unaffected | Production environment remains untouched |
| 12 | Rollback plan documented | Clear rollback strategy is documented |

---

## 8. API Roadmap (Design Only, Not Implemented)

### 8.1 Sub-Phase Roadmap

| Phase | Name | Scope | Implementation |
|-------|------|-------|---------------|
| 1G-04-00 | Design Scope Freeze | This document — docs only | ✅ Current |
| 1G-04-01 | Dry-Run Policy Service Model | Policy decision engine design | Not started |
| 1G-04-02 | Dry-Run Read-Only API Design | GET/POST design discussion only | Not started |
| 1G-04-03 | Dry-Run API Implementation | Backend routes, no execution | Not started |
| 1G-04-04 | Dry-Run UI Panel | Frontend panel, no execution | Not started |
| 1G-04-05 | Dry-Run Browser/Network/A11y | Verification of dry-run | Not started |
| 1G-04-06 | Audit Design | Audit schema and storage design | Not started |
| 1G-04-07 | Controlled Execution Scope Freeze | Design-only scope for execution | Not started |
| Beyond 1G-04 | Execution Implementation | Deferred beyond design freeze | Not started |

### 8.2 Route Governance Invariants

The following invariants must hold throughout Phase 1G-04-00:

| Metric | Value | Must Not Change |
|--------|-------|----------------|
| OpenAPI paths | 31 | Yes |
| Runtime routes | 31 | Yes |
| Tool GET routes | 4 | Yes |
| Tool write routes | 0 | Yes |

**Phase 1G-04-00 must not change route counts.**

### 8.3 Future Route Considerations

Future sub-phases (1G-04-01 through 1G-04-07) may propose new routes. Each proposal must:

1. Be documented in a separate scope freeze document
2. Specify the exact route method, path, request/response schema
3. Specify the impact on OpenAPI path counts
4. Specify the impact on Tool GET and Tool write route counts
5. Receive separate approval before implementation
6. Maintain the principle that Dry-Run routes are logically distinct from Execute routes

---

## 9. UI Roadmap (Design Only, Not Implemented)

### 9.1 UI Principles

1. **No Execute button** in the design phase (1G-04-00)
2. **Dry-Run button** (if added in future sub-phase) must be **visually distinct** from any future Execute button
3. **Dry-Run result must clearly state** "No tool was executed."
4. **Blocked tools** must not expose argument generation helpers
5. **R4/R5 tools** must display blocked-only status
6. **Provider schema sending** must never be implied by any UI element

### 9.2 Forbidden UI Elements (Phase 1G-04-00)

The following must NOT appear in any UI during the design freeze:

| Element | Reason |
|---------|--------|
| "Run" / "Execute" button | No execution capability |
| "Send to Provider" button | Provider schema sending is out of scope |
| "Dispatch" button | No dispatch capability |
| "Enable Tool" toggle | Tool enabling is out of scope |
| "Autofill Args" button | Implies execution intent |
| "Generate Args" button | Parameter generation is out of scope |
| Any button implying execution or mutation | Safety principle |

### 9.3 Future Dry-Run UI (Design Only)

When a Dry-Run UI is designed in a future sub-phase:

- Dry-Run results must be displayed in a read-only panel
- The panel must show: decision, risk tier, reason, redacted arguments, missing fields, forbidden fields
- The panel must NOT show: raw arguments, secrets, handler references, file paths
- The panel must include a prominent notice: "This is a simulation. No tool was executed."

---

## 10. Audit Roadmap (Design Only, Not Implemented)

### 10.1 Dry-Run Audit Design

A Dry-Run audit may record the following (design only, not implemented):

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 string | When the dry-run occurred |
| `canonicalName` | string | Tool canonical name |
| `riskTier` | string | Risk tier (R0–R5) |
| `decision` | string | Dry-run decision |
| `reasonCode` | string | Machine-readable reason |
| `redactedArgsSummary` | string | Summary of redacted arguments (no raw data) |
| `origin` | string | Request origin (UI, API, etc.) |

### 10.2 Execution Audit Design

An Execution audit (if later implemented) must be **stricter and separate** from Dry-Run audit:

- Additional fields: execution result, duration, output summary, error details
- Separate storage table from Dry-Run audit
- Higher retention requirements
- Access logging

### 10.3 Prohibited Audit Content

No audit record (Dry-Run or Execution) may contain:

- Raw secrets, API keys, tokens, or credentials
- Provider keys or authorization headers
- Full unredacted argument payloads
- Handler references, callable objects, or file paths

### 10.4 Implementation Status

**No audit storage is implemented in 1G-04-00.** This section is design only.

---

## 11. Kill Switches

### 11.1 Kill Switch Inventory

| Switch | Purpose | Default State |
|--------|---------|--------------|
| `HERMES_TOOL_EXECUTION_ENABLED` | Master switch for tool execution | Unset / disabled |
| `HERMES_AGENT_TOOLS_ENABLED` | Agent tool loop enable switch | Unset / disabled |
| `HERMES_AGENT_RUN_ENABLED` | Agent run enable switch | Unset / disabled |

### 11.2 Kill Switch Contract

1. All three kill switches **remain unset / disabled** in 1G-04-00.
2. Kill switches use **fail-closed** semantics: unset or falsy means disabled.
3. Kill switches must be explicitly set to a truthy value to enable the corresponding capability.
4. Kill switches are checked at runtime, not just at startup.
5. Kill switch state changes do not require application restart.

### 11.3 Phase 1G-04-00 Kill Switch Status

All kill switches are confirmed **disabled**:

- `HERMES_TOOL_EXECUTION_ENABLED` — not set
- `HERMES_AGENT_TOOLS_ENABLED` — not set
- `HERMES_AGENT_RUN_ENABLED` — not set

---

## 12. Route Governance — Expected Counts

### 12.1 Current Counts (from Phase 1G-03 Closure)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |

### 12.2 Phase 1G-04-00 Invariant

**Phase 1G-04-00 must not change route counts.** This is a docs-only design freeze. No new routes are added, modified, or removed.

### 12.3 Future Count Expectations

Future sub-phases may propose route changes:

| Phase | Expected Change | Notes |
|-------|----------------|-------|
| 1G-04-01 | +0 routes (policy model only) | No API |
| 1G-04-02 | +0 routes (design discussion) | No API |
| 1G-04-03 | +N routes (dry-run API) | Separate scope freeze |
| 1G-04-04 | +0 routes (frontend only) | No new backend routes |
| 1G-04-05 | +0 routes (tests only) | No new routes |
| 1G-04-06 | +0 routes (audit design) | No API |
| 1G-04-07 | +0 routes (scope freeze) | No API |

---

## 13. Acceptance Criteria

### 13.1 Documentation

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-04 design scope document created |
| 2 | Dry-Run definition documented |
| 3 | Controlled Execution definition documented |
| 4 | Non-goals documented |
| 5 | Risk tier policy documented (R0–R5) |
| 6 | Candidate allowlist policy documented |
| 7 | API roadmap documented |
| 8 | UI roadmap documented |
| 9 | Audit roadmap documented |
| 10 | Kill switches documented |

### 13.2 Safety Boundary

| # | Criterion |
|---|-----------|
| 11 | No code changes |
| 12 | No OpenAPI changes |
| 13 | No API route changes |
| 14 | No frontend src changes |
| 15 | No frontend test changes |
| 16 | No router changes |
| 17 | No provider schema sending |
| 18 | No tool dispatch |
| 19 | No tool execution |
| 20 | No tool audit storage |
| 21 | STATIC_ALLOWLIST remains empty |
| 22 | Tool write routes remain 0 |

### 13.3 Route Governance

| # | Criterion |
|---|-----------|
| 23 | OpenAPI paths = 31 (unchanged) |
| 24 | Runtime routes = 31 (unchanged) |
| 25 | Tool GET routes = 4 (unchanged) |
| 26 | Tool write routes = 0 (unchanged) |

### 13.4 Production Safety

| # | Criterion |
|---|-----------|
| 27 | Production Gateway PID 1717 unaffected |
| 28 | Dev Gateway stopped |
| 29 | Ports 5180/5181 free |

### 13.5 Git and Release

| # | Criterion |
|---|-----------|
| 30 | Local docs-only commit created |
| 31 | Not pushed |
| 32 | Phase 1G-04-01 not started |
| 33 | Controlled Execution not started |

---

## 14. Implementation Plan Update

This section records what must be updated in `docs/webui/phase-1-implementation-plan.md`:

| Field | Value |
|-------|-------|
| Phase 1G-03 status | Completed / Closed |
| Phase 1G-04 status | Started as design-only scope freeze |
| Phase 1G-04-00 status | In progress / Completed locally |
| Phase 1G-04-01 status | Not Started |
| Controlled Execution status | Not Started |
| Tool Dry-Run Implementation status | Not Started |
| Provider Schema Sending status | Not Started |

### Prohibited Statements

The following must **never** appear in the implementation plan as a result of 1G-04-00:

- "Dry-Run implemented"
- "Execution enabled"
- "Provider Schema sent"
- "Tool execution available"
- "STATIC_ALLOWLIST populated"

---

## 15. Absolute Prohibitions

### 15.1 Files That Must Not Be Modified

```
hermes_cli/
apps/hermes-dev-webui/src/
apps/hermes-dev-webui/tests/
apps/hermes-dev-webui/e2e/
apps/hermes-dev-webui/playwright/
agent/
tools/
toolsets.py
```

### 15.2 Specific Files That Must Not Be Modified

```
docs/webui/openapi/dev-web-api-v1.yaml
hermes_cli/main.py
hermes_cli/dev_web_api.py
hermes_cli/dev_web_tool_policy.py
hermes_cli/dev_web_tool_schema_preview.py
hermes_cli/dev_web_tool_schema_preview_service.py
```

### 15.3 Capabilities That Must Not Be Enabled

- Tool Execution
- Tool Dispatch
- Provider Schema Sending
- Tool Audit storage
- STATIC_ALLOWLIST modification
- Kill switch activation
- Agent tool loop enablement

### 15.4 Git Operations That Must Not Be Performed

```bash
git push
git push --force
git rebase
git merge
git reset --hard
git clean -fd
git checkout -- .
git commit --amend
```

---

## 16. Safety Gates

### 16.1 Pre-Commit Gates

Before creating the docs-only commit, the following must pass:

| Gate | Expected |
|------|----------|
| `compileall` (backend modules) | PASS |
| `toolsets.py` compile | PASS |
| Backend governance tests | PASS |
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| `memory-check` | PASS |
| `dev-check` | PASS (WARN: .claude/ only) |

### 16.2 Post-Commit Gates

After creating the docs-only commit:

| Gate | Expected |
|------|----------|
| Local HEAD | 1 commit ahead of remote |
| Remote HEAD | Unchanged |
| Tracked worktree | Clean |
| .claude/ | Untracked only |
| Production Gateway PID 1717 | Running, unaffected |

---

## 17. Phase 1G-03 Baseline Confirmation

| Field | Value |
|-------|-------|
| Phase 1G-03 final HEAD | `512a6c6c222581f95cf059197fb2d55a2237a2e2` |
| Phase 1G-03 status | Closed / Completed |
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| STATIC_ALLOWLIST | 0 (empty) |
| STATIC_DENYLIST | 26 tools |
| CANDIDATE_ALLOWLIST | 6 tools |
| Provider Schema Sending | Not implemented / Not sent |
| Tool Dispatch | 0 |
| Tool Execution | Disabled |
| Tool Audit | Absent |

---

## 18. Git Commit

| Field | Value |
|-------|-------|
| Commit type | `docs` |
| Scope | `webui` |
| Message | `docs(webui): define phase 1g-04 execution safety scope` |
| Files added | `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` |
| Files modified | `docs/webui/phase-1-implementation-plan.md` |
| Pushed | No |

---

## 19. Phase 1G-04-01 Completion Record

### Phase 1G-04-01: Tool Dry-Run Policy Service Model

| Field | Value |
|-------|-------|
| Phase | 1G-04-01 |
| Title | Tool Dry-Run Policy Service Model |
| Status | Completed locally |
| Date | 2026-06-11 |
| Branch | dev-huangruibang |
| Base commit | d0790abf8d05ddfeb469fcd7aea8ac42d7364032 |

### Deliverables

| File | Description |
|------|-------------|
| `hermes_cli/dev_web_tool_dry_run.py` | Pure dry-run policy model: decisions, reason codes, argument sanitizer, risk-tier engine |
| `tests/test_dev_web_tool_dry_run.py` | 425 unit tests covering models, risk tiers, redaction, no side effects, catalog, summary |

### What Was Implemented

1. **Dry-Run Decision constants**: `would_allow`, `would_block`, `would_redact`, `requires_review`
2. **Dry-Run Reason codes**: 18 reason codes covering all decision paths
3. **Argument sanitizer**: Secret key/value redaction, forbidden field tracking, depth/string/list limits, JSON-safe output
4. **Frozen dataclasses**: `ToolDryRunRequest`, `ToolDryRunResult`, `ToolDryRunPolicySummary`
5. **Policy engine**: `dry_run_tool_policy()` — pure function, risk-tier based decisions
6. **Catalog query**: `list_tool_dry_run_policies()` — all 71 tools, sorted alphabetically
7. **Summary**: `compute_dry_run_policy_summary()` — aggregate counts by decision type

### Decision Matrix (as implemented)

| Tool Status | Decision | Reason |
|-------------|----------|--------|
| Unknown (not in inventory) | `would_block` | `WOULD_BLOCK_UNKNOWN_TOOL` |
| Permanent denylist | `would_block` | `WOULD_BLOCK_DENYLISTED` |
| R5 (high-risk system) | `would_block` | `WOULD_BLOCK_R5_SYSTEM_RISK` |
| R4 (process/execution) | `would_block` | `WOULD_BLOCK_R4_EXECUTION_RISK` |
| R3 (controlled write, no sensitive args) | `requires_review` | `REQUIRES_REVIEW_R3` |
| R3 (controlled write, sensitive args) | `would_redact` | `REQUIRES_REVIEW_R3` + redaction codes |
| R2 (external network) | `requires_review` | `REQUIRES_REVIEW_R2` |
| R1 (local read) | `would_allow` | `WOULD_ALLOW_STATIC_POLICY` + `DRY_RUN_ONLY_NO_EXECUTION` |
| R0 (pure compute) | `would_allow` | `WOULD_ALLOW_STATIC_POLICY` + `DRY_RUN_ONLY_NO_EXECUTION` |

### Invariants Verified

- `execution_allowed` is ALWAYS `False`
- `dispatch_allowed` is ALWAYS `False`
- `provider_schema_allowed` is ALWAYS `False`
- `audit_written` is ALWAYS `False`
- `STATIC_ALLOWLIST` remains empty
- stdlib only, no file IO, no network, no environment mutation
- Deterministic output

### What Was NOT Implemented

- No API route added
- No OpenAPI path added
- No frontend source changed
- No router changed
- No provider schema sending
- No tool handler call
- No tool dispatch
- No tool execution
- No audit storage
- No STATIC_ALLOWLIST population

### Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |

---

## 20. Phase 1G-04-02 Completion Record

### Phase 1G-04-02: Dry-Run Read-Only API Design

| Field | Value |
|-------|-------|
| Phase | 1G-04-02 |
| Title | Dry-Run Read-Only API Design Scope Freeze |
| Status | Completed locally |
| Date | 2026-06-11 |
| Branch | dev-huangruibang |
| Base commit | 821716bf5e95678a666a1b77ab5812b3ad81b8cc |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-02-dry-run-read-only-api-design.md` | API design document: endpoint, DTOs, error codes, route governance, security boundary, sanitization, future tests, future OpenAPI, future UI notes |

### What Was Designed

1. **Recommended endpoint**: `POST /api/dev/v1/tools/dry-run` — non-mutating policy decision endpoint
2. **Request DTO**: `canonicalName` (required), `argumentsPreview` (optional object), `sourceContext`, `uiOrigin`, `requestId`
3. **Response DTO**: Standard envelope with `ok`/`data`/`error`, policy decision fields, invariant guarantees (`executionAllowed=false`, etc.)
4. **Error codes**: 6 codes covering validation, policy unavailability, and internal errors
5. **Unknown tool behavior**: HTTP 200 with `exists=false` and `decision=would_block` (frozen decision)
6. **Route governance impact**: +1 dry-run route, Tool write routes remains 0, separate governance bucket
7. **Security boundary**: No tool handler calls, no dispatch, no execution, no provider schema, no audit
8. **Input sanitization**: Reuses Phase 1G-04-01 sanitizer semantics
9. **Future test scope**: 23 planned tests across decision, validation, security, and governance categories
10. **Future OpenAPI schema names**: 6 recommended schema names
11. **Future UI requirements**: "No tool executed" notice, no Execute terminology, redaction display
12. **Audit behavior**: Not implemented, deferred to Phase 1G-04-06

### What Was NOT Implemented

- No API route added
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No router changed
- No provider schema sending
- No tool handler call
- No tool dispatch
- No tool execution
- No audit storage
- No STATIC_ALLOWLIST population

### Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |

---

## 21. Phase 1G-04-03 Completion Record

### Phase 1G-04-03: Dry-Run API Implementation Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-03 |
| Title | Tool Dry-Run API Implementation Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-11 |
| Branch | dev-huangruibang |
| Base commit | eca4e2b33464783e23ece310e042c759106dcd03 |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-03-dry-run-api-implementation-scope.md` | Implementation scope freeze: allowed files, forbidden files, request/response/error contracts, route governance, test plan, network safety |

### What Was Frozen

1. **Implementation target**: `POST /api/dev/v1/tools/dry-run` — non-mutating policy decision
2. **Allowed files**: `dev_web_api.py`, OpenAPI YAML, 3 test files, 3 doc files
3. **Forbidden files**: all frontend, agent, tools, toolsets, runtime, memory, review, env, .claude
4. **Request validation**: `canonicalName` (required), `argumentsPreview` (optional object), `sourceContext`, `uiOrigin`, `requestId`
5. **Response contract**: standard envelope with invariant guarantees (executionAllowed=false, dispatchAllowed=false, providerSchemaAllowed=false, auditWritten=false)
6. **Error contract**: 6 error codes (400 validation, 503 policy unavailable, 500 internal)
7. **Unknown tool behavior**: HTTP 200 with exists=false and decision=would_block
8. **Route governance**: +1 dry-run route (31→32), Tool write routes remains 0, separate governance bucket
9. **OpenAPI freeze**: +1 path + 6 schemas (not modified in this phase)
10. **Backend implementation**: must use existing `dry_run_tool_policy()` only
11. **Test plan**: 29 tests across decision, validation, security, governance categories
12. **Network safety**: no external calls, no provider, no execute, no dispatch, no audit

### What Was NOT Implemented

- No API route added
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No router changed
- No provider schema sending
- No tool handler call
- No tool dispatch
- No tool execution
- No audit storage
- No STATIC_ALLOWLIST population

### Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 31 |
| Runtime routes | 31 |
| Tool GET routes | 4 |
| Tool write routes | 0 |

---

## 22. Phase 1G-04-04 Completion Record

### Phase 1G-04-04: Dry-Run API Implementation

| Field | Value |
|-------|-------|
| Phase | 1G-04-04 |
| Title | Tool Dry-Run API Implementation |
| Status | Completed / Pushed |
| Date | 2026-06-11 |
| Branch | dev-huangruibang |
| Commit | 1340e5105f92665a09b9fc9fd03c0ce8006147c2 |

### Deliverables

| File | Description |
|------|-------------|
| `hermes_cli/dev_web_api.py` | Added `_register_tool_dry_run_routes()` — 1 POST route handler |
| `docs/webui/openapi/dev-web-api-v1.yaml` | Added 1 path + 6 schemas for dry-run |
| `tests/test_dev_web_tool_dry_run_api.py` | 44 API-level tests covering decisions, validation, security, governance |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-04 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-04 status |

### What Was Implemented

1. **Route**: `POST /api/dev/v1/tools/dry-run` — non-mutating policy decision endpoint
2. **Handler**: calls existing `dry_run_tool_policy()` and `sanitize_arguments_preview()` from `dev_web_tool_dry_run.py`
3. **Request validation**: canonicalName required, argumentsPreview optional object, sourceContext/uiOrigin/requestId optional strings
4. **Response**: standard envelope with data/meta, invariant execution flags always false
5. **Error codes**: TOOL_DRY_RUN_INVALID_REQUEST, TOOL_DRY_RUN_INVALID_CANONICAL_NAME, TOOL_DRY_RUN_INVALID_ARGUMENTS, TOOL_DRY_RUN_POLICY_UNAVAILABLE, TOOL_DRY_RUN_INTERNAL_ERROR
6. **44 tests**: 9 decision tests, 2 denylist/unknown, 19 validation, 8 security, 2 envelope, 6 governance

### What Was NOT Implemented

- No tool handler calls
- No tool dispatch
- No tool execution
- No provider schema sending
- No audit storage
- No STATIC_ALLOWLIST population
- No frontend source changes
- No Dry-Run UI

### Route Governance

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

---

## 23. Phase 1G-04-05 Completion Record

### Phase 1G-04-05: Dry-Run API Browser / Network / A11y Safety Verification

| Field | Value |
|-------|-------|
| Phase | 1G-04-05 |
| Title | Tool Dry-Run API Browser / Network / A11y Safety Verification |
| Status | Completed locally / Not pushed |
| Date | 2026-06-11 |
| Branch | dev-huangruibang |
| Base commit | 1340e5105f92665a09b9fc9fd03c0ce8006147c2 |

### Deliverables

| File | Description |
|------|-------------|
| `apps/hermes-dev-webui/tests/smoke/phase-1g-04-dry-run-api-safety-smoke.spec.ts` | 18 Playwright smoke tests covering API, redaction, unknown tools, validation, network safety, UI non-exposure, A11y, execution flag invariants |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-04 and 1G-04-05 completion records |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-04 and 1G-04-05 status |

### What Was Verified

1. **API Smoke** (3 tests): POST dry-run returns safe decisions, R0/R1 tools return would_allow, dry-run POST not counted as tool write
2. **Redaction Smoke** (1 test): Secret arguments are redacted, no raw secrets in response
3. **Unknown Tool Smoke** (1 test): Returns 200 with exists=false and would_block, not 404
4. **Validation Error Smoke** (3 tests): Missing/invalid fields return 400, no stack trace leakage, no provider info
5. **Network Safety** (3 tests): No external provider requests, no execute/dispatch/audit write requests, dry-run classified in separate bucket
6. **UI Non-Exposure** (2 tests): No Execute/Dispatch/Provider-Schema buttons, no misleading execution text — skipped when WebUI not running
7. **A11y Safety** (1 test): Existing landmarks present, no unlabeled buttons, no dangerous execute buttons — skipped when WebUI not running
8. **Execution Flag Invariant** (4 tests): R0, R1, denylisted, and unknown tools all have all four flags false

### Safety Verification Results

| Check | Result |
|-------|--------|
| No provider requests | ✅ Verified |
| No Provider Schema sent | ✅ Verified |
| No Tool Handler called | ✅ Verified |
| No Tool Dispatch | ✅ Verified |
| No Tool Execution | ✅ Verified |
| No Tool Audit write | ✅ Verified |
| No STATIC_ALLOWLIST change | ✅ Verified |
| No raw secrets returned | ✅ Verified |
| No external network requests | ✅ Verified |
| No execute/dispatch/audit writes | ✅ Verified |
| No new Dry-Run UI | ✅ Verified |
| No new Execute buttons | ✅ Verified |

### Test Results

| Suite | Result |
|-------|--------|
| Browser smoke (18 tests) | 15 passed, 3 skipped (WebUI not running) |
| Frontend type-check | PASS |
| Frontend lint | PASS |
| Frontend build | PASS |
| Backend Dry-Run API (44 tests) | 44 passed, 2 skipped |
| Backend Dry-Run model (425 tests) | 425 passed |
| Route governance (124 tests) | 124 passed, 5 deselected |
| compileall | PASS |
| ruff | PASS |
| memory-check | PASS |
| dev-check | WARN (dirty worktree only) |

### What Was NOT Implemented

- No API code changes
- No OpenAPI changes
- No frontend source changes
- No frontend route changes
- No Dry-Run UI implementation
- No Audit Storage implementation
- No Controlled Execution start

### Route Governance (unchanged from 1G-04-04)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

---

## 24. Phase 1G-04-06 Completion Record

### Phase 1G-04-06: Dry-Run Audit Storage Scope / Design

| Field | Value |
|-------|-------|
| Phase | 1G-04-06 |
| Title | Dry-Run Audit Storage Scope / Design Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-11 |
| Branch | dev-huangruibang |
| Base commit | 6b4de050e7c296e3189535c09abbdd5b753caa1e |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-06-dry-run-audit-storage-scope.md` | Audit storage scope/design freeze: event model, sensitive data policy, storage location, retention/rotation, failure modes, future allowed/forbidden files, test plan |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-06 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-06 status |

### What Was Designed

1. **Audit goal**: Record local, non-mutating, already-redacted Dry-Run decision results
2. **Non-goals**: No execution recording, no raw arguments, no audit UI, no audit API
3. **Audit event model**: 30 fields including eventId, eventType, timestamp, canonicalName, decision, reasonCodes, redactedArgumentsPreview, invariant execution flags (always false)
4. **Sensitive data policy**: Reuses existing sanitizer, 18 forbidden field names, 4 secret value patterns, no raw storage
5. **Storage location**: `$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl` (dev-only, local-only)
6. **Retention/rotation**: max 32 KiB event, max 5 MiB file, max 3 rotated files, append-only JSONL
7. **Failure modes**: Audit failure never enables execution, never calls provider, never leaks secrets
8. **Future allowed files**: `dev_web_tool_dry_run_audit.py` (new), `dev_web_api.py` (modify), test files, doc files
9. **Future forbidden files**: All frontend, OpenAPI, main.py, agent, tools, toolsets, runtime, memory, review, env, .claude
10. **Future implementation phase**: Phase 1G-04-07 (Internal Audit Writer)
11. **Deferred items**: Audit viewer UI, audit search API, audit export, audit read route

### What Was NOT Implemented

- No audit storage module
- No audit storage file
- No audit API route
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No tool handler call
- No tool dispatch
- No tool execution
- No audit write
- No STATIC_ALLOWLIST population

### Route Governance (unchanged from 1G-04-05)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

---

*Phase 1G-04-00 Design Scope Freeze — Tool Dry-Run / Controlled Execution: design-only, docs-only, no implementation, no execution, no provider schema send, no tool dispatch, no tool audit, no allowlist change.*

---

## 25. Phase 1G-04-07 Completion Record

### Phase 1G-04-07: Internal Audit Writer Implementation

| Field | Value |
|-------|-------|
| Phase | 1G-04-07 |
| Title | Tool Dry-Run Internal Audit Writer |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | 91abc32656842a9923202698deab814def193dd6 |

### Deliverables

| File | Description |
|------|-------------|
| `hermes_cli/dev_web_tool_dry_run_audit.py` | New audit writer module: event builder, defensive sanitizer, JSONL append, file rotation, path validation |
| `tests/test_dev_web_tool_dry_run_audit.py` | 42 audit writer unit tests: event model, path validation, JSONL append, size/rotation, failure modes, security boundaries |
| `hermes_cli/dev_web_api.py` | Dry-Run API handler integrated with audit writer; auditWritten reflects audit write status |
| `tests/test_dev_web_tool_dry_run_api.py` | Updated to 61 tests: audit integration with HERMES_HOME, audit failure safety, route governance |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-07 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-07 status |
| `docs/webui/phase-1g-04-06-dry-run-audit-storage-scope.md` | Updated with 1G-04-07 implementation note |

### What Was Implemented

1. **Audit writer module** (`dev_web_tool_dry_run_audit.py`): stdlib-only, no provider/tool handler/dispatch imports
2. **Event builder** (`build_dry_run_audit_event`): Constructs JSON-safe audit event from ToolDryRunResult
3. **Defensive sanitizer**: Secondary redaction pass on all event values, forbidden field names, secret value patterns
4. **Event writer** (`write_dry_run_audit_event`): JSONL append with rotation, size limits, path validation
5. **Path validation**: HERMES_HOME enforcement, production path rejection, state.db rejection
6. **File rotation**: max 5 MiB per file, max 3 retained files (current + 2 rotated)
7. **Event size limit**: max 32 KiB per event, oversized events rejected safely
8. **Dry-Run API integration**: Handler calls audit writer after policy decision
9. **Response semantics**: `auditWritten=true` means audit write success only (not tool execution)
10. **Failure safety**: Audit write failure returns `auditWritten=false`, adds safe policyNote/reasonCode

### What Was NOT Implemented

- No audit read API route
- No audit search/list API route
- No audit viewer UI
- No audit export functionality
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No tool handler call
- No tool dispatch
- No tool execution
- No STATIC_ALLOWLIST population
- No Controlled Execution started

### Route Governance (unchanged from 1G-04-06)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

### Test Results

| Test Suite | Result |
|------------|--------|
| Audit writer tests | 42 passed |
| Dry-Run API tests | 61 passed, 2 skipped |
| Dry-Run model regression | 425 passed |
| Related backend regression | 1111 passed, 2 skipped |
| Route governance | 124 passed, 5 deselected |
| compileall | PASS |
| ruff | PASS |
| memory-check | PASS |
| dev-check | PASS (WARN: dirty worktree expected) |

---

*Phase 1G-04-07 Internal Audit Writer: audit writer module implemented, Dry-Run API integrated, dev-only JSONL audit storage, no new routes, no OpenAPI change, no frontend change, no tool execution, no provider schema sent, no allowlist change, no Controlled Execution.*

---

## 26. Phase 1G-04-08 Completion Record

### Phase 1G-04-08: Controlled Execution Scope / Gate Design Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-08 |
| Title | Controlled Execution Scope / Gate Design Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | 5bed1369b3d2927a304ea094e16d516d8f639ee7 |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-08-controlled-execution-gate-scope.md` | Controlled Execution gate scope/design freeze: gate stack (15 gates), kill switches, allowlist strategy, human confirmation, dry-run preflight, audit preconditions, provider schema boundary, tool handler boundary, execution result boundary, future API/OpenAPI/frontend strategies, test plan (32 tests), P0/P1/P2 risks, acceptance criteria |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-08 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-08 status |

### What Was Designed

1. **Gate stack**: 15 gates (Gate 0–14) defining the complete execution pathway from build-time capability through post-execution audit
2. **Kill switches**: 3 environment variables (`HERMES_TOOL_EXECUTION_ENABLED`, `HERMES_AGENT_TOOLS_ENABLED`, `HERMES_AGENT_RUN_ENABLED`) plus future `HERMES_PROVIDER_SCHEMA_ENABLED`
3. **Kill switch contract**: Unset=false, Empty=false, anything except "true"=false, production=false, dev=false
4. **Allowlist strategy**: STATIC_ALLOWLIST empty, one-by-one review, R0/R1 eligible initially, R2 requires review, R3/R4/R5 blocked
5. **Human confirmation**: Token bound to canonicalName, argument digest, riskTier, decision, requestId, timestamp, expiry; single-use only
6. **Dry-run preflight**: Every execution originates from dry-run `would_allow`; audit write must succeed
7. **Audit preconditions**: Pre-execution audit required (blocks on failure), post-execution audit best-effort
8. **Provider schema boundary**: Controlled Execution does not imply Provider Schema Sending; separate phase required
9. **Tool handler boundary**: Handler called only after all gates; policy decision isolated from handler lookup
10. **Execution result boundary**: Sanitized, size-limited (64 KiB), timeout-limited (R0: 2s, R1: 5s, hard max: 30s), no stack traces
11. **Future API strategy**: `POST /api/dev/v1/tools/execute` (not added in this phase)
12. **Future OpenAPI strategy**: Execution response types (preflight_blocked, confirmation_failed, audit_failed, handler_failed, execution_succeeded, execution_timeout, output_too_large)
13. **Future frontend strategy**: No Execute button until backend gates exist; explicit confirmation required; visual distinction from Dry-Run
14. **Test plan**: 32 future tests covering kill switches, allowlist, risk tier, dry-run preflight, human confirmation, security boundaries, audit, route governance
15. **Risk classification**: P0 (12 items), P1 (21 items), P2 (8 items)

### What Was NOT Implemented

- No Controlled Execution implementation
- No tool execution
- No new execution route
- No Tool Handler call
- No Provider Schema sending
- No Provider API call
- No Tool Dispatch
- No audit read API
- No audit viewer UI
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No STATIC_ALLOWLIST population
- No allowlist activation
- No risk tier changes
- No kill switch activation
- No code changes of any kind

### Route Governance (unchanged from 1G-04-07)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

---

*Phase 1G-04-08 Controlled Execution Scope / Gate Design Freeze: scope/gate design only, docs-only, no implementation, no execution route, no OpenAPI change, no frontend change, no tool handler call, no provider schema send, no allowlist change, no route change, no Controlled Execution started.*

---

## 27. Phase 1G-04-09 Completion Record

### Phase 1G-04-09: Controlled Execution Implementation Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-09 |
| Title | Controlled Execution Implementation Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | `945361d473d67a930ca5345093ead9348b39630d` |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-09-controlled-execution-implementation-scope.md` | Implementation scope freeze: future phase split, first implementation target, execute route strategy, OpenAPI strategy, first tool candidate policy, allowlist activation rule, kill switch scope, dry-run preflight binding, confirmation token scope, audit preconditions, tool handler lookup scope, execution runtime boundary, failure response contract, route governance future delta, future allowed/forbidden files, test matrix, entry/exit criteria |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-09 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-09 status |

### What Was Frozen

1. **Future phase split**: 6 phases (1G-04-10 through 1G-04-15) for Controlled Execution implementation
2. **First implementation target**: Backend execute gate skeleton only — all requests blocked by default
3. **Execute route strategy**: `POST /api/dev/v1/tools/execute` (not added in this phase)
4. **OpenAPI strategy**: 8 future schema names defined (not modified in this phase)
5. **First tool candidate policy**: R0/R1 only, local-only, deterministic, no network IO, no secrets access
6. **Allowlist activation rule**: One-by-one review, no wildcard, no automatic promotion
7. **Kill switch scope**: Exact `"true"` only, all other values block
8. **Dry-run preflight binding**: SHA-256 digest, 5-minute expiry, must match canonicalName and riskTier
9. **Confirmation token scope**: Single-use, ≤ 5-minute expiry, binds to requestId/canonicalName/digest/riskTier/auditEventId
10. **Audit preconditions**: Pre-execution audit blocks on failure, post-execution audit best-effort
11. **Tool handler lookup scope**: Only after all gates pass, isolated from provider schema
12. **Execution runtime boundary**: 64 KiB max result, 5s default / 15s hard timeout
13. **Failure response contract**: 13 blocked response types, no handler/provider/dispatch on blocked paths
14. **Route governance future delta**: OpenAPI 32→33, Runtime 32→33, Tool execution 0→1 (future only)
15. **Future allowed files**: 11 files listed for future modification (not modified in this phase)
16. **Future forbidden files**: 11 categories listed as permanently forbidden
17. **Test matrix**: 35 future tests across kill switches, allowlist, risk tier, dry-run, confirmation, security, audit, governance, frontend safety
18. **Entry criteria**: 13 conditions for starting implementation
19. **Exit criteria**: 13 conditions for completing implementation

### What Was NOT Implemented

- No Controlled Execution implementation
- No tool execution
- No new execution route
- No Tool Handler call
- No Provider Schema sending
- No Provider API call
- No Tool Dispatch
- No audit read API
- No audit viewer UI
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No STATIC_ALLOWLIST population
- No allowlist activation
- No risk tier changes
- No kill switch activation
- No code changes of any kind

### Route Governance (unchanged from 1G-04-08)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

---

*Phase 1G-04-09 Controlled Execution Implementation Scope Freeze: implementation scope definition only, docs-only, no code changes, no OpenAPI changes, no route changes, no frontend changes, no test changes, no execution implementation, no tool handler call, no provider schema send, no allowlist change, no Controlled Execution started.*

---

## 28. Phase 1G-04-10 Completion Record

### Phase 1G-04-10: Execute Route Contract / OpenAPI Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-10 |
| Title | Execute Route Contract / OpenAPI Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | `f5644ccadf61cd557ce743c2e9924db4c81ca54a` |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-10-execute-route-contract-openapi-scope.md` | Execute route contract / OpenAPI scope freeze: future route definition, route governance delta, Tool write vs Tool execution classification, request/response schema drafts, decision enum draft, gate status model, audit status model, result preview model, error code draft, blocked-by-default contract, dry-run preflight contract, confirmation contract, future OpenAPI file strategy, future runtime file strategy, future forbidden files, test matrix (31 tests), entry/exit criteria |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-10 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-10 status |

### What Was Frozen

1. **Future route definition**: `POST /api/dev/v1/tools/execute` — classified as Tool execution route, not added in this phase
2. **Route governance delta**: OpenAPI 32→33, Runtime 32→33, Tool execution 0→1 (future only, not applied)
3. **Tool write vs Tool execution classification**: Execute route counted as execution, not write; Tool write routes remain 0
4. **Request schema draft**: 9 fields (canonicalName, argumentsPreview, dryRunRequestId, dryRunDecisionDigest, confirmationToken, requestId, sourceContext, uiOrigin, clientCreatedAt) with required/optional classification and prohibited content rules
5. **Response schema draft**: Standard envelope with ToolExecuteData (17 fields), invariant defaults (executionAllowed=false, dispatchAllowed=false, providerSchemaAllowed=false, toolHandlerCalled=false, providerApiCalled=false)
6. **Decision enum draft**: 12 values covering all blocked states, `would_execute`, `executed`, `execution_failed`
7. **Gate status model**: 14 gates with per-gate pass/fail/reason/message/blocking status
8. **Audit status model**: 5 fields covering dry-run, pre-execution, and post-execution audit status
9. **Result preview model**: 7 fields with max 64 KiB preview, no raw secrets/stack traces
10. **Error code draft**: 22 error codes covering validation, policy, dry-run, confirmation, digest, audit, handler, execution, sanitization, and internal errors
11. **Blocked-by-default contract**: All switches unset → blocked_by_kill_switch; STATIC_ALLOWLIST empty → blocked_by_allowlist; no blocked response may call Tool Handler
12. **Dry-run preflight contract**: Execute must reference valid dry-run would_allow with auditWritten=true; dry-run success does not imply execution
13. **Confirmation contract**: Single-use, ≤ 5-minute expiry, binds to 7 fields; no implicit/auto/bypass confirmation
14. **Future OpenAPI file strategy**: 9 changes to dev-web-api-v1.yaml when route added (not modified in this phase)
15. **Future runtime file strategy**: 11 allowed files for future modification (not modified in this phase)
16. **Future forbidden files**: 13 categories permanently forbidden
17. **Test matrix**: 31 future tests across route governance, blocked-by-default, dry-run preflight, confirmation, digest, security boundary
18. **Entry criteria**: 14 conditions for starting execute route implementation
19. **Exit criteria**: 12 conditions for completing execute route implementation

### What Was NOT Implemented

- No execute route added
- No OpenAPI path added or modified
- No runtime route changed
- No frontend source changed
- No router changed
- No Tool Handler call
- No Tool Dispatch
- No Tool Execution
- No Provider Schema sending
- No Provider API call
- No STATIC_ALLOWLIST population
- No allowlist activation
- No audit read API
- No audit viewer UI
- No Controlled Execution started
- No code changes of any kind

### Route Governance (unchanged from 1G-04-09)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 32 |
| Runtime routes | 32 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 0 |

---

*Phase 1G-04-10 Execute Route Contract / OpenAPI Scope Freeze: route contract and OpenAPI scope definition only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no execution implementation, no tool handler call, no provider schema send, no allowlist change, no Controlled Execution started.*

---

## 29. Phase 1G-04-11 Completion Record

### Phase 1G-04-11: Backend Execute Gate Skeleton

| Field | Value |
|-------|-------|
| Phase | 1G-04-11 |
| Title | Backend Execute Gate Skeleton |
| Status | Completed locally / Pushed in commit `3c9220978` |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Commit | `3c9220978448d5c5f728f3bf51764378654065ab` |

### Deliverables

| File | Description |
|------|-------------|
| `hermes_cli/dev_web_tool_execute.py` | **New** — blocked-only execute gate skeleton: decision constants, error codes, gate constants, secret/forbidden-field redaction, request/result models, 9-gate evaluation, blocked result builder, policy summary |
| `hermes_cli/dev_web_api.py` | **Modify** — added `_register_tool_execute_routes()` registering `POST /api/dev/v1/tools/execute` |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — added 1 path + execute schemas (`ToolExecuteRequest`, `ToolExecuteDecision`, `ToolExecuteErrorCode`, `ToolExecuteGateStatusItem`, `ToolExecuteAuditStatus`, `ToolExecuteResultPreview`, `ToolExecuteData`, `ToolExecuteResponse`) |
| `hermes_cli/main.py` | **Modify** — updated dev-check route governance expectations |
| `tests/test_dev_web_tool_execute.py` | **New** — execute gate unit tests |
| `tests/test_dev_web_tool_execute_api.py` | **New** — execute API integration tests |
| `tests/test_dev_check_webui.py` | **Modify** — updated route governance expectations |
| `tests/test_dev_web_0c06_closure.py` | **Modify** — updated route governance expectations |
| `tests/test_dev_web_tool_dry_run_api.py` | **Modify** — route governance alignment |
| `tests/test_dev_web_tool_policy_api.py` | **Modify** — route governance alignment |
| `tests/test_dev_web_tool_schema_preview_api.py` | **Modify** — route governance alignment |

### What Was Implemented

1. **Execute route**: `POST /api/dev/v1/tools/execute` — classified as Tool execution route
2. **Blocked-only gate stack**: 9 gates evaluated in order — kill_switch, agent_tools, static_allowlist, known_tool, denylist, risk_tier, dry_run_preflight, digest, confirmation
3. **Kill switch contract**: exact lowercase `"true"` only; unset / empty / any other value blocks
4. **Skeleton digest gate**: accepts any non-empty digest; real verification deferred to Phase 1G-04-12+
5. **Skeleton confirmation gate**: checks token presence only; no issuance, no verification
6. **Hard block after all gates**: even when every gate passes, returns `decision=blocked`, `errorCode=execution_not_implemented`
7. **All execution flags false**: `executionAllowed`, `dispatchAllowed`, `providerSchemaAllowed`, `toolHandlerCalled`, `providerApiCalled`, `executionStarted`, `executionAttempted` always `false`
8. **Stdlib-only module**: no provider, handler, dispatch, agent, or toolsets execution imports

### What Was NOT Implemented

- No confirmation token issuance
- No confirmation token verification
- No token store
- No digest verification (skeleton accepts any non-empty digest)
- No dry-run historical lookup
- No pre-execution audit (`auditAttempted=false`)
- No post-execution audit
- No Tool Handler call
- No Tool Dispatch
- No Tool Execution
- No Provider Schema sending
- No Provider API call
- No STATIC_ALLOWLIST population
- No frontend source changes
- No frontend execute UI

### Route Governance (changed from 1G-04-10)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

---

*Phase 1G-04-11 Backend Execute Gate Skeleton: blocked-only execute route added (33 paths / 1 execution route), all execution flags false, no token issuance, no digest verification, no handler call, no dispatch, no execution, no provider schema send, STATIC_ALLOWLIST empty, Controlled Execution not started.*

---

## 30. Phase 1G-04-12 Completion Record

### Phase 1G-04-12: Confirmation Token / Digest Backend Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-12 |
| Title | Confirmation Token / Digest Backend Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | `3c9220978448d5c5f728f3bf51764378654065ab` |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-12-confirmation-token-digest-scope.md` | Confirmation token / digest backend scope freeze: phase definition, current baseline, confirmation token goal, digest binding goal, non-goals, future token lifecycle, token payload draft, token storage strategy, token expiry and replay prevention, digest canonicalization strategy, digest mismatch contract, dry-run preflight binding, audit binding, future execute route behavior delta, future OpenAPI strategy, future allowed files, future forbidden files, test matrix (30 tests), entry/exit criteria |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-11 and Phase 1G-04-12 completion records |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-11 and Phase 1G-04-12 status |

### What Was Frozen

1. **Confirmation token scope**: necessary-but-never-sufficient human-confirmation proof generated only after dry-run preflight; binds to canonicalName, arguments digest, risk tier, dry-run decision, audit event, requestId, timestamp
2. **Digest binding scope**: SHA-256 over canonical JSON of normalized execute input; prevents argument/canonicalName/stale-dry-run substitution; rejects mismatches before handler lookup
3. **Future token lifecycle**: 12-step flow from dry-run through handler lookup — frozen, not implemented
4. **Token payload draft**: 15 fields (version, tokenId, requestId, canonicalName, riskTier, policyVersion, dryRunRequestId, dryRunDecision, dryRunDecisionDigest, dryRunAuditEventId, argumentsDigest, issuedAt, expiresAt, singleUse, issuer); excludes raw arguments and secrets
5. **Token storage strategy**: dev-only, ephemeral, never production state.db, never ~/.hermes, never git; file-backed stores only hashed identifiers and metadata
6. **Token expiry / replay prevention**: ≤ 5-minute expiry, single-use; confirmation_missing / confirmation_invalid / confirmation_expired / confirmation_reused error mapping; replay prevention before handler lookup
7. **Digest canonicalization strategy**: sha256(canonical_json(NormalizedExecuteDigestInput)) over canonicalName, riskTier, policyVersion, dryRunDecision, sanitizedArgumentsPreview, dryRunRequestId, dryRunAuditEventId
8. **Digest mismatch contract**: blocked_by_digest_mismatch with toolHandlerCalled=false, executionStarted=false, providerApiCalled=false
9. **Dry-run preflight binding**: execute must reference prior would_allow with auditWritten=true; current dry-run historical lookup not implemented in this phase
10. **Audit binding**: token binds to dry-run audit event id; future pre/post execution audit include token id/hash and digest; never raw token secret or raw arguments
11. **Future execute route behavior delta**: token/digest backend may validate token shape, expiry, single-use, and digest match; route may remain blocked-only; does not imply handler call or execution
12. **Future OpenAPI strategy**: no path change; may refine existing execute schemas and add confirmation_expired / confirmation_reused error codes; path count stays 33
13. **Future allowed files**: 9 existing files plus optional 2 new token-module files (future only)
14. **Future forbidden files**: 13 categories permanently forbidden
15. **Test matrix**: 30 future tests across token issuance, lifecycle, binding, digest, no-side-effect, audit safety, route governance
16. **Entry criteria**: 13 conditions for starting token / digest implementation
17. **Exit criteria**: 14 conditions for completing token / digest implementation

### What Was NOT Implemented

- No confirmation token issuance
- No confirmation token verification
- No token store
- No digest verification
- No dry-run historical lookup
- No pre/post execution audit
- No execute route behavior change
- No OpenAPI change
- No new route added
- No route governance change
- No Tool Handler call
- No Tool Dispatch
- No Tool Execution
- No Provider Schema sending
- No Provider API call
- No STATIC_ALLOWLIST modification
- No frontend change
- No audit read API
- No audit viewer
- No code changes of any kind

### Route Governance (unchanged from 1G-04-11)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

---

*Phase 1G-04-12 Confirmation Token / Digest Backend Scope Freeze: confirmation token and digest binding backend scope definition only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no token implementation, no digest verification implementation, no execute route behavior change, no audit read API, no audit viewer, no tool handler call, no provider schema send, no allowlist change, no Controlled Execution started.*

---

## 31. Phase 1G-04-13 Completion Record

### Phase 1G-04-13: First Executable Tool Candidate Selection / Allowlist Activation Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-13 |
| Title | First Executable Tool Candidate Selection / Allowlist Activation Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | `8c2bb40cffcec66ae5569c2093cdc62db440acc3` |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-13-first-executable-tool-allowlist-scope.md` | First executable tool candidate selection / allowlist activation scope freeze: phase definition, current baseline, first executable candidate goal, candidate eligibility criteria (18 criteria), candidate exclusion criteria (13 exclusions), candidate selection strategy (10 steps), candidate recommendation (`clarify` R0 recommended, shortlist of 6), allowlist activation goal, allowlist activation rules (17 rules), STATIC_ALLOWLIST future delta, kill switch relationship, dry-run/confirmation/digest relationship, execute route behavior delta, route governance strategy, future OpenAPI strategy, future allowed files, future forbidden files, future test matrix (28 tests), entry criteria (12 conditions), exit criteria (15 conditions) |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-13 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-13 status |

### What Was Frozen

1. **First executable candidate goal**: the first tool that may later be considered for STATIC_ALLOWLIST activation; chosen for safety, determinism, testability, and minimal blast radius; candidate selection is not allowlist activation; allowlist activation is not execution
2. **Candidate eligibility criteria**: 18 mandatory criteria including R0/R1, local-only, deterministic, no network, no provider, no secrets, no shell, no production state, bounded output, JSON-safe, redaction-compatible, side-effect-free, and on CANDIDATE_ALLOWLIST
3. **Candidate exclusion criteria**: 13 exclusion categories covering R2+, network, provider, credentials, filesystem mutation, shell, long-running, production state, secrets, browser, frontend, audit, and non-candidate tools
4. **Candidate selection strategy**: 10-step filtering process from 71-tool inventory → R0/R1 → local-only → no network/provider/secret/shell/mutation → bounded output → introspection-preferred → well-tested → simple arguments → redact-able output
5. **Candidate recommendation**: `clarify` (R0) recommended as first executable candidate — pure computation, no I/O, no filesystem, no DB, no network, no state mutation, bounded input/output, comprehensive test coverage; shortlist of all 6 CANDIDATE_ALLOWLIST tools evaluated with safety assessment
6. **Allowlist activation goal**: one-by-one, reviewed, committed as separate implementation phase, tested, reversible
7. **Allowlist activation rules**: 17 rules including no wildcard, no category, no risk-tier, no auto-promotion, no config/env fill, exact canonicalName only, one commit per tool, governance tests required, no handler/dispatch/execution by itself
8. **STATIC_ALLOWLIST future delta**: `frozenset()` → `frozenset({"clarify"})` if confirmed; not applied in Phase 1G-04-13; delta application requires 7 conditions
9. **Kill switch relationship**: necessary but not sufficient; exact `"true"` required; independent from allowlist; all remaining gates still apply
10. **Dry-run / confirmation / digest relationship**: allowlisting does not bypass any gate — dry-run, audit, confirmation token, digest verification, denylist, risk-tier, redaction all still required
11. **Execute route behavior delta**: current baseline (blocked-only, empty allowlist) vs. future (single tool passes Gate 3, all other gates still apply); allowlist activation does not imply execution/handler/provider
12. **Route governance strategy**: no change in Phase 1G-04-13; no change expected for future allowlist activation; 33/33/4/0/1/1 maintained
13. **Future OpenAPI strategy**: no path change; 33 paths maintained; response schema refinements may occur without path changes
14. **Future allowed files**: 7 backend files, 4 test files, 2 doc files, 2 optional new files (if independent module needed)
15. **Future forbidden files**: 13 categories including frontend, agent, tools, toolsets, runtime, memory, review, .env, .claude, ~/.hermes, production state.db, OpenAPI YAML
16. **Future test matrix**: 28 tests across allowlist, kill switch, gate stack, execution boundary, route governance, and delta management categories
17. **Entry criteria**: 12 conditions for starting allowlist activation implementation
18. **Exit criteria**: 15 conditions for completing allowlist activation implementation

### What Was NOT Implemented

- No STATIC_ALLOWLIST modification
- No STATIC_ALLOWLIST population
- No allowlist activation implementation
- No tool handler integration
- No tool dispatch implementation
- No real tool execution
- No confirmation token implementation
- No digest verification implementation
- No provider integration
- No frontend execute UI implementation
- No audit read API
- No audit viewer
- No code changes of any kind
- No OpenAPI file changes
- No route changes
- No execute route behavior changes

### Route Governance (unchanged from 1G-04-11/12)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

---

## Phase 1G-04-14: Clarify Allowlist Activation / Still Blocked-Only

| Field | Value |
|-------|-------|
| Phase | 1G-04-14 |
| Title | Clarify Allowlist Activation / Still Blocked-Only |
| Status | Completed locally / not pushed |
| Date | 2026-06-12 |
| Commit | Local only |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |

### What Changed

- `STATIC_ALLOWLIST` changed from `frozenset()` to `frozenset({"clarify"})`
- `clarify` ToolPolicyEntry `statically_allowed` changed from `False` to `True`
- Execute Gate 3 changed from empty-allowlist check to membership check
- `evaluate_static_tool_policy("clarify")` now returns `allowed=True`
- Dev-check updated to verify `STATIC_ALLOWLIST == frozenset({"clarify"})`
- All tests updated to reflect the new allowlist state

### What Did NOT Change

- Only `clarify` is allowlisted — no wildcard, category, risk-tier, or dynamic allowlist
- Execute route remains blocked-only — `clarify` still blocked by later gates
- No handler lookup, no dispatch, no execution
- No Provider Schema sent, no Provider API called
- No confirmation token, no digest verification, no dry-run historical lookup
- No pre/post execution audit
- No real Controlled Execution started
- No OpenAPI changes, no frontend changes, no route count changes

### Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |

### Test Results

1141 passed, 0 failed, 2 skipped.

---

*Phase 1G-04-14 Clarify Allowlist Activation / Still Blocked-Only: STATIC_ALLOWLIST changed from frozenset() to frozenset({"clarify"}), clarify is the only allowlisted canonicalName, execute route remains blocked-only, no handler lookup, no dispatch, no execution, no provider schema, no provider API, no token, no digest, no real Controlled Execution, no OpenAPI changes, no frontend changes, no route count changes.*

---

## 33. Phase 1G-04-15 Completion Record

### Phase 1G-04-15: Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-15 |
| Title | Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Branch | dev-huangruibang |
| Base commit | `2e60523ecf7d13a845e765c01609aae67d4f74b9` |

### Deliverables

| File | Description |
|------|-------------|
| `docs/webui/phase-1g-04-15-dry-run-historical-lookup-preflight-binding-scope.md` | Dry-run historical lookup / confirmation-digest preflight binding scope freeze: phase definition, current baseline, dry-run historical lookup goal, historical record source, lookup input contract, lookup output contract, lookup failure contract, preflight gate order (21 gates), confirmation token binding goal, digest binding goal, expiry strategy, replay prevention strategy, audit binding strategy, execute route behavior delta, route governance strategy, future OpenAPI strategy, future allowed files, future forbidden files, future test matrix (33 tests), entry criteria, exit criteria, acceptance criteria |
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Updated with Phase 1G-04-15 completion record |
| `docs/webui/phase-1-implementation-plan.md` | Updated Phase 1G-04-15 status |

### What Was Frozen

1. **Dry-run historical lookup goal**: read-only retrieval of prior dry-run decision via `dryRunRequestId`; necessary but never sufficient; blocks before handler lookup
2. **Historical record source**: dev-only dry-run audit JSONL (`$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl`); forbidden sources: `~/.hermes`, production state.db, committed runtime files, frontend localStorage, browser cache, provider logs
3. **Lookup input contract**: 7 fields (`dryRunRequestId` required, `canonicalName` required, `dryRunDecisionDigest` required, `auditEventId` optional, `argumentsDigest` optional, `policyVersion` optional, `riskTier` optional); `policyVersion` must match or fail closed
4. **Lookup output contract**: 15 fields (found, dryRunRequestId, canonicalName, decision, riskTier, policyVersion, sanitizedArgumentsPreview, argumentsDigest, dryRunDecisionDigest, auditWritten, auditEventId, createdAt, expiresAt, lookupSource, redactionStatus); excludes raw arguments, secrets, credentials, headers, cookies, raw token secret
5. **Lookup failure contract**: 12 error codes (dry_run_missing, dry_run_not_found, dry_run_expired, dry_run_not_allowed, dry_run_audit_missing, dry_run_digest_missing, dry_run_digest_mismatch, dry_run_canonical_name_mismatch, dry_run_policy_version_mismatch, dry_run_risk_tier_mismatch, dry_run_arguments_mismatch, dry_run_lookup_unavailable); all failures block before handler lookup; all failures keep executionAllowed=false
6. **Preflight gate order**: 21 gates frozen (request shape → kill switches → static allowlist → known tool → denylist/risk-tier → dryRunRequestId → dry-run lookup → dry-run decision → auditWritten → canonicalName binding → riskTier binding → policyVersion binding → arguments digest binding → confirmationToken present → token verification → token expiry → token reuse → token digest binding → digest verification → pre-execution audit → handler lookup)
7. **Confirmation token binding goal**: binds to dryRunRequestId, dryRunDecisionDigest, canonicalName, arguments digest, auditEventId, policyVersion, riskTier; verified before handler lookup; failure never calls provider
8. **Digest binding goal**: prevents argument substitution, canonicalName substitution, stale dry-run reuse, policy-version drift, risk-tier drift; sha256(canonical_json(input)) over 8 fields
9. **Expiry strategy**: dry-run reference TTL ≤ 5 minutes; confirmation token TTL ≤ dry-run TTL; expiry blocks before token verification and digest verification respectively
10. **Replay prevention strategy**: dryRunRequestId not indefinitely reusable; confirmationToken single-use; consumed token blocks on reuse; replay prevention before handler lookup
11. **Audit binding strategy**: lookup references dry-run audit event; preflight records lookup pass/fail; pre/post execution audit include dryRunRequestId, dryRunDecisionDigest, token id/hash, digest; never raw secrets or raw token secret
12. **Execute route behavior delta**: current (blocked-only, clarify allowlisted, no lookup) vs. future (can lookup, can verify binding, may still remain blocked-only); key principle: lookup/token/digest do not imply execution
13. **Route governance strategy**: no count change in 1G-04-15; 33/33/4/0/1/1 maintained
14. **Future OpenAPI strategy**: no path change; may refine existing execute schemas and add error codes; 33 paths maintained
15. **Future allowed files**: 10 existing backend files + 4 optional new modules (not created in this phase)
16. **Future forbidden files**: frontend, agent, tools, toolsets, runtime, memory, review, .env, .claude, ~/.hermes, production state.db
17. **Future test matrix**: 33 tests across dry-run lookup (11), confirmation token (7), combined paths (4), safety invariants (7), route governance (4)
18. **Entry criteria**: 13 conditions for starting implementation
19. **Exit criteria**: 19 conditions for completing implementation

### What Was NOT Implemented

- No dry-run historical lookup implementation
- No confirmation token issuance
- No confirmation token verification
- No token store
- No digest verification
- No pre/post execution audit
- No execute route behavior change
- No OpenAPI change
- No new route added
- No route governance change
- No Tool Handler call
- No Tool Dispatch
- No Tool Execution
- No Provider Schema sending
- No Provider API call
- No STATIC_ALLOWLIST modification
- No frontend change
- No audit read API
- No audit viewer
- No code changes of any kind

### Route Governance (unchanged from 1G-04-14)

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

*Phase 1G-04-15 Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze: scope definition only, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no dry-run historical lookup implementation, no token implementation, no digest verification implementation, no handler call, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*

---

## Phase 1G-04-16: Dry-Run Historical Lookup Read-Only Implementation

| Field | Value |
|-------|-------|
| Phase | 1G-04-16 |
| Title | Dry-Run Historical Lookup Read-Only Implementation / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-12 |
| Dependencies | Phase 1G-04-15 completed locally |

### Summary

Implemented read-only dry-run historical lookup from dev-only audit JSONL. The execute route now retrieves prior dry-run records by `dryRunRequestId` and verifies decision, auditWritten, canonicalName, riskTier, policyVersion, and digest bindings before reaching the confirmation token gate.

The execute route remains blocked-only. Even when clarify passes all dry-run lookup and binding gates, it is blocked by the confirmation token boundary because token verification is not implemented.

### Delta from 1G-04-15

- New module: `hermes_cli/dev_web_tool_execute_preflight.py` (read-only lookup helper)
- Modified: `hermes_cli/dev_web_tool_execute.py` (integrated lookup gates)
- Modified: `hermes_cli/dev_web_api.py` (pass hermes_home to evaluator)
- Modified: OpenAPI `ToolExecuteErrorCode` enum (added 9 new error codes)
- New tests: 35 preflight reader tests
- Updated tests: 82 execute + 56 execute-api tests
- New doc: `phase-1g-04-16-dry-run-historical-lookup-read-only-implementation.md`

### Not Implemented

- Confirmation token issuance
- Confirmation token verification
- Token store
- Digest verification
- Pre/post execution audit
- Handler lookup
- Dispatch
- Execution
- Provider Schema sending
- Provider API call
- Frontend execute UI
- Audit read API
- Audit viewer
- Real Controlled Execution

### Route Governance (unchanged from 1G-04-15)

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

*Phase 1G-04-16 Dry-Run Historical Lookup Read-Only Implementation: read-only lookup implemented, execute gate integrated, all paths blocked, no token, no digest verification, no handler, no dispatch, no execution, no provider, no Controlled Execution started.*

---

## Phase 1G-04-17: Preflight Production Path Guard Hardening

| Field | Value |
|-------|-------|
| Phase | 1G-04-17 |
| Title | Preflight Production Path Guard Hardening / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Dependencies | Phase 1G-04-16 completed locally |

### Summary

Hardened the dry-run execute preflight lookup's production path guard from equality-only (`home == prod_home`) to containment-based checks using `Path.relative_to()`. The new guard blocks:
- Exact production home
- Production home subtrees
- Resolved audit paths inside production home
- Symlink/path traversal into production home
- Path traversal escaping the dev audit directory

Paths like `.hermes-dev` are NOT falsely blocked because containment uses `Path.relative_to()`, not string prefix matching.

The execute route remains blocked-only. No behavior expansion. No new routes.

### Delta from 1G-04-16

- Modified: `hermes_cli/dev_web_tool_execute_preflight.py` (containment guard)
- New helper: `_is_relative_to()` in preflight module
- New tests: 23 preflight containment tests
- Updated tests: 5 execute model tests + 4 execute API tests
- New doc: `phase-1g-04-17-preflight-production-path-guard-hardening.md`

### Not Implemented

- Confirmation token issuance
- Confirmation token verification
- Token store
- Digest verification
- Pre/post execution audit
- Handler lookup
- Dispatch
- Execution
- Provider Schema sending
- Provider API call
- Frontend execute UI
- Audit read API
- Audit viewer
- Real Controlled Execution

### Route Governance (unchanged from 1G-04-16)

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

*Phase 1G-04-17 Preflight Production Path Guard Hardening: containment-based production guard implemented, production subtree blocked, symlink/path traversal blocked, dev audit directory containment enforced, execute route remains blocked-only, no token, no digest verification, no handler, no dispatch, no execution, no provider, no Controlled Execution started.*

---

## Phase 1G-04-18: Confirmation Token Issuance / Verification Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 1G-04-18 |
| Title | Confirmation Token Issuance / Verification Scope Freeze |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Dependencies | Phase 1G-04-17 completed locally |

### Summary

Froze the future confirmation token issuance, verification, storage, TTL, single-use, and dry-run binding design as a docs-only scope document. Defined the complete token lifecycle, binding contract, hash strategy, verification gate order (29 gates), failure contract (15 error codes), audit strategy, digest verification boundary, and future test matrix (36 tests).

### Delta from 1G-04-17

- New doc: `docs/webui/phase-1g-04-18-confirmation-token-scope.md`
- Updated: Phase 1G-04 scope doc, implementation plan, Phase 1G-04-17 cross-reference

### Confirmation Token Scope Frozen

1. **Token goal**: Short-lived, single-use, dev-only approval artifact; necessary but never sufficient
2. **Issuance source**: Only after successful dry-run (would_allow + auditWritten + allowlisted); preferred Option A (extend dry-run response) over Option B (new endpoint)
3. **Binding contract**: 11 bound fields (dryRunRequestId, dryRunDecisionDigest, canonicalName, riskTier, policyVersion, auditEventId, argumentsDigest, redactionVersion, issuedAt, expiresAt, nonce)
4. **Payload strategy**: Raw token = `base64url(random_256bit_secret)`; opaque, no JSON claims
5. **Hash strategy**: Store only HMAC-SHA256(server secret, raw token) or SHA-256(raw token); never store raw token
6. **Token store**: Dev-only, file-backed JSONL recommended at `$HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl`; forbidden: ~/.hermes, production state.db, repo, frontend, provider logs
7. **TTL**: ≤ 5 minutes; token expiresAt ≤ dry-run expiresAt; expired blocks before digest verification
8. **Single-use**: Consumed before pre-execution audit readiness; reused token blocks with `confirmation_reused`
9. **Verification gate order**: 29 gates frozen (Gates 1–13 existing + Gates 14–29 new token gates)
10. **Failure contract**: 15 error codes; all block before handler lookup; all keep side-effect flags false
11. **Audit strategy**: Record tokenId, tokenHash prefix, binding fields; never raw token, secrets, or arguments
12. **Digest verification boundary**: Token verification ≠ digest verification; separate concerns; token checks recorded fields, digest independently verifies current request
13. **Execute route behavior delta**: Token implementation does not imply real execution; route may remain blocked after token verification
14. **Route governance**: No count change; 33/33/4/0/1/1 maintained
15. **Future OpenAPI**: No path change; may refine existing schemas
16. **Future test matrix**: 36 tests across issuance (10), verification (14), safety invariants (7), governance (5)

### Not Implemented

- Confirmation token issuance
- Confirmation token verification
- Token store
- Digest verification
- Pre/post execution audit
- Handler lookup
- Dispatch
- Execution
- Provider Schema sending
- Provider API call
- Frontend execute UI
- Audit read API
- Audit viewer
- Real Controlled Execution

### Route Governance (unchanged from 1G-04-17)

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

*Phase 1G-04-18 Confirmation Token Issuance / Verification Scope Freeze: confirmation token issuance, verification, storage, TTL, single-use, and dry-run binding design frozen, docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes, no token implementation, no token store, no digest verification, no handler lookup, no dispatch, no execution, no provider schema send, no allowlist change, no Controlled Execution started.*
