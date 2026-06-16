# Phase 3B-Live-Enablement — Human Approval Model

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Human Approval Model |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Principle

Live enablement is **never automatic.** Every live request requires a fresh,
explicit, in-scope human approval. No approval → fail closed.

## 2. Pre-approval conditions (all must hold)

Before a live approval may be issued, the operator must explicitly confirm:

1. The user has explicitly requested entering live enablement.
2. The provider name is explicitly chosen.
3. The API key is **env-only** (no UI input, no file read).
4. The budget cap is explicitly confirmed.
5. The model is explicitly confirmed.
6. The base-URL host allowlist is explicitly confirmed.
7. The read-only tool allowlist is explicitly confirmed.
8. There will be **no** production rollout.
9. There will be **no** provider write.
10. There will be **no** autonomous write.
11. The kill switch can be triggered at any time.
12. The execution window is explicitly confirmed.

## 3. Approval record — required fields

```
approvalId
approvalScope = provider_live_enablement
providerName
providerMode = real
model
baseUrlHost
budgetCap
requestCap
tokenCap
toolAllowlist
expiresAt
approvedBy = human_operator
auditRequired = true
```

## 4. Approval record — forbidden fields

The approval record must **never** contain:

```
API key
Authorization header
raw bearer token
raw provider prompt with secrets
raw provider response
production path
```

## 5. Approval lifetime

Recommended defaults for the **first** live test:

| Field | Value |
|-------|-------|
| Window | 5 minutes |
| Reuse | single-use for the first request |
| Renewal | manual; a fresh approval is required for each additional request |

Once `expiresAt` passes, the approval is invalid; any in-flight or new request
fails with `blocked_live_provider_approval_expired`.

## 6. Blocked reasons (approval layer)

```
blocked_live_provider_not_human_approved
blocked_live_provider_approval_expired
blocked_live_provider_approval_scope_invalid
```

`approvalScope` mismatch (e.g. an approval issued for `provider_live_enablement`
being used for any other scope, or a `providerName` / `model` / `baseUrlHost` /
`toolAllowlist` mismatch) yields `blocked_live_provider_approval_scope_invalid`.

## 7. Revocation

- An approval is revoked when the kill switch fires (see
  [phase-3b-live-enablement-kill-switch-and-rollback.md](phase-3b-live-enablement-kill-switch-and-rollback.md)).
- An approval is revoked when it expires.
- Revocation is recorded with `provider_live_enablement_expired` or
  `provider_live_enablement_kill_switch_triggered`.
- Re-enabling requires a **fresh** approval (never reuse a revoked one).

## 8. Audit

Approval issuance and revocation are audited via
`provider_live_enablement_approved` / `..._denied` / `..._expired`, with
`redactionApplied=true` and only the safe fields above. See
[phase-3b-live-enablement-audit-policy.md](phase-3b-live-enablement-audit-policy.md).

## 9. Cross-references

- [Phase 3B-Live-Enablement scope freeze](phase-3b-live-enablement-scope-freeze.md)
- [Phase 3B-Live-Enablement kill switch](phase-3b-live-enablement-kill-switch-and-rollback.md)
- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
