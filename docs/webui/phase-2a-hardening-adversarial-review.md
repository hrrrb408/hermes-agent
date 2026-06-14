# Phase 2A-H1 — Hardening: Adversarial Review Completion

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2A-H1 |
| Title | Hardening — Adversarial Review Completion & Boundary Stabilization |
| Status | Completed |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Input HEAD | `0527d6c892b24afde03ff9259a612b2f59ee8018` |
| Hardening ID | `HARDENING-2A-H1-001` |
| Adversarial Review Closure ID | `ADV-REVIEW-CLOSURE-2A-H1-001` |
| Boundary Audit ID | `BOUNDARY-AUDIT-2A-H1-001` |
| Scope | Close the Phase 2A P2 (adversarial-review agent died mid-run) with a deterministic, reproducible 7-lens hardening audit. No new feature capability. |

---

## 1. Original P2

During the Phase 2A final hardening pass, an **adversarial-review agent died
mid-run**. The Phase 2A final report recorded this as a P2:

> `agent error, not a finding` — Phase 1G preservation already independently
> verified by the full Phase 1G test suite, the live completed smoke profile,
> the end-to-end clarify check, and the security/routes/allowlist reviewers
> (all clean).

The P2 was correctly classified as a **process / tooling issue, not a product
defect**: the underlying Phase 2A surface (read-only multi-tool execution) and
the Phase 1G controlled-execution chain were already independently verified by
multiple deterministic gates. What was missing was a **single, reproducible,
agent-independent adversarial-review artifact** that future phases can re-run
to obtain the same verdict without depending on a live agent staying alive.

---

## 2. Why This Is a Process / Tooling P2, Not a Product P0 / P1

| Question | Answer |
|----------|--------|
| Did Phase 2A introduce a Provider Schema send? | No — `providerSchemaSent` is hardcoded `False` everywhere. |
| Did Phase 2A introduce a Provider API call? | No — `providerApiCalled` is hardcoded `False` everywhere. |
| Did Phase 2A add a Tool write route? | No — Tool write routes remain `0`. |
| Did Phase 2A add any HTTP route? | No — route governance stays `34/34/5/0/1/1`. |
| Did Phase 2A expand the allowlist beyond 6 read-only tools? | No — `STATIC_ALLOWLIST` is exactly `{clarify, tool_policy_read, route_governance_read, audit_events_read, dev_environment_read, release_status_read}`. |
| Did Phase 2A break the Phase 1G clarify chain? | No — the clarify path is preserved exactly. |
| Did the agent failure leak any secret / token / repr? | No — the agent produced no partial output that reached any artifact. |

Every product-level invariant already held. The P2 was the **absence of a
closed, reproducible adversarial-review record**, which is a process gap.

---

## 3. Replacement Hardening Method

Phase 2A-H1 replaces the unstable agent-only adversarial-review evidence path
with a **deterministic 7-lens hardening audit**:

1. A committed test file —
   `tests/test_dev_web_phase_2a_hardening_boundaries.py` (45 tests) — encodes
   every lens invariant as an assertion. It is deterministic (no live gateway
   dependency; the dev_environment_read probe is monkeypatched), hermetic (no
   `~/.hermes` / `state.db` / network), and re-runnable on any clean checkout.
2. A committed audit script —
   `scripts/run-dev-webui-phase2a-hardening-audit.sh` — orchestrates the
   automatable lens checks, the smoke harness, and the Hermes health gates,
   and prints a PASS / FAIL summary with a non-zero exit on failure.
3. This document records the per-lens evidence, findings, fixes, and final
   verdict.

A dead agent can no longer leave the adversarial review unclosed, because the
review is now a checked-in, deterministic artifact — not a live agent.

---

## 4. 7-Lens Review Matrix

| Lens | Name | Status | Findings | Fixes |
|------|------|--------|----------|-------|
| 1 | Phase 1G Preservation | **PASS** | 0 | none |
| 2 | Allowlist / Registry Boundary | **PASS** | 0 | none |
| 3 | Route Governance / OpenAPI Boundary | **PASS** | 0 | none |
| 4 | Provider / Write / Side-effect Boundary | **PASS** | 0 | none |
| 5 | Audit Redaction / Secret Exposure Boundary | **PASS** | 0 | none |
| 6 | Production Isolation / Runtime Safety Boundary | **PASS** | 0 | none |
| 7 | Frontend Contract / Smoke / User Flow Boundary | **PASS** | 0 | none |

**Final: 7 / 7 PASS. 0 P0. 0 P1.**

---

## 5. Per-Lens Evidence

### Lens 1 — Phase 1G Preservation

- **Scope:** confirm Phase 2A did not disturb the Phase 1G clarify-only
  controlled-execution chain.
- **Evidence checked:** `clarify ∈ STATIC_ALLOWLIST`;
  `_is_supported_controlled_tool("clarify")`; the
  `clarify_execution_completed` / `blocked_handler_call_not_clarify` decision
  constants; the clarify `{type, message, questions}` envelope; the full
  Phase 1G backend chain (execute, confirmation, digest, preflight,
  handler-call, dispatch, handler-lookup, pre/post audit).
- **Commands run:** `./scripts/run_tests.sh` over the 10 Phase 1G chain files;
  `./scripts/run-dev-webui-execute-audit-smoke.sh completed`;
  `./scripts/run-dev-webui-execute-audit-smoke.sh blocked`.
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. 626 tests passed / 0 failed across the 10 chain
  files; both smoke profiles PASS.
- **Residual risk:** none.

### Lens 2 — Allowlist / Registry Boundary

- **Scope:** confirm `STATIC_ALLOWLIST` expanded only to the 6 read-only tools,
  single-source, and consistent with the registry.
- **Evidence checked:** `STATIC_ALLOWLIST == {clarify + 5 read-only}`;
  `PHASE_2A_READ_ONLY_TOOL_IDS == 5`; static ⊆ candidate; static ∩ deny = ∅;
  every tool `read_only / provider_required=False / write_required=False /
  external_side_effects=False / requires_confirmation=True / safety_tier
  "read_only_safe" / enabled_in_phase "2A"`; unsupported / write / shell /
  provider / unknown tools stay out.
- **Commands run:** `./scripts/run_tests.sh tests/test_dev_web_phase_2a_read_only_registry.py tests/test_dev_web_phase_2a_security_boundaries.py`.
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. 156 tests passed / 0 failed (4-file group).
- **Residual risk:** none.

### Lens 3 — Route Governance / OpenAPI Boundary

- **Scope:** confirm Phase 2A added zero HTTP routes.
- **Evidence checked:** OpenAPI paths == runtime routes == 34; Tool GET == 5;
  Tool write == 0; Tool dry-run == 1; Tool execution == 1; no second execution
  route; no write route; no Provider route.
- **Commands run:** `./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py`.
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. 124 tests passed / 0 failed. Governance frozen at
  `34/34/5/0/1/1`.
- **Residual risk:** none.

### Lens 4 — Provider / Write / Side-effect Boundary

- **Scope:** confirm Phase 2A enabled no Provider, introduced no write, no
  external side effects.
- **Evidence checked:** every Phase 2A tool completes with
  `providerSchemaSent / providerApiCalled / externalSideEffects /
  filesystemChanged / networkCalled` all `False`, plus top-level
  `executionAllowed / dispatchAllowed / providerSchemaAllowed` all `False`;
  the handler-call and post-execution-audit modules hardcode
  `"providerSchemaSent": False` and `"providerApiCalled": False`.
- **Commands run:** `./scripts/run_tests.sh tests/test_dev_web_phase_2a_read_only_execute.py tests/test_dev_web_phase_2a_security_boundaries.py`;
  `rg -n "providerSchemaSent|providerApiCalled" …` (only `False` literals +
  doc comments).
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. No Provider completion state anywhere.
- **Residual risk:** none.

### Lens 5 — Audit Redaction / Secret Exposure Boundary

- **Scope:** confirm Phase 2A multi-tool audit leaks no raw token, full
  tokenHash, raw arguments, secrets, or callable/function repr.
- **Evidence checked:** result envelopes + audit JSONL (dry-run, pre-execution,
  post-execution) for all five tools contain no `Bearer `, `BEGIN PRIVATE KEY`,
  `sk-`, `<function`, `<bound method`, `object at 0x`, `rawToken`,
  `rawArguments`, `fullTokenHash`; per-tool `toolId` filter isolates one tool.
- **Commands run:** `./scripts/run_tests.sh` over the 6 audit files (Phase 2A
  audit + dry-run-audit + pre/post audit + audit-read + audit-read-api).
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. 204 tests passed / 0 failed (6-file group).
- **Residual risk:** none.

### Lens 6 — Production Isolation / Runtime Safety Boundary

- **Scope:** confirm neither Phase 2A nor this hardening phase touched
  production.
- **Evidence checked:** `PRODUCTION_GATEWAY_EXPECTED_PID == 1962`; handler /
  registry / execute modules contain no `os.kill`, `.terminate(`, `os.system(`,
  `Popen(`, `import signal`, no `~/.hermes` / `state.db` access in real code,
  no `prod_path.read/write/open`; the only subprocess use is bounded
  `shutil.which`-guarded read-only `pgrep` / `lsof` (5s timeout, errors
  swallowed); live observation PID 1962, count 1, ports 5180/5181 free before
  and after.
- **Commands run:** `ps` / `pgrep` / `lsof`; source `rg` over the read-only
  scope; the hardening boundary test Lens 6 class.
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. No production access; gateway untouched.
- **Residual risk:** future host-reboot PID drift is a carried-over P2 (the
  smoke harness fails closed on it; it does not block Phase 2A-H1).

### Lens 7 — Frontend Contract / Smoke / User Flow Boundary

- **Scope:** confirm the frontend multi-tool UI, execution result, and audit
  filter match the backend contract.
- **Evidence checked:** frontend `SELECTABLE_TOOLS` mirrors the backend
  `STATIC_ALLOWLIST` (6 tools, clarify first); `DEFAULT_TOOL == clarify`;
  `pnpm type-check` / `pnpm lint` / `pnpm test` / `pnpm build` all pass; the
  `phase2a` smoke profile exercises all five read-only tools + the audit
  `toolId` filter + the multi-tool selector.
- **Commands run:** `pnpm type-check`, `pnpm lint`, `pnpm test` (692 passed),
  `pnpm build` (1863 modules); `./scripts/run-dev-webui-execute-audit-smoke.sh all`.
- **Findings:** 0.
- **Fixes:** none.
- **Final status:** **PASS**. 692 frontend unit tests passed / 0 failed; smoke
  `phase2a` profile 7 passed / 0 failed; smoke `all` Overall PASS.
- **Residual risk:** none.

---

## 6. Fixes Applied

No product-code fixes were required. All seven lenses passed on the existing
Phase 2A baseline. The only changes introduced by Phase 2A-H1 are the
deterministic hardening artifacts themselves:

- `tests/test_dev_web_phase_2a_hardening_boundaries.py` (new — 45 tests)
- `scripts/run-dev-webui-phase2a-hardening-audit.sh` (new — deterministic
  7-lens audit)
- `docs/webui/phase-2a-hardening-*.md` (new — this + boundary-audit +
  test-report + closure)
- `docs/webui/phase-1g-05-risk-register.md` (addendum)
- `docs/webui/phase-1-implementation-plan.md` (addendum)

---

## 7. Final Verdict

**7 / 7 lenses PASS. 0 P0. 0 P1.** The original Phase 2A P2 — adversarial-review
agent died mid-run — is **resolved** by `ADV-REVIEW-CLOSURE-2A-H1-001`.

The adversarial review is now a checked-in, deterministic, agent-independent
artifact. A dead agent can no longer leave the review unclosed.

---

## 8. Residual Risks

- **P0:** none.
- **P1:** none.
- **P2 (carried forward):** future Production Gateway PID drift on host reboot
  (the smoke harness fails closed and requires a new refresh phase); the
  accepted non-blocking audit-scale / pagination / rotation limitations
  (P2-02 / P2-03 / P2-04 / P2-08); Provider integration deferred to Phase 2B;
  Tool write deferred to Phase 2C.

---

## 9. Closure Statement

Phase 2A-H1 Hardening completed successfully. The original Phase 2A P2
(adversarial-review agent died mid-run) is closed by
`ADV-REVIEW-CLOSURE-2A-H1-001`. A deterministic 7-lens hardening audit
replaced the unstable agent-only evidence path. All seven lenses passed:
Phase 1G Preservation, Allowlist / Registry Boundary, Route Governance /
OpenAPI Boundary, Provider / Write / Side-effect Boundary, Audit Redaction /
Secret Exposure Boundary, Production Isolation / Runtime Safety Boundary, and
Frontend Contract / Smoke / User Flow Boundary. No P0 or P1 findings remain.

Phase 2A read-only multi-tool execution remains intact for `clarify`,
`tool_policy_read`, `route_governance_read`, `audit_events_read`,
`dev_environment_read`, and `release_status_read`. The Phase 1G controlled
execution chain remains preserved. Route governance remains `34/34/5/0/1/1`.

Phase 2B was not started.
