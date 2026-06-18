# Phase 3C — Route Governance Summary

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Route Governance Summary |
| Status | Unchanged |
| Date | 2026-06-18 |

## 1. Frozen baseline

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET | **5** |
| Tool write HTTP route | **0** |
| Tool dry-run route | **1** |
| Tool execution route | **1** |
| New HTTP route | **none** |
| New Provider route | **none** |
| New Tool write route | **none** |

Compact form: `34/34/5/0/1/1` (surfaced as `routeGovernanceExpected` in the
`/status` capabilityRegistry block).

## 2. How the Capability Registry is exposed

The Capability Registry is exposed **only** through the existing
`GET /api/dev/v1/status` response, under `data.capabilityRegistry`. The
per-capability list / detail is a deterministic static mirror on the frontend;
only the authoritative validation status + counts come from the live `/status`
block.

- No new route was introduced.
- No write route was introduced.
- No provider route was introduced.
- No capability-specific path exists in the OpenAPI document.

## 3. Verification

- `tests/test_dev_check_webui.py` + `tests/test_dev_web_0c06_closure.py` →
  OpenAPI 34 / runtime 34 / 5 / 0 / 1 / 1.
- The H1 status-API security test asserts the OpenAPI path count is the frozen
  34 and that no path contains `capabilit`.
- The smoke specs assert no capability HTTP route exists.

## 4. Cross-references

- [Final security boundary](phase-3c-security-boundary-final.md)
- [Test gate summary](phase-3c-test-gate-summary.md)
- [Status-API hardening](phase-3c-h1-status-api-hardening.md)
