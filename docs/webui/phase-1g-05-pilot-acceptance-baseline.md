# Phase 1G-05: Pilot Acceptance Baseline

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-05 |
| Title | Pilot Acceptance Baseline — Dev WebUI Controlled-Execution Pilot |
| Status | Baseline authored (Pilot execution pending explicit approval) |
| Date | 2026-06-13 |
| Branch | `dev-huangruibang` |
| Candidate | Phase 1G-04 sealed mainline at `94f22f67b` |
| Scope | Define Pilot acceptance scenarios, severities, and pass/fail criteria. No code change. |

---

## 1. Purpose

This document defines the **Pilot acceptance baseline** for the Hermes Dev
WebUI controlled-execution capability. It lists the scenarios a Pilot reviewer
must execute against the sealed Phase 1G-04 mainline, the expected results, the
security assertions attached to each scenario, and the severity classification
that determines whether a finding blocks the Pilot.

The Pilot runs **only** against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Dev API bind: `127.0.0.1:5181` (isolated)
- WebUI bind: `127.0.0.1:5180` (isolated)
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID `69355`: **never affected**

---

## 2. Severity Classification

| Severity | Meaning | Pilot action on failure |
|----------|---------|-------------------------|
| **P0 blocker** | A safety boundary is violated (allowlist, Provider, secret leak, production access, raw token exposure). | **Stop the Pilot immediately.** Do not proceed. Report and remediate before any further Pilot step. |
| **P1 release blocker** | A sealed capability does not work, or a required gate fails (regression, route governance, build, smoke). | **Pilot cannot pass.** Report; do not mark the Pilot accepted. |
| **P2 known limitation** | A recorded, non-blocking limitation (audit pagination, dormant stale test assumption, visual polish, non-clarify disabled by design, Provider a permanent non-goal). | **Record against the risk register; do not block.** See `docs/webui/phase-1g-05-risk-register.md`. |

---

## 3. Pilot Scenarios

Each scenario lists: preconditions, steps, expected result, security assertion,
and pass/fail criteria.

### Scenario A — WebUI loads

- **Preconditions:** Dev API and WebUI started by the smoke harness on
  `127.0.0.1:5181` / `127.0.0.1:5180`. Production Gateway running, PID `69355`.
- **Steps:** Open the WebUI at `http://127.0.0.1:5180`.
- **Expected result:** The three-column workbench renders; theme system loads
  (default Obsidian); no console errors about missing API.
- **Security assertion:** WebUI binds only to `127.0.0.1`; production Gateway
  PID unchanged.
- **Pass:** page renders, Dev API health reachable.
- **Fail:** blank page, API health unreachable → P1.
- **Severity (on fail):** P1.

### Scenario B — Tool policy / schema preview available

- **Preconditions:** Dev API up.
- **Steps:** Open the Tools panel; view tool policy and schema preview.
- **Expected result:** Read-only policy / schema preview renders; canonical
  tool inventory and risk tiers display; `clarify` is the only allowlisted tool.
- **Security assertion:** No Provider Schema is sent; no Provider API is called.
- **Pass:** read-only preview renders with `STATIC_ALLOWLIST = {"clarify"}`.
- **Fail:** allowlist shows more than clarify, or schema preview sends a
  Provider Schema → **P0**.
- **Severity (on fail):** P0 (allowlist / Provider), else P1.

### Scenario C — clarify dry-run visible

- **Preconditions:** Dev API up.
- **Steps:** In Tools → Execute, run a dry-run for `clarify`.
- **Expected result:** Dry-run returns a safe decision, risk assessment, short
  digest, and a confirmation-token ID (`confirmationTokenId`). It does **not**
  return the raw confirmation token.
- **Security assertion:** Raw token never appears in the response, DOM, or
  console; only the token ID + short digest are surfaced.
- **Pass:** dry-run decision visible, raw token absent.
- **Fail:** raw token exposed → **P0**; dry-run errors → P1.
- **Severity (on fail):** P0 (token leak), else P1.

### Scenario D — default blocked execution behavior

- **Preconditions:** Dev API started with kill switches and handler-call gate
  **unset** (shipping default).
- **Steps:** Confirm & Execute on the `clarify` dry-run.
- **Expected result:** Execute returns `blocked_tool_handler_call_not_enabled`
  (or `blocked_by_kill_switch` if kill switches are off). No handler call, no
  execution, no post-execution audit.
- **Security assertion:** No handler call occurs; no side effect; only a
  pre-execution audit attempt may be written (no execution audit).
- **Pass:** decision is a blocked decision; no `clarify_execution_completed`.
- **Fail:** execution completes without the explicit gate → **P0**.
- **Severity (on fail):** P0.

### Scenario E — explicit dev/test clarify execution completed

- **Preconditions:** Dev API started with
  `HERMES_TOOL_EXECUTION_ENABLED=true`, `HERMES_AGENT_TOOLS_ENABLED=true`,
  `HERMES_TOOL_HANDLER_CALL_ENABLED=true`. (`EXECUTE_EXPECTED=clarify_execution_completed`.)
- **Steps:** Confirm & Execute on the `clarify` dry-run.
- **Expected result:** Execute returns `clarify_execution_completed`, surfacing
  `handlerCallId` and `postExecutionAuditId`.
- **Security assertion:** Provider / external side-effect flags are all `false`;
  the result is bounded to `clarify`.
- **Pass:** decision `clarify_execution_completed`, false provider flags.
- **Fail:** any provider flag `true`, or a non-clarify tool executes → **P0**;
  decision wrong → P1.
- **Severity (on fail):** P0 (Provider / non-clarify), else P1.

### Scenario F — postExecutionAuditId visible

- **Preconditions:** Scenario E completed.
- **Steps:** Inspect the execute response.
- **Expected result:** `postExecutionAuditId` is present and non-empty, and
  correlates to the written post-execution audit event.
- **Security assertion:** The audit event contains no raw token, no full
  tokenHash, no raw arguments, no secrets (whitelist normalization + redaction).
- **Pass:** `postExecutionAuditId` present and correlates safely.
- **Fail:** audit event leaks raw token / raw args / secret → **P0**; ID missing
  → P1.
- **Severity (on fail):** P0 (leak), else P1.

### Scenario G — audit viewer shows dry-run audit

- **Preconditions:** Scenario C run.
- **Steps:** Open the Audit viewer; select `auditKind=dry_run`.
- **Expected result:** Dry-run audit events render with safe per-event summaries;
  malformed lines are skipped safely; empty state renders when there is no event.
- **Security assertion:** No raw arguments in the viewer; whitelist-normalized
  fields only.
- **Pass:** dry-run events render safely.
- **Fail:** raw arguments visible → **P0**; viewer errors → P1.
- **Severity (on fail):** P0 (raw args), else P1.

### Scenario H — audit viewer shows pre-execution audit

- **Preconditions:** Scenario D or E run.
- **Steps:** Open the Audit viewer; select `auditKind=pre_execution`.
- **Expected result:** Pre-execution audit events render safely with correlation
  IDs.
- **Security assertion:** No raw token, no full tokenHash, no raw arguments,
  no callable / function repr.
- **Pass:** pre-execution events render safely.
- **Fail:** leak of token / tokenHash / args / callable → **P0**; viewer errors
  → P1.
- **Severity (on fail):** P0 (leak), else P1.

### Scenario I — audit viewer shows post-execution audit

- **Preconditions:** Scenario E completed (explicit gate).
- **Steps:** Open the Audit viewer; select `auditKind=post_execution`.
- **Expected result:** Post-execution audit event renders; provider / external
  side-effect flags show `false`.
- **Security assertion:** No raw token, no full tokenHash, no raw arguments;
  provider payload never exposed.
- **Pass:** post-execution event renders safely with `false` flags.
- **Fail:** provider payload exposed or any flag `true` → **P0**; event missing
  → P1.
- **Severity (on fail):** P0 (Provider / leak), else P1.

### Scenario J — provider flags false

- **Preconditions:** Any execute path (D or E).
- **Steps:** Inspect execute response and post-execution audit.
- **Expected result:** `providerSchemaSent=false`, `providerApiCalled=false`,
  and all external side-effect flags are `false`.
- **Security assertion:** No Provider integration is reachable from this path.
- **Pass:** all provider / external flags false.
- **Fail:** any provider flag `true` → **P0**.
- **Severity (on fail):** P0.

### Scenario K — no non-clarify execution

- **Preconditions:** Dev API up; explicit gate enabled.
- **Steps:** Attempt a dry-run / execute against any canonical name other than
  `clarify`.
- **Expected result:** The request is rejected at the allowlist gate
  (`blocked_*` decision). No handler call, no execution.
- **Security assertion:** Only `clarify` is allowlisted; non-clarify tools are
  disabled by design.
- **Pass:** non-clarify blocked.
- **Fail:** a non-clarify tool executes or is allowlisted → **P0**.
- **Severity (on fail):** P0.

### Scenario L — no Provider Schema / Provider API

- **Preconditions:** Full Pilot run.
- **Steps:** Grep execute responses, audit events, audit viewer payloads, and
  logs for Provider Schema / Provider API activity.
- **Expected result:** None. Provider integration is a permanent non-goal for
  this controlled path.
- **Security assertion:** No Provider Schema is sent; no Provider API is called.
- **Pass:** zero Provider activity.
- **Fail:** Provider Schema sent or Provider API called → **P0**.
- **Severity (on fail):** P0.

### Scenario M — route governance stable

- **Preconditions:** Dev API up.
- **Steps:** Run route-governance tests / `dev-check`.
- **Expected result:** OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write 0 /
  dry-run 1 / execution 1; `STATIC_ALLOWLIST = frozenset({"clarify"})`.
- **Security assertion:** No new route, no Tool write route, no second execution
  route, no Provider route.
- **Pass:** governance matches the sealed baseline.
- **Fail:** route count or allowlist differs → **P0** if allowlist / write /
  Provider route; P1 otherwise.
- **Severity (on fail):** P0 / P1.

### Scenario N — production PID unaffected

- **Preconditions:** Full Pilot run complete; servers torn down.
- **Steps:** Check Production Gateway PID, ports `5180` / `5181`, and confirm
  `~/.hermes` / production `state.db` untouched.
- **Expected result:** Production Gateway PID is still `69355`; Dev Gateway
  stopped; ports `5180` / `5181` free; no production access.
- **Security assertion:** Production is fully isolated from the Pilot.
- **Pass:** PID `69355`, ports free, no production access.
- **Fail:** PID changed, production accessed, or port conflict → **P0**.
- **Severity (on fail):** P0.

---

## 4. Pilot Run Matrix

| Scenario | Severity (on fail) | Default-gate run | Explicit-gate run |
|----------|--------------------|------------------|-------------------|
| A — WebUI loads | P1 | ✔ | ✔ |
| B — Policy / schema preview | P0 / P1 | ✔ | ✔ |
| C — clarify dry-run visible | P0 / P1 | ✔ | ✔ |
| D — default blocked execution | P0 | ✔ | — |
| E — explicit clarify completed | P0 / P1 | — | ✔ |
| F — postExecutionAuditId visible | P0 / P1 | — | ✔ |
| G — dry-run audit viewer | P0 / P1 | ✔ | ✔ |
| H — pre-execution audit viewer | P0 / P1 | ✔ | ✔ |
| I — post-execution audit viewer | P0 / P1 | — | ✔ |
| J — provider flags false | P0 | ✔ | ✔ |
| K — no non-clarify execution | P0 | ✔ | ✔ |
| L — no Provider Schema / API | P0 | ✔ | ✔ |
| M — route governance stable | P0 / P1 | ✔ | ✔ |
| N — production PID unaffected | P0 | ✔ | ✔ |

The Pilot is executed in two server-gate configurations, matching the sealed
browser-smoke matrix:

- **Blocked run:** kill switches on, handler-call gate **unset** →
  `blocked_tool_handler_call_not_enabled`.
- **Completed run:** all three gates `=true` (incl. handler-call) →
  `clarify_execution_completed`.

---

## 5. Pilot Pass Criteria

The Pilot is **accepted** only when **all** of the following hold:

1. No P0 blocker in any scenario (A–N).
2. No P1 release blocker in any scenario.
3. Both server-gate configurations (blocked + completed) pass their applicable
   scenarios.
4. Route governance matches the sealed baseline exactly.
5. Production Gateway PID `69355` is unchanged at Pilot end; ports `5180` /
   `5181` free.
6. All P2 findings are recorded against the risk register, not silently ignored.

Any P2 finding observed during the Pilot is appended to
`docs/webui/phase-1g-05-risk-register.md` with a severity, current impact,
reason it is not a blocker, and exit criteria.

---

## 6. Pilot Reporting

At Pilot completion, the reviewer records:

- Scenario-by-scenario pass/fail with the observed decision string.
- The two server-gate configurations used and their results.
- Any P0 / P1 / P2 finding.
- Production Gateway PID before and after.
- A go / no-go statement.

A no-go (any P0 / P1) **does not** reopen Phase 1G-04. It is reported as a
Pilot finding against this baseline and addressed via a separately approved
phase.

---

*Phase 1G-05 Pilot Acceptance Baseline — 14 scenarios (A–N), two gate
configurations, P0/P1/P2 severities. Pilot candidate is the sealed Phase 1G-04
mainline at `94f22f67b`. No code change required to run the Pilot.*
