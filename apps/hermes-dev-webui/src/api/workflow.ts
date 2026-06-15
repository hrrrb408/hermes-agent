/**
 * Workflow API client for the Hermes Dev WebUI (Phase 3A).
 *
 * Reuses the existing POST /api/dev/v1/tools/dry-run route with
 * body.mode='workflow_plan_preview' | 'workflow_step_preview' |
 * 'workflow_state_read', and the existing POST /api/dev/v1/tools/execute route
 * with body.mode='workflow_step_execute' — NO new route is added.
 *
 * Safety:
 *   - This client never sends an API key, secret, or password. The only opaque
 *     credential it carries is the single-use approval token issued by the
 *     step-preview response, which is consumed exactly once.
 *   - Write/rollback steps are preview/reference-only by backend design; this
 *     client has no way to request write or rollback execution.
 */

import { apiPost } from './client'

import type {
  WorkflowPlanPreviewRequest,
  WorkflowStateReadListResult,
  WorkflowStateReadRequest,
  WorkflowStepExecuteRequest,
  WorkflowStepPreviewRequest,
} from '@/types/api/workflow'
import type {
  WorkflowExecutionState,
  WorkflowPlan,
  WorkflowStepExecuteResponse,
  WorkflowStepPreviewResponse,
} from '@/lib/workflowTypes'

const API_PREFIX = '/api/dev/v1'

/** Build + preview a workflow plan (and materialize a runnable execution). */
export async function runWorkflowPlanPreview(
  request: WorkflowPlanPreviewRequest,
  signal?: AbortSignal,
) {
  return apiPost<WorkflowPlan>(
    `${API_PREFIX}/tools/dry-run`,
    request,
    undefined,
    signal,
  )
}

/** Preview one step (non-executing) and issue its single-use approval token. */
export async function runWorkflowStepPreview(
  request: WorkflowStepPreviewRequest,
  signal?: AbortSignal,
) {
  return apiPost<WorkflowStepPreviewResponse>(
    `${API_PREFIX}/tools/dry-run`,
    request,
    undefined,
    signal,
  )
}

/** Execute one approved step (consumes the single-use approval token). */
export async function executeWorkflowStep(
  request: WorkflowStepExecuteRequest,
  signal?: AbortSignal,
) {
  return apiPost<WorkflowStepExecuteResponse>(
    `${API_PREFIX}/tools/execute`,
    request,
    undefined,
    signal,
  )
}

/** Read one execution state (+ timeline) or list stored executions. */
export async function readWorkflowState(
  request: WorkflowStateReadRequest,
  signal?: AbortSignal,
) {
  if (request.workflowExecutionId) {
    return apiPost<WorkflowExecutionState & { mode: 'workflow_state_read' }>(
      `${API_PREFIX}/tools/dry-run`,
      request,
      undefined,
      signal,
    )
  }
  return apiPost<WorkflowStateReadListResult>(
    `${API_PREFIX}/tools/dry-run`,
    request,
    undefined,
    signal,
  )
}
