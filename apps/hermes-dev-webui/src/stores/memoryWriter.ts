/**
 * Memory Writer Preview Store.
 *
 * Manages state for the Memory Writer dry-run panel:
 * - Active operation selection (WRITE / UPDATE / ARCHIVE)
 * - Form state for each operation
 * - Preview result, loading, and error states
 * - AbortController for request cancellation
 *
 * This store never triggers real writes — preview only.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  previewMemoryWrite,
  previewMemoryUpdate,
  previewMemoryArchive,
} from '@/api/memory'
import { isDevApiError } from '@/api/client'
import type {
  MemoryDryRunResult,
  MemoryWriterOperation,
  MemoryWriterLoadingState,
  MemoryUpdateDryRunRequest,
  MemoryArchiveDryRunRequest,
} from '@/types/api/memory'

function _handleError(err: unknown): string {
  if (isDevApiError(err)) {
    return err.message || 'An API error occurred.'
  }
  if (err instanceof Error) {
    return err.message
  }
  return 'An unexpected error occurred.'
}

export const useMemoryWriterStore = defineStore('memoryWriter', () => {
  // ── Active operation ──
  const activeOperation = ref<MemoryWriterOperation>('write')

  // ── Loading state ──
  const loadingState = ref<MemoryWriterLoadingState>('idle')
  const previewError = ref<string | null>(null)
  const previewResult = ref<MemoryDryRunResult | null>(null)

  // ── Abort controller ──
  let _abortController: AbortController | null = null

  // ── WRITE form ──
  const writeForm = ref({
    query: '',
    summary: '',
    title: '',
    category: '',
    type: 'project_status',
    importance: 'P2' as 'P0' | 'P1' | 'P2' | 'P3',
    ttl: 'project' as 'permanent' | 'project' | 'session' | 'temporary',
    tags: '',
    sourceConfidence: 'user_confirmed' as 'user_confirmed' | 'assistant_inferred',
  })

  // ── UPDATE form ──
  const updateForm = ref({
    memoryId: '',
    summary: '',
    importance: '' as '' | 'P0' | 'P1' | 'P2' | 'P3',
    ttl: '' as '' | 'permanent' | 'project' | 'session' | 'temporary',
    tags: '',
  })

  // ── ARCHIVE form ──
  const archiveForm = ref({
    memoryId: '',
    reason: '',
  })

  // ── Computed ──
  const isLoading = computed(() => loadingState.value === 'loading')
  const isSuccess = computed(() => loadingState.value === 'success')
  const isError = computed(() => loadingState.value === 'error')
  const isIdle = computed(() => loadingState.value === 'idle')

  // ── Actions ──

  function _cancelPending() {
    if (_abortController) {
      _abortController.abort()
      _abortController = null
    }
  }

  function setActiveOperation(op: MemoryWriterOperation) {
    _cancelPending()
    activeOperation.value = op
    previewResult.value = null
    previewError.value = null
    loadingState.value = 'idle'
  }

  async function runWritePreview() {
    _cancelPending()
    _abortController = new AbortController()
    const signal = _abortController.signal

    loadingState.value = 'loading'
    previewError.value = null
    previewResult.value = null

    try {
      const tags = writeForm.value.tags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0)

      const response = await previewMemoryWrite(
        {
          query: writeForm.value.query,
          candidate: {
            summary: writeForm.value.summary,
            title: writeForm.value.title || undefined,
            category: writeForm.value.category,
            type: writeForm.value.type || undefined,
            importance: writeForm.value.importance,
            ttl: writeForm.value.ttl,
            tags,
            sourceConfidence: writeForm.value.sourceConfidence,
          },
        },
        signal,
      )
      previewResult.value = response.data
      loadingState.value = 'success'
    } catch (err: unknown) {
      if (signal.aborted) return
      previewError.value = _handleError(err)
      loadingState.value = 'error'
    }
  }

  async function runUpdatePreview() {
    _cancelPending()
    _abortController = new AbortController()
    const signal = _abortController.signal

    loadingState.value = 'loading'
    previewError.value = null
    previewResult.value = null

    try {
      const tags = updateForm.value.tags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0)

      const candidate: MemoryUpdateDryRunRequest['candidate'] = {
        summary: updateForm.value.summary,
        ...(updateForm.value.importance ? { importance: updateForm.value.importance } : {}),
        ...(updateForm.value.ttl ? { ttl: updateForm.value.ttl } : {}),
        ...(tags.length > 0 ? { tags } : {}),
      }

      const response = await previewMemoryUpdate(
        updateForm.value.memoryId,
        { candidate },
        signal,
      )
      previewResult.value = response.data
      loadingState.value = 'success'
    } catch (err: unknown) {
      if (signal.aborted) return
      previewError.value = _handleError(err)
      loadingState.value = 'error'
    }
  }

  async function runArchivePreview() {
    _cancelPending()
    _abortController = new AbortController()
    const signal = _abortController.signal

    loadingState.value = 'loading'
    previewError.value = null
    previewResult.value = null

    try {
      const payload: MemoryArchiveDryRunRequest = {
        ...(archiveForm.value.reason ? { reason: archiveForm.value.reason } : {}),
      }

      const response = await previewMemoryArchive(
        archiveForm.value.memoryId,
        payload,
        signal,
      )
      previewResult.value = response.data
      loadingState.value = 'success'
    } catch (err: unknown) {
      if (signal.aborted) return
      previewError.value = _handleError(err)
      loadingState.value = 'error'
    }
  }

  function clearPreview() {
    _cancelPending()
    previewResult.value = null
    previewError.value = null
    loadingState.value = 'idle'
  }

  function resetForms() {
    clearPreview()
    writeForm.value = {
      query: '',
      summary: '',
      title: '',
      category: '',
      type: 'project_status',
      importance: 'P2',
      ttl: 'project',
      tags: '',
      sourceConfidence: 'user_confirmed',
    }
    updateForm.value = {
      memoryId: '',
      summary: '',
      importance: '',
      ttl: '',
      tags: '',
    }
    archiveForm.value = {
      memoryId: '',
      reason: '',
    }
  }

  return {
    // State
    activeOperation,
    loadingState,
    previewError,
    previewResult,
    writeForm,
    updateForm,
    archiveForm,

    // Computed
    isLoading,
    isSuccess,
    isError,
    isIdle,

    // Actions
    setActiveOperation,
    runWritePreview,
    runUpdatePreview,
    runArchivePreview,
    clearPreview,
    resetForms,
  }
})
