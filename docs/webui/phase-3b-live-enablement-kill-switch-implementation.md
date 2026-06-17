# Phase 3B-Live-Enablement — Kill Switch / Disable Implementation

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Module | `hermes_cli/dev_web_provider_live_kill_switch.py` |
| Tests | `tests/test_dev_web_phase_3b_live_kill_switch.py` |
| Date | 2026-06-17 |

Implements the frozen [kill switch / rollback policy](phase-3b-live-enablement-kill-switch-and-rollback.md).

## 1. State

`KillSwitchState` is value-free:

```
active, triggeredBy (a KILL_SWITCH_TRIGGER_* reason | ""), triggeredAt
```

Inactive by default. The store lives under
`$HERMES_HOME/gateway/dev/provider-live-kill-switch/kill-switch.json` (atomic,
dev-only, never carries a secret, never committed).

## 2. Frozen trigger reasons (14)

```
manual_operator_trigger            budget_exceeded
rate_limit_exceeded                secret_detected
response_too_large                 malformed_unsafe_response
off_allowlist_redirect             route_governance_drift
production_gateway_pid_drift       audit_write_failure
unexpected_provider_tool_call      provider_write_autonomous_suggestion
smoke_failure                      manual_abort
```

## 3. Behavior

`trigger_kill_switch(reason, now_iso)` arms the switch (an unknown reason
normalizes to `manual_operator_trigger`). When active, the orchestrator blocks
all live requests with `blocked_live_provider_kill_switch_active`, **before**
the secret read and **before** any network call, and emits
`provider_live_enablement_kill_switch_triggered` (redacted).

`clear_kill_switch` returns the switch to inactive. **Clearing is not an
approval** — re-enabling a live request still requires a fresh human approval.

## 4. Fail-open read, fail-closed write

A corrupt / missing store reads as inactive (the live path is still gated by
the approval + budget + network + secret layers), while triggering uses a
fail-closed atomic write (returns `False` on any I/O failure). The production
home is always rejected.

## 5. Disable / rollback procedure

1. arm the kill switch (or it arms on any trigger),
2. `revoke_all_approvals`,
3. `reset_live_counters`,
4. clear the kill switch (re-enable still needs a fresh approval),
5. confirm the boundary UI shows disabled,
6. re-assert route governance (34 / 34 / 5 / 0 / 1 / 1) + the blocked-real
   smoke layer + Production Gateway PID `28428` unchanged.

## 6. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Approval implementation](phase-3b-live-enablement-approval-implementation.md)
