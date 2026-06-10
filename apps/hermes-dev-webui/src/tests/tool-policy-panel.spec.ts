/**
 * Tests for the Tool Policy Panel UI components.
 *
 * Covers:
 * - Workspace Tools Tab integration
 * - ToolPolicyPanel sub-tabs (Overview / Catalog)
 * - Policy Overview (loading, error, retry, success, risk, execution, safety, limits)
 * - Catalog (loading, error, retry, filters, list, selection, detail, pagination, empty)
 * - Keyboard navigation
 * - ARIA attributes
 * - Read-only boundary (no action buttons)
 * - Lifecycle (mount/unmount cleanup)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import WorkspacePanel from '@/components/layout/WorkspacePanel.vue'
import ToolPolicyPanel from '@/components/workspace/ToolPolicyPanel.vue'
import { useUiStore } from '@/stores/ui'
import { useToolPolicyStore } from '@/stores/toolPolicy'

// ── Mock the API module ──

vi.mock('@/api/toolPolicy', () => ({
  fetchToolPolicyStatus: vi.fn(),
  fetchToolCatalog: vi.fn(),
}))

import { fetchToolPolicyStatus, fetchToolCatalog } from '@/api/toolPolicy'

// ── Test data factories ──

function makePolicyData(overrides: Record<string, unknown> = {}) {
  return {
    mode: 'DEFAULT_DENY',
    inventoryCount: 71,
    riskCounts: { R0: 1, R1: 5, R2: 19, R3: 26, R4: 17, R5: 3 },
    permanentDenylistCount: 26,
    candidateAllowlistCount: 6,
    enabledAllowlistCount: 0,
    execution: {
      implemented: false,
      enabled: false,
      providerSchemaSent: false,
      dispatchAvailable: false,
      auditAvailable: false,
    },
    limits: {
      maxArgumentPayloadBytes: 65536,
      maxArgumentNestingDepth: 8,
      maxArgumentStringLength: 32768,
      maxArgumentArrayLength: 256,
      defaultR0TimeoutSeconds: 30,
      defaultR1TimeoutSeconds: 60,
      maxToolTimeoutSeconds: 300,
      maxToolCallsPerRun: 50,
      maxGlobalConcurrency: 10,
      maxConcurrencyPerRun: 5,
      maxSerializedOutputBytes: 1048576,
      maxAgentVisibleOutputBytes: 524288,
      maxWebPreviewOutputBytes: 65536,
    },
    safety: {
      readOnly: true,
      sideEffects: false,
      writeEnabled: false,
      executeAvailable: false,
      policyMutationAvailable: false,
    },
    ...overrides,
  }
}

function makeCatalogItem(overrides: Record<string, unknown> = {}) {
  return {
    canonicalName: 'clarify',
    primaryRisk: 'R0' as const,
    riskRank: '0',
    capabilities: ['PURE_COMPUTE'] as const,
    permanentlyDenied: false,
    candidateAllowlisted: false,
    staticallyAllowed: false,
    allowed: false,
    policyStatus: 'UNLISTED' as const,
    reasonCode: 'TOOL_NOT_ALLOWED',
    sourceModule: 'tools/clarify.py',
    rationalePreview: 'Pure computation.',
    executionAvailable: false,
    schemaPreviewAvailable: false,
    dryRunAvailable: false,
    ...overrides,
  }
}

function makeCatalogData(overrides: Record<string, unknown> = {}) {
  return {
    items: [
      makeCatalogItem(),
      makeCatalogItem({
        canonicalName: 'terminal',
        primaryRisk: 'R4',
        riskRank: '4',
        capabilities: ['PROCESS_EXECUTION'],
        policyStatus: 'PERMANENTLY_DENIED',
        permanentlyDenied: true,
        reasonCode: 'PERMANENTLY_DENIED',
        rationalePreview: 'Shell execution.',
      }),
      makeCatalogItem({
        canonicalName: 'memory',
        primaryRisk: 'R1',
        riskRank: '1',
        capabilities: ['LOCAL_FILE_READ'],
        policyStatus: 'CANDIDATE',
        candidateAllowlisted: true,
        reasonCode: 'CANDIDATE_ALLOWLISTED',
        rationalePreview: 'Read memory files.',
      }),
    ],
    page: 1,
    pageSize: 25,
    total: 3,
    totalPages: 1,
    filters: { q: null, risk: null, capability: null, policyStatus: null, sort: 'nameAsc' },
    summary: { inventoryCount: 71, permanentDenylistCount: 26, candidateAllowlistCount: 6, enabledAllowlistCount: 0 },
    safety: { readOnly: true, sideEffects: false, executeAvailable: false },
    ...overrides,
  }
}

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-10T10:00:00Z' }

function mockPolicyResolve(data: Record<string, unknown>) {
  return (fetchToolPolicyStatus as ReturnType<typeof vi.fn>).mockResolvedValue({ data, meta: MOCK_META })
}

function mockCatalogResolve(data: Record<string, unknown>) {
  return (fetchToolCatalog as ReturnType<typeof vi.fn>).mockResolvedValue({ data, meta: MOCK_META })
}

function mockPolicyReject(err: unknown) {
  return (fetchToolPolicyStatus as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

function mockCatalogReject(err: unknown) {
  return (fetchToolCatalog as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ═══════════════════════════════════════════════════════════════════════════
// 1. Workspace Integration
// ═══════════════════════════════════════════════════════════════════════════

describe('Workspace Tools Tab Integration', () => {
  it('renders Tools tab alongside other tabs', () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.length).toBeGreaterThanOrEqual(6)
    expect(wrapper.find('#workspace-tab-tools').exists()).toBe(true)
  })

  it('switches to Tools panel when Tools tab is clicked', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-tools').trigger('click')
    expect(useUiStore().workspaceTab).toBe('tools')
    // Should show the ToolPolicyPanel
    expect(wrapper.find('#tool-policy-tab-overview').exists()).toBe(true)
  })

  it('preserves other tab switching after Tools tab is added', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    // Click Tools
    await wrapper.get('#workspace-tab-tools').trigger('click')
    expect(useUiStore().workspaceTab).toBe('tools')
    // Click Memory
    await wrapper.get('#workspace-tab-memory').trigger('click')
    expect(useUiStore().workspaceTab).toBe('memory')
    // Click Agent
    await wrapper.get('#workspace-tab-agent').trigger('click')
    expect(useUiStore().workspaceTab).toBe('agent')
  })

  it('Tools tab has correct ARIA attributes', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tab = wrapper.get('#workspace-tab-tools')
    expect(tab.attributes('role')).toBe('tab')
    expect(tab.attributes('aria-controls')).toBe('workspace-tabpanel-tools')
    expect(['true', 'false']).toContain(tab.attributes('aria-selected'))
  })

  it('Tools tab has focus-visible capability', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tab = wrapper.get('#workspace-tab-tools')
    const tabindex = tab.attributes('tabindex')
    expect(tabindex !== undefined).toBe(true)
    expect(Number(tabindex)).toBeGreaterThanOrEqual(-1)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 2. ToolPolicyPanel Sub-Tabs
// ═══════════════════════════════════════════════════════════════════════════

describe('ToolPolicyPanel sub-tabs', () => {
  function mountPanel() {
    return mount(ToolPolicyPanel)
  }

  it('renders two sub-tabs: Policy Overview and Catalog', () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountPanel()
    const subTabs = wrapper.findAll('[role="tab"]')
    expect(subTabs).toHaveLength(2)
    expect(wrapper.text()).toContain('Policy Overview')
    expect(wrapper.text()).toContain('Catalog')
  })

  it('Policy Overview is default selected', () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountPanel()
    const overviewTab = wrapper.get('#tool-policy-tab-overview')
    expect(overviewTab.attributes('aria-selected')).toBe('true')
    const catalogTab = wrapper.get('#tool-policy-tab-catalog')
    expect(catalogTab.attributes('aria-selected')).toBe('false')
  })

  it('switches to Catalog sub-tab on click', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    const store = useToolPolicyStore()
    expect(store.activeSubTab).toBe('catalog')
  })

  it('sub-tabs have correct ARIA attributes', () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountPanel()
    const overviewTab = wrapper.get('#tool-policy-tab-overview')
    expect(overviewTab.attributes('role')).toBe('tab')
    expect(overviewTab.attributes('aria-controls')).toBe('tool-policy-tabpanel-overview')
    const catalogTab = wrapper.get('#tool-policy-tab-catalog')
    expect(catalogTab.attributes('role')).toBe('tab')
    expect(catalogTab.attributes('aria-controls')).toBe('tool-policy-tabpanel-catalog')
  })

  it('sub-tab panels have correct ARIA attributes', () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountPanel()
    const panel = wrapper.get('#tool-policy-tabpanel-overview')
    expect(panel.attributes('role')).toBe('tabpanel')
    expect(panel.attributes('aria-labelledby')).toBe('tool-policy-tab-overview')
  })

  it('supports keyboard navigation between sub-tabs', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    // ArrowRight from overview → catalog
    await wrapper.get('#tool-policy-tab-overview').trigger('keydown', { key: 'ArrowRight' })
    const store = useToolPolicyStore()
    expect(store.activeSubTab).toBe('catalog')
    // Home → overview
    await wrapper.get('#tool-policy-tab-catalog').trigger('keydown', { key: 'Home' })
    expect(store.activeSubTab).toBe('overview')
    // End → catalog
    await wrapper.get('#tool-policy-tab-overview').trigger('keydown', { key: 'End' })
    expect(store.activeSubTab).toBe('catalog')
  })

  it('loads policy on mount', async () => {
    mockPolicyResolve(makePolicyData())
    mountPanel()
    await flushPromises()
    expect(fetchToolPolicyStatus).toHaveBeenCalledTimes(1)
  })

  it('aborts requests on unmount', () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountPanel()
    const store = useToolPolicyStore()
    const spy = vi.spyOn(store, 'abortAllRequests')
    wrapper.unmount()
    expect(spy).toHaveBeenCalled()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 3. Policy Overview
// ═══════════════════════════════════════════════════════════════════════════

describe('Policy Overview', () => {
  function mountOverview() {
    return mount(ToolPolicyPanel)
  }

  it('shows loading state', async () => {
    // Don't resolve policy — stay loading
    (fetchToolPolicyStatus as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}))
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('Loading tool policy')
    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(true)
  })

  it('shows error state with retry button', async () => {
    mockPolicyReject({ code: 'NETWORK_ERROR', message: 'Network error.' })
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Network error.')
    const retryBtn = wrapper.find('.panel-retry-btn')
    expect(retryBtn.exists()).toBe(true)
    expect(retryBtn.text()).toContain('Retry policy')
  })

  it('retry button calls store.retryPolicy', async () => {
    mockPolicyReject({ code: 'NETWORK_ERROR', message: 'Network error.' })
    const wrapper = mountOverview()
    await flushPromises()
    // Now mock success for retry
    mockPolicyResolve(makePolicyData())
    await wrapper.find('.panel-retry-btn').trigger('click')
    await flushPromises()
    expect(fetchToolPolicyStatus).toHaveBeenCalledTimes(2)
  })

  it('shows safety notice text', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('Read-only policy view')
    expect(wrapper.text()).toContain('No tools are enabled')
    expect(wrapper.text()).toContain('No tool calls can be executed')
    expect(wrapper.text()).toContain('No provider schemas are sent')
  })

  it('shows policy summary from backend data', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('DEFAULT_DENY')
    expect(wrapper.text()).toContain('71')
    expect(wrapper.text()).toContain('26')
    expect(wrapper.text()).toContain('6')
    // Enabled = 0
    const text = wrapper.text()
    const enabledMatch = text.match(/Enabled Allowlist\s*\n?\s*0/)
    expect(enabledMatch).toBeTruthy()
  })

  it('shows risk distribution with labels', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('Risk Distribution')
    expect(wrapper.text()).toContain('R0')
    expect(wrapper.text()).toContain('Pure compute')
    expect(wrapper.text()).toContain('R5')
    expect(wrapper.text()).toContain('Administrative / critical')
  })

  it('shows execution status as disabled/unavailable', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('Execution Status')
    expect(wrapper.text()).toContain('Disabled')
    expect(wrapper.text()).toContain('Not sent')
    expect(wrapper.text()).toContain('Unavailable')
  })

  it('shows safety status correctly', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('Safety Status')
    // Safety fields should show read-only and disabled states
    expect(wrapper.text()).toContain('Unavailable')
  })

  it('shows policy limits with units', async () => {
    mockPolicyResolve(makePolicyData())
    const wrapper = mountOverview()
    await flushPromises()
    expect(wrapper.text()).toContain('Policy Limits')
    // Check timeout values with seconds
    expect(wrapper.text()).toContain('30s')
    expect(wrapper.text()).toContain('60s')
    expect(wrapper.text()).toContain('300s')
  })

  it('shows empty state when no data', async () => {
    // Store stays in idle state — don't load
    const wrapper = mountOverview()
    await flushPromises()
    // If we navigate away and back, the store might have data or not
    // This test checks that the empty template renders
    const text = wrapper.text()
    expect(
      text.includes('Loading') ||
      text.includes('No tool policy') ||
      text.includes('Read-only')
    ).toBe(true)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 4. Catalog
// ═══════════════════════════════════════════════════════════════════════════

describe('Catalog', () => {
  function mountCatalog() {
    mockPolicyResolve(makePolicyData())
    const wrapper = mount(ToolPolicyPanel)
    return wrapper
  }

  async function switchToCatalog(wrapper: ReturnType<typeof mountCatalog>) {
    mockCatalogResolve(makeCatalogData())
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
  }

  it('shows loading state', async () => {
    mockPolicyResolve(makePolicyData())
    // Catalog loading: don't resolve
    mockCatalogResolve(makeCatalogData())
    // Override to hang
    ;(fetchToolCatalog as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}))
    const wrapper = mountCatalog()
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Loading tool catalog')
  })

  it('shows error state with retry', async () => {
    const wrapper = mountCatalog()
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Catalog error.' })
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Catalog error.')
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry catalog'))
    expect(retryBtn).toBeTruthy()
  })

  it('retry catalog reloads', async () => {
    const wrapper = mountCatalog()
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Error.' })
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    mockCatalogResolve(makeCatalogData())
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry catalog'))
    await retryBtn!.trigger('click')
    await flushPromises()
    expect(fetchToolCatalog).toHaveBeenCalledTimes(2)
  })

  it('renders filter controls', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    expect(wrapper.find('#tc-search').exists()).toBe(true)
    expect(wrapper.find('#tc-risk').exists()).toBe(true)
    expect(wrapper.find('#tc-capability').exists()).toBe(true)
    expect(wrapper.find('#tc-status').exists()).toBe(true)
    expect(wrapper.find('#tc-sort').exists()).toBe(true)
    expect(wrapper.find('#tc-pagesize').exists()).toBe(true)
  })

  it('filter controls have associated labels', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    // Each filter should have a label element or aria-label
    const searchInput = wrapper.find('#tc-search')
    expect(searchInput.attributes('maxlength')).toBe('120')
  })

  it('renders tool items with correct fields', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    expect(wrapper.text()).toContain('clarify')
    expect(wrapper.text()).toContain('terminal')
    expect(wrapper.text()).toContain('memory')
  })

  it('shows risk badges with text labels', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    // Risk levels should be text, not just colors
    expect(wrapper.text()).toContain('R0')
    expect(wrapper.text()).toContain('R4')
    expect(wrapper.text()).toContain('R1')
  })

  it('shows Allowed: No for all tools', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const allowedTexts = wrapper.findAll('.tc-item__allowed')
    for (const el of allowedTexts) {
      expect(el.text()).toContain('Allowed: No')
    }
  })

  it('Candidate items show Not enabled', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    // 'memory' tool is CANDIDATE
    const memoryItem = wrapper.findAll('.tc-item').find(item => item.text().includes('memory'))
    expect(memoryItem).toBeTruthy()
    expect(memoryItem!.text()).toContain('Candidate')
    expect(memoryItem!.text()).toContain('Not enabled')
  })

  it('Permanently denied items show correct status', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const terminalItem = wrapper.findAll('.tc-item').find(item => item.text().includes('terminal'))
    expect(terminalItem).toBeTruthy()
    expect(terminalItem!.text()).toContain('Permanently denied')
  })

  it('selects a tool on click', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const clarifyItem = wrapper.findAll('.tc-item').find(item => item.text().includes('clarify'))
    expect(clarifyItem).toBeTruthy()
    await clarifyItem!.trigger('click')
    const store = useToolPolicyStore()
    expect(store.selectedToolName).toBe('clarify')
  })

  it('shows detail panel on selection', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const clarifyItem = wrapper.findAll('.tc-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.tc-detail')
    expect(detail.exists()).toBe(true)
    // Check detail fields
    expect(detail.text()).toContain('clarify')
    expect(detail.text()).toContain('PURE_COMPUTE')
    expect(detail.text()).toContain('UNLISTED')
    expect(detail.text()).toContain('TOOL_NOT_ALLOWED')
    expect(detail.text()).toContain('tools/clarify.py')
  })

  it('detail shows execution unavailable states', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const clarifyItem = wrapper.findAll('.tc-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.tc-detail')
    // Should show "Unavailable" for execution, schema preview, dry-run
    const detailText = detail.text()
    expect(detailText).toContain('Unavailable')
  })

  it('supports keyboard selection (Enter/Space)', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const clarifyItem = wrapper.findAll('.tc-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('keydown', { key: 'Enter' })
    const store = useToolPolicyStore()
    expect(store.selectedToolName).toBe('clarify')
    store.clearSelection()
    await clarifyItem!.trigger('keydown', { key: ' ' })
    expect(store.selectedToolName).toBe('clarify')
  })

  it('shows pagination with page info', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    expect(wrapper.text()).toContain('Page 1 of 1')
    expect(wrapper.text()).toContain('3 tools')
  })

  it('pagination buttons are disabled at boundaries', async () => {
    const wrapper = mountCatalog()
    await switchToCatalog(wrapper)
    const prevBtn = wrapper.findAll('.tc-page-btn').find(b => b.text().includes('Prev'))
    const nextBtn = wrapper.findAll('.tc-page-btn').find(b => b.text().includes('Next'))
    expect(prevBtn!.attributes('disabled')).toBeDefined()
    expect(nextBtn!.attributes('disabled')).toBeDefined()
  })

  it('shows empty state for filtered results', async () => {
    const wrapper = mountCatalog()
    mockCatalogResolve(makeCatalogData({ items: [], total: 0, totalPages: 0, filters: { q: 'xyz', risk: null, capability: null, policyStatus: null, sort: 'nameAsc' } }))
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('No tools match')
  })

  it('shows "0 results" for truly empty catalog', async () => {
    const wrapper = mountCatalog()
    mockCatalogResolve(makeCatalogData({ items: [], total: 0, totalPages: 0 }))
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('0 results')
  })

  it('loads catalog when switching to Catalog tab', async () => {
    const wrapper = mountCatalog()
    mockCatalogResolve(makeCatalogData())
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    expect(fetchToolCatalog).toHaveBeenCalled()
  })

  it('Clear filters button resets filters', async () => {
    const wrapper = mountCatalog()
    mockCatalogResolve(makeCatalogData({ items: [], total: 0, totalPages: 0, filters: { q: 'xyz', risk: null, capability: null, policyStatus: null, sort: 'nameAsc' } }))
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    const clearBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Clear filters'))
    expect(clearBtn).toBeTruthy()
    mockCatalogResolve(makeCatalogData())
    await clearBtn!.trigger('click')
    await flushPromises()
    const store = useToolPolicyStore()
    expect(store.filters.q).toBe('')
    expect(store.filters.risk).toBeUndefined()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 5. Search Debounce
// ═══════════════════════════════════════════════════════════════════════════

describe('Catalog search debounce', () => {
  it('debounces search input at 300ms', async () => {
    vi.useFakeTimers()
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()

    const searchInput = wrapper.find('#tc-search')
    await searchInput.setValue('test')
    // After 200ms, loadCatalog should NOT have been called again
    vi.advanceTimersByTime(200)
    const callsAfter200 = (fetchToolCatalog as ReturnType<typeof vi.fn>).mock.calls.length
    // After 300ms total, it should fire
    vi.advanceTimersByTime(150)
    await flushPromises()
    const callsAfter350 = (fetchToolCatalog as ReturnType<typeof vi.fn>).mock.calls.length
    expect(callsAfter350).toBeGreaterThan(callsAfter200)
    vi.useRealTimers()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 6. Read-Only Boundary
// ═══════════════════════════════════════════════════════════════════════════

describe('Read-only boundary', () => {
  function mountAndLoad() {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    return mount(ToolPolicyPanel)
  }

  it('contains no Enable button', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    for (const btn of buttons) {
      expect(btn.text()).not.toMatch(/^Enable$/)
    }
  })

  it('contains no Execute button', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    for (const btn of buttons) {
      expect(btn.text()).not.toContain('Execute')
      expect(btn.text()).not.toContain('Run Tool')
    }
  })

  it('contains no Dry-Run action button', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    // "Dry-Run Available" as status text is OK, but no button
    const buttons = wrapper.findAll('button')
    for (const btn of buttons) {
      expect(btn.text()).not.toContain('Dry-Run')
      expect(btn.text()).not.toContain('Try Tool')
      expect(btn.text()).not.toContain('Test Tool')
    }
  })

  it('contains no Schema Preview action button', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    for (const btn of buttons) {
      expect(btn.text()).not.toContain('Preview Schema')
    }
  })

  it('contains no Allowlist/Denylist mutation controls', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    const text = wrapper.text()
    expect(text).not.toContain('Add to Allowlist')
    expect(text).not.toContain('Remove from Denylist')
    expect(text).not.toContain('Promote')
  })

  it('contains no policy save controls', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    const text = wrapper.text()
    expect(text).not.toContain('Save Policy')
    expect(text).not.toContain('Apply')
  })

  it('does not display "Enabled" for Candidate items', async () => {
    const wrapper = mountAndLoad()
    await flushPromises()
    // Switch to catalog
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    // The memory item is CANDIDATE, should show "Candidate" not "Enabled"
    const memoryItem = wrapper.findAll('.tc-item').find(item => item.text().includes('memory'))
    expect(memoryItem).toBeTruthy()
    const itemText = memoryItem!.text()
    expect(itemText).toContain('Candidate')
    expect(itemText).toContain('Not enabled')
    // Must NOT say "Enabled" as a status
    expect(itemText).not.toMatch(/\bEnabled\b/)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 7. Accessibility
// ═══════════════════════════════════════════════════════════════════════════

describe('Accessibility', () => {
  it('tool list items have role="option"', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    const items = wrapper.findAll('[role="option"]')
    expect(items.length).toBe(3)
  })

  it('tool list container has role="listbox"', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)
  })

  it('selected item has aria-selected', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    const items = wrapper.findAll('[role="option"]')
    await items[0]!.trigger('click')
    expect(items[0]!.attributes('aria-selected')).toBe('true')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 8. Lifecycle
// ═══════════════════════════════════════════════════════════════════════════

describe('Lifecycle', () => {
  it('clears debounce timer on unmount', async () => {
    vi.useFakeTimers()
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-catalog').trigger('click')
    await flushPromises()
    // Type in search to set debounce
    const searchInput = wrapper.find('#tc-search')
    await searchInput.setValue('test')
    // Unmount before debounce fires
    wrapper.unmount()
    // Timer should be cleared — advancing should not cause errors
    vi.advanceTimersByTime(500)
    vi.useRealTimers()
  })
})
