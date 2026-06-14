/**
 * Phase 2A component tests — multi-tool selector + per-tool argument forms.
 *
 * Covers:
 *  - the tool selector renders all six selectable tools
 *  - the default selection is clarify (backward compatible)
 *  - selecting a read-only tool hides clarify fields and shows the tool's args
 *  - safety badges render (read-only, provider off, no side effects)
 *  - the structured read-only result renders on a mocked completed execute
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ToolExecutePanel from '@/components/workspace/ToolExecutePanel.vue'
import type { DryRunResultData, ExecuteResultData, ToolRiskTier } from '@/types/api/toolExecute'

vi.mock('@/api/toolExecute', () => ({
  runDryRun: vi.fn(),
  executeTool: vi.fn(),
}))

import { runDryRun, executeTool } from '@/api/toolExecute'

function makeDryRunData(tool: string, riskTier: ToolRiskTier): DryRunResultData {
  return {
    canonicalName: tool,
    exists: true,
    riskTier,
    decision: 'would_allow',
    reasonCodes: [],
    policyNotes: [],
    redactedArgumentsPreview: {},
    forbiddenFields: [],
    missingRequiredFields: [],
    executionAllowed: false,
    dispatchAllowed: false,
    providerSchemaAllowed: false,
    auditWritten: true,
    dryRunDecisionDigest: 'sha256:abcdef',
    digestAlgorithm: 'sha256',
    digestPackageVersion: '1',
    canonicalizationVersion: 'json-sort-v1',
    confirmationToken: 'raw-secret',
    confirmationTokenId: 'ctok_abc',
    confirmationTokenExpiresAt: '2026-06-14T01:00:00+00:00',
  }
}

function makeExecuteData(tool: string, riskTier: ToolRiskTier, result: Record<string, unknown>): ExecuteResultData {
  return {
    canonicalName: tool,
    exists: true,
    riskTier,
    decision: `${tool}_execution_completed`,
    reasonCodes: [],
    policyNotes: [],
    errorCode: null,
    executionAllowed: false,
    dispatchAllowed: false,
    providerSchemaAllowed: false,
    toolHandlerCalled: true,
    providerApiCalled: false,
    executionStarted: true,
    executionCompleted: true,
    executionAttempted: true,
    handlerCallId: 'thc_abc',
    handlerCallStatus: 'completed',
    executionStatus: 'completed',
    postExecutionAuditId: 'pexa_abc',
    postExecutionAuditStatus: 'written',
    sideEffects: {
      providerSchemaSent: false,
      providerApiCalled: false,
      externalSideEffects: false,
      filesystemChanged: false,
      networkCalled: false,
    },
    resultPreview: { available: true, previewType: tool, previewSizeBytes: 100, truncated: false },
    preExecutionAuditId: 'pea_abc',
    executeRequestId: 'exe_abc',
    preExecutionAuditStatus: 'written',
    handlerLookupId: 'hl_abc',
    handlerLookupStatus: 'found',
    handlerDescriptor: {},
    dispatchId: 'dsp_abc',
    dispatchStatus: 'planned',
    dispatchPlan: {},
    toolResult: { type: tool, message: 'ok', result },
  } as ExecuteResultData
}

describe('ToolExecutePanel Phase 2A — selector', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(runDryRun).mockClear()
    vi.mocked(executeTool).mockClear()
  })

  function mountPanel() {
    return mount(ToolExecutePanel, { attachTo: document.body })
  }

  it('renders a selector with all six selectable tools', () => {
    const wrapper = mountPanel()
    const select = wrapper.find('#tool-execute-canonical')
    expect(select.exists()).toBe(true)
    const options = select.findAll('option')
    expect(options).toHaveLength(6)
    const ids = options.map((o) => o.attributes('value'))
    expect(ids).toEqual([
      'clarify',
      'tool_policy_read',
      'route_governance_read',
      'audit_events_read',
      'dev_environment_read',
      'release_status_read',
    ])
  })

  it('defaults to clarify (backward compatible)', () => {
    const wrapper = mountPanel()
    expect((wrapper.find('#tool-execute-canonical').element as HTMLSelectElement).value).toBe('clarify')
  })

  it('shows clarify question/choices fields by default', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('#tool-execute-question').exists()).toBe(true)
    expect(wrapper.find('#tool-execute-choices').exists()).toBe(true)
  })

  it('switching to a read-only tool shows its argument form and hides clarify fields', async () => {
    const wrapper = mountPanel()
    await wrapper.find('#tool-execute-canonical').setValue('audit_events_read')
    // clarify fields hidden
    expect(wrapper.find('#tool-execute-question').exists()).toBe(false)
    // audit_events_read declares a limit integer arg
    expect(wrapper.find('#tool-execute-arg-limit').exists()).toBe(true)
    // and a toolId string arg
    expect(wrapper.find('#tool-execute-arg-toolId').exists()).toBe(true)
  })

  it('renders the safety badges for a read-only tool', async () => {
    const wrapper = mountPanel()
    await wrapper.find('#tool-execute-canonical').setValue('route_governance_read')
    const text = wrapper.text()
    expect(text).toContain('Read-only')
    expect(text).toContain('Provider: off')
    expect(text).toContain('Write: off')
    expect(text).toContain('No external side effects')
  })

  it('renders the structured result on a completed read-only execute', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData('tool_policy_read', 'R0'),
      meta: { requestId: 'r1', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData('tool_policy_read', 'R0', { staticAllowlistSize: 6 }),
      meta: { requestId: 'r2', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    const wrapper = mountPanel()
    await wrapper.find('#tool-execute-canonical').setValue('tool_policy_read')
    await wrapper.find('#tool-execute-dry-run').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('would_allow'))
    await wrapper.find('#tool-execute-run').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Completed'))
    const structured = wrapper.find('#tool-execute-structured-result')
    expect(structured.exists()).toBe(true)
    expect(structured.text()).toContain('staticAllowlistSize')
  })

  it('renders the side-effect flags as false after a read-only execute', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData('release_status_read', 'R1'),
      meta: { requestId: 'r1', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData('release_status_read', 'R1', { phase1gStatus: 'SEALED' }),
      meta: { requestId: 'r2', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    const wrapper = mountPanel()
    await wrapper.find('#tool-execute-canonical').setValue('release_status_read')
    await wrapper.find('#tool-execute-dry-run').trigger('click')
    await wrapper.find('#tool-execute-run').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Completed'))
    const flags = wrapper.find('#tool-execute-side-effects')
    expect(flags.text()).toContain('false')
  })

  it('clarify still renders the legacy question/choices (Phase 1G preserved)', async () => {
    const wrapper = mountPanel()
    // select clarify explicitly
    await wrapper.find('#tool-execute-canonical').setValue('clarify')
    expect(wrapper.find('#tool-execute-question').exists()).toBe(true)
    expect(wrapper.find('#tool-execute-choices').exists()).toBe(true)
    // no read-only structured-result block initially
    expect(wrapper.find('#tool-execute-arg-limit').exists()).toBe(false)
  })
})
