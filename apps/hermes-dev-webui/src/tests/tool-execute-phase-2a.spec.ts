/**
 * Phase 2A frontend tests — multi-tool selector + read-only execution.
 *
 * Covers:
 *  - the selectable tool list (clarify + five read-only) is exposed and ordered
 *  - setCanonicalName switches tools and resets per-tool argument state
 *  - the generic completed-check (executionCompleted === true) recognizes every
 *    read-only tool's `<toolId>_execution_completed` decision
 *  - read-only argument building emits only declared, bounded keys
 *  - the raw confirmation token is never exposed (invariant preserved)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolExecuteStore } from '@/stores/toolExecute'
import { SELECTABLE_TOOLS, SELECTABLE_TOOL_IDS, EXECUTABLE_TOOL } from '@/constants/readOnlyTools'

vi.mock('@/api/toolExecute', () => ({
  runDryRun: vi.fn(),
  executeTool: vi.fn(),
}))

import { runDryRun, executeTool } from '@/api/toolExecute'
import type { DryRunResultData, ExecuteResultData, ToolRiskTier } from '@/types/api/toolExecute'

const READ_ONLY_TOOLS = SELECTABLE_TOOLS.filter((t) => t.id !== 'clarify')

function makeDryRunData(tool: string, riskTier: ToolRiskTier, overrides: Partial<DryRunResultData> = {}): DryRunResultData {
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
    confirmationToken: 'raw-token-secret',
    confirmationTokenId: 'ctok_abc',
    confirmationTokenExpiresAt: '2026-06-14T01:00:00+00:00',
    ...overrides,
  }
}

function makeExecuteData(tool: string, overrides: Partial<ExecuteResultData> = {}): ExecuteResultData {
  return {
    canonicalName: tool,
    exists: true,
    riskTier: 'R1',
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
    toolResult: { type: tool, message: 'ok' },
    ...overrides,
  } as ExecuteResultData
}

describe('Phase 2A selectable tools', () => {
  it('exposes exactly six tools with clarify first', () => {
    expect(SELECTABLE_TOOL_IDS).toHaveLength(6)
    expect(SELECTABLE_TOOL_IDS[0]).toBe('clarify')
    expect(EXECUTABLE_TOOL).toBe('clarify')
    expect(READ_ONLY_TOOLS).toHaveLength(5)
  })

  it('includes the five read-only inspection tools', () => {
    const ids = new Set(READ_ONLY_TOOLS.map((t) => t.id))
    expect(ids).toEqual(
      new Set([
        'tool_policy_read',
        'route_governance_read',
        'audit_events_read',
        'dev_environment_read',
        'release_status_read',
      ]),
    )
  })

  it('every read-only tool declares read-only invariants implicitly', () => {
    // The badges are rendered from a constant in the panel; here we assert the
    // metadata shape the badges derive from.
    for (const tool of SELECTABLE_TOOLS) {
      expect(tool.displayName).toBeTruthy()
      expect(tool.description).toBeTruthy()
      expect(tool.category).toBeTruthy()
    }
  })
})

describe('Phase 2A store multi-tool dispatch', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(runDryRun).mockClear()
    vi.mocked(executeTool).mockClear()
    localStorage.clear()
  })

  it('setCanonicalName switches the selected tool', () => {
    const store = useToolExecuteStore()
    expect(store.canonicalName).toBe('clarify')
    store.setCanonicalName('tool_policy_read')
    expect(store.canonicalName).toBe('tool_policy_read')
    expect(store.selectedToolMeta?.id).toBe('tool_policy_read')
  })

  it('setCanonicalName ignores unknown tool ids', () => {
    const store = useToolExecuteStore()
    store.setCanonicalName('terminal') // not selectable
    expect(store.canonicalName).toBe('clarify')
  })

  it('switching tools resets per-tool argument state', () => {
    const store = useToolExecuteStore()
    store.setQuestion('hello')
    store.setArgumentValue('includeDisabled', true)
    store.setCanonicalName('tool_policy_read')
    // clarify-specific state cleared
    expect(store.question).toBe('')
    // argumentValues cleared on switch
    expect(store.argumentValues).toEqual({})
  })

  it('builds read-only tool arguments from declared keys', async () => {
    const store = useToolExecuteStore()
    store.setCanonicalName('audit_events_read')
    store.setArgumentValue('limit', 5)
    store.setArgumentValue('toolId', 'clarify')

    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData('audit_events_read', 'R1'),
      meta: { requestId: 'r1', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    await store.runDryRun()
    expect(runDryRun).toHaveBeenCalledOnce()
    const firstCall = vi.mocked(runDryRun).mock.calls[0]
    const call = firstCall ? firstCall[0] : null
    expect(call).not.toBeNull()
    expect(call!.canonicalName).toBe('audit_events_read')
    expect(call!.argumentsPreview).toMatchObject({ limit: 5, toolId: 'clarify' })
  })

  it('recognizes each read-only tool completed decision via executionCompleted', async () => {
    for (const tool of READ_ONLY_TOOLS) {
      setActivePinia(createPinia())
      const store = useToolExecuteStore()
      store.setCanonicalName(tool.id)

      vi.mocked(runDryRun).mockResolvedValue({
        data: makeDryRunData(tool.id, tool.riskTier),
        meta: { requestId: 'r1', timestamp: '2026-06-14T00:00:00+00:00' },
      })
      await store.runDryRun()

      vi.mocked(executeTool).mockResolvedValue({
        data: makeExecuteData(tool.id),
        meta: { requestId: 'r2', timestamp: '2026-06-14T00:00:00+00:00' },
      })
      await store.runExecute()

      expect(store.status).toBe('completed')
      expect(store.executeDecision).toBe(`${tool.id}_execution_completed`)
    }
  })

  it('marks blocked when executionCompleted is false', async () => {
    const store = useToolExecuteStore()
    store.setCanonicalName('tool_policy_read')
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData('tool_policy_read', 'R0'),
      meta: { requestId: 'r1', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    await store.runDryRun()
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData('tool_policy_read', {
        executionCompleted: false,
        decision: 'blocked_by_allowlist',
        toolHandlerCalled: false,
      }),
      meta: { requestId: 'r2', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    await store.runExecute()
    expect(store.status).toBe('blocked')
  })

  it('never exposes the raw confirmation token on the store', async () => {
    const store = useToolExecuteStore()
    store.setCanonicalName('release_status_read')
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData('release_status_read', 'R1'),
      meta: { requestId: 'r1', timestamp: '2026-06-14T00:00:00+00:00' },
    })
    await store.runDryRun()
    // The raw token must never be a property of the store.
    expect((store as unknown as Record<string, unknown>).confirmationToken).toBeUndefined()
    expect((store as unknown as Record<string, unknown>)._confirmationToken).toBeUndefined()
    // Only the safe id is exposed.
    expect(store.confirmationTokenId).toBe('ctok_abc')
  })
})
