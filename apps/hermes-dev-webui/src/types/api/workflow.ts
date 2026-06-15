/**
 * Workflow API request types (Phase 3A).
 *
 * The workflow surface reuses the existing POST /api/dev/v1/tools/dry-run and
 * POST /api/dev/v1/tools/execute routes via ``mode`` branches — no new route.
 */

import type {
  WorkflowExecutionState,
  WorkflowPlan,
  WorkflowPlanRequest,
  WorkflowStepExecuteResponse,
  WorkflowStepPreviewResponse,
} from '@/lib/workflowTypes'

export type {
  WorkflowExecutionState,
  WorkflowPlan,
  WorkflowPlanRequest,
  WorkflowStepExecuteResponse,
  WorkflowStepPreviewResponse,
}

/** workflow_plan_preview body (dry-run). */
export interface WorkflowPlanPreviewRequest {
  readonly mode: 'workflow_plan_preview'
  readonly title?: string
  readonly goal?: string
  readonly steps?: readonly Record<string, unknown>[]
}

/** workflow_step_preview body (dry-run). */
export interface WorkflowStepPreviewRequest {
  readonly mode: 'workflow_step_preview'
  readonly workflowExecutionId: string
  readonly stepId: string
}

/** workflow_step_execute body (execute). */
export interface WorkflowStepExecuteRequest {
  readonly mode: 'workflow_step_execute'
  readonly workflowExecutionId: string
  readonly stepId: string
  readonly approvalToken: string
}

/** workflow_state_read body (dry-run). */
export interface WorkflowStateReadRequest {
  readonly mode: 'workflow_state_read'
  readonly workflowExecutionId?: string
  readonly limit?: number
}

/** workflow_state_read list response. */
export interface WorkflowStateReadListResult {
  readonly mode: 'workflow_state_read'
  readonly executions: readonly {
    readonly workflowExecutionId: string
    readonly workflowId: string
    readonly title: string
    readonly status: string
    readonly createdAt: string
    readonly updatedAt: string
    readonly completedStepCount: number
    readonly totalStepCount: number
  }[]
  readonly count: number
}
