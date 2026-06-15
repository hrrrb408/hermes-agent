/**
 * Phase 3A — Workflow step list tests.
 *
 * Asserts the step list renders each step type with its status, marks the
 * cursor (current) step, supports selection, and formats statuses.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowStepList from '@/components/devconsole/WorkflowStepList.vue'
import type { WorkflowStep } from '@/lib/workflowTypes'

function step(overrides: Partial<WorkflowStep>): WorkflowStep {
  return {
    stepId: overrides.stepId ?? 'wfs_1',
    stepType: overrides.stepType ?? 'read_only_tool',
    title: overrides.title ?? 'Step',
    status: overrides.status ?? 'planned',
    requiresApproval: true, requiresDryRun: true, requiresConfirmation: true,
    writeRequired: false, readOnly: true, localSideEffects: false, externalSideEffects: false,
    input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '',
    ...overrides,
  } as unknown as WorkflowStep
}

describe('Phase 3A workflow step list', () => {
  it('renders one row per step with the step type label', () => {
    const steps = [
      step({ stepId: 'a', stepType: 'read_only_tool', title: 'Read env', status: 'completed' }),
      step({ stepId: 'b', stepType: 'fake_provider_roundtrip', title: 'Provider', status: 'planned' }),
      step({ stepId: 'c', stepType: 'manual_note', title: 'Note', status: 'planned' }),
    ]
    const wrapper = mount(WorkflowStepList, { props: { steps, cursorStepId: 'b' } })
    expect(wrapper.findAll('[data-testid^="dev-workflow-step-row-"]').length).toBe(3)
    expect(wrapper.text()).toContain('Read-only tool')
    expect(wrapper.text()).toContain('Fake provider round-trip')
    expect(wrapper.text()).toContain('Manual note')
  })

  it('marks the cursor step as current', () => {
    const wrapper = mount(WorkflowStepList, {
      props: { steps: [step({ stepId: 'a' })], cursorStepId: 'a' },
    })
    expect(wrapper.find('[aria-current="step"]').exists()).toBe(true)
  })

  it('emits select with the step id when a row is clicked', async () => {
    const wrapper = mount(WorkflowStepList, {
      props: { steps: [step({ stepId: 'wfs_9' })], cursorStepId: null },
    })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual(['wfs_9'])
  })

  it('renders a completed step with a positive tone marker', () => {
    const wrapper = mount(WorkflowStepList, {
      props: { steps: [step({ stepId: 'a', status: 'completed' })], cursorStepId: null },
    })
    const status = wrapper.find('[data-testid="dev-workflow-step-status"]')
    expect(status.text()).toBe('Completed')
    expect(status.attributes('data-tone')).toBe('positive')
  })

  it('renders a blocked step with a negative tone marker', () => {
    const wrapper = mount(WorkflowStepList, {
      props: { steps: [step({ stepId: 'a', status: 'blocked' })], cursorStepId: null },
    })
    const status = wrapper.find('[data-testid="dev-workflow-step-status"]')
    expect(status.attributes('data-tone')).toBe('negative')
  })
})
