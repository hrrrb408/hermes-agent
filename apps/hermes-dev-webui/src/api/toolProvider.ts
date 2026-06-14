/**
 * Provider Schema / API round-trip API client for the Dev WebUI (Phase 2B).
 *
 * Reuses the existing POST /api/dev/v1/tools/execute route with
 * body.mode='provider_roundtrip' — no new route is added.
 *
 * Safety:
 *   - The provider mode is fake by default; real mode is blocked by the
 *     backend unless explicitly enabled.
 *   - This client never sends an API key. The backend only reads provider
 *     keys from the environment.
 *   - No raw arguments, tokens, or secrets are persisted here.
 */

import { apiPost } from './client'

import type {
  ProviderRoundtripRequest,
  ProviderRoundtripResultData,
} from '@/types/api/toolProvider'

const API_PREFIX = '/api/dev/v1'

/**
 * Run the controlled Provider round-trip.
 *
 * Fake mode is deterministic and offline. Real mode is blocked by the backend
 * unless fully enabled (env key + dev home + production gate). The UI may not
 * supply an API key.
 */
export async function runProviderRoundtrip(
  request: ProviderRoundtripRequest,
  signal?: AbortSignal,
) {
  return apiPost<ProviderRoundtripResultData>(
    `${API_PREFIX}/tools/execute`,
    request,
    undefined,
    signal,
  )
}
