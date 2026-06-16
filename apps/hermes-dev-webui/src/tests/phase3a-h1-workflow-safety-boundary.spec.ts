/**
 * Phase 3A-H1 — Workflow safety boundary hardening.
 *
 * Pins the frozen capability boundary: every blocked capability (real provider,
 * provider auto-write, autonomous write, write execute, rollback execute, shell,
 * database mutation, external service write, production rollout) renders
 * Blocked; the three allowed capabilities + manual approval + audit render their
 * labels; the blocked-reason catalogue is complete and stable; and the boundary
 * never references a production home path or leaks secret material.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowSafetyBoundary from '@/components/devconsole/WorkflowSafetyBoundary.vue'
import { BOUNDARY_ROWS, formatBoundaryValue } from '@/lib/workflowFormatters'
import {
  WORKFLOW_BLOCKED_REASONS,
  isWorkflowBlockedReason,
} from '@/lib/workflowBlockedReasons'
import type { WorkflowSafetyBoundary as WorkflowSafetyBoundaryType } from '@/lib/workflowTypes'

const LEAK_PATTERNS: ReadonlyArray<RegExp> = [
  /sk-[A-Za-z0-9_-]{16,}/,
  /\/Users\/huangruibang\/\.hermes/,
  /\bstate\.db\b/,
  /<function|object at 0x/,
]

const BOUNDARY: WorkflowSafetyBoundaryType = {
  realProvider: 'blocked', providerAutoWrite: 'blocked', autonomousWrite: 'blocked',
  writeExecute: 'blocked', rollbackExecute: 'blocked', shellCommand: 'blocked',
  databaseMutation: 'blocked', externalServiceWrite: 'blocked', productionRollout: 'blocked',
  sandboxWritePreview: 'allowed', rollbackReference: 'allowed', fakeProvider: 'allowed',
  manualApproval: 'required', audit: 'enabled',
}

const BLOCKED_KEYS = [
  'realProvider', 'providerAutoWrite', 'autonomousWrite', 'writeExecute',
  'rollbackExecute', 'shellCommand', 'databaseMutation', 'externalServiceWrite',
  'productionRollout',
] as const

describe('Phase 3A-H1 workflow safety boundary', () => {
  it('renders one row per capability with a stable testid', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } })
    for (const row of BOUNDARY_ROWS) {
      expect(wrapper.find(`[data-testid="dev-workflow-boundary-${row.key}"]`).exists()).toBe(true)
    }
    // Exactly 14 capabilities — the frozen set.
    expect(BOUNDARY_ROWS.length).toBe(14)
  })

  it('every high-risk capability is Blocked', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } })
    for (const key of BLOCKED_KEYS) {
      expect(
        wrapper.find(`[data-testid="dev-workflow-boundary-${key}"]`).text(),
        key,
      ).toBe('Blocked')
    }
  })

  it('the allowed capabilities and required/enabled states render correctly', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } })
    expect(wrapper.find('[data-testid="dev-workflow-boundary-sandboxWritePreview"]').text()).toBe('Allowed')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-rollbackReference"]').text()).toBe('Allowed')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-fakeProvider"]').text()).toBe('Allowed')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-manualApproval"]').text()).toBe('Required')
    expect(wrapper.find('[data-testid="dev-workflow-boundary-audit"]').text()).toBe('Enabled')
  })

  it('the boundary never references a production path or secret material', () => {
    const html = mount(WorkflowSafetyBoundary, { props: { boundary: BOUNDARY } }).html()
    for (const pat of LEAK_PATTERNS) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect(html, `boundary leaked ${pat}`).not.toMatch(pat as any)
    }
  })

  it('formatBoundaryValue maps the four known states and falls back for unknown', () => {
    expect(formatBoundaryValue('blocked')).toBe('Blocked')
    expect(formatBoundaryValue('allowed')).toBe('Allowed')
    expect(formatBoundaryValue('required')).toBe('Required')
    expect(formatBoundaryValue('enabled')).toBe('Enabled')
    expect(formatBoundaryValue('custom')).toBe('custom')
    expect(formatBoundaryValue(null)).toBe('unknown')
    expect(formatBoundaryValue(undefined)).toBe('unknown')
  })

  it('the blocked-reason catalogue is workflow-prefixed and complete', () => {
    expect(WORKFLOW_BLOCKED_REASONS.length).toBeGreaterThanOrEqual(21)
    for (const code of WORKFLOW_BLOCKED_REASONS) {
      expect(code.startsWith('blocked_workflow_')).toBe(true)
      expect(isWorkflowBlockedReason(code)).toBe(true)
    }
  })

  it('the required safety + approval blocked reasons are present', () => {
    const required = [
      'blocked_workflow_real_provider_not_allowed',
      'blocked_workflow_autonomous_write_not_allowed',
      'blocked_workflow_provider_write_not_allowed',
      'blocked_workflow_rollback_execute_not_allowed',
      'blocked_workflow_shell_not_allowed',
      'blocked_workflow_database_not_allowed',
      'blocked_workflow_external_service_not_allowed',
      'blocked_workflow_production_not_allowed',
      'blocked_workflow_approval_required',
      'blocked_workflow_approval_expired',
      'blocked_workflow_approval_digest_mismatch',
      'blocked_workflow_approval_already_used',
      'blocked_workflow_unsafe_path_not_allowed',
      'blocked_workflow_secret_input_not_allowed',
      'blocked_workflow_raw_token_input_not_allowed',
    ]
    for (const code of required) {
      expect(isWorkflowBlockedReason(code), code).toBe(true)
    }
    expect(isWorkflowBlockedReason('not_a_real_code')).toBe(false)
    expect(isWorkflowBlockedReason(null)).toBe(false)
  })
})
