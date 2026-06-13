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

import { getAuditEvents } from '@/api/toolAudit'
import { isDevApiError } from '@/api/client'

import type {
  AuditEventItem,
  AuditKind,
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

  let abortController: AbortController | null = null

  const isEmpty = computed(() => state.value === 'empty')
  const isLoading = computed(() => state.value === 'loading')

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
  }
})
