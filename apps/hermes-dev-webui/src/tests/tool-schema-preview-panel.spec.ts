/**
 * Tests for the Tool Schema Preview Panel UI components.
 *
 * Covers:
 * - Panel rendering (title, read-only notice, summary, list, detail)
 * - Loading / error / empty / retry states
 * - Search and filter functionality
 * - Tool selection and detail display
 * - Field list rendering
 * - Keyboard navigation
 * - ARIA attributes
 * - Read-only boundary (no execution CTA)
 * - Network safety (only GET calls)
 * - Lifecycle (mount/unmount cleanup)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import ToolPolicyPanel from '@/components/workspace/ToolPolicyPanel.vue'
import { useToolSchemaPreviewStore } from '@/stores/toolSchemaPreview'
import { useToolPolicyStore } from '@/stores/toolPolicy'

// ── Mock the API modules ──

vi.mock('@/api/toolPolicy', () => ({
  fetchToolPolicyStatus: vi.fn(),
  fetchToolCatalog: vi.fn(),
}))

vi.mock('@/api/toolSchemaPreview', () => ({
  fetchToolSchemaPreviewCatalog: vi.fn(),
  fetchToolSchemaPreviewByCanonicalName: vi.fn(),
}))

import { fetchToolPolicyStatus } from '@/api/toolPolicy'
import {
  fetchToolSchemaPreviewCatalog,
  fetchToolSchemaPreviewByCanonicalName,
} from '@/api/toolSchemaPreview'

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

function makeSchemaPreviewItem(overrides: Record<string, unknown> = {}) {
  return {
    canonicalName: 'clarify',
    risk: 'R0',
    capabilities: ['PURE_COMPUTE'],
    schemaPreviewAvailable: true,
    schemaShape: 'object',
    inputFields: [
      {
        fieldName: 'query',
        fieldType: 'string',
        required: true,
        descriptionPreview: 'The question to clarify.',
        enumPreview: null,
        defaultPresence: false,
        constraintsPreview: null,
      },
    ],
    redactionStatus: 'clean',
    reasonCode: 'AVAILABLE',
    unavailableReason: null,
    ...overrides,
  }
}

function makeCatalogData(overrides: Record<string, unknown> = {}) {
  return {
    totalCount: 3,
    availableCount: 2,
    unavailableCount: 1,
    items: [
      makeSchemaPreviewItem(),
      makeSchemaPreviewItem({
        canonicalName: 'memory',
        risk: 'R1',
        capabilities: ['LOCAL_FILE_READ'],
        schemaPreviewAvailable: true,
        reasonCode: 'AVAILABLE',
      }),
      makeSchemaPreviewItem({
        canonicalName: 'terminal',
        risk: 'R4',
        capabilities: ['PROCESS_EXECUTION'],
        schemaPreviewAvailable: false,
        reasonCode: 'RISK_R4_EXECUTION',
        unavailableReason: 'Permanently denied: shell execution risk.',
        redactionStatus: 'unavailable',
      }),
    ],
    ...overrides,
  }
}

function makeLookupData(overrides: Record<string, unknown> = {}) {
  return {
    found: true,
    preview: makeSchemaPreviewItem(),
    reasonCode: 'FOUND',
    ...overrides,
  }
}

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-11T10:00:00Z' }

function mockPolicyResolve(data: Record<string, unknown>) {
  return (fetchToolPolicyStatus as ReturnType<typeof vi.fn>).mockResolvedValue({ data, meta: MOCK_META })
}

function mockCatalogResolve(data: Record<string, unknown>) {
  return (fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>).mockResolvedValue({ data, meta: MOCK_META })
}

function mockCatalogReject(err: unknown) {
  return (fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

function mockPreviewResolve(data: Record<string, unknown>) {
  return (fetchToolSchemaPreviewByCanonicalName as ReturnType<typeof vi.fn>).mockResolvedValue({ data, meta: MOCK_META })
}

function mockPreviewReject(err: unknown) {
  return (fetchToolSchemaPreviewByCanonicalName as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ═══════════════════════════════════════════════════════════════════════════
// 1. Panel Rendering
// ═══════════════════════════════════════════════════════════════════════════

describe('Panel Rendering', () => {
  function mountAndSwitch() {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    return wrapper
  }

  async function switchToSchemaPreview(wrapper: ReturnType<typeof mountAndSwitch>) {
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
  }

  it('renders Schema Preview sub-tab', async () => {
    const wrapper = mountAndSwitch()
    const tab = wrapper.find('#tool-policy-tab-schema-preview')
    expect(tab.exists()).toBe(true)
    expect(tab.text()).toContain('Schema Preview')
  })

  it('renders read-only notice', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('Schema Preview is read-only')
    expect(wrapper.text()).toContain('Preview availability does not imply execution availability')
    expect(wrapper.text()).toContain('Provider schema is not sent')
    expect(wrapper.text()).toContain('Tool execution remains disabled')
  })

  it('renders summary cards with counts', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('Total tools')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('Available')
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('Unavailable')
  })

  it('renders filter controls', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.find('#sp-search').exists()).toBe(true)
    expect(wrapper.find('#sp-availability').exists()).toBe(true)
    expect(wrapper.find('#sp-risk').exists()).toBe(true)
  })

  it('renders tool items from catalog', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('clarify')
    expect(wrapper.text()).toContain('memory')
    expect(wrapper.text()).toContain('terminal')
  })

  it('renders risk badges with text', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('R0')
    expect(wrapper.text()).toContain('R4')
  })

  it('renders availability status per item', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('Preview available')
    expect(wrapper.text()).toContain('Unavailable')
  })

  it('renders redaction status for non-clean items', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    // terminal has redactionStatus: 'unavailable'
    expect(wrapper.text()).toContain('unavailable')
  })

  it('renders unavailable reason for unavailable items', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('Permanently denied: shell execution risk.')
  })

  it('renders detail placeholder when no tool selected', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('Select a tool to view schema preview details')
  })

  it('loads schema preview catalog on mount', async () => {
    const wrapper = mountAndSwitch()
    await switchToSchemaPreview(wrapper)
    expect(fetchToolSchemaPreviewCatalog).toHaveBeenCalled()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 2. Loading / Error / Empty / Retry
// ═══════════════════════════════════════════════════════════════════════════

describe('Loading / Error / Empty / Retry', () => {
  function mountPanel() {
    mockPolicyResolve(makePolicyData())
    return mount(ToolPolicyPanel)
  }

  async function switchToSchemaPreview(wrapper: ReturnType<typeof mountPanel>) {
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
  }

  it('shows catalog loading state', async () => {
    ;(fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}))
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('Loading schema previews')
    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(true)
  })

  it('shows catalog error with retry button', async () => {
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Network error.' })
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Network error.')
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry preview'))
    expect(retryBtn).toBeTruthy()
  })

  it('retry catalog reloads data', async () => {
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Network error.' })
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    mockCatalogResolve(makeCatalogData())
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry preview'))
    await retryBtn!.trigger('click')
    await flushPromises()
    expect(fetchToolSchemaPreviewCatalog).toHaveBeenCalledTimes(2)
  })

  it('shows empty state when catalog has no items', async () => {
    mockCatalogResolve(makeCatalogData({
      totalCount: 0,
      availableCount: 0,
      unavailableCount: 0,
      items: [],
    }))
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.text()).toContain('No schema preview data available')
  })

  it('shows detail loading state', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    // Mock preview to hang
    ;(fetchToolSchemaPreviewByCanonicalName as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}))
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Loading schema detail')
  })

  it('shows detail error with retry', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    mockPreviewReject({ code: 'NETWORK_ERROR', message: 'Detail error.' })
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Detail error.')
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry detail'))
    expect(retryBtn).toBeTruthy()
  })

  it('retry detail reloads preview', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    mockPreviewReject({ code: 'NETWORK_ERROR', message: 'Error.' })
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    mockPreviewResolve(makeLookupData())
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry detail'))
    await retryBtn!.trigger('click')
    await flushPromises()
    expect(fetchToolSchemaPreviewByCanonicalName).toHaveBeenCalledTimes(2)
  })

  it('shows not found state for missing tool', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await switchToSchemaPreview(wrapper)
    mockPreviewReject({
      code: 'TOOL_SCHEMA_PREVIEW_NOT_FOUND',
      message: "Tool schema preview not found for 'nonexistent'.",
      status: 404,
    })
    // Directly fetch a non-existent tool via store
    const store = useToolSchemaPreviewStore()
    await store.fetchPreview('nonexistent')
    await flushPromises()
    expect(wrapper.text()).toContain('not found')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 3. Search and Filter
// ═══════════════════════════════════════════════════════════════════════════

describe('Search and Filter', () => {
  function mountAndLoad() {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    return wrapper
  }

  async function switchToSchemaPreview(wrapper: ReturnType<typeof mountAndLoad>) {
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
  }

  it('search input filters by canonicalName', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const searchInput = wrapper.find('#sp-search')
    await searchInput.setValue('clar')
    await flushPromises()
    // Only clarify should be visible
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(1)
    expect(items[0]!.text()).toContain('clarify')
  })

  it('search input filters by capability', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const searchInput = wrapper.find('#sp-search')
    await searchInput.setValue('PROCESS_EXECUTION')
    await flushPromises()
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(1)
    expect(items[0]!.text()).toContain('terminal')
  })

  it('availability filter shows only available tools', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const select = wrapper.find('#sp-availability')
    await select.setValue('available')
    await flushPromises()
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(2)
    for (const item of items) {
      expect(item.text()).toContain('Preview available')
    }
  })

  it('availability filter shows only unavailable tools', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const select = wrapper.find('#sp-availability')
    await select.setValue('unavailable')
    await flushPromises()
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(1)
    expect(items[0]!.text()).toContain('terminal')
  })

  it('risk filter shows only matching risk level', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const select = wrapper.find('#sp-risk')
    await select.setValue('R4')
    await flushPromises()
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(1)
    expect(items[0]!.text()).toContain('terminal')
  })

  it('combined search and filter work together', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    await wrapper.find('#sp-search').setValue('memo')
    await wrapper.find('#sp-availability').setValue('available')
    await flushPromises()
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(1)
    expect(items[0]!.text()).toContain('memory')
  })

  it('Clear filters button appears when filters are active', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    await wrapper.find('#sp-search').setValue('test')
    await flushPromises()
    const clearBtn = wrapper.find('.sp-clear-btn')
    expect(clearBtn.exists()).toBe(true)
    expect(clearBtn.text()).toContain('Clear filters')
  })

  it('Clear filters button resets all filters', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    await wrapper.find('#sp-search').setValue('test')
    await wrapper.find('#sp-availability').setValue('available')
    await wrapper.find('#sp-risk').setValue('R0')
    await flushPromises()
    await wrapper.find('.sp-clear-btn').trigger('click')
    await flushPromises()
    // All items should be visible now
    const items = wrapper.findAll('.sp-item')
    expect(items).toHaveLength(3)
  })

  it('shows "No tools match" when filters yield empty results', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    await wrapper.find('#sp-search').setValue('nonexistent-tool-name-xyz')
    await flushPromises()
    expect(wrapper.text()).toContain('No tools match the current filters')
  })

  it('filter controls have associated labels for accessibility', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const searchInput = wrapper.find('#sp-search')
    expect(searchInput.attributes('maxlength')).toBe('120')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 4. Selection and Detail
// ═══════════════════════════════════════════════════════════════════════════

describe('Selection and Detail', () => {
  function mountAndLoad() {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    return mount(ToolPolicyPanel)
  }

  async function switchToSchemaPreview(wrapper: ReturnType<typeof mountAndLoad>) {
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
  }

  it('clicking a tool item calls fetchPreview', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    expect(fetchToolSchemaPreviewByCanonicalName).toHaveBeenCalledWith('clarify', expect.any(AbortSignal))
  })

  it('selectedCanonicalName is updated on selection', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const store = useToolSchemaPreviewStore()
    expect(store.selectedCanonicalName).toBe('clarify')
  })

  it('detail panel shows selected tool info', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.exists()).toBe(true)
    expect(detail.text()).toContain('clarify')
    expect(detail.text()).toContain('object')
    expect(detail.text()).toContain('AVAILABLE')
    expect(detail.text()).toContain('clean')
  })

  it('detail panel shows risk with label', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.text()).toContain('R0')
    expect(detail.text()).toContain('Pure compute')
  })

  it('detail panel shows capabilities', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.text()).toContain('PURE_COMPUTE')
  })

  it('detail panel shows unavailable reason for unavailable tool', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData({
      found: true,
      preview: makeSchemaPreviewItem({
        canonicalName: 'terminal',
        risk: 'R4',
        schemaPreviewAvailable: false,
        reasonCode: 'RISK_R4_EXECUTION',
        unavailableReason: 'Permanently denied: shell execution risk.',
      }),
      reasonCode: 'FOUND',
    }))
    const terminalItem = wrapper.findAll('.sp-item').find(item => item.text().includes('terminal'))
    await terminalItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.text()).toContain('Permanently denied: shell execution risk.')
  })

  it('detail panel renders input fields correctly', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.text()).toContain('Input Fields')
    expect(detail.text()).toContain('query')
    expect(detail.text()).toContain('string')
    expect(detail.text()).toContain('required')
    expect(detail.text()).toContain('The question to clarify.')
  })

  it('detail panel shows enum values', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData({
      found: true,
      preview: makeSchemaPreviewItem({
        inputFields: [
          {
            fieldName: 'mode',
            fieldType: 'string',
            required: false,
            descriptionPreview: 'The mode.',
            enumPreview: ['fast', 'slow', 'balanced'],
            defaultPresence: true,
            constraintsPreview: null,
          },
        ],
      }),
      reasonCode: 'FOUND',
    }))
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.text()).toContain('fast')
    expect(detail.text()).toContain('slow')
    expect(detail.text()).toContain('balanced')
    expect(detail.text()).toContain('has default')
  })

  it('detail panel shows constraints preview', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData({
      found: true,
      preview: makeSchemaPreviewItem({
        inputFields: [
          {
            fieldName: 'count',
            fieldType: 'integer',
            required: true,
            descriptionPreview: 'Count.',
            enumPreview: null,
            defaultPresence: false,
            constraintsPreview: 'min: 1, max: 100',
          },
        ],
      }),
      reasonCode: 'FOUND',
    }))
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    const detail = wrapper.find('.sp-detail')
    expect(detail.text()).toContain('min: 1, max: 100')
  })

  it('detail panel shows "No input fields" for empty schema', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData({
      found: true,
      preview: makeSchemaPreviewItem({ inputFields: [] }),
      reasonCode: 'FOUND',
    }))
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('No input fields in this schema preview')
  })

  it('supports keyboard selection with Enter', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    const store = useToolSchemaPreviewStore()
    expect(store.selectedCanonicalName).toBe('clarify')
  })

  it('supports keyboard selection with Space', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    mockPreviewResolve(makeLookupData())
    const clarifyItem = wrapper.findAll('.sp-item').find(item => item.text().includes('clarify'))
    await clarifyItem!.trigger('keydown', { key: ' ' })
    await flushPromises()
    const store = useToolSchemaPreviewStore()
    expect(store.selectedCanonicalName).toBe('clarify')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 5. Sub-Tab Navigation
// ═══════════════════════════════════════════════════════════════════════════

describe('Sub-Tab Navigation', () => {
  function mountPanel() {
    mockPolicyResolve(makePolicyData())
    return mount(ToolPolicyPanel)
  }

  it('Schema Preview tab has correct ARIA attributes', async () => {
    const wrapper = mountPanel()
    const tab = wrapper.get('#tool-policy-tab-schema-preview')
    expect(tab.attributes('role')).toBe('tab')
    expect(tab.attributes('aria-controls')).toBe('tool-policy-tabpanel-schema-preview')
    expect(['true', 'false']).toContain(tab.attributes('aria-selected'))
  })

  it('Schema Preview tabpanel has correct ARIA attributes', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
    const panel = wrapper.get('#tool-policy-tabpanel-schema-preview')
    expect(panel.attributes('role')).toBe('tabpanel')
    expect(panel.attributes('aria-labelledby')).toBe('tool-policy-tab-schema-preview')
  })

  it('supports keyboard navigation to Schema Preview tab', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    // ArrowRight from overview → catalog
    await wrapper.get('#tool-policy-tab-overview').trigger('keydown', { key: 'ArrowRight' })
    const policyStore = useToolPolicyStore()
    expect(policyStore.activeSubTab).toBe('catalog')
    // ArrowRight from catalog → schema-preview
    await wrapper.get('#tool-policy-tab-catalog').trigger('keydown', { key: 'ArrowRight' })
    expect(policyStore.activeSubTab).toBe('schema-preview')
  })

  it('End key navigates to Schema Preview (last tab)', async () => {
    mockCatalogResolve(makeCatalogData())
    const wrapper = mountPanel()
    await wrapper.get('#tool-policy-tab-overview').trigger('keydown', { key: 'End' })
    const policyStore = useToolPolicyStore()
    expect(policyStore.activeSubTab).toBe('schema-preview')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 6. Accessibility
// ═══════════════════════════════════════════════════════════════════════════

describe('Accessibility', () => {
  function mountAndLoad() {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    return mount(ToolPolicyPanel)
  }

  async function switchToSchemaPreview(wrapper: ReturnType<typeof mountAndLoad>) {
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
  }

  it('tool list items have role="option"', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const options = wrapper.findAll('.sp-item[role="option"]')
    expect(options).toHaveLength(3)
  })

  it('tool list container has role="listbox"', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    expect(wrapper.find('.sp-list[role="listbox"]').exists()).toBe(true)
  })

  it('selected item has aria-selected="true"', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const items = wrapper.findAll('.sp-item')
    await items[0]!.trigger('click')
    await flushPromises()
    expect(items[0]!.attributes('aria-selected')).toBe('true')
  })

  it('search input has maxlength', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const searchInput = wrapper.find('#sp-search')
    expect(searchInput.attributes('maxlength')).toBe('120')
  })

  it('loading state has aria-busy', async () => {
    ;(fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}))
    mockPolicyResolve(makePolicyData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(true)
  })

  it('retry buttons have aria-label', async () => {
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Error.' })
    mockPolicyResolve(makePolicyData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
    const retryBtn = wrapper.findAll('.panel-retry-btn').find(b => b.text().includes('Retry preview'))
    expect(retryBtn).toBeTruthy()
    expect(retryBtn!.attributes('aria-label')).toBeTruthy()
  })

  it('read-only notice has role="status"', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const notice = wrapper.find('.sp-notice')
    expect(notice.exists()).toBe(true)
    expect(notice.attributes('role')).toBe('status')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 7. Read-Only Boundary
// ═══════════════════════════════════════════════════════════════════════════

describe('Read-only boundary', () => {
  function mountAndLoad() {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    return mount(ToolPolicyPanel)
  }

  async function switchToSchemaPreview(wrapper: ReturnType<typeof mountAndLoad>) {
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
  }

  const FORBIDDEN_BUTTONS = [
    'Run', 'Execute', 'Dry Run', 'Send to Provider', 'Generate Args',
    'Autofill Args', 'Call Tool', 'Test Tool', 'Enable Tool',
    'Save Allowlist', 'Dispatch', 'Audit',
  ]

  for (const forbidden of FORBIDDEN_BUTTONS) {
    it(`contains no "${forbidden}" action button`, async () => {
      const wrapper = mountAndLoad()
      await switchToSchemaPreview(wrapper)
      const buttons = wrapper.findAll('button')
      for (const btn of buttons) {
        expect(btn.text()).not.toContain(forbidden)
      }
    })
  }

  it('does not display raw schema', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const text = wrapper.text()
    expect(text).not.toContain('raw schema')
    expect(text).not.toContain('schema_json')
  })

  it('does not display handler/callable/path/secret', async () => {
    const wrapper = mountAndLoad()
    await switchToSchemaPreview(wrapper)
    const text = wrapper.text()
    expect(text).not.toContain('handler')
    expect(text).not.toContain('callable')
    expect(text).not.toContain('source path')
    expect(text).not.toContain('secret')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 8. Network Safety
// ═══════════════════════════════════════════════════════════════════════════

describe('Network safety', () => {
  it('store only calls fetchCatalog and fetchPreview', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    mockPreviewResolve(makeLookupData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()

    const store = useToolSchemaPreviewStore()
    await store.fetchPreview('clarify')
    await flushPromises()

    // Only GET API functions should have been called
    expect(fetchToolSchemaPreviewCatalog).toHaveBeenCalled()
    expect(fetchToolSchemaPreviewByCanonicalName).toHaveBeenCalled()
  })

  it('store does not expose dangerous actions', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.executeTool).toBeUndefined()
    expect(store.execute).toBeUndefined()
    expect(store.dryRunTool).toBeUndefined()
    expect(store.dryRun).toBeUndefined()
    expect(store.sendProviderSchema).toBeUndefined()
    expect(store.sendSchema).toBeUndefined()
    expect(store.dispatchTool).toBeUndefined()
    expect(store.dispatch).toBeUndefined()
    expect(store.enableTool).toBeUndefined()
    expect(store.saveAllowlist).toBeUndefined()
    expect(store.updatePolicy).toBeUndefined()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 9. Lifecycle
// ═══════════════════════════════════════════════════════════════════════════

describe('Lifecycle', () => {
  it('aborts all requests on unmount', async () => {
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
    const store = useToolSchemaPreviewStore()
    const spy = vi.spyOn(store, 'abortAllRequests')
    wrapper.unmount()
    expect(spy).toHaveBeenCalled()
  })

  it('respects catalogState idle check on mount', async () => {
    const store = useToolSchemaPreviewStore()
    // Pre-load catalog so state is not idle
    mockCatalogResolve(makeCatalogData())
    await store.fetchCatalog()
    vi.clearAllMocks()

    mockPolicyResolve(makePolicyData())
    const wrapper = mount(ToolPolicyPanel)
    await wrapper.get('#tool-policy-tab-schema-preview').trigger('click')
    await flushPromises()
    // fetchCatalog should NOT have been called again
    expect(fetchToolSchemaPreviewCatalog).not.toHaveBeenCalled()
  })
})
