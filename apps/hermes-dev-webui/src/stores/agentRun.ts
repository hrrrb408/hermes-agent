/**
 * Agent Run store for the Dev WebUI.
 *
 * Manages state for Live Run tab: creation, SSE streaming,
 * cancellation, reconnection, and usage tracking.
 *
 * Phase 1F: Tools disabled, Auto Memory disabled, dev-only.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  createAgentRun,
  getAgentRunStatus,
  cancelAgentRun,
  connectAgentRunEvents,
} from '@/api/agentRun'
import { isDevApiError } from '@/api/client'

import type {
  AgentRunEvent,
  AgentRunUsage,
  SSEConnectionStatus,
} from '@/types/api/agentRun'
import { TERMINAL_RUN_STATUSES } from '@/types/api/agentRun'

export type RunCreationState = 'idle' | 'creating' | 'created' | 'error'

export const useAgentRunStore = defineStore('agent-run', () => {
  // ── Run State ──

  const runId = ref<string | null>(null)
  const status = ref<string | null>(null)
  const sessionId = ref('')
  const model = ref<{ name: string; provider: string } | null>(null)
  const streamUrl = ref<string | null>(null)
  const cancelUrl = ref<string | null>(null)

  // ── Creation State ──

  const creationState = ref<RunCreationState>('idle')
  const creationError = ref('')

  // ── Form State ──

  const form = ref({
    sessionId: '',
    message: '',
    confirmationText: '',
    dryRunPreviewed: false,
    acknowledgedCallLlm: false,
    acknowledgedWriteSession: false,
    modelOverride: '',
    temperature: null as number | null,
    maxOutputTokens: null as number | null,
  })

  // ── SSE / Streaming State ──

  const connectionStatus = ref<SSEConnectionStatus>('disconnected')
  const streamText = ref('')
  const events = ref<AgentRunEvent[]>([])
  const lastEventId = ref<string | null>(null)
  const usage = ref<AgentRunUsage | null>(null)
  const error = ref<string | null>(null)
  const streamError = ref<string | null>(null)

  // ── Cancel State ──

  const isCancelling = ref(false)

  // ── Safety State ──

  const killSwitchEnabled = ref(false)

  // ── Abort Control ──

  let abortController: AbortController | null = null

  // ── Computed ──

  const isCreating = computed(() => creationState.value === 'creating')
  const isRunning = computed(() =>
    status.value !== null && !TERMINAL_RUN_STATUSES.includes(status.value as typeof TERMINAL_RUN_STATUSES[number])
  )
  const isTerminal = computed(() =>
    status.value !== null && TERMINAL_RUN_STATUSES.includes(status.value as typeof TERMINAL_RUN_STATUSES[number])
  )
  const canCancel = computed(() =>
    isRunning.value && !isCancelling.value
  )
  const canCreate = computed(() =>
    creationState.value === 'idle' || creationState.value === 'error'
  )

  // ── Helpers ──

  function handleError(err: unknown): string {
    if (isDevApiError(err)) {
      if (err.code === 'REQUEST_CANCELLED') return ''
      return `${err.code}: ${err.message}`
    }
    if (err instanceof Error) return err.message
    return 'An unexpected error occurred.'
  }

  // ── Create Run ──

  async function createRun(): Promise<void> {
    // Validate form
    const f = form.value
    if (!f.sessionId.trim()) {
      creationError.value = 'Session ID is required.'
      creationState.value = 'error'
      return
    }
    if (!f.message.trim() || f.message.trim().length < 1) {
      creationError.value = 'Message is required (1-4000 characters).'
      creationState.value = 'error'
      return
    }
    if (f.confirmationText !== 'RUN') {
      creationError.value = 'Type RUN to confirm execution.'
      creationState.value = 'error'
      return
    }
    if (!f.dryRunPreviewed) {
      creationError.value = 'You must preview the run first (Dry Run).'
      creationState.value = 'error'
      return
    }
    if (!f.acknowledgedCallLlm || !f.acknowledgedWriteSession) {
      creationError.value = 'You must acknowledge all effects.'
      creationState.value = 'error'
      return
    }

    // Clean up previous run
    cleanup()

    abortController = new AbortController()
    creationState.value = 'creating'
    creationError.value = ''

    const payload = {
      sessionId: f.sessionId.trim(),
      message: f.message.trim(),
      confirmationText: 'RUN' as const,
      dryRunPreviewed: true as const,
      acknowledgedEffects: ['CALL_LLM', 'WRITE_SESSION'] as const,
      options: {
        stream: true as const,
        tools: false as const,
        autoMemory: false as const,
      },
      overrides: {
        model: f.modelOverride.trim() || null,
        temperature: f.temperature,
        maxOutputTokens: f.maxOutputTokens,
      },
    }

    try {
      const response = await createAgentRun(payload, abortController.signal)
      const data = response.data

      runId.value = data.runId
      sessionId.value = data.sessionId
      status.value = data.status
      model.value = data.model
      streamUrl.value = data.streamUrl
      cancelUrl.value = data.cancelUrl
      killSwitchEnabled.value = data.safety.killSwitchEnabled

      creationState.value = 'created'

      // Auto-connect to SSE
      connectSSE()
    } catch (err: unknown) {
      const msg = handleError(err)
      if (!msg) return // cancelled
      creationError.value = msg
      creationState.value = 'error'
      // Check if kill switch disabled
      if (msg.includes('AGENT_RUN_DISABLED')) {
        killSwitchEnabled.value = false
      }
    }
  }

  // ── SSE Connection ──

  function connectSSE(): void {
    if (!runId.value) return

    connectionStatus.value = 'connecting'
    streamError.value = null

    const sseAbort = new AbortController()

    connectAgentRunEvents(
      runId.value,
      handleSSEEvent,
      handleSSEError,
      sseAbort.signal,
      lastEventId.value ?? undefined,
    )

    // Store abort controller for cleanup
    abortController = sseAbort
  }

  function handleSSEEvent(event: AgentRunEvent): void {
    // Guard against stale events from old runs
    if (runId.value && event.runId !== runId.value) return

    events.value.push(event)
    lastEventId.value = String(event.sequence)

    if (connectionStatus.value !== 'connected') {
      connectionStatus.value = 'connected'
    }

    switch (event.type) {
      case 'message.delta': {
        // Append incremental text
        const delta = event.data?.delta
        if (typeof delta === 'string') {
          streamText.value += delta
        }
        break
      }
        break

      case 'usage.updated':
      case 'message.completed':
        if (event.data?.usage) {
          usage.value = event.data.usage as AgentRunUsage
        }
        break

      case 'run.completed':
      case 'run.cancelled':
      case 'run.failed':
        // Terminal event
        status.value = event.type === 'run.completed'
          ? 'COMPLETED'
          : event.type === 'run.cancelled'
            ? 'CANCELLED'
            : 'FAILED'
        if (event.data?.usage) {
          usage.value = event.data.usage as AgentRunUsage
        }
        if (event.data?.errorCode) {
          error.value = String(event.data.errorCode)
        }
        connectionStatus.value = 'disconnected'
        break

      case 'run.cancelling':
        status.value = 'CANCELLING'
        break

      case 'run.started':
        status.value = 'RUNNING'
        break

      case 'run.created':
        status.value = 'CREATED'
        break

      case 'heartbeat':
        // No state change needed
        break
    }
  }

  function handleSSEError(err: Error): void {
    streamError.value = err.message
    connectionStatus.value = 'error'

    // If not terminal, attempt reconnect after delay
    if (!isTerminal.value && runId.value) {
      connectionStatus.value = 'reconnecting'
      // The SSE parser will stop; user can click reconnect
    }
  }

  // ── Reconnect ──

  function reconnect(): void {
    if (!runId.value) return
    connectSSE()
  }

  // ── Cancel ──

  async function cancelRun(): Promise<void> {
    if (!runId.value || isCancelling.value || isTerminal.value) return

    isCancelling.value = true
    const cancelAbort = new AbortController()

    try {
      await cancelAgentRun(runId.value, cancelAbort.signal)
      // Status will be updated via SSE events
    } catch (err: unknown) {
      const msg = handleError(err)
      if (msg) {
        error.value = msg
      }
    } finally {
      isCancelling.value = false
    }
  }

  // ── Check Existing Run ──

  async function checkRunStatus(targetRunId: string): Promise<void> {
    const checkAbort = new AbortController()
    try {
      const response = await getAgentRunStatus(targetRunId, checkAbort.signal)
      const data = response.data
      runId.value = data.runId
      sessionId.value = data.sessionId
      status.value = data.status
      model.value = data.model
      usage.value = data.usage
      if (data.error) {
        error.value = `${data.error.code}: ${data.error.message}`
      }
      killSwitchEnabled.value = data.safety?.killSwitchEnabled ?? false
      creationState.value = 'created'

      // If still running, connect to SSE
      if (!TERMINAL_RUN_STATUSES.includes(data.status as typeof TERMINAL_RUN_STATUSES[number])) {
        connectSSE()
      }
    } catch {
      // Run not found or other error — reset
      runId.value = null
      status.value = null
    }
  }

  // ── Cleanup ──

  function cleanup(): void {
    abortController?.abort()
    abortController = null

    runId.value = null
    status.value = null
    sessionId.value = ''
    model.value = null
    streamUrl.value = null
    cancelUrl.value = null
    streamText.value = ''
    events.value = []
    lastEventId.value = null
    usage.value = null
    error.value = null
    streamError.value = null
    connectionStatus.value = 'disconnected'
    isCancelling.value = false
  }

  function reset(): void {
    cleanup()
    creationState.value = 'idle'
    creationError.value = ''
    form.value.confirmationText = ''
    form.value.dryRunPreviewed = false
    form.value.acknowledgedCallLlm = false
    form.value.acknowledgedWriteSession = false
  }

  function fullReset(): void {
    reset()
    form.value = {
      sessionId: '',
      message: '',
      confirmationText: '',
      dryRunPreviewed: false,
      acknowledgedCallLlm: false,
      acknowledgedWriteSession: false,
      modelOverride: '',
      temperature: null,
      maxOutputTokens: null,
    }
  }

  return {
    // State
    runId,
    status,
    sessionId,
    model,
    streamUrl,
    cancelUrl,
    creationState,
    creationError,
    form,
    connectionStatus,
    streamText,
    events,
    lastEventId,
    usage,
    error,
    streamError,
    isCancelling,
    killSwitchEnabled,

    // Computed
    isCreating,
    isRunning,
    isTerminal,
    canCancel,
    canCreate,

    // Actions
    createRun,
    cancelRun,
    reconnect,
    checkRunStatus,
    cleanup,
    reset,
    fullReset,

    // Internal (exposed for testing)
    handleSSEEvent,
    handleSSEError,
  }
})
