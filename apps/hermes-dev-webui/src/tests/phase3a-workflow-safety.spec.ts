/**
 * Phase 3A — Workflow safety boundary tests.
 *
 * Asserts the frozen boundary renders every capability with the correct
 * Allowed / Blocked / Required / Enabled label, and that the real provider,
 * autonomous write, shell, database, external service, and production rollout
 * capabilities are all Blocked.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowSafetyBoundary from '@/components/devconsole/WorkflowSafetyBoundary.vue'
import { WORKFLOW_BLOCKED_REASONS, isWorkflowBlockedReason } from '@/lib/workflowBlockedReasons'
import { BOUNDARY_ROWS, formatBoundaryValue } from '@/lib/workflowFormatters'
import type { WorkflowSafetyBoundary as WorkflowSafetyBoundaryType } from '@/lib/workflowTypes'

const BOUNDARY: WorkflowSafetyBoundaryType = {
  realProvider: 'blocked', providerAutoWrite: 'blocked', autonomousWrite: 'blocked',
  writeExecute: 'blocked', rollbackExecute: 'blocked', shellCommand: 'blocked',
  databaseMutation: 'blocked', externalServiceWrite: 'blocked', productionRollout: 'blocked',
  sandboxWritePreview: 'allowed', rollbackReference: 'allowed', fakeProvider: 'allowed',
  manualApproval: 'required', audit: 'enabled',
}

describe('Phase 3A workflow safety boundary', () => {
  it('renders the boundary panel with every capability', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } })
    for (const row of BOUNDARY_ROWS) {
      expect(wrapper.find(`[data-testid="dev-workflow-boundary-${row.key}"]`).exists()).toBe(true)
    }
  })

  it('blocks real provider, autonomous write, shell, database, external service, production', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } })
    for (const key of ['realProvider', 'autonomousWrite', 'shellCommand', 'databaseMutation', 'externalServiceWrite', 'productionRollout', 'rollbackExecute', 'writeExecute', 'providerAutoWrite'] as const) {
      expect(wrapper.find(`[data-testid="dev-workflow-boundary-${key}"]`).text()).toBe('Blocked')
    }
  })

  it('allows sandbox write preview, rollback reference, and fake provider; requires manual approval', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } })
    expect(wrapper.find('[data-testid="dev-workflow-boundary-sandboxWritePreview"]').text()).toBe('Allowed')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-rollbackReference"]').text()).toBe('Allowed')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-fakeProvider"]').text()).toBe('Allowed')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-manualApproval"]').text()).toBe('Required')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-audit"]').text()).toBe('Enabled')
  })

  it('formatBoundaryValue maps known values and falls back for unknown', () => {
    expect(formatBoundaryValue('blocked')).toBe('Blocked')
    expect(formatBoundaryValue('allowed')).toBe('Allowed')
    expect(formatBoundaryValue('required')).toBe('Required')
    expect(formatBoundaryValue('enabled')).toBe('Enabled')
    expect(formatBoundaryValue('custom')).toBe('custom')
    expect(formatBoundaryValue(null)).toBe('unknown')
  })

  it('every workflow blocked reason is recognized', () => {
    expect(WORKFLOW_BLOCKED_REASONS.length).toBeGreaterThanOrEqual(20)
    expect(isWorkflowBlockedReason('blocked_workflow_shell_not_allowed')).toBe(true)
    expect(isWorkflowBlockedReason('blocked_workflow_approval_required')).toBe(true)
    expect(isWorkflowBlockedReason('not_a_real_code')).toBe(false)
    expect(isWorkflowBlockedReason(null)).toBe(false)
  })
})
