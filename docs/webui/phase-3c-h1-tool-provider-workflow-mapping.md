# Phase 3C-H1 — Tool / Provider / Workflow Mapping

| Field | Value |
|-------|-------|
| Lens | 5 / 6 / 7 — Tool / Sandbox / Rollback, Provider / Live Gate, Workflow / Approval |
| Hardening ID | `CAP-MAPPING-3C-H1-001` |
| Status | PASS |

## Scope

The exact permission-class / status mapping for every described tool, provider,
and workflow capability. A mapping regression (e.g. a forbidden provider write
re-classified as READ_ONLY) fails this test.

## Evidence (mapping invariants)

- Read-only tools (`clarify`, `tool_policy_read`, `route_governance_read`,
  `audit_events_read`, `dev_environment_read`, `release_status_read`) →
  `READ_ONLY`.
- Sandbox writes (`dev_sandbox_file_{write,append,patch}`) → `WRITE_CONFIRM`
  (dry-run + confirmation + audit); readback → `READ_ONLY`; rollback →
  `ROLLBACK_CONFIRM`.
- Provider fake / boundary / classification → `READ_ONLY`; real gated +
  manual one-shot → `LIVE_PROVIDER_GATED` (disabled, listed, not executed);
  `provider.write` / `auto_write` / `autonomous_action` / `tool_execution` →
  `ADMIN_FORBIDDEN` (permanently blocked).
- Workflow read-only steps → `READ_ONLY`; sandbox write preview →
  `WRITE_PREVIEW`; write/rollback → blocked until separately authorized;
  auto-advance / autonomous write / background schedule → `ADMIN_FORBIDDEN`.
- WRITE_CONFIRM / ROLLBACK_CONFIRM / LIVE_PROVIDER_GATED entries still declare
  every gate the external path requires (the registry never satisfies them).

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_tool_provider_workflow_mapping.py
```

## Fixes

Test-only. No implementation change.

## Residual risk

None.
