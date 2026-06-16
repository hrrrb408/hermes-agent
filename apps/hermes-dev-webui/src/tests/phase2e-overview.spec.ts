/**
 * Phase 2E — Overview dashboard section tests.
 *
 * Asserts the dashboard renders phase status, the frozen route-governance
 * baseline (34/34/5/0/1/1), safety badges, and live policy/audit-store cards —
 * and crucially that it makes NO execution POST (no dry-run / execute / write /
 * provider calls): the Overview is sourced purely from read-only GETs + frozen
 * constants.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolPolicy', () => ({
  fetchToolPolicyStatus: vi.fn(),
  fetchToolCatalog: vi.fn(),
}))
vi.mock('@/api/toolAudit', () => ({
  getAuditEvents: vi.fn(),
  getAuditEventsV2: vi.fn(),
}))
// Execution-surface APIs must NEVER be called from the Overview.
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({
  runWritePreview: vi.fn(),
  executeWrite: vi.fn(),
  runRollbackPreview: vi.fn(),
  executeRollback: vi.fn(),
}))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn(), fetchProviderBoundary: vi.fn().mockResolvedValue(null) }))

import { fetchToolPolicyStatus } from '@/api/toolPolicy'
import { getAuditEventsV2 } from '@/api/toolAudit'
import { runDryRun, executeTool } from '@/api/toolExecute'
import { runWritePreview, executeWrite } from '@/api/toolWrite'
import { runProviderRoundtrip } from '@/api/toolProvider'

import OverviewSection from '@/components/devconsole/OverviewSection.vue'

function mockPolicy(): void {
  vi.mocked(fetchToolPolicyStatus).mockResolvedValue({
    data: {
      mode: 'controlled',
      inventoryCount: 76,
      riskCounts: { R0: 3, R1: 8, R2: 19, R3: 26, R4: 17, R5: 3 },
      permanentDenylistCount: 26,
      candidateAllowlistCount: 11,
      enabledAllowlistCount: 0,
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
  })
}

function mockStoreEvents(): void {
  vi.mocked(getAuditEventsV2).mockResolvedValue({
    data: {
      items: [], nextCursor: null, previousCursor: null, hasMore: false, limit: 50, order: 'desc',
      query: {},
      storeStatus: { present: true, segmentCount: 2, monotonic: true, activeSegment: 'seg-000002', schemaVersion: 'audit_schema_v2' },
      indexStatus: { present: true, consistent: true, stale: false, lastSequence: 10, eventCount: 10, segmentCount: 2, fields: ['toolId'] },
      schemaVersion: 'audit_schema_v2',
      skippedMalformed: 0,
    },
    meta: { requestId: 'a1', timestamp: '2026-06-15T00:00:00+00:00' },
  })
}

describe('OverviewSection (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(fetchToolPolicyStatus).mockReset()
    vi.mocked(getAuditEventsV2).mockReset()
    vi.mocked(runDryRun).mockClear()
    vi.mocked(executeTool).mockClear()
    vi.mocked(runWritePreview).mockClear()
    vi.mocked(executeWrite).mockClear()
    vi.mocked(runProviderRoundtrip).mockClear()
    mockPolicy()
    mockStoreEvents()
    window.localStorage.clear()
  })

  function mountOverview() {
    return mount(OverviewSection, { attachTo: document.body })
  }

  it('renders the phase status summary', async () => {
    const wrapper = mountOverview()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SEALED'))
    expect(wrapper.text()).toContain('Completed')
  })

  it('renders the frozen route-governance baseline (34/34/5/0/1/1)', async () => {
    const wrapper = mountOverview()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SEALED'))
    const text = wrapper.text()
    expect(text).toContain('34 / 34')
    expect(text).toContain('write route 0')
    expect(text).toContain('1 / 1') // dry-run / execute
  })

  it('renders the invariant safety badges', async () => {
    const wrapper = mountOverview()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="dev-safety-badges"]').exists()).toBe(true))
    const text = wrapper.text()
    expect(text).toContain('Production untouched')
    expect(text).toContain('No ~/.hermes access')
    expect(text).toContain('Tool write route = 0')
    expect(text).toContain('Real provider blocked')
    expect(text).toContain('Audit store dev-only')
  })

  it('renders live policy inventory + audit-store cards', async () => {
    const wrapper = mountOverview()
    await vi.waitFor(() => expect(wrapper.text()).toContain('76'))
    const text = wrapper.text()
    expect(text).toContain('Tool inventory')
    expect(text).toContain('Audit store')
    expect(text).toContain('Present')
    expect(text).toContain('Consistent')
  })

  it('renders next safe-action hints', () => {
    const wrapper = mountOverview()
    const text = wrapper.text()
    expect(text).toContain('Next safe actions')
    expect(text).toContain('read-only tool')
    expect(text).toContain('Provider Round-trip')
  })

  it('makes NO execution POST (no dry-run / execute / write / provider)', async () => {
    mountOverview()
    await vi.waitFor(() => expect(vi.mocked(fetchToolPolicyStatus)).toHaveBeenCalled())
    // Give any pending microtasks a tick.
    await Promise.resolve()
    expect(runDryRun).not.toHaveBeenCalled()
    expect(executeTool).not.toHaveBeenCalled()
    expect(runWritePreview).not.toHaveBeenCalled()
    expect(executeWrite).not.toHaveBeenCalled()
    expect(runProviderRoundtrip).not.toHaveBeenCalled()
  })

  it('exposes no API-key / shell-command / raw-token inputs', () => {
    const wrapper = mountOverview()
    const html = wrapper.html()
    expect(html).not.toMatch(/api[_-]?key/i)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    // No shell command textarea inviting free shell input.
    expect(wrapper.findAll('[data-shell-input]').length).toBe(0)
  })
})
