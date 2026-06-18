# Phase 3C-H1 — Permission Non-grant Hardening

| Field | Value |
|-------|-------|
| Lens | 3 — Capability Registry Non-grant / Permission Inheritance |
| Hardening ID | `CAP-PERMISSION-NON-GRANT-3C-H1-001` |
| Status | PASS |

## Scope

The registry describes capabilities; it never authorizes them. A
`permissionClass` is a label, not a runtime grant. The registry exposes no
execute/grant/enable/approve/confirm/dry-run/rollback function, imports no
execution surface, performs no side effect when its read API is used, and
changes no Tool policy / Provider live gate / Workflow approval.

## Evidence

- Registry `__all__` and every module's public callables contain no
  grant/execute verb (`execute`, `grant`, `enable`, `approve`, `confirm`,
  `issue_token`, `dry_run`, `rollback`, `dispatch`, `invoke`, `fetch`,
  `load_plugin`, `import_module`, …).
- No registry module imports an execution surface (`run_agent`, `toolsets`,
  `tools`, the provider-live / sandbox-write / workflow-runtime modules).
- Exercising the full read API against a temp dev home creates **no**
  side-effect artifact (no confirmation tokens, no rollback manifests, no
  audit events, no approvals, no capability-registry store).
- WRITE_CONFIRM / ROLLBACK_CONFIRM / LIVE_PROVIDER_GATED entries still declare
  every gate the real external path requires; the registry offers no function
  to satisfy them.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_permission_non_grant.py
```

## Fixes

Test-only. No implementation change.

## Residual risk

None.
