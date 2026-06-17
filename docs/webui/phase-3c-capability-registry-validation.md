# Phase 3C — Capability Registry Validation (Implementation Reference)

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Module | `hermes_cli/dev_web_capability_registry.py` (+ `_policy.py`) |
| Status | Implemented |

`validate_manifest(entries)` returns a `ValidationReport`. Per-entry checks:

- forbidden field present → entry rejected outright (fail closed)
- required fields present; enums valid; capabilityId stable format
- boolean flags are booleans; first-version invariants (devOnly, productionAllowed)
- blocked ⇒ blockedReason; unknown field rejected
- policy composition (`check_capability_policy`): forbidden classes
  non-executable; enabled requires verified trust + non-forbidden class;
  WRITE_CONFIRM/ROLLBACK_CONFIRM/LIVE_PROVIDER_GATED gate coherence;
  READ_ONLY no write-gate

Cross-entry: `capabilityId` uniqueness.

Fail-closed read model: invalid manifest → summary `status=validation_failed`;
invalid entry in detail list → reduced to a blocked record.

Events emitted via the audit bridge:
`capability_registry_validation_passed` / `capability_registry_validation_failed`
/ `capability_registry_manifest_rejected`.
