# Phase 3C-H1 — /status API Hardening

| Field | Value |
|-------|-------|
| Lens | 10 — /status CapabilityRegistry API / Route Governance |
| Hardening ID | `CAP-STATUS-API-3C-H1-001` |
| Status | PASS |

## Scope

The Capability Registry is exposed ONLY through the existing `GET /status`
response under `data.capabilityRegistry`. The block is value-free, the frozen
policy flags hold, and route governance is unchanged.

## Evidence

- The block exists with `registryVersion = "phase3c-static-v1"`,
  `capabilityCount = 46`, and counts that partition the total.
- `routeGovernanceExpected = "34/34/5/0/1/1"`.
- Frozen flags: `dynamicLoadingAllowed = remoteRegistryAllowed =
  marketplaceAllowed = productionAllowed = false`; `devOnly = true`;
  `redactionApplied = true`; validation passed with 0 errors.
- The block is value-free (no `apiKey`, `Authorization`, `Bearer`, callable
  repr, shell command, SQL, production path, plugin path, dynamic import path,
  `<function`, `sk-`).
- Route governance unchanged: OpenAPI path count is the frozen **34**; no
  path contains `capabilit`; no `/capability-registry` or `/registry` route.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_status_api_security.py
```

## Fixes

Test-only. No implementation change.

## Residual risk

None.
