/**
 * TypeScript types for the Dev API agent status and preview endpoints.
 *
 * Matches the Phase 1E API contract.
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

// ── Phase 1E: Agent Preview Types ──

/** Session info in a preview response. */
export interface AgentPreviewSession {
  readonly sessionId: string
  readonly exists: boolean
  readonly historyIncluded: boolean
  readonly historyMessageCount: number
  readonly historyTruncated: boolean
}

/** Safe model metadata in a preview response. */
export interface AgentPreviewModel {
  readonly name: string
  readonly provider: string
  readonly temperature: number | null
  readonly maxOutputTokens: number | null
}

/** A single prompt section in the preview. */
export interface AgentPromptSection {
  readonly type: string
  readonly included: boolean
  readonly characterCount: number
  readonly messageCount: number | null
  readonly preview: string | null
  readonly redacted: boolean
}

/** Prompt metadata in the preview response. */
export interface AgentPromptMetadata {
  readonly sectionCount: number
  readonly characterCount: number
  readonly truncated: boolean
  readonly sections: readonly AgentPromptSection[]
}

/** A memory item in the context preview. */
export interface AgentMemoryContextItem {
  readonly memoryId: string
  readonly title: string
  readonly category: string
  readonly score: number
  readonly summaryPreview: string
}

/** Memory context info in the preview response. */
export interface AgentMemoryContextPreview {
  readonly enabled: boolean
  readonly categoryCount: number
  readonly memoryCount: number
  readonly items: readonly AgentMemoryContextItem[]
  readonly truncated: boolean
}

/** Capability plan in the preview response. */
export interface AgentCapabilityPreview {
  readonly llmCallRequested: boolean
  readonly llmCallAvailable: boolean
  readonly llmCallForcedDisabled: boolean
  readonly streamingRequested: boolean
  readonly streamingAvailable: boolean
  readonly streamingForcedDisabled: boolean
  readonly toolsRequested: boolean
  readonly toolExecutionAvailable: boolean
  readonly toolExecutionForcedDisabled: boolean
  readonly autoMemoryRequested: boolean
  readonly memoryWriteAvailable: boolean
  readonly memoryWriteForcedDisabled: boolean
  readonly sessionWriteAvailable: boolean
  readonly reviewQueueAvailable: boolean
}

/** A safety check result. */
export interface AgentPreviewCheck {
  readonly code: string
  readonly passed: boolean
  readonly message: string
}

/** Safety flags in the preview response. */
export interface AgentPreviewSafety {
  readonly readOnly: boolean
  readonly sideEffects: boolean
  readonly llmCalled: boolean
  readonly toolsExecuted: boolean
  readonly sessionWritten: boolean
  readonly memoryWritten: boolean
  readonly reviewQueued: boolean
}

/** Response data for POST /agent/prompt/preview and /agent/run/dry-run. */
export interface AgentPreviewResult {
  readonly dryRun: boolean
  readonly operation: 'PROMPT_PREVIEW' | 'AGENT_RUN_DRY_RUN'
  readonly allowed: boolean
  readonly blockedReason: string | null
  readonly session: AgentPreviewSession
  readonly model: AgentPreviewModel
  readonly prompt: AgentPromptMetadata
  readonly memoryContext: AgentMemoryContextPreview
  readonly capabilities: AgentCapabilityPreview
  readonly checks: readonly AgentPreviewCheck[]
  readonly noEffects: readonly string[]
  readonly safety: AgentPreviewSafety
  readonly warnings: readonly string[]
  readonly userMessagePreview?: string
}

/** Request options for prompt preview. */
export interface PromptPreviewOptions {
  readonly includeHistory?: boolean
  readonly historyLimit?: number
  readonly includeMemoryContext?: boolean
  readonly memoryQuery?: string
  readonly maxCategories?: number
  readonly maxMemories?: number
  readonly includeSystemPreview?: boolean
  readonly includeToolMetadata?: boolean
}

/** Request options for run dry-run. */
export interface RunDryRunOptions {
  readonly includeHistory?: boolean
  readonly historyLimit?: number
  readonly includeMemoryContext?: boolean
  readonly memoryQuery?: string
  readonly toolsRequested?: boolean
  readonly streamRequested?: boolean
  readonly autoMemoryRequested?: boolean
}

/** Override parameters for both preview endpoints. */
export interface AgentPreviewOverrides {
  readonly model?: string | null
  readonly temperature?: number | null
  readonly maxOutputTokens?: number | null
}

/** Request body for POST /agent/prompt/preview. */
export interface AgentPromptPreviewRequest {
  readonly sessionId?: string
  readonly message: string
  readonly options?: PromptPreviewOptions
  readonly overrides?: AgentPreviewOverrides
}

/** Request body for POST /agent/run/dry-run. */
export interface AgentRunDryRunRequest {
  readonly sessionId?: string
  readonly message: string
  readonly options?: RunDryRunOptions
  readonly overrides?: AgentPreviewOverrides
}
