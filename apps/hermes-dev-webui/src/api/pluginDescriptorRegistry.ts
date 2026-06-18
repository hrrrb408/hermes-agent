/**
 * Plugin Descriptor Registry API client for the Dev WebUI (Phase 3D).
 *
 * Reads the frozen descriptor-registry summary from GET /api/dev/v1/status data
 * .pluginDescriptorRegistry. **No new HTTP route is introduced.** Value-free
 * only: the response never carries an API key, Authorization header, Bearer
 * token, raw secret, callable repr, shell command, SQL statement, production
 * path, local plugin path, dynamic import path, external URL, download URL, or
 * install command.
 */

import { apiGet } from './client'

import type { PluginDescriptorRegistrySummary } from '@/types/api/pluginDescriptorRegistry'

const API_PREFIX = '/api/dev/v1'

/**
 * Phase 3D: fetch the static Plugin Descriptor Registry summary block.
 *
 * Reads GET /status data.pluginDescriptorRegistry. The descriptor list / detail
 * is a deterministic static mirror (constants/pluginDescriptorRegistryManifest);
 * only the authoritative validation status + counts come from the live /status.
 */
export async function fetchPluginDescriptorRegistryStatus(
  signal?: AbortSignal,
): Promise<PluginDescriptorRegistrySummary | null> {
  try {
    const resp = await apiGet<{ pluginDescriptorRegistry: PluginDescriptorRegistrySummary }>(
      `${API_PREFIX}/status`,
      undefined,
      signal,
    )
    return resp.data.pluginDescriptorRegistry ?? null
  } catch {
    // Read-only: a failure degrades to null (the static mirror still renders).
    return null
  }
}
