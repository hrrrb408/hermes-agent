/**
 * Phase 2E-H1 — Lens 4: Audit Cross-navigation Boundary.
 *
 * Hardens the result→audit cross-navigation bridge end-to-end:
 *   - AuditIdLink renders a LOSSY id and emits the full id on click.
 *   - prefillAuditSearch switches section + store mode + filter AND fires load.
 *   - the Audit Viewer prefill marker is rendered lossy (truncated) — the full
 *     id lives only in the store as the active search filter.
 *   - missing / cleared prefill shows no marker.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/toolPolicy', () => ({ fetchToolPolicyStatus: vi.fn(), fetchToolCatalog: vi.fn() }))
vi.mock('@/api/toolAudit', () => ({ getAuditEvents: vi.fn(), getAuditEventsV2: vi.fn() }))
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({ runWritePreview: vi.fn(), executeWrite: vi.fn(), runRollbackPreview: vi.fn(), executeRollback: vi.fn() }))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn() }))

import { getAuditEventsV2 } from '@/api/toolAudit'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import AuditViewerSection from '@/components/devconsole/AuditViewerSection.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import { useToolAuditStore } from '@/stores/toolAudit'

function mockStoreEventsV2(): void {
  vi.mocked(getAuditEventsV2).mockResolvedValue({
    data: {
      items: [],
      nextCursor: null,
      previousCursor: null,
      hasMore: false,
      limit: 50,
      order: 'desc',
      query: {},
      storeStatus: { present: true, segmentCount: 1, monotonic: true, activeSegment: 'seg-000001', schemaVersion: 'audit_schema_v2' },
      indexStatus: { present: true, consistent: true, stale: false, lastSequence: 0, eventCount: 0, segmentCount: 1, fields: [] },
      schemaVersion: 'audit_schema_v2',
      skippedMalformed: 0,
    },
    meta: { requestId: 'r1', timestamp: '2026-06-15T00:00:00+00:00' },
  })
}

describe('Lens 4 — Audit cross-navigation (Phase 2E-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getAuditEventsV2).mockReset()
    mockStoreEventsV2()
    window.localStorage.clear()
  })

  it('AuditIdLink renders a lossy id but emits the FULL id on click', async () => {
    const full = 'pexa_0123456789abcdef0123456789abcdef_deadbeef'
    const wrapper = mount(AuditIdLink, { props: { id: full, label: 'post-exec audit' } })
    // The long id is truncated for display…
    expect(wrapper.text()).not.toContain(full)
    // …but the emitted payload carries the full id.
    await wrapper.find('button').trigger('click')
    const events = wrapper.emitted('navigate')
    expect(events).toBeTruthy()
    expect(events![0]![0]).toBe(full)
    // The accessible label still references the full id (screen-reader context).
    expect(wrapper.find('button').attributes('aria-label')).toContain('Jump to audit viewer')
  })

  it('AuditIdLink renders nothing for an empty / null id', () => {
    expect(mount(AuditIdLink, { props: { id: null } }).find('button').exists()).toBe(false)
    expect(mount(AuditIdLink, { props: { id: '' } }).find('button').exists()).toBe(false)
  })

  it('prefillAuditSearch switches to audit, enables store mode, sets the filter, AND fires load', async () => {
    const nav = useDevConsoleNavStore()
    const audit = useToolAuditStore()
    nav.initializeNavState()

    await nav.prefillAuditSearch('pexa_abc123')

    expect(nav.activeSection).toBe('audit')
    expect(audit.storeMode).toBe(true)
    expect(audit.searchInput).toBe('pexa_abc123')
    // The query MUST have fired — setting a filter alone is not enough.
    expect(getAuditEventsV2).toHaveBeenCalled()
  })

  it('the Audit Viewer prefill marker is rendered LOSSY (full id not displayed at length)', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const full = 'rollback_0123456789abcdef0123456789abcdef_deadbeef_cafebabe'
    nav.pendingAuditPrefill = full

    const wrapper = mount(AuditViewerSection)
    const marker = wrapper.find('[data-testid="dev-audit-prefill-marker"]')
    expect(marker.exists()).toBe(true)
    // The full long id must NOT appear in the rendered marker.
    expect(marker.text()).not.toContain(full)
    // A truncated prefix is shown instead.
    expect(marker.text().length).toBeLessThan(full.length)
  })

  it('clearing the prefill removes the marker', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    nav.pendingAuditPrefill = 'pexa_short'

    const wrapper = mount(AuditViewerSection)
    expect(wrapper.find('[data-testid="dev-audit-prefill-marker"]').exists()).toBe(true)
    await wrapper.find('[data-testid="dev-audit-clear-prefill"]').trigger('click')
    expect(nav.pendingAuditPrefill).toBeNull()
    expect(wrapper.find('[data-testid="dev-audit-prefill-marker"]').exists()).toBe(false)
  })

  it('no prefill → no marker (safe empty cross-nav state)', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    expect(nav.pendingAuditPrefill).toBeNull()
    const wrapper = mount(AuditViewerSection)
    expect(wrapper.find('[data-testid="dev-audit-prefill-marker"]').exists()).toBe(false)
  })
})
