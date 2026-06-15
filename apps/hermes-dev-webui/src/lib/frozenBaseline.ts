/**
 * Frozen Dev Console baseline constants (Phase 2E).
 *
 * IMPORTANT — WHY THESE ARE FROZEN, NOT FETCHED LIVE:
 *
 * The authoritative route-governance numbers (34/34/5/0/1/1), the production
 * gateway PID baseline (28428), and the sealed phase timeline are surfaced by
 * the read-only tools `route_governance_read`, `dev_environment_read`, and
 * `release_status_read`. Those tools are dispatched through the controlled-
 * execution chain (POST /tools/dry-run → confirmation token → POST /tools/execute),
 * which means fetching them live from the dashboard would:
 *
 *   1. consume one-time confirmation tokens on every dashboard load,
 *   2. write spurious pre/post-execution audit events that pollute the very
 *      audit trail the Audit Viewer is meant to be a faithful record of,
 *   3. require the full execution gate stack (HERMES_TOOL_EXECUTION_ENABLED +
 *      HERMES_AGENT_TOOLS_ENABLED + HERMES_TOOL_HANDLER_CALL_ENABLED) to be ON
 *      just to render the dashboard — breaking the "fails closed" property when
 *      the operator has not opted into execution.
 *
 * These values are instead pinned here and continuously verified by:
 *   - the smoke harness preflight (scripts/run-dev-webui-execute-audit-smoke.sh
 *     fails closed if the live production gateway PID is not 28428), and
 *   - the backend route-governance invariant test
 *     (tests/test_dev_check_webui.py + tests/test_dev_web_0c06_closure.py
 *     assert OpenAPI 34 / runtime 34 / tool GET 5 / tool write route 0 /
 *     dry-run 1 / execution 1).
 *
 * Do NOT "improve" the dashboard by calling the read-only tools live. If the
 * production gateway PID drifts (e.g. a host reboot / authorized restart), an
 * authorized P2 baseline refresh is required (update both this constant and the
 * smoke harness PRODUCTION_GATEWAY_PID), exactly as was done 1962 → 28428.
 */

/**
 * Pinned route-governance baseline. The Dev WebUI must never change this surface;
 * the backend invariant tests fail closed on drift.
 */
export interface RouteGovernanceBaseline {
  /** OpenAPI business paths under /api/dev/v1 (frozen). */
  readonly openApiPaths: number
  /** Runtime-registered routes (frozen). */
  readonly runtimeRoutes: number
  /** Read-only tool GET routes (e.g. /policy, /catalog, /audit-events, /schemas...). */
  readonly toolGetRoutes: number
  /** Mutating tool routes under /tools EXCLUDING dry-run + execute (must be 0). */
  readonly toolWriteRoutes: number
  /** /tools/dry-run route count (frozen at 1). */
  readonly toolDryRunRoutes: number
  /** /tools/execute route count (frozen at 1). */
  readonly toolExecutionRoutes: number
}

export const FROZEN_ROUTE_GOVERNANCE: Readonly<RouteGovernanceBaseline> = Object.freeze({
  openApiPaths: 34,
  runtimeRoutes: 34,
  toolGetRoutes: 5,
  toolWriteRoutes: 0,
  toolDryRunRoutes: 1,
  toolExecutionRoutes: 1,
})

/** Human-readable label for the frozen route-governance status. */
export const FROZEN_ROUTE_GOVERNANCE_STATUS = 'frozen_baseline'

/** Pinned production gateway PID (read-only observation target; never acted upon). */
export const FROZEN_PRODUCTION_GATEWAY_PID = 28428

/**
 * Pinned phase timeline. Phase 1G is sealed, Phase 2 is unlocked, and Phases
 * 2A through 2D-H1 are completed and pushed. Phase 2E is in progress (this
 * phase); Phase 3 is not started.
 */
export interface PhaseTimelineEntry {
  readonly phase: string
  readonly status: string
}

export const FROZEN_PHASE_TIMELINE: readonly PhaseTimelineEntry[] = [
  { phase: 'Phase 1G', status: 'SEALED' },
  { phase: 'Phase 2', status: 'UNLOCKED' },
  { phase: 'Phase 2A', status: 'completed' },
  { phase: 'Phase 2B', status: 'completed' },
  { phase: 'Phase 2C', status: 'completed' },
  { phase: 'Phase 2C-H1', status: 'completed' },
  { phase: 'Phase 2D', status: 'completed' },
  { phase: 'Phase 2D-H1', status: 'completed' },
  { phase: 'Phase 2E', status: 'in_progress' },
  { phase: 'Phase 3', status: 'not_started' },
]

/** Pinned release identifiers (mirror the sealed release docs). */
export const FROZEN_RELEASE_IDS = {
  phase1gStatus: 'SEALED',
  phase2Status: 'UNLOCKED',
  phase2eStatus: 'in_progress',
  phase3Status: 'not_started',
} as const

/** Static read-only allowlist surfaced by the policy tools (6 tools). */
export const FROZEN_STATIC_ALLOWLIST: readonly string[] = [
  'clarify',
  'tool_policy_read',
  'route_governance_read',
  'audit_events_read',
  'dev_environment_read',
  'release_status_read',
]

/** Static write tools surfaced by the sandbox-write registry (5 tools). */
export const FROZEN_STATIC_WRITE_TOOLS: readonly string[] = [
  'dev_sandbox_file_write',
  'dev_sandbox_file_append',
  'dev_sandbox_file_patch',
  'dev_sandbox_file_readback',
  'dev_sandbox_rollback_execute',
]
