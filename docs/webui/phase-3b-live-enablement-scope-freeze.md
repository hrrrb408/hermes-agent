# Phase 3B-Live-Enablement — Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement Scope Freeze |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Frozen direction

Future live enablement **may only** be:

> **Strict Manual Real Provider Read-only Enablement**

The frozen invariants:

1. The real provider remains **disabled by default.**
2. Live enablement must be **explicitly authorized by a human operator.**
3. Live enablement must be **one-shot, short-window, and revocable.**
4. Live enablement runs **only** under the dev `HERMES_HOME`
   (`/Users/huangruibang/Code/hermes-home-dev`).
5. Live enablement is verified **only** in the controlled dev WebUI / dev gateway
   environment.
6. No production rollout.
7. No provider write.
8. No provider auto-write.
9. No provider rollback execute.
10. No autonomous write.
11. No shell / database / external-tool calls.
12. No Provider HTTP route and no new Tool write HTTP route.
13. No `~/.hermes` access; no production `state.db` access.
14. Only the read-only tool allowlist is permitted.
15. A budget cap is mandatory.
16. A rate limit is mandatory.
17. Request / response size limits are mandatory.
18. Audit is mandatory.
19. A kill switch is mandatory.
20. A rollback / disable procedure is mandatory.
21. A GO / NO-GO gate is mandatory.

## 2. What live enablement is NOT

- It is **not** automatic. It never self-enables.
- It is **not** persistent. Each window expires; renewal needs fresh approval.
- It is **not** broad. First live test = **one** request, non-streaming, no retry,
  no tool execution.
- It is **not** production-facing. It is dev-only and operator-witnessed.
- It is **not** a write path. Provider write / auto-write / rollback / autonomous
  write remain permanently blocked.

## 3. Boundary checks (to be enforced by the future implementation)

The future implementation must reject, with a precise blocked reason, any attempt
that:

- Lacks a valid, unexpired, in-scope human approval.
- Targets a host not on the approved network allowlist.
- Uses a non-`https://` scheme.
- Would exceed the approved budget / request / token / retry caps.
- Has the kill switch active.
- Is not dev-only (wrong `HERMES_HOME`, production path detected).
- Detects a secret in prompt / response / args / audit.
- Tries a write / rollback / shell / db / external / production tool.
- Would create a new route.

## 4. Frozen blocked-reason catalogue (live layer)

```
blocked_live_provider_not_human_approved
blocked_live_provider_approval_expired
blocked_live_provider_approval_scope_invalid
blocked_live_provider_budget_missing
blocked_live_provider_kill_switch_active
blocked_live_provider_dev_only_violation
blocked_live_provider_host_not_approved
blocked_live_provider_scheme_not_https
blocked_live_provider_redirect_not_allowed
blocked_live_provider_private_network_not_allowed
blocked_live_provider_response_fetch_not_allowed
blocked_live_provider_network_timeout
blocked_live_provider_response_too_large
blocked_live_provider_budget_not_configured
blocked_live_provider_budget_exceeded
blocked_live_provider_request_cap_exceeded
blocked_live_provider_token_cap_exceeded
blocked_live_provider_retry_not_allowed
blocked_live_provider_counter_unavailable
```

## 5. Relationship to existing boundary

This scope freeze is **additive** to the Phase 3B / Phase 3B-H1 boundary. It
introduces the **live layer** gating on top of the already-shipped disabled /
fake / real-gated modes. It does not relax any existing gate; it only adds
human-approval, kill-switch, and live-budget gates in front of the real-gated
path's concrete network call.

## 6. Cross-references

- [Phase 3B-Live-Enablement planning](phase-3b-live-enablement-planning.md)
- [Phase 3B-Live-Enablement human approval](phase-3b-live-enablement-human-approval.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)
