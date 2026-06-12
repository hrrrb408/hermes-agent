# Phase 1G-04-13: First Executable Tool Candidate Selection / Allowlist Activation Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-13 |
| Title | First Executable Tool Candidate Selection / Allowlist Activation Scope Freeze |
| Status | Frozen (docs-only, no implementation) |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-13 scope freeze) |
| Dependencies | Phase 1G-04-12 completed locally |
| Branch | dev-huangruibang |
| Base commit | 8c2bb40cffcec66ae5569c2093cdc62db440acc3 |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Freezes the future first executable tool candidate selection scope
2. Freezes the future STATIC_ALLOWLIST activation rules and policy
3. Defines candidate eligibility and exclusion criteria
4. Defines candidate selection strategy
5. Proposes a candidate recommendation or shortlist
6. Defines future allowlist activation rules (one-by-one, no wildcard, no auto-promotion)
7. Defines future STATIC_ALLOWLIST delta (not applied in this phase)
8. Defines kill switch / dry-run / confirmation / digest relationship to allowlisting
9. Defines execute route behavior delta (current vs. future)
10. Defines route governance strategy (no change)
11. Defines future OpenAPI strategy (no change)
12. Defines future allowed files, forbidden files, test matrix
13. Defines entry and exit criteria for future allowlist activation
14. Does **not** activate STATIC_ALLOWLIST
15. Does **not** modify STATIC_ALLOWLIST
16. Does **not** implement allowlist activation
17. Does **not** modify execute route behavior
18. Does **not** modify OpenAPI
19. Does **not** add runtime routes
20. Does **not** implement real Controlled Execution
21. Does **not** call tool handlers
22. Does **not** dispatch tools
23. Does **not** call providers
24. Does **not** execute tools

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Phase Definition

Phase 1G-04-13 = **First Executable Tool Candidate Selection / Allowlist Activation Scope Freeze**.

This phase freezes the future first executable tool candidate selection and allowlist activation scope.

This phase does not activate STATIC_ALLOWLIST.
This phase does not modify STATIC_ALLOWLIST.
This phase does not implement allowlist activation.
This phase does not modify execute route behavior.
This phase does not modify OpenAPI.
This phase does not add runtime routes.
This phase does not implement real Controlled Execution.
This phase does not call tool handlers.
This phase does not dispatch tools.
This phase does not call providers.
This phase does not execute tools.

---

## 2. Current Baseline

| Metric | Value |
|--------|-------|
| Remote HEAD | `8c2bb40cffcec66ae5569c2093cdc62db440acc3` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| Dry-Run API | Implemented |
| Dry-Run Audit Writer | Implemented |
| Execute Route | Implemented as blocked-only |
| Confirmation Token Scope | Frozen (Phase 1G-04-12) |
| Digest Scope | Frozen (Phase 1G-04-12) |
| Tool execution route count | 1 |
| Tool write route count | 0 |
| Controlled Execution implementation | Not started |
| STATIC_ALLOWLIST | Empty (`frozenset()`) |
| Provider Schema | Not sent |
| Tool Handler | Not called |
| Tool Execution | Disabled |
| Production Gateway PID | 80468 |

### Tool Inventory Summary

| Risk Tier | Count | Candidate Allowlisted |
|-----------|-------|----------------------|
| R0 | 1 (`clarify`) | Yes |
| R1 | 5 (`read_file`, `search_files`, `session_search`, `skill_view`, `skills_list`) | Yes |
| R2 | 19 | No |
| R3 | 26 | No |
| R4 | 17 | No |
| R5 | 3 | No |
| **Total** | **71** | **6** |

---

## 3. First Executable Tool Candidate Goal

The first executable tool candidate is the first tool that may later be considered for explicit STATIC_ALLOWLIST activation.

The candidate must be chosen for **safety**, **determinism**, **testability**, and **minimal blast radius**.

Candidate selection does not activate execution.
Candidate selection does not add the tool to STATIC_ALLOWLIST.
Candidate selection does not permit handler lookup.
Candidate selection does not permit dispatch.
Candidate selection does not permit execution.

### Critical Distinction

**Candidate selection is not allowlist activation.**

**Allowlist activation is not execution.**

Kill switches, dry-run, audit, confirmation token, digest verification, and all other gates still apply even after allowlist activation.

---

## 4. Candidate Eligibility Criteria

A tool may be considered as a first executable candidate only if it satisfies **all** of the following:

| # | Criterion | Rationale |
|---|-----------|-----------|
| 1 | **Must be R0 or R1** | Lowest risk tiers only; R2+ excluded for first candidate |
| 2 | **Must be local-only** | No external service dependencies |
| 3 | **Must be deterministic or nearly deterministic** | Same inputs produce same or predictable outputs |
| 4 | **Must not require provider credentials** | No API keys, tokens, or secrets needed |
| 5 | **Must not require network IO** | No outbound network requests |
| 6 | **Must not require shell/subprocess** | No process spawning |
| 7 | **Must not mutate production state** | No writes to ~/.hermes, production state.db, or production Gateway |
| 8 | **Must not read ~/.hermes** | Dev-home isolation required |
| 9 | **Must not access production state.db** | Dev-home isolation required |
| 10 | **Must not expose secrets** | No credential, key, or token exposure in output |
| 11 | **Must not require user private data beyond explicitly provided safe inputs** | No implicit data collection |
| 12 | **Must have bounded runtime** | Predictable, short execution time |
| 13 | **Must have bounded output** | Output size within redaction and truncation limits |
| 14 | **Must have JSON-safe output** | Output is JSON-serializable |
| 15 | **Must be redaction-compatible** | Output can be safely sanitized without data loss |
| 16 | **Must be testable with unit tests** | Full coverage achievable with mock inputs |
| 17 | **Must be reversible or side-effect-free** | No irreversible state changes |
| 18 | **Must be on CANDIDATE_ALLOWLIST** | Only pre-identified candidates are eligible |

---

## 5. Candidate Exclusion Criteria

The following categories of tools are **excluded** from first executable candidate consideration:

| # | Exclusion | Rationale |
|---|-----------|-----------|
| 1 | R2/R3/R4/R5 tools | Risk tiers too high for first candidate |
| 2 | Network-dependent tools | External service calls have unbounded risk |
| 3 | Provider-dependent tools | Provider API calls require credentials and create external state |
| 4 | Credential-dependent tools | Require API keys, tokens, or secrets |
| 5 | Filesystem mutation tools | Write operations unless explicitly dev-only and future-scoped |
| 6 | Shell/subprocess tools | Process execution has unbounded blast radius |
| 7 | Long-running tools | Unpredictable runtime exceeds safe limits |
| 8 | Tools that can touch production state | ~/.hermes or production state.db access prohibited |
| 9 | Tools that can leak secrets | Output may contain credentials or tokens |
| 10 | Tools requiring browser automation | Complex runtime dependencies |
| 11 | Tools requiring frontend UI | Frontend is not an execution target |
| 12 | Tools requiring audit read API | Audit reading is out of scope |
| 13 | Tools not on CANDIDATE_ALLOWLIST | Only pre-identified candidates (6 tools) are eligible |

---

## 6. Candidate Selection Strategy

The following strategy is used to select the first executable tool candidate:

1. **Enumerate existing canonical tool catalog.** Start from `TOOL_POLICY_INVENTORY` (71 tools).
2. **Filter by risk tier R0/R1.** Only the 6 CANDIDATE_ALLOWLIST tools qualify.
3. **Filter to local-only.** Remove any tool with network, provider, or remote dependencies.
4. **Filter out filesystem mutation.** Remove any tool that writes to files.
5. **Filter out tools with unbounded output.** Output must be bounded and redact-able.
6. **Filter out tools requiring external services.** No provider, network, or remote state.
7. **Prefer introspection or validation-style tools.** Tools that read/validate rather than transform.
8. **Prefer tools already represented in policy/dry-run tests.** Well-tested behavior reduces risk.
9. **Prefer tools whose arguments are simple and schema-bounded.** Small, well-defined input surface.
10. **Prefer tools whose result can be safely redacted and truncated.** Output fits within 64 KiB.

### Candidate Family Selection

This phase may select a candidate family and propose concrete canonical names, but must not activate:

- Candidate family may be selected.
- Concrete canonicalName may be proposed.
- No STATIC_ALLOWLIST change is made.
- No runtime allowlist activation is made.

If a unique candidate cannot be safely determined:

- Document candidate shortlist and require a future selection phase.
- Do not guess.
- Do not activate allowlist.

---

## 7. Candidate Recommendation

Based on analysis of the existing policy catalog (`hermes_cli/dev_web_tool_policy.py`), the following candidate evaluation is presented:

### Candidate Shortlist (All R0/R1 on CANDIDATE_ALLOWLIST)

| # | canonicalName | Risk Tier | Local-Only | No Network | No Secrets | No Shell | Bounded Output | Safety Assessment |
|---|--------------|-----------|------------|------------|------------|----------|----------------|-------------------|
| 1 | `clarify` | R0 | Yes | Yes | Yes | Yes | Yes (question string) | **Highest safety** — pure computation, no I/O, no filesystem, no DB |
| 2 | `skills_list` | R1 | Yes | Yes | Yes | Yes | Yes (name + description list) | **High safety** — directory listing, no path exposure |
| 3 | `skill_view` | R1 | Yes | Yes | Yes | Yes | Yes (skill content) | **Medium-high safety** — reads skill content, needs path restriction |
| 4 | `search_files` | R1 | Yes | Yes | Yes | Yes | Yes (search results) | **Medium safety** — filesystem read, needs root-allowlist |
| 5 | `read_file` | R1 | Yes | Yes | Yes | Yes | Variable (file content) | **Lower safety** — reads arbitrary file content, needs strict root enforcement |
| 6 | `session_search` | R1 | Yes | Yes | Yes | Yes | Yes (FTS5 results) | **Medium-high safety** — local DB read, needs output redaction |

### Recommended First Executable Candidate

```
Recommended first executable candidate:
- canonicalName:    clarify
- riskTier:         R0
- reason:           Purely interactive tool — asks user a question. No I/O, no filesystem
                    access, no database access, no network, no state mutation, no secrets.
                    Deterministic output (echo of question). Bounded input and output.
                    Sole R0 tool. Already has comprehensive dry-run and policy test coverage.
- required arguments: question (string)
- output boundary:   JSON-safe question string, bounded by MAX_ARGUMENT_STRING_LENGTH
- safety rationale:  Cannot mutate any state. Cannot read filesystem. Cannot access network.
                     Cannot access secrets. Cannot spawn processes. Output is the question
                     itself, which is already known to the caller.
- remaining blockers:
  1. STATIC_ALLOWLIST activation (separate phase)
  2. Kill switch enablement (HERMES_TOOL_EXECUTION_ENABLED, HERMES_AGENT_TOOLS_ENABLED)
  3. Confirmation token issuance/verification (not implemented)
  4. Digest verification (not implemented)
  5. Dry-run historical lookup (not implemented)
  6. Pre/post execution audit (not implemented)
  7. Tool handler lookup adapter (not implemented)
  8. User explicit approval
```

### Important Caveat

**This recommendation does not modify STATIC_ALLOWLIST.**

**This recommendation does not enable execution.**

If the candidate canonicalName cannot be confirmed from code audit alone (i.e., the real tool handler's actual behavior must be verified), then:

- Selection remains pending until handler-level confirmation.
- `clarify` remains the recommended candidate subject to handler audit.
- Do not activate STATIC_ALLOWLIST until handler behavior is verified.

---

## 8. Allowlist Activation Goal

STATIC_ALLOWLIST activation is the explicit future step that moves one selected canonical tool from candidate-only to allowlisted-for-execute-gate evaluation.

STATIC_ALLOWLIST activation must be **one-by-one**.
STATIC_ALLOWLIST activation must be **reviewed**.
STATIC_ALLOWLIST activation must be **committed as a separate implementation phase**.
STATIC_ALLOWLIST activation must be **tested**.
STATIC_ALLOWLIST activation must be **reversible**.

**Phase 1G-04-13 does not activate STATIC_ALLOWLIST.**

---

## 9. Allowlist Activation Rules

The following rules govern any future STATIC_ALLOWLIST activation:

| # | Rule | Rationale |
|---|------|-----------|
| 1 | No wildcard allowlist | Broad patterns circumvent per-tool review |
| 2 | No category allowlist | Category-level enablement skips individual review |
| 3 | No risk-tier allowlist | Tier-level enablement skips individual review |
| 4 | No candidate auto-promotion | Candidate status is advisory, not automatic approval |
| 5 | No dry-run auto-promotion | Dry-run success does not imply execution approval |
| 6 | No UI auto-promotion | UI actions cannot auto-add tools to allowlist |
| 7 | No provider auto-promotion | Provider suggestions cannot auto-add tools |
| 8 | No config auto-fill | Config files cannot populate allowlist |
| 9 | No environment-variable auto-fill | Env vars cannot populate allowlist |
| 10 | No implicit allowlist | Allowlist must be explicitly constructed in code |
| 11 | No broad regex allowlist | Regex patterns circumvent exact-name review |
| 12 | Only exact canonicalName may be allowlisted | Exact string match required |
| 13 | One commit activates at most one canonicalName | Atomic, reviewable changes |
| 14 | Activation must include tests proving Tool write routes remain 0 | Route governance invariant |
| 15 | Activation must include tests proving Tool execution routes remain 1 | Route governance invariant |
| 16 | Activation must not call handler by itself | Handler lookup is a separate gate |
| 17 | Activation must not execute by itself | Execution requires all gates |

---

## 10. STATIC_ALLOWLIST Future Delta

### Current State

```
STATIC_ALLOWLIST = frozenset()  # empty
```

### Future Implementation Phase

If `clarify` is confirmed as the first executable candidate:

```
STATIC_ALLOWLIST = frozenset({"clarify"})
```

**This delta is not applied in Phase 1G-04-13.**

If the candidate canonicalName is not finalized, the future delta remains pending:

```
STATIC_ALLOWLIST = frozenset()  # remains empty until candidate confirmed and approved
```

### Delta Application Requirements

Any future delta to STATIC_ALLOWLIST must satisfy:

1. The canonicalName must be on CANDIDATE_ALLOWLIST.
2. The canonicalName must be R0 or R1.
3. The canonicalName must have been individually audited against the real tool handler code.
4. The delta must be a single atomic commit.
5. The delta must be accompanied by updated tests.
6. The delta must not change route governance counts.
7. The delta must not enable execution by itself.

---

## 11. Kill Switch Relationship

Kill switches are **necessary but not sufficient** for tool execution.

| Switch | Requirement | Default |
|--------|-------------|---------|
| `HERMES_TOOL_EXECUTION_ENABLED` | Must be exactly `"true"` | Unset / disabled |
| `HERMES_AGENT_TOOLS_ENABLED` | Must be exactly `"true"` | Unset / disabled |

Any other value (including `"1"`, `"yes"`, `"True"`, `"TRUE"`, `"on"`, `"enabled"`) blocks execution.

Even if kill switches are `"true"` and STATIC_ALLOWLIST contains the candidate:
- Execution still requires dry-run preflight pass.
- Execution still requires auditWritten.
- Execution still requires confirmation token (when implemented).
- Execution still requires digest verification (when implemented).
- Execution still requires all remaining gates to pass.

Kill switches and allowlist are independent layers — neither substitutes for the other.

---

## 12. Dry-Run / Confirmation / Digest Relationship

Allowlisting does not bypass any gate.

| Gate | Relationship to Allowlist |
|------|--------------------------|
| Dry-Run | Candidate allowlisting does not bypass dry-run. Every execution must originate from a successful dry-run. |
| Audit Written | Candidate allowlisting does not bypass auditWritten. Dry-run audit must succeed before execution. |
| Confirmation Token | Candidate allowlisting does not bypass confirmation token. Token must be issued, valid, and unused. |
| Digest Verification | Candidate allowlisting does not bypass digest. SHA-256 digest must match the dry-run record. |
| Denylist | Candidate allowlisting does not bypass denylist. (Current candidates are not denylisted.) |
| Risk-Tier Check | Candidate allowlisting does not bypass risk-tier check. Only R0/R1 pass. |
| Result Redaction | Candidate allowlisting does not bypass redaction. All output is sanitized. |

---

## 13. Execute Route Behavior Delta

### Current Phase 1G-04-13 Baseline

- Execute route exists at `POST /api/dev/v1/tools/execute`
- Execute route is blocked-only — all requests return a blocked decision
- STATIC_ALLOWLIST is empty
- Token/digest not implemented
- No handler lookup
- No dispatch
- No execution

### Future Allowlist Activation Phase

- STATIC_ALLOWLIST may contain exactly one canonicalName (e.g., `clarify`)
- `blocked_by_allowlist` gate may be bypassed **only** for that canonicalName
- Route may still block at later gates (dry-run, confirmation, digest, handler)
- Handler lookup still forbidden unless a later explicit phase enables it

### Critical Distinction

**Allowlist activation does not imply execution.**

**Allowlist activation does not imply handler lookup.**

**Allowlist activation does not imply provider access.**

Allowlist activation only means the tool passes Gate 3 (STATIC_ALLOWLIST check) of the 9-gate evaluation stack. All remaining gates must still pass.

---

## 14. Route Governance Strategy

### Phase 1G-04-13

No route governance count change.

| Metric | Value | Change |
|--------|-------|--------|
| OpenAPI paths | 33 | None |
| Runtime routes | 33 | None |
| Tool GET routes | 4 | None |
| Tool write routes | 0 | None |
| Tool dry-run routes | 1 | None |
| Tool execution routes | 1 | None |

### Future STATIC_ALLOWLIST Activation

No route governance count change expected.

- OpenAPI paths should remain 33.
- Runtime routes should remain 33.
- Tool GET routes should remain 4.
- Tool write routes should remain 0.
- Tool dry-run routes should remain 1.
- Tool execution routes should remain 1.

Adding a tool to STATIC_ALLOWLIST changes runtime behavior of the existing execute route for that tool only — it does not add new routes or change governance counts.

---

## 15. Future OpenAPI Strategy

### Phase 1G-04-13

No OpenAPI change.

### Future Allowlist Activation

No OpenAPI path change expected. OpenAPI paths remain 33 unless a new route is added.

If future documentation needs to expose allowlist state (e.g., in the policy catalog response), that requires a separate scope document and may change existing response schemas without changing path counts.

Adding error codes (e.g., `confirmation_expired`, `confirmation_reused`) may change the OpenAPI error schema without changing path counts.

---

## 16. Future Allowed Files

The following files may be modified in a future STATIC_ALLOWLIST activation implementation phase:

### Backend Files

| File | Purpose |
|------|---------|
| `hermes_cli/dev_web_tool_policy.py` | Add canonicalName to STATIC_ALLOWLIST |
| `hermes_cli/dev_web_tool_execute.py` | Update gate evaluation for allowlisted tool |
| `hermes_cli/dev_web_api.py` | Update execute route response if needed |

### Test Files

| File | Purpose |
|------|---------|
| `tests/test_dev_web_tool_execute.py` | Tests for allowlist activation |
| `tests/test_dev_web_tool_execute_api.py` | API-level tests for allowlisted tool |
| `tests/test_dev_check_webui.py` | Governance invariant verification |
| `tests/test_dev_web_0c06_closure.py` | Boundary closure verification |

### Documentation Files

| File | Purpose |
|------|---------|
| `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` | Status update |
| `docs/webui/phase-1-implementation-plan.md` | Progress update |

### Optional New Files (if independent allowlist module needed)

| File | Purpose |
|------|---------|
| `hermes_cli/dev_web_tool_allowlist.py` | Independent allowlist activation module |
| `tests/test_dev_web_tool_allowlist.py` | Allowlist activation tests |

**These are future allowed files only. They are not modified in Phase 1G-04-13.**

---

## 17. Future Forbidden Files

The following files must **not** be modified in any STATIC_ALLOWLIST activation phase:

| File/Directory | Reason |
|----------------|--------|
| `apps/hermes-dev-webui/src/` | Frontend not modified until execute UI phase |
| `apps/hermes-dev-webui/tests/` | Frontend tests not modified until execute UI phase |
| `apps/hermes-dev-webui/e2e/` | E2E tests not modified until execute UI phase |
| `agent/` | Agent core not modified |
| `tools/` | Tool handlers not modified |
| `toolsets.py` | Toolset definitions not modified |
| Runtime files committed to repo | Runtime state files not modified |
| `memory/` files | Memory data not modified |
| `review/` files | Review data not modified |
| `.env` | Environment variables not modified |
| `.claude/` | Session data not modified |
| `~/.hermes` | Production home never accessed |
| Production `state.db` | Production state never accessed |
| `docs/webui/openapi/dev-web-api-v1.yaml` | OpenAPI file not modified for allowlist activation |

---

## 18. Future Test Matrix

The following tests must be implemented in the future STATIC_ALLOWLIST activation phase:

### STATIC_ALLOWLIST Tests

| # | Test | Category |
|---|------|----------|
| 1 | STATIC_ALLOWLIST empty blocks all canonical tools | Allowlist |
| 2 | Candidate selection does not modify STATIC_ALLOWLIST | Allowlist |
| 3 | Candidate selection does not change route governance | Governance |
| 4 | Allowlist activation accepts exact canonicalName only | Allowlist |
| 5 | Allowlist activation rejects wildcard | Allowlist |
| 6 | Allowlist activation rejects category | Allowlist |
| 7 | Allowlist activation rejects risk-tier broad enablement | Allowlist |
| 8 | Allowlist activation rejects unknown tool | Allowlist |
| 9 | Allowlist activation rejects R2/R3/R4/R5 first candidate | Allowlist |
| 10 | Allowlist activation rejects network/provider tools | Allowlist |
| 11 | Allowlist activation rejects shell/subprocess tools | Allowlist |
| 12 | Allowlist activation rejects production-state tools | Allowlist |

### Kill Switch Interaction Tests

| # | Test | Category |
|---|------|----------|
| 13 | Kill switches unset still block allowlisted candidate | Kill Switch |
| 14 | Kill switch `"true"` exactness still enforced | Kill Switch |
| 15 | Non-canonical truthy values still block | Kill Switch |

### Gate Stack Tests

| # | Test | Category |
|---|------|----------|
| 16 | Allowlisted candidate without dry-run still blocks | Gate Stack |
| 17 | Allowlisted candidate without confirmation still blocks | Gate Stack |
| 18 | Allowlisted candidate without digest verification still blocks | Gate Stack |

### Execution Boundary Tests

| # | Test | Category |
|---|------|----------|
| 19 | Allowlisted candidate does not call handler by itself | Execution |
| 20 | Allowlisted candidate does not dispatch by itself | Execution |
| 21 | Allowlisted candidate does not execute by itself | Execution |
| 22 | Allowlisted candidate does not call provider | Execution |

### Route Governance Tests

| # | Test | Category |
|---|------|----------|
| 23 | Tool write routes remain 0 | Governance |
| 24 | Tool execution routes remain 1 | Governance |
| 25 | OpenAPI paths remain 33 | Governance |
| 26 | Runtime routes remain 33 | Governance |

### Delta Management Tests

| # | Test | Category |
|---|------|----------|
| 27 | STATIC_ALLOWLIST delta has explicit review | Delta |
| 28 | STATIC_ALLOWLIST delta is reversible | Delta |

---

## 19. Entry Criteria for Future Allowlist Activation

Before any STATIC_ALLOWLIST activation implementation may begin, **all** of the following must be true:

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Phase 1G-04-13 docs pushed | Git history |
| 2 | No P0/P1 open | Issue tracker / scope review |
| 3 | User explicitly approves allowlist activation implementation | User instruction |
| 4 | Candidate canonicalName is confirmed | Handler code audit |
| 5 | Candidate is R0/R1 | Policy inventory |
| 6 | Candidate is local-only | Handler code audit |
| 7 | Candidate has no provider/network/secret/shell/production-state dependency | Handler code audit |
| 8 | Execute route remains blocked-only before implementation | Route governance tests |
| 9 | Route governance green | dev-check |
| 10 | Execute tests green | pytest |
| 11 | Dry-run regressions green | pytest |
| 12 | Production gateway stable | PID verification |

---

## 20. Exit Criteria for Future Allowlist Activation

After STATIC_ALLOWLIST activation implementation, **all** of the following must be true:

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | STATIC_ALLOWLIST contains at most one exact canonicalName | Code review |
| 2 | No wildcard/category/risk-tier allowlist | Code review |
| 3 | Tool write routes remain 0 | dev-check |
| 4 | Tool execution routes remain 1 | dev-check |
| 5 | OpenAPI paths remain 33 | dev-check |
| 6 | Runtime routes remain 33 | dev-check |
| 7 | Kill switches still required | Tests |
| 8 | Dry-run still required | Tests |
| 9 | Confirmation token still required (when implemented) | Tests |
| 10 | Digest verification still required (when implemented) | Tests |
| 11 | No handler call unless explicitly enabled by later phase | Tests |
| 12 | No dispatch unless explicitly enabled by later phase | Tests |
| 13 | No execution unless explicitly enabled by later phase | Tests |
| 14 | STATIC_ALLOWLIST delta is documented | Scope docs |
| 15 | Production gateway unaffected | PID verification |

---

## 21. Acceptance Criteria for Phase 1G-04-13

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Docs-only | ✅ |
| 2 | New first executable tool / allowlist scope doc added | ✅ |
| 3 | Phase 1G-04 scope doc updated | ✅ |
| 4 | Implementation plan updated | ✅ |
| 5 | No code changes | ✅ |
| 6 | No OpenAPI file changes | ✅ |
| 7 | No tests changed | ✅ |
| 8 | No frontend changes | ✅ |
| 9 | No routes changed | ✅ |
| 10 | No execute route behavior changes | ✅ |
| 11 | No STATIC_ALLOWLIST changes | ✅ |
| 12 | No allowlist activation | ✅ |
| 13 | No token implementation | ✅ |
| 14 | No digest verification implementation | ✅ |
| 15 | No Tool Handler call | ✅ |
| 16 | No Tool Dispatch | ✅ |
| 17 | No Tool Execution | ✅ |
| 18 | No Provider Schema sent | ✅ |
| 19 | No Provider API called | ✅ |
| 20 | OpenAPI paths still 33 | ✅ |
| 21 | Runtime routes still 33 | ✅ |
| 22 | Tool GET 4 | ✅ |
| 23 | Tool write 0 | ✅ |
| 24 | Tool dry-run 1 | ✅ |
| 25 | Tool execution 1 | ✅ |
| 26 | Execute route remains blocked-only | ✅ |
| 27 | Real Controlled Execution not started | ✅ |
| 28 | Local docs-only commit created | ✅ |
| 29 | Not pushed | ✅ |

---

## 22. Risk Classification

### P0 Risks (Must Block)

None identified. This phase is docs-only with no code changes.

### P1 Risks (Must Not Claim Completion)

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Scope doc missing first executable tool candidate goal | Section 3 |
| 2 | Scope doc missing candidate eligibility criteria | Section 4 |
| 3 | Scope doc missing candidate exclusion criteria | Section 5 |
| 4 | Scope doc missing candidate selection strategy | Section 6 |
| 5 | Scope doc missing candidate recommendation or shortlist | Section 7 |
| 6 | Scope doc missing allowlist activation goal | Section 8 |
| 7 | Scope doc missing allowlist activation rules | Section 9 |
| 8 | Scope doc missing STATIC_ALLOWLIST future delta | Section 10 |
| 9 | Scope doc missing kill switch relationship | Section 11 |
| 10 | Scope doc missing dry-run/confirmation/digest relationship | Section 12 |
| 11 | Scope doc missing execute route behavior delta | Section 13 |
| 12 | Scope doc missing route governance strategy | Section 14 |
| 13 | Scope doc missing future OpenAPI strategy | Section 15 |
| 14 | Scope doc missing future allowed files | Section 16 |
| 15 | Scope doc missing future forbidden files | Section 17 |
| 16 | Scope doc missing future test matrix | Section 18 |
| 17 | Scope doc missing entry criteria | Section 19 |
| 18 | Scope doc missing exit criteria | Section 20 |
| 19 | Scope doc incorrectly claims STATIC_ALLOWLIST populated | Review |
| 20 | Scope doc incorrectly claims allowlist activated | Review |
| 21 | Scope doc incorrectly claims execution enabled | Review |
| 22 | Route governance fails | Gate test |
| 23 | OpenAPI paths ≠ 33 | Gate test |
| 24 | Runtime routes ≠ 33 | Gate test |
| 25 | Tool GET ≠ 4 | Gate test |
| 26 | Tool write ≠ 0 | Gate test |
| 27 | Tool dry-run ≠ 1 | Gate test |
| 28 | Tool execution ≠ 1 | Gate test |
| 29 | memory-check fails | Gate test |
| 30 | dev-check fails | Gate test |
| 31 | compileall fails | Gate test |
| 32 | Worktree contains out-of-scope files | Boundary check |

### P2 Risks (Acceptable, Document)

| # | Risk | Notes |
|---|------|-------|
| 1 | Final canonicalName may still require future implementation phase confirmation | `clarify` recommended but handler audit pending |
| 2 | STATIC_ALLOWLIST remains empty | Expected — no activation in this phase |
| 3 | Allowlist activation not implemented | Expected — future phase |
| 4 | Confirmation token issuance/verification not implemented | Expected — future phase |
| 5 | Token store not implemented | Expected — future phase |
| 6 | Digest verification not implemented | Expected — future phase |
| 7 | Dry-run historical lookup not implemented | Expected — future phase |
| 8 | Pre/post execution audit not implemented | Expected — future phase |
| 9 | Execute route still does not execute tools | Expected — blocked-only |
| 10 | Frontend execute UI not implemented | Expected — future phase |
| 11 | Browser smoke not re-run | Expected — no code changes |
