# Phase 1G Final Release Seal — `FINAL-SEAL-1G-11-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G (sealed) |
| Title | Phase 1G Final Release Seal |
| Status | Sealed |
| Seal Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Final Seal ID | `FINAL-SEAL-1G-11-001` |
| Phase 2 Unlock ID | `PHASE-2-UNLOCK-1G-11-001` |
| Seal baseline input HEAD | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| Authorizing Human Decision | `HUMAN-DECISION-1G-10B-001` (GO) |
| Scope | Consolidate Phase 1G into a single sealed release baseline and hand off to Phase 2. No code change. |

---

## 1. Phase 1G Timeline

| Phase | Name | Status |
|-------|------|--------|
| 1G-00 | Tool Execution Safety Framework scope & contract freeze | completed |
| 1G-01 | Tool inventory + static policy module | completed |
| 1G-02 | Tool policy read-only API / panel | completed |
| 1G-03 | Tool schema preview | closed (1G-03-01 … 1G-03-07) |
| 1G-04 | Tool call dry-run + controlled execution chain (1G-04-00 … 1G-04-31) | **SEALED** |
| 1G-05 | Post-sealing readiness & Pilot acceptance baseline | pushed |
| 1G-06 | Pilot release rehearsal / smoke harness hardening | pushed |
| 1G-07 | Release Candidate Dry Run (`RC-1G-07-001`, GO) | pushed |
| 1G-08 | Pilot acceptance preparation (`PILOT-1G-08-001`) | pushed |
| 1G-09 | Pilot acceptance execution (`PILOT-EXEC-1G-09-001`, PASS) | pushed |
| 1G-10 | Post-Pilot closeout / final release decision preparation | pushed |
| 1G-10A | Smoke harness PID baseline refresh (`69355` → `1962`) | pushed |
| 1G-10B | Human approver final decision (`HUMAN-DECISION-1G-10B-001`, GO) | pushed |
| 1G-11 | Final release seal & Phase 2 unlock | **SEALED / pushed** |

---

## 2. Phase 1G Final Commit Chain

The sealed Phase 1G release chain (most recent last):

```
1G-04-31 final webui sealing (SEALED)
  └── 1G-05 post-sealing readiness (da5c31a8c, pushed)
       └── 1G-06 pilot release rehearsal (311221e0d, pushed)
            └── 1G-07 release candidate dry run, RC-1G-07-001 GO (6f9176953, pushed)
                 └── 1G-08 pilot acceptance preparation (9812c069e, pushed)
                      └── 1G-09 pilot acceptance execution, PASS (cd7298416, pushed)
                           └── 1G-10 post-pilot closeout (56b571fec region)
                                └── 1G-10A smoke harness PID refresh (56b571fec, pushed)
                                     └── 1G-10B human approver final decision, GO (3c6ae479b, pushed)
                                          └── 1G-11 final release seal & Phase 2 unlock (this commit)
```

| Point | Commit |
|-------|--------|
| Phase 1G-04 sealed HEAD | `94f22f67b` |
| Phase 1G-10B human decision record (input to 1G-11) | `3c6ae479b` |
| Phase 1G-11 seal commit | this commit |
| Human approver reviewed HEAD | `56b571fec1f61b8d6554b1c4a0bf597576266bd1` |

---

## 3. Phase 1G Accepted Scope

Phase 1G delivered a **clarify-only controlled execution MVP** for the Dev
WebUI, on the dev instance only (`HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev`,
bind `127.0.0.1` only, production fail-closed).

Accepted scope:

- Read-only tool policy / schema inspection.
- `clarify` dry-run (no dispatch).
- Controlled execution chain: dry-run → confirmation token → digest verification
  → pre-execution audit → handler lookup → dispatch planning → **clarify-only**
  handler call → post-execution audit.
- Read-only, redacted, whitelist-normalized audit events API and Audit Viewer.
- Browser smoke / E2E harness with two gate profiles (blocked + completed).
- Release rehearsal, RC dry run, Pilot preparation, Pilot execution, and the
  human approver final decision.

---

## 4. Phase 1G Delivered Capabilities

| # | Capability | Delivered |
|---|------------|-----------|
| 1 | Dev WebUI loads (`127.0.0.1`, dev `HERMES_HOME`) | ✅ |
| 2 | Tools panel visible (read-only catalog) | ✅ |
| 3 | Tool policy / schema read-only inspection | ✅ |
| 4 | `clarify` dry-run | ✅ |
| 5 | Confirmation token (in-memory only) | ✅ |
| 6 | Digest verification | ✅ |
| 7 | Pre-execution audit | ✅ |
| 8 | Handler lookup | ✅ |
| 9 | Dispatch planning | ✅ |
| 10 | clarify-only handler call | ✅ |
| 11 | Post-execution audit | ✅ |
| 12 | Audit events read API | ✅ |
| 13 | Audit Viewer (redacted, whitelist-normalized) | ✅ |
| 14 | Browser smoke / E2E harness | ✅ |
| 15 | Release rehearsal / RC / Pilot PASS | ✅ |
| 16 | Pilot PASS (`PILOT-EXEC-1G-09-001`) | ✅ |
| 17 | Human approver GO (`HUMAN-DECISION-1G-10B-001`) | ✅ |
| 18 | Phase 2 unlock (`PHASE-2-UNLOCK-1G-11-001`) | ✅ |

---

## 5. Phase 1G Security Guarantees

| Guarantee | Held |
|-----------|------|
| `STATIC_ALLOWLIST` exactly `frozenset({"clarify"})` | ✅ |
| Raw confirmation token never in response / DOM / log / console / `localStorage` / `sessionStorage` / audit event | ✅ |
| Full `tokenHash` never surfaced | ✅ |
| Raw arguments never in the audit viewer | ✅ |
| Secrets / API keys / credentials never logged or committed | ✅ |
| Callable / function repr never exposed | ✅ |
| Audit JSONL never committed | ✅ |
| `.claude/` never committed | ✅ |
| `~/.hermes` never accessed | ✅ |
| Production `state.db` never accessed | ✅ |
| Force push / rebase / `git reset --hard` never attempted | ✅ |

---

## 6. Phase 1G Route Governance Baseline

| Metric | Sealed value |
|--------|--------------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

**Frozen.** This is the Phase 1G release contract.

---

## 7. Phase 1G Audit Capabilities

- Pre-execution audit record per controlled execution attempt.
- Post-execution audit record per controlled execution outcome.
- Append-only JSONL audit storage under the dev `HERMES_HOME` (read-only reader;
  production-path rejection; per-request parse cap; malformed-line skip).
- Read-only audit events API (`GET /api/dev/v1/tools/audit-events`).
- Frontend Audit Viewer: redacted, whitelist-normalized, no raw token / full
  `tokenHash` / raw arguments / callable repr.

---

## 8. Phase 1G Frontend Capabilities

- Three-column Dev WebUI workbench (session sidebar | chat | workspace).
- Tools panel: read-only catalog, policy, schema preview.
- Execute UI: clarify-only controlled execution workbench (default-block +
  explicit-completed gate profiles).
- Audit Viewer: redacted, whitelist-normalized audit events.
- Five frozen built-in themes render correctly across the shared component tree.

---

## 9. Phase 1G Pilot Result

| Field | Value |
|-------|-------|
| Pilot Result | **PASS** (`PILOT-EXEC-1G-09-001`) |
| Required scenarios | **15 / 15** (A–O) |
| P0 | 0 |
| P1 | 0 |
| Gate profiles | blocked (`blocked_tool_handler_call_not_enabled`) + completed (`clarify_execution_completed`) |
| `providerSchemaSent` | false (asserted) |
| `providerApiCalled` | false (asserted) |
| `externalSideEffects` | false (controlled-execution chain) |

---

## 10. Phase 1G Human Approval

| Field | Value |
|-------|-------|
| Human Decision ID | `HUMAN-DECISION-1G-10B-001` |
| Approver | 黄瑞邦 — Project Owner / Release Approver |
| Decision | **GO** |
| Decision Date | 2026-06-14 |
| Release authorization | **granted by the designated human approver** |
| Reviewed HEAD | `56b571fec1f61b8d6554b1c4a0bf597576266bd1` |
| P2-09 (sign-off dependency) | **resolved** |

---

## 11. Phase 1G Known P2

| ID | Summary | Blocks release? |
|----|---------|-----------------|
| P2-01 | Stale `auditWritten=false` assumption in a dormant smoke spec | no |
| P2-02 | Offset-based audit pagination | no |
| P2-03 | Multi-file JSONL rotation not implemented | no |
| P2-04 | JSONL race handling not implemented | no |
| P2-05 | Non-clarify tools disabled by design | no |
| P2-06 | Provider integration a permanent non-goal | no |
| P2-07 | Frontend visual polish optional | no |
| P2-08 | Large-scale audit search / indexing not implemented | no |
| P2-09 | Human approver sign-off dependency | **resolved** (`HUMAN-DECISION-1G-10B-001`) |

P2-01 … P2-08 are accepted, non-blocking, and carry forward into Phase 2.

---

## 12. Phase 1G Permanent Non-Goals

These are **permanent non-goals** for Phase 1G. They remain excluded even after
the GO decision:

- non-clarify tool execution;
- Provider Schema sending;
- Provider API calls;
- Tool write routes;
- a second Tool execution route;
- a Provider route;
- production `~/.hermes` access;
- production `state.db` access;
- public rollout to arbitrary endpoints (the WebUI binds to `127.0.0.1` only).

---

## 13. Phase 1G Not-Implemented Capabilities

Phase 1G did **not** implement the following. They are explicitly deferred:

1. production rollout — not performed;
2. non-clarify execution — not enabled;
3. Provider Schema — not sent;
4. Provider API — not called;
5. Tool write route — not added;
6. second execution route — not added;
7. production `~/.hermes` — not accessed;
8. production `state.db` — not accessed;
9. advanced audit pagination / search / rotation / race handling — not implemented;
10. frontend polish — not completed (functional; visual polish optional);
11. real multi-tool execution — not implemented (Phase 2A target).

---

## 14. Phase 1G Production Safety

| Check | Release-baseline value |
|-------|------------------------|
| Production Gateway process count | exactly 1 |
| Production Gateway PID | `1962` (Phase 1G-10A refreshed baseline) |
| Production Gateway command | `hermes_cli.main gateway run --replace` (identical) |
| Production Gateway stopped / restarted / replaced / reconfigured by Phase 1G | no |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Dev `HERMES_HOME` isolation | PASS |
| Production `~/.hermes` accessed | no |
| Production `state.db` accessed | no |

---

## 15. Phase 1G Final Seal Statement

**Phase 1G is SEALED.**

`FINAL-SEAL-1G-11-001` records the final seal of Phase 1G. The Phase 1G release
decision is **GO** (`HUMAN-DECISION-1G-10B-001`); release authorization is
granted by the designated human approver. The Phase 1G release baseline — route
governance 34 / 34 / 5 / 0 / 1 / 1, `STATIC_ALLOWLIST = frozenset({"clarify"})`,
the clarify-only controlled execution MVP, and the frozen security boundary —
is the contract every future phase must respect.

Phase 1G-11 did not perform a production rollout, did not modify production, did
not access `~/.hermes`, and did not access production `state.db`.

---

## 16. Phase 2 Handoff

Phase 2 is **unlocked** (`PHASE-2-UNLOCK-1G-11-001`). The recommended Phase 2
vertical-slice sequence:

| Phase | Target |
|-------|--------|
| 2A | Real Tool Execution MVP — read-only multi-tool execution |
| 2B | Provider Schema / API controlled integration |
| 2C | Tool write execution (stronger confirmation / rollback / sandbox) |
| 2D | Advanced audit storage / search / pagination / rotation |
| 2E | Frontend product workflow and operator polish |

Phase 2A is the recommended next phase. It is **separately authorized** —
Phase 1G-11 does not start Phase 2A implementation.

The required safety invariants carried forward into Phase 2 (each Phase 2 slice
must preserve these):

- `STATIC_ALLOWLIST` expansion requires a full per-tool audit before any
  addition;
- the controlled execution chain (dry-run → confirmation token → digest →
  pre-execution audit → handler lookup → dispatch → handler call →
  post-execution audit) is the template for any new execution surface;
- raw token / full `tokenHash` / raw arguments / secrets / callable repr are
  never exposed;
- production `~/.hermes` and production `state.db` are never accessed;
- the WebUI binds to `127.0.0.1` only;
- dev `HERMES_HOME` isolation is enforced (fail-closed).

---

## 17. Cross-References

- Phase 1G-11 seal & Phase 2 unlock:
  `docs/webui/phase-1g-11-final-release-seal-and-phase-2-unlock.md`.
- Phase 2 unlock plan: `docs/webui/phase-2-unlock-plan.md`.
- Phase 2A MVP plan: `docs/webui/phase-2a-real-tool-execution-mvp-plan.md`.
- Human approver final decision: `docs/webui/phase-1g-10b-human-approver-final-decision.md`.
- Phase 1G-04 final acceptance: `docs/webui/phase-1g-04-final-acceptance-report.md`.
- Phase 1G-04 final webui sealing: `docs/webui/phase-1g-04-31-final-webui-sealing.md`.
- Phase 1G-09 Pilot final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.
- Implementation plan: `docs/webui/phase-1-implementation-plan.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

*Phase 1G Final Release Seal — `FINAL-SEAL-1G-11-001`. Phase 1G is **SEALED**.
Release decision **GO**; release authorization granted by the designated human
approver under `HUMAN-DECISION-1G-10B-001`. The clarify-only controlled
execution MVP is the delivered capability. Production rollout was not performed.
Phase 2 is unlocked (`PHASE-2-UNLOCK-1G-11-001`) for separately authorized work.*
