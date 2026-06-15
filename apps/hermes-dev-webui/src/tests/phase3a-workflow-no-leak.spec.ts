/**
 * Phase 3A — Workflow section no-leak tests.
 *
 * Asserts that NO workflow component ever surfaces an API key, raw token, full
 * token hash, raw arguments, secret material, callable/function repr, or a
 * production path. Safety terms may appear only in negative assertions / blocked
 * reasons / boundary labels.
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
  /\brawArguments\b|\braw_args\b|\bfullTokenHash\b|\btokenSecret\b|\bplainToken\b|\bapiKey\b/i,
  /\/Users\/huangruibang\/\.hermes/,
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

describe('Phase 3A workflow no-leak', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('the Workflow section leaks no secret / token / callable / production path', () => {
    const wrapper = mount(WorkflowSection)
    assertNoLeak(wrapper.html(), 'WorkflowSection')
  })

  it('the plan form exposes no API-key / password / shell input', () => {
    const wrapper = mount(WorkflowPlanForm)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    assertNoLeak(wrapper.html(), 'WorkflowPlanForm')
  })

  it('the plan preview renders blocked reasons without leaking secret material', () => {
    const plan = {
      workflowId: 'wf_x', workflowPlanId: 'wfp_x', schemaVersion: 'workflow_schema_v1',
      title: 't', steps: [], safetyBoundary: SAFETY_BOUNDARY,
      blockedSteps: [{ stepId: 'wfs_b', stepType: 'shell_command', title: 'bad', status: 'blocked', requiresApproval: false, requiresDryRun: false, requiresConfirmation: false, writeRequired: false, readOnly: true, localSideEffects: false, externalSideEffects: false, input: {}, safeInputSummary: {}, createdAt: '', updatedAt: '', blockedReason: 'blocked_workflow_shell_not_allowed' }],
      requiredApprovals: 0, auditPreview: {}, summary: 's', createdAt: '',
      allowedStepTypes: [], forbiddenStepTypes: [],
    } as unknown as WorkflowPlan
    const wrapper = mount(WorkflowPlanPreview, { props: { plan } })
    expect(wrapper.text()).toContain('blocked_workflow_shell_not_allowed')
    assertNoLeak(wrapper.html(), 'WorkflowPlanPreview')
  })

  it('the step list / detail render safe summaries with no raw args', () => {
    const step: WorkflowStep = {
      stepId: 'wfs_1', stepType: 'read_only_tool', title: 'Read env', status: 'completed',
      toolId: 'dev_environment_read', requiresApproval: true, requiresDryRun: true,
      requiresConfirmation: true, writeRequired: false, readOnly: true, localSideEffects: false,
      externalSideEffects: false, input: {}, safeInputSummary: { readOnly: true },
      createdAt: '', updatedAt: '',
      result: { type: 'dev_environment_read', message: 'ok', result: { readOnly: true } },
    } as unknown as WorkflowStep
    const list = mount(WorkflowStepList, { props: { steps: [step], cursorStepId: null } })
    assertNoLeak(list.html(), 'WorkflowStepList')
    const detail = mount(WorkflowStepDetail, {
      props: { step, preview: null, hasApprovalToken: false, loading: false },
    })
    assertNoLeak(detail.html(), 'WorkflowStepDetail')
  })

  it('the timeline renders audit links without leaking secrets', () => {
    const event: WorkflowTimelineEvent = {
      eventId: 'wfa_1', eventType: 'workflow_step_completed', createdAt: '2026-06-16T00:00:00Z',
      stepId: 'wfs_1', stepType: 'read_only_tool', message: 'done',
      auditLinks: [{ auditId: 'evt_abc123', auditKind: 'internal', label: 'audit' }],
    } as unknown as WorkflowTimelineEvent
    const wrapper = mount(WorkflowTimeline, { props: { events: [event] } })
    assertNoLeak(wrapper.html(), 'WorkflowTimeline')
  })

  it('the approval gate never renders the raw token', () => {
    const wrapper = mount(WorkflowApprovalGate, {
      props: { approvalRequired: true, hasToken: true, approvalId: 'cft_abc', expiresAt: '2026-06-16T00:05:00Z' },
    })
    // The raw token value is never a prop and never rendered.
    expect(wrapper.text()).toContain('cft_abc')
    assertNoLeak(wrapper.html(), 'WorkflowApprovalGate')
  })

  it('the safety boundary never references a production home path', () => {
    const wrapper = mount(WorkflowSafetyBoundary, { props: { boundary: SAFETY_BOUNDARY } })
    assertNoLeak(wrapper.html(), 'WorkflowSafetyBoundary')
  })
})
