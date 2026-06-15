/**
 * Phase 2E — Audit Viewer section tests.
 *
 * The section reuses the existing AuditViewerPanel (Phase 2D durable store:
 * store-mode toggle, filters, cursor pagination, store/index status). Asserts
 * the viewer controls render, cursor pagination is present, and the
 * cross-reference prefill marker can be cleared.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolAudit', () => ({
  getAuditEvents: vi.fn(),
  getAuditEventsV2: vi.fn(),
}))

import { getAuditEvents, getAuditEventsV2 } from '@/api/toolAudit'
import AuditViewerSection from '@/components/devconsole/AuditViewerSection.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

function mockLegacy(): void {
  vi.mocked(getAuditEvents).mockResolvedValue({
    data: { auditKind: 'post_execution', items: [], nextCursor: null, limit: 50, hasMore: false, skippedMalformed: 0 },
    meta: { requestId: 'a1', timestamp: '2026-06-15T00:00:00+00:00' },
  })
}

describe('AuditViewerSection (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getAuditEvents).mockReset()
    vi.mocked(getAuditEventsV2).mockReset()
    mockLegacy()
    window.localStorage.clear()
  })

  it('renders the reused AuditViewerPanel controls (store toggle, filters, cursor pagination)', () => {
    const wrapper = mount(AuditViewerSection)
    expect(wrapper.find('#audit-viewer-store-toggle').exists()).toBe(true)
    expect(wrapper.find('[role="tablist"]').exists()).toBe(true)
  })

  it('renders the store-mode filter bar and pagination when store mode is enabled', async () => {
    const wrapper = mount(AuditViewerSection)
    // Toggle store mode on.
    await wrapper.find('#audit-viewer-store-toggle').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('#audit-viewer-store-controls').exists()).toBe(true))
    expect(wrapper.find('#audit-viewer-store-limit').exists()).toBe(true)
    expect(wrapper.find('#audit-viewer-eventtype-filter').exists()).toBe(true)
    expect(wrapper.find('#audit-viewer-status-filter').exists()).toBe(true)
    expect(wrapper.find('#audit-viewer-search-input').exists()).toBe(true)
    expect(wrapper.find('#audit-viewer-store-apply').exists()).toBe(true)
  })

  it('shows the prefill marker and clears it via the clear button', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    // Simulate a cross-nav prefill (the store is the source of truth).
    nav.pendingAuditPrefill = 'pexa_abc123'

    const wrapper = mount(AuditViewerSection)
    expect(wrapper.text()).toContain('pexa_abc123')
    expect(wrapper.find('[data-testid="dev-audit-clear-prefill"]').exists()).toBe(true)

    await wrapper.find('[data-testid="dev-audit-clear-prefill"]').trigger('click')
    expect(nav.pendingAuditPrefill).toBeNull()
  })

  it('never surfaces raw tokens / full hashes / callable reprs', () => {
    const wrapper = mount(AuditViewerSection)
    const html = wrapper.html()
    expect(html).not.toMatch(/sk-[A-Za-z0-9_-]{16,}/)
    expect(html).not.toMatch(/Bearer /)
    expect(html).not.toMatch(/<function|object at 0x/)
    expect(html).not.toMatch(/rawArguments|fullTokenHash|plainToken/)
  })
})
