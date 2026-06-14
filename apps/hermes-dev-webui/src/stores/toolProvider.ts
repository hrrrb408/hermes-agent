/**
 * Provider round-trip store — Phase 2B controlled Provider workbench state.
 *
 * Manages the provider mode selector (disabled / fake / real), the user
 * message, the allowed-tools selection, and the round-trip result. Real mode
 * is presented in the UI but is always blocked by the backend unless
 * explicitly enabled; the UI never accepts an API key.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { runProviderRoundtrip as runProviderRoundtripApi } from '@/api/toolProvider'
import { isDevApiError } from '@/api/client'
import { SELECTABLE_TOOL_IDS } from '@/constants/readOnlyTools'

import type {
  ProviderMode,
  ProviderRoundtripResultData,
} from '@/types/api/toolProvider'

export type ProviderRoundtripStatus = 'idle' | 'loading' | 'completed' | 'blocked' | 'error'

/** Real mode is surfaced in the UI but blocked by the backend by default. */
export const PROVIDER_MODES: readonly ProviderMode[] = ['disabled', 'fake', 'real']

function _handleError(err: unknown): string {
  if (isDevApiError(err)) {
    return err.message
  }
  return 'An unexpected error occurred.'
}

export const useToolProviderStore = defineStore('tool-provider', () => {
  const providerMode = ref<ProviderMode>('disabled')
  const message = ref('')
  const selectedToolIds = ref<string[]>([...SELECTABLE_TOOL_IDS])
  const status = ref<ProviderRoundtripStatus>('idle')
  const error = ref('')
  const result = ref<ProviderRoundtripResultData | null>(null)

  const canRun = computed(
    () => providerMode.value === 'fake' && message.value.trim().length > 0 && status.value !== 'loading',
  )

  const isRealBlocked = computed(
    () => providerMode.value === 'real',
  )

  function setProviderMode(mode: ProviderMode): void {
    providerMode.value = mode
  }

  function setMessage(value: string): void {
    message.value = value.slice(0, 4000)
  }

  function toggleTool(id: string): void {
    const idx = selectedToolIds.value.indexOf(id)
    if (idx >= 0) {
      selectedToolIds.value = selectedToolIds.value.filter((t) => t !== id)
    } else {
      selectedToolIds.value = [...selectedToolIds.value, id]
    }
  }

  function selectAllTools(): void {
    selectedToolIds.value = [...SELECTABLE_TOOL_IDS]
  }

  function clearAllTools(): void {
    selectedToolIds.value = []
  }

  function reset(): void {
    status.value = 'idle'
    error.value = ''
    result.value = null
  }

  async function runRoundtrip(signal?: AbortSignal): Promise<void> {
    if (providerMode.value !== 'fake') {
      // Real / disabled modes are surfaced but the backend blocks real mode;
      // disabled does nothing. We still send the request so the backend can
      // record the blocked reason, mirroring the API contract.
    }
    status.value = 'loading'
    error.value = ''
    result.value = null
    try {
      const response = await runProviderRoundtripApi(
        {
          mode: 'provider_roundtrip',
          providerMode: providerMode.value,
          message: message.value,
          allowedToolIds: selectedToolIds.value,
        },
        signal,
      )
      result.value = response.data
      status.value = response.data.status === 'completed' ? 'completed' : 'blocked'
    } catch (err) {
      error.value = _handleError(err)
      status.value = 'error'
    }
  }

  return {
    providerMode,
    message,
    selectedToolIds,
    status,
    error,
    result,
    canRun,
    isRealBlocked,
    setProviderMode,
    setMessage,
    toggleTool,
    selectAllTools,
    clearAllTools,
    reset,
    runRoundtrip,
  }
})
