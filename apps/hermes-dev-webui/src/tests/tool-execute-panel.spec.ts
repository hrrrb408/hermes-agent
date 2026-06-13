/**
 * Tests for the ToolExecutePanel component (Phase 1G-04-30).
 *
 * Covers rendering of the clarify-only workbench, the dry-run/execute
 * controls, safe result surfacing, and the invariant that the raw
 * confirmation token is never rendered in the DOM.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ToolExecutePanel from '@/components/workspace/ToolExecutePanel.vue'
import { useToolExecuteStore } from '@/stores/toolExecute'
import type {
  DryRunResultData,
  ExecuteResultData,
} from '@/types/api/toolExecute'

vi.mock('@/api/toolExecute', () => ({
  runDryRun: vi.fn(),
  executeTool: vi.fn(),
}))

import { runDryRun, executeTool } from '@/api/toolExecute'

function makeDryRunData(overrides: Partial<DryRunResultData> = {}): DryRunResultData {
  return {
    canonicalName: 'clarify',
    exists: true,
    riskTier: 'R0',
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
    dryRunDecisionDigest: 'sha256:abcdef1234567890',
    digestAlgorithm: 'sha256',
    digestPackageVersion: '1',
    canonicalizationVersion: 'json-sort-v1',
    confirmationToken: 'raw-secret-token-do-not-render',
    confirmationTokenId: 'ctok_abc',
    confirmationTokenExpiresAt: '2026-06-13T01:00:00+00:00',
    ...overrides,
  }
}

function makeExecuteData(overrides: Partial<ExecuteResultData> = {}): ExecuteResultData {
  return {
    canonicalName: 'clarify',
    exists: true,
    riskTier: 'R0',
    decision: 'clarify_execution_completed',
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
    },
    toolResult: { type: 'clarify', message: 'Which?', questions: [] },
    ...overrides,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('ToolExecutePanel', () => {
  it('renders the clarify-only workbench with Dry Run and Execute controls', () => {
    const wrapper = mount(ToolExecutePanel)
    expect(wrapper.find('#tool-execute-canonical').exists()).toBe(true)
    expect(wrapper.find('#tool-execute-dry-run').exists()).toBe(true)
    expect(wrapper.find('#tool-execute-run').exists()).toBe(true)
    const input = wrapper.find('#tool-execute-canonical').element as HTMLInputElement
    expect(input.value).toBe('clarify')
  })

  it('runs a dry-run and surfaces the safe decision without the raw token', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const wrapper = mount(ToolExecutePanel)
    await wrapper.find('#tool-execute-dry-run').trigger('click')
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('would_allow')
    })
    expect(wrapper.text()).toContain('ctok_abc')
    expect(wrapper.text()).not.toContain('raw-secret-token-do-not-render')
  })

  it('shows the completed result and false side-effect flags after execute', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData(),
      meta: { requestId: 'r2', timestamp: 't2' },
    })
    const wrapper = mount(ToolExecutePanel)
    await wrapper.find('#tool-execute-dry-run').trigger('click')
    await vi.waitFor(() => {
      expect(wrapper.find('#tool-execute-run').attributes('disabled')).toBeUndefined()
    })
    await wrapper.find('#tool-execute-run').trigger('click')
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('clarify_execution_completed')
    })
    expect(wrapper.text()).toContain('thc_abc')
    expect(wrapper.text()).toContain('pexa_abc')
    const flags = wrapper.find('#tool-execute-side-effects')
    expect(flags.exists()).toBe(true)
    expect(flags.text()).toContain('false')
  })

  it('shows the blocked decision when the handler-call gate blocks', async () => {
    const store = useToolExecuteStore()
    store.executeResult = makeExecuteData({
      decision: 'blocked_tool_handler_call_not_enabled',
      toolHandlerCalled: false,
      executionStarted: false,
      executionCompleted: false,
      executionAttempted: true,
      handlerCallId: undefined,
      postExecutionAuditId: undefined,
    })
    const wrapper = mount(ToolExecutePanel)
    expect(wrapper.text()).toContain('blocked_tool_handler_call_not_enabled')
  })
})
