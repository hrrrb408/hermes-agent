# Phase 3C-H1 — Audit No-leak Hardening

| Field | Value |
|-------|-------|
| Lens | 9 — capability_registry_* Audit / Redaction / No-leak |
| Hardening ID | `CAP-AUDIT-3C-H1-001` |
| Status | PASS |

## Scope

All 10 frozen `capability_registry_*` event types must be writable, must carry
`redactionApplied = True`, and must never persist a forbidden field — even when
the caller smuggles one through `safe_metadata` or as a non-JSON value. Audit
failure never enables the registry, and the production home is refused.

## Evidence

- Exactly 10 event types; the safe-payload field set is frozen and excludes
  every secret shape (`apiKey`, `Authorization`, `secret`, `tokenHash`,
  `rawPrompt`, `callable`, `shellCommand`, `sqlStatement`, `productionPath`,
  `pythonImportPath`).
- `redact_capability_registry_payload` drops every forbidden field, drops
  bytes/callables, collapses nested secrets in `safe_metadata`, and returns
  `{}` for non-mapping input.
- Each of the 10 event types writes a redacted, no-leak event even when the
  caller supplies a smuggled `safe_metadata`.
- A bad HERMES_HOME does not raise; the registry summary stays valid when
  audit is unavailable.
- The production home (`/Users/huangruibang/.hermes`) is categorically refused.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_audit_no_leak.py
```

## Fixes

Test-only. No implementation change.

## Residual risk

None.
