/**
 * Phase 3A-H1 — Workflow UI state hardening.
 *
 * Adversarial store-level tests: the build → preview → execute lifecycle
 * advances phases correctly, the approval gate is enforced (no execute without
 * a preview-issued token), the single-use approval token is dropped after
 * consumption, errors are surfaced safely, and reset clears all transient
 * state including the approval token map.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const planPreview = vi.fn()
const stepPreview = vi.fn()
const executeStep = vi.fn()
const readState = vi.fn()

vi.mock('@/api/workflow', () => ({
  runWorkflowPlanPreview: (...args: unknown[]) => planPreview(...args),
  runWorkflowStepPreview: (...args: unknown[]) => stepPreview(...args),
  executeWorkflowStep: (...args: unknown[]) => executeStep(...args),
  readWorkflowState: (...args: unknown[]) => readState(...args),
}))

import { useToolWorkflowStore } from '@/stores/toolWorkflow'

const BOUNDARY = {
  realProvider: 'blocked', providerAutoWrite: 'blocked', autonomousWrite: 'blocked',
  writeExecute: 'blocked', rollbackExecute: 'blocked', shellCommand: 'blocked',
  databaseMutation: 'blocked', externalServiceWrite: 'blocked', productionRollout: 'blocked',
  sandboxWritePreview: 'allowed', rollbackReference: 'allowed', fakeProvider: 'allowed',
  manualApproval: 'required', audit: 'enabled',
}

function planResponse(steps: unknown[] = []): Record<string, unknown> {
  return {
    data: {
      workflowId: 'wf_1', workflowPlanId: 'wfp_1', schemaVersion: 'workflow_schema_v1',
      title: 'Demo', goal: '', steps, safetyBoundary: BOUNDARY, blockedSteps: [],
      requiredApprovals: steps.length, auditPreview: {}, summary: 's', createdAt: '',
      workflowExecutionId: 'wfx_1', executionStatus: 'running', cursorStepId: steps[0] ? (steps[0] as Record<string, unknown>).stepId : null,
      allowedStepTypes: [], forbiddenStepTypes: [], mode: 'workflow_plan_preview',
    },
  }
}

function stateResponse(steps: unknown[]): Record<string, unknown> {
  return {
    data: {
      mode: 'workflow_state_read', workflowExecutionId: 'wfx_1', workflowId: 'wf_1',
      workflowPlanId: 'wfp_1', schemaVersion: 'workflow_schema_v1', title: 'Demo',
      status: 'running', steps, cursorStepId: steps[0] ? (steps[0] as Record<string, unknown>).stepId : null,
      safetyBoundary: BOUNDARY, createdAt: '', updatedAt: '', timeline: [],
      completedStepCount: 0, totalStepCount: steps.length,
    },
  }
}

function readStep(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'planned',
    toolId: 'dev_environment_read', requiresApproval: true, requiresDryRun: true,
    requiresConfirmation: true, writeRequired: false, readOnly: true, localSideEffects: false,
    externalSideEffects: false, input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '',
    ...overrides,
  }
}

describe('Phase 3A-H1 workflow UI state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    planPreview.mockReset()
    stepPreview.mockReset()
    executeStep.mockReset()
    readState.mockReset()
  })

  it('buildPlan advances idle → loading → ready and materializes the execution', async () => {
    const steps = [readStep()]
    planPreview.mockResolvedValue(planResponse(steps))
    readState.mockResolvedValue(stateResponse(steps))
    const store = useToolWorkflowStore()
    expect(store.phase).toBe('idle')
    const promise = store.buildPlan()
    await flushPromises()
    await promise
    expect(planPreview).toHaveBeenCalled()
    expect(store.phase).toBe('ready')
    expect(store.plan).not.toBeNull()
    expect(store.hasExecution).toBe(true)
  })

  it('buildPlan surfaces blocked phase when the plan has only blocked steps', async () => {
    planPreview.mockResolvedValue({
      data: {
        workflowId: 'wf_1', workflowPlanId: 'wfp_1', schemaVersion: 'workflow_schema_v1',
        title: 'Demo', goal: '', steps: [], safetyBoundary: BOUNDARY,
        blockedSteps: [readStep({ stepType: 'shell_command', blockedReason: 'blocked_workflow_shell_not_allowed' })],
        requiredApprovals: 0, auditPreview: {}, summary: 's', createdAt: '',
        workflowExecutionId: null, executionStatus: 'blocked', cursorStepId: null,
        allowedStepTypes: [], forbiddenStepTypes: [], mode: 'workflow_plan_preview',
      },
    })
    const store = useToolWorkflowStore()
    await store.buildPlan()
    await flushPromises()
    expect(store.phase).toBe('blocked')
    expect(store.planBlocked).toBe(true)
  })

  it('buildPlan surfaces an error safely without leaking internal detail', async () => {
    planPreview.mockRejectedValue({ message: 'boom' })
    const store = useToolWorkflowStore()
    await store.buildPlan()
    await flushPromises()
    expect(store.phase).toBe('error')
    expect(typeof store.error).toBe('string')
    // The error path never surfaces secret-shaped material.
    expect(store.error).not.toMatch(/sk-[A-Za-z0-9]{8,}/)
  })

  it('executeStep refuses without a preview-issued approval token', async () => {
    const steps = [readStep()]
    planPreview.mockResolvedValue(planResponse(steps))
    readState.mockResolvedValue(stateResponse(steps))
    const store = useToolWorkflowStore()
    await store.buildPlan()
    await flushPromises()
    await store.executeStep('wfs_1')
    expect(executeStep).not.toHaveBeenCalled()
    expect(store.phase).toBe('blocked')
    expect(store.error).toContain('Approval')
  })

  it('previewStep stores the approval token, execute consumes + drops it (single-use)', async () => {
    const steps = [readStep()]
    planPreview.mockResolvedValue(planResponse(steps))
    readState.mockResolvedValue(stateResponse(steps))
    stepPreview.mockResolvedValue({
      data: {
        mode: 'workflow_step_preview', workflowExecutionId: 'wfx_1', stepId: 'wfs_1',
        preview: { previewKind: 'read_only_tool_dry_run' }, auditLink: null, stepStatus: 'previewed',
        approvalRequired: true, approvalToken: 'cft_secret123.token456', approvalId: 'cft_secret123',
        approvalExpiresAt: '2026-06-16T00:05:00Z',
      },
    })
    executeStep.mockResolvedValue({
      data: {
        mode: 'workflow_step_execute', workflowExecutionId: 'wfx_1', stepId: 'wfs_1', status: 'completed',
        result: { type: 'dev_environment_read' }, approvalId: 'cft_secret123', auditLinks: [],
        executionStatus: 'running', cursorStepId: null, completedStepCount: 1, safetyBoundary: BOUNDARY,
      },
    })
    const store = useToolWorkflowStore()
    await store.buildPlan()
    await flushPromises()
    await store.previewStep('wfs_1')
    await flushPromises()
    expect(store.approvalTokens['wfs_1']).toBe('cft_secret123.token456')
    await store.executeStep('wfs_1')
    await flushPromises()
    expect(executeStep).toHaveBeenCalled()
    // The single-use token is dropped after consumption.
    expect(store.approvalTokens['wfs_1']).toBeUndefined()
  })

  it('reset clears the plan, execution, and all approval tokens', async () => {
    const steps = [readStep()]
    planPreview.mockResolvedValue(planResponse(steps))
    readState.mockResolvedValue(stateResponse(steps))
    const store = useToolWorkflowStore()
    await store.buildPlan()
    await flushPromises()
    store.approvalTokens['wfs_1'] = 'cft_secret.token'
    store.reset()
    expect(store.plan).toBeNull()
    expect(store.execution).toBeNull()
    expect(Object.keys(store.approvalTokens).length).toBe(0)
    expect(store.phase).toBe('idle')
  })
})
