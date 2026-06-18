# Phase 3D — Static Plugin Descriptor Manifest

Source of truth: `hermes_cli/dev_web_plugin_descriptor_manifest.py`.

The manifest is a **literal Python tuple of dicts** — static, tracked,
deterministic, dev-only, disabled-by-default, descriptor-only.

## Guarantees

- **Static.** No runtime plugin path, no `importlib`, no path-based load, no
  directory scan, no remote fetch, no marketplace.
- **Deterministic.** `CREATED_AT` / `UPDATED_AT` are pinned constants
  (`2026-06-18T00:00:00Z`). The loader never samples the clock.
- **No execution surface.** No entry carries a forbidden field.
- **Capability-bound.** Every `capabilityBindings` references an existing
  Phase 3C capabilityId.
- **Dev-only + disabled-by-default.** Every entry: `devOnly=true`,
  `productionAllowed=false`, `disabledByDefault=true`.

## Versioning

`MANIFEST_VERSION = "phase3d-static-descriptor-v1"`. Bumped only under an
authorized scope freeze.

## Contents

12 descriptors (see the implementation doc for the full table). Partition:
3 visible (registry views), 4 disabled (read-only / write-preview / provider /
workflow bridges), 5 blocked (dynamic-load / remote-registry / marketplace /
external-execution / production-operation).

Blocked descriptors bind Phase 3C `capability.forbidden.*` capabilities and
carry a `blockedReason`. The frontend mirror lives at
`src/constants/pluginDescriptorRegistryManifest.ts`.
