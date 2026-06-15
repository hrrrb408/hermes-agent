/**
 * Unified Dev Console safety badges (Phase 2E).
 *
 * The single source of truth for the invariant safety badges rendered by the
 * Overview dashboard and the Safety Boundary panel. Every badge describes a
 * property that is TRUE for the dev console by construction — these are not
 * live probes, they are the frozen invariants the dev environment enforces.
 *
 * Only the new Overview / Safety / Diagnostics sections consume this module.
 * The existing workspace panels keep their own inline badge arrays (scope
 * discipline — no blast-radius refactor of tested panels in 2E).
 */

export type SafetyBadgeTone = 'ok' | 'warn' | 'danger' | 'info'

export interface SafetyBadge {
  /** Stable id used as the v-for key + test hook. */
  readonly id: string
  /** Short label rendered in the badge. */
  readonly label: string
  /** One-line explanation of what the invariant means. */
  readonly description: string
  /** Visual tone (ok = green, warn = amber, danger = red, info = neutral). */
  readonly tone: SafetyBadgeTone
  /** Semantic group for grouping in the Safety panel. */
  readonly group: 'production' | 'environment' | 'route' | 'provider' | 'write' | 'audit'
}

export const SAFETY_BADGES: readonly SafetyBadge[] = [
  {
    id: 'production-untouched',
    label: 'Production untouched',
    description: 'The production Gateway (~/.hermes) is never read, written, stopped, restarted, or signaled by the dev console.',
    tone: 'ok',
    group: 'production',
  },
  {
    id: 'dev-hermes-home',
    label: 'Dev HERMES_HOME active',
    description: 'All dev runtime data uses /Users/huangruibang/Code/hermes-home-dev, isolated from the production instance.',
    tone: 'ok',
    group: 'environment',
  },
  {
    id: 'no-prod-home-access',
    label: 'No ~/.hermes access',
    description: 'The dev WebUI never reads or writes the production home directory.',
    tone: 'ok',
    group: 'environment',
  },
  {
    id: 'route-tool-write-zero',
    label: 'Tool write route = 0',
    description: 'There is no dedicated mutating tool HTTP route. Write/rollback reuse /tools/execute via body.mode.',
    tone: 'ok',
    group: 'route',
  },
  {
    id: 'route-governance-frozen',
    label: 'Route governance frozen',
    description: 'OpenAPI 34 / runtime 34 / tool GET 5 / dry-run 1 / execution 1 — verified by backend invariant tests.',
    tone: 'ok',
    group: 'route',
  },
  {
    id: 'real-provider-blocked',
    label: 'Real provider blocked',
    description: 'Real provider mode is disabled by default and requires explicit enablement plus a dev-home + PID gate.',
    tone: 'warn',
    group: 'provider',
  },
  {
    id: 'provider-write-preview-only',
    label: 'Provider write preview-only',
    description: 'A provider may request a write preview but never auto-execute or auto-rollback a write.',
    tone: 'ok',
    group: 'provider',
  },
  {
    id: 'sandbox-write-only',
    label: 'Sandbox write only',
    description: 'Write tools operate only inside the dev sandbox and require HERMES_TOOL_WRITE_EXECUTION_ENABLED.',
    tone: 'warn',
    group: 'write',
  },
  {
    id: 'rollback-supported',
    label: 'Rollback supported',
    description: 'Every executed write records a rollback manifest with a file-backed single-use confirmation token + TTL.',
    tone: 'ok',
    group: 'write',
  },
  {
    id: 'audit-store-dev-only',
    label: 'Audit store dev-only',
    description: 'The durable audit store lives under the dev HERMES_HOME and never touches production state.db.',
    tone: 'ok',
    group: 'audit',
  },
  {
    id: 'audit-redaction-enabled',
    label: 'Redaction enabled',
    description: 'Audit events are sanitized before surfacing — no raw tokens, full hashes, raw arguments, or callable reprs.',
    tone: 'ok',
    group: 'audit',
  },
]

/** Lookup a badge by id (returns undefined if not found). */
export function getSafetyBadge(id: string): SafetyBadge | undefined {
  return SAFETY_BADGES.find((b) => b.id === id)
}

/** Badges filtered by group (for the grouped Safety panel layout). */
export function badgesByGroup(group: SafetyBadge['group']): readonly SafetyBadge[] {
  return SAFETY_BADGES.filter((b) => b.group === group)
}
