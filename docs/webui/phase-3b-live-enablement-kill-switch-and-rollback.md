# Phase 3B-Live-Enablement — Kill Switch / Disable / Rollback Policy

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Kill Switch / Disable / Rollback |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Principle

A live provider session must be killable instantly, must disable cleanly, and
must return the boundary to its disabled-by-default state. Re-enabling requires a
fresh human approval.

> **This planning phase does not execute a live disable**, because live is not
> enabled. It freezes the procedure only.

## 2. Kill-switch triggers

The kill switch fires on **any** of:

1. Manual operator trigger.
2. Budget exceeded.
3. Rate limit exceeded.
4. Secret detected (in prompt / response / args / audit).
5. Response too large.
6. Provider returns a malformed or unsafe response.
7. Off-allowlist redirect.
8. Route governance drift.
9. Production Gateway PID drift (≠ `28428` or count ≠ `1`).
10. Audit write failure.
11. Unexpected provider tool-call.
12. Provider suggests a write / autonomous action.
13. Smoke failure.
14. Manual operator abort.

## 3. Kill-switch behavior

1. Set provider live mode to **disabled**.
2. Invalidate the live approval (revoke, do not reuse).
3. Block all future live requests.
4. Write `provider_live_enablement_kill_switch_triggered` (redacted).
5. Preserve no secret in the audit entry.
6. Surface a safe UI status (live disabled, reason shown without secrets).
7. Require a **fresh** approval to re-enable.

## 4. Rollback / disable procedure

The disable procedure returns the boundary to the disabled-by-default state:

1. `unset HERMES_PROVIDER_API_ENABLED`.
2. Set `HERMES_PROVIDER_MODE=disabled`.
3. Clear the live approval store.
4. Confirm the Provider Boundary UI shows disabled.
5. Run route governance (must remain 34 / 34 / 5 / 0 / 1 / 1).
6. Run the smoke `blocked-real` layer (must block).
7. Verify no live request is possible.
8. Verify the Production Gateway PID is unchanged (`28428`).
9. Document the result.

The future implementation must make this procedure idempotent and safe to run at
any time, including mid-request (best-effort abort of an in-flight call).

## 5. What rollback is NOT

- It is **not** a provider write / auto-write / data mutation. It only flips the
  live-enablement gates and clears the approval.
- It is **not** a production operation. It touches only the dev `HERMES_HOME`.
- It does **not** stop, restart, replace, or signal the Production Gateway.

## 6. Blocked reasons (kill-switch layer)

```
blocked_live_provider_kill_switch_active
blocked_live_provider_dev_only_violation
```

## 7. Cross-references

- [Phase 3B-Live-Enablement human approval](phase-3b-live-enablement-human-approval.md)
- [Phase 3B-Live-Enablement audit policy](phase-3b-live-enablement-audit-policy.md)
- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
