# Phase 1G-06: Pilot Release Rehearsal

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-06 |
| Title | Pilot Release Rehearsal & Smoke Harness Hardening |
| Status | Pushed (release rehearsal baseline, `311221e0d`) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Base commit | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` (Phase 1G-05 readiness baseline) |
| Scope | Release rehearsal checklist, release-candidate validation, go/no-go template, smoke harness hardening. No code feature, no route, no allowlist change. |
| Author | Dev Agent (Phase 1G-06 pilot release rehearsal) |

---

## 1. Phase Definition

Phase 1G-06 is an **independent release-rehearsal phase** that runs *after* the
Phase 1G-05 Post-Sealing Readiness baseline was pushed at `da5c31a8c`.

Phase 1G-06 does **not** reopen Phase 1G-04. It does **not** introduce any new
product capability. It hardens the release rehearsal and smoke execution only:

1. Re-confirm the Phase 1G-04 sealed baseline and the Phase 1G-05 pushed baseline.
2. Fixate the execute/audit browser smoke as a repeatable, committed harness.
3. Define the gate profiles (A blocked / B completed / C fully-disabled) precisely.
4. Establish a Pilot release rehearsal checklist.
5. Establish a release-candidate validation report.
6. Establish a smoke harness runbook + a dev-only committed smoke script.
7. Establish a reusable go / no-go decision template.
8. Re-run the final backend, frontend, smoke, memory, and dev gates.
9. Confirm route governance and safety boundaries are unchanged.
10. Confirm the production instance is unaffected.
11. Create a single local commit.
12. Do **not** push.
13. Do **not** start Phase 1G-07.

> **Hard separation:** Phase 1G-04 is sealed. Phase 1G-05 is the pushed
> readiness baseline. Phase 1G-06 adds **no** functionality. It converts the
> Phase 1G-05 readiness into a repeatable release rehearsal baseline.

---

## 2. Baselines

### 2.1 Phase 1G-04 sealed baseline

| Item | Value |
|------|-------|
| Phase 1G-04 status | **SEALED** |
| Sealing commit | `docs(webui): seal phase 1g-04` → `94f22f67b` |
| Full chain | dry-run historical lookup → confirmation token → digest verification → pre-execution audit → handler lookup → dispatch planning → clarify-only handler call → post-execution audit → read-only audit events API → frontend Execute UI → audit viewer → browser smoke / E2E |

### 2.2 Phase 1G-05 readiness baseline

| Item | Value |
|------|-------|
| Phase 1G-05 status | **Pushed readiness baseline** |
| Push commit | `docs(webui): add phase 1g-05 readiness baseline` → `da5c31a8c` |
| Deliverables | post-sealing readiness, pilot acceptance baseline, release checklist, ops / rollback runbook, risk register |

### 2.3 Current HEAD at Phase 1G-06 start

| Item | Value |
|------|-------|
| Local HEAD | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` |
| Remote HEAD | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` |
| Merge base | `da5c31a8ccfec7c5d0e61bff5de5b8e704fb7a38` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |
| Dev `HERMES_HOME` | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway PID | `69355` |

---

## 3. Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

Phase 1G-06 changes **nothing** about route governance or the allowlist. Both
are re-verified by `tests/test_dev_check_webui.py`,
`tests/test_dev_web_0c06_closure.py`, and `./scripts/run-dev-hermes.sh dev-check`.

---

## 4. Release Rehearsal Goal

Convert the Phase 1G-05 readiness artifacts into a **repeatable rehearsal**:

- Anyone running the rehearsal can reproduce the exact gate profiles and the
  exact expected UI / API decisions without ad-hoc `/tmp` scripts.
- The rehearsal is anchored on a committed dev-only smoke harness so the
  execution / audit path is exercised identically every time.
- A go / no-go decision can be recorded against a fixed template.

The rehearsal does **not** execute a real Pilot against production. It runs only
against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Dev API bind: `127.0.0.1:5181`
- WebUI bind: `127.0.0.1:5180`
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID `69355`: **never affected**

---

## 5. Smoke Gate Profiles

The execute route's behavior is determined by the gate env vars the Dev API
process inherits at startup. `EXECUTE_EXPECTED` tells the Playwright smoke spec
which decision string to assert on the current configuration.

### 5.1 Profile A — handler-call blocked

Goal: upstream execution gates are on, but the handler-call gate is **off**, so
the UI / API shows `blocked_tool_handler_call_not_enabled`.

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
export HERMES_TOOL_EXECUTION_ENABLED=true
export HERMES_AGENT_TOOLS_ENABLED=true
# HERMES_TOOL_HANDLER_CALL_ENABLED intentionally UNSET
export EXECUTE_EXPECTED=blocked_tool_handler_call_not_enabled
```

Expected:

- `decision = blocked_tool_handler_call_not_enabled`
- `toolHandlerCalled = false`
- `executionCompleted = false`
- `providerSchemaSent = false`
- `providerApiCalled = false`
- `externalSideEffects = false`

> **Common mistake (recorded):** unsetting *all* gates does **not** produce
> `blocked_tool_handler_call_not_enabled` — it produces `blocked_by_kill_switch`
> (the first gate). To exercise the handler-call-blocked decision, the upstream
> execution gates must be **on** while `HERMES_TOOL_HANDLER_CALL_ENABLED`
> remains **unset**.

### 5.2 Profile B — clarify completed

Goal: explicit dev/test gates on with `canonicalName=clarify`, so the UI / API
shows `clarify_execution_completed`.

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
export HERMES_TOOL_EXECUTION_ENABLED=true
export HERMES_AGENT_TOOLS_ENABLED=true
export HERMES_TOOL_HANDLER_CALL_ENABLED=true
export HERMES_POST_EXECUTION_AUDIT_ENABLED=true
export EXECUTE_EXPECTED=clarify_execution_completed
```

Expected:

- `decision = clarify_execution_completed`
- `canonicalName = clarify`
- `handlerCallId` starts with `thc_`
- `postExecutionAuditId` starts with `pexa_`
- `providerSchemaSent = false`
- `providerApiCalled = false`
- `externalSideEffects = false`
- audit viewer shows the post-execution audit event

### 5.3 Profile C — fully disabled (optional safety supplement)

Goal: all gates unset (shipping default), so the system is blocked at the
earliest kill switch.

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED
export EXECUTE_EXPECTED=blocked_by_kill_switch   # informational; smoke spec targets A/B
```

Expected:

- `decision = blocked_by_kill_switch` (or the equivalent first-gate blocked decision)
- `toolHandlerCalled = false`
- `executionCompleted = false`
- `providerSchemaSent = false`
- `providerApiCalled = false`

Profile C is a **safety supplement**. It does **not** replace Profile A. The
committed smoke harness exposes Profile A and Profile B as named modes; Profile
C is documented as an optional manual variant (its decision is not one of the
smoke spec's two named expectations).

---

## 6. Pilot Rehearsal Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Phase 1G-04 sealed baseline confirmed (`94f22f67b`) | ✅ |
| 2 | Phase 1G-05 pushed readiness baseline confirmed (`da5c31a8c`) | ✅ |
| 3 | Local HEAD == remote HEAD, ahead/behind = 0/0 | ✅ |
| 4 | Tracked worktree clean (only `.claude/` untracked) | ✅ |
| 5 | Route governance = 34 / 34 / 5 / 0 / 1 / 1 | ✅ |
| 6 | `STATIC_ALLOWLIST = frozenset({"clarify"})` | ✅ |
| 7 | Gate profiles A / B / C documented | ✅ |
| 8 | Dev-only smoke harness committed (`scripts/run-dev-webui-execute-audit-smoke.sh`) | ✅ |
| 9 | Smoke harness runbook authored | ✅ |
| 10 | Release-candidate validation report authored | ✅ |
| 11 | Go / no-go template authored | ✅ |
| 12 | Backend regression re-run, 0 failed | ✅ |
| 13 | Frontend type-check / lint / unit / build re-run, 0 failed | ✅ |
| 14 | Browser smoke Profile A (blocked) re-run, 0 failed | ✅ |
| 15 | Browser smoke Profile B (completed) re-run, 0 failed | ✅ |
| 16 | `memory-check` PASS | ✅ |
| 17 | `dev-check` PASS | ✅ |
| 18 | Production Gateway PID `69355` unaffected | ✅ |
| 19 | Ports `5180` / `5181` free at rehearsal end | ✅ |
| 20 | No allowlist expansion, no Provider Schema / API, no non-clarify execution | ✅ |
| 21 | No route / code / runtime artifact change | ✅ |
| 22 | Single local commit created, **not pushed** | ✅ |

---

## 7. Release Candidate Validation Checklist

The release-candidate validation report lives at
`docs/webui/phase-1g-06-release-candidate-validation.md`. It records the actual
observed results for:

1. Git baseline.
2. Route governance.
3. Backend regression.
4. Compile / ruff.
5. Frontend type-check.
6. Frontend lint.
7. Frontend unit tests.
8. Frontend build.
9. Browser smoke — blocked profile.
10. Browser smoke — completed profile.
11. `memory-check`.
12. `dev-check`.
13. Production Gateway PID.
14. Final port status.
15. Go / no-go outcome.

---

## 8. Smoke Execution Commands

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

# Profile A — handler-call blocked
./scripts/run-dev-webui-execute-audit-smoke.sh blocked

# Profile B — clarify completed
./scripts/run-dev-webui-execute-audit-smoke.sh completed

# Both (default)
./scripts/run-dev-webui-execute-audit-smoke.sh all
```

The harness binds to `127.0.0.1` only, refuses the production `HERMES_HOME`,
pre-checks ports `5180` / `5181`, starts only the services it needs, kills only
the PIDs it started, traps cleanup on exit, and never affects the Production
Gateway. See `docs/webui/phase-1g-06-smoke-harness-runbook.md` for the full
runbook.

---

## 9. Go / No-Go Decision

The go / no-go template lives at `docs/webui/phase-1g-06-go-no-go-template.md`.

**GO requires:**

- No P0, no P1.
- All required gates pass (backend, frontend, smoke A + B, memory, dev).
- Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
- `STATIC_ALLOWLIST = frozenset({"clarify"})`.
- No Provider Schema / API, no non-clarify execution.
- Production Gateway PID `69355` unchanged.
- Ports `5180` / `5181` free.
- No forbidden file touched, no audit JSONL / `.claude/` committed.

**NO-GO on:** any P0, any P1, backend regression failure, frontend build failure,
smoke failure, route governance change, allowlist change, production PID change,
or any provider-boundary violation.

On a NO-GO: do **not** push; do **not** reopen Phase 1G-04; record the finding
and address it via a separately approved phase.

---

## 10. Known P2 (non-blocking)

See `docs/webui/phase-1g-05-risk-register.md`. Summary (all P2, none blocking):

- Stale dormant `auditWritten=false` assumption (P2-01).
- Offset-based audit pagination (P2-02).
- Multi-file JSONL rotation not implemented (P2-03).
- JSONL race handling not implemented (P2-04).
- Non-clarify tools disabled by design (P2-05).
- Provider integration is a permanent non-goal (P2-06).
- Frontend visual polish optional (P2-07).
- Large-scale audit search / indexing not implemented (P2-08).

---

## 11. Exit Criteria

Phase 1G-06 is complete when **all** hold:

1. The four Phase 1G-06 docs exist (rehearsal, runbook, validation, go/no-go).
2. The Phase 1G-05 docs and the implementation plan reference Phase 1G-06.
3. The dev-only smoke harness is committed (or an equivalent runbook is complete).
4. Gate profiles A / B / C are documented; the common-mistake note is recorded.
5. Route governance and `STATIC_ALLOWLIST` are unchanged.
6. All required gates pass with 0 failures.
7. Production Gateway PID `69355` is unchanged; ports `5180` / `5181` are free.
8. A single local commit is created and **not** pushed.
9. Phase 1G-07 is **not** started.

---

## 12. Next Phase Options

Phase 1G-06 does not start any follow-on phase. Candidate follow-on work (each
must be separately approved):

- **Pilot execution** — run the Pilot acceptance baseline
  (`docs/webui/phase-1g-05-pilot-acceptance-baseline.md`) against the sealed
  mainline, now driven by the committed rehearsal harness.
- **Polish (optional, P2)** — frontend visual polish / accessibility pass.
- **Audit hardening (optional, P2)** — JSONL rotation, cursor pagination, audit
  search / indexing.
- **Phase 1G-07** — explicitly **not started** by this phase. Its scope, if any,
  must be defined and approved separately.

---

## 13. Non-Reopening Declaration

> **Phase 1G-06 does not reopen Phase 1G-04.**
> **Phase 1G-06 does not introduce a new product capability.**
> **Phase 1G-06 hardens release rehearsal and smoke execution only.**

No Phase 1G-04 route, allowlist, execute gate, audit behavior, frontend
capability, or test strength is changed, weakened, or expanded by Phase 1G-06.
The only deliverables are the rehearsal docs, the smoke harness runbook, the
release-candidate validation, the go/no-go template, the optional committed
dev-only smoke script, and a final re-verification pass.

---

*Phase 1G-06 Pilot Release Rehearsal — release rehearsal baseline created.
Phase 1G-04 remains sealed; Phase 1G-05 remains the pushed readiness baseline.*
