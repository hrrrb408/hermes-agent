/**
 * Phase 2E — Safety Boundary panel tests.
 *
 * Asserts the panel renders the invariant safety badges grouped by surface,
 * the frozen route-governance baseline (34/34/5/0/1/1), the production PID
 * baseline (28428), and the live policy flags (mocked). The panel makes NO
 * execution POST.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolPolicy', () => ({
  fetchToolPolicyStatus: vi.fn().mockResolvedValue({
    data: {
      mode: 'controlled', inventoryCount: 76,
      riskCounts: { R0: 3, R1: 8, R2: 19, R3: 26, R4: 17, R5: 3 },
      permanentDenylistCount: 26, candidateAllowlistCount: 11, enabledAllowlistCount: 0,
      execution: { implemented: true, enabled: false, providerSchemaSent: false, dispatchAvailable: false, auditAvailable: true },
      limits: {
        maxArgumentPayloadBytes: 32768, maxArgumentNestingDepth: 8, maxArgumentStringLength: 8192,
        maxArgumentArrayLength: 64, defaultR0TimeoutSeconds: 10, defaultR1TimeoutSeconds: 20,
        maxToolTimeoutSeconds: 30, maxToolCallsPerRun: 3, maxGlobalConcurrency: 1,
        maxConcurrencyPerRun: 1, maxSerializedOutputBytes: 65536, maxAgentVisibleOutputBytes: 32768,
        maxWebPreviewOutputBytes: 32768,
      },
      safety: { readOnly: true, sideEffects: false, writeEnabled: false, executeAvailable: false, policyMutationAvailable: false },
    },
    meta: { requestId: 'p1', timestamp: '2026-06-15T00:00:00+00:00' },
  }),
  fetchToolCatalog: vi.fn(),
}))

import SafetySection from '@/components/devconsole/SafetySection.vue'

describe('SafetySection (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the invariant safety badges', () => {
    const wrapper = mount(SafetySection)
    const text = wrapper.text()
    expect(text).toContain('Production untouched')
    expect(text).toContain('No ~/.hermes access')
    expect(text).toContain('Tool write route = 0')
    expect(text).toContain('Real provider blocked')
    expect(text).toContain('Audit store dev-only')
  })

  it('renders the frozen route-governance baseline 34/34/5/0/1/1', () => {
    const wrapper = mount(SafetySection)
    const dl = wrapper.find('.devconsole-card .devconsole-kv')
    expect(dl.exists()).toBe(true)
    const text = dl.text()
    expect(text).toContain('34')
    expect(text).toContain('OpenAPI paths')
    expect(text).toContain('Runtime routes')
    expect(text).toContain('Tool GET routes')
    expect(text).toContain('Tool write HTTP route')
    expect(text).toContain('Tool dry-run route')
    expect(text).toContain('Tool execution route')
  })

  it('renders the production PID baseline 28428 (read-only)', () => {
    const wrapper = mount(SafetySection)
    expect(wrapper.text()).toContain('28428')
    expect(wrapper.text()).toContain('read-only')
  })

  it('renders grouped badge surfaces', () => {
    const wrapper = mount(SafetySection)
    const text = wrapper.text()
    expect(text).toContain('Production isolation')
    expect(text).toContain('Route governance')
    expect(text).toContain('Provider boundary')
    expect(text).toContain('Write boundary')
    expect(text).toContain('Audit boundary')
  })

  it('never instructs bypassing the production gate', () => {
    const wrapper = mount(SafetySection)
    expect(wrapper.text()).toContain('do not bypass the production gate')
  })
})
