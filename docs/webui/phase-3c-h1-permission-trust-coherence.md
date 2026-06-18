# Phase 3C-H1 — Permission / Trust / Status Coherence

| Field | Value |
|-------|-------|
| Lens | 4 — PermissionClass / TrustLevel / Status Coherence |
| Hardening ID | `CAP-PERMISSION-TRUST-3C-H1-001` |
| Status | PASS |

## Scope

The frozen composition rules between `permissionClass`, `trustLevel`,
`status`, and the runtime gate flags must hold — no described capability can
be inconsistent.

## Evidence (rules hardened)

- `enabled` requires `trustLevel ∈ {BUILTIN_VERIFIED, DEV_STATIC_MANIFEST}`
  and a non-forbidden permission class.
- Forbidden trust/permission classes are always `disabled`/`blocked`.
- `EXPERIMENTAL_DISABLED` cannot be `enabled`.
- `WRITE_CONFIRM` ⇒ dry-run + confirmation + audit.
- `ROLLBACK_CONFIRM` ⇒ confirmation + audit.
- `LIVE_PROVIDER_GATED` ⇒ approval + budget + kill switch + audit.
- `READ_ONLY` cannot declare `confirmed_execute` / `manual_live`.
- `blocked` requires a `blockedReason`.
- Every first-version capability: `devOnly = true`, `productionAllowed = false`.
- The static manifest validates clean and partitions consistently.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_permission_trust_coherence.py
```

## Fixes

Test-only. No implementation change.

## Residual risk

None.
