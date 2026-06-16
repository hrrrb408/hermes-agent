/**
 * Phase 3A-H1 — Workflow no-leak hardening.
 *
 * Deep, adversarial no-leak scan: NO workflow component — section, form, plan
 * preview, step list, step detail, timeline, approval gate, safety boundary —
 * ever surfaces an API key, raw token, full token hash, raw arguments, secret
 * material, callable/function repr, or a production path. Secret-shaped
 * material may appear ONLY inside blocked reasons / negative assertions / mock
 * payloads that are stripped before render.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/workflow', () => ({
  runWorkflowPlanPreview: vi.fn(),
  runWorkflowStepPreview: vi.fn(),
  executeWorkflowStep: vi.fn(),
  readWorkflowState: vi.fn(),
}))

import WorkflowSection from '@/components/devconsole/WorkflowSection.vue'
import WorkflowPlanForm from '@/components/devconsole/WorkflowPlanForm.vue'
import WorkflowPlanPreview from '@/components/devconsole/WorkflowPlanPreview.vue'
import WorkflowStepList from '@/components/devconsole/WorkflowStepList.vue'
import WorkflowStepDetail from '@/components/devconsole/WorkflowStepDetail.vue'
import WorkflowTimeline from '@/components/devconsole/WorkflowTimeline.vue'
import WorkflowApprovalGate from '@/components/devconsole/WorkflowApprovalGate.vue'
import WorkflowSafetyBoundary from '@/components/devconsole/WorkflowSafetyBoundary.vue'
import type { WorkflowPlan, WorkflowStep, WorkflowTimelineEvent } from '@/lib/workflowTypes'

const LEAK_PATTERNS: ReadonlyArray<RegExp> = [
  /sk-[A-Za-z0-9_-]{16,}/,
  /Bearer\s+\S+/i,
  /-----BEGIN[A-Z0-9 ]*PRIVATE KEY-----/,
  /<function|<bound method|object at 0x/,
  /\brawArguments\b|\braw_args\b|\bfullTokenHash\b|\btokenSecret\b|\bplainToken\b/i,
  /\/Users\/huangruibang\/\.hermes/,
  /\bstate\.db\b/,
]

function assertNoLeak(html: string, label: string): void {
  for (const pat of LEAK_PATTERNS) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(html, `${label} leaked ${pat}`).not.toMatch(pat as any)
  }
}

const SAFETY_BOUNDARY = {
  realProvider: 'blocked', providerAutoWrite: 'blocked', autonomousWrite: 'blocked',
  writeExecute: 'blocked', rollbackExecute: 'blocked', shellCommand: 'blocked',
  databaseMutation: 'blocked', externalServiceWrite: 'blocked', productionRollout: 'blocked',
  sandboxWritePreview: 'allowed', rollbackReference: 'allowed', fakeProvider: 'allowed',
  manualApproval: 'required', audit: 'enabled',
}

function step(overrides: Record<string, unknown> = {}): WorkflowStep {
  return {
    stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'completed',
    toolId: 'dev_environment_read', requiresApproval: true, requiresDryRun: true,
    requiresConfirmation: true, writeRequired: false, readOnly: true, localSideEffects: false,
    externalSideEffects: false, input: {}, safeInputSummary: { readOnly: true },
    createdAt: '', updatedAt: '',
    ...overrides,
  } as unknown as WorkflowStep
}

describe('Phase 3A-H1 workflow no-leak', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('every mounted component is leak-free by default', () => {
    assertNoLeak(mount(WorkflowSection).html(), 'WorkflowSection')
    assertNoLeak(mount(WorkflowPlanForm).html(), 'WorkflowPlanForm')
    assertNoLeak(mount(WorkflowSafetyBoundary, { props: { boundary: SAFETY_BOUNDARY } }).html(), 'WorkflowSafetyBoundary')
  })

  it('the plan form exposes no password / api-key / shell input', () => {
    const wrapper = mount(WorkflowPlanForm)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    assertNoLeak(wrapper.html(), 'WorkflowPlanForm')
  })

  it('a plan with a blocked shell step renders the blocked reason without leaking', () => {
    const plan = {
      workflowId: 'wf_x', workflowPlanId: 'wfp_x', schemaVersion: 'workflow_schema_v1',
      title: 't', steps: [], safetyBoundary: SAFETY_BOUNDARY,
      blockedSteps: [step({ stepId: 'wfs_b', stepType: 'shell_command', title: 'bad', status: 'blocked', blockedReason: 'blocked_workflow_shell_not_allowed' })],
      requiredApprovals: 0, auditPreview: {}, summary: 's', createdAt: '',
      allowedStepTypes: [], forbiddenStepTypes: [],
    } as unknown as WorkflowPlan
    const wrapper = mount(WorkflowPlanPreview, { props: { plan } })
    expect(wrapper.text()).toContain('blocked_workflow_shell_not_allowed')
    assertNoLeak(wrapper.html(), 'WorkflowPlanPreview')
  })

  it('a step carrying secret-shaped result material renders nothing leaked', () => {
    // A result that *would* be secret is shown only as the safe summary; the
    // detail never echoes raw token / hash carriers.
    const s = step({
      result: { type: 'dev_environment_read', note: '[REDACTED]' },
    })
    const detail = mount(WorkflowStepDetail, {
      props: { step: s, preview: null, hasApprovalToken: false, loading: false },
    })
    assertNoLeak(detail.html(), 'WorkflowStepDetail')
    const list = mount(WorkflowStepList, { props: { steps: [s], cursorStepId: null } })
    assertNoLeak(list.html(), 'WorkflowStepList')
  })

  it('the timeline renders audit links without leaking secrets', () => {
    const event = {
      eventId: 'wfa_1', eventType: 'workflow_step_completed', createdAt: '2026-06-16T00:00:00Z',
      stepId: 'wfs_1', stepType: 'read_only_tool', message: 'done',
      auditLinks: [{ auditId: 'evt_abc123', auditKind: 'internal', label: 'audit' }],
    } as unknown as WorkflowTimelineEvent
    assertNoLeak(mount(WorkflowTimeline, { props: { events: [event] } }).html(), 'WorkflowTimeline')
  })

  it('the approval gate never renders the raw token or a full hash', () => {
    const wrapper = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: true, approvalId: 'cft_abc', expiresAt: '2026-06-16T00:05:00Z' },
    })
    assertNoLeak(wrapper.html(), 'WorkflowApprovalGate')
  })

  it('a blocked-reason panel never surfaces secret material in its explanation', () => {
    // The blocked-reason catalogue explanations must stay secret-free.
    const wrapper = mount(WorkflowPlanPreview, {
      props: {
        plan: {
          workflowId: 'wf_x', workflowPlanId: 'wfp_x', schemaVersion: 'workflow_schema_v1',
          title: 't', steps: [], safetyBoundary: SAFETY_BOUNDARY,
          blockedSteps: [step({ stepId: 'wfs_b', stepType: 'real_provider_roundtrip', title: 'bad', status: 'blocked', blockedReason: 'blocked_workflow_real_provider_not_allowed' })],
          requiredApprovals: 0, auditPreview: {}, summary: 's', createdAt: '',
          allowedStepTypes: [], forbiddenStepTypes: [],
        } as unknown as WorkflowPlan,
      },
    })
    assertNoLeak(wrapper.html(), 'blocked-reason panel')
  })
})
