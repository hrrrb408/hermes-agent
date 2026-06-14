/**
 * Type definitions for the Tool Dry-Run and Tool Execute APIs.
 *
 * These types model the read-only policy decision (dry-run) and the
 * controlled execution gate (execute) responses. The confirmation token
 * is kept as an in-memory-only value — it is never persisted to storage
 * and never logged.
 */

/** Risk tier reported by the dry-run / execute policy. */
export type ToolRiskTier = 'R0' | 'R1' | 'R2' | 'R3' | 'R4' | 'R5' | null

/** Dry-run policy decision. */
export type DryRunDecision =
  | 'would_allow'
  | 'would_block'
  | 'would_redact'
  | 'requires_review'

/** Execute gate decision. */
export type ExecuteDecision = string

/** Safe dry-run response data. */
export interface DryRunResultData {
  readonly canonicalName: string
  readonly exists: boolean
  readonly riskTier: ToolRiskTier
  readonly decision: DryRunDecision
  readonly reasonCodes: readonly string[]
  readonly policyNotes: readonly string[]
  readonly redactedArgumentsPreview: Record<string, unknown>
  readonly forbiddenFields: readonly string[]
  readonly missingRequiredFields: readonly string[]
  readonly executionAllowed: false
  readonly dispatchAllowed: false
  readonly providerSchemaAllowed: false
  readonly auditWritten: boolean
  readonly dryRunDecisionDigest: string | null
  readonly digestAlgorithm: string | null
  readonly digestPackageVersion: string | null
  readonly canonicalizationVersion: string | null
  /** Raw confirmation token — IN-MEMORY ONLY. Never persist, never log. */
  readonly confirmationToken?: string | null
  readonly confirmationTokenId?: string | null
  readonly confirmationTokenExpiresAt?: string | null
}

/** Safe clarify tool result (execute success path only). */
export interface ClarifyToolResult {
  readonly type: string | null
  readonly message: string | null
  readonly questions?: readonly unknown[]
  /**
   * Phase 2A: structured result payload for read-only inspection tools
   * (tool_policy_read, route_governance_read, audit_events_read,
   * dev_environment_read, release_status_read). Absent for clarify.
   */
  readonly result?: unknown
}

/** Side-effect summary (execute success path only — all flags false). */
export interface ToolExecutionSideEffects {
  readonly providerSchemaSent: false
  readonly providerApiCalled: false
  readonly externalSideEffects: false
}

/** Safe execute response data. */
export interface ExecuteResultData {
  readonly canonicalName: string
  readonly exists: boolean
  readonly riskTier: ToolRiskTier
  readonly decision: ExecuteDecision
  readonly reasonCodes: readonly string[]
  readonly policyNotes: readonly string[]
  readonly errorCode: string | null
  readonly executionAllowed: false
  readonly dispatchAllowed: false
  readonly providerSchemaAllowed: false
  readonly toolHandlerCalled: boolean
  readonly providerApiCalled: false
  readonly executionStarted: boolean
  readonly executionCompleted: boolean
  readonly executionAttempted: boolean
  // Correlation IDs (safe to display in dev-only UI)
  readonly dryRunRequestId?: string | null
  readonly confirmationTokenId?: string | null
  readonly preExecutionAuditId?: string | null
  readonly preExecutionAuditStatus?: string | null
  readonly executeRequestId?: string | null
  readonly handlerLookupId?: string | null
  readonly handlerLookupStatus?: string | null
  readonly dispatchId?: string | null
  readonly dispatchStatus?: string | null
  readonly handlerCallId?: string | null
  readonly handlerCallStatus?: string | null
  readonly executionStatus?: string | null
  readonly postExecutionAuditId?: string | null
  readonly postExecutionAuditStatus?: string | null
  readonly toolResult?: ClarifyToolResult | null
  readonly sideEffects?: ToolExecutionSideEffects | null
}

/** Request body for the dry-run endpoint. */
export interface DryRunRequest {
  readonly canonicalName: string
  readonly argumentsPreview?: Record<string, unknown> | null
  readonly requestId?: string
  readonly issueConfirmationToken?: boolean
  readonly sourceContext?: string
  readonly uiOrigin?: string
}

/** Request body for the execute endpoint. */
export interface ExecuteRequest {
  readonly canonicalName: string
  readonly argumentsPreview?: Record<string, unknown> | null
  readonly dryRunRequestId?: string
  readonly dryRunDecisionDigest?: string
  /** Raw confirmation token — IN-MEMORY ONLY, passed straight through. */
  readonly confirmationToken?: string
  readonly requestId?: string
  readonly sourceContext?: string
  readonly uiOrigin?: string
}
