/**
 * Phase 3A — Workflow approval gate tests.
 *
 * Asserts the approval gate reflects required / ready / none states, and that
 * the step detail disables Execute until an approval token exists. Write-execute
 * and rollback-execute affordances are never offered (preview/reference only).
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowApprovalGate from '@/components/devconsole/WorkflowApprovalGate.vue'
import WorkflowStepDetail from '@/components/devconsole/WorkflowStepDetail.vue'
import type { WorkflowStep } from '@/lib/workflowTypes'

function baseStep(overrides: Partial<WorkflowStep> = {}): WorkflowStep {
  return {
    stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'planned',
    toolId: 'dev_environment_read', requiresApproval: true, requiresDryRun: true,
    requiresConfirmation: true, writeRequired: false, readOnly: true, localSideEffects: false,
    externalSideEffects: false, input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '',
    ...overrides,
  } as unknown as WorkflowStep
}

describe('Phase 3A workflow approval gate', () => {
  it('shows "required" when approval is required but no token exists', () => {
    const wrapper = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: false, approvalId: null, expiresAt: null },
    })
    expect(wrapper.find('[data-testid="dev-workflow-approval-required"]').exists()).toBe(true)
  })

  it('shows "ready" when an approval token is present', () => {
    const wrapper = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: true, approvalId: 'cft_abc', expiresAt: '2026-06-16T00:05:00Z' },
    })
    expect(wrapper.find('[data-testid="dev-workflow-approval-ready"]').exists()).toBe(true)
  })

  it('shows "none" when the step type has no approval gate', () => {
    const wrapper = mount(WorkflowApprovalGate, {
      props: { approvalRequired: false, hasToken: false, approvalId: null, expiresAt: null },
    })
    expect(wrapper.find('[data-testid="dev-workflow-approval-none"]').exists()).toBe(true)
  })

  it('disables Execute before an approval token exists', () => {
    const wrapper = mount(WorkflowStepDetail, {
      props: { step: baseStep(), preview: null, hasApprovalToken: false, loading: false },
    })
    const btn = wrapper.find('[data-testid="dev-workflow-execute-btn"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('enables Execute when an approval token is present', () => {
    const wrapper = mount(WorkflowStepDetail, {
      props: { step: baseStep({ status: 'previewed' }), preview: null, hasApprovalToken: true, loading: false },
    })
    const btn = wrapper.find('[data-testid="dev-workflow-execute-btn"]')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('marks write-preview and rollback-reference steps as preview/reference only', () => {
    const write = mount(WorkflowStepDetail, {
      props: { step: baseStep({ stepType: 'sandbox_write_preview', status: 'previewed' }), preview: null, hasApprovalToken: true, loading: false },
    })
    expect(write.find('[data-testid="dev-workflow-write-execute-blocked"]').exists()).toBe(true)
    const rollback = mount(WorkflowStepDetail, {
      props: { step: baseStep({ stepType: 'rollback_reference', status: 'previewed' }), preview: null, hasApprovalToken: true, loading: false },
    })
    expect(rollback.find('[data-testid="dev-workflow-write-execute-blocked"]').exists()).toBe(true)
  })
})
