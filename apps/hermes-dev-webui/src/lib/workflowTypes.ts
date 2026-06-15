/**
 * Phase 3A Workflow type definitions for the Hermes Dev WebUI.
 *
 * These types mirror the backend ``workflow_schema_v1`` document shape
 * (camelCase) returned by the workflow mode branches on
 * ``POST /tools/dry-run`` and ``POST /tools/execute``. They are pure data
 * types — no behaviour, no secrets, no tokens beyond the opaque single-use
 * approval token issued by the step preview.
 */

export const WORKFLOW_SCHEMA_VERSION = 'workflow_schema_v1'

/** The six step types permitted inside a Phase 3A workflow. */
export type WorkflowStepType =
  | 'read_only_tool'
  | 'fake_provider_roundtrip'
  | 'sandbox_write_preview'
  | 'rollback_reference'
  | 'manual_note'
  | 'audit_query'

/** Per-step lifecycle status. */
export type WorkflowStepStatus =
  | 'draft'
  | 'planned'
  | 'previewed'
  | 'approval_required'
  | 'approved'
  | 'ready'
  | 'running'
  | 'completed'
  | 'blocked'
  | 'failed'
  | 'skipped'

/** Execution-level (coarse) status. */
export type WorkflowExecutionStatus =
  | 'draft'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'blocked'

export interface WorkflowAuditLink {
  readonly auditId: string
  readonly auditKind: string
  readonly label?: string
}

export interface WorkflowSafetyBoundary {
  readonly realProvider: string
  readonly providerAutoWrite: string
  readonly autonomousWrite: string
  readonly writeExecute: string
  readonly rollbackExecute: string
  readonly shellCommand: string
  readonly databaseMutation: string
  readonly externalServiceWrite: string
  readonly productionRollout: string
  readonly sandboxWritePreview: string
  readonly rollbackReference: string
  readonly fakeProvider: string
  readonly manualApproval: string
  readonly audit: string
}

export interface WorkflowStep {
  readonly stepId: string
  readonly stepType: WorkflowStepType
  readonly title: string
  readonly status: WorkflowStepStatus
  readonly description?: string
  readonly toolId?: string
  readonly providerMode?: string
  readonly allowedToolIds?: readonly string[]
  readonly requiresApproval: boolean
  readonly requiresDryRun: boolean
  readonly requiresConfirmation: boolean
  readonly writeRequired: boolean
  readonly readOnly: boolean
  readonly localSideEffects: boolean
  readonly externalSideEffects: boolean
  readonly input: Readonly<Record<string, unknown>>
  readonly safeInputSummary: Readonly<Record<string, unknown>>
  readonly preview?: Readonly<Record<string, unknown>>
  readonly result?: Readonly<Record<string, unknown>>
  readonly auditLinks?: readonly WorkflowAuditLink[]
  readonly blockedReason?: string
  readonly approvalId?: string
  readonly createdAt: string
  readonly updatedAt: string
}

export interface WorkflowTimelineEvent {
  readonly eventId: string
  readonly eventType: string
  readonly createdAt: string
  readonly stepId?: string
  readonly stepType?: string
  readonly stepStatus?: string
  readonly approvalId?: string
  readonly toolId?: string
  readonly providerMode?: string
  readonly writePreviewId?: string
  readonly rollbackId?: string
  readonly auditLinks?: readonly WorkflowAuditLink[]
  readonly message?: string
  readonly blockedReason?: string
}

export interface WorkflowPlan {
  readonly workflowId: string
  readonly workflowPlanId: string
  readonly schemaVersion: string
  readonly title: string
  readonly goal?: string
  readonly steps: readonly WorkflowStep[]
  readonly safetyBoundary: WorkflowSafetyBoundary
  readonly blockedSteps: readonly WorkflowStep[]
  readonly requiredApprovals: number
  readonly auditPreview: Readonly<Record<string, unknown>>
  readonly summary: string
  readonly createdAt: string
  readonly allowedStepTypes: readonly string[]
  readonly forbiddenStepTypes: readonly string[]
  /** Present when the plan materialized a runnable execution. */
  readonly workflowExecutionId?: string | null
  readonly executionStatus?: string | null
  readonly cursorStepId?: string | null
}

export interface WorkflowExecutionState {
  readonly workflowExecutionId: string
  readonly workflowId: string
  readonly workflowPlanId: string
  readonly schemaVersion: string
  readonly title: string
  readonly status: WorkflowExecutionStatus
  readonly steps: readonly WorkflowStep[]
  readonly cursorStepId: string | null
  readonly safetyBoundary: WorkflowSafetyBoundary
  readonly createdAt: string
  readonly updatedAt: string
  readonly timeline: readonly WorkflowTimelineEvent[]
  readonly completedStepCount: number
  readonly totalStepCount: number
}

/** Response of the workflow_step_preview mode (issues the approval token). */
export interface WorkflowStepPreviewResponse {
  readonly mode: 'workflow_step_preview'
  readonly workflowExecutionId: string
  readonly stepId: string
  readonly preview: Readonly<Record<string, unknown>>
  readonly auditLink: WorkflowAuditLink | null
  readonly stepStatus: WorkflowStepStatus | null
  readonly approvalRequired: boolean
  readonly approvalToken: string | null
  readonly approvalId: string | null
  readonly approvalExpiresAt: string | null
}

/** Response of the workflow_step_execute mode. */
export interface WorkflowStepExecuteResponse {
  readonly mode: 'workflow_step_execute'
  readonly workflowExecutionId: string
  readonly stepId: string
  readonly status: string
  readonly result: Readonly<Record<string, unknown>>
  readonly approvalId: string | null
  readonly auditLinks: readonly WorkflowAuditLink[]
  readonly executionStatus: string | null
  readonly cursorStepId: string | null
  readonly completedStepCount: number | null
  readonly safetyBoundary: WorkflowSafetyBoundary
}

/** A single planned step in a build-plan request. */
export interface WorkflowPlanStepRequest {
  readonly stepType: WorkflowStepType | string
  readonly toolId?: string
  readonly providerMode?: string
  readonly message?: string
  readonly allowedToolIds?: readonly string[]
  readonly targetRelativePath?: string
  readonly content?: string
  readonly rollbackId?: string
  readonly note?: string
  readonly title?: string
  readonly description?: string
  readonly arguments?: Readonly<Record<string, unknown>>
  readonly [key: string]: unknown
}

export interface WorkflowPlanRequest {
  readonly title?: string
  readonly goal?: string
  readonly steps?: readonly WorkflowPlanStepRequest[]
}
