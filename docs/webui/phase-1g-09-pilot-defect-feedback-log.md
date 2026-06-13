# Phase 1G-09: Pilot Defect / Feedback Log — `PILOT-EXEC-1G-09-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-09 |
| Title | Pilot Defect / Feedback Log |
| Status | Filled (Pilot executed) |
| Date | 2026-06-14 |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Template | `docs/webui/phase-1g-08-pilot-defect-feedback-template.md` |
| Scope | Defect / feedback log for the Pilot run. No code change. |

---

## 1. New Defects (this Pilot)

```text
No new P0 defects.
No new P1 defects.
No new P2 defects introduced by Phase 1G-09.
No Pilot-blocking feedback.
```

Phase 1G-09 executed the prepared Pilot acceptance pack against the sealed
Phase 1G-04 mainline. All 15 scenarios (A–O) passed under the two named
server-gate profiles. No safety-boundary violation, no route-governance change,
no allowlist expansion, no Provider Schema / API activity, no non-clarify
execution, no raw token / tokenHash / arguments / secret exposure, and no
production access occurred.

---

## 2. Carried-Over P2 (8)

The following P2 items are carried over from
`docs/webui/phase-1g-05-risk-register.md`. They are accepted, non-blocking
limitations; none was aggravated by Phase 1G-09 (docs + gate re-verification
only; no code touched).

| Risk ID | Title | Severity | Status |
|---------|-------|----------|--------|
| P2-01 | Stale `auditWritten=false` assumption in a dormant smoke spec | P2 | carried over |
| P2-02 | Offset-based audit pagination | P2 | carried over |
| P2-03 | Multi-file JSONL rotation not implemented | P2 | carried over |
| P2-04 | JSONL race handling not implemented | P2 | carried over |
| P2-05 | Non-clarify tools disabled by design | P2 (by-design) | carried over |
| P2-06 | Provider integration is a permanent non-goal | P2 (by-design) | carried over |
| P2-07 | Frontend visual polish optional | P2 | carried over |
| P2-08 | Large-scale audit search / indexing not implemented | P2 | carried over |

### P2-01 — stale dormant `auditWritten=false` assumption

- **Status:** Carried over. The dormant spec is not wired into any active smoke
  runner; Phase 1G-09 did not touch it.

### P2-02 — offset-based audit pagination

- **Status:** Carried over. Local-dev audit volume remains small; the read-only,
  redacted, whitelist-normalized offset path is correct and bounded.

### P2-03 — multi-file JSONL rotation not implemented

- **Status:** Carried over. Single-file append log remains adequate for
  local-dev volume; the safe reader still caps total lines parsed per request.

### P2-04 — JSONL race handling not implemented

- **Status:** Carried over. The local-dev execute path is low-concurrency
  (single-generation per session); the reader remains fail-safe (skips malformed
  lines).

### P2-05 — non-clarify tools disabled by design

- **Status:** Carried over and re-confirmed. `STATIC_ALLOWLIST =
  frozenset({"clarify"})`; dev-check "Static allowlist: clarify"; Scenario L
  PASS.

### P2-06 — Provider integration is a permanent non-goal

- **Status:** Carried over and re-confirmed. `providerSchemaSent=false` and
  `providerApiCalled=false` on both profiles; dev-check "Provider tool schema:
  not sent"; Scenarios J / K PASS.

### P2-07 — frontend visual polish optional

- **Status:** Carried over. No polish work bundled into Phase 1G-09.

### P2-08 — large-scale audit search / indexing not implemented

- **Status:** Carried over. The per-request parse cap remains a deliberate
  safety property for local-dev volumes.

---

## 3. Decision Impact

```text
P0 count:    0   (no Pilot-blocking violation)
P1 count:    0   (no unresolved Pilot blocker)
P2 count:    8   (carried over; accepted, non-blocking; none new)
```

- No P0 → the Pilot did **not** stop.
- No unresolved P1 → the Pilot is eligible for PASS.
- 8 carried-over P2 → recorded against the risk register; do **not** block.
- A Phase 1G-09 addendum is appended to
  `docs/webui/phase-1g-05-risk-register.md`.

---

## 4. Feedback Items

```text
Feedback items:
  - none.
```

No UX, documentation, operational, smoke-harness, audit-viewer, or
execution-flow feedback was raised during this Pilot execution. The committed
harness ran both profiles cleanly, printed the final summary, and self-cleaned.

---

## 5. Cross-References

- Risk register: `docs/webui/phase-1g-05-risk-register.md` (P2-01 … P2-08;
  Phase 1G-09 addendum appended).
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Per-scenario results: `docs/webui/phase-1g-09-pilot-acceptance-record.md`.
- Final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.

---

*Phase 1G-09 Pilot Defect / Feedback Log — `PILOT-EXEC-1G-09-001`. No new P0 /
P1 / P2; 8 carried-over P2 remain accepted and non-blocking. Phase 1G-04
remains sealed.*
