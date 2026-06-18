# Phase 3D-H1 — Static Plugin Descriptor Registry Hardening

- **Phase:** 3D-H1
- **Hardening ID:** HARDENING-3D-H1-001
- **Baseline:** `bc52f02d2` — Phase 3D Static Plugin Descriptor Registry Implementation
- **Status:** completed
- **Scope type:** hardening pass (deterministic verification + tightening). **No new capability.**

## Goal

Verify and harden the first version of the static, dev-only Plugin Descriptor
Registry across twelve lenses. The registry must remain:

1. descriptor-only
2. disabled-by-default
3. read-only
4. non-executing
5. free of a plugin runtime
6. free of a plugin loader
7. free of dynamic code loading
8. free of local plugin directory loading
9. free of remote registry access
10. free of a marketplace
11. free of external plugin fetch
12. free of provider-generated plugins and LLM-generated plugin installs

Descriptors may only bind to existing Phase 3C `capabilityId`s, may never create
a capability, never grant permission, never create an approval / confirmation /
dry-run / route / execution path, and must inherit the most-restrictive permission
among their bindings.

## What changed

- **Implementation code:** no change. The hardening pass confirmed the frozen
  boundary holds; no defect required a fix.
- **Tests:** 10 new backend hardening test files + 8 new frontend hardening test
  files.
- **Smoke:** a new `phase3d_h1_plugin_descriptor_registry_hardening` profile +
  spec, wired into the `all` aggregate.
- **Audit script:** `scripts/run-dev-webui-phase3d-hardening-audit.sh`.
- **Docs:** this file + 13 lens-scoped hardening records.

## Hardening IDs

| Area | ID |
|------|----|
| Overall | HARDENING-3D-H1-001 |
| Manifest consistency | PLUG-MANIFEST-3D-H1-001 |
| Forbidden fields | PLUG-FORBIDDEN-FIELDS-3D-H1-001 |
| Capability binding | PLUG-CAPABILITY-BINDING-3D-H1-001 |
| Permission inheritance | PLUG-PERMISSION-INHERITANCE-3D-H1-001 |
| Trust boundary | PLUG-TRUST-BOUNDARY-3D-H1-001 |
| Non-execution | PLUG-NON-EXECUTION-3D-H1-001 |
| No dynamic loading | PLUG-NO-DYNAMIC-3D-H1-001 |
| Provider/workflow boundary | PLUG-PROVIDER-WORKFLOW-3D-H1-001 |
| Audit no-leak | PLUG-AUDIT-3D-H1-001 |
| Status API | PLUG-STATUS-API-3D-H1-001 |
| UI a11y / no-leak | PLUG-UI-3D-H1-001 |
| Smoke | PLUG-SMOKE-3D-H1-001 |

## 12-Lens result

All 12 lenses PASS. P0 = 0. P1 = 0. See
[phase-3d-h1-test-report.md](phase-3d-h1-test-report.md) and the per-lens records.

## Non-goals (unchanged)

No plugin runtime. No plugin loader. No plugin execution. No dynamic loading. No
local plugin directory loading. No remote registry. No marketplace. No external
plugin fetch. No provider-generated plugin. No LLM-generated plugin install. No
production rollout. No new route.

The registry describes descriptors only; it does not grant permission and does not
execute a plugin.
