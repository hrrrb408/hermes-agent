/**
 * Tool Audit store — read-only audit viewer state.
 *
 * Manages loading of safe, redacted audit events for the dry-run,
 * pre-execution, and post-execution audit kinds. Supports kind switching,
 * limit control, refresh, and cursor pagination. No raw token, full token
 * hash, raw arguments, or secrets are ever held or surfaced — the backend
 * returns only whitelisted safe items.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { getAuditEvents, getAuditEventsV2 } from '@/api/toolAudit'
import { isDevApiError } from '@/api/client'

import type {
  AuditEventItem,
  AuditKind,
  StoreAuditEventItem,
  AuditStoreStatus,
  AuditIndexStatus,
} from '@/types/api/toolAudit'

export type AuditLoadingState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

export const AUDIT_KINDS: readonly AuditKind[] = [
  'dry_run',
  'pre_execution',
  'post_execution',
] as const

export const AUDIT_KIND_LABELS: Record<AuditKind, string> = {
  dry_run: 'Dry-Run',
  pre_execution: 'Pre-Execution',
  post_execution: 'Post-Execution',
}

function _handleError(err: unknown): string {
  if (isDevApiError(err)) {
    return err.message
  }
  return 'An unexpected error occurred.'
}

export const useToolAuditStore = defineStore('tool-audit', () => {
  const state = ref<AuditLoadingState>('idle')
  const error = ref('')
  const auditKind = ref<AuditKind>('post_execution')
  const limit = ref<number>(50)
  const canonicalNameFilter = ref<string>('')

  const items = ref<readonly AuditEventItem[]>([])
  const nextCursor = ref<string | null>(null)
  const hasMore = ref(false)
  const skippedMalformed = ref(0)

  // ---- Phase 2D durable-store query state ----
  const storeMode = ref(false)
  const storeItems = ref<readonly StoreAuditEventItem[]>([])
  const storeNextCursor = ref<string | null>(null)
  const storePreviousCursor = ref<string | null>(null)
  const storeHasMore = ref(false)
  const storeSkipped = ref(0)
  const storeStatus = ref<AuditStoreStatus | null>(null)
  const indexStatus = ref<AuditIndexStatus | null>(null)
  const storeSchemaVersion = ref<string>('')
  const storeSegmentCount = ref(0)
  const corruptSkipped = ref(0)

  const eventTypeFilter = ref<string>('')
  const statusFilter = ref<string>('')
  const sourceFilter = ref<string>('')
  const providerModeFilter = ref<string>('')
  const writeRequiredFilter = ref<string>('') // '' | 'true' | 'false'
  const readOnlyFilter = ref<string>('')
  const searchInput = ref<string>('')

  let abortController: AbortController | null = null

  const isEmpty = computed(() => state.value === 'empty')
  const isLoading = computed(() => state.value === 'loading')
  const indexStale = computed(
    () => !!indexStatus.value && (indexStatus.value.stale || !indexStatus.value.consistent),
  )

  function setAuditKind(kind: AuditKind): void {
    if (kind !== auditKind.value) {
      auditKind.value = kind
      // Reset pagination on kind change
      nextCursor.value = null
      hasMore.value = false
    }
  }

  function setLimit(value: number): void {
    limit.value = Math.max(1, Math.min(100, Math.floor(value)))
  }

  function setCanonicalNameFilter(value: string): void {
    canonicalNameFilter.value = value
  }

  async function loadEvents(): Promise<void> {
    abortController?.abort()
    abortController = new AbortController()
    state.value = 'loading'
    error.value = ''

    try {
      const response = await getAuditEvents(
        {
          auditKind: auditKind.value,
          limit: limit.value,
          canonicalName: canonicalNameFilter.value.trim() || undefined,
        },
        abortController.signal,
      )
      const data = response.data
      items.value = data.items
      nextCursor.value = data.nextCursor
      hasMore.value = data.hasMore
      skippedMalformed.value = data.skippedMalformed
      state.value = data.items.length > 0 ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      state.value = 'error'
    }
  }

  async function loadMore(): Promise<void> {
    if (!hasMore.value || !nextCursor.value) return
    abortController?.abort()
    abortController = new AbortController()

    try {
      const response = await getAuditEvents(
        {
          auditKind: auditKind.value,
          limit: limit.value,
          cursor: nextCursor.value,
          canonicalName: canonicalNameFilter.value.trim() || undefined,
        },
        abortController.signal,
      )
      const data = response.data
      items.value = [...items.value, ...data.items]
      nextCursor.value = data.nextCursor
      hasMore.value = data.hasMore
      skippedMalformed.value = data.skippedMalformed
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      state.value = 'error'
    }
  }

  function reset(): void {
    abortController?.abort()
    state.value = 'idle'
    error.value = ''
    items.value = []
    nextCursor.value = null
    hasMore.value = false
    skippedMalformed.value = 0
  }

  // ---- Phase 2D store-mode helpers ----

  function _storeFilters() {
    return {
      eventType: eventTypeFilter.value.trim() || undefined,
      status: statusFilter.value.trim() || undefined,
      source: sourceFilter.value.trim() || undefined,
      providerMode: providerModeFilter.value.trim() || undefined,
      readOnly: readOnlyFilter.value === '' ? undefined : readOnlyFilter.value === 'true',
      writeRequired: writeRequiredFilter.value === '' ? undefined : writeRequiredFilter.value === 'true',
      search: searchInput.value.trim() || undefined,
    }
  }

  function setStoreMode(enabled: boolean): void {
    storeMode.value = !!enabled
    storeItems.value = []
    storeNextCursor.value = null
    storePreviousCursor.value = null
    storeHasMore.value = false
    storeSkipped.value = 0
    corruptSkipped.value = 0
  }

  function setEventTypeFilter(v: string): void { eventTypeFilter.value = v }
  function setStatusFilter(v: string): void { statusFilter.value = v }
  function setSourceFilter(v: string): void { sourceFilter.value = v }
  function setProviderModeFilter(v: string): void { providerModeFilter.value = v }
  function setWriteRequiredFilter(v: string): void { writeRequiredFilter.value = v }
  function setReadOnlyFilter(v: string): void { readOnlyFilter.value = v }
  function setSearchInput(v: string): void { searchInput.value = v }

  function _buildStoreQuery(cursor?: string) {
    const filters = _storeFilters()
    return {
      auditKind: auditKind.value as unknown as string,
      limit: limit.value,
      order: 'desc' as const,
      cursor,
      ...filters,
    }
  }

  async function loadStoreEvents(): Promise<void> {
    abortController?.abort()
    abortController = new AbortController()
    state.value = 'loading'
    error.value = ''
    try {
      const resp = await getAuditEventsV2(_buildStoreQuery(), abortController.signal)
      const data = resp.data
      storeItems.value = data.items
      storeNextCursor.value = data.nextCursor
      storePreviousCursor.value = data.previousCursor
      storeHasMore.value = data.hasMore
      storeSkipped.value = data.skippedMalformed
      corruptSkipped.value = data.skippedMalformed
      storeStatus.value = data.storeStatus
      indexStatus.value = data.indexStatus
      storeSchemaVersion.value = data.schemaVersion
      storeSegmentCount.value = data.storeStatus.segmentCount
      state.value = data.items.length > 0 ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      state.value = 'error'
    }
  }

  async function loadStoreNext(): Promise<void> {
    if (!storeHasMore.value || !storeNextCursor.value) return
    abortController?.abort()
    abortController = new AbortController()
    try {
      const resp = await getAuditEventsV2(
        _buildStoreQuery(storeNextCursor.value),
        abortController.signal,
      )
      const data = resp.data
      storeItems.value = [...storeItems.value, ...data.items]
      storeNextCursor.value = data.nextCursor
      storePreviousCursor.value = data.previousCursor
      storeHasMore.value = data.hasMore
      storeSkipped.value += data.skippedMalformed
      corruptSkipped.value += data.skippedMalformed
      storeStatus.value = data.storeStatus
      indexStatus.value = data.indexStatus
      storeSchemaVersion.value = data.schemaVersion
      storeSegmentCount.value = data.storeStatus.segmentCount
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      state.value = 'error'
    }
  }

  function resetStore(): void {
    abortController?.abort()
    storeItems.value = []
    storeNextCursor.value = null
    storePreviousCursor.value = null
    storeHasMore.value = false
    storeSkipped.value = 0
    corruptSkipped.value = 0
  }

  return {
    state,
    error,
    auditKind,
    limit,
    canonicalNameFilter,
    items,
    nextCursor,
    hasMore,
    skippedMalformed,
    isEmpty,
    isLoading,
    setAuditKind,
    setLimit,
    setCanonicalNameFilter,
    loadEvents,
    loadMore,
    reset,
    // Phase 2D store-mode
    storeMode,
    storeItems,
    storeNextCursor,
    storePreviousCursor,
    storeHasMore,
    storeSkipped,
    storeStatus,
    indexStatus,
    indexStale,
    storeSchemaVersion,
    storeSegmentCount,
    corruptSkipped,
    eventTypeFilter,
    statusFilter,
    sourceFilter,
    providerModeFilter,
    writeRequiredFilter,
    readOnlyFilter,
    searchInput,
    setStoreMode,
    setEventTypeFilter,
    setStatusFilter,
    setSourceFilter,
    setProviderModeFilter,
    setWriteRequiredFilter,
    setReadOnlyFilter,
    setSearchInput,
    loadStoreEvents,
    loadStoreNext,
    resetStore,
  }
})
