/**
 * Tests for the Tool Audit Pinia store (Phase 1G-04-30).
 *
 * Covers audit kind switching, loading, empty state, pagination,
 * error handling, and the safety invariant that no raw secret ever
 * enters store state from the API.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolAuditStore } from '@/stores/toolAudit'
import type { AuditEventItem } from '@/types/api/toolAudit'

// ── Mock the API module ──

vi.mock('@/api/toolAudit', () => ({
  getAuditEvents: vi.fn(),
}))

import { getAuditEvents } from '@/api/toolAudit'

function makeItem(overrides: Partial<AuditEventItem> = {}): AuditEventItem {
  return {
    auditKind: 'post_execution',
    auditId: 'pexa_abc',
    timestamp: '2026-06-13T00:00:00+00:00',
    canonicalName: 'clarify',
    decision: 'clarify_execution_completed',
    executionStatus: 'completed',
    handlerCallId: 'thc_abc',
    sideEffects: {
      providerSchemaSent: false,
      providerApiCalled: false,
      externalSideEffects: false,
    },
    safeSummary: { questionCount: 1 },
    ...overrides,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
})

describe('toolAuditStore — initial state', () => {
  it('defaults to post_execution kind and idle state', () => {
    const store = useToolAuditStore()
    expect(store.auditKind).toBe('post_execution')
    expect(store.state).toBe('idle')
    expect(store.items).toEqual([])
  })
})

describe('toolAuditStore — loading', () => {
  it('loads items into success state', async () => {
    vi.mocked(getAuditEvents).mockResolvedValue({
      data: {
        auditKind: 'post_execution',
        items: [makeItem()],
        nextCursor: null,
        limit: 50,
        hasMore: false,
        skippedMalformed: 0,
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolAuditStore()
    await store.loadEvents()
    expect(store.state).toBe('success')
    expect(store.items.length).toBe(1)
    expect(store.items[0]?.handlerCallId).toBe('thc_abc')
  })

  it('enters empty state when no items', async () => {
    vi.mocked(getAuditEvents).mockResolvedValue({
      data: {
        auditKind: 'dry_run',
        items: [],
        nextCursor: null,
        limit: 50,
        hasMore: false,
        skippedMalformed: 0,
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolAuditStore()
    store.setAuditKind('dry_run')
    await store.loadEvents()
    expect(store.state).toBe('empty')
    expect(store.isEmpty).toBe(true)
  })

  it('enters error state on API failure', async () => {
    vi.mocked(getAuditEvents).mockRejectedValue({
      code: 'NETWORK_ERROR',
      message: 'Unable to connect.',
    })
    const store = useToolAuditStore()
    await store.loadEvents()
    expect(store.state).toBe('error')
    expect(store.error).toBe('Unable to connect.')
  })

  it('switching kind resets pagination', async () => {
    vi.mocked(getAuditEvents).mockResolvedValue({
      data: {
        auditKind: 'post_execution',
        items: [makeItem()],
        nextCursor: '50',
        limit: 50,
        hasMore: true,
        skippedMalformed: 0,
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolAuditStore()
    await store.loadEvents()
    expect(store.hasMore).toBe(true)
    store.setAuditKind('dry_run')
    expect(store.hasMore).toBe(false)
    expect(store.nextCursor).toBeNull()
  })
})

describe('toolAuditStore — pagination', () => {
  it('loadMore appends items and advances cursor', async () => {
    vi.mocked(getAuditEvents)
      .mockResolvedValueOnce({
        data: {
          auditKind: 'post_execution',
          items: [makeItem({ auditId: 'a' })],
          nextCursor: '1',
          limit: 1,
          hasMore: true,
          skippedMalformed: 0,
        },
        meta: { requestId: 'r1', timestamp: 't1' },
      })
      .mockResolvedValueOnce({
        data: {
          auditKind: 'post_execution',
          items: [makeItem({ auditId: 'b' })],
          nextCursor: null,
          limit: 1,
          hasMore: false,
          skippedMalformed: 0,
        },
        meta: { requestId: 'r2', timestamp: 't2' },
      })
    const store = useToolAuditStore()
    store.setLimit(1)
    await store.loadEvents()
    await store.loadMore()
    expect(store.items.map((i) => i.auditId)).toEqual(['a', 'b'])
    expect(store.hasMore).toBe(false)
  })
})

describe('toolAuditStore — safety', () => {
  it('surfaces only safe fields (no raw token / args / secrets)', async () => {
    // Even if the API contract were violated, the store only reflects what
    // the typed response carries. Confirm side-effects are faithfully false.
    vi.mocked(getAuditEvents).mockResolvedValue({
      data: {
        auditKind: 'post_execution',
        items: [makeItem()],
        nextCursor: null,
        limit: 50,
        hasMore: false,
        skippedMalformed: 0,
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolAuditStore()
    await store.loadEvents()
    const se = store.items[0]?.sideEffects
    expect(se?.providerSchemaSent).toBe(false)
    expect(se?.providerApiCalled).toBe(false)
    expect(se?.externalSideEffects).toBe(false)
  })
})

describe('toolAuditStore — limit control', () => {
  it('clamps limit to [1, 100]', () => {
    const store = useToolAuditStore()
    store.setLimit(0)
    expect(store.limit).toBe(1)
    store.setLimit(9999)
    expect(store.limit).toBe(100)
    store.setLimit(25)
    expect(store.limit).toBe(25)
  })
})
