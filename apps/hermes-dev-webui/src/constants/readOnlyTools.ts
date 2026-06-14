/**
 * Phase 2A selectable read-only tools (frontend constant).
 *
 * Mirrors the backend STATIC_ALLOWLIST (clarify + five Phase 2A read-only
 * inspection tools). The backend test `test_dev_web_phase_2a_read_only_frontend_contract`
 * pins this list against the real STATIC_ALLOWLIST so the two cannot drift.
 *
 * Every tool is readOnly=true, providerRequired=false, writeRequired=false,
 * externalSideEffects=false, requiresConfirmation=true (the controlled-
 * execution chain still applies: dry-run → confirmation token → digest →
 * pre/post-execution audit).
 */

export interface ReadOnlyToolMeta {
  /** Canonical tool id (sent to the backend as canonicalName). */
  id: string
  /** Human-readable label for the selector. */
  displayName: string
  /** One-line description shown under the selector. */
  description: string
  /** Semantic category, drives the badge color. */
  category: 'baseline' | 'policy' | 'governance' | 'audit' | 'environment' | 'release'
  /** Risk tier from the backend policy inventory (R0 = pure compute, R1 = read). */
  riskTier: 'R0' | 'R1'
  /**
   * Per-tool argument form spec. `clarify` uses question/choices textareas;
   * the read-only tools each declare their accepted boolean/string/integer
   * fields so the UI can render a bounded, type-safe form (never free shell /
   * path / provider input).
   */
  arguments: ReadonlyArray<ReadOnlyToolArgument>
}

export interface ReadOnlyToolArgument {
  key: string
  kind: 'boolean' | 'string' | 'integer'
  label: string
  required?: boolean
  default?: boolean | number
  min?: number
  max?: number
  maxLength?: number
}

/**
 * The full selectable tool list. Order = selector order. Clarify remains first
 * (the Phase 1G baseline default) for backward compatibility.
 */
export const SELECTABLE_TOOLS: readonly ReadOnlyToolMeta[] = [
  {
    id: 'clarify',
    displayName: 'Clarify',
    description:
      'Present a clarifying question with optional choices (Phase 1G baseline).',
    category: 'baseline',
    riskTier: 'R0',
    arguments: [
      { key: 'question', kind: 'string', label: 'Question', required: false, maxLength: 4000 },
      { key: 'choices', kind: 'string', label: 'Choices (one per line)', required: false, maxLength: 4000 },
    ],
  },
  {
    id: 'tool_policy_read',
    displayName: 'Tool Policy Read',
    description:
      'Return the current tool-execution policy: allowlist, read-only tools, disabled categories, route counts.',
    category: 'policy',
    riskTier: 'R0',
    arguments: [
      { key: 'includeDisabled', kind: 'boolean', label: 'Include disabled/denied categories', default: false },
    ],
  },
  {
    id: 'route_governance_read',
    displayName: 'Route Governance Read',
    description:
      'Return the OpenAPI/runtime/tool route-governance summary (34/34/5/0/1/1 baseline).',
    category: 'governance',
    riskTier: 'R0',
    arguments: [
      { key: 'includeDetails', kind: 'boolean', label: 'Include per-route detail', default: false },
    ],
  },
  {
    id: 'audit_events_read',
    displayName: 'Audit Events Read',
    description:
      'Query the dev audit-event summary with safe filters (limit, eventType, toolId, status, correlationId).',
    category: 'audit',
    riskTier: 'R1',
    arguments: [
      { key: 'limit', kind: 'integer', label: 'Limit', default: 20, min: 1, max: 100 },
      { key: 'eventType', kind: 'string', label: 'Event type', maxLength: 80 },
      { key: 'toolId', kind: 'string', label: 'Tool id', maxLength: 128 },
      { key: 'status', kind: 'string', label: 'Status', maxLength: 64 },
      { key: 'correlationId', kind: 'string', label: 'Correlation id', maxLength: 128 },
    ],
  },
  {
    id: 'dev_environment_read',
    displayName: 'Dev Environment Read',
    description:
      'Return the dev environment health summary: HERMES_HOME, ports, read-only production gateway PID observation.',
    category: 'environment',
    riskTier: 'R1',
    arguments: [
      { key: 'includePorts', kind: 'boolean', label: 'Include port checks (5180/5181)', default: true },
      { key: 'includeProductionGatewayReadOnlyCheck', kind: 'boolean', label: 'Read-only production gateway check', default: true },
    ],
  },
  {
    id: 'release_status_read',
    displayName: 'Release Status Read',
    description:
      'Return the docs/webui release-status summary: Phase 1G sealed, Phase 2 unlocked, Phase 2A status.',
    category: 'release',
    riskTier: 'R1',
    arguments: [
      { key: 'includePhaseTimeline', kind: 'boolean', label: 'Include phase timeline', default: false },
      { key: 'includeP2Backlog', kind: 'boolean', label: 'Include P2 backlog', default: false },
    ],
  },
]

/** The selectable tool ids (sent to the backend). */
export const SELECTABLE_TOOL_IDS: readonly string[] = SELECTABLE_TOOLS.map((t) => t.id)

/** Default tool (first = clarify, the Phase 1G baseline). */
export const DEFAULT_TOOL = SELECTABLE_TOOLS[0]?.id ?? 'clarify'

/** Backward-compat: the single-tool constant name kept as the default. */
export const EXECUTABLE_TOOL = DEFAULT_TOOL

/** Lookup a tool's metadata by id. */
export function getToolMeta(id: string): ReadOnlyToolMeta | undefined {
  return SELECTABLE_TOOLS.find((t) => t.id === id)
}

/** True if the id is one of the selectable tools. */
export function isSelectableTool(id: string): boolean {
  return SELECTABLE_TOOL_IDS.includes(id)
}
