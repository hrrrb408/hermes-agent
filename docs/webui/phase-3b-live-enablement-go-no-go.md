# Phase 3B-Live-Enablement — GO / NO-GO

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — GO / NO-GO |
| Status | Decision recorded — live enablement **not started**; real provider remains **disabled by default** |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |
| Decision ID | `PHASE-3B-LIVE-ENABLEMENT-GO-NOGO-001` |

## 1. Decision

| Field | Value |
|-------|-------|
| Decision | **GO** for preparing the Phase 3B-Live-Enablement **implementation prompt only** |
| Live provider may start now | **no** (not in planning) |
| Real API key may be read now | **no** |
| Real network may be called now | **no** |
| Implementation prompt may be prepared | **yes** |
| Production rollout | **no** |
| Provider write | **no** |
| Provider auto-write | **no** |
| Autonomous write | **no** |
| Human approval required (future) | **yes** |
| Budget cap required (future) | **yes** |
| Kill switch required (future) | **yes** |

## 2. Basis

- Phase 3B shipped a disabled-by-default, read-only, audited, redacted provider
  boundary; Phase 3B-H1 hardened it (10/10 lenses PASS, P0=0, P1=0).
- The real HTTP client is **not** wired into the live request path; tests / smoke
  use an injected `MockHttpClient`; no real key is read; no real network call
  occurs.
- This planning phase freezes the minimal safe closed-loop for a future,
  separately-authorized live enablement without enabling it.

## 3. What GO authorizes

GO authorizes **preparing** the live-enablement handoff only:

- Authoring the execution brief
  ([phase-3b-live-enablement-execution-brief.md](phase-3b-live-enablement-execution-brief.md)).
- Authoring the prompt draft
  ([phase-3b-live-enablement-prompt.md](phase-3b-live-enablement-prompt.md)).
- Committing and pushing this docs-only planning phase
  (`docs(webui): plan provider live enablement`).

## 4. What GO does NOT authorize

- Starting live enablement or wiring a real HTTP client.
- Any product / frontend / backend / script change.
- Reading any API key (or checking whether one exists).
- Any external network call.
- Provider write / auto-write / rollback / autonomous write / shell / db /
  external write.
- Production rollout; `~/.hermes` or production `state.db` access.
- A new HTTP route, Provider route, or Tool write HTTP route.
- Stopping / restarting / replacing / signaling the Production Gateway.

## 5. Live enablement entry gate (future)

Live enablement may start only when **all** are true:

1. The user explicitly asks for the live-enablement implementation.
2. Live enablement is separately authorized by the user.
3. Branch = `dev-huangruibang`; tree clean (only `.claude/` untracked).
4. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
5. Production Gateway PID healthy (`28428`) or consciously refreshed by a
   separately authorized safety phase.
6. `~/.hermes` and production `state.db` not accessed.
7. `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` committed and pushed.
8. The live-enablement prompt draft is the approved starting brief.
9. The human approval model, secret-read policy, network allowlist, budget policy,
   audit policy, kill switch, and smoke strategy are all satisfied at runtime.

## 6. NO-GO conditions

The decision becomes **NO-GO** (stop, do not push, do not proceed) if, during a
future live enablement:

- Live scope is violated (live enabled without authorization, API-key leak,
  secret in audit/log/UI, arbitrary-URL fetch, off-allowlist redirect, provider
  write / auto-write / autonomous execution, shell / db / external write,
  production rollout, route drift).
- The Production Gateway PID drifts from `28428` or count ≠ `1`.
- Route governance drifts without an approved change.
- Any P0 risk materializes.
- Any P1 push-gate fails.

## 7. Cross-references

- [Phase 3B-Live-Enablement planning](phase-3b-live-enablement-planning.md)
- [Phase 3B-Live-Enablement risk register](phase-3b-live-enablement-risk-register.md)
- [Phase 3B-Live-Enablement execution brief](phase-3b-live-enablement-execution-brief.md)
- [Phase 3B-Live-Enablement prompt draft](phase-3b-live-enablement-prompt.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)
