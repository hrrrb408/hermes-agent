# Phase 3B-Live-Enablement Execution Brief — Strict Manual Real Provider Enablement

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement |
| Title | Strict Manual Real Provider Enablement (Execution Brief) |
| Status | Brief prepared — live enablement **not started** |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |
| Brief ID | `PHASE-3B-LIVE-ENABLEMENT-EXECUTION-BRIEF-001` |

> This brief is the one-page contract for a future, separately-authorized
> Phase 3B-Live-Enablement. **Live enablement is not started by this planning
> phase.** The full copy-paste prompt is
> [phase-3b-live-enablement-prompt.md](phase-3b-live-enablement-prompt.md).

---

## 1. Name

Strict Manual Real Provider Read-only Enablement.

## 2. Goal

Wire the **concrete real HTTP client** into the existing Phase 3B real-gated
provider path, behind a new **live layer**: a fresh, single-use, short-window,
revocable human approval; an empty-default network allowlist; a strict budget /
rate-limit cap; a kill switch; and redacted dual-write audit. The first live test
is **one** non-streaming request, no tool execution, no retry, ≤ 5 cents, with
immediate auto-disable afterward.

## 3. Scope (allowed, future)

- Live human-approval model (issue / validate / expire / revoke).
- Concrete real HTTP client wired into the **existing** real-gated path (no new
  route; reuses `mode`-branched `/tools/dry-run` + `/tools/execute`).
- Empty-default network allowlist with operator-approved HTTPS host.
- Live budget / rate-limit caps layered on the Phase 3B budget modules.
- Kill switch + disable / rollback procedure.
- `provider_live_*` audit events (dual-written; redacted; fail-closed).
- Smoke layers 0–5 (deterministic, injected mock) and the opt-in layer 6.

## 4. Non-goals (forbidden)

Provider write; provider auto-write; provider rollback execute; autonomous write;
shell / database / external-tool calls; streaming; multi-provider routing;
background tasks / cron; production rollout; `~/.hermes` access; production
`state.db` access; dynamic plugin loading; arbitrary-URL fetch; storing / logging
/ committing an API key; a new HTTP route / Provider route / Tool write route;
reading a real API key outside the live process local.

## 5. Inputs

- Baseline: `4e6a8a49899a153993cd48252ff29e8b6c60e961` (Phase 3B-H1).
- HERMES_HOME: `/Users/huangruibang/Code/hermes-home-dev`.
- Reused capabilities: Phase 3B real-gated boundary, Phase 2B-H1 redaction,
  Phase 2A read-only allowlist, Phase 2C-H1 confirmation model, Phase 2D durable
  audit store, Phase 3A workflow container.

## 6. Outputs

- A live-layer gate (human approval + kill switch + live budget) in front of the
  concrete real HTTP client.
- `provider_live_*` audit events dual-written to the Phase 2D store + dev JSONL.
- Live smoke layers 0–6 (layer 6 opt-in).
- Live-enablement closeout docs.

## 7. Human approval model

See [phase-3b-live-enablement-human-approval.md](phase-3b-live-enablement-human-approval.md).
First live test: 5-minute window, single-use, manual renewal.

## 8. Secret / network / budget

- Secret: env-only `OPENAI_API_KEY`; value never persisted/logged/audited/rendered.
- Network: HTTPS-only; `api.openai.com` (recommended initial); no redirect / fetch.
- Budget: 1 request, ≤ 1000 tokens (≤ 200 output), ≤ 5 cents, 0 retries, 60 s.

## 9. Audit / kill switch

- Audit: `provider_live_*` events, `redactionApplied=true`, dual-write, fail-closed.
- Kill switch: 14 trigger conditions; revokes approval; requires fresh approval to
  re-enable.

## 10. Risk gates

P0 stop conditions and P1 push-gates from
[phase-3b-live-enablement-risk-register.md](phase-3b-live-enablement-risk-register.md).

## 11. Commit message (this planning phase)

```
docs(webui): plan provider live enablement
```

The future live-enablement execution uses its own conventional commit, e.g.
`feat(webui): add live provider enablement layer`.

## 12. Final report format

A closeout report mirroring the Phase 3B / Phase 3B-H1 structure: scope, what
changed, what did not change, route governance, production safety, gates,
residual risks (P2), conclusion.

## 13. Live enablement must NOT start here

This brief is the contract for a future, separately-authorized phase. It does not
start live enablement. The copy-paste prompt lives at
[phase-3b-live-enablement-prompt.md](phase-3b-live-enablement-prompt.md).

## 14. Cross-references

- [Phase 3B-Live-Enablement planning](phase-3b-live-enablement-planning.md)
- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
- [Phase 3B-Live-Enablement prompt draft](phase-3b-live-enablement-prompt.md)
