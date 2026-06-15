/**
 * Phase 3A — Workflow plan preview tests.
 *
 * Asserts the plan preview renders the workflow/plan/execution ids, planned
 * steps, blocked steps (with the unified BlockedReasonPanel), and the summary.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowPlanPreview from '@/components/devconsole/WorkflowPlanPreview.vue'
import type { WorkflowPlan } from '@/lib/workflowTypes'

const BOUNDARY = {
  realProvider: 'blocked', providerAutoWrite: 'blocked', autonomousWrite: 'blocked',
  writeExecute: 'blocked', rollbackExecute: 'blocked', shellCommand: 'blocked',
  databaseMutation: 'blocked', externalServiceWrite: 'blocked', productionRollout: 'blocked',
  sandboxWritePreview: 'allowed', rollbackReference: 'allowed', fakeProvider: 'allowed',
  manualApproval: 'required', audit: 'enabled',
}

function plan(overrides: Partial<WorkflowPlan> = {}): WorkflowPlan {
  return {
    workflowId: 'wf_abc', workflowPlanId: 'wfp_abc', schemaVersion: 'workflow_schema_v1',
    title: 'Demo plan', goal: 'inspect', steps: [
      { stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'planned', requiresApproval: true, requiresDryRun: true, requiresConfirmation: true, writeRequired: false, readOnly: true, localSideEffects: false, externalSideEffects: false, input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '' },
    ],
    safetyBoundary: BOUNDARY, blockedSteps: [], requiredApprovals: 1,
    auditPreview: {}, summary: 'Demo plan: 1 step(s) planned, 0 blocked.', createdAt: '',
    workflowExecutionId: 'wfx_abc', executionStatus: 'running', cursorStepId: 'wfs_1',
    allowedStepTypes: [], forbiddenStepTypes: [],
    ...overrides,
  } as unknown as WorkflowPlan
}

describe('Phase 3A workflow plan preview', () => {
  it('renders the workflow, plan, and execution ids', () => {
    const wrapper = mount(WorkflowPlanPreview, { props: { plan: plan() } })
    expect(wrapper.find('[data-testid="dev-workflow-id"]').text()).toBe('wf_abc')
    expect(wrapper.find('[data-testid="dev-workflow-execution-id"]').text()).toBe('wfx_abc')
    expect(wrapper.find('[data-testid="dev-workflow-plan-summary"]').text()).toContain('1 step(s) planned')
  })

  it('lists the planned steps', () => {
    const wrapper = mount(WorkflowPlanPreview, { props: { plan: plan() } })
    expect(wrapper.find('[data-testid="dev-workflow-planned-step-read_only_tool"]').exists()).toBe(true)
  })

  it('renders a BlockedReasonPanel for each blocked step', () => {
    const wrapper = mount(WorkflowPlanPreview, {
      props: {
        plan: plan({
          steps: [],
          blockedSteps: [{
            stepId: 'wfs_b', stepType: 'shell_command', title: 'bad', status: 'blocked',
            requiresApproval: false, requiresDryRun: false, requiresConfirmation: false,
            writeRequired: false, readOnly: true, localSideEffects: false, externalSideEffects: false,
            input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '',
            blockedReason: 'blocked_workflow_shell_not_allowed',
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          } as any],
        }),
      },
    })
    const panel = wrapper.find('[data-testid="dev-blocked-reason"]')
    expect(panel.exists()).toBe(true)
    expect(panel.text()).toContain('blocked_workflow_shell_not_allowed')
  })

  it('shows the empty-run hint when the plan is fully blocked', () => {
    const wrapper = mount(WorkflowPlanPreview, {
      props: { plan: plan({ steps: [], blockedSteps: [] }) },
    })
    expect(wrapper.text()).toContain('No runnable steps')
  })
})
