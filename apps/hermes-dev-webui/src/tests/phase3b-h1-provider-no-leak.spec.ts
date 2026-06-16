/**
 * Phase 3B-H1: Provider no-leak HARDENING.
 *
 * Exhaustive sweep of the provider surface (round-trip panel + boundary
 * component + result projection) for every forbidden value class. The DOM and
 * the store result must NEVER render: an API-key input, an API-key value, an
 * Authorization / Bearer header, a raw token, a full tokenHash, a raw secret in
 * arguments, a callable repr, a masked key fragment, or a production path.
 *
 * Provider Secret Redaction ID: PROVIDER-SECRET-3B-H1-001
 * Provider UI Security ID: PROVIDER-UI-3B-H1-001
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderRoundtripPanel from '@/components/workspace/ProviderRoundtripPanel.vue'
import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import type { ProviderBoundaryStatus, ProviderRoundtripResultData } from '@/types/api/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn().mockResolvedValue(null),
  runProviderRoundtrip: vi.fn(),
}))

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
    gatingReason: 'blocked_provider_api_key_missing',
    providerWriteBlocked: true, providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true, productionRolloutBlocked: true,
    redactionApplied: true,
  } as ProviderBoundaryStatus
}

const FORBIDDEN = [
  'sk-', 'Bearer ', 'Authorization:', 'apiKeyValue', 'accessToken',
  'refresh_token', 'client_secret', 'fullTokenHash', 'plainToken',
  'rawArguments', 'rawPrompt', 'rawResponse',
  '<function', '<bound method', 'object at 0x',
  '/Users/huangruibang/.hermes', 'state.db',
]

describe('Phase 3B-H1 provider no-leak hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders NO API-key input control anywhere in the round-trip panel', () => {
    const wrapper = mount(ProviderRoundtripPanel)
    const html = wrapper.html().toLowerCase()
    expect(html).not.toMatch(/api ?key|password|bearer|authorization/)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    expect(wrapper.find('[data-testid="provider-boundary-status"]').exists()).toBe(true)
  })

  it('renders no forbidden secret value in the boundary component', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    for (const needle of FORBIDDEN) {
      expect(html).not.toContain(needle)
    }
  })

  it('never renders a raw key prefix, masked key, or key fragment', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    expect(html).not.toMatch(/sk-\*+/i)
    expect(html).not.toMatch(/key:\s*sk-/i)
    expect(html).not.toMatch(/sk-[a-z0-9]/i)
  })

  it('does not expose a full tokenHash / plainToken field', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html().toLowerCase()
    expect(html).not.toContain('tokenhash')
    expect(html).not.toContain('plaintoken')
  })

  it('never renders a callable / function / object repr', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    expect(html).not.toMatch(/<function|<bound method|object at 0x/i)
  })

  it('a blocked write-tool result projection leaks no secret', () => {
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
        toolIds: ['clarify'], readOnlyOnly: true,
        writeToolCount: 0, providerRecursiveToolCount: 0,
      },
    }
    const store = useToolProviderStore()
    store.result = result
    const blob = JSON.stringify(store.result)
    for (const needle of FORBIDDEN) {
      expect(blob).not.toContain(needle)
    }
  })
})
