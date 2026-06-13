/**
 * Tool Execute store — clarify-only controlled execution workbench state.
 *
 * Manages the dry-run → confirm → execute flow for the single allowlisted
 * tool (clarify). The raw confirmation token returned by the dry-run
 * endpoint is held in an in-memory, non-reactive closure variable that is
 * never returned from the store, never persisted to storage, and never
 * logged. Only the safe correlation IDs (confirmationTokenId, audit IDs)
 * are exposed.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { runDryRun as runDryRunApi, executeTool as executeToolApi } from '@/api/toolExecute'
import { isDevApiError } from '@/api/client'

import type {
  DryRunResultData,
  ExecuteResultData,
} from '@/types/api/toolExecute'

/** Only clarify is allowlisted for controlled execution. */
export const EXECUTABLE_TOOL = 'clarify'

/** Execute workbench status. */
export type ExecuteStatus =
  | 'idle'
  | 'dry_run_loading'
  | 'dry_run_ready'
  | 'confirmation_required'
  | 'execute_loading'
  | 'blocked'
  | 'completed'
  | 'error'

function _handleError(err: unknown): string {
  if (isDevApiError(err)) {
    return err.message
  }
  return 'An unexpected error occurred.'
}

function _generateDryRunRequestId(): string {
  const rand =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, '')
      : Math.random().toString(36).slice(2)
  return `dr_${rand}`
}

export const useToolExecuteStore = defineStore('tool-execute', () => {
  const status = ref<ExecuteStatus>('idle')
  const error = ref('')

  const canonicalName = ref<string>(EXECUTABLE_TOOL)
  const question = ref('')
  const choicesText = ref('') // newline- or comma-separated choices

  const dryRunResult = ref<DryRunResultData | null>(null)
  const executeResult = ref<ExecuteResultData | null>(null)

  // Safe correlation state (exposed)
  const dryRunRequestId = ref<string | null>(null)
  const dryRunDecisionDigest = ref<string | null>(null)
  const confirmationTokenId = ref<string | null>(null)
  const confirmationTokenExpiresAt = ref<string | null>(null)

  // Raw confirmation token — IN-MEMORY ONLY. Never returned, never persisted,
  // never logged. Held in a closure variable so it is not reactive and not
  // discoverable via store state or devtools.
  let _confirmationToken: string | null = null

  let dryRunAbort: AbortController | null = null
  let executeAbort: AbortController | null = null

  // ── Derived state ──

  const isDryRunLoading = computed(() => status.value === 'dry_run_loading')
  const isExecuteLoading = computed(() => status.value === 'execute_loading')
  const isBlocked = computed(() => status.value === 'blocked')
  const isCompleted = computed(() => status.value === 'completed')

  /** The decision label to surface from the most recent execute result. */
  const executeDecision = computed(
    () => executeResult.value?.decision ?? null,
  )

  /** True only when the default handler-call gate blocks a valid request. */
  const isHandlerCallBlocked = computed(
    () => executeResult.value?.decision === 'blocked_tool_handler_call_not_enabled',
  )

  const sideEffects = computed(() => executeResult.value?.sideEffects ?? null)

  // ── Actions ──

  function _buildArguments(): Record<string, unknown> {
    const args: Record<string, unknown> = {}
    const q = question.value.trim()
    if (q) {
      args.question = q
    }
    const rawChoices = choicesText.value
      .split(/[\n,]/)
      .map((c) => c.trim())
      .filter((c) => c.length > 0)
    if (rawChoices.length > 0) {
      args.choices = rawChoices
    }
    return args
  }

  function setQuestion(value: string): void {
    question.value = value
  }

  function setChoicesText(value: string): void {
    choicesText.value = value
  }

  async function runDryRun(): Promise<void> {
    dryRunAbort?.abort()
    dryRunAbort = new AbortController()
    status.value = 'dry_run_loading'
    error.value = ''
    executeResult.value = null

    const requestId = _generateDryRunRequestId()
    dryRunRequestId.value = requestId

    try {
      const response = await runDryRunApi(
        {
          canonicalName: canonicalName.value,
          argumentsPreview: _buildArguments(),
          requestId,
          issueConfirmationToken: true,
          sourceContext: 'dev-webui',
          uiOrigin: 'tool-execute-panel',
        },
        dryRunAbort.signal,
      )
      dryRunResult.value = response.data
      dryRunDecisionDigest.value = response.data.dryRunDecisionDigest

      const token = response.data.confirmationToken ?? null
      _confirmationToken = token
      confirmationTokenId.value = response.data.confirmationTokenId ?? null
      confirmationTokenExpiresAt.value =
        response.data.confirmationTokenExpiresAt ?? null

      if (
        response.data.decision === 'would_allow' &&
        token &&
        confirmationTokenId.value
      ) {
        status.value = 'confirmation_required'
      } else {
        // Eligible decision known but no token issued — ready without confirm.
        status.value = 'dry_run_ready'
      }
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      status.value = 'error'
    }
  }

  async function runExecute(): Promise<void> {
    if (!_confirmationToken || !dryRunDecisionDigest.value || !dryRunRequestId.value) {
      error.value = 'A valid dry-run confirmation is required before executing.'
      status.value = 'error'
      return
    }

    executeAbort?.abort()
    executeAbort = new AbortController()
    status.value = 'execute_loading'
    error.value = ''

    try {
      const response = await executeToolApi(
        {
          canonicalName: canonicalName.value,
          argumentsPreview: _buildArguments(),
          dryRunRequestId: dryRunRequestId.value,
          dryRunDecisionDigest: dryRunDecisionDigest.value,
          confirmationToken: _confirmationToken,
          requestId: dryRunRequestId.value,
          sourceContext: 'dev-webui',
          uiOrigin: 'tool-execute-panel',
        },
        executeAbort.signal,
      )
      executeResult.value = response.data

      if (response.data.decision === 'clarify_execution_completed') {
        status.value = 'completed'
        // The one-time confirmation token has been consumed.
        _confirmationToken = null
      } else {
        // Any non-completed decision is a controlled block.
        status.value = 'blocked'
        _confirmationToken = null
      }
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      status.value = 'error'
      _confirmationToken = null
    }
  }

  function reset(): void {
    dryRunAbort?.abort()
    executeAbort?.abort()
    status.value = 'idle'
    error.value = ''
    dryRunResult.value = null
    executeResult.value = null
    dryRunRequestId.value = null
    dryRunDecisionDigest.value = null
    confirmationTokenId.value = null
    confirmationTokenExpiresAt.value = null
    _confirmationToken = null
  }

  function abortAllRequests(): void {
    dryRunAbort?.abort()
    executeAbort?.abort()
  }

  return {
    // state
    status,
    error,
    canonicalName,
    question,
    choicesText,
    dryRunResult,
    executeResult,
    dryRunRequestId,
    dryRunDecisionDigest,
    confirmationTokenId,
    confirmationTokenExpiresAt,
    // derived
    isDryRunLoading,
    isExecuteLoading,
    isBlocked,
    isCompleted,
    executeDecision,
    isHandlerCallBlocked,
    sideEffects,
    // actions
    setQuestion,
    setChoicesText,
    runDryRun,
    runExecute,
    reset,
    abortAllRequests,
  }
})
