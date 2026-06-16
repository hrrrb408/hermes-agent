# Phase 3B GO / NO-GO

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Phase 3B GO / NO-GO — Real Provider Read-only Integration Handoff Decision |
| Status | Decision recorded — Phase 3B implementation **complete** (see [phase-3b-real-provider-readonly-integration.md](phase-3b-real-provider-readonly-integration.md)); real provider remains **disabled by default** |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Decision ID | `PHASE-3B-GO-NOGO-001` |

---

## 1. Decision

| Field | Value |
|-------|-------|
| Decision | **GO** for Phase 3B Implementation prompt preparation only |
| Selected Phase 3B scope | Real Provider Read-only Controlled Integration |
| Phase 3B execution | not started |
| Human approval required before execution | yes |
| Phase 3B may start | only after the user explicitly asks for the prompt / implementation |
| Phase 3B may code | only inside `dev-huangruibang`, separately authorized |
| Real provider allowed in future implementation | yes, but **disabled by default** |
| Provider write allowed | **no** |
| Provider auto-write allowed | **no** |
| Autonomous write allowed | **no** |
| Production rollout allowed | **no** |
| Shell / DB / external-service write allowed | **no** |
| New HTTP route allowed (default) | **no** |
| API-key source | env only |
| UI API-key input | **no** |
| Audit required | **yes** |

---

## 2. Basis for Decision

- Phase 3A (Dev-only Agent Workflow MVP) is **implemented** and Phase 3A-H1
  (Workflow Hardening) is **complete** (11/11 lenses PASS, P0=0, P1=0). The
  workflow container that Phase 3B was sequenced behind now exists.
- Phase 2B / 2B-H1 built the provider boundary (schema projection, request
  envelope, fake adapter, blocked real adapter, audit, sanitizer) and left exactly
  one thing deferred: the concrete real-vendor call (`blocked_real_provider_not_wired_in_phase_2b`).
- Phase 2D / 2D-H1 hardened the durable audit store that Phase 3B's `provider_real_*`
  events will dual-write into.
- This planning phase froze the scope, the selection matrix (OpenAI-compatible
  generic boundary first), the API-key / secret strategy, the network boundary,
  the request / response schema, the audit model, the failure / timeout / retry
  policy, the cost / rate-limit policy, and the security risk register.
- All P0 risks are stop conditions (none introduced by this planning phase); P1
  risks are execution-phase push-gates; P2 risks are deferred sequencing.

---

## 3. What GO Authorizes

GO authorizes **preparing** the Phase 3B handoff only:

- Authoring the Phase 3B execution brief ([phase-3b-execution-brief.md](phase-3b-execution-brief.md)).
- Authoring the Phase 3B prompt draft ([phase-3b-prompt.md](phase-3b-prompt.md)).
- Committing and pushing this docs-only planning phase
  (`docs(webui): plan phase 3b provider integration`).

---

## 4. What GO Does Not Authorize

GO does **not** authorize:

- Starting Phase 3B implementation.
- Any product / frontend / backend / script change.
- Wiring or enabling a real provider call.
- Reading any API key.
- Making any external network call.
- Provider auto-write / auto-rollback.
- Autonomous write.
- Shell command / database mutation / external service write.
- Production rollout.
- `~/.hermes` or production `state.db` access.
- A new HTTP route, Tool write HTTP route, or Provider route.
- Stopping / restarting / replacing / signaling the Production Gateway.

---

## 5. Phase 3B Entry Gate

Phase 3B implementation may start only when **all** are true:

1. The user explicitly asks for the Phase 3B execution prompt / implementation.
2. Phase 3B is separately authorized by the user.
3. Branch = `dev-huangruibang`; tree clean (only `.claude/` untracked).
4. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) or an explicitly
   approved, separately-authorized change.
5. Production Gateway PID healthy (`28428`) or consciously refreshed by a
   separately authorized safety phase.
6. `~/.hermes` and production `state.db` not accessed.
7. `PHASE-3B-PLANNING-001` committed and pushed.
8. The Phase 3B prompt draft is the approved starting brief.

---

## 6. NO-GO Conditions

The decision becomes **NO-GO** (stop, do not push, do not proceed) if, during a
future Phase 3B execution:

- Phase 3B scope is violated (real provider enabled without authorization, API-key
  leak, secret in audit/log/UI, prompt-injection-driven disallowed call, arbitrary
  URL fetch, provider write / auto-write / autonomous execution, shell / db /
  external write, production rollout, route drift).
- The Production Gateway PID drifts from `28428` or count != `1`.
- Route governance drifts without an approved change.
- Any P0 risk materializes.
- Any P1 push-gate fails.

---

## 7. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
- [Phase 3B execution brief](phase-3b-execution-brief.md)
- [Phase 3B prompt draft](phase-3b-prompt.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
