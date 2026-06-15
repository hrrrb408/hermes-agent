/**
 * Controlled write tools store — Phase 2C dev-sandbox write workbench state.
 *
 * Manages the write-tool selector, target path + content inputs, the dry-run
 * preview result, the explicit confirmation checkbox, and the execution
 * result. The execute action is only enabled after a non-blocked preview and
 * an explicit user confirmation. The store never holds an API key or secret;
 * the confirmation token is an opaque single-use credential from the preview.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { runWritePreview as runWritePreviewApi, executeWrite as executeWriteApi, runRollbackPreview as runRollbackPreviewApi, executeRollback as executeRollbackApi } from '@/api/toolWrite'
import { isDevApiError } from '@/api/client'
import { WRITE_TOOL_IDS, type WriteToolArguments, type WriteToolId } from '@/types/api/toolWrite'

import type {
  RollbackExecuteResultData,
  RollbackPreviewResultData,
  WriteExecuteResultData,
  WritePreviewResultData,
} from '@/types/api/toolWrite'

export type WriteStatus = 'idle' | 'loading' | 'previewed' | 'completed' | 'blocked' | 'error'

const MAX_CONTENT_LENGTH = 64_000
const MAX_TARGET_PATH_LENGTH = 256

function _handleError(err: unknown): string {
  if (isDevApiError(err)) {
    return err.message
  }
  return 'An unexpected error occurred.'
}

/** Reject target paths that look unsafe before even calling the backend. */
export function isTargetPathUnsafe(value: string): boolean {
  if (!value) return false
  if (value.startsWith('/') || value.startsWith('~') || value.startsWith('\\')) return true
  if (value.includes('..')) return true
  if (value.includes('\x00')) return true
  return false
}

export const useToolWriteStore = defineStore('tool-write', () => {
  const toolId = ref<WriteToolId>('dev_sandbox_file_write')
  const targetPath = ref('')
  const content = ref('')
  const searchFragment = ref('')
  const replaceFragment = ref('')
  const explicitConfirmed = ref(false)
  const status = ref<WriteStatus>('idle')
  const error = ref('')
  const preview = ref<WritePreviewResultData | null>(null)
  const executeResult = ref<WriteExecuteResultData | null>(null)

  // Phase 2C-H1 — rollback execution state.
  const rollbackId = ref('')
  const rollbackPreview = ref<RollbackPreviewResultData | null>(null)
  const rollbackResult = ref<RollbackExecuteResultData | null>(null)
  const rollbackConfirmed = ref(false)
  const rollbackStatus = ref<WriteStatus>('idle')

  const selectableTools = WRITE_TOOL_IDS

  const targetPathUnsafe = computed(() => isTargetPathUnsafe(targetPath.value))

  const canPreview = computed(
    () =>
      targetPath.value.trim().length > 0 &&
      !targetPathUnsafe.value &&
      targetPath.value.length <= MAX_TARGET_PATH_LENGTH &&
      status.value !== 'loading',
  )

  const needsContent = computed(
    () => toolId.value === 'dev_sandbox_file_write' || toolId.value === 'dev_sandbox_file_append',
  )
  const needsPatch = computed(() => toolId.value === 'dev_sandbox_file_patch')

  const canExecute = computed(
    () =>
      preview.value !== null &&
      !preview.value.blocked &&
      preview.value.confirmationToken !== null &&
      explicitConfirmed.value === true &&
      status.value !== 'loading',
  )

  function setToolId(value: WriteToolId): void {
    toolId.value = value
    explicitConfirmed.value = false
    preview.value = null
    executeResult.value = null
    status.value = 'idle'
    error.value = ''
  }

  function setTargetPath(value: string): void {
    targetPath.value = value.slice(0, MAX_TARGET_PATH_LENGTH)
  }

  function setContent(value: string): void {
    content.value = value.slice(0, MAX_CONTENT_LENGTH)
  }

  function setSearchFragment(value: string): void {
    searchFragment.value = value.slice(0, MAX_CONTENT_LENGTH)
  }

  function setReplaceFragment(value: string): void {
    replaceFragment.value = value.slice(0, MAX_CONTENT_LENGTH)
  }

  function setExplicitConfirmed(value: boolean): void {
    explicitConfirmed.value = value
  }

  function reset(): void {
    status.value = 'idle'
    error.value = ''
    preview.value = null
    executeResult.value = null
    explicitConfirmed.value = false
  }

  function _buildArguments(): WriteToolArguments {
    const args: WriteToolArguments = { targetPath: targetPath.value.trim() }
    if (needsContent.value) {
      return { ...args, content: content.value, mode: 'create_or_replace' }
    }
    if (needsPatch.value) {
      return { ...args, search: searchFragment.value, replace: replaceFragment.value }
    }
    return args
  }

  async function runPreview(signal?: AbortSignal): Promise<void> {
    if (!canPreview.value) return
    status.value = 'loading'
    error.value = ''
    preview.value = null
    executeResult.value = null
    explicitConfirmed.value = false
    try {
      const response = await runWritePreviewApi(
        {
          mode: 'write_preview',
          toolId: toolId.value,
          arguments: _buildArguments(),
        },
        signal,
      )
      preview.value = response.data
      status.value = response.data.blocked ? 'blocked' : 'previewed'
    } catch (err) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      status.value = 'error'
    }
  }

  async function runExecute(signal?: AbortSignal): Promise<void> {
    if (!canExecute.value || preview.value === null) return
    status.value = 'loading'
    error.value = ''
    executeResult.value = null
    try {
      const response = await executeWriteApi(
        {
          mode: 'write',
          toolId: toolId.value,
          arguments: _buildArguments(),
          writePlanId: preview.value.writePlanId,
          confirmationToken: preview.value.confirmationToken ?? '',
          argumentDigest: preview.value.argumentDigest,
        },
        signal,
      )
      executeResult.value = response.data
      status.value = response.data.status === 'completed' ? 'completed' : 'blocked'
      // Phase 2C-H1: surface the rollback id so the UI can offer rollback.
      if (response.data.status === 'completed' && response.data.rollbackId) {
        rollbackId.value = response.data.rollbackId
      }
    } catch (err) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      status.value = 'error'
    }
  }

  // ---- Phase 2C-H1: rollback execution ----

  function setRollbackId(value: string): void {
    rollbackId.value = value.slice(0, 128)
    rollbackPreview.value = null
    rollbackResult.value = null
    rollbackConfirmed.value = false
    rollbackStatus.value = 'idle'
  }

  function setRollbackConfirmed(value: boolean): void {
    rollbackConfirmed.value = value
  }

  const canRollbackPreview = computed(
    () => rollbackId.value.trim().length > 0 && rollbackStatus.value !== 'loading',
  )

  const canRollbackExecute = computed(
    () =>
      rollbackPreview.value !== null &&
      !rollbackPreview.value.blocked &&
      rollbackPreview.value.confirmationToken !== null &&
      rollbackConfirmed.value === true &&
      rollbackStatus.value !== 'loading',
  )

  /** Token state derived from the last rollback result / blocked reason. */
  const rollbackTokenState = computed<'idle' | 'active' | 'used' | 'expired' | 'replay_blocked' | 'blocked'>(() => {
    if (rollbackResult.value === null) return 'idle'
    if (rollbackResult.value.status === 'completed') return 'used'
    const reason = rollbackResult.value.blockedReason ?? ''
    if (reason.includes('already_used') || reason.includes('already_executed') || reason.includes('replay')) {
      return 'replay_blocked'
    }
    if (reason.includes('expired')) return 'expired'
    return 'blocked'
  })

  async function runRollbackPreviewFn(signal?: AbortSignal): Promise<void> {
    if (!canRollbackPreview.value) return
    rollbackStatus.value = 'loading'
    rollbackPreview.value = null
    rollbackResult.value = null
    rollbackConfirmed.value = false
    try {
      const response = await runRollbackPreviewApi(
        { mode: 'rollback_preview', rollbackId: rollbackId.value.trim(), includeManifestList: true },
        signal,
      )
      rollbackPreview.value = response.data
      rollbackStatus.value = response.data.blocked ? 'blocked' : 'previewed'
    } catch (err) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      rollbackStatus.value = 'error'
    }
  }

  async function runRollbackExecuteFn(signal?: AbortSignal): Promise<void> {
    if (!canRollbackExecute.value || rollbackPreview.value === null) return
    rollbackStatus.value = 'loading'
    rollbackResult.value = null
    try {
      const response = await executeRollbackApi(
        {
          mode: 'rollback',
          rollbackId: rollbackPreview.value.rollbackId,
          confirmationToken: rollbackPreview.value.confirmationToken ?? '',
          argumentDigest: rollbackPreview.value.argumentDigest,
        },
        signal,
      )
      rollbackResult.value = response.data
      rollbackStatus.value = response.data.status === 'completed' ? 'completed' : 'blocked'
    } catch (err) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      rollbackStatus.value = 'error'
    }
  }

  return {
    toolId,
    targetPath,
    content,
    searchFragment,
    replaceFragment,
    explicitConfirmed,
    status,
    error,
    preview,
    executeResult,
    selectableTools,
    targetPathUnsafe,
    canPreview,
    canExecute,
    needsContent,
    needsPatch,
    setToolId,
    setTargetPath,
    setContent,
    setSearchFragment,
    setReplaceFragment,
    setExplicitConfirmed,
    reset,
    runPreview,
    runExecute,
    // Phase 2C-H1 rollback
    rollbackId,
    rollbackPreview,
    rollbackResult,
    rollbackConfirmed,
    rollbackStatus,
    rollbackTokenState,
    canRollbackPreview,
    canRollbackExecute,
    setRollbackId,
    setRollbackConfirmed,
    runRollbackPreview: runRollbackPreviewFn,
    runRollbackExecute: runRollbackExecuteFn,
  }
})
