/**
 * Agent API functions for the Dev WebUI.
 *
 * Provides typed wrappers for:
 * - GET  /api/dev/v1/agent/status
 * - POST /api/dev/v1/agent/prompt/preview
 * - POST /api/dev/v1/agent/run/dry-run
 */

import { apiGet, apiPost } from './client'
import type {
  AgentStatusData,
  AgentPreviewResult,
  AgentPromptPreviewRequest,
  AgentRunDryRunRequest,
} from '@/types/api/agent'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Fetch agent configuration status.
 *
 * Returns safe status information only — no secrets, no API keys.
 */
export async function fetchAgentStatus(signal?: AbortSignal) {
  return apiGet<AgentStatusData>(`${API_PREFIX}/agent/status`, undefined, signal)
}

/**
 * Preview agent prompt assembly (dry-run, no side effects).
 *
 * Returns prompt metadata, section breakdowns, and safety flags.
 * No LLM call is made.
 */
export async function previewAgentPrompt(
  payload: AgentPromptPreviewRequest,
  signal?: AbortSignal,
) {
  return apiPost<AgentPreviewResult>(
    `${API_PREFIX}/agent/prompt/preview`,
    payload,
    undefined,
    signal,
  )
}

/**
 * Preview agent run capabilities (dry-run, no side effects).
 *
 * Returns capability plan with all execution capabilities forced disabled.
 * No LLM call, no tool execution, no session/memory writes.
 */
export async function dryRunAgent(
  payload: AgentRunDryRunRequest,
  signal?: AbortSignal,
) {
  return apiPost<AgentPreviewResult>(
    `${API_PREFIX}/agent/run/dry-run`,
    payload,
    undefined,
    signal,
  )
}
