import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useToolAuditStore } from '@/stores/toolAudit'

/**
 * Dev Console navigation store (Phase 2E).
 *
 * Owns the active console section (persisted to localStorage, mirroring the
 * `useUiStore` pattern) and the result→audit cross-navigation bridge. The
 * bridge (`prefillAuditSearch`) is the keystone of the "回链" requirement:
 * clicking an audit/correlation id in any result block jumps to the Audit
 * Viewer pre-filtered to that id.
 *
 * `prefillAuditSearch` MUST perform the load (not just set the filter) — the
 * AuditViewerPanel only queries from onMounted / Apply / pagination, so setting
 * a filter alone would show a stale or empty list.
 */

/** First-class dev console sections (left nav rail order). */
export type DevConsoleSection =
  | 'overview'
  | 'tools'
  | 'provider'
  | 'write'
  | 'audit'
  | 'safety'
  | 'diagnostics'
  | 'workflow'
  | 'capabilities'

export const CONSOLE_SECTIONS: readonly DevConsoleSection[] = [
  'overview',
  'tools',
  'provider',
  'write',
  'audit',
  'safety',
  'workflow',
  'capabilities',
  'diagnostics',
]

/** Human-readable labels for the nav rail. */
export const CONSOLE_SECTION_LABELS: Readonly<Record<DevConsoleSection, string>> = {
  overview: 'Overview',
  tools: 'Tool Execution',
  provider: 'Provider Round-trip',
  write: 'Sandbox Write & Rollback',
  audit: 'Audit Viewer',
  safety: 'Safety Boundary',
  diagnostics: 'Diagnostics',
  workflow: 'Workflow',
  capabilities: 'Capability Registry',
} as const

const STORAGE_KEY = 'hermes-dev-webui.devconsole.section'
const DEFAULT_SECTION: DevConsoleSection = 'overview'

function isSection(value: string | null): value is DevConsoleSection {
  return value !== null && (CONSOLE_SECTIONS as readonly string[]).includes(value)
}

function readStoredSection(): DevConsoleSection {
  if (typeof window === 'undefined') return DEFAULT_SECTION
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return isSection(value) ? value : DEFAULT_SECTION
  } catch {
    return DEFAULT_SECTION
  }
}

export const useDevConsoleNavStore = defineStore('dev-console-nav', () => {
  const activeSection = ref<DevConsoleSection>(DEFAULT_SECTION)
  /** Transient prefill value (not persisted); informational — the toolAudit store is the source of truth. */
  const pendingAuditPrefill = ref<string | null>(null)
  let initialized = false

  function persist(section: DevConsoleSection): void {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem(STORAGE_KEY, section)
    } catch {
      // UI persistence is optional when storage is unavailable.
    }
  }

  function setSection(section: DevConsoleSection): void {
    activeSection.value = section
    persist(section)
  }

  function initializeNavState(): void {
    if (initialized) return
    initialized = true
    activeSection.value = readStoredSection()
  }

  function resetNavState(): void {
    activeSection.value = DEFAULT_SECTION
    pendingAuditPrefill.value = null
    persist(DEFAULT_SECTION)
  }

  /**
   * Jump to the Audit Viewer pre-filtered to `value`. Performs the query:
   * switches to store mode, sets the search filter, and fires loadStoreEvents.
   * Safe to call from any section (e.g. an AuditIdLink click in the Write result).
   */
  async function prefillAuditSearch(value: string): Promise<void> {
    if (!value) return
    const audit = useToolAuditStore()
    activeSection.value = 'audit'
    pendingAuditPrefill.value = value
    audit.setStoreMode(true)
    audit.setSearchInput(value)
    await audit.loadStoreEvents()
  }

  /** Clear the transient prefill marker (after the Audit section has consumed it). */
  function clearPendingPrefill(): void {
    pendingAuditPrefill.value = null
  }

  return {
    activeSection,
    pendingAuditPrefill,
    setSection,
    initializeNavState,
    resetNavState,
    prefillAuditSearch,
    clearPendingPrefill,
  }
})
