/**
 * Phase 3A — Workflow panel (section) tests.
 *
 * Asserts the Workflow section renders, is registered in the console nav, the
 * create-plan form is present, and the store wires the build-plan action to the
 * mocked API. Also covers the store-level approval gating (no execute without a
 * preview-issued token).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
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

import WorkflowSection from '@/components/devconsole/WorkflowSection.vue'
import WorkflowPlanForm from '@/components/devconsole/WorkflowPlanForm.vue'
import { useToolWorkflowStore } from '@/stores/toolWorkflow'
import {
  CONSOLE_SECTIONS,
  CONSOLE_SECTION_LABELS,
} from '@/stores/devConsoleNav'

const BOUNDARY = {
  realProvider: 'blocked', providerAutoWrite: 'blocked', autonomousWrite: 'blocked',
  writeExecute: 'blocked', rollbackExecute: 'blocked', shellCommand: 'blocked',
  databaseMutation: 'blocked', externalServiceWrite: 'blocked', productionRollout: 'blocked',
  sandboxWritePreview: 'allowed', rollbackReference: 'allowed', fakeProvider: 'allowed',
  manualApproval: 'required', audit: 'enabled',
}

describe('Phase 3A workflow panel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    planPreview.mockReset()
    stepPreview.mockReset()
    executeStep.mockReset()
    readState.mockReset()
    readState.mockResolvedValue({ data: { mode: 'workflow_state_read', executions: [], count: 0 } })
  })

  it('registers the Workflow section in the console nav', () => {
    expect(CONSOLE_SECTIONS).toContain('workflow')
    expect(CONSOLE_SECTION_LABELS.workflow).toBe('Workflow')
  })

  it('renders the section with the create-plan form and safety boundary', () => {
    const wrapper = mount(WorkflowSection)
    expect(wrapper.find('[data-testid="dev-workflow-plan-form"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="dev-workflow-safety-boundary"]').exists()).toBe(true)
    expect(wrapper.text().toLowerCase()).toContain('no real provider')
    expect(wrapper.text().toLowerCase()).toContain('no autonomous write')
  })

  it('the create-plan form exposes no API-key / shell-command input', () => {
    const wrapper = mount(WorkflowPlanForm)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    expect(wrapper.html()).not.toMatch(/api[_-]?key/i)
  })

  it('builds a plan via the mocked API and materializes an execution', async () => {
    planPreview.mockResolvedValue({
      data: {
        workflowId: 'wf_1', workflowPlanId: 'wfp_1', schemaVersion: 'workflow_schema_v1',
        title: 'Demo', goal: '', steps: [], safetyBoundary: BOUNDARY, blockedSteps: [],
        requiredApprovals: 0, auditPreview: {}, summary: 's', createdAt: '',
        workflowExecutionId: 'wfx_1', executionStatus: 'draft', cursorStepId: null,
        allowedStepTypes: [], forbiddenStepTypes: [], mode: 'workflow_plan_preview',
      },
    })
    readState.mockResolvedValue({
      data: {
        mode: 'workflow_state_read', workflowExecutionId: 'wfx_1', workflowId: 'wf_1',
        workflowPlanId: 'wfp_1', schemaVersion: 'workflow_schema_v1', title: 'Demo',
        status: 'running', steps: [], cursorStepId: null, safetyBoundary: BOUNDARY,
        createdAt: '', updatedAt: '', timeline: [], completedStepCount: 0, totalStepCount: 0,
      },
    })
    const store = useToolWorkflowStore()
    await store.buildPlan()
    await flushPromises()
    expect(planPreview).toHaveBeenCalled()
    expect(store.plan).not.toBeNull()
    expect(store.hasExecution).toBe(true)
  })

  it('refuses to execute a step before a preview-issued approval token exists', async () => {
    const store = useToolWorkflowStore()
    // Simulate a materialized execution with one planned step but no approval
    // token issued (i.e. the step was never previewed).
    store.execution = {
      workflowExecutionId: 'wfx_1', workflowId: 'wf_1', workflowPlanId: 'wfp_1',
      schemaVersion: 'workflow_schema_v1', title: 'Demo', status: 'running',
      steps: [{
        stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'planned',
        requiresApproval: true, requiresDryRun: true, requiresConfirmation: true,
        writeRequired: false, readOnly: true, localSideEffects: false, externalSideEffects: false,
        input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any],
      cursorStepId: 'wfs_1', safetyBoundary: BOUNDARY, createdAt: '', updatedAt: '',
      timeline: [], completedStepCount: 0, totalStepCount: 1,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any
    await store.executeStep('wfs_1')
    expect(executeStep).not.toHaveBeenCalled()
    expect(store.error).toContain('Approval required')
  })
})
