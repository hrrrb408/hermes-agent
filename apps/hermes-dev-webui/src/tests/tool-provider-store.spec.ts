/**
 * Tests for the Provider round-trip Pinia store (Phase 2B).
 *
 * Covers the mode/message/selection state, the round-trip success + blocked
 * paths, and the invariant that no API key is ever accepted or sent.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolProviderStore } from '@/stores/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  runProviderRoundtrip: vi.fn(),
}))

import { runProviderRoundtrip } from '@/api/toolProvider'
import type { ProviderRoundtripResultData } from '@/types/api/toolProvider'

function makeResult(overrides: Partial<ProviderRoundtripResultData> = {}): ProviderRoundtripResultData {
  return {
    status: 'completed',
    mode: 'provider_roundtrip',
    providerMode: 'fake',
    providerRequestId: 'prqs_test',
    providerResponseId: 'prsp_test',
    providerSchemaSent: true,
    providerApiCalled: true,
    externalNetworkCalled: false,
    readOnlyOnly: true,
    toolWriteDisabled: true,
    toolCalls: [
      { id: 'ptc_1', name: 'route_governance_read', arguments: {}, status: 'valid', blockedReason: null },
    ],
    toolResults: [
      { toolCallId: 'ptc_1', toolId: 'route_governance_read', status: 'executed', executed: true, blockedReason: null },
    ],
    finalAnswer: 'Provider round-trip completed.',
    providerAuditIds: ['prau_1', 'prau_2'],
    blockedReason: null,
    schemaSummary: {
      schemaVersion: 1,
      bundleVersion: 1,
      toolCount: 6,
      toolIds: ['clarify', 'tool_policy_read', 'route_governance_read', 'audit_events_read', 'dev_environment_read', 'release_status_read'],
      readOnlyOnly: true,
      writeToolCount: 0,
      providerRecursiveToolCount: 0,
    },
    ...overrides,
  }
}

describe('toolProvider store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(runProviderRoundtrip).mockReset()
  })

  it('defaults to disabled mode with all tools selected', () => {
    const store = useToolProviderStore()
    expect(store.providerMode).toBe('disabled')
    expect(store.selectedToolIds.length).toBeGreaterThan(0)
    expect(store.canRun).toBe(false) // disabled → cannot run
  })

  it('switching to fake + message enables run', () => {
    const store = useToolProviderStore()
    store.setProviderMode('fake')
    store.setMessage('check route governance')
    expect(store.canRun).toBe(true)
  })

  it('marks real mode as blocked-surfaced', () => {
    const store = useToolProviderStore()
    store.setProviderMode('real')
    expect(store.isRealBlocked).toBe(true)
  })

  it('toggleTool adds and removes a tool id', () => {
    const store = useToolProviderStore()
    const initial = store.selectedToolIds.length
    store.clearAllTools()
    expect(store.selectedToolIds).toEqual([])
    store.toggleTool('route_governance_read')
    expect(store.selectedToolIds).toEqual(['route_governance_read'])
    store.toggleTool('route_governance_read')
    expect(store.selectedToolIds).toEqual([])
    expect(initial).toBeGreaterThan(0)
  })

  it('runRoundtrip stores a completed result', async () => {
    vi.mocked(runProviderRoundtrip).mockResolvedValue({
      data: makeResult(),
      meta: { requestId: 'r1', timestamp: 't1' },
    } as never)
    const store = useToolProviderStore()
    store.setProviderMode('fake')
    store.setMessage('check route governance')
    await store.runRoundtrip()
    expect(store.status).toBe('completed')
    expect(store.result?.providerMode).toBe('fake')
    expect(store.result?.externalNetworkCalled).toBe(false)
  })

  it('runRoundtrip records blocked status', async () => {
    vi.mocked(runProviderRoundtrip).mockResolvedValue({
      data: makeResult({ status: 'blocked', blockedReason: 'blocked_provider_real_mode_not_enabled', providerMode: 'real' }),
      meta: { requestId: 'r1', timestamp: 't1' },
    } as never)
    const store = useToolProviderStore()
    store.setProviderMode('real')
    store.setMessage('x')
    await store.runRoundtrip()
    expect(store.status).toBe('blocked')
    expect(store.result?.blockedReason).toBe('blocked_provider_real_mode_not_enabled')
  })

  it('runRoundtrip handles API errors', async () => {
    vi.mocked(runProviderRoundtrip).mockRejectedValue(new Error('boom'))
    const store = useToolProviderStore()
    store.setProviderMode('fake')
    store.setMessage('x')
    await store.runRoundtrip()
    expect(store.status).toBe('error')
    expect(store.error).toBeTruthy()
  })

  it('never sends an API key in the request body', async () => {
    vi.mocked(runProviderRoundtrip).mockResolvedValue({
      data: makeResult(),
      meta: { requestId: 'r1', timestamp: 't1' },
    } as never)
    const store = useToolProviderStore()
    store.setProviderMode('fake')
    store.setMessage('x')
    await store.runRoundtrip()
    const calls = vi.mocked(runProviderRoundtrip).mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const call = calls[0]![0]
    expect(JSON.stringify(call)).not.toMatch(/apiKey|api_key|authorization|bearer/i)
  })
})
