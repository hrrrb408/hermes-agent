/**
 * TypeScript types for the Dev API agent run endpoints.
 *
 * Matches the Phase 1F API contract:
 * POST /api/dev/v1/agent/runs
 * GET  /api/dev/v1/agent/runs/{runId}
 * GET  /api/dev/v1/agent/runs/{runId}/events  (SSE)
 * POST /api/dev/v1/agent/runs/{runId}/cancel
 */

/** Model info returned in run responses. */
export interface AgentRunModel {
  readonly name: string
  readonly provider: string
}

/** Capabilities returned in run responses. */
export interface AgentRunCapabilities {
  readonly llmCall: boolean
  readonly streaming: boolean
  readonly tools: boolean
  readonly autoMemory: boolean
  readonly sessionWrite: boolean
  readonly memoryWrite: boolean
  readonly reviewQueue: boolean
}

/** Safety flags returned in run responses. */
export interface AgentRunSafety {
  readonly devOnly: boolean
  readonly killSwitchEnabled: boolean
  readonly toolsDisabled: boolean
  readonly autoMemoryDisabled: boolean
}

/** Token usage from provider response. */
export interface AgentRunUsage {
  readonly inputTokens: number | null
  readonly outputTokens: number | null
  readonly totalTokens: number | null
  readonly cachedTokens: number | null
  readonly cost: number | null
  readonly costEstimated: boolean
}

/** Error info in run status. */
export interface AgentRunError {
  readonly code: string
  readonly message: string
}

/** Response data for POST /agent/runs (202 Accepted). */
export interface CreateRunResponseData {
  readonly runId: string
  readonly sessionId: string
  readonly status: string
  readonly streamUrl: string
  readonly statusUrl: string
  readonly cancelUrl: string
  readonly model: AgentRunModel
  readonly capabilities: AgentRunCapabilities
  readonly safety: AgentRunSafety
}

/** Response data for GET /agent/runs/{runId}. */
export interface RunStatusResponseData {
  readonly runId: string
  readonly sessionId: string
  readonly status: string
  readonly createdAt: string
  readonly startedAt: string | null
  readonly completedAt: string | null
  readonly cancelRequested: boolean
  readonly clientConnected: boolean
  readonly model: AgentRunModel
  readonly usage: AgentRunUsage | null
  readonly capabilities: AgentRunCapabilities
  readonly safety: AgentRunSafety
  readonly error?: AgentRunError
}

/** Response data for POST /agent/runs/{runId}/cancel. */
export interface CancelRunResponseData {
  readonly runId: string
  readonly cancelRequested: boolean
  readonly statusBefore: string
  readonly statusAfter: string
  readonly alreadyTerminal: boolean
}

/** Request body for POST /agent/runs. */
export interface CreateRunRequest {
  readonly sessionId: string
  readonly message: string
  readonly confirmationText: 'RUN'
  readonly dryRunPreviewed: true
  readonly acknowledgedEffects: readonly ['CALL_LLM', 'WRITE_SESSION']
  readonly options: {
    readonly stream: true
    readonly tools: false
    readonly autoMemory: false
  }
  readonly overrides?: {
    readonly model?: string | null
    readonly temperature?: number | null
    readonly maxOutputTokens?: number | null
  }
}

// ── SSE Event Types ──

/** SSE event envelope for agent run. */
export interface AgentRunEvent {
  readonly runId: string
  readonly sequence: number
  readonly timestamp: string
  readonly type: AgentRunEventType
  readonly data: Record<string, unknown>
}

/** All allowed SSE event types for Phase 1F. */
export type AgentRunEventType =
  | 'run.created'
  | 'run.started'
  | 'message.delta'
  | 'message.completed'
  | 'usage.updated'
  | 'run.cancelling'
  | 'run.cancelled'
  | 'run.completed'
  | 'run.failed'
  | 'heartbeat'

/** Terminal event types. */
export const TERMINAL_EVENT_TYPES: readonly AgentRunEventType[] = [
  'run.completed',
  'run.cancelled',
  'run.failed',
] as const

/** Run lifecycle states matching backend RunStatus enum. */
export type RunStatus =
  | 'CREATED'
  | 'STARTING'
  | 'RUNNING'
  | 'CANCELLING'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'FAILED'
  | 'EXPIRED'

/** Terminal states. */
export const TERMINAL_RUN_STATUSES: readonly RunStatus[] = [
  'COMPLETED',
  'CANCELLED',
  'FAILED',
  'EXPIRED',
] as const

/** Connection status for SSE. */
export type SSEConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'
