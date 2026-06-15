# Phase 3 Risk Register

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3 Planning |
| Title | Phase 3 Risk Register (P0 / P1 / P2) |
| Status | Recorded |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Risk-Register ID | `PHASE-3-RISK-REGISTER-001` |

> Companion to [phase-3-planning.md](phase-3-planning.md). This register covers
> Phase 3 as a whole with emphasis on the Phase 3A entry gate. None of these
> risks are introduced by this planning phase — this is docs-only.

Each risk follows: ID · Severity · Description · Impact · Mitigation · Risk
owner · Gate · Blocking condition.

---

## 1. P0 Risks (block / stop immediately)

### R3-P0-01 — Real provider enabled unexpectedly

- **Severity:** P0
- **Description:** A Phase 3 change wires or enables a real provider vendor
  call when only disabled / fake is authorized.
- **Impact:** Network call, API-key / token exposure, prompt injection,
  hallucinated tool calls, real cost.
- **Mitigation:** Keep provider in `disabled` / `fake`; real provider blocked
  by default and by the Phase 2B-H1 eligibility gate. Workflow provider steps
  reuse the fake adapter only.
- **Risk owner:** Phase 3A implementer + gates.
- **Gate:** route governance + provider contract tests + smoke.
- **Blocking condition:** any `externalNetworkCalled=true` outside an
  explicitly authorized real-provider phase.

### R3-P0-02 — Provider auto-write

- **Description:** A provider write path auto-executes a write without an
  explicit operator approval.
- **Impact:** Unauthorized write to the dev sandbox / possible state change.
- **Mitigation:** Provider write stays preview-only (`blocked_write_provider_auto_execute_denied`
  is unchanged from Phase 2C). Workflow write steps require an explicit gate
  approval.
- **Gate:** write contract tests + smoke.
- **Blocking condition:** any provider-driven write execution.

### R3-P0-03 — Autonomous write without confirmation

- **Description:** A workflow step executes a write autonomously, bypassing the
  confirmation token.
- **Impact:** Unauthorized file mutation inside the dev sandbox.
- **Mitigation:** Every write step reuses the Phase 2C/2C-H1 confirmation-token
  + write gate. No step may auto-execute a write.
- **Gate:** write + confirmation-token tests.
- **Blocking condition:** any write without a valid confirmation token.

### R3-P0-04 — Shell command execution

- **Description:** A Phase 3 change introduces shell / process execution.
- **Impact:** Arbitrary command execution, escape from the sandbox.
- **Mitigation:** No shell / process tool is added. Boundary search rejects
  `subprocess` / `os.system` / `shell=True` etc. in the committed diff.
- **Blocking condition:** any shell / process execution introduced.

### R3-P0-05 — Database mutation

- **Description:** A Phase 3 change writes to a database or production
  `state.db`.
- **Impact:** Production / persisted state corruption.
- **Mitigation:** No new DB; no `state.db` write. Boundary search rejects
  `INSERT INTO` / `UPDATE … SET` / `DELETE FROM` etc.
- **Blocking condition:** any database mutation introduced.

### R3-P0-06 — External service write

- **Description:** A Phase 3 change writes to an external service over the
  network.
- **Impact:** Outbound side effect, data exfiltration.
- **Mitigation:** No network write outside the offline fake provider. Boundary
  search rejects `requests.post` / `httpx` / `urllib` / `aiohttp` / `curl` etc.
- **Blocking condition:** any outbound network write introduced.

### R3-P0-07 — Production rollout

- **Description:** A Phase 3 change performs a production rollout or binds to a
  non-loopback interface.
- **Impact:** Production exposure.
- **Mitigation:** WebUI binds to `127.0.0.1` only; dev `HERMES_HOME` enforced;
  no production rollout.
- **Blocking condition:** any production rollout or `0.0.0.0` bind.

### R3-P0-08 — `~/.hermes` access

- **Description:** A Phase 3 change reads from or writes to `~/.hermes`.
- **Impact:** Production instance touched.
- **Mitigation:** `enforce_dev_environment()` allowlist; boundary search rejects
  the production path as a live target.
- **Blocking condition:** any `~/.hermes` read/write.

### R3-P0-09 — Production `state.db` access

- **Description:** A Phase 3 change accesses the production `state.db`.
- **Impact:** Production state touched.
- **Mitigation:** dev `HERMES_HOME` isolation enforced.
- **Blocking condition:** any production `state.db` access.

### R3-P0-10 — API key exposure

- **Description:** A Phase 3 surface renders, logs, or commits an API key.
- **Impact:** Secret leak.
- **Mitigation:** Provider UI never accepts a key; sanitizer redacts; boundary
  search sweeps for `sk-` / `api[_-]?key` / `Bearer` / PEM.
- **Blocking condition:** any API key rendered / logged / committed.

### R3-P0-11 — Raw token / full tokenHash / raw arguments / callable repr exposure

- **Description:** A Phase 3 surface leaks a raw confirmation token, full token
  hash, raw tool arguments, or a callable / function repr.
- **Impact:** Token replay / internal exposure.
- **Mitigation:** Inherit the Phase 2E-H1 no-leak closure; sanitizer collapses
  non-JSON values to a sentinel; ids rendered lossy via `truncateHash`.
- **Blocking condition:** any such value surfaced.

### R3-P0-12 — Route governance unauthorized expansion

- **Description:** A Phase 3 change adds an HTTP route, a Tool write HTTP route,
  or a Provider route without explicit separate authorization.
- **Impact:** Surface / boundary drift.
- **Mitigation:** Default is "no new route"; workflow reuses the existing
  `mode`-branched routes. Any change must be explicitly approved + recorded.
- **Gate:** `test_dev_check_webui.py` + `test_dev_web_0c06_closure.py`.
- **Blocking condition:** OpenAPI / runtime route count drifts from 34 / 34
  without an approved, recorded change.

### R3-P0-13 — Runtime artifact commit

- **Description:** A Phase 3 change stages / commits an audit-store /
  token-store / rollback-manifest / runtime-audit-JSONL file or `.claude/`.
- **Impact:** Secret / state leak into the repository.
- **Mitigation:** Boundary search rejects these paths; `.gitignore` coverage
  verified.
- **Blocking condition:** any such artifact staged.

### R3-P0-14 — Production Gateway stopped / restarted / replaced / signaled / PID drift

- **Description:** A Phase 3 change stops / restarts / replaces / signals /
  reconfigures the Production Gateway, or the PID drifts from `28428`.
- **Impact:** Production messaging outage.
- **Mitigation:** Dev WebUI never controls the production gateway; pre/post
  production-safety checks pin PID `28428` and count `1`.
- **Blocking condition:** PID != `28428` or count != `1` at any check.

---

## 2. P1 Risks (block push until resolved)

### R3-P1-01 — Workflow state corruption

- **Description:** Workflow state becomes unreadable / inconsistent.
- **Impact:** Workflow cannot resume; operator confusion.
- **Mitigation:** Dev-only store; validate on load; corrupted state fails safe
  (read-only, no execution).
- **Gate:** workflow state tests.

### R3-P1-02 — Workflow audit missing

- **Description:** A workflow step runs without writing / linking its audit
  event.
- **Impact:** Audit gap; loss of traceability.
- **Mitigation:** Every step reuses the controlled-execution audit chain; a
  test asserts every executed step has a linked audit id.
- **Gate:** audit-linkage tests.

### R3-P1-03 — Approval-gate bypass

- **Description:** A step advances past a gate without confirmation.
- **Impact:** Unauthorized step execution.
- **Mitigation:** Gates reuse the Phase 2C-H1 confirmation-token model; a test
  asserts a gate cannot be skipped.
- **Gate:** approval-gate tests.

### R3-P1-04 — Step order invalid

- **Description:** Steps execute out of order or skip prerequisites.
- **Impact:** Incoherent plan; unsafe sequencing.
- **Mitigation:** The planner validates step order; invalid orders are rejected
  before preview.
- **Gate:** planner validation tests.

### R3-P1-05 — Cursor / audit link broken

- **Description:** Cross-navigation from a step to its audit event fails.
- **Impact:** Operator cannot trace a step to its audit.
- **Mitigation:** Reuse `devConsoleNav.prefillAuditSearch`; test the cross-nav
  bridge (as in Phase 2E-H1 Lens 4).
- **Gate:** cross-navigation tests.

### R3-P1-06 — Fake provider step incorrect

- **Description:** The fake-provider workflow step behaves differently from the
  Phase 2B fake round-trip.
- **Impact:** Drift between workflow and standalone provider panel.
- **Mitigation:** The step reuses the exact Phase 2B fake provider path; test
  parity.
- **Gate:** provider-step tests.

### R3-P1-07 — Write-preview step writes unexpectedly

- **Description:** The write-preview step performs an actual write.
- **Impact:** Unauthorized write.
- **Mitigation:** Preview reuses `mode=write_preview`; only an explicitly
  approved execute step writes. Test that preview never writes.
- **Gate:** write-preview tests.

### R3-P1-08 — Rollback reference incorrect

- **Description:** A rollback-reference step points at the wrong manifest or
  fails to surface the rollback link.
- **Impact:** Operator cannot roll back.
- **Mitigation:** Reuse the Phase 2C-H1 rollback store; test the reference
  resolves.
- **Gate:** rollback-reference tests.

### R3-P1-09 — Console workflow UI unusable

- **Description:** The Workflow section breaks the console navigation /
  accessibility baseline.
- **Impact:** Operator cannot use the feature.
- **Mitigation:** Inherit the Phase 2E-H1 accessibility + no-leak closure;
  hardening tests.
- **Gate:** accessibility + no-leak hardening tests.

### R3-P1-10 — Smoke failure

- **Description:** A smoke profile fails or an existing profile regresses.
- **Impact:** Cannot verify the surface end-to-end.
- **Mitigation:** New additive profile + zero regression on existing profiles.
- **Blocking condition:** any smoke failure.

### R3-P1-11 — Preservation failure

- **Description:** A Phase 3 change regresses the Phase 1G/2 controlled-
  execution chain.
- **Impact:** Capability regression.
- **Mitigation:** Preservation suite must stay green.
- **Blocking condition:** any preservation failure.

---

## 3. P2 Risks (recorded, non-blocking)

### R3-P2-01 — Real provider integration deferred

- Deferred to Phase 3B after the workflow container exists.

### R3-P2-02 — Production pilot deferred

- Deferred to Phase 3D after real operator value exists.

### R3-P2-03 — Dynamic plugin registry deferred

- Deferred to Phase 3C after a capability / policy framework exists.

### R3-P2-04 — Workflow scheduling deferred

- No cron / scheduler / background autonomous agent in Phase 3A.

### R3-P2-05 — Multi-user workflow deferred

- Single-user dev namespace only in Phase 3A.

### R3-P2-06 — Advanced visual polish deferred

- Visual design system / motion polish is optional future work.

### R3-P2-07 — Full WCAG deferred

- Phase 3A inherits the Phase 2E-H1 practical accessibility baseline; full
  WCAG 2.1 AA remains deferred.

### R3-P2-08 — Audit compliance advanced deferred

- Encryption at rest / retention / compression / reporting deferred to Phase 3E.

### R3-P2-09 — Future Production Gateway PID drift

- Smoke harness fails closed; an authorized refresh phase updates the constant.

### R3-P2-10 — Token encryption at rest / multi-user token namespace deferred

- Inherited from Phase 2C-H1 residual risks.

---

## 4. Summary

| Tier | Count | Blocks Phase 3A? |
|------|-------|------------------|
| P0 | 14 | Each is a stop condition; none is introduced by this planning phase |
| P1 | 11 | Block push until resolved (during a future 3A execution phase) |
| P2 | 10 | Non-blocking; recorded for sequencing |

---

## 5. Cross-References

- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 1G-05 risk register](phase-1g-05-risk-register.md) (historical baseline)
