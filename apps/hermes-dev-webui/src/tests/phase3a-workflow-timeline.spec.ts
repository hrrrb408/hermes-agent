/**
 * Phase 3A — Workflow timeline tests.
 *
 * Asserts the timeline renders events, the empty state, audit-link
 * cross-navigation chips, and blocked-reason badges.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowTimeline from '@/components/devconsole/WorkflowTimeline.vue'
import type { WorkflowTimelineEvent } from '@/lib/workflowTypes'

function event(overrides: Partial<WorkflowTimelineEvent> = {}): WorkflowTimelineEvent {
  return {
    eventId: overrides.eventId ?? 'wfa_1',
    eventType: overrides.eventType ?? 'workflow_step_completed',
    createdAt: overrides.createdAt ?? '2026-06-16T00:00:00Z',
    ...overrides,
  } as unknown as WorkflowTimelineEvent
}

describe('Phase 3A workflow timeline', () => {
  it('renders the empty state when there are no events', () => {
    const wrapper = mount(WorkflowTimeline, { props: { events: [] } })
    expect(wrapper.text()).toContain('No timeline events yet')
  })

  it('renders each event with its type', () => {
    const wrapper = mount(WorkflowTimeline, {
      props: { events: [event({ eventId: 'wfa_1', eventType: 'workflow_step_started' }), event({ eventId: 'wfa_2', eventType: 'workflow_step_completed' })] },
    })
    const types = wrapper.findAll('[data-testid="dev-workflow-timeline-type"]')
    expect(types.length).toBe(2)
    expect(wrapper.text()).toContain('workflow_step_started')
    expect(wrapper.text()).toContain('workflow_step_completed')
  })

  it('renders audit-link chips that emit navigate on click', async () => {
    const wrapper = mount(WorkflowTimeline, {
      props: { events: [event({ eventId: 'wfa_1', auditLinks: [{ auditId: 'evt_xyz', auditKind: 'internal', label: 'audit' }] })] },
    })
    const link = wrapper.find('[data-testid="dev-audit-id-link"]')
    expect(link.exists()).toBe(true)
    await link.trigger('click')
    expect(wrapper.emitted('navigate')).toBeTruthy()
    expect(wrapper.emitted('navigate')![0]).toEqual(['evt_xyz'])
  })

  it('renders a blocked-reason badge when an event was blocked', () => {
    const wrapper = mount(WorkflowTimeline, {
      props: { events: [event({ eventId: 'wfa_1', eventType: 'workflow_step_blocked', blockedReason: 'blocked_workflow_approval_required' })] },
    })
    const badge = wrapper.find('[data-testid="dev-workflow-timeline-blocked"]')
    expect(badge.exists()).toBe(true)
  })
})
