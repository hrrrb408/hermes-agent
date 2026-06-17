# Phase 3B-Live-Enablement — Live Approval Implementation

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Module | `hermes_cli/dev_web_provider_live_approval.py` |
| Tests | `tests/test_dev_web_phase_3b_live_approval.py` |
| Date | 2026-06-17 |

Implements the frozen [human-approval model](phase-3b-live-enablement-human-approval.md).

## 1. Approval record (`LiveApproval`)

Value-free, frozen dataclass:

```
approvalId, approvalScope = provider_live_enablement, providerName, providerMode = real,
model, baseUrlHost, budgetCapCents, requestCap, tokenCap, outputTokenCap,
toolAllowlist, expiresAt, createdAt, approvedBy = human_operator,
singleUse = true, usedAt, redactionApplied = true
```

Forbidden fields (never present): API key, Authorization header, bearer token,
raw prompt, raw response, production path.

## 2. Lifetime

| Field | Value |
|-------|-------|
| Window (TTL) | 5 minutes (`DEFAULT_TTL_SECONDS = 300`) |
| Reuse | single-use (`singleUse = true`) |
| Renewal | manual; a fresh approval is required per request |

`issue_live_approval(...)` writes an atomic, append-style record. The store
lives under `$HERMES_HOME/gateway/dev/provider-live-approvals/approvals.json`,
is gitignored, never carries a secret, and is never committed. A single in-flight
approval is permitted at a time.

## 3. Validation order

1. `None` approval → `blocked_live_provider_not_human_approved`
2. scope ≠ `provider_live_enablement` → `blocked_live_provider_approval_scope_invalid`
3. providerMode ≠ `real` → `blocked_live_provider_approval_scope_invalid`
4. now > `expiresAt` → `blocked_live_provider_approval_expired`
5. `singleUse` + `usedAt` set → `blocked_live_provider_approval_used`

`match_live_approval(...)` rejects provider / model / host / tool-allowlist
mismatch with `blocked_live_provider_approval_mismatch`.

## 4. Single-use invalidation

`mark_approval_used(approval_id, ...)` sets `usedAt` exactly once. A second call
is a no-op. After a completed live request the orchestrator invalidates the
approval immediately (`approval_invalidated = true`).

## 5. Dev-only store (fail closed)

`_resolve_store_path` rejects the production home (`/Users/huangruibang/.hermes`),
a missing `HERMES_HOME`, a path escaping the home, and any `state.db` path. On
any rejection the store returns no approval and issuing returns `None`
(fail closed — no approval is granted). `revoke_all_approvals` clears the store
for the disable / rollback procedure.

## 6. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Kill switch implementation](phase-3b-live-enablement-kill-switch-implementation.md)
