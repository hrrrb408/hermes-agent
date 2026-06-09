/**
 * Agent Run API functions for the Dev WebUI.
 *
 * Provides typed wrappers for Phase 1F Agent Run endpoints:
 * - POST /api/dev/v1/agent/runs               Create Run
 * - GET  /api/dev/v1/agent/runs/{runId}        Run Status
 * - GET  /api/dev/v1/agent/runs/{runId}/events  SSE Stream
 * - POST /api/dev/v1/agent/runs/{runId}/cancel   Cancel Run
 */

import { apiGet, apiPost, getDefaultBaseUrl, isDevApiError } from './client'
import type {
  CreateRunRequest,
  CreateRunResponseData,
  RunStatusResponseData,
  CancelRunResponseData,
  AgentRunEvent,
} from '@/types/api/agentRun'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Create a new Agent Run.
 *
 * Returns 202 Accepted with run metadata, stream URL, and cancel URL.
 * The actual execution happens asynchronously — connect to the SSE
 * stream URL to receive events.
 */
export async function createAgentRun(
  payload: CreateRunRequest,
  signal?: AbortSignal,
) {
  return apiPost<CreateRunResponseData>(
    `${API_PREFIX}/agent/runs`,
    payload,
    { timeoutMs: 15_000 },
    signal,
  )
}

/**
 * Get Agent Run status.
 *
 * Returns whitelisted status fields. Full response content is available
 * via Session Message API after run completes.
 */
export async function getAgentRunStatus(runId: string, signal?: AbortSignal) {
  return apiGet<RunStatusResponseData>(
    `${API_PREFIX}/agent/runs/${encodeURIComponent(runId)}`,
    undefined,
    signal,
  )
}

/**
 * Cancel an Agent Run.
 *
 * Idempotent — returns alreadyTerminal=true if run has already finished.
 */
export async function cancelAgentRun(runId: string, signal?: AbortSignal) {
  return apiPost<CancelRunResponseData>(
    `${API_PREFIX}/agent/runs/${encodeURIComponent(runId)}/cancel`,
    {},
    undefined,
    signal,
  )
}

/**
 * Connect to an Agent Run SSE event stream using fetch + ReadableStream.
 *
 * Uses native fetch instead of EventSource to support:
 * - Custom headers (Last-Event-ID)
 * - AbortController
 * - Unified error handling
 *
 * @param runId - The run to stream events for.
 * @param onEvent - Callback for each parsed SSE event.
 * @param onError - Callback for connection/stream errors.
 * @param signal - AbortController signal for cancellation.
 * @param lastEventId - Optional Last-Event-ID for reconnection.
 */
export function connectAgentRunEvents(
  runId: string,
  onEvent: (event: AgentRunEvent) => void,
  onError: (error: Error) => void,
  signal: AbortSignal,
  lastEventId?: string,
): void {
  const baseUrl = getDefaultBaseUrl()
  const url = `${baseUrl}${API_PREFIX}/agent/runs/${encodeURIComponent(runId)}/events`

  const headers: Record<string, string> = {
    Accept: 'text/event-stream',
    'Cache-Control': 'no-cache',
  }
  if (lastEventId) {
    headers['Last-Event-ID'] = lastEventId
  }

  let currentData = ''

  fetch(url, { headers, signal })
    .then(async (response) => {
      if (!response.ok) {
        // Try to parse error body
        const text = await response.text()
        let code = 'SSE_CONNECTION_ERROR'
        let message = `SSE connection failed: HTTP ${response.status}`
        try {
          const parsed = JSON.parse(text)
          if (parsed?.error?.code) code = parsed.error.code
          if (parsed?.error?.message) message = parsed.error.message
        } catch {
          // Use default error message
        }
        onError(new Error(`${code}: ${message}`))
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError(new Error('No response body'))
        return
      }

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        // Process SSE lines — events separated by double newline
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            currentData = line.slice(6)
          } else if (line === '' && currentData) {
            // Empty line = event boundary
            try {
              const parsed = JSON.parse(currentData)
              onEvent(parsed as AgentRunEvent)
            } catch {
              // Skip malformed events
            }
            currentData = ''
          }
        }
      }
    })
    .catch((err: unknown) => {
      if (signal.aborted) return
      if (isDevApiError(err)) {
        onError(new Error(`${err.code}: ${err.message}`))
      } else if (err instanceof Error) {
        onError(err)
      } else {
        onError(new Error('SSE connection failed'))
      }
    })
}
