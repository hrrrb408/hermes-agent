/**
 * Tool Execute store — read-only controlled execution workbench state.
 *
 * Manages the dry-run → confirm → execute flow for the allowlisted read-only
 * tools (clarify + the five Phase 2A inspection tools). The raw confirmation
 * token returned by the dry-run endpoint is held in an in-memory, non-reactive
 * closure variable that is never returned from the store, never persisted to
 * storage, and never logged. Only the safe correlation IDs
 * (confirmationTokenId, audit IDs) are exposed.
 *
 * Phase 2A: generalized from clarify-only to multi-tool dispatch-by-name. The
 * "completed" signal is now the executionCompleted boolean (not the decision
 * string), so every read-only tool's `<toolId>_execution_completed` decision
 * is recognized. Clarify keeps its Phase 1G behavior.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { runDryRun as runDryRunApi, executeTool as executeToolApi } from '@/api/toolExecute'
import { isDevApiError } from '@/api/client'

import type {
  DryRunResultData,
  ExecuteResultData,
} from '@/types/api/toolExecute'
import {
  DEFAULT_TOOL,
  EXECUTABLE_TOOL,
  SELECTABLE_TOOLS,
  SELECTABLE_TOOL_IDS,
  getToolMeta,
} from '@/constants/readOnlyTools'

// Re-export for callers that imported EXECUTABLE_TOOL from this module.
export { EXECUTABLE_TOOL, SELECTABLE_TOOLS, SELECTABLE_TOOL_IDS }

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

  const canonicalName = ref<string>(DEFAULT_TOOL)
  const question = ref('')
  const choicesText = ref('') // newline- or comma-separated choices (clarify only)

  // Phase 2A: generic per-tool argument values for the read-only tools.
  // Bounded by each tool's argument spec in constants/readOnlyTools.ts — the
  // UI never accepts free shell/path/provider input, only the declared keys.
  const argumentValues = ref<Record<string, unknown>>({})

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

  /** Metadata for the currently selected tool (display name, arg spec, badges). */
  const selectedToolMeta = computed(() => getToolMeta(canonicalName.value))

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

  /** Build the arguments payload for the currently selected tool. */
  function _buildArguments(): Record<string, unknown> {
    // Clarify keeps its dedicated question/choices builder.
    if (canonicalName.value === 'clarify') {
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

    // Read-only tools: emit only the declared keys with non-empty values.
    const meta = selectedToolMeta.value
    const args: Record<string, unknown> = {}
    if (!meta) {
      return args
    }
    for (const spec of meta.arguments) {
      if (!(spec.key in argumentValues.value)) {
        continue
      }
      const value = argumentValues.value[spec.key]
      if (value === undefined || value === null || value === '') {
        continue
      }
      // Bound strings to their declared maxLength defensively.
      if (spec.kind === 'string' && typeof value === 'string') {
        const max = spec.maxLength ?? 4000
        args[spec.key] = value.slice(0, max)
      } else if (spec.kind === 'integer') {
        // Coerce strings (form inputs) or numbers, bound to [min, max].
        const min = spec.min ?? 1
        const max = spec.max ?? 100
        const parsed =
          typeof value === 'number'
            ? value
            : typeof value === 'string' && value !== ''
              ? Number.parseInt(value, 10)
              : NaN
        if (Number.isFinite(parsed)) {
          args[spec.key] = Math.min(Math.max(Math.trunc(parsed), min), max)
        }
      } else if (spec.kind === 'boolean' && typeof value === 'boolean') {
        args[spec.key] = value
      }
    }
    return args
  }

  function setCanonicalName(value: string): void {
    if (!SELECTABLE_TOOL_IDS.includes(value)) {
      return
    }
    if (value === canonicalName.value) {
      return
    }
    canonicalName.value = value
    // Reset per-tool argument state when switching tools.
    argumentValues.value = {}
    question.value = ''
    choicesText.value = ''
  }

  /** Set one argument value for the current read-only tool. */
  function setArgumentValue(key: string, value: unknown): void {
    argumentValues.value = { ...argumentValues.value, [key]: value }
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

      // Phase 2A: the authoritative "completed" signal is the executionCompleted
      // boolean (set True by the backend _build_success_result for every tool).
      // Clarify returns decision 'clarify_execution_completed'; each read-only
      // tool returns '<toolId>_execution_completed' — both are recognized here.
      if (response.data.executionCompleted === true) {
        status.value = 'completed'
        // The one-time confirmation token has been consumed.
        _confirmationToken = null
      } else {
        // Any non-completed result is a controlled block.
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
    argumentValues,
    dryRunResult,
    executeResult,
    dryRunRequestId,
    dryRunDecisionDigest,
    confirmationTokenId,
    confirmationTokenExpiresAt,
    // derived
    selectedToolMeta,
    isDryRunLoading,
    isExecuteLoading,
    isBlocked,
    isCompleted,
    executeDecision,
    isHandlerCallBlocked,
    sideEffects,
    // actions
    setCanonicalName,
    setArgumentValue,
    setQuestion,
    setChoicesText,
    runDryRun,
    runExecute,
    reset,
    abortAllRequests,
  }
})
