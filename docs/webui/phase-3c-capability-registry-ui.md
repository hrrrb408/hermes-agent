# Phase 3C — Capability Registry UI

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Entry | Dev Console `/#/console` → "Capability Registry" (nav rail, 9th section) |
| Status | Implemented (read-only) |

Components (`apps/hermes-dev-webui/src/components/devconsole/`):
`CapabilityRegistrySection`, `CapabilityRegistrySummary`,
`CapabilityRegistryTable`, `CapabilityRegistryDetailDrawer`,
`CapabilityPermissionBadge`, `CapabilityTrustBadge`, `CapabilityStatusBadge`.

Store: `src/stores/capabilityRegistry.ts` (combines live `/status` summary +
static manifest mirror; read-only filters; no enable/disable/promote/delete).

The UI surfaces: registry status/version, counts, permission/trust/category
counts, frozen flags (all "no" except dev-only), capability list + detail,
blocked reasons, runtime gates, bindings, and the "registry describes only —
does not grant permission" notice. Badges are non-color (icon + label).

The UI never surfaces an API key, Authorization, Bearer, raw token, callable
repr, shell command, SQL, production path, local plugin path, dynamic import
path, or external URL.
