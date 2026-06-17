/**
 * Capability Registry store — Phase 3C static dev-only registry state.
 *
 * Combines:
 *   - the live GET /status data.capabilityRegistry summary (authoritative
 *     validation status + counts), and
 *   - the deterministic static manifest mirror (the read-only capability list
 *     + detail — no new HTTP route is introduced).
 *
 * The registry describes capabilities only; it never grants permission. The UI
 * is read-only: no enable/disable/promote/delete controls. No API key,
 * Authorization, Bearer, secret, callable repr, shell command, SQL statement,
 * production path, local plugin path, dynamic import path, or external URL is
 * ever surfaced.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { fetchCapabilityRegistryStatus } from '@/api/capabilityRegistry'
import { CAPABILITY_REGISTRY_MANIFEST } from '@/constants/capabilityRegistryManifest'

import type {
  CapabilityCategory,
  CapabilityDetail,
  CapabilityPermissionClass,
  CapabilityRegistrySummary,
  CapabilityStatus,
  CapabilityTrustLevel,
} from '@/types/api/capabilityRegistry'

export type CapabilityLoadState = 'idle' | 'loading' | 'loaded' | 'error'

/** Frozen policy flags mirrored from the backend (the /status block confirms). */
export const CAPABILITY_FROZEN_FLAGS = {
  devOnly: true,
  productionAllowed: false,
  dynamicLoadingAllowed: false,
  remoteRegistryAllowed: false,
  marketplaceAllowed: false,
} as const

export const useCapabilityRegistryStore = defineStore('capability-registry', () => {
  const summary = ref<CapabilityRegistrySummary | null>(null)
  const loadState = ref<CapabilityLoadState>('idle')
  const error = ref('')
  const selectedCapabilityId = ref<string | null>(null)

  /** Filter state (read-only view filters; never mutates the registry). */
  const filterCategory = ref<CapabilityCategory | 'all'>('all')
  const filterPermission = ref<CapabilityPermissionClass | 'all'>('all')
  const filterTrust = ref<CapabilityTrustLevel | 'all'>('all')
  const filterStatus = ref<CapabilityStatus | 'all'>('all')

  const capabilities = computed<readonly CapabilityDetail[]>(() => CAPABILITY_REGISTRY_MANIFEST)

  const filteredCapabilities = computed<readonly CapabilityDetail[]>(() => {
    return CAPABILITY_REGISTRY_MANIFEST.filter((c) => {
      if (filterCategory.value !== 'all' && c.category !== filterCategory.value) return false
      if (filterPermission.value !== 'all' && c.permissionClass !== filterPermission.value) return false
      if (filterTrust.value !== 'all' && c.trustLevel !== filterTrust.value) return false
      if (filterStatus.value !== 'all' && c.status !== filterStatus.value) return false
      return true
    })
  })

  const selectedCapability = computed<CapabilityDetail | null>(() => {
    if (!selectedCapabilityId.value) return null
    return CAPABILITY_REGISTRY_MANIFEST.find((c) => c.capabilityId === selectedCapabilityId.value) ?? null
  })

  const liveSummary = computed<CapabilityRegistrySummary | null>(() => summary.value)

  async function loadSummary(signal?: AbortSignal): Promise<void> {
    loadState.value = 'loading'
    error.value = ''
    try {
      summary.value = await fetchCapabilityRegistryStatus(signal)
      loadState.value = 'loaded'
    } catch (err) {
      loadState.value = 'error'
      error.value = err instanceof Error ? err.message : 'Failed to load capability registry status.'
    }
  }

  function selectCapability(capabilityId: string | null): void {
    selectedCapabilityId.value = capabilityId
  }

  function resetFilters(): void {
    filterCategory.value = 'all'
    filterPermission.value = 'all'
    filterTrust.value = 'all'
    filterStatus.value = 'all'
  }

  return {
    summary,
    liveSummary,
    loadState,
    error,
    capabilities,
    filteredCapabilities,
    selectedCapabilityId,
    selectedCapability,
    filterCategory,
    filterPermission,
    filterTrust,
    filterStatus,
    loadSummary,
    selectCapability,
    resetFilters,
  }
})
