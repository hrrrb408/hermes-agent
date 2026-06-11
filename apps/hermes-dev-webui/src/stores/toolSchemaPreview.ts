/**
 * Tool Schema Preview store for the Dev WebUI.
 *
 * Manages loading and selection state for the Schema Preview read-only data layer.
 *
 * Safety invariants:
 *   - Only GET requests — no POST/PUT/PATCH/DELETE
 *   - No tool execution, no dry-run, no provider schema sending
 *   - No dispatch, no audit, no allowlist mutation
 *   - preview ≠ execution — schemaPreviewAvailable does not enable execution
 *   - No localStorage / sessionStorage persistence
 *   - No background polling
 *   - No UI route navigation
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  fetchToolSchemaPreviewCatalog,
  fetchToolSchemaPreviewByCanonicalName,
} from '@/api/toolSchemaPreview'
import { isDevApiError } from '@/api/client'

import type {
  ToolSchemaPreviewCatalogData,
  ToolSchemaPreviewLookupData,
} from '@/types/api/toolSchemaPreview'
import type { LoadingState } from '@/stores/workspacePanel'

export const useToolSchemaPreviewStore = defineStore('workspace-tool-schema-preview', () => {
  // ── State ──

  const catalogState = ref<LoadingState>('idle')
  const previewState = ref<LoadingState>('idle')

  const catalog = ref<ToolSchemaPreviewCatalogData | null>(null)
  const selectedPreview = ref<ToolSchemaPreviewLookupData | null>(null)

  const selectedCanonicalName = ref<string | null>(null)

  const catalogError = ref('')
  const previewError = ref('')

  const lastFetchedAt = ref<string | null>(null)

  // ── Abort / Race protection ──

  let catalogAbortController: AbortController | null = null
  let previewAbortController: AbortController | null = null

  let catalogRequestSequence = 0
  let previewRequestSequence = 0

  // ── Computed / Getters ──

  const isCatalogLoading = computed(() => catalogState.value === 'loading')
  const isPreviewLoading = computed(() => previewState.value === 'loading')

  const hasCatalog = computed(() => catalog.value !== null)
  const hasSelectedPreview = computed(() => selectedPreview.value !== null)

  const items = computed(
    () => catalog.value?.items ?? [],
  )

  const availableItems = computed(
    () => items.value.filter(item => item.schemaPreviewAvailable),
  )

  const unavailableItems = computed(
    () => items.value.filter(item => !item.schemaPreviewAvailable),
  )

  const totalCount = computed(
    () => catalog.value?.totalCount ?? 0,
  )

  const availableCount = computed(
    () => catalog.value?.availableCount ?? 0,
  )

  const unavailableCount = computed(
    () => catalog.value?.unavailableCount ?? 0,
  )

  // ── Helpers ──

  function handleError(err: unknown): string {
    if (isDevApiError(err)) {
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  // ── Actions ──

  async function fetchCatalog(): Promise<void> {
    catalogAbortController?.abort()
    catalogAbortController = new AbortController()

    const sequence = ++catalogRequestSequence
    catalogState.value = 'loading'
    catalogError.value = ''

    try {
      const response = await fetchToolSchemaPreviewCatalog(
        catalogAbortController.signal,
      )

      // Stale response check
      if (sequence !== catalogRequestSequence) return

      catalog.value = response.data
      catalogState.value = response.data.items.length > 0 ? 'success' : 'empty'
      lastFetchedAt.value = response.meta.timestamp
    } catch (err: unknown) {
      if (sequence !== catalogRequestSequence) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      catalogError.value = handleError(err)
      catalogState.value = 'error'
    }
  }

  async function fetchPreview(canonicalName: string): Promise<void> {
    previewAbortController?.abort()
    previewAbortController = new AbortController()

    const sequence = ++previewRequestSequence
    previewState.value = 'loading'
    previewError.value = ''
    selectedCanonicalName.value = canonicalName

    try {
      const response = await fetchToolSchemaPreviewByCanonicalName(
        canonicalName,
        previewAbortController.signal,
      )

      // Stale response check
      if (sequence !== previewRequestSequence) return

      selectedPreview.value = response.data
      previewState.value = response.data.found ? 'success' : 'error'

      if (!response.data.found) {
        previewError.value = `Tool "${canonicalName}" not found in the policy inventory.`
      }
    } catch (err: unknown) {
      if (sequence !== previewRequestSequence) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return

      previewError.value = handleError(err)
      previewState.value = 'error'

      // 404 is a normal "not found" — not an execution state
      if (isDevApiError(err) && err.status === 404) {
        previewError.value = `Tool "${canonicalName}" not found in the policy inventory.`
      }
    }
  }

  // ── Reset actions ──

  function resetCatalog(): void {
    catalogAbortController?.abort()
    catalogAbortController = null
    catalogState.value = 'idle'
    catalog.value = null
    catalogError.value = ''
    lastFetchedAt.value = null
  }

  function resetSelectedPreview(): void {
    previewAbortController?.abort()
    previewAbortController = null
    previewState.value = 'idle'
    selectedPreview.value = null
    selectedCanonicalName.value = null
    previewError.value = ''
  }

  function resetErrors(): void {
    catalogError.value = ''
    previewError.value = ''
  }

  function resetAll(): void {
    resetCatalog()
    resetSelectedPreview()
    catalogRequestSequence = 0
    previewRequestSequence = 0
  }

  // ── Abort / Cleanup ──

  function abortCatalogRequest(): void {
    catalogAbortController?.abort()
    catalogAbortController = null
  }

  function abortPreviewRequest(): void {
    previewAbortController?.abort()
    previewAbortController = null
  }

  function abortAllRequests(): void {
    abortCatalogRequest()
    abortPreviewRequest()
  }

  return {
    // State
    catalogState,
    previewState,
    catalog,
    selectedPreview,
    selectedCanonicalName,
    catalogError,
    previewError,
    lastFetchedAt,
    // Computed / Getters
    isCatalogLoading,
    isPreviewLoading,
    hasCatalog,
    hasSelectedPreview,
    items,
    availableItems,
    unavailableItems,
    totalCount,
    availableCount,
    unavailableCount,
    // Actions
    fetchCatalog,
    fetchPreview,
    resetCatalog,
    resetSelectedPreview,
    resetErrors,
    resetAll,
    abortCatalogRequest,
    abortPreviewRequest,
    abortAllRequests,
  }
})
