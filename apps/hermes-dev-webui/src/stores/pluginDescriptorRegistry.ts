/**
 * Plugin Descriptor Registry store — Phase 3D static dev-only registry state.
 *
 * Combines:
 *   - the live GET /status data.pluginDescriptorRegistry summary (authoritative
 *     validation status + counts), and
 *   - the deterministic static manifest mirror (the read-only descriptor list
 *     + detail — no new HTTP route is introduced).
 *
 * The registry describes future plugin descriptors only — it never grants
 * permission, never loads a plugin, never executes a plugin. The UI is
 * read-only: no enable/disable/install/execute controls. No plugin runtime, no
 * plugin loader, no dynamic loading, no local plugin directory loading, no
 * remote registry / marketplace / external plugin fetch. No API key,
 * Authorization, Bearer, secret, callable repr, shell command, SQL statement,
 * production path, local plugin path, dynamic import path, external URL,
 * download URL, or install command is ever surfaced.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { fetchPluginDescriptorRegistryStatus } from '@/api/pluginDescriptorRegistry'
import { PLUGIN_DESCRIPTOR_MANIFEST } from '@/constants/pluginDescriptorRegistryManifest'

import type {
  PluginDescriptorDetail,
  PluginDescriptorRegistrySummary,
  PluginPermissionClass,
  PluginSource,
  PluginStatus,
  PluginTrustLevel,
} from '@/types/api/pluginDescriptorRegistry'

export type PluginDescriptorLoadState = 'idle' | 'loading' | 'loaded' | 'error'

/** Frozen policy flags mirrored from the backend (the /status block confirms). */
export const PLUGIN_FROZEN_FLAGS = {
  devOnly: true,
  productionAllowed: false,
  pluginRuntimeImplemented: false,
  pluginLoaderImplemented: false,
  dynamicLoadingAllowed: false,
  localPluginDirectoryLoadingAllowed: false,
  remoteRegistryAllowed: false,
  marketplaceAllowed: false,
  externalPluginFetchAllowed: false,
  providerGeneratedPluginAllowed: false,
  llmGeneratedPluginInstallAllowed: false,
  pluginExecutionAllowed: false,
  newRouteIntroduced: false,
} as const

export const usePluginDescriptorRegistryStore = defineStore('plugin-descriptor-registry', () => {
  const summary = ref<PluginDescriptorRegistrySummary | null>(null)
  const loadState = ref<PluginDescriptorLoadState>('idle')
  const error = ref('')
  const selectedPluginId = ref<string | null>(null)

  /** Filter state (read-only view filters; never mutates the registry). */
  const filterTrust = ref<PluginTrustLevel | 'all'>('all')
  const filterPermission = ref<PluginPermissionClass | 'all'>('all')
  const filterStatus = ref<PluginStatus | 'all'>('all')
  const filterSource = ref<PluginSource | 'all'>('all')

  const descriptors = computed<readonly PluginDescriptorDetail[]>(() => PLUGIN_DESCRIPTOR_MANIFEST)

  const filteredDescriptors = computed<readonly PluginDescriptorDetail[]>(() => {
    return PLUGIN_DESCRIPTOR_MANIFEST.filter((d) => {
      if (filterTrust.value !== 'all' && d.trustLevel !== filterTrust.value) return false
      if (filterPermission.value !== 'all' && d.permissionClass !== filterPermission.value) return false
      if (filterStatus.value !== 'all' && d.status !== filterStatus.value) return false
      if (filterSource.value !== 'all' && d.source !== filterSource.value) return false
      return true
    })
  })

  const selectedDescriptor = computed<PluginDescriptorDetail | null>(() => {
    if (!selectedPluginId.value) return null
    return PLUGIN_DESCRIPTOR_MANIFEST.find((d) => d.pluginId === selectedPluginId.value) ?? null
  })

  const liveSummary = computed<PluginDescriptorRegistrySummary | null>(() => summary.value)

  async function loadSummary(signal?: AbortSignal): Promise<void> {
    loadState.value = 'loading'
    error.value = ''
    try {
      summary.value = await fetchPluginDescriptorRegistryStatus(signal)
      loadState.value = 'loaded'
    } catch (err) {
      loadState.value = 'error'
      error.value = err instanceof Error ? err.message : 'Failed to load plugin descriptor registry status.'
    }
  }

  function selectPlugin(pluginId: string | null): void {
    selectedPluginId.value = pluginId
  }

  function resetFilters(): void {
    filterTrust.value = 'all'
    filterPermission.value = 'all'
    filterStatus.value = 'all'
    filterSource.value = 'all'
  }

  return {
    summary,
    liveSummary,
    loadState,
    error,
    descriptors,
    filteredDescriptors,
    selectedPluginId,
    selectedDescriptor,
    filterTrust,
    filterPermission,
    filterStatus,
    filterSource,
    loadSummary,
    selectPlugin,
    resetFilters,
  }
})
