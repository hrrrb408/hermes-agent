# Phase 1G-04-14: Clarify Allowlist Activation / Still Blocked-Only

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-14 |
| Title | Clarify Allowlist Activation / Still Blocked-Only |
| Status | Completed locally |
| Date | 2026-06-12 |
| Author | Dev Agent (Phase 1G-04-14 implementation) |
| Dependencies | Phase 1G-04-13 completed and pushed |
| Branch | dev-huangruibang |
| Base commit | `ad1f7026c3c3a18c7f5f0acc3b7b0afa39c6ccb1` |
| Pushed | No |

---

## 1. Phase Definition

Phase 1G-04-14 = **Clarify Allowlist Activation / Still Blocked-Only**.

This phase activates the STATIC_ALLOWLIST gate for exactly one tool: `clarify`.
The execute route remains blocked-only. No tool handler is called. No dispatch occurs.
No execution is enabled. No Provider Schema is sent. No Provider API is called.

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base commit | `ad1f7026c3c3a18c7f5f0acc3b7b0afa39c6ccb1` (Phase 1G-04-13) |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST before | `frozenset()` (empty) |
| Dry-Run API | Implemented |
| Dry-Run Audit Writer | Implemented |
| Execute Route | Implemented as blocked-only |
| Confirmation Token | Not implemented |
| Digest Verification | Not implemented |
| Tool Handler lookup | Not implemented |
| Tool Dispatch | Not implemented |
| Tool Execution | Disabled |
| Provider Schema | Not sent |
| Provider API | Not called |
| Production Gateway PID | 80468 |

---

## 3. Implemented Delta

### STATIC_ALLOWLIST Change

```
Before: STATIC_ALLOWLIST = frozenset()
After:  STATIC_ALLOWLIST = frozenset({"clarify"})
```

### clarify Entry Update

```
ToolPolicyEntry(
    canonical_name="clarify",
    ...
    statically_allowed=False,  →  statically_allowed=True,
    ...
)
```

### Execute Gate Update

Gate 3 (Static Allowlist) in `dev_web_tool_execute.py` changed from:
- Empty-allowlist check: `if len(STATIC_ALLOWLIST) == 0: block`
- To membership check: `if canonical_name not in STATIC_ALLOWLIST: block`

### Dev-Check Update

`main.py` dev-check gate changed from:
- `len(STATIC_ALLOWLIST) == 0` → PASS
- To `STATIC_ALLOWLIST == frozenset({"clarify"})` → PASS

### Integrity Verification Update

`_verify_inventory_integrity()` and `validate_static_tool_policy()` now verify:
- `STATIC_ALLOWLIST == frozenset({"clarify"})` (exactly one tool, exactly "clarify")

### Policy Decision Update

`evaluate_static_tool_policy("clarify")` now returns:
- `allowed=True`
- `statically_allowed=True`
- `reason_code="TOOL_ALLOWED"`

### Test Updates

All tests that previously asserted `STATIC_ALLOWLIST == frozenset()` or `len(STATIC_ALLOWLIST) == 0` updated to assert `STATIC_ALLOWLIST == frozenset({"clarify"})`.

New tests added for:
- clarify passes allowlist gate but blocked by later gates
- non-clarify tools remain blocked_by_allowlist
- All side-effect flags remain false for both clarify and non-clarify

---

## 4. Why clarify

| Criterion | Assessment |
|-----------|------------|
| Risk tier | R0 — pure computation |
| I/O | None |
| Filesystem | No access |
| Database | No access |
| Network | No access |
| Provider | No provider dependency |
| Secrets | No credential exposure |
| Shell/subprocess | None |
| Output | Question string — bounded, JSON-safe, known to caller |
| Determinism | Deterministic |
| Reversibility | Side-effect-free |
| Testability | Full coverage achievable with mock inputs |
| Candidate status | On CANDIDATE_ALLOWLIST (6 tools, R0/R1 only) |

---

## 5. What This Does NOT Enable

This allowlist activation does **not** enable:

- Tool Handler lookup — handler lookup is not implemented
- Tool Dispatch — dispatch is not implemented
- Tool Execution — execution is not implemented
- Provider Schema sending — not implemented
- Provider API calls — not implemented
- Confirmation Token issuance/verification — not implemented
- Digest verification — not implemented
- Dry-run historical lookup — not implemented
- Pre/post execution audit — not implemented
- Real Controlled Execution — not started

The execute route remains blocked-only. `clarify` only passes Gate 3 (STATIC_ALLOWLIST);
it is still blocked by Gates 7–9 (dry-run preflight, digest, confirmation token).

---

## 6. Kill Switch Relationship

Kill switches are still required and still enforced:

| Switch | Requirement | Behavior |
|--------|-------------|----------|
| `HERMES_TOOL_EXECUTION_ENABLED` | Must be exactly `"true"` | Unset/default → blocked_by_kill_switch |
| `HERMES_AGENT_TOOLS_ENABLED` | Must be exactly `"true"` | Unset/default → blocked_by_kill_switch |

`"TRUE"`, `"True"`, `"1"`, `"yes"`, `"on"` all continue to block.

Even with both kill switches set to exact `"true"`:
- `clarify` passes Gates 1–3 but blocks at Gate 7 (dry-run preflight)
- Non-`clarify` tools block at Gate 3 (not in STATIC_ALLOWLIST)

---

## 7. Dry-Run / Confirmation / Digest Relationship

| Gate | Relationship to Allowlist Activation |
|------|--------------------------------------|
| Gate 7: Dry-run preflight | `clarify` still requires dry-run. Not bypassed. |
| Gate 8: Digest | `clarify` still requires digest. Not bypassed. |
| Gate 9: Confirmation token | `clarify` still requires token. Not bypassed. |
| Denylist | Not bypassed (clarify is not denylisted). |
| Risk-tier | Not bypassed (clarify is R0, passes automatically). |

---

## 8. Blocked-Only Guarantee

All execute responses continue to satisfy:

```
executionAllowed = false
dispatchAllowed = false
providerSchemaAllowed = false
toolHandlerCalled = false
providerApiCalled = false
executionStarted = false
executionAttempted = false
executionCompleted = false
```

This is true for:
- `clarify` with kill switches unset → blocked_by_kill_switch
- `clarify` with kill switches exact "true" → blocked_requires_dry_run
- Non-`clarify` tools → blocked_by_allowlist
- Unknown tools → blocked_by_allowlist
- Denylisted tools → blocked_by_allowlist

---

## 9. Route Governance

No route governance changes.

| Metric | Value | Change |
|--------|-------|--------|
| OpenAPI paths | 33 | None |
| Runtime routes | 33 | None |
| Tool GET routes | 4 | None |
| Tool write routes | 0 | None |
| Tool dry-run routes | 1 | None |
| Tool execution routes | 1 | None |

Adding a tool to STATIC_ALLOWLIST changes runtime behavior of the existing execute route
for that tool only — it does not add new routes or change governance counts.

---

## 10. Security Boundary

### Code Changed

| File | Change |
|------|--------|
| `hermes_cli/dev_web_tool_policy.py` | STATIC_ALLOWLIST, clarify entry, integrity checks, decision logic |
| `hermes_cli/dev_web_tool_execute.py` | Gate 3 membership check |
| `hermes_cli/main.py` | dev-check allowlist gate |

### Not Changed

| Item | Status |
|------|--------|
| OpenAPI file | Not modified |
| Frontend source | Not modified |
| Routes | No new routes |
| Execute route behavior | Still blocked-only |
| Handler lookup | Not enabled |
| Tool Handler called | Never |
| Tool Dispatch | Never |
| Tool Execution | Never |
| Provider Schema sent | Never |
| Provider API called | Never |
| Confirmation Token | Not implemented |
| Digest Verification | Not implemented |
| Dry-run historical lookup | Not implemented |
| Pre/post execution audit | Not implemented |
| Real Controlled Execution | Not started |

---

## 11. Tests

| Test Suite | Count | Result |
|------------|-------|--------|
| `test_dev_web_tool_execute.py` | Model tests | All pass |
| `test_dev_web_tool_execute_api.py` | API tests | All pass |
| `test_dev_web_tool_policy.py` | Policy tests | All pass |
| `test_dev_web_tool_policy_api.py` | Policy API tests | All pass |
| `test_dev_web_tool_schema_preview.py` | Schema preview tests | All pass |
| `test_dev_web_tool_schema_preview_api.py` | Schema preview API tests | All pass |
| `test_dev_web_tool_dry_run.py` | Dry-run model tests | All pass |
| `test_dev_web_tool_dry_run_api.py` | Dry-run API tests | All pass |
| `test_dev_web_tool_dry_run_audit.py` | Audit tests | All pass |
| `test_dev_check_webui.py` | Route governance tests | All pass |
| `test_dev_web_0c06_closure.py` | Closure tests | All pass |
| **Total** | **1141 passed** | **0 failed** |

### New Test Coverage

- `clarify` passes allowlist gate when kill switches exact "true"
- `clarify` blocked by dry-run gate after passing allowlist
- Non-clarify candidate tools blocked by allowlist
- `STATIC_ALLOWLIST == frozenset({"clarify"})`
- `STATIC_ALLOWLIST` is frozenset (immutable)
- All blocked responses have side-effect flags false
- Policy summary reports allowlist size 1, tools ("clarify",)
- Route governance unchanged: 33/33/4/0/1/1

---

## 12. Risks

### P0 Risks

None identified. STATIC_ALLOWLIST contains exactly `clarify`. No wildcard, category,
risk-tier, dynamic, environment-derived, or candidate-list-wide allowlist was introduced.
No execution, handler, dispatch, provider, or real Controlled Execution was enabled.

### P1 Risks

None identified. All gates and tests pass. Route governance is correct. Production gateway
unaffected.

### P2 Risks (Acceptable, Documented)

| # | Risk | Notes |
|---|------|-------|
| 1 | Execute route still does not execute tools | Expected — blocked-only |
| 2 | Handler lookup not enabled | Expected — future phase |
| 3 | Confirmation token not implemented | Expected — future phase |
| 4 | Token store not implemented | Expected — future phase |
| 5 | Digest verification not implemented | Expected — future phase |
| 6 | Dry-run historical lookup not implemented | Expected — future phase |
| 7 | Pre/post execution audit not implemented | Expected — future phase |
| 8 | Frontend execute UI not implemented | Expected — future phase |
| 9 | Browser smoke not re-run | Expected — no frontend changes |
| 10 | `policy_service.py` comment "Always false — STATIC_ALLOWLIST is empty" is stale | Cosmetic only; DTO `allowed` field still correctly reflects `entry.statically_allowed` |
| 11 | `clarify` handler-level audit still needed | Future phase |

---

## 13. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | STATIC_ALLOWLIST exactly `frozenset({"clarify"})` | ✅ |
| 2 | clarify is the only allowlisted canonicalName | ✅ |
| 3 | No wildcard/category/risk-tier allowlist | ✅ |
| 4 | Non-clarify tools remain blocked_by_allowlist | ✅ |
| 5 | Kill switches unset still block clarify | ✅ |
| 6 | Kill switches wrong value still block clarify | ✅ |
| 7 | Kill switches exact "true" + clarify passes allowlist but blocks at later gates | ✅ |
| 8 | Execute route remains blocked-only | ✅ |
| 9 | No handler lookup | ✅ |
| 10 | No dispatch | ✅ |
| 11 | No execution | ✅ |
| 12 | No provider schema | ✅ |
| 13 | No provider API | ✅ |
| 14 | No confirmation token implementation | ✅ |
| 15 | No digest verification implementation | ✅ |
| 16 | No dry-run historical lookup | ✅ |
| 17 | No pre/post execution audit | ✅ |
| 18 | No frontend changes | ✅ |
| 19 | No OpenAPI changes | ✅ |
| 20 | No route count changes | ✅ |
| 21 | OpenAPI paths = 33 | ✅ |
| 22 | Runtime routes = 33 | ✅ |
| 23 | Tool GET = 4 | ✅ |
| 24 | Tool write = 0 | ✅ |
| 25 | Tool dry-run = 1 | ✅ |
| 26 | Tool execution = 1 | ✅ |
| 27 | 1141 tests pass | ✅ |
| 28 | memory-check PASS | ✅ |
| 29 | dev-check PASS (only .claude/ WARN) | ✅ |
| 30 | Production Gateway PID 80468 unaffected | ✅ |
| 31 | Local commit created | ✅ |
| 32 | Not pushed | ✅ |
| 33 | Real Controlled Execution not started | ✅ |
