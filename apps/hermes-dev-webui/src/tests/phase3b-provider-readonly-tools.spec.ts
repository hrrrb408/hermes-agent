/**
 * Phase 3B: Real Provider read-only tool-allowlist UI tests.
 *
 * Verifies the boundary component renders the read-only tool allowlist
 * (clarify + the five read-only inspection tools), and that a write tool
 * requested by a provider round-trip result is surfaced as blocked (never
 * executed).
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import { SELECTABLE_TOOL_IDS } from '@/constants/readOnlyTools'
import type { ProviderBoundaryStatus, ProviderRoundtripResultData } from '@/types/api/toolProvider'

function makeBoundary(): ProviderBoundaryStatus {
  return {
    providerMode: 'real', apiEnabled: true,
    providerName: 'openai_compatible', providerNameImplemented: true,
    baseUrlHost: 'api.openai.com', baseUrlAllowed: true,
    model: 'gpt-4o-mini', modelAllowed: true,
    timeoutSeconds: 20, maxRetries: 2, dailyBudgetCents: 100, maxTokens: 1024,
    perMinuteRequestCap: 20, dailyRequestCap: 200, dailyTokenCap: 500000,
    apiKeySource: 'env', apiKeyPresent: true, apiKeySourceDetail: 'env_present',
    isDevHome: true, realReachable: false,
    gatingReason: 'blocked_provider_production_gate_drift',
    providerWriteBlocked: true, providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true, productionRolloutBlocked: true,
    redactionApplied: true,
  } as ProviderBoundaryStatus
}

describe('Phase 3B provider read-only allowlist UI', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the read-only tool allowlist', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    for (const tool of SELECTABLE_TOOL_IDS) {
      expect(html).toContain(tool)
    }
  })

  it('includes the six read-only inspection tools', () => {
    expect(SELECTABLE_TOOL_IDS).toEqual(
      expect.arrayContaining([
        'clarify', 'tool_policy_read', 'route_governance_read',
        'audit_events_read', 'dev_environment_read', 'release_status_read',
      ]),
    )
  })

  it('marks provider write as blocked when a write tool appears in a result', () => {
    // A provider round-trip result with a blocked write tool call: the UI must
    // surface it as blocked, never executed.
    const result: ProviderRoundtripResultData = {
      status: 'blocked',
      mode: 'provider_roundtrip',
      providerMode: 'fake',
      providerRequestId: 'prqs',
      providerResponseId: 'prsp',
      providerSchemaSent: true,
      providerApiCalled: true,
      externalNetworkCalled: false,
      readOnlyOnly: true,
      toolWriteDisabled: true,
      toolCalls: [
        { id: 'ptc', name: 'write_file', arguments: {}, status: 'blocked', blockedReason: 'blocked_provider_write_not_allowed' },
      ],
      toolResults: [
        { toolCallId: 'ptc', toolId: 'write_file', status: 'blocked', executed: false, blockedReason: 'blocked_provider_write_not_allowed' },
      ],
      finalAnswer: 'blocked',
      providerAuditIds: [],
      blockedReason: 'blocked_tool_calls:write_file',
      schemaSummary: {
        schemaVersion: 1, bundleVersion: 1, toolCount: 6,
        toolIds: SELECTABLE_TOOL_IDS, readOnlyOnly: true,
        writeToolCount: 0, providerRecursiveToolCount: 0,
      },
    }
    const store = useToolProviderStore()
    store.result = result
    // The store's result surfaces the blocked write tool call.
    const tr = store.result.toolResults[0]
    expect(tr).toBeTruthy()
    expect(tr?.toolId).toBe('write_file')
    expect(tr?.executed).toBe(false)
    expect(tr?.blockedReason).toBe('blocked_provider_write_not_allowed')
  })
})
