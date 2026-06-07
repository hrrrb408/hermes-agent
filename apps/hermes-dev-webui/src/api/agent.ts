/**
 * Agent status API function for the Dev WebUI.
 *
 * Provides a typed wrapper for the agent status endpoint:
 * - GET /api/dev/v1/agent/status
 */

import { apiGet } from './client'
import type { AgentStatusData } from '@/types/api/agent'

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
