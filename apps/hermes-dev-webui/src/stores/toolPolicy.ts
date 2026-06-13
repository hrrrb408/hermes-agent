/**
 * Tool Policy store for the Dev WebUI.
 *
 * Manages loading, filtering, pagination, and selection state for
 * the Tool Policy read-only data layer.
 *
 * Safety invariants:
 *   - enabledAllowlistCount must be 0
 *   - execution.enabled must be false
 *   - execution.providerSchemaSent must be false
 *   - execution.dispatchAvailable must be false
 *   - safety.readOnly must be true
 *   - safety.sideEffects must be false
 *   - safety.executeAvailable must be false
 *   - All catalog items must have allowed=false
 *   - All catalog items must have executionAvailable=false
 *
 * Any violation → store enters safety error state with
 * code TOOL_POLICY_SAFETY_INVARIANT_FAILED.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { fetchToolPolicyStatus, fetchToolCatalog } from '@/api/toolPolicy'
import { isDevApiError } from '@/api/client'

import type {
  ToolPolicyStatusResponse,
  ToolCatalogResponse,
  ToolCatalogFilters,
  ToolCatalogItem,
  ToolRiskLevel,
  ToolCapability,
  ToolPolicyStatus,
  ToolCatalogSort,
} from '@/types/api/toolPolicy'
import type { LoadingState } from '@/stores/workspacePanel'

/** Default catalog filter values. */
const DEFAULT_FILTERS: Readonly<ToolCatalogFilters> = {
  q: '',
  risk: undefined,
  capability: undefined,
  policyStatus: undefined,
  page: 1,
  pageSize: 25,
  sort: 'nameAsc',
}

export type ToolPolicySubTab =
  | 'overview'
  | 'catalog'
  | 'schema-preview'
  | 'execute'
  | 'audit'

export const useToolPolicyStore = defineStore('workspace-tool-policy', () => {
  // ── State ──

  const activeSubTab = ref<ToolPolicySubTab>('overview')

  const policyState = ref<LoadingState>('idle')
  const catalogState = ref<LoadingState>('idle')

  const policy = ref<ToolPolicyStatusResponse | null>(null)
  const catalog = ref<ToolCatalogResponse | null>(null)

  const selectedToolName = ref<string | null>(null)

  const filters = ref<ToolCatalogFilters>({ ...DEFAULT_FILTERS })

  const policyError = ref('')
  const catalogError = ref('')

  // ── Abort / Race protection ──

  let policyAbortController: AbortController | null = null
  let catalogAbortController: AbortController | null = null

  let policyRequestSequence = 0
  let catalogRequestSequence = 0

  // ── Computed / Getters ──

  const isPolicyLoading = computed(() => policyState.value === 'loading')
  const isCatalogLoading = computed(() => catalogState.value === 'loading')

  const hasPolicy = computed(() => policy.value !== null)
  const hasCatalog = computed(() => catalog.value !== null)

  const catalogItems = computed(
    () => catalog.value?.items ?? [],
  )

  const selectedTool = computed<ToolCatalogItem | null>(() => {
    const name = selectedToolName.value
    if (name === null) return null
    return catalogItems.value.find(item => item.canonicalName === name) ?? null
  })

  const hasCatalogResults = computed(
    () => (catalog.value?.total ?? 0) > 0,
  )

  const isCatalogEmpty = computed(
    () =>
      (catalogState.value === 'success' || catalogState.value === 'empty') &&
      (catalog.value?.total ?? 0) === 0,
  )

  /** Read-only mode — always true from backend safety flags. */
  const isReadOnly = computed(
    () => policy.value?.safety.readOnly ?? true,
  )

  /** Execution available — always false from backend. */
  const isExecutionAvailable = computed(
    () => policy.value?.execution.enabled ?? false,
  )

  // ── Safety invariant checks ──

  function checkPolicySafetyInvariants(data: ToolPolicyStatusResponse): string | null {
    if (data.enabledAllowlistCount !== 0) {
      return `enabledAllowlistCount=${data.enabledAllowlistCount}, expected 0`
    }
    if (data.execution.enabled) {
      return 'execution.enabled=true, expected false'
    }
    if (data.execution.providerSchemaSent) {
      return 'execution.providerSchemaSent=true, expected false'
    }
    if (data.execution.dispatchAvailable) {
      return 'execution.dispatchAvailable=true, expected false'
    }
    if (!data.safety.readOnly) {
      return 'safety.readOnly=false, expected true'
    }
    if (data.safety.sideEffects) {
      return 'safety.sideEffects=true, expected false'
    }
    if (data.safety.executeAvailable) {
      return 'safety.executeAvailable=true, expected false'
    }
    return null
  }

  function checkCatalogItemSafety(item: ToolCatalogItem): string | null {
    if (item.allowed) {
      return `catalog item "${item.canonicalName}" allowed=true, expected false`
    }
    if (item.executionAvailable) {
      return `catalog item "${item.canonicalName}" executionAvailable=true, expected false`
    }
    if (item.schemaPreviewAvailable) {
      return `catalog item "${item.canonicalName}" schemaPreviewAvailable=true, expected false`
    }
    if (item.dryRunAvailable) {
      return `catalog item "${item.canonicalName}" dryRunAvailable=true, expected false`
    }
    return null
  }

  function checkCatalogSafety(data: ToolCatalogResponse): string | null {
    if (!data.safety.readOnly) {
      return 'catalog safety.readOnly=false, expected true'
    }
    if (data.safety.sideEffects) {
      return 'catalog safety.sideEffects=true, expected false'
    }
    if (data.safety.executeAvailable) {
      return 'catalog safety.executeAvailable=true, expected false'
    }
    for (const item of data.items) {
      const violation = checkCatalogItemSafety(item)
      if (violation) return violation
    }
    return null
  }

  // ── Helpers ──

  function handleError(err: unknown): string {
    if (isDevApiError(err)) {
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  // ── Actions ──

  async function loadPolicy(): Promise<void> {
    policyAbortController?.abort()
    policyAbortController = new AbortController()

    const sequence = ++policyRequestSequence
    policyState.value = 'loading'
    policyError.value = ''

    try {
      const response = await fetchToolPolicyStatus(
        policyAbortController.signal,
      )
      const data = response.data

      // Stale response check
      if (sequence !== policyRequestSequence) return

      // Safety invariant check
      const violation = checkPolicySafetyInvariants(data)
      if (violation) {
        policyState.value = 'error'
        policyError.value = `Safety invariant violated: ${violation}`
        return
      }

      policy.value = data
      policyState.value = 'success'
    } catch (err: unknown) {
      if (sequence !== policyRequestSequence) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      policyError.value = handleError(err)
      policyState.value = 'error'
    }
  }

  async function loadCatalog(): Promise<void> {
    catalogAbortController?.abort()
    catalogAbortController = new AbortController()

    const sequence = ++catalogRequestSequence
    catalogState.value = 'loading'
    catalogError.value = ''

    try {
      const response = await fetchToolCatalog(
        filters.value,
        catalogAbortController.signal,
      )
      const data = response.data

      // Stale response check
      if (sequence !== catalogRequestSequence) return

      // Safety invariant check
      const violation = checkCatalogSafety(data)
      if (violation) {
        catalogState.value = 'error'
        catalogError.value = `Safety invariant violated: ${violation}`
        return
      }

      catalog.value = data
      catalogState.value = data.items.length > 0 ? 'success' : 'empty'

      // Clear selection if selected tool no longer in results
      if (selectedToolName.value !== null) {
        const stillPresent = data.items.some(
          item => item.canonicalName === selectedToolName.value,
        )
        if (!stillPresent) {
          selectedToolName.value = null
        }
      }
    } catch (err: unknown) {
      if (sequence !== catalogRequestSequence) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      catalogError.value = handleError(err)
      catalogState.value = 'error'
    }
  }

  // ── Filter actions ──

  function setQuery(value: string): void {
    filters.value = { ...filters.value, q: value, page: 1 }
  }

  function setRisk(value: ToolRiskLevel | undefined): void {
    filters.value = { ...filters.value, risk: value, page: 1 }
  }

  function setCapability(value: ToolCapability | undefined): void {
    filters.value = { ...filters.value, capability: value, page: 1 }
  }

  function setPolicyStatus(value: ToolPolicyStatus | undefined): void {
    filters.value = { ...filters.value, policyStatus: value, page: 1 }
  }

  function setPage(value: number): void {
    const normalized = Math.max(1, Math.floor(value))
    filters.value = { ...filters.value, page: normalized }
  }

  function setPageSize(value: number): void {
    const clamped = Math.min(100, Math.max(1, Math.floor(value)))
    filters.value = { ...filters.value, pageSize: clamped, page: 1 }
  }

  function setSort(value: ToolCatalogSort): void {
    filters.value = { ...filters.value, sort: value, page: 1 }
  }

  // ── Selection actions ──

  function selectTool(canonicalName: string): void {
    selectedToolName.value = canonicalName
  }

  function clearSelection(): void {
    selectedToolName.value = null
  }

  // ── Retry actions ──

  function retryPolicy(): void {
    loadPolicy()
  }

  function retryCatalog(): void {
    loadCatalog()
  }

  // ── Abort / Cleanup ──

  function abortPolicyRequest(): void {
    policyAbortController?.abort()
    policyAbortController = null
  }

  function abortCatalogRequest(): void {
    catalogAbortController?.abort()
    catalogAbortController = null
  }

  function abortAllRequests(): void {
    abortPolicyRequest()
    abortCatalogRequest()
  }

  // ── Reset ──

  function reset(): void {
    abortAllRequests()
    activeSubTab.value = 'overview'
    policyState.value = 'idle'
    catalogState.value = 'idle'
    policy.value = null
    catalog.value = null
    selectedToolName.value = null
    filters.value = { ...DEFAULT_FILTERS }
    policyError.value = ''
    catalogError.value = ''
    policyRequestSequence = 0
    catalogRequestSequence = 0
  }

  return {
    // State
    activeSubTab,
    policyState,
    catalogState,
    policy,
    catalog,
    selectedToolName,
    filters,
    policyError,
    catalogError,
    // Computed / Getters
    isPolicyLoading,
    isCatalogLoading,
    hasPolicy,
    hasCatalog,
    catalogItems,
    selectedTool,
    hasCatalogResults,
    isCatalogEmpty,
    isReadOnly,
    isExecutionAvailable,
    // Actions
    loadPolicy,
    loadCatalog,
    setQuery,
    setRisk,
    setCapability,
    setPolicyStatus,
    setPage,
    setPageSize,
    setSort,
    selectTool,
    clearSelection,
    retryPolicy,
    retryCatalog,
    abortPolicyRequest,
    abortCatalogRequest,
    abortAllRequests,
    reset,
  }
})
