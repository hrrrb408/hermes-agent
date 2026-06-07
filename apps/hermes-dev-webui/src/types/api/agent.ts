/**
 * TypeScript types for the Dev API agent status endpoint.
 *
 * Matches the Phase 0C-05 API contract.
 */

/** Agent runtime status flags. */
export interface AgentRuntimeStatus {
  readonly entry: string
  readonly messageSendEnabled: boolean
  readonly streamingEnabled: boolean
  readonly toolExecutionEnabled: boolean
}

/** Agent model configuration (safe fields only). */
export interface AgentModelStatus {
  readonly configured: boolean
  readonly provider: string
  readonly name: string
}

/** Agent memory status flags. */
export interface AgentMemoryStatus {
  readonly enabled: boolean
  readonly contextLoaderEnabled: boolean
  readonly autoWriteEnabled: boolean
  readonly reviewQueueEnabled: boolean
}

/** Response data for GET /agent/status. */
export interface AgentStatusData {
  readonly available: boolean
  readonly readOnly: boolean
  readonly runtime: AgentRuntimeStatus
  readonly model: AgentModelStatus
  readonly memory: AgentMemoryStatus
}
