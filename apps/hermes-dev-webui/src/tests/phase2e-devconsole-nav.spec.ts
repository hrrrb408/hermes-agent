/**
 * Phase 2E dev-console navigation store tests.
 *
 * Covers section persistence + the result→audit cross-navigation bridge
 * (`prefillAuditSearch`), which must switch section, enable store mode, set the
 * search filter, AND fire the query (loadStoreEvents) — not just set a filter.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock the audit API so cross-store orchestration does not hit the network.
vi.mock('@/api/toolAudit', () => ({
  getAuditEvents: vi.fn(),
  getAuditEventsV2: vi.fn(),
}))

import { getAuditEventsV2 } from '@/api/toolAudit'
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
      storeStatus: {
        present: true,
        segmentCount: 1,
        monotonic: true,
        activeSegment: 'seg-000001',
        schemaVersion: 'audit_schema_v2',
      },
      indexStatus: {
        present: true,
        consistent: true,
        stale: false,
        lastSequence: 0,
        eventCount: 0,
        segmentCount: 1,
        fields: [],
      },
      schemaVersion: 'audit_schema_v2',
      skippedMalformed: 0,
    },
    meta: { requestId: 'r1', timestamp: '2026-06-15T00:00:00+00:00' },
  })
}

describe('devConsoleNav store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getAuditEventsV2).mockReset()
    mockStoreEventsV2()
    window.localStorage.clear()
  })

  it('defaults to the overview section', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    expect(nav.activeSection).toBe('overview')
  })

  it('persists and restores the active section', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    nav.setSection('safety')
    expect(window.localStorage.getItem('hermes-dev-webui.devconsole.section')).toBe('safety')

    // Simulate a fresh store reading persisted state.
    const nav2 = useDevConsoleNavStore()
    // re-init path: readStoredSection reads localStorage directly
    nav2.initializeNavState()
    expect(nav2.activeSection).toBe('safety')
  })

  it('falls back to overview for an invalid persisted section', () => {
    window.localStorage.setItem('hermes-dev-webui.devconsole.section', 'nonsense')
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    expect(nav.activeSection).toBe('overview')
  })

  it('prefillAuditSearch switches section, enables store mode, sets the filter, AND loads', async () => {
    const nav = useDevConsoleNavStore()
    const audit = useToolAuditStore()
    nav.initializeNavState()
    expect(audit.storeMode).toBe(false)

    await nav.prefillAuditSearch('pexa_abc123')

    expect(nav.activeSection).toBe('audit')
    expect(nav.pendingAuditPrefill).toBe('pexa_abc123')
    expect(audit.storeMode).toBe(true)
    expect(audit.searchInput).toBe('pexa_abc123')
    // The query MUST have fired (setting a filter alone is not enough).
    expect(getAuditEventsV2).toHaveBeenCalled()
  })

  it('prefillAuditSearch is a no-op for an empty value', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    await nav.prefillAuditSearch('')
    expect(nav.activeSection).toBe('overview')
    expect(getAuditEventsV2).not.toHaveBeenCalled()
  })

  it('clearPendingPrefill clears the transient marker', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    await nav.prefillAuditSearch('rollback_xyz')
    expect(nav.pendingAuditPrefill).toBe('rollback_xyz')
    nav.clearPendingPrefill()
    expect(nav.pendingAuditPrefill).toBeNull()
  })
})
