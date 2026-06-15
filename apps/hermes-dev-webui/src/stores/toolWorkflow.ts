/**
 * Workflow store — Phase 3A dev-only Agent Workflow MVP state.
 *
 * Owns the plan-request form, the built plan preview, the live execution
 * state, the transient per-step approval token (issued by step preview,
 * consumed by step execute), and the loading/error flags. The store never
 * holds an API key, secret, or password; the approval token is an opaque
 * single-use credential issued by the backend preview.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  executeWorkflowStep as executeWorkflowStepApi,
  readWorkflowState as readWorkflowStateApi,
  runWorkflowPlanPreview as runWorkflowPlanPreviewApi,
  runWorkflowStepPreview as runWorkflowStepPreviewApi,
} from '@/api/workflow'
import { isDevApiError } from '@/api/client'
import type {
  WorkflowExecutionState,
  WorkflowPlan,
  WorkflowStepExecuteResponse,
  WorkflowStepPreviewResponse,
} from '@/lib/workflowTypes'

export type WorkflowPhase = 'idle' | 'loading' | 'ready' | 'blocked' | 'error'

function _handleError(err: unknown): string {
  if (isDevApiError(err)) {
    return err.message
  }
  return 'An unexpected error occurred.'
}

/** A draft step row in the create-plan form. */
export interface DraftStepRow {
  stepType: string
  toolId: string
  message: string
  note: string
  targetRelativePath: string
}

/** A lightweight execution summary (from workflow_state_read list). */
export interface WorkflowExecutionSummary {
  workflowExecutionId: string
  title: string
  status: string
}

function _emptyDraftStep(): DraftStepRow {
  return {
    stepType: 'read_only_tool',
    toolId: 'dev_environment_read',
    message: '',
    note: '',
    targetRelativePath: '',
  }
}

export const useToolWorkflowStore = defineStore('tool-workflow', () => {
  const title = ref('Dev workflow demo')
  const goal = ref('')
  const draftSteps = ref<DraftStepRow[]>([_emptyDraftStep()])

  const phase = ref<WorkflowPhase>('idle')
  const error = ref('')
  const plan = ref<WorkflowPlan | null>(null)
  const execution = ref<WorkflowExecutionState | null>(null)
  /** Transient approval token for the currently-previewed step, keyed by stepId. */
  const approvalTokens = ref<Record<string, string>>({})
  /** Transient preview responses, keyed by stepId. */
  const stepPreviews = ref<Record<string, WorkflowStepPreviewResponse>>({})
  const lastExecute = ref<WorkflowStepExecuteResponse | null>(null)
  const executions = ref<WorkflowExecutionSummary[]>([])

  const hasPlan = computed(() => plan.value !== null)
  const hasExecution = computed(() => execution.value !== null)
  const blockedStepCount = computed(() => plan.value?.blockedSteps.length ?? 0)
  const planBlocked = computed(() => blockedStepCount.value > 0 && (plan.value?.steps.length ?? 0) === 0)

  function addDraftStep(): void {
    if (draftSteps.value.length >= 8) return
    draftSteps.value.push(_emptyDraftStep())
  }

  function removeDraftStep(index: number): void {
    if (draftSteps.value.length <= 1) return
    draftSteps.value.splice(index, 1)
  }

  function setDraftStep(index: number, patch: Partial<DraftStepRow>): void {
    draftSteps.value[index] = { ...draftSteps.value[index], ...patch } as DraftStepRow
  }

  function resetForm(): void {
    title.value = 'Dev workflow demo'
    goal.value = ''
    draftSteps.value = [_emptyDraftStep()]
  }

  function _buildRequestSteps(): Record<string, unknown>[] {
    return draftSteps.value.map((row) => {
      const step: Record<string, unknown> = { stepType: row.stepType, title: row.stepType }
      if (row.stepType === 'read_only_tool') step.toolId = row.toolId
      if (row.stepType === 'fake_provider_roundtrip') {
        step.providerMode = 'fake'
        step.message = row.message || 'Inspect the dev environment.'
        step.allowedToolIds = ['tool_policy_read', 'route_governance_read']
      }
      if (row.stepType === 'sandbox_write_preview') {
        step.toolId = 'dev_sandbox_file_write'
        step.targetRelativePath = row.targetRelativePath || 'workflow-demo/example.md'
        step.content = row.message || '# Workflow demo\n\nPreview only — no write executed.\n'
      }
      if (row.stepType === 'rollback_reference') step.rollbackId = ''
      if (row.stepType === 'manual_note') step.note = row.note || 'Operator review note.'
      return step
    })
  }

  async function buildPlan(): Promise<void> {
    phase.value = 'loading'
    error.value = ''
    try {
      const res = await runWorkflowPlanPreviewApi({
        mode: 'workflow_plan_preview',
        title: title.value,
        goal: goal.value,
        steps: _buildRequestSteps(),
      })
      plan.value = res.data
      approvalTokens.value = {}
      stepPreviews.value = {}
      lastExecute.value = null
      if (res.data.workflowExecutionId) {
        await loadExecution(res.data.workflowExecutionId)
      } else {
        execution.value = null
      }
      phase.value = planBlocked.value ? 'blocked' : 'ready'
    } catch (err) {
      error.value = _handleError(err)
      phase.value = 'error'
    }
  }

  async function previewStep(stepId: string): Promise<void> {
    if (!execution.value) return
    phase.value = 'loading'
    error.value = ''
    try {
      const res = await runWorkflowStepPreviewApi({
        mode: 'workflow_step_preview',
        workflowExecutionId: execution.value.workflowExecutionId,
        stepId,
      })
      stepPreviews.value[stepId] = res.data
      if (res.data.approvalToken) {
        approvalTokens.value[stepId] = res.data.approvalToken
      }
      await loadExecution(execution.value.workflowExecutionId)
      phase.value = 'ready'
    } catch (err) {
      error.value = _handleError(err)
      phase.value = 'error'
    }
  }

  async function executeStep(stepId: string): Promise<void> {
    if (!execution.value) return
    const token = approvalTokens.value[stepId]
    if (!token) {
      error.value = 'Approval required. Preview the step first to issue an approval token.'
      phase.value = 'blocked'
      return
    }
    phase.value = 'loading'
    error.value = ''
    try {
      const res = await executeWorkflowStepApi({
        mode: 'workflow_step_execute',
        workflowExecutionId: execution.value.workflowExecutionId,
        stepId,
        approvalToken: token,
      })
      lastExecute.value = res.data
      // The approval token is single-use; drop it after consumption.
      delete approvalTokens.value[stepId]
      await loadExecution(execution.value.workflowExecutionId)
      phase.value = 'ready'
    } catch (err) {
      error.value = _handleError(err)
      phase.value = 'error'
    }
  }

  async function loadExecution(executionId: string): Promise<void> {
    try {
      const res = await readWorkflowStateApi({
        mode: 'workflow_state_read',
        workflowExecutionId: executionId,
      })
      const data = res.data as WorkflowExecutionState & { mode: string }
      // Strip the API-only `mode` field so the stored object matches the schema.
      const { mode: _mode, ...state } = data
      void _mode
      execution.value = state as unknown as WorkflowExecutionState
    } catch (err) {
      error.value = _handleError(err)
    }
  }

  async function loadExecutions(): Promise<void> {
    try {
      const res = await readWorkflowStateApi({ mode: 'workflow_state_read', limit: 50 })
      const data = res.data as { executions?: WorkflowExecutionSummary[] }
      executions.value = data.executions ?? []
    } catch (err) {
      error.value = _handleError(err)
    }
  }

  function reset(): void {
    phase.value = 'idle'
    error.value = ''
    plan.value = null
    execution.value = null
    approvalTokens.value = {}
    stepPreviews.value = {}
    lastExecute.value = null
    resetForm()
  }

  return {
    // state
    title,
    goal,
    draftSteps,
    phase,
    error,
    plan,
    execution,
    approvalTokens,
    stepPreviews,
    lastExecute,
    executions,
    // computed
    hasPlan,
    hasExecution,
    blockedStepCount,
    planBlocked,
    // actions
    addDraftStep,
    removeDraftStep,
    setDraftStep,
    resetForm,
    buildPlan,
    previewStep,
    executeStep,
    loadExecution,
    loadExecutions,
    reset,
  }
})
