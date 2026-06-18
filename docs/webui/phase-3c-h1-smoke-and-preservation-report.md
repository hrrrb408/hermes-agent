# Phase 3C-H1 — Smoke + Preservation Report

| Field | Value |
|-------|-------|
| Lens | 12 — Smoke / Preservation / Production Isolation |
| Hardening ID | `CAP-SMOKE-3C-H1-001` |
| Status | PASS |

## 1. Smoke — Profile Q (phase3c_h1_capability_registry_hardening)

New smoke profile `phase3c_h1_capability_registry_hardening` (Profile Q) +
spec `tests/smoke/phase-3c-h1-capability-registry-hardening-smoke.spec.ts`,
included in the `all` target. Identical read-only gate env as Profile P
(read-only execution gates on + FAKE provider only).

The profile verifies the 23-point H1 boundary:

1. capabilityRegistry block exists
2. capability count = 46
3. backend validation valid
4. `dynamicLoadingAllowed = false`
5. `remoteRegistryAllowed = false`
6. `marketplaceAllowed = false`
7. `productionAllowed = false`
8. registry describes only
9. does not grant permission
10. live manual one-shot listed but disabled / not executed
11. dynamic_plugin_load blocked
12. remote_registry blocked
13. marketplace blocked
14. shell / database / external_http / production_operation blocked
15. UI registry panel visible
16. UI badges have text labels
17. UI no API key
18. UI no Authorization
19. UI no callable repr
20. UI no production path
21. route governance unchanged
22. Production Gateway PID 28428 unchanged
23. ports final free

Points 22–23 (PID / ports) and `~/.hermes` / production `state.db` isolation
are enforced by the hardening audit script, not the Playwright spec.

## 2. `all` aggregate invariants

`all` now runs Profile A..Q and **includes** both
`phase3c_capability_registry_static` and `phase3c_h1_capability_registry_hardening`.

`all` **excludes** the manual one-shot live profile, dynamic plugin runtime,
remote registry, marketplace, and external plugin fetch — verified by the
hardening audit script.

## 3. Preservation

The hardening audit script runs Phase 2A / 2B / 2C / 2D / 2E / 3A / 3A-H1 /
3B / 3B-H1 / Live / Live-H1 / 3C preservation tests — 0 failed.

## 4. Production isolation

Production Gateway PID 28428 (count 1) was not stopped / restarted / replaced
/ signaled. Dev Gateway stopped; Dashboard not started; 5180 / 5181 free
before and after. No `~/.hermes` or production `state.db` access. No runtime
artifact or `.claude/` staged.

## Commands

```bash
./scripts/run-dev-webui-execute-audit-smoke.sh all
./scripts/run-dev-webui-phase3c-hardening-audit.sh
```
