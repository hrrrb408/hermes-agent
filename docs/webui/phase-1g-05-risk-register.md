# Phase 1G-05: Risk Register

> **Phase 2A Update:** The five Phase 2A planning risks (R2A-01..R2A-05) are
> mitigated by the Phase 2A implementation. R2A-01/R2A-02: every added tool was
> per-tool audited + individually authorized + read-only proven (bounded
> Dev-WebUI-local handlers, ambiguity → exclusion). R2A-03:
> `providerSchemaSent` / `providerApiCalled` remain False (Provider is Phase 2B).
> R2A-04: Tool write routes remain 0 (write is Phase 2C). R2A-05: the per-request
> audit parse cap is retained as a backstop (Phase 2D delivers scale hardening).
> See [phase-2a-security-boundary.md](phase-2a-security-boundary.md).

> **Phase 3 Planning Update:** Phase 2 is functionally complete (2A–2E + all
> -H1 hardening passes, HEAD `bb373d61e`); all carried-forward P2 items here
> remain non-blocking and map onto future Phase 3 slices (real provider → 3B;
> audit retention / encryption / advanced indexing → 3E; token encryption at
> rest / multi-user namespace → future). Phase 3 planning is recorded under
> `PHASE-3-PLANNING-001` with its own register at
> [phase-3-risk-register.md](phase-3-risk-register.md) (P0/P1/P2) and the
> recommended Phase 3A = Dev-only Agent Workflow MVP. Phase 3A is not started;
> route governance (34/34/5/0/1/1) and Production Gateway PID `28428` are
> unchanged. This register remains the historical Phase 1G-05 baseline.

> **Phase 3B Implementation Update:** Phase 3B (Real Provider Read-only
> Controlled Integration) is now **implemented** — see
> [phase-3b-security-boundary.md](phase-3b-security-boundary.md) and
> [phase-3b-test-report.md](phase-3b-test-report.md). The real-provider
> boundary is disabled by default; no real network call is exercised in tests
> or smoke; the API key is env-only (never persisted/logged/rendered); provider
> write / auto-write / autonomous execution / rollback / shell / db /
> external-write / streaming / multi-provider routing / production rollout all
> remain blocked. Route governance (34/34/5/0/1/1) and Production Gateway PID
> `28428` are unchanged.

> **Phase 3B-Live-Enablement Planning Update (2026-06-17):** A docs-only
> planning pass (`PHASE-3B-LIVE-ENABLEMENT-PLANNING-001`) froze the minimal
> safe closed-loop for a future, separately-authorized Strict Manual Real
> Provider Read-only Enablement (human approval, env-only secret read, empty-
> default HTTPS network allowlist, strict budget / rate-limit caps, read-only
> tool allowlist, redacted dual-write audit, kill switch / rollback, layered
> smoke). Live enablement is **not** started; no real HTTP client wiring, no
> real API key read, no external network call, no provider write / auto-write /
> autonomous write, no production rollout. Live-layer risks (LIV-P0..P2) live
> in [phase-3b-live-enablement-risk-register.md](phase-3b-live-enablement-risk-register.md);
> nothing here is relaxed. Route governance (34/34/5/0/1/1) and Production
> Gateway PID `28428` are unchanged.

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-05 |
| Title | Risk Register — Post-Sealing P2 Inventory |
| Status | Authored |
| Date | 2026-06-13 |
| Branch | `dev-huangruibang` |
| Scope | Record P2 (non-blocking) risks remaining after Phase 1G-04 sealing. No code change. |

---

## 1. Summary

> **Update (2026-06-14, Phase 2B):** the Provider integration deferral
> tracked here is resolved. Phase 2B delivered a controlled Provider
> Schema / API round-trip (deterministic fake provider; real provider
> blocked by default). See
> [phase-2b-provider-schema-api-integration.md](phase-2b-provider-schema-api-integration.md).
> The risk register below remains the historical Phase 1G-05 baseline.

| Severity | Count | Blocks Phase 1G-04 sealed acceptance? |
|----------|-------|---------------------------------------|
| **P0** | 0 | n/a |
| **P1** | 0 | n/a |
| **P2** | 9 (P2-01 … P2-08 technical; P2-09 release authorization dependency) | **No** (P2-09 gates release authorization only, not technical acceptance) |

> **No P0. No P1.** The remaining P2 items do **not** block the Phase 1G-04
> sealed acceptance, the Phase 1G-05 post-sealing readiness, or the Pilot
> acceptance baseline. P2-01 … P2-08 are technical, non-blocking items recorded
> for transparency and future-phase planning. P2-09 (added at Phase 1G-10) is a
> **release authorization dependency** — it gates release only because the
> human approver sign-off is the approver's authority; it is **not** a technical
> Pilot failure.

---

## 2. P0 Risks

*(none)*

No allowlist change, no non-clarify execution, no Provider Schema / API, no raw
secret / token / tokenHash / arguments exposure, no production access, and no
route expansion were introduced. The sealed boundaries hold.

---

## 3. P1 Risks

*(none)*

Backend regression, frontend typecheck / lint / unit / build, route governance,
`compileall`, `toolsets.py` compile, `ruff`, `memory-check`, `dev-check`, and
browser smoke (both gate configurations) all pass on the sealed baseline.

---

## 4. P2 Risks

Each P2 risk below follows the format: Risk ID · Severity · Description ·
Current impact · Reason not a blocker · Owner / future phase · Suggested action
· Exit criteria.

### P2-01 — Stale `auditWritten=false` assumption in a dormant smoke spec

- **Risk ID:** P2-01
- **Severity:** P2
- **Description:** The dormant
  `apps/hermes-dev-webui/tests/smoke/phase-1g-04-dry-run-api-safety-smoke.spec.ts`
  carries a stale assumption that `auditWritten=false`. Since Phase 1G-04-06
  dry-run audit storage, `auditWritten` reflects dry-run audit-event persistence
  (true under a configured `HERMES_HOME`), not an execution side effect.
- **Current impact:** None at runtime. The spec is **not** wired into any active
  smoke runner, so it does not affect any gate.
- **Reason not a blocker:** It is a historical stale test assumption in a dormant
  file. It was intentionally left unmodified during the conservative sealing
  phase to avoid touching a security-flag assertion.
- **Owner / future phase:** Test hygiene / future local-dev phase (optional).
- **Suggested action:** When a dedicated test-hygiene phase is approved, update
  the stale assertion (or retire the dormant spec) with an explicit test-strength
  note. Do not weaken any active security assertion.
- **Exit criteria:** The dormant spec either reflects the current `auditWritten`
  semantics or is removed; no active smoke gate is affected.

### P2-02 — Offset-based audit pagination

- **Risk ID:** P2-02
- **Severity:** P2
- **Description:** The read-only audit events API uses offset-based pagination.
- **Current impact:** For local-dev audit volumes this is adequate. Offset
  pagination degrades at very large offsets.
- **Reason not a blocker:** Local-dev audit volume is small; the current
  pagination is correct and bounded.
- **Owner / future phase:** Audit hardening (future local-dev work).
- **Suggested action:** If audit volume grows, introduce cursor-based pagination
  keyed on the audit `eventId` / timestamp. Keep the read-only, redacted,
  whitelist-normalized contract.
- **Exit criteria:** Cursor-based pagination available; offset path either
  retained for compatibility or removed with a deprecation note.

### P2-03 — Multi-file JSONL rotation not implemented

- **Risk ID:** P2-03
- **Severity:** P2
- **Description:** Audit JSONL files are single-file append logs; there is no
  rotation across multiple files.
- **Current impact:** None for local-dev. A single growing file is acceptable at
  current volume.
- **Reason not a blocker:** Volume is local-dev-only and bounded; the safe reader
  caps total lines parsed per request at 1000.
- **Owner / future phase:** Audit hardening (future local-dev work).
- **Suggested action:** Add size/age-based rotation when needed; update the safe
  reader to traverse rotated files in order. Preserve production-path rejection.
- **Exit criteria:** Rotation policy documented and implemented; reader handles
  rotated files; no production path reachable.

### P2-04 — JSONL race handling not implemented

- **Risk ID:** P2-04
- **Severity:** P2
- **Description:** Concurrent append + read on the audit JSONL files is not
  formally synchronized; the reader is tolerant (skips malformed lines) but does
  not guarantee a consistent snapshot.
- **Current impact:** Minimal. The local-dev execute path is low-concurrency
  (single-generation per session), and malformed-line skip keeps reads safe.
- **Reason not a blocker:** Concurrency is low; the reader is fail-safe (never
  exposes partial/unsafe records).
- **Owner / future phase:** Audit hardening (future local-dev work).
- **Suggested action:** If concurrency grows, add atomic append + a snapshot
  mechanism (e.g., copy-then-read, or a lock-free ring buffer). Keep the
  whitelist-normalized, redacted output.
- **Exit criteria:** Documented concurrency contract; consistent snapshot reads
  under the documented concurrency level.

### P2-05 — Non-clarify tools disabled by design

- **Risk ID:** P2-05
- **Severity:** P2 (by-design)
- **Description:** Only `clarify` is in `STATIC_ALLOWLIST`. All other tools are
  ineligible for execution regardless of gates.
- **Current impact:** This is the intended safety posture, not a defect.
- **Reason not a blocker:** It is the core safety boundary. Expanding the
  allowlist is explicitly forbidden without a separately approved, audited phase.
- **Owner / future phase:** Any future allowlist expansion requires a full
  per-tool audit (registered name, input/output schema, side effects) before
  addition to a safe toolset — out of scope for Phase 1G-05.
- **Suggested action:** Do not expand. Document any future candidate tool's audit
  trail before consideration.
- **Exit criteria:** N/A — `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.

### P2-06 — Provider integration is a permanent non-goal

- **Risk ID:** P2-06
- **Severity:** P2 (by-design)
- **Description:** No Provider Schema is sent and no Provider API is called on
  the controlled-execution path. `providerSchemaSent=false` and
  `providerApiCalled=false` everywhere.
- **Current impact:** None. This is the intended posture.
- **Reason not a blocker:** Provider integration is a **permanent non-goal** for
  this controlled path. It is excluded by design, not deferred.
- **Owner / future phase:** None. Any Provider work would be a separate,
  separately-governed capability — not part of the Dev WebUI controlled-execution
  scope.
- **Suggested action:** Maintain the invariant. Reject any change that would
  send a Provider Schema or call a Provider API.
- **Exit criteria:** N/A — Provider integration remains a permanent non-goal.

### P2-07 — Frontend visual polish optional

- **Risk ID:** P2-07
- **Severity:** P2
- **Description:** The Dev WebUI is functionally complete; visual polish
  (refinements, micro-interactions, accessibility edge cases) is optional.
- **Current impact:** None functional. The five-theme system renders correctly
  across the shared component tree.
- **Reason not a blocker:** Polish is non-functional and does not affect any
  safety boundary or capability.
- **Owner / future phase:** Polish phase (optional, future).
- **Suggested action:** Address polish in a dedicated, separately approved phase
  if desired. Do not bundle polish into safety-boundary phases.
- **Exit criteria:** A polish phase checklist passes; no functional regression.

### P2-08 — Large-scale audit search / indexing not implemented

- **Risk ID:** P2-08
- **Severity:** P2
- **Description:** The audit read API caps total lines parsed per request at
  1000; there is no full-text search or index over audit history.
- **Current impact:** None for local-dev. The cap keeps reads bounded and safe.
- **Reason not a blocker:** Local-dev audit volume is small and bounded; the cap
  is a deliberate safety property.
- **Owner / future phase:** Audit hardening (future local-dev work).
- **Suggested action:** If large-scale audit search is needed, add an indexed
  store (read-only, redacted, whitelist-normalized). Keep the per-request parse
  cap as a backstop.
- **Exit criteria:** Indexed read-only audit search available; production paths
  rejected; raw token / args / secrets never indexed.

### P2-09 — Human approver sign-off pending (release authorization dependency)

- **Risk ID:** P2-09
- **Severity:** P2 (release authorization dependency)
- **Description:** The Phase 1G-09 Pilot acceptance execution
  (`PILOT-EXEC-1G-09-001`) passed at the technical level (0 P0, 0 P1, 15 / 15
  scenarios A–O). A real Pilot-accepted PASS — and any release authorization —
  requires a designated human approver's sign-off. As of the Phase 1G-10
  closeout, that human approver sign-off is **pending**.
- **Current impact:** The technical Pilot PASS stands as a **recommendation
  only**. Release authorization is **not granted** until the human approver
  signs off. No push, production rollout, or Phase 1G-11 start is permitted
  without it.
- **Reason not a blocker:** This is a **release authorization dependency, not a
  technical Pilot failure.** It gates release only because it is the human
  approver's authority; every technical GO prerequisite is met.
- **Owner / future phase:** the designated human approver (outside the Dev
  Agent's authority). Completion mechanism:
  `docs/webui/phase-1g-10-human-approver-signoff-template.md`.
- **Suggested action:** The human approver reviews the Phase 1G-10 final release
  decision preparation package and completes the sign-off template with a real
  GO / NO-GO / PAUSED decision. The Dev Agent does not fabricate or self-grant
  this sign-off.
- **Exit criteria:** The human approver sign-off template is completed by the
  designated approver with a recorded decision; release authorization status is
  updated accordingly.

---

## 5. Risk Acceptance

P2-01 … P2-08 are **accepted as known technical limitations**. They are
recorded here so they are visible to the Pilot reviewer and to any future phase.
None of P2-01 … P2-08:

- expands `STATIC_ALLOWLIST` beyond `frozenset({"clarify"})`,
- sends a Provider Schema or calls a Provider API,
- enables non-clarify execution,
- exposes the raw token / full tokenHash / raw arguments / secrets,
- touches production `~/.hermes` or production `state.db`,
- adds a Tool write route, a second execution route, or a Provider route.

Any new finding discovered during the Pilot is appended to this register with a
Risk ID, severity, current impact, reason it is (or is not) a blocker, owner,
suggested action, and exit criteria.

---

## 6. Cross-References

- Sealed baseline & boundaries:
  `docs/webui/phase-1g-04-final-acceptance-report.md`,
  `docs/webui/phase-1g-04-31-final-webui-sealing.md`.
- Pilot scenarios that exercise these risks:
  `docs/webui/phase-1g-05-pilot-acceptance-baseline.md`.
- Release checklist:
  `docs/webui/phase-1g-05-release-checklist.md`.
- Ops / rollback / troubleshooting:
  `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`.

---

## 7. Phase 1G-06 Addendum — Rehearsal Re-Verification

Phase 1G-06 (Pilot Release Rehearsal / Smoke Harness Hardening) re-verified the
sealed mainline through the full release gate sequence via the committed
rehearsal harness. The risk picture is unchanged.

- **No new P0. No new P1.** The rehearsal produced 0 P0 and 0 P1 findings.
- Phase 1G-04 remains **SEALED**; Phase 1G-05 remains the **pushed** baseline;
  no route, allowlist, or product capability changed.
- The eight P2 items above remain accepted, non-blocking, and carry forward.
  None was aggravated by the rehearsal harness or the gate-profile fix.
- The `blocked_tool_handler_call_not_enabled` vs `blocked_by_kill_switch`
  distinction recorded in Phase 1G-06 is a **documentation / smoke-profile
  correction**, not a code defect — the blocked-default behavior is unchanged
  and still correct.
- Rehearsal validation results: `docs/webui/phase-1g-06-release-candidate-validation.md`.

---

## 8. Phase 1G-07 Addendum — Release Candidate Dry Run Re-Verification

Phase 1G-07 (Release Candidate Dry Run, RC `RC-1G-07-001`) re-verified the
current `dev-huangruibang` branch through the full release gate sequence via the
committed rehearsal harness. The risk picture is unchanged.

- **No new P0. No new P1.** The RC dry run produced 0 P0 and 0 P1 findings.
- Phase 1G-04 remains **SEALED**; Phase 1G-05 remains the **pushed** readiness
  baseline; Phase 1G-06 remains the **pushed** release rehearsal baseline; no
  route, allowlist, or product capability changed.
- The eight P2 items above remain accepted, non-blocking, and carry forward.
  None was aggravated by the RC dry run.
- Observed gate results: backend route governance 124 passed / 0 failed; related
  backend regression 19 files 1471 passed / 0 failed; compile / `py_compile
  toolsets.py` / ruff clean; frontend type-check / lint 0-0 / 674 unit /
  1862-module build pass; smoke A 6 passed / 1 skipped / 0 failed; smoke B 7
  passed / 0 failed; memory-check PASS; dev-check WARN only for `.claude/`;
  Production Gateway PID `69355` unchanged; ports `5180` / `5181` free.
- RC dry-run validation results: `docs/webui/phase-1g-07-rc-validation-report.md`.
- RC Go / No-Go decision: `docs/webui/phase-1g-07-go-no-go-decision.md`
  (**Decision: GO**). Current `dev-huangruibang` is eligible to enter Pilot
  acceptance.

---

---

## 9. Phase 1G-08 Addendum — Pilot Acceptance Preparation Re-Verification

Phase 1G-08 (Pilot Acceptance Preparation, Pilot `PILOT-1G-08-001`) re-verified
the current `dev-huangruibang` branch (HEAD `6f9176953…`, the pushed Phase 1G-07
GO RC) through the full release gate sequence. The risk picture is unchanged.

- **No new P0. No new P1.** Phase 1G-08 produced 0 P0 and 0 P1 findings.
- Phase 1G-04 remains **SEALED**; Phase 1G-05 remains the **pushed** readiness
  baseline; Phase 1G-06 remains the **pushed** release rehearsal baseline;
  Phase 1G-07 remains the **pushed** GO RC dry run; no route, allowlist, or
  product capability changed.
- The eight P2 items above remain accepted, non-blocking, and carry forward.
  None was aggravated by Phase 1G-08 (docs-only; no code touched).
- Observed Phase 1G-08 gate results: route governance 124 passed / 0 failed;
  related backend regression 19 files 1471 passed / 0 failed; compile /
  `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / unit /
  build pass; smoke A 6 passed / 1 skipped / 0 failed; smoke B 7 passed / 0
  failed; memory-check PASS; dev-check WARN only for `.claude/`; Production
  Gateway PID `69355` unchanged; ports `5180` / `5181` free.
- Any new P2 observed during Pilot execution is appended to this register per
  the Phase 1G-08 defect / feedback template and the exit criteria.

---

## 10. Phase 1G-09 Addendum — Pilot Acceptance Execution Re-Verification

Phase 1G-09 (Pilot Acceptance Execution, Pilot `PILOT-1G-08-001` / execution
`PILOT-EXEC-1G-09-001`) executed the prepared Pilot acceptance pack against the
current `dev-huangruibang` branch (HEAD `9812c069e…`, the pushed Phase 1G-08
Pilot acceptance preparation) through the full release gate sequence and the
committed smoke harness. The risk picture is unchanged.

- **No new P0. No new P1. No new P2.** The Pilot execution produced 0 P0, 0 P1,
  and 0 new P2 findings. All 15 required scenarios (A–O) passed under the two
  named gate profiles.
- Phase 1G-04 remains **SEALED**; Phase 1G-05 remains the **pushed** readiness
  baseline; Phase 1G-06 remains the **pushed** release rehearsal baseline;
  Phase 1G-07 remains the **pushed** GO RC dry run; Phase 1G-08 remains the
  **pushed** Pilot acceptance preparation; no route, allowlist, or product
  capability changed.
- The eight P2 items above remain accepted, non-blocking, and carry forward.
  None was aggravated by Phase 1G-09 (docs + gate re-verification only; no code
  touched).
- Observed Phase 1G-09 gate results: route governance 124 passed / 0 failed;
  related backend regression 19 files 1471 passed / 0 failed; compile /
  `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / 674
  unit (31 files) / build 1862 modules pass; smoke A 6 passed / 1 skipped / 0
  failed; smoke B 7 passed / 0 failed; memory-check PASS; dev-check WARN only
  for `.claude/`; Production Gateway PID `69355` unchanged; ports `5180` /
  `5181` free.
- Pilot final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`
  (**Decision: PASS**; all technical PASS criteria met; human approver sign-off
  pending). Current `dev-huangruibang` is eligible for post-Pilot closeout /
  final release decision preparation.

---

## 11. Phase 1G-10 Addendum — Post-Pilot Closeout Re-Verification

Phase 1G-10 (Post-Pilot Closeout / Final Release Decision Preparation, Closeout
`CLOSEOUT-1G-10-001`, preparation `RELEASE-DECISION-PREP-1G-10-001`) consolidated
the Phase 1G-09 Pilot PASS into a post-Pilot closeout package and prepared the
final release decision materials against the current `dev-huangruibang` branch
(HEAD `cd7298416…`, the pushed Phase 1G-09 Pilot acceptance execution PASS
record). The risk picture is unchanged at the technical level; one new,
non-technical P2 is recorded.

- **No new P0. No new P1.** Phase 1G-10 produced 0 P0 and 0 P1 findings (it is
  docs-only; no code was touched).
- **No new technical P2.** P2-01 … P2-08 remain accepted, non-blocking, and
  carry forward. None was aggravated by Phase 1G-10.
- **P2-09 added** (this addendum / §4): the Phase 1G-09 Pilot PASS is a
  technical recommendation only; release authorization requires the designated
  human approver's sign-off, which is **pending**. P2-09 is a **release
  authorization dependency, not a technical Pilot failure.**
- **Release authorization not granted.** Phase 1G-10 prepared final release
  decision materials; it did not authorize a release, a push, a production
  rollout, or Phase 1G-11.
- **No production impact.** Exactly one Production Gateway is running with the
  identical command; this phase did not stop / restart / replace / reconfigure
  it. The sealed-baseline PID `69355` (referenced through Phase 1G-09) no longer
  exists at Phase 1G-10 closeout — the host rebooted (`2026-06-14 04:02:09`) and
  `launchd` respawned the gateway as PID `1962` (PPID=1). This is environmental
  host-reboot drift, not a phase action. No `~/.hermes` access; no production
  `state.db` access; ports `5180` / `5181` free.
- **No route governance impact.** Route governance remains OpenAPI 34 / runtime
  34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1.
- **No allowlist impact.** `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- **No provider impact.** No Provider Schema sent; no Provider API called.
- Observed Phase 1G-10 gate results: route governance 124 passed / 0 failed;
  related backend regression 19 files 1471 passed / 0 failed; compile /
  `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / 674
  unit (31 files) / build pass; smoke A 6 passed / 1 skipped / 0 failed; smoke B
  7 passed / 0 failed; memory-check PASS; dev-check WARN only for `.claude/`;
  ports `5180` / `5181` free.
- Closeout package: `docs/webui/phase-1g-10-post-pilot-closeout.md`,
  `docs/webui/phase-1g-10-final-release-decision-preparation.md`,
  `docs/webui/phase-1g-10-human-approver-signoff-template.md`,
  `docs/webui/phase-1g-10-release-readiness-summary.md`,
  `docs/webui/phase-1g-10-pilot-closeout-report.md`,
  `docs/webui/phase-1g-10-final-go-no-go-draft.md`. Recommended draft decision:
  **GO, pending human approver sign-off**.

---

## 12. Phase 1G-10A Addendum — Smoke Harness PID Baseline Refresh

Phase 1G-10A (Smoke Harness PID Baseline Refresh, Refresh
`SMOKE-PID-REFRESH-1G-10A-001`) closed the **P2 environment observation** raised
by Phase 1G-10: the dev-only browser smoke harness
(`scripts/run-dev-webui-execute-audit-smoke.sh`) had its read-only Production
Gateway PID preflight pinned to a now-stale sealed value, so it was fail-closing
on a correct, healthy gateway after the host reboot. The risk picture is
unchanged at the technical level; the observation is closed for the current
session.

- **P2 environment observation: smoke harness PID baseline drift.** The sealed
  baseline PID referenced through Phase 1G-09 (`69355`) no longer exists; the
  observed healthy Production Gateway PID after the host reboot is `1962`.
- **Old PID baseline:** `69355`.
- **New observed PID:** `1962`.
- **Root cause:** host reboot (`2026-06-14 04:02:09`) + `launchd` respawn of the
  Production Gateway at `04:04:30` as PID `1962` (PPID = 1). Environmental drift,
  not a phase action.
- **Production health:** exactly one Production Gateway process running, with the
  identical command `hermes_cli.main gateway run --replace`.
- **Production action by Phase 1G-10A:** **none.** The Production Gateway was not
  stopped, restarted, replaced, signaled, or reconfigured. PID `1962` was
  unchanged before and after the phase.
- **`~/.hermes` access:** **none.**
- **Production `state.db` access:** **none.**
- **Script refresh scope:** the pinned PID *value* in the dev-only smoke harness
  was refreshed from `69355` to `1962`, with a comment recording the Phase 1G-10
  host-reboot drift origin. This refresh is allowed **only** in Phase 1G-10A. The
  smoke / preflight / production-count / ports-cleanup logic is **unchanged**;
  the harness still **fails closed** on any future PID drift.
- **Fresh smoke rerun required and performed:** smoke A `6 passed / 1 skipped /
  0 failed`; smoke B `7 passed / 0 failed`; **Overall PASS**.
- **No new P0. No new P1. No new technical P2.** P2-01 … P2-09 remain accepted,
  non-blocking, and carry forward. None was aggravated by Phase 1G-10A.
- **No route governance impact.** Route governance remains OpenAPI 34 / runtime
  34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1.
- **No allowlist impact.** `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- **No provider impact.** No Provider Schema sent; no Provider API called.
- **No release authorization impact.** Release authorization remains pending
  human approver sign-off. Phase 1G-11 is **not started**.

> **P2 environment observation closed for the current session by Phase 1G-10A.**
> A future host reboot can cause a new PID drift; the smoke harness is expected
> to **fail closed again** at that point, at which time a new refresh phase (or
> an explicit operator decision) is required.

---

## 13. Phase 1G-10B Addendum — Human Approver Final Decision

Phase 1G-10B (Human Approver Final Decision, Decision
`HUMAN-DECISION-1G-10B-001`) recorded the designated human approver's final
release decision against the current `dev-huangruibang` branch (HEAD
`56b571fec…`, the pushed Phase 1G-10 + Phase 1G-10A combined state). The risk
picture is unchanged at the technical level; the release authorization dependency
is cleared.

- **P2-09 (human approver sign-off pending): resolved** by
  `HUMAN-DECISION-1G-10B-001`. The designated human approver (黄瑞邦) recorded a
  real **GO** decision on 2026-06-14.
- **Release authorization dependency: cleared.** Release authorization is
  **granted** by the designated human approver.
- **P2-01 … P2-08 remain carried over** as accepted, non-blocking backlog items.
  None was aggravated by Phase 1G-10B (docs-only; no code touched).
- **No new P0. No new P1. No new technical P2.** Phase 1G-10B produced 0 P0, 0 P1,
  and 0 new P2 findings.
- **No route governance impact.** Route governance remains OpenAPI 34 / runtime
  34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1.
- **No allowlist impact.** `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- **No provider impact.** No Provider Schema sent; no Provider API called.
- **No production impact.** Exactly one Production Gateway is running (PID `1962`,
  the Phase 1G-10A refreshed baseline); this phase did not stop / restart / replace
  / reconfigure it. No `~/.hermes` access; no production `state.db` access; ports
  `5180` / `5181` free.
- Decision record: `docs/webui/phase-1g-10b-human-approver-final-decision.md`.
- This addendum authorizes the release decision only; it does not perform a
  production rollout, does not modify production, and does not start Phase 1G-11.

---

## 14. Phase 1G-11 Addendum — Final Release Seal & Phase 2 Unlock

Phase 1G-11 (Final Release Seal & Phase 2 Unlock, Seal `FINAL-SEAL-1G-11-001`,
Unlock `PHASE-2-UNLOCK-1G-11-001`) sealed Phase 1G and unlocked Phase 2 against
the current `dev-huangruibang` branch (HEAD `3c6ae479b…`, the pushed Phase
1G-10B human approver final decision GO record). The risk picture is unchanged
at the technical level; Phase 1G is sealed and Phase 2 is unlocked for
separately authorized work.

- **P2-09 (human approver sign-off pending): remains resolved** by
  `HUMAN-DECISION-1G-10B-001`. Phase 1G is sealed by `FINAL-SEAL-1G-11-001`;
  Phase 2 is unlocked by `PHASE-2-UNLOCK-1G-11-001`.
- **P2-01 … P2-08 remain carried over** as accepted, non-blocking backlog items.
  None was aggravated by Phase 1G-11 (docs-only; no code touched).
- **No new P0. No new P1. No new technical P2.** Phase 1G-11 produced 0 P0, 0
  P1, and 0 new technical P2 findings.
- **No route governance impact.** Route governance remains OpenAPI 34 / runtime
  34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1.
- **No allowlist impact.** `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- **No provider impact.** No Provider Schema sent; no Provider API called.
- **No production impact.** Exactly one Production Gateway is running (PID
  `1962`, the Phase 1G-10A refreshed baseline); this phase did not stop / restart
  / replace / signal / reconfigure it. No `~/.hermes` access; no production
  `state.db` access; ports `5180` / `5181` free.
- **Operational P2 carried forward:** future host reboot may cause Production
  Gateway PID drift again; the dev-only smoke harness is expected to **fail
  closed** at that point and require a new refresh phase (or explicit operator
  decision). The smoke harness must remain fail-closed on PID drift.
- **Phase 2 must not inherit uncontrolled write or Provider execution.** Each
  Phase 2 slice preserves every Phase 1G safety invariant; allowlist expansion
  is per-tool audited; the controlled execution chain is the template for any new
  execution surface.

### New Phase 2 Risks (R2A-01 … R2A-05)

The following risks are introduced for Phase 2 planning. They are **not**
blocking Phase 1G (which is sealed); they govern Phase 2A and beyond. Each has a
mitigation.

#### R2A-01 — Expanding beyond clarify may introduce unintended tool execution

- **Risk ID:** R2A-01
- **Severity:** P2 (Phase 2 planning)
- **Description:** Phase 2A admits tools beyond `clarify`. Each new tool is a
  new execution surface; a misclassified tool could execute when it should not.
- **Current impact:** None yet (Phase 2A not started).
- **Mitigation:** every Phase 2A candidate is **per-tool audited** (registered
  name, input / output schema, side-effect classification) and **individually
  authorized** before addition to the execution surface. Read-only proof is
  required. Ambiguity is resolved toward exclusion.
- **Exit criteria:** each Phase 2A tool carries a recorded audit trail; no tool
  executes without an individual authorization.

#### R2A-02 — Read-only tool boundaries may be ambiguous

- **Risk ID:** R2A-02
- **Severity:** P2 (Phase 2 design)
- **Description:** A candidate tool's read-only status may be unclear (e.g. a
  tool that reads but also logs, caches, or touches shared state).
- **Current impact:** None yet (Phase 2A not started).
- **Mitigation:** the read-only-first principle requires provable
  side-effect-freedom; any ambiguity excludes the tool from Phase 2A and pushes
  it to Phase 2C (write) or out of scope.
- **Exit criteria:** a documented read-only proof per Phase 2A tool; ambiguous
  tools are not admitted.

#### R2A-03 — Provider integration must remain out of Phase 2A

- **Risk ID:** R2A-03
- **Severity:** P2 (Phase 2 sequencing)
- **Description:** Provider Schema / Provider API integration is Phase 2B, not
  2A. Accidentally enabling a Provider path in Phase 2A would move
  `providerSchemaSent` / `providerApiCalled` to `true` prematurely.
- **Current impact:** None yet (Phase 2A not started).
- **Mitigation:** Phase 2A is read-only and Provider-free by scope; the
  `providerSchemaSent=false` / `providerApiCalled=false` invariants remain
  asserted until Phase 2B is separately authorized.
- **Exit criteria:** Phase 2A ships with both Provider flags `false`; Provider
  work is deferred to Phase 2B.

#### R2A-04 — Tool write must remain out of Phase 2A

- **Risk ID:** R2A-04
- **Severity:** P2 (Phase 2 sequencing)
- **Description:** Tool write execution is Phase 2C, not 2A. A write-capable
  tool admitted to Phase 2A would break the read-only contract.
- **Current impact:** None yet (Phase 2A not started).
- **Mitigation:** Phase 2A explicitly excludes writes, shell, DB mutation, and
  any non-read-only side effect. Write candidates are Phase 2C only.
- **Exit criteria:** Phase 2A ships with no write tool; Tool write routes remain
  `0` until Phase 2C.

#### R2A-05 — Audit volume may grow with more tools

- **Risk ID:** R2A-05
- **Severity:** P2 (Phase 2 scale)
- **Description:** Adding more executable tools increases audit JSONL volume,
  which interacts with the carried-over P2-02 / P2-03 / P2-04 / P2-08 audit
  limitations.
- **Current impact:** None yet (Phase 2A not started).
- **Mitigation:** the per-request parse cap (1000 lines) and malformed-line skip
  keep reads bounded and safe; Phase 2D will deliver cursor pagination,
  rotation, race handling, and search when audit volume warrants it.
- **Exit criteria:** audit reads remain bounded and safe as Phase 2 tool count
  grows; Phase 2D closes the audit-scale limitations.

---

## 15. Phase 2A-H1 Addendum — Adversarial Review Completion & Boundary Stabilization

Phase 2A-H1 (Hardening — Adversarial Review Completion & Boundary Stabilization,
Hardening `HARDENING-2A-H1-001`, Closure `ADV-REVIEW-CLOSURE-2A-H1-001`,
Boundary Audit `BOUNDARY-AUDIT-2A-H1-001`) closed the Phase 2A P2 —
**adversarial-review agent died mid-run** — against the current
`dev-huangruibang` branch (input HEAD `0527d6c89…`, the pushed Phase 2A
read-only tool execution). The technical risk picture is unchanged; the
process / tooling P2 is resolved with a deterministic, agent-independent
artifact.

- **P2 (adversarial-review agent died mid-run): resolved** by
  `ADV-REVIEW-CLOSURE-2A-H1-001`. Resolution: the unstable agent-only evidence
  path was replaced with a **deterministic 7-lens hardening audit** and a full
  gate re-run. Result: **7 / 7 lenses PASS, 0 P0, 0 P1.**
- **This was a process / tooling P2, not a product defect.** Phase 2A's
  read-only multi-tool execution and the Phase 1G controlled-execution chain
  were already independently verified by the full Phase 1G test suite, the live
  completed smoke profile, the end-to-end clarify check, and the security /
  routes / allowlist reviewers (all clean). The gap was the absence of a single,
  reproducible, agent-independent adversarial-review record.
- **Deterministic artifacts delivered:**
  `tests/test_dev_web_phase_2a_hardening_boundaries.py` (45 tests, encodes
  every lens invariant, hermetic / no live-gateway dependency) and
  `scripts/run-dev-webui-phase2a-hardening-audit.sh` (orchestrates the audit
  with a PASS / FAIL verdict and non-zero exit on failure).
- **Carried forward (non-blocking):** P2-01 … P2-08 accepted backlog; future
  Production Gateway PID drift on host reboot (the smoke harness fails closed);
  Provider integration deferred to Phase 2B (R2A-03); Tool write deferred to
  Phase 2C (R2A-04); audit-scale hardening deferred to Phase 2D (R2A-05 /
  P2-02 / P2-03 / P2-04 / P2-08).
- **No new P0. No new P1. No new technical P2.** Phase 2A-H1 introduced no
  product-code change; it added only the deterministic hardening artifacts and
  docs.
- **No route governance impact.** Route governance remains OpenAPI 34 / runtime
  34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1.
- **No allowlist impact.** `STATIC_ALLOWLIST` remains exactly the six read-only
  tools (clarify + tool_policy_read, route_governance_read, audit_events_read,
  dev_environment_read, release_status_read).
- **No provider impact.** `providerSchemaSent` / `providerApiCalled` remain
  `False` everywhere; no Provider Schema sent; no Provider API called.
- **No production impact.** Exactly one Production Gateway is running (PID
  `1962`, the Phase 1G-10A refreshed baseline); this phase did not stop /
  restart / replace / signal / reconfigure it. No `~/.hermes` access; no
  production `state.db` access; ports `5180` / `5181` free.
- Records: `docs/webui/phase-2a-hardening-adversarial-review.md`,
  `docs/webui/phase-2a-hardening-boundary-audit.md`,
  `docs/webui/phase-2a-hardening-test-report.md`,
  `docs/webui/phase-2a-hardening-closure.md`.
- **Phase 2B is not started.**

---

## 16. Phase 2B-H1 Addendum — Provider Round-trip Hardening & Transient Flake Closure

Phase 2B-H1 (Hardening — Provider Round-trip Hardening & Transient Flake
Closure, Hardening `HARDENING-2B-H1-001`, Provider Boundary Audit
`PROVIDER-BOUNDARY-AUDIT-2B-H1-001`, Provider Flake Closure
`PROVIDER-FLAKE-CLOSURE-2B-H1-001`) hardened the Phase 2B Provider round-trip
and closed the Phase 2B P2 backlog against the current `dev-huangruibang`
branch (input HEAD `a3cd3b762…`, the pushed Phase 2B controlled provider
round-trip). The technical risk picture is improved (one latent audit-secret
gap fixed); no new risk is introduced.

- **P2 (transient provider/audit redaction flake observed in Phase 2B): resolved
  / closed.** The flake (`test_audit_jsonl_no_secret_or_repr[audit_events_read-R1]`,
  one failure under high parallelism) was **not reproduced** in 60+ deterministic
  reruns (10× isolated variant, 10× full hardening file, 10× high-parallelism
  batch, 10× Phase 2B audit/hardening, plus parametrized repeats). No leak path
  exists in the audit writers. Closure ID: `PROVIDER-FLAKE-CLOSURE-2B-H1-001`.
  Result: closed as non-reproduced with deterministic, agent-independent evidence.
- **Latent audit-secret gap (fixed, in scope):** the provider audit sanitizer's
  PEM private-key value pattern matched only bare/RSA (the schema-module copy
  matched no standard header at all), and suffixed secret field names
  (`privateKeyPem`, `credentials`, `xApiKey`) escaped `_is_forbidden_field`.
  Widened to catch every PEM variant (`-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`)
  across all four provider modules; `_is_forbidden_field` substring stems
  broadened (`apikey`, `privatekey`, `credential`). Pinned by new tests.
- **P2-1 (real-vendor provider adapter not wired in Phase 2B): accepted P2.**
  The blocked framework exists; real mode is blocked by default and stays
  blocked even when eligible. The concrete vendor call is deferred to a
  separately-authorized future phase.
- **Tool write deferred to Phase 2C.** Tool write remains `0`; no write tool
  executed.
- **Production rollout not performed.** Release authorization remains governed
  by the human approver decision chain; Phase 2B-H1 performed no rollout.
- **Deterministic artifacts delivered:**
  `tests/test_dev_web_phase_2b_hardening_boundaries.py` (66 tests, 8-lens
  boundary + flake-closure scenario + PEM/field-stem pinning) and
  `scripts/run-dev-webui-phase2b-hardening-audit.sh` (14-check audit with
  PASS/FAIL verdict and non-zero exit on failure).
- **No new P0. No new P1. No new technical P2.** Phase 2B-H1's only product-code
  change is the strictly-improving provider audit secret-pattern widening
  (never relaxes a boundary; all four modules on the allowed-modify list).
- **No route governance impact.** Route governance remains OpenAPI 34 / runtime
  34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1. No new route.
- **No allowlist impact.** `STATIC_ALLOWLIST` remains exactly the six read-only
  tools.
- **No production impact.** Exactly one Production Gateway is running (PID
  `1962`); this phase did not stop / restart / replace / signal / reconfigure
  it. No `~/.hermes` access; no production `state.db` access; ports `5180` /
  `5181` free.
- Records: `docs/webui/phase-2b-h1-provider-roundtrip-hardening.md`,
  `docs/webui/phase-2b-h1-provider-boundary-audit.md`,
  `docs/webui/phase-2b-h1-provider-flake-closure.md`,
  `docs/webui/phase-2b-h1-test-report.md`.
- **Phase 2C is not started.**

---

*Phase 1G-05 Risk Register — 0 P0, 0 P1, 9 P2 (P2-01 … P2-08 accepted,
non-blocking; P2-09 human approver sign-off **resolved** by
`HUMAN-DECISION-1G-10B-001` — release authorization dependency cleared, not a
technical Pilot failure) + 5 new Phase 2 planning risks (R2A-01 … R2A-05, each
with a mitigation). Phase 1G is **sealed** by `FINAL-SEAL-1G-11-001`; Phase 2 is
**unlocked** by `PHASE-2-UNLOCK-1G-11-001`. The technical P2 items do not block
Phase 1G-04 sealed acceptance, the Pilot baseline, the Phase 1G-07 RC dry run
(`RC-1G-07-001`, GO), or the Phase 1G-09 Pilot acceptance execution
(`PILOT-EXEC-1G-09-001`, PASS). Human approver final decision recorded in Phase
1G-10B: **GO**; release authorization granted by the designated human approver.
Phase 1G is sealed; Phase 2A is not started.*

## Phase 2C Update — Controlled Tool Write Execution

Phase 2C introduces controlled dev-sandbox write tools. New risk register
entries (all mitigated, P0/P1 = 0):

- **R2C-01 (write-outside-sandbox)** — mitigated by sandbox path validation +
  symlink-escape check + source-inspection tests. No write escapes the sandbox.
- **R2C-02 (route-addition)** — mitigated by reusing `/tools/dry-run` +
  `/tools/execute` via `mode` branches; route governance stays 34/34/5/0/1/1.
- **R2C-03 (secret/arg leak)** — mitigated by audit re-redaction + result
  shape (no raw arguments); verified by the no-secret-leak tests.
- **R2C-04 (provider auto-write)** — mitigated: provider write is preview-only,
  `blocked_write_provider_auto_execute_denied`; real provider write blocked.
- **R2C-05 (production gateway PID drift)** — an external restart moved the
  live PID `1962 → 28428` during the session; under user authorization the
  baseline constant was refreshed. The task sanctions an authorized PID refresh
  on drift (P2). The gateway was never stopped/restarted/signaled by Phase 2C.

## Phase 2C-H1 Update — Write Execution Hardening

Phase 2C-H1 closes two write-execution risks (all mitigated, P0/P1 = 0):

- **R2C-H1-01 (rollback escapes sandbox)** — mitigated by manifest-store
  `rollbackId` validation, sandbox target validation, symlink-escape check, and
  current-hash verification at preview + execute time.
- **R2C-H1-02 (token replay / expiry / scope confusion)** — mitigated by the
  file-backed token store: plain secret never stored, TTL enforced, scope
  isolation (write↔rollback↔provider), persistent single-use replay protection.
- **R2C-H1-03 (beforeContent leak)** — mitigated: restore content stored
  internally only, never returned by the public safe view or written to audit.
- **R2C-H1-04 (production gateway PID drift)** — baseline carried from Phase 2C
  at **28428**; unchanged by this work.

## Phase 2D update

Phase 2D (durable audit store) resolves or advances several register items:

- The deferred "advanced audit storage / indexing" item is now implemented
  (canonical `audit_schema_v2`, append-only store, index, cursor pagination,
  rotation, corruption quarantine).
- The Phase 2A `str(object)` sanitizer defense-in-depth gap is **closed** by
  the unified audit sanitizer (non-JSON-native values collapse to
  `<non_json_value>` / `<bytes_redacted>`, never a repr).
- Audit JSONL rotation / race hardening is implemented (file locking +
  on-disk sequence floor + unique tmp-replace meta writes).
- Production Gateway PID baseline remains **28428**; Phase 2D performs no
  production rollout, no `~/.hermes` access, and no production `state.db`
  access. Audit store files remain runtime-only (never committed). See
  [phase-2d-audit-security-boundary](phase-2d-audit-security-boundary.md).

## Phase 2D-H1 Update — Audit Storage Hardening

Phase 2D-H1 (audit storage hardening) is complete and pushed
(`chore(webui): harden audit storage indexing`). It deterministically hardens
the Phase 2D durable dev audit store with a 10-lens review (schema, sanitizer,
append store, index, query, rotation, recovery, dual-write, API+Viewer no-leak,
production isolation). All 10 lenses PASS; 0 P0, 0 P1.

- Hardening ID: `HARDENING-2D-H1-001`
- Audit Consistency ID: `AUDIT-CONSISTENCY-2D-H1-001`
- Audit Stress ID: `AUDIT-STRESS-2D-H1-001`
- Audit Security Closure ID: `AUDIT-SECURITY-CLOSURE-2D-H1-001`

Resolved / closed:
- durable audit store MVP hardening (concurrency, stale-meta sequence floor,
  rotation, corruption quarantine, dual-write consistency all validated)
- index / query / rotation / recovery stress validation (index == scan for all
  indexed fields; 32-thread append; repeated-run 5/5)
- dual-write consistency validation (all 7 audit kinds bridge exactly once)
- audit API / UI no-leak validation (no secret / raw args / callable repr /
  production path on disk, index, API, Viewer, or cursor tokens)
- the unified sanitizer `str(object)` defense-in-depth gap remains closed

One latent inconsistency was fixed (security-neutral):
- `_minimal_safe_event` `sequence: -1` → `0` so the fallback event actually
  validates against `audit_schema_v2` and can persist a safe breadcrumb as its
  docstring states (no boundary loosened).

Remaining P2 (deferred, unchanged):
- production audit rollout deferred
- audit encryption at rest deferred
- multi-user audit namespace deferred
- retention deletion deferred
- compression deferred
- advanced full-text indexing deferred
- cross-device sync deferred
- real provider vendor integration deferred
- frontend UX polish deferred
- future host-reboot PID drift may require an authorized baseline refresh
  (Production Gateway baseline remains 28428)

Production Gateway PID baseline remains **28428**; Phase 2D-H1 performs no
production rollout, no `~/.hermes` access, and no production `state.db` access.
Audit store files remain runtime-only (never committed). See
[phase-2d-h1-audit-storage-hardening](phase-2d-h1-audit-storage-hardening.md).

## Phase 2E addendum — Frontend UX Polish

Phase 2E is frontend-only polish (a unified developer console at `/#/console`).
It introduces **no new backend capability, no new HTTP route, no Tool write
route, no Provider route**, and no production access. Residual risks are all P2:
full WCAG certification is deferred; the frozen route-governance / PID baselines
are verified by the smoke preflight + backend invariant tests rather than probed
live from the UI (live probing would consume confirmation tokens and pollute the
audit trail). Production Gateway PID baseline remains **28428**; no `~/.hermes`
access; no production `state.db` access; runtime artifacts remain uncommitted.
See [phase-2e-frontend-ux-polish](phase-2e-frontend-ux-polish.md) and
[phase-2e-accessibility-and-safety-review](phase-2e-accessibility-and-safety-review.md).

## Phase 2E-H1 addendum — Frontend UX Hardening

Phase 2E-H1 (Frontend UX Hardening — Console Stability, Accessibility & Safety
Closure) is complete and pushed (`chore(webui): harden dev console ux`). It is a
hardening phase — not Phase 3 — that deterministically hardens the Phase 2E
unified developer console through a 9-lens review. All 9 lenses PASS; 0 P0, 0 P1.

- Hardening ID: `HARDENING-2E-H1-001`
- Console Workflow Review ID: `CONSOLE-WORKFLOW-2E-H1-001`
- Accessibility Review ID: `ACCESSIBILITY-2E-H1-001`
- UI Security Closure ID: `UI-SECURITY-CLOSURE-2E-H1-001`

Resolved / closed:
- console routing and navigation-state hardening (additive route, vertical
  tablist + roving tabindex, persistence + invalid fallback, KeepAlive
  dynamic-component fallback)
- overview / safety baseline hardening (stale Phase 2E "in progress" status
  corrected to "completed"; Phase 2E-H1 added to the frozen timeline)
- workflow continuity hardening (read-only / provider / write / rollback / audit
  coherent; cross-nav strips + unified blocked panels per surface)
- audit cross-navigation hardening (prefill bridge intact; prefill marker made
  lossy so the full id lives only in the store)
- blocked-reason fallback hardening (P1 catalogue drift corrected:
  `blocked_write_forbidden_target` → the real backend `blocked_write_forbidden_path`;
  8 missing stable backend codes added; unknown fallback + actions reworded to
  avoid the literal "bypass"; backend vocabulary pinned as a contract)
- accessibility / responsive baseline hardening (tablist, aria-selected, Arrow /
  Home / End + focus move, role=status/role=alert/aria-busy, non-color severity
  text, 820px responsive collapse, focus-visible)
- UI no-leak closure (no API key / raw token / full hash / raw arg / secret /
  callable repr / production path; no runtime artifact committed)

Remaining P2 (deferred, unchanged):
- full WCAG certification deferred
- advanced visual design system deferred
- production audit rollout deferred
- audit encryption at rest deferred
- multi-user namespace deferred
- retention deletion deferred
- compression deferred
- advanced full-text indexing deferred
- real provider vendor integration deferred
- future host-reboot PID drift may require an authorized baseline refresh
  (Production Gateway baseline remains 28428)

No new backend high-risk capability was introduced. No new HTTP route, Tool write
HTTP route, Provider route, shell command tool, database mutation, external
service write, real provider vendor call, production rollout, `~/.hermes` access,
or production `state.db` access was introduced. Route governance remains OpenAPI
34 / runtime 34 / Tool GET 5 / Tool write route 0 / dry-run 1 / execution 1.
Production Gateway PID **28428** untouched; no `~/.hermes` access; no production
`state.db` access; runtime artifacts remain uncommitted. Phase 3 is **not
started**. See [phase-2e-h1-frontend-ux-hardening](phase-2e-h1-frontend-ux-hardening.md),
[phase-2e-h1-console-workflow-review](phase-2e-h1-console-workflow-review.md),
[phase-2e-h1-accessibility-responsive-review](phase-2e-h1-accessibility-responsive-review.md),
[phase-2e-h1-ui-security-closure](phase-2e-h1-ui-security-closure.md), and
[phase-2e-h1-test-report](phase-2e-h1-test-report.md).

---

## Phase 3A Status Update (2026-06-16)

Phase 3A (Dev-only Agent Workflow MVP) is **implemented**. The workflow surface
adds no new route, no new audit kind, and no new high-risk capability: it only
orchestrates the existing read-only / fake-provider / write-preview /
rollback-reference surfaces behind a manual, approval-gated, audit-linked runner.
All P0 stop conditions remain clear: real provider blocked, autonomous write
blocked, write/rollback execution from the workflow blocked, shell / db /
external write blocked, no `~/.hermes` access, no production `state.db` access,
route governance unchanged (34/34/5/0/1/1), Production Gateway PID `28428`
untouched. See [phase-3a-security-boundary](phase-3a-security-boundary.md).

## Phase 3A-H1 Addendum — Workflow Hardening (2026-06-16)

**ID:** `HARDENING-3A-H1-001` (with `WORKFLOW-STATE-3A-H1-001`,
`WORKFLOW-APPROVAL-3A-H1-001`, `WORKFLOW-AUDIT-3A-H1-001`,
`WORKFLOW-UI-3A-H1-001`).

Phase 3A-H1 is the deterministic hardening pass that follows Phase 3A (NOT
Phase 3B). It adds adversarial backend tests (7 files / 300 tests), frontend
hardening specs (5 files / 33 tests), a `phase3a_h1_workflow_hardening` smoke
profile, and an 11-lens audit script — with **no implementation change** and
**no new capability**.

All P0 stop conditions remain clear after the pass: real provider blocked,
provider auto-write / autonomous write blocked, workflow write-execute and
rollback-execute blocked (preview / reference only), shell / db / external
write blocked, no `~/.hermes` access, no production `state.db` access, route
governance unchanged (34/34/5/0/1/1), Production Gateway PID `28428` untouched
(read-only check). 11/11 lenses PASS; P0 = 0; P1 = 0; Phase 3B not started.

No new risk introduced. Residual risks are unchanged from Phase 3A. See
[phase-3a-h1-workflow-hardening](phase-3a-h1-workflow-hardening.md).

## Phase 3B Planning Addendum — Real Provider Read-only Scope Freeze (2026-06-16)

**ID:** `PHASE-3B-PLANNING-001` (companion register:
`PHASE-3B-RISK-REGISTER-001`, see
[phase-3b-security-risk-register](phase-3b-security-risk-register.md)).

Phase 3B Planning is the **docs-only** scope freeze for the future Real Provider
Read-only Controlled Integration. It introduces **no new risk** — it does not
wire or enable a real provider, does not read an API key, does not make a network
call, and does not change any product code. The real provider remains blocked by
default exactly as after Phase 2B-H1 (`blocked_real_provider_not_wired_in_phase_2b`).

The companion register records the risks that govern a **future** Phase 3B
implementation (12 P0 stop conditions, 9 P1 push-gates, 7 P2 deferrals). The P0
stop conditions of direct relevance here are: real provider enabled without
authorization (`R3B-P0-01`), API-key leak (`R3B-P0-02`), secret in audit / log /
UI (`R3B-P0-03`), prompt-injection-driven disallowed tool call (`R3B-P0-04`),
arbitrary-URL fetch / SSRF (`R3B-P0-05`), provider write / auto-write /
autonomous execution (`R3B-P0-06`), shell / db / external write (`R3B-P0-07`),
route drift (`R3B-P0-08`), production rollout (`R3B-P0-09`), `~/.hermes` /
production `state.db` access (`R3B-P0-10`), Production Gateway PID drift
(`R3B-P0-11`), runtime-artifact commit (`R3B-P0-12`).

All P0 stop conditions remain clear after this planning phase: real provider
blocked, API key not read / not leaked, no external network call, provider write
/ auto-write / autonomous execution blocked, shell / db / external write blocked,
no `~/.hermes` access, no production `state.db` access, route governance
unchanged (34/34/5/0/1/1), Production Gateway PID `28428` untouched. **Phase 3B
implementation was not started.** See [phase-3b-planning](phase-3b-planning.md)
and [phase-3b-go-no-go](phase-3b-go-no-go.md).

---

## Phase 3B-H1 update (completed)

Phase 3B (real-provider read-only boundary) shipped, then Phase 3B-H1 hardened
it: **10 / 10 lenses PASS, P0 = 0, P1 = 0.** Every P0 stop condition holds —
real provider disabled by default, API key not read / not leaked (env-only,
value-free), no external network call (mock-only), provider write / auto-write /
autonomous write blocked, shell / db / external write blocked, no `~/.hermes`
access, no production `state.db` access, route governance unchanged
(34/34/5/0/1/1), Production Gateway PID `28428` untouched. **Phase 3C was not
started.** See [phase-3b-h1-provider-boundary-hardening](phase-3b-h1-provider-boundary-hardening.md).

## Phase 3B-Live-Enablement implementation update (2026-06-17)

The live layer shipped (`PHASE-3B-LIVE-ENABLEMENT-IMPL-001`) on top of the
hardened boundary. P0 = 0, P1 = 0: live provider disabled by default; a live
request requires a fresh single-use 5-minute human approval; the API key is
read env-only and only past every gate, value-free (never in audit / log / UI /
exception); the only egress is a single HTTPS POST to `api.openai.com`
(http / localhost / private IP / off-allowlist redirect blocked); first-live
caps enforced (1 request / 1000 / 200 / 5c / 0 retry / 60s); 14-trigger kill
switch blocks before secret read / network; provider write / auto-write /
autonomous write / shell / db / external / production remain blocked; no tool
execution for the first live request; 18 redacted dual-write `provider_live_*`
audit events (fail-closed); single-use approval invalidated after use; no new
route (34/34/5/0/1/1); no `~/.hermes` / production `state.db` access; PID
`28428` untouched. Default tests / smoke read no real key and make no real
network call. **Manual one-shot live execution remains NO-GO until separately
authorized. Phase 3C was not started.** See
[phase-3b-live-enablement-implementation](phase-3b-live-enablement-implementation.md),
[phase-3b-live-enablement-security-boundary](phase-3b-live-enablement-security-boundary.md),
[phase-3b-live-enablement-risk-register](phase-3b-live-enablement-risk-register.md),
and [phase-3b-live-enablement-test-report](phase-3b-live-enablement-test-report.md).

The live gate was hardened in place under `HARDENING-3B-LIVE-H1-001`
(Phase 3B-Live-Enablement H1). The deterministic 11-lens hardening pass added
edge-case backend + frontend tests, a `phase3b_live_h1_hardening` smoke profile
(in `all`), a hardening audit script, and hardening docs. 11/11 lenses PASS,
P0 = 0, P1 = 0. No live request was executed, no real `OPENAI_API_KEY` was read,
no real network call was made, and no implementation defect was found (so no
production-boundary code changed). The TTL / single-use / in-scope / value-free
approval, the never-reads-env-on-blocked-path secret gate, the single-host
HTTPS allowlist, the frozen caps + fail-closed counters, the 14-trigger kill
switch, the no-tool-execution round-trip, and the redacted fail-closed
`provider_live_*` audit all held under the added edge-case probes. The manual
one-shot live profile remains excluded from `all`. Route governance unchanged
(34/34/5/0/1/1). PID `28428` untouched. See
[phase-3b-live-h1-hardening](phase-3b-live-h1-hardening.md) and
[phase-3b-live-h1-test-report](phase-3b-live-h1-test-report.md).

Remaining P2 (deferred, unchanged): streaming, multi-provider routing, provider
write, token encryption at rest, multi-user namespace, and the separately-
authorized manual one-shot live execution (and any concrete real HTTP client
wiring behind it).

---

## Phase 3C Planning update (scope frozen — not implemented)

The next slice — **Phase 3C — Plugin / Capability Registry** — had its scope
**frozen** in a separate docs-only planning phase (`PHASE-3C-PLANNING-001`)
without being implemented. The Phase 3C risk register
([phase-3c-security-risk-register.md](phase-3c-security-risk-register.md)) is
**additive** to this one; it does not relax any P0/P1 here. Its P0 stop
conditions include: dynamic plugin loading introduced (CAP-P0-01), external
marketplace / remote registry introduced (CAP-P0-02), capability grants
permission instead of describing it (CAP-P0-03), write capability bypasses
dry-run / confirmation (CAP-P0-04), provider live gate bypassed (CAP-P0-05),
shell / database / external-HTTP capability exposed (CAP-P0-06), production
operation exposed (CAP-P0-07), `~/.hermes` / production `state.db` accessed
(CAP-P0-08), route governance drift (CAP-P0-09), secret / callable / path leak
in registry or UI (CAP-P0-10), runtime artifact committed (CAP-P0-11), and
`.claude/` committed (CAP-P0-12). The registry is static, dev-only, and
descriptive (grants no permission, loads no code, adds no route by default).
**Phase 3C Implementation was completed (2026-06-17) within the frozen scope.**
All CAP-P0 stop conditions remain closed: no dynamic loading, marketplace,
remote registry, permission grant, gate bypass, shell/SQL/HTTP/production
capability execution, `~/.hermes` / production `state.db` access, route drift,
secret/callable/path leak, or runtime/`.claude` artifact. Forbidden fields are
rejected by validation; the registry is read-only and no-leak. See
[phase-3c-static-capability-registry-implementation](phase-3c-static-capability-registry-implementation.md),
[phase-3c-capability-registry-security-boundary](phase-3c-capability-registry-security-boundary.md),
and [phase-3c-go-no-go](phase-3c-go-no-go.md).

---

## Phase 3C-H1 Hardening Update (2026-06-18)

`HARDENING-3C-H1-001` hardened the static Capability Registry through a 12-lens
review (12 / 12 PASS, P0 = 0, P1 = 0). **One real defect was found and closed:**
the forbidden-field scanner was shallow, so a forbidden field nested inside an
allowed field's value (e.g. `{"metadataSchema": {"shellCommand": ...}}`) could
pass validation and leak through the read model. The scan is now **recursive**
(top-level keys + any nested dict / list / tuple), and scalar-string fields are
type-guarded against nested-structure smuggling. CAP-P0-10 (secret / callable /
path leak in registry or UI) is reinforced: three independent layers now
enforce the forbidden-field boundary — the recursive scan, the scalar type
guard, and the `DETAIL_FIELDS` read-model allowlist. All 160 Phase 3C backend
tests still pass; 8 backend + 6 frontend hardening test files, a new smoke
profile (Profile Q), and `scripts/run-dev-webui-phase3c-hardening-audit.sh`
were added. No new P0/P1 risk introduced. **Phase 3D (Plugin Runtime) not
started.** See [phase-3c-h1-capability-registry-hardening](phase-3c-h1-capability-registry-hardening.md)
and [phase-3c-h1-forbidden-fields-hardening](phase-3c-h1-forbidden-fields-hardening.md).

---

## Phase 3C Closeout Update (2026-06-18)

Phase 3C is formally **closed** (`PHASE-3C-CLOSEOUT-001`). The Phase 3C risk
register (CAP-P0-01 … CAP-P0-12) is fully **CLOSED** — P0 open = 0, P1 open =
0. The one real defect (nested forbidden-field leak, CAP-P0-10 reinforcement)
is CLOSED. The single P2 (frontend TS manifest mirror generator) is deferred,
non-blocking, and its drift is bounded by the H1 manifest-consistency test.
Phase 3D (Plugin Runtime) carries its own future risk register and is not
started. See [phase-3c-risk-closure](phase-3c-risk-closure.md) and
[phase-3c-closeout](phase-3c-closeout.md).

---

## Phase 3D Planning Addendum — Plugin Runtime Scope Freeze (2026-06-18)

**ID:** `PHASE-3D-PLANNING-001` (companion register: `PHASE-3D-RISK-REGISTER-001`,
see [phase-3d-risk-register](phase-3d-risk-register.md)).

Phase 3D Planning is the **docs-only** scope freeze for a future Phase 3D Plugin
Runtime. It introduces **no new risk** — it does not implement a plugin runtime,
does not load any plugin, does not perform dynamic loading, does not read any API
key, does not make a network call, and does not change any product code.

The companion register records the risks that govern a **future** Phase 3D
implementation (22 P0 stop conditions, 8 P1 push-gates, 5 P2 deferrals). The P0
stop conditions of direct relevance here are: plugin runtime implemented during
planning (PLUG-P0-01), dynamic import (PLUG-P0-02), local plugin directory loading
(PLUG-P0-03), remote registry (PLUG-P0-04), marketplace (PLUG-P0-05), external
plugin fetch (PLUG-P0-06), provider-generated plugin (PLUG-P0-07), LLM-generated
tool auto-install (PLUG-P0-08), shell command execution (PLUG-P0-09), database
mutation (PLUG-P0-10), external HTTP execution (PLUG-P0-11), production operation
(PLUG-P0-12), permission grant bypass (PLUG-P0-13), Tool policy bypass
(PLUG-P0-14), Provider live gate bypass (PLUG-P0-15), Workflow approval bypass
(PLUG-P0-16), audit bypass (PLUG-P0-17), secret / callable / path leak
(PLUG-P0-18), route governance drift (PLUG-P0-19), `~/.hermes` / production
`state.db` access (PLUG-P0-20), runtime artifact commit (PLUG-P0-21), and
`.claude/` commit (PLUG-P0-22).

All P0 stop conditions remain clear after this planning phase: no plugin runtime,
no dynamic loading, no remote registry, no marketplace, no external plugin fetch,
no provider-generated plugin, no LLM-generated plugin install, no shell / DB /
external-HTTP / production execution, no provider write, no autonomous write, no
`~/.hermes` access, no production `state.db` access, route governance unchanged
(34 / 34 / 5 / 0 / 1 / 1), Production Gateway PID `28428` untouched. **Phase 3D
Implementation was not started.** See [phase-3d-planning](phase-3d-planning.md),
[phase-3d-plugin-runtime-scope-freeze](phase-3d-plugin-runtime-scope-freeze.md),
and [phase-3d-go-no-go](phase-3d-go-no-go.md).

---

## Phase 3D Planning Closeout Addendum (2026-06-18)

Phase 3D Planning is formally **closed** (`PHASE-3D-PLANNING-CLOSEOUT-001`,
docs-only). Risk closure: **P0 introduced by planning = 0; P1 = 0; P2 deferred =
5** (PLUG-P2-01 … PLUG-P2-05, intentional deferrals). Every PLUG-P0 stop condition
remains clear (closed) at the closeout baseline: no plugin runtime, no dynamic
loading, no remote registry, no marketplace, no external plugin fetch, no
provider-generated plugin, no LLM-generated plugin install, no shell / DB /
external-HTTP / production execution, no provider write, no autonomous write, no
`~/.hermes` access, no production `state.db` access, route governance unchanged
(34 / 34 / 5 / 0 / 1 / 1), Production Gateway PID `28428` untouched. **Phase 3D
Implementation was not started.** Implementation readiness = **CONDITIONAL GO**
for prompt preparation only, **NO-GO** for execution. See
[phase-3d-risk-closure](phase-3d-risk-closure.md),
[phase-3d-planning-closeout](phase-3d-planning-closeout.md), and
[phase-3d-final-go-no-go](phase-3d-final-go-no-go.md).

## Update — Phase 3D Implementation COMPLETE (static descriptor skeleton)

**Phase 3D Implementation is COMPLETE** as a static dev-only plugin descriptor
registry skeleton (descriptor-only, disabled-by-default, capability-bound,
read-only). No new risk was introduced: there is no plugin runtime, no loader,
no dynamic loading, no local plugin directory loading, no remote registry /
marketplace / external plugin fetch, no provider-generated plugin, no
LLM-generated plugin install, no shell / DB / external-HTTP / production
execution, no provider write, no autonomous write, no new route, no `~/.hermes`
access, no production `state.db` access. The plugin-runtime risk items remain
**deferred / NO-GO**. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1);
Production Gateway PID `28428` untouched. See
[phase-3d-plugin-descriptor-security-boundary](phase-3d-plugin-descriptor-security-boundary.md)
and
[phase-3d-plugin-descriptor-test-report](phase-3d-plugin-descriptor-test-report.md).
