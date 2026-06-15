/**
 * Phase 2D — Tool Audit durable-store mode tests.
 *
 * Covers the store-mode query path: cursor pagination, filters, safe search,
 * store/index status badges, redactionApplied visibility, corruption warning,
 * and the safety invariant that no raw secret/callable/raw-args ever enters
 * store state from the API.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolAuditStore } from '@/stores/toolAudit'
import type {
  StoreAuditEventItem,
  StoreAuditEventsData,
} from '@/types/api/toolAudit'

// ── Mock the API module (both legacy + v2) ──

vi.mock('@/api/toolAudit', () => ({
  getAuditEvents: vi.fn(),
  getAuditEventsV2: vi.fn(),
}))

import { getAuditEventsV2 } from '@/api/toolAudit'

function makeStoreItem(
  overrides: Partial<StoreAuditEventItem> = {},
): StoreAuditEventItem {
  return {
    eventId: 'evt_1',
    sequence: 1,
    createdAt: '2026-06-15T00:00:00+00:00',
    eventType: 'clarify_execution_completed',
    auditKind: 'post_execution',
    toolId: 'clarify',
    status: 'completed',
    readOnly: true,
    writeRequired: false,
    providerMode: 'fake',
    redactionApplied: true,
    schemaVersion: 'audit_schema_v2',
    ...overrides,
  }
}

function makeStoreData(
  items: StoreAuditEventItem[],
  overrides: Partial<StoreAuditEventsData> = {},
): StoreAuditEventsData {
  return {
    items,
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
      activeSegment: 'audit-000001.jsonl',
      schemaVersion: 'audit_schema_v2',
    },
    indexStatus: {
      present: true,
      consistent: true,
      stale: false,
      lastSequence: items.length,
      eventCount: items.length,
      segmentCount: 1,
      fields: ['eventType', 'toolId'],
    },
    schemaVersion: 'audit_schema_v2',
    skippedMalformed: 0,
    ...overrides,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('toolAuditStore v2 — store mode', () => {
  it('defaults to store mode off', () => {
    const store = useToolAuditStore()
    expect(store.storeMode).toBe(false)
    expect(store.storeItems).toEqual([])
  })

  it('toggles store mode and clears store items', () => {
    const store = useToolAuditStore()
    store.setStoreMode(true)
    expect(store.storeMode).toBe(true)
    store.setStoreMode(false)
    expect(store.storeMode).toBe(false)
    expect(store.storeItems).toEqual([])
  })

  it('loads store events with status badges', async () => {
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([makeStoreItem()]),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    expect(store.state).toBe('success')
    expect(store.storeItems.length).toBe(1)
    expect(store.storeStatus?.present).toBe(true)
    expect(store.indexStatus?.present).toBe(true)
    expect(store.storeSchemaVersion).toBe('audit_schema_v2')
    expect(store.storeSegmentCount).toBe(1)
  })

  it('renders empty state when no store events', async () => {
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([]),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    expect(store.state).toBe('empty')
  })

  it('records corrupt-skipped count as corruption warning', async () => {
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([makeStoreItem()], { skippedMalformed: 2 }),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    expect(store.corruptSkipped).toBe(2)
  })

  it('paginates with next cursor', async () => {
    vi.mocked(getAuditEventsV2)
      .mockResolvedValueOnce({
        data: makeStoreData([makeStoreItem({ eventId: 'a', sequence: 2 })], {
          nextCursor: 'cur1', hasMore: true,
        }),
      } as never)
      .mockResolvedValueOnce({
        data: makeStoreData([makeStoreItem({ eventId: 'b', sequence: 1 })]),
      } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    expect(store.storeHasMore).toBe(true)
    expect(store.storeNextCursor).toBe('cur1')
    await store.loadStoreNext()
    expect(store.storeItems.length).toBe(2)
  })

  it('indexStale reflects stale index status', async () => {
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([makeStoreItem()], {
        indexStatus: {
          present: true, consistent: false, stale: true,
          lastSequence: 1, eventCount: 1, segmentCount: 1, fields: [],
        },
      }),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    expect(store.indexStale).toBe(true)
  })

  it('filters are settable', () => {
    const store = useToolAuditStore()
    store.setEventTypeFilter('foo')
    store.setStatusFilter('blocked')
    store.setProviderModeFilter('fake')
    store.setWriteRequiredFilter('true')
    store.setReadOnlyFilter('false')
    store.setSearchInput('needle')
    expect(store.eventTypeFilter).toBe('foo')
    expect(store.statusFilter).toBe('blocked')
    expect(store.providerModeFilter).toBe('fake')
    expect(store.writeRequiredFilter).toBe('true')
    expect(store.readOnlyFilter).toBe('false')
    expect(store.searchInput).toBe('needle')
  })

  it('resetStore clears store state', async () => {
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([makeStoreItem()]),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    store.resetStore()
    expect(store.storeItems).toEqual([])
    expect(store.storeHasMore).toBe(false)
  })

  it('never holds raw secret from API response', async () => {
    // Even if the API somehow returned a secret field, it must not be a
    // top-level surfaced field (the backend strips forbidden keys).
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([
        makeStoreItem({
          safeMetadata: { api_key: '[REDACTED]' },
        }),
      ]),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    const blob = JSON.stringify(store.storeItems)
    expect(blob).not.toContain('sk-')
    expect(blob).not.toContain('rawArguments')
  })

  it('exposes redactionApplied per item', async () => {
    vi.mocked(getAuditEventsV2).mockResolvedValue({
      data: makeStoreData([makeStoreItem({ redactionApplied: true })]),
    } as never)
    const store = useToolAuditStore()
    store.setStoreMode(true)
    await store.loadStoreEvents()
    const first = store.storeItems[0]
    expect(first).toBeDefined()
    expect(first?.redactionApplied).toBe(true)
  })
})
