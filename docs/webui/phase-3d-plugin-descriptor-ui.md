# Phase 3D — Plugin Descriptor UI

Location: Dev Console → **Plugin Descriptors** nav section (`#/console`).

## Components

- `PluginDescriptorRegistrySection.vue` — read-only section.
- `PluginRuntimeDisabledBanner.vue` — runtime-disabled invariants banner.
- `PluginDescriptorRegistrySummary.vue` — frozen flags + counts.
- `PluginDescriptorRegistryTable.vue` — descriptor list with badges.
- `PluginDescriptorRegistryDetailDrawer.vue` — safe detail drawer.
- `PluginDescriptorTrustBadge.vue` / `PluginDescriptorStatusBadge.vue` /
  `PluginDescriptorPermissionBadge.vue` — non-color badges (label + icon).

## What the UI shows

- Plugin runtime disabled; plugin loader not implemented; dynamic loading
  disabled; local plugin directory loading disabled; remote registry disabled;
  marketplace disabled; external plugin fetch disabled; no provider-generated
  plugin; no LLM-generated plugin install.
- Descriptor only; does not grant permission; does not execute a plugin.
- Frozen policy flags (all runtime flags `false`).
- Descriptor counts; capability bindings (as plain Phase 3C ids); blocked
  reasons.

## What the UI never shows

API key, Authorization, Bearer token, raw secret, callable repr, shell command,
SQL statement, production path, local plugin path, dynamic import path, external
URL, download URL, install command.

## Accessibility / no-leak

- Badges carry a text label + icon (never color alone); forbidden classes /
  trust levels carry an explicit "Forbidden" / "Not executable" marker.
- The section inherits the Phase 2E-H1 a11y baseline; the nav rail remains a
  labelled vertical tablist (now 10 tabs) with roving tabindex.
- CSS uses the shared semantic variable system (`plugin-*` classes mirror the
  Phase 3C `cap-*` classes in `src/styles/devconsole.css`).
