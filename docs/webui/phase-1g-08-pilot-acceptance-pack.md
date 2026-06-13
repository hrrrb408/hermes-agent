# Phase 1G-08: Pilot Acceptance Pack — `PILOT-1G-08-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Acceptance Pack |
| Status | Prepared (Pilot execution pending explicit approval) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Scope | The complete, ready-to-run Pilot acceptance pack: scenarios, environment, commands, evidence, pass / fail, known limitations. No code change. |

---

## 1. Identification

| Field | Value |
|------|-------|
| Pilot ID | `PILOT-1G-08-001` |
| RC ID | `RC-1G-07-001` |
| Baseline HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Phase 1G-04 sealed | `94f22f67b` |
| Phase 1G-05 pushed | `da5c31a8c` |
| Phase 1G-06 pushed | `311221e0d` |
| Phase 1G-07 pushed (GO) | `6f9176953` |

---

## 2. Scope

The Pilot validates the sealed Phase 1G-04 WebUI mainline (the controlled
clarify-execution + audit path) on the Phase 1G-05 / 1G-06 / 1G-07 baselines.
It executes **only** against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Dev API bind: `127.0.0.1:5181` (isolated)
- WebUI bind: `127.0.0.1:5180` (isolated)
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID `69355`: **never affected**

The Pilot exercises the committed smoke harness
(`scripts/run-dev-webui-execute-audit-smoke.sh`) across the two named gate
profiles (blocked + completed), then walks the scenario list (A–O) capturing
evidence against the acceptance record template.

---

## 3. Out of Scope

- Reopening or expanding Phase 1G-04.
- Any new product capability, route, allowlist entry, Provider integration, or
  non-clarify execution.
- Any access to production `~/.hermes` or production `state.db`.
- Any stop / restart / replace / reconfigure of the Production Gateway.
- Any push to the remote.
- Starting Phase 1G-09.

---

## 4. Required Environment

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

unset HERMES_AGENT_RUN_ENABLED
unset HERMES_TOOL_EXECUTION_ENABLED
unset HERMES_AGENT_TOOLS_ENABLED
unset HERMES_TOOL_HANDLER_CALL_ENABLED
unset HERMES_POST_EXECUTION_AUDIT_ENABLED

unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY
unset GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY
```

- Source root: `/Users/huangruibang/Code/hermes-agent-dev`
- Branch: `dev-huangruibang`
- Node toolchain: whichever `apps/hermes-dev-webui` resolves via `pnpm`.
- Python: the existing `.venv` (never run `setup-hermes.sh`).

---

## 5. Required Safety Boundary

The Pilot must keep all of these invariants true throughout and after the run.
Any violation is a P0 and stops the Pilot:

- `STATIC_ALLOWLIST` is exactly `frozenset({"clarify"})`.
- No non-clarify tool executes or becomes allowlisted.
- `providerSchemaSent=false` and `providerApiCalled=false` everywhere.
- The raw confirmation token never appears in a response, the DOM, a log, the
  console, `localStorage`, `sessionStorage`, or an audit event.
- The full token hash is never surfaced.
- Raw arguments never appear in the audit viewer.
- No secret / API key / credential is logged or committed.
- Production `~/.hermes` and production `state.db` are never accessed.
- No Tool write route, no second execution route, no Provider route appears.
- No audit JSONL or `.claude/` is staged or committed.
- No force push, rebase, or `git reset --hard` is attempted.

---

## 6. Required Commands

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

# Baseline
git status --short --branch
git rev-parse HEAD
git rev-parse origin/dev-huangruibang
git rev-list --left-right --count origin/dev-huangruibang...HEAD

# Gates
./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py -- -q
./scripts/run-dev-webui-execute-audit-smoke.sh all
./scripts/run-dev-hermes.sh memory-check
./scripts/run-dev-hermes.sh dev-check

# Frontend (in apps/hermes-dev-webui)
#   pnpm type-check ; pnpm lint ; pnpm test ; pnpm build

# Production isolation (read-only)
ps aux | grep '[h]ermes_cli.main gateway run'
lsof -nP -iTCP:5180 -sTCP:LISTEN || true
lsof -nP -iTCP:5181 -sTCP:LISTEN || true
```

---

## 7. Required Evidence

Per scenario, capture (into the acceptance record):

- The scenario ID and name.
- The observed decision string (where applicable).
- The server-gate configuration used (blocked / completed).
- `providerSchemaSent` / `providerApiCalled` / `externalSideEffects` values.
- `handlerCallId` / `postExecutionAuditId` presence (completed profile only).
- A short note on the audit viewer state (empty / dry-run / pre-execution /
  post-execution).
- The PASS / FAIL / BLOCKED / SKIPPED status.
- The Production Gateway PID before and after.
- The final `5180` / `5181` port state.
- Any defect ID raised.

No screenshot may contain a secret, an API key, the raw confirmation token, the
full token hash, or raw arguments. When in doubt, capture a text summary rather
than a raw screenshot.

---

## 8. Acceptance Scenarios

> Each scenario below lists: Objective · Preconditions · Steps · Expected result
> · Evidence to capture · Pass criteria · Fail criteria · Severity if failed.
> Two server-gate configurations apply: **Blocked** (upstream execution gates on,
> handler-call gate unset → `blocked_tool_handler_call_not_enabled`) and
> **Completed** (all three gates `=true` → `clarify_execution_completed`). See
> `docs/webui/phase-1g-06-smoke-harness-runbook.md` for the exact env vars.

### Scenario A — WebUI loads

- **Objective:** Confirm the three-column workbench renders on the dev bind.
- **Preconditions:** Dev API on `127.0.0.1:5181`; WebUI on `127.0.0.1:5180`;
  Production Gateway PID `69355`.
- **Steps:** Open `http://127.0.0.1:5180`.
- **Expected result:** Three-column workbench renders; default theme (Obsidian)
  loads; no console error about a missing API.
- **Evidence to capture:** page-load note; Dev API health reachable.
- **Pass criteria:** page renders; Dev API health reachable.
- **Fail criteria:** blank page, API health unreachable.
- **Severity (on fail):** P1.

### Scenario B — Tools panel visible

- **Objective:** Confirm the Tools panel renders the controlled-execution
  surface.
- **Preconditions:** Scenario A passed; Dev API up.
- **Steps:** Open the Tools panel; confirm the dry-run / Execute sub-tab and the
  Audit viewer are reachable.
- **Expected result:** Tools panel renders; Execute + Audit sub-tabs present.
- **Evidence to capture:** panel-render note.
- **Pass criteria:** Tools panel and sub-tabs render.
- **Fail criteria:** panel or sub-tabs missing.
- **Severity (on fail):** P1.

### Scenario C — Tool schema / policy read-only inspection

- **Objective:** Confirm the read-only policy / schema preview renders with the
  correct allowlist and risk tiers.
- **Preconditions:** Scenario B passed.
- **Steps:** View the tool policy / schema preview.
- **Expected result:** Canonical tool inventory and risk tiers display;
  `clarify` is the only allowlisted tool.
- **Evidence to capture:** allowlist shows `{"clarify"}`; no Provider Schema sent.
- **Pass criteria:** read-only preview renders with `STATIC_ALLOWLIST = {"clarify"}`.
- **Fail criteria:** allowlist shows more than `clarify`, or a Provider Schema is
  sent.
- **Severity (on fail):** P0 (allowlist / Provider), else P1.

### Scenario D — clarify dry-run

- **Objective:** Confirm a clarify dry-run returns a safe decision and surfaces
  only the token ID + short digest (never the raw token).
- **Preconditions:** Scenario C passed.
- **Steps:** In Tools → Execute, run a dry-run for `clarify`.
- **Expected result:** Dry-run returns a safe decision, risk assessment, short
  digest, and `confirmationTokenId`. It does **not** return the raw confirmation
  token.
- **Evidence to capture:** decision + `confirmationTokenId`; raw token absent.
- **Pass criteria:** dry-run decision visible; raw token absent.
- **Fail criteria:** raw token exposed → P0; dry-run errors → P1.
- **Severity (on fail):** P0 (token leak), else P1.

### Scenario E — blocked profile (`blocked_tool_handler_call_not_enabled`)

- **Objective:** Confirm the blocked execution decision appears under the blocked
  gate profile.
- **Preconditions:** Blocked gate profile (`HERMES_TOOL_EXECUTION_ENABLED=true`,
  `HERMES_AGENT_TOOLS_ENABLED=true`, handler-call gate unset).
- **Steps:** Confirm & Execute on the clarify dry-run.
- **Expected result:** Execute returns `blocked_tool_handler_call_not_enabled`;
  `toolHandlerCalled=false`; `executionCompleted=false`; no post-execution audit.
- **Evidence to capture:** decision + all provider / external flags `false`.
- **Pass criteria:** decision is a blocked decision; no `clarify_execution_completed`.
- **Fail criteria:** execution completes without the explicit gate → P0.
- **Severity (on fail):** P0.

### Scenario F — completed profile (`clarify_execution_completed`)

- **Objective:** Confirm the bounded clarify handler runs under the explicit
  gate profile and writes a post-execution audit.
- **Preconditions:** Completed gate profile (all three gates `=true`).
- **Steps:** Confirm & Execute on the clarify dry-run.
- **Expected result:** Execute returns `clarify_execution_completed`,
  `canonicalName=clarify`, `handlerCallId` (`thc_…`), `postExecutionAuditId`
  (`pexa_…`); all provider / external flags `false`.
- **Evidence to capture:** decision + IDs; all provider / external flags `false`.
- **Pass criteria:** decision `clarify_execution_completed`; false provider flags.
- **Fail criteria:** any provider flag `true` or a non-clarify tool executes →
  P0; decision wrong → P1.
- **Severity (on fail):** P0 (Provider / non-clarify), else P1.

### Scenario G — audit viewer: dry-run event

- **Objective:** Confirm the audit viewer renders dry-run events safely.
- **Preconditions:** Scenario D run.
- **Steps:** Open the Audit viewer; select `auditKind=dry_run`.
- **Expected result:** Dry-run audit events render with safe per-event summaries;
  malformed lines are skipped safely; empty state renders when there is no event.
- **Evidence to capture:** viewer-render note; no raw arguments.
- **Pass criteria:** dry-run events render safely.
- **Fail criteria:** raw arguments visible → P0; viewer errors → P1.
- **Severity (on fail):** P0 (raw args), else P1.

### Scenario H — audit viewer: pre-execution event

- **Objective:** Confirm the audit viewer renders pre-execution events safely.
- **Preconditions:** Scenario E or F run.
- **Steps:** Open the Audit viewer; select `auditKind=pre_execution`.
- **Expected result:** Pre-execution audit events render safely with correlation
  IDs.
- **Evidence to capture:** viewer-render note; no token / tokenHash / raw args /
  callable.
- **Pass criteria:** pre-execution events render safely.
- **Fail criteria:** leak of token / tokenHash / args / callable → P0; viewer
  errors → P1.
- **Severity (on fail):** P0 (leak), else P1.

### Scenario I — audit viewer: post-execution event

- **Objective:** Confirm the audit viewer renders the post-execution event with
  `false` provider / external flags.
- **Preconditions:** Scenario F completed.
- **Steps:** Open the Audit viewer; select `auditKind=post_execution`.
- **Expected result:** Post-execution audit event renders; provider / external
  side-effect flags show `false`; no raw token, full tokenHash, raw arguments, or
  provider payload.
- **Evidence to capture:** viewer-render note; all provider / external flags
  `false`.
- **Pass criteria:** post-execution event renders safely with `false` flags.
- **Fail criteria:** provider payload exposed or any flag `true` → P0; event
  missing → P1.
- **Severity (on fail):** P0 (Provider / leak), else P1.

### Scenario J — `providerSchemaSent=false`

- **Objective:** Confirm no Provider Schema is sent on any execute path.
- **Preconditions:** Any execute path (E or F).
- **Steps:** Inspect execute response and post-execution audit.
- **Expected result:** `providerSchemaSent=false` everywhere.
- **Evidence to capture:** the flag value from the response and the audit.
- **Pass criteria:** `providerSchemaSent=false` on every path.
- **Fail criteria:** `providerSchemaSent=true` → P0.
- **Severity (on fail):** P0.

### Scenario K — `providerApiCalled=false`

- **Objective:** Confirm no Provider API is called on any execute path.
- **Preconditions:** Any execute path (E or F).
- **Steps:** Inspect execute response and post-execution audit.
- **Expected result:** `providerApiCalled=false` everywhere.
- **Evidence to capture:** the flag value from the response and the audit.
- **Pass criteria:** `providerApiCalled=false` on every path.
- **Fail criteria:** `providerApiCalled=true` → P0.
- **Severity (on fail):** P0.

### Scenario L — no non-clarify execution

- **Objective:** Confirm only `clarify` is allowlisted and non-clarify tools are
  rejected.
- **Preconditions:** Dev API up; explicit gate enabled.
- **Steps:** Attempt a dry-run / execute against any canonical name other than
  `clarify`.
- **Expected result:** The request is rejected at the allowlist gate
  (`blocked_*` decision). No handler call, no execution.
- **Evidence to capture:** the rejected decision string.
- **Pass criteria:** non-clarify blocked.
- **Fail criteria:** a non-clarify tool executes or is allowlisted → P0.
- **Severity (on fail):** P0.

### Scenario M — route governance unchanged

- **Objective:** Confirm route governance matches the sealed baseline.
- **Preconditions:** Dev API up.
- **Steps:** Run the route-governance tests and `dev-check`.
- **Expected result:** OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write 0 /
  dry-run 1 / execution 1; `STATIC_ALLOWLIST = frozenset({"clarify"})`.
- **Evidence to capture:** the test / dev-check summary line.
- **Pass criteria:** governance matches the sealed baseline.
- **Fail criteria:** route count or allowlist differs → P0 if allowlist / write /
  Provider route; P1 otherwise.
- **Severity (on fail):** P0 / P1.

### Scenario N — Production Gateway PID unaffected

- **Objective:** Confirm the Production Gateway PID is unchanged at Pilot end.
- **Preconditions:** Full Pilot run complete; servers torn down.
- **Steps:** Check the Production Gateway PID (read-only `ps`) and ports.
- **Expected result:** Production Gateway PID is still `69355`; Dev Gateway
  stopped; ports `5180` / `5181` free; no production access.
- **Evidence to capture:** PID before / after; port state.
- **Pass criteria:** PID `69355`, ports free, no production access.
- **Fail criteria:** PID changed, production accessed, or port conflict → P0.
- **Severity (on fail):** P0.

### Scenario O — final ports free

- **Objective:** Confirm the dev ports are released after the Pilot.
- **Preconditions:** Servers torn down.
- **Steps:** `lsof -nP -iTCP:5180 -sTCP:LISTEN`; `lsof -nP -iTCP:5181 -sTCP:LISTEN`.
- **Expected result:** Both ports free.
- **Evidence to capture:** the (empty) `lsof` output for each port.
- **Pass criteria:** `5180` and `5181` free.
- **Fail criteria:** a port still held → P1 (or P0 if held by a process the
  Pilot cannot account for).
- **Severity (on fail):** P1 / P0.

### Scenario run matrix

| Scenario | Severity (on fail) | Blocked run | Completed run |
|----------|--------------------|-------------|----------------|
| A — WebUI loads | P1 | ✔ | ✔ |
| B — Tools panel visible | P1 | ✔ | ✔ |
| C — Policy / schema read-only | P0 / P1 | ✔ | ✔ |
| D — clarify dry-run | P0 / P1 | ✔ | ✔ |
| E — blocked profile | P0 | ✔ | — |
| F — completed profile | P0 / P1 | — | ✔ |
| G — dry-run audit viewer | P0 / P1 | ✔ | ✔ |
| H — pre-execution audit viewer | P0 / P1 | ✔ | ✔ |
| I — post-execution audit viewer | P0 / P1 | — | ✔ |
| J — `providerSchemaSent=false` | P0 | ✔ | ✔ |
| K — `providerApiCalled=false` | P0 | ✔ | ✔ |
| L — no non-clarify execution | P0 | ✔ | ✔ |
| M — route governance | P0 / P1 | ✔ | ✔ |
| N — production PID unaffected | P0 | ✔ | ✔ |
| O — final ports free | P1 / P0 | ✔ | ✔ |

---

## 9. Required Screenshots / Log Summaries

Per scenario, capture a **text summary** of:

- the decision string (E / F / L);
- the provider / external flags (E / F / I / J / K);
- the audit-viewer state (G / H / I);
- the route-governance / dev-check summary line (M);
- the PID + port snapshot (N / O).

Screenshots are optional and must never contain a secret, an API key, the raw
token, the full token hash, or raw arguments. Prefer text summaries.

---

## 10. Pass / Fail Criteria

The Pilot is **accepted (PASS)** only when **all** hold:

1. No P0 in any scenario (A–O).
2. No unresolved P1 in any scenario.
3. Both server-gate configurations (blocked + completed) pass their applicable
   scenarios.
4. Route governance matches the sealed baseline exactly (34 / 34 / 5 / 0 / 1 / 1).
5. `STATIC_ALLOWLIST = frozenset({"clarify"})`.
6. Production Gateway PID `69355` unchanged at Pilot end; `5180` / `5181` free.
7. No Provider Schema / API; no non-clarify execution; no Tool write route.
8. No `~/.hermes` / production `state.db` access; no secret / token / tokenHash /
   raw-arguments exposure.
9. All P2 findings recorded against the risk register, not silently ignored.
10. Evidence complete for every scenario; acceptance record signed off.

Any P0 or unresolved P1 → **NO-GO** (does not reopen Phase 1G-04).

---

## 11. Known P2 Limitations (carry-in)

See `docs/webui/phase-1g-05-risk-register.md` (8 P2 items, all non-blocking):

- P2-01 — stale dormant `auditWritten=false` assumption.
- P2-02 — offset-based audit pagination.
- P2-03 — multi-file JSONL rotation not implemented.
- P2-04 — JSONL race handling not implemented.
- P2-05 — non-clarify tools disabled by design.
- P2-06 — Provider integration is a permanent non-goal.
- P2-07 — frontend visual polish optional.
- P2-08 — large-scale audit search / indexing not implemented.

Any new P2 observed during the Pilot is appended to the risk register.

---

## 12. Go / No-Go Relation

The Pilot PASS outcome is the **final gate** between `RC-1G-07-001` (GO at the
release-candidate level) and a Pilot-accepted mainline. A Pilot NO-GO does **not**
revoke the RC GO by itself; it records a Pilot finding that must be addressed
before the mainline can be Pilot-accepted. The Pilot record and its defect
records together are the evidence an approver uses to sign the Pilot.

---

## 13. Pilot Completion Checklist

- [ ] Pilot ID `PILOT-1G-08-001` recorded on the acceptance record.
- [ ] Git baseline confirmed (branch, HEAD, ahead/behind, clean worktree).
- [ ] Route governance confirmed (34 / 34 / 5 / 0 / 1 / 1).
- [ ] `STATIC_ALLOWLIST = frozenset({"clarify"})` confirmed.
- [ ] Blocked profile (E) run; decision recorded.
- [ ] Completed profile (F) run; decision + IDs recorded.
- [ ] Audit viewer states recorded (G / H / I).
- [ ] Provider / external flags all `false` (J / K).
- [ ] Non-clarify rejected (L).
- [ ] Route governance re-checked (M).
- [ ] Production Gateway PID `69355` before / after recorded (N).
- [ ] Final ports `5180` / `5181` free (O).
- [ ] All evidence captured; no secret / token / tokenHash / raw-args exposure.
- [ ] Defect / feedback records created for any finding.
- [ ] Acceptance record signed off (PASS / NO-GO / PAUSED).

---

## 14. Cross-References

- Pilot preparation: `docs/webui/phase-1g-08-pilot-acceptance-preparation.md`.
- Operator guide: `docs/webui/phase-1g-08-pilot-operator-guide.md`.
- Participant guide: `docs/webui/phase-1g-08-pilot-participant-guide.md`.
- Acceptance record template:
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Smoke harness runbook: `docs/webui/phase-1g-06-smoke-harness-runbook.md`.
- Pilot acceptance baseline (scenarios / severities):
  `docs/webui/phase-1g-05-pilot-acceptance-baseline.md`.
- RC validation: `docs/webui/phase-1g-07-rc-validation-report.md`.
- RC Go / No-Go: `docs/webui/phase-1g-07-go-no-go-decision.md`.

---

*Phase 1G-08 Pilot Acceptance Pack — `PILOT-1G-08-001` against RC `RC-1G-07-001`
(GO). 15 scenarios (A–O), two gate profiles, explicit evidence and pass / fail.
Production Gateway PID `69355` is never affected.*
