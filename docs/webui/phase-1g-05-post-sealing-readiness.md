# Phase 1G-05: Post-Sealing Readiness

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-05 |
| Title | Post-Sealing Readiness — Pilot / Release Entry Baseline |
| Status | Completed locally (not pushed) |
| Date | 2026-06-13 |
| Branch | `dev-huangruibang` |
| Base commit | `94f22f67b14f4a076965e381beb707aecf5c726c` (Phase 1G-04-31 final sealing) |
| Scope | Documentation, acceptance baseline, release checklist, ops runbook, risk register. No code, no route, no allowlist change. |
| Author | Dev Agent (Phase 1G-05 post-sealing readiness) |

---

## 1. Phase Definition

Phase 1G-05 is an **independent post-sealing phase** that runs *after* the
Phase 1G-04 WebUI mainline was sealed at `94f22f67b`.

Phase 1G-05 does **not** reopen Phase 1G-04. It does **not** add functionality.
It prepares Pilot / release readiness only:

1. Re-confirm the Phase 1G-04 sealed baseline.
2. Establish a Pilot acceptance baseline.
3. Establish a release checklist.
4. Establish ops / rollback / troubleshooting documentation.
5. Establish a P2 risk register.
6. Record follow-on phase recommendations.
7. Run the final smoke / regression gates to confirm the sealed state did not regress.
8. Create a single local docs commit.
9. Do **not** push.
10. Do **not** start Phase 1G-06.

> **Hard separation:** Phase 1G-04 is sealed. No new functionality is backfilled
> into Phase 1G-04 from this phase. This phase only produces productionization
> checks, the Pilot acceptance baseline, the release checklist, ops notes, the
> risk register, and lightweight P2 documentation.

---

## 2. Phase 1G-04 Sealed Baseline

| Item | Value |
|------|-------|
| Phase 1G-04 status | **SEALED** |
| Sealing commit | `docs(webui): seal phase 1g-04` → `94f22f67b` |
| Local HEAD | `94f22f67b14f4a076965e381beb707aecf5c726c` |
| Remote HEAD | `94f22f67b14f4a076965e381beb707aecf5c726c` |
| Merge base | `94f22f67b14f4a076965e381beb707aecf5c726c` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |
| Dev `HERMES_HOME` | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway baseline PID | `69355` |

The sealed mainline delivers the full clarify-only controlled-execution chain:
dry-run historical lookup → confirmation token → digest verification →
pre-execution audit → handler lookup → dispatch planning → clarify-only handler
call → post-execution audit → read-only audit events API → frontend Execute UI
→ audit viewer → browser smoke / E2E. See
`docs/webui/phase-1g-04-final-acceptance-report.md` and
`docs/webui/phase-1g-04-31-final-webui-sealing.md`.

---

## 3. Current Route Governance

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

Verified by `tests/test_dev_check_webui.py`, `tests/test_dev_web_0c06_closure.py`,
and `./scripts/run-dev-hermes.sh dev-check`. Exactly one read-only GET route
(`/tools/audit-events`) was added during the Phase 1G-04-30 closeout. No Tool
write route, no second execution route, no Provider route exists.

### 3.1 Current Allowlist

`STATIC_ALLOWLIST` is defined at
`hermes_cli/dev_web_tool_policy.py:1019` as
`frozenset({"clarify"})` and is re-validated at lines 1100 and 1537. It is the
sole permission boundary for the execute route. Handler existence, handler
lookup, and dispatch plans are **necessary but not sufficient** — none of them
is permission. Only membership in `STATIC_ALLOWLIST` grants execution eligibility.

Phase 1G-05 changes **nothing** about the allowlist. It remains exactly
`frozenset({"clarify"})`. No wildcard allowlist, category allowlist, risk-tier
allowlist, dynamic / env / config allowlist, or allowlist expansion of any kind
is introduced.

---

## 4. Current Controlled-Execution Chain

The execute route (`POST /api/dev/v1/tools/execute`) enforces gates in this
fixed order:

```
kill switch (HERMES_TOOL_EXECUTION_ENABLED)
  → agent-tools switch (HERMES_AGENT_TOOLS_ENABLED)
  → STATIC_ALLOWLIST membership (canonical name must be "clarify")
  → dry-run historical lookup (dryRunRequestId + dryRunDecisionDigest binding)
  → confirmation token (verify + one-shot consume)
  → digest verification (recompute, exact match, bound to real eventId/timestamp/expiry)
  → pre-execution audit (write before any handler call)
  → handler lookup (resolve safe handler descriptor)
  → dispatch planning (side-effect-free dispatch envelope/plan)
  → handler-call enable gate (HERMES_TOOL_HANDLER_CALL_ENABLED)
  → clarify-only handler call
  → post-execution audit (provider / external side-effect flags, all false)
  → safe normalized response
```

Supporting read surface: `GET /api/dev/v1/tools/audit-events` returns redacted,
whitelist-normalized audit items for `dry_run` / `pre_execution` / `post_execution`
kinds. The audit JSONL reader
(`hermes_cli/dev_web_tool_audit_read.py`) enforces production-path containment
and per-kind normalization.

---

## 5. Default Safe Behavior

With the kill switches unset (the shipping default):

```
HERMES_TOOL_HANDLER_CALL_ENABLED  unset
HERMES_TOOL_EXECUTION_ENABLED     unset
HERMES_AGENT_TOOLS_ENABLED        unset
```

→ the execute route blocks before any handler call.

- With kill switches unset, execute returns `blocked_by_kill_switch`.
- With kill switches on but `HERMES_TOOL_HANDLER_CALL_ENABLED` unset, execute
  returns `blocked_tool_handler_call_not_enabled` — **no handler call, no
  execution, no side effect**. A pre-execution audit record is written (the
  attempt is durable), but no post-execution audit exists because no execution
  happened.

This is the production-safe posture: execution is blocked by default.

---

## 6. Explicit Dev/Test Gate Behavior

With the explicit dev/test gate set:

```
HERMES_TOOL_EXECUTION_ENABLED=true
HERMES_AGENT_TOOLS_ENABLED=true
HERMES_TOOL_HANDLER_CALL_ENABLED=true
+ canonicalName="clarify"
+ all prior gates pass
```

→ the bounded safe clarify handler is invoked:

- A safe result is normalized.
- A post-execution audit record is written (provider / external side-effect
  flags all `false`).
- A safe controlled-execution response is returned with decision
  `clarify_execution_completed`, surfacing `handlerCallId` and
  `postExecutionAuditId`.
- The audit viewer can display the post-execution audit event.

This is the **only** path that performs a real handler call, and it is bounded
to `clarify`. No other canonical name can pass the allowlist gate.

---

## 7. Post-Sealing Readiness Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Phase 1G-04 sealing commit present (`94f22f67b`) | ✅ |
| 2 | Local HEAD == remote HEAD, ahead/behind = 0/0 | ✅ |
| 3 | Tracked worktree clean (only `.claude/` untracked) | ✅ |
| 4 | Route governance = 34 / 34 / 5 / 0 / 1 / 1 | ✅ |
| 5 | `STATIC_ALLOWLIST = frozenset({"clarify"})` | ✅ |
| 6 | No allowlist expansion | ✅ |
| 7 | No Provider Schema / Provider API | ✅ |
| 8 | No non-clarify execution | ✅ |
| 9 | No Tool write route | ✅ |
| 10 | No new route | ✅ |
| 11 | Default safe behavior (execute blocked by default) | ✅ |
| 12 | Explicit dev/test clarify execution works | ✅ |
| 13 | Pilot acceptance baseline authored | ✅ (see doc 2) |
| 14 | Release checklist authored | ✅ (see doc 3) |
| 15 | Ops / rollback runbook authored | ✅ (see doc 4) |
| 16 | P2 risk register authored | ✅ (see doc 5) |
| 17 | Implementation plan records Phase 1G-05 | ✅ (see doc update) |
| 18 | Final regression / smoke / gates re-run, 0 failed | ✅ |
| 19 | Production Gateway PID `69355` unaffected | ✅ |
| 20 | Single local docs commit created, **not pushed** | ✅ |

---

## 8. Invariants Checklist

These invariants must hold throughout Phase 1G-05 and beyond:

1. `STATIC_ALLOWLIST` is exactly `frozenset({"clarify"})`.
2. Route governance stays at OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write 0 / Tool dry-run 1 / Tool execution 1.
3. Execution is blocked by default; only the explicit dev/test gate enables clarify.
4. No Provider Schema is ever sent; no Provider API is ever called
   (`providerSchemaSent=false`, `providerApiCalled=false` everywhere).
5. No non-clarify tool can execute.
6. The raw confirmation token never leaves an in-memory, non-reactive closure
   (never persisted, logged, rendered, or audited).
7. Only a short digest and the token ID are surfaced — never the full token hash.
8. Raw arguments never reach the audit viewer (whitelist normalization).
9. Secrets are defensively redacted; the audit reader rejects production paths.
10. Callable / function repr is never exposed.
11. Audit JSONL is runtime-generated under dev `HERMES_HOME` only — never committed.
12. `.claude/` is never staged or committed.
13. Production `~/.hermes` and production `state.db` are never touched.
14. Production Gateway PID `69355` is never stopped, restarted, replaced, or reconfigured.
15. No force push, force-with-lease, rebase, or merge is used.

---

## 9. Follow-On Phase Entry Points

Phase 1G-05 establishes the entry baseline for the *next* work. Candidate
follow-on phases (each must be separately approved; **none is started by
Phase 1G-05**):

- **Pilot** — run the Pilot acceptance baseline
  (`docs/webui/phase-1g-05-pilot-acceptance-baseline.md`) against the sealed
  mainline. No code change required; the sealed build is the Pilot candidate.
- **Polish (optional)** — frontend visual polish and accessibility pass (P2,
  non-blocking). See the risk register.
- **Audit hardening (optional)** — multi-file JSONL rotation, offset pagination
  improvements, and large-scale audit search / indexing (P2, future local-dev
  work). See the risk register.
- **Phase 1G-06** — explicitly **not started** by this phase. Its scope, if any,
  must be defined and approved separately.

---

## 10. Non-Reopening Declaration

> **Phase 1G-05 does not reopen Phase 1G-04.**
> **Phase 1G-05 prepares Pilot / release readiness only.**

Phase 1G-04 WebUI mainline functionality is sealed. No Phase 1G-04 route,
allowlist, execute gate, audit behavior, frontend capability, or test strength
is changed, weakened, or expanded by Phase 1G-05. The only deliverables of this
phase are documentation, the Pilot acceptance baseline, the release checklist,
the ops / rollback runbook, the risk register, and a final re-verification pass.

If a P0 / P1 regression is discovered during the final re-verification, work
stops and the regression is reported separately — it is **not** silently folded
back into Phase 1G-04 and it is **not** fixed inside this phase without an
explicit, documented scope decision.

---

*Phase 1G-05 Post-Sealing Readiness — sealed baseline re-confirmed, Pilot /
release entry baseline established. Phase 1G-04 remains sealed.*
