/**
 * Capability Registry API client for the Dev WebUI (Phase 3C).
 *
 * Reads the frozen registry summary from GET /api/dev/v1/status data
 * .capabilityRegistry. **No new HTTP route is introduced.** Value-free only:
 * the response never carries an API key, Authorization header, Bearer token,
 * raw secret, callable repr, shell command, SQL statement, production path,
 * local plugin path, dynamic import path, or external URL.
 */

import { apiGet } from './client'

import type { CapabilityRegistrySummary } from '@/types/api/capabilityRegistry'

const API_PREFIX = '/api/dev/v1'

/**
 * Phase 3C: fetch the static Capability Registry summary block.
 *
 * Reads GET /status data.capabilityRegistry. The capability list / detail is
 * a deterministic static mirror (constants/capabilityRegistryManifest); only
 * the authoritative validation status + counts come from the live /status.
 */
export async function fetchCapabilityRegistryStatus(
  signal?: AbortSignal,
): Promise<CapabilityRegistrySummary | null> {
  try {
    const resp = await apiGet<{ capabilityRegistry: CapabilityRegistrySummary }>(
      `${API_PREFIX}/status`,
      undefined,
      signal,
    )
    return resp.data.capabilityRegistry ?? null
  } catch {
    // Read-only: a failure degrades to null (the static mirror still renders).
    return null
  }
}
