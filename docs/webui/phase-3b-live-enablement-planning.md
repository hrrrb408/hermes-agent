# Phase 3B-Live-Enablement Planning — Strict Manual Real Provider Enablement

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement Scope Freeze (Planning) |
| Status | Planning prepared — live enablement **not started**; real provider remains **disabled by default** |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Input HEAD | `4e6a8a49899a153993cd48252ff29e8b6c60e961` (`chore(webui): harden provider read-only boundary`) |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

> This is a **docs-only planning phase.** It freezes the scope, the human
> approval model, the secret-read policy, the network allowlist, the budget /
> rate-limit policy, the audit policy, the kill-switch / rollback policy, the
> smoke strategy, the risk register, and the GO / NO-GO for a **future,
> separately-authorized** live real-provider enablement. It does **not** enable a
> live provider, does **not** implement a real HTTP client wiring, does **not**
> read a real API key, and does **not** perform any external network call.

---

## 1. Goal

After Phase 3B (Real Provider Read-only Controlled Integration) and Phase 3B-H1
(Provider Boundary Hardening) shipped a disabled-by-default, read-only,
audited, redacted provider boundary, this planning phase freezes the **minimal
safe closed-loop** for a future **Strict Manual Real Provider Read-only
Enablement**:

- Human approval (single-use, short window, revocable).
- Secret-read boundary (env-only, value never leaves the backend process).
- Network allowlist (HTTPS, single allowlisted host, no redirect, no extra fetch).
- Budget / rate-limit caps (one request, capped tokens, capped cents, no retry).
- Read-only tool-call allowlist (unchanged from Phase 2A).
- Audit (redacted, dual-write, fail-closed).
- Kill switch / disable / rollback procedure.
- Smoke strategy (layered; live layer gated behind explicit human approval).
- Risk register and GO / NO-GO.

## 2. Non-goals (forbidden in this planning phase)

- Enabling a live real provider.
- Implementing a real HTTP client wiring.
- Reading a real API key (or checking whether one exists).
- Printing, committing, persisting, or rendering any API key.
- Any external network call.
- Any provider write, auto-write, rollback, or autonomous write.
- Any shell / database / external-HTTP tool.
- Any production rollout, `~/.hermes` access, or production `state.db` access.
- A new HTTP route, a Provider route, or a Tool write HTTP route.
- Any product / frontend / backend / script change.

This phase is **docs-only.** Only files under `docs/webui/` are added / updated.

## 3. Scope freeze

Future live enablement is frozen to **Strict Manual Real Provider Read-only
Enablement.** See [phase-3b-live-enablement-scope-freeze.md](phase-3b-live-enablement-scope-freeze.md).

## 4. Companion documents

| Topic | Document |
|-------|----------|
| Scope freeze | [phase-3b-live-enablement-scope-freeze.md](phase-3b-live-enablement-scope-freeze.md) |
| Human approval model | [phase-3b-live-enablement-human-approval.md](phase-3b-live-enablement-human-approval.md) |
| Secret-read policy | [phase-3b-live-enablement-secret-read-policy.md](phase-3b-live-enablement-secret-read-policy.md) |
| Network allowlist | [phase-3b-live-enablement-network-allowlist.md](phase-3b-live-enablement-network-allowlist.md) |
| Budget / rate-limit policy | [phase-3b-live-enablement-budget-policy.md](phase-3b-live-enablement-budget-policy.md) |
| Audit policy | [phase-3b-live-enablement-audit-policy.md](phase-3b-live-enablement-audit-policy.md) |
| Kill switch / rollback | [phase-3b-live-enablement-kill-switch-and-rollback.md](phase-3b-live-enablement-kill-switch-and-rollback.md) |
| Smoke strategy | [phase-3b-live-enablement-smoke-strategy.md](phase-3b-live-enablement-smoke-strategy.md) |
| Risk register | [phase-3b-live-enablement-risk-register.md](phase-3b-live-enablement-risk-register.md) |
| GO / NO-GO | [phase-3b-live-enablement-go-no-go.md](phase-3b-live-enablement-go-no-go.md) |
| Execution brief | [phase-3b-live-enablement-execution-brief.md](phase-3b-live-enablement-execution-brief.md) |
| Prompt draft | [phase-3b-live-enablement-prompt.md](phase-3b-live-enablement-prompt.md) |

## 5. GO / NO-GO summary

- **GO** for preparing the Phase 3B-Live-Enablement **implementation prompt only.**
- **NO-GO** for actual live provider enablement until the user explicitly authorizes.

See [phase-3b-live-enablement-go-no-go.md](phase-3b-live-enablement-go-no-go.md).

## 6. Production safety

Production Gateway PID `28428` was not stopped / restarted / replaced / signaled /
reconfigured. Dev services bind `127.0.0.1` only. No `~/.hermes` access; no
production `state.db` access. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).

## 7. Cross-references

- [Phase 3B real-provider read-only integration](phase-3b-real-provider-readonly-integration.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)
- [Phase 3B-H1 provider boundary hardening](phase-3b-h1-provider-boundary-hardening.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)
