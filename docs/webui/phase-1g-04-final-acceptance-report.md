# Phase 1G-04 Final Acceptance Report

## Document Information

| Field | Value |
|-------|-------|
| Title | Phase 1G-04 — Tool Dry-Run / Controlled Execution — Final Acceptance Report |
| Scope | Phase 1G-04-20 → Phase 1G-04-31 (confirmation token → final sealing) |
| Status | Accepted — Phase 1G-04 WebUI mainline sealed |
| Date | 2026-06-13 |
| Branch | dev-huangruibang |
| Sealing commit | `docs(webui): seal phase 1g-04` (see Git log) |
| Pre-sealing baseline HEAD | `5d498fd7e09e2353ce0aa9d6a99444e59d388ef6` |

---

## 1. Purpose

This report is the consolidated acceptance for the Phase 1G-04 WebUI mainline.
It summarizes the controlled-execution capability chain built from
Phase 1G-04-20 (confirmation token) through Phase 1G-04-31 (final sealing),
states the final security boundaries, and records the final verification
results. It supersedes the per-phase "completed locally / not pushed" notes —
the entire chain is now committed and pushed.

---

## 2. Capability Summary (Phase 1G-04-20 → 1G-04-31)

| # | Capability | Phase(s) | Final State |
|---|-----------|----------|-------------|
| 1 | **Confirmation token** | 1G-04-18/19/20 | One-shot token issued by the dry-run endpoint; verified + consumed by the execute gate. Raw token never persisted / logged / rendered; only `confirmationTokenId` + expiry surfaced. |
| 2 | **Digest verification** | 1G-04-21/22 | `dryRunDecisionDigest` recomputed bound to the real audit `eventId` / timestamp / expiry; exact-match required (digest-binding fix in 1G-04-30 makes the real chain pass). |
| 3 | **Pre-execution audit** | 1G-04-23/24 | Pre-execution audit record written before any handler call. |
| 4 | **Handler lookup** | 1G-04-25/26 | Registered handler descriptor resolved for the canonical name. |
| 5 | **Dispatch planning** | 1G-04-27/28 | Side-effect-free dispatch envelope / plan built (still not a handler call or execution). |
| 6 | **Clarify-only handler call** | 1G-04-29 | Bounded safe clarify handler invoked only when the explicit handler-call gate is enabled and all prior gates pass. |
| 7 | **Post-execution audit** | 1G-04-29 | Post-execution audit written with provider / external side-effect flags (all false). |
| 8 | **Audit read API** | 1G-04-30 | `GET /api/dev/v1/tools/audit-events` (dry_run / pre_execution / post_execution) — read-only, redacted, whitelist-normalized. |
| 9 | **Execute UI** | 1G-04-30 | Clarify-only controlled-execution workbench (Tools → Execute / Audit sub-tabs). |
| 10 | **Audit viewer** | 1G-04-30 | Read-only audit events with kind switching / filter / refresh / empty state. |
| 11 | **Browser smoke / E2E** | 1G-04-30 | Both default-block (`blocked_tool_handler_call_not_enabled`) and completed (`clarify_execution_completed`) scenarios pass. |
| 12 | **Route governance** | 1G-04-30 | 33/33/4/0/1/1 → **34/34/5/0/1/1** (exactly one read-only GET added). |
| 13 | **Allowlist** | 1G-04-13/14 | `STATIC_ALLOWLIST = frozenset({"clarify"})` — unchanged throughout. |
| 14 | **Production safety** | all | Production Gateway PID `69355` unaffected; production `~/.hermes` / `state.db` untouched; dev-only `HERMES_HOME`; `127.0.0.1` only. |

### Execute route gate order (final)

```
kill switch → agent-tools switch → allowlist → dry-run historical lookup →
confirmation token (verify + consume) → digest verification →
pre-execution audit → handler lookup → dispatch planning →
handler-call enable gate → clarify-only handler call →
post-execution audit → safe response
```

With all kill switches unset (default), execute blocks at the first gate
(`blocked_by_kill_switch`). With kill switches on but the handler-call gate
unset, execute blocks at `blocked_tool_handler_call_not_enabled` (no handler
call, no execution). Only with the explicit handler-call gate enabled does the
clarify-only handler execute and return `clarify_execution_completed`.

---

## 3. Final Security Boundaries

| # | Boundary | Status |
|---|----------|--------|
| 1 | Only `clarify` is allowlisted | ✅ `STATIC_ALLOWLIST = frozenset({"clarify"})` |
| 2 | Non-clarify execution is disabled | ✅ no other tool can pass the allowlist gate |
| 3 | Provider Schema is not sent | ✅ `providerSchemaSent = false` everywhere |
| 4 | Provider API is not called | ✅ `providerApiCalled = false` everywhere |
| 5 | Tool write route count remains 0 | ✅ |
| 6 | Production `~/.hermes` is untouched | ✅ |
| 7 | Production `state.db` is untouched | ✅ |
| 8 | Audit JSONL is runtime-generated, not committed | ✅ lives under dev `HERMES_HOME/gateway/dev/audit/` only |
| 9 | `.claude/` remains untracked | ✅ never staged or committed |

### Data-exposure invariants

- Raw confirmation token: held in-memory only; never returned by the store,
  persisted to `localStorage`/`sessionStorage`, logged, rendered in the DOM, or
  written to audit.
- Full token hash: never surfaced; only a short digest and the token ID are
  exposed.
- Raw arguments: never reach the audit viewer (whitelist normalization).
- Secrets: defensively redacted; the audit reader rejects production paths.
- Callable / function repr: never exposed.

---

## 4. Route Governance (Final)

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |

Verified by `tests/test_dev_check_webui.py`, `tests/test_dev_web_0c06_closure.py`,
and `./scripts/run-dev-hermes.sh dev-check`.

---

## 5. Final Verification Results

### Backend

| Gate | Result |
|------|--------|
| Full related backend regression (19 files) | **1471 passed, 2 skipped, 5 deselected, 0 failed** |
| `compileall` (changed modules) | pass |
| `toolsets.py` compile | pass |
| `ruff check` (changed files) | all checks passed |
| `memory-check` | PASS |
| `dev-check` | WARN (only `Git worktree: dirty` from untracked `.claude/`) |

### Frontend

| Gate | Result |
|------|--------|
| `pnpm type-check` | pass |
| `pnpm lint` | pass (0 errors / 0 warnings) |
| `pnpm test` (vitest) | **674 passed (31 files), 0 failed** |
| `pnpm build` (vite) | pass |

### Browser smoke / E2E (phase-1g-04-30)

| Scenario | Result |
|----------|--------|
| Blocked (`blocked_tool_handler_call_not_enabled`) | **6 passed, 1 skipped, 0 failed** |
| Completed (`clarify_execution_completed`) | **7 passed, 0 failed** |

### Production / runtime

| Item | Result |
|------|--------|
| Production Gateway PID | `69355` before and after (unchanged) |
| Dev Gateway | stopped |
| Dashboard | not started |
| `5180` / `5181` | free before and after |
| Production `~/.hermes` / `state.db` | untouched |

---

## 6. P2 / Known Limitations (non-blocking)

1. **Stale `auditWritten=false` assumption** in the dormant
   `phase-1g-04-dry-run-api-safety-smoke.spec.ts`. The `auditWritten` field now
   reflects dry-run audit-event persistence (true under a configured
   `HERMES_HOME` since Phase 1G-04-06), not an execution side effect. The spec
   is not wired into any active smoke runner. Left as a historical stale test
   assumption rather than modified during the conservative sealing phase.
2. Audit pagination is offset-based; multi-file JSONL rotation / race handling
   is future local-dev work.
3. The audit read API caps total lines parsed per request at 1000; large-scale
   audit search / indexing is future work.
4. Non-clarify tools remain disabled (by design).
5. Provider integration is a permanent non-goal for this controlled path.
6. Frontend visual polish is optional / future.

---

## 7. Acceptance Conclusion

Phase 1G-04 WebUI mainline is **sealed**.

The full controlled-execution closeout for clarify-only dev execution is in
place end-to-end: dry-run, confirmation token, digest verification,
pre-execution audit, handler lookup, dispatch planning, clarify-only handler
call, post-execution audit, read-only audit events API, frontend Execute UI,
audit viewer, and browser smoke/E2E coverage.

Route governance is stable at OpenAPI paths 34 / runtime routes 34 / Tool GET 5
/ Tool write 0 / Tool dry-run 1 / Tool execution 1, and `STATIC_ALLOWLIST`
remains `frozenset({"clarify"})`.

No Provider Schema sending, Provider API call, non-clarify execution, Tool
write route, production home access, production state.db access, audit JSONL
commit, `.claude/` commit, raw token leak, full tokenHash leak, raw arguments
leak, secret leak, callable/function repr exposure, or route expansion beyond
the approved 34-route state was introduced.

The final sealing commit was pushed to `origin/dev-huangruibang`. Local and
remote are synchronized with `ahead / behind = 0 / 0`. Production Gateway PID
`69355` was not affected.

---

## 8. Post-Sealing Readiness (Phase 1G-05)

Phase 1G-04 sealed acceptance stands unchanged. The post-sealing readiness
package was added in **Phase 1G-05** (docs-only, no reopening of this report's
conclusions) and references this report as its sealed baseline:

- `docs/webui/phase-1g-05-post-sealing-readiness.md`
- `docs/webui/phase-1g-05-pilot-acceptance-baseline.md`
- `docs/webui/phase-1g-05-release-checklist.md`
- `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`
- `docs/webui/phase-1g-05-risk-register.md`

The §6 P2 list above is the source for the Phase 1G-05 risk register.

---

*Phase 1G-04 Final Acceptance Report — accepted and sealed.*
