# Phase 1G-05: Risk Register

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

| Severity | Count | Blocks Phase 1G-04 sealed acceptance? |
|----------|-------|---------------------------------------|
| **P0** | 0 | n/a |
| **P1** | 0 | n/a |
| **P2** | 8 | **No** |

> **No P0. No P1.** The remaining P2 items do **not** block the Phase 1G-04
> sealed acceptance, the Phase 1G-05 post-sealing readiness, or the Pilot
> acceptance baseline. They are recorded for transparency and future-phase
> planning.

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

---

## 5. Risk Acceptance

These eight P2 items are **accepted as known limitations**. They are recorded
here so they are visible to the Pilot reviewer and to any future phase. None of
them:

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

*Phase 1G-05 Risk Register — 0 P0, 0 P1, 8 P2 (accepted, non-blocking). The
remaining P2 items do not block Phase 1G-04 sealed acceptance, the Pilot
baseline, or the Phase 1G-07 RC dry run (`RC-1G-07-001`, GO).*
