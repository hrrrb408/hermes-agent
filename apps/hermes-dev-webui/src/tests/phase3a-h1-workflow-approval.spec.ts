/**
 * Phase 3A-H1 — Workflow approval gate hardening.
 *
 * Adversarial approval-gate tests: the gate reflects required / ready / none,
 * Execute is disabled until an approval token exists and is otherwise enabled,
 * write-execute and rollback-execute affordances are NEVER offered (preview /
 * reference only), and the gate renders the public approval id (cft_…) but
 * NEVER the raw single-use token, a full token hash, or secret material.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowApprovalGate from '@/components/devconsole/WorkflowApprovalGate.vue'
import WorkflowStepDetail from '@/components/devconsole/WorkflowStepDetail.vue'
import type { WorkflowStep } from '@/lib/workflowTypes'

const LEAK_PATTERNS: ReadonlyArray<RegExp> = [
  /sk-[A-Za-z0-9_-]{16,}/,
  /Bearer\s+\S+/i,
  /<function|<bound method|object at 0x/,
  /\brawArguments\b|\bfullTokenHash\b|\btokenSecret\b|\bplainToken\b/i,
  /\/Users\/huangruibang\/\.hermes/,
]

function assertNoLeak(html: string, label: string): void {
  for (const pat of LEAK_PATTERNS) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(html, `${label} leaked ${pat}`).not.toMatch(pat as any)
  }
}

function baseStep(overrides: Partial<WorkflowStep> = {}): WorkflowStep {
  return {
    stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'planned',
    toolId: 'dev_environment_read', requiresApproval: true, requiresDryRun: true,
    requiresConfirmation: true, writeRequired: false, readOnly: true, localSideEffects: false,
    externalSideEffects: false, input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '',
    ...overrides,
  } as unknown as WorkflowStep
}

describe('Phase 3A-H1 workflow approval gate', () => {
  it('required / ready / none states render the correct testid', () => {
    const required = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: false, approvalId: null, expiresAt: null },
    })
    expect(required.find('[data-testid="dev-workflow-approval-required"]').exists()).toBe(true)

    const ready = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: true, approvalId: 'cft_abc', expiresAt: '2026-06-16T00:05:00Z' },
    })
    expect(ready.find('[data-testid="dev-workflow-approval-ready"]').exists()).toBe(true)

    const none = mount(WorkflowApprovalGate, {
      props: { approvalRequired: false, hasToken: false, approvalId: null, expiresAt: null },
    })
    expect(none.find('[data-testid="dev-workflow-approval-none"]').exists()).toBe(true)
  })

  it('Execute is disabled before approval and enabled once a token exists', () => {
    const before = mount(WorkflowStepDetail, {
      props: { step: baseStep(), preview: null, hasApprovalToken: false, loading: false },
    })
    const btnBefore = before.find('[data-testid="dev-workflow-execute-btn"]')
    expect(btnBefore.exists()).toBe(true)
    expect(btnBefore.attributes('disabled')).toBeDefined()

    const after = mount(WorkflowStepDetail, {
      props: { step: baseStep({ status: 'previewed' }), preview: null, hasApprovalToken: true, loading: false },
    })
    expect(after.find('[data-testid="dev-workflow-execute-btn"]').attributes('disabled')).toBeUndefined()
  })

  it('Execute is disabled while loading', () => {
    const wrapper = mount(WorkflowStepDetail, {
      props: { step: baseStep({ status: 'previewed' }), preview: null, hasApprovalToken: true, loading: true },
    })
    expect(wrapper.find('[data-testid="dev-workflow-execute-btn"]').attributes('disabled')).toBeDefined()
  })

  it('write-execute and rollback-execute are never offered — preview/reference only', () => {
    for (const stepType of ['sandbox_write_preview', 'rollback_reference'] as const) {
      const wrapper = mount(WorkflowStepDetail, {
        props: { step: baseStep({ stepType, status: 'previewed' }), preview: null, hasApprovalToken: true, loading: false },
      })
      // A write/rollback step surfaces the blocked badge, not an execute path.
      expect(wrapper.find('[data-testid="dev-workflow-write-execute-blocked"]').exists()).toBe(true)
    }
  })

  it('the approval gate renders the public approval id but never the raw token', () => {
    const wrapper = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: true, approvalId: 'cft_publicid', expiresAt: '2026-06-16T00:05:00Z' },
    })
    const html = wrapper.html()
    // The public correlation id is shown.
    expect(html).toContain('cft_publicid')
    // The raw secret half of a token (cft_x.secret) is never a rendered value.
    expect(html).not.toMatch(/cft_publicid\.[A-Za-z0-9_-]+/)
    assertNoLeak(html, 'WorkflowApprovalGate')
  })

  it('the step detail never leaks raw args / token / callable / production path', () => {
    const wrapper = mount(WorkflowStepDetail, {
      props: {
        step: baseStep({ status: 'completed' }),
        preview: null,
        hasApprovalToken: false,
        loading: false,
      },
    })
    assertNoLeak(wrapper.html(), 'WorkflowStepDetail')
  })
})
