import { defineStore } from 'pinia'
import { ref } from 'vue'

export type WorkspaceTab = 'files' | 'memory' | 'context' | 'agent' | 'reviews' | 'tools' | 'provider'

export const UI_STORAGE_KEYS = {
  sidebarCollapsed: 'hermes-dev-webui.ui.sidebar-collapsed',
  workspaceCollapsed: 'hermes-dev-webui.ui.workspace-collapsed',
  workspaceTab: 'hermes-dev-webui.ui.workspace-tab',
} as const

const DEFAULT_WORKSPACE_TAB: WorkspaceTab = 'context'
const WORKSPACE_TABS: readonly WorkspaceTab[] = ['files', 'memory', 'context', 'reviews', 'agent', 'tools', 'provider']

function isWorkspaceTab(value: string | null): value is WorkspaceTab {
  return value !== null && WORKSPACE_TABS.includes(value as WorkspaceTab)
}

function readBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === 'undefined') return fallback
  try {
    const value = localStorage.getItem(key)
    if (value === 'true') return true
    if (value === 'false') return false
  } catch {
    return fallback
  }
  return fallback
}

function persist(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(key, value)
  } catch {
    // UI persistence is optional when storage is unavailable.
  }
}

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(false)
  const workspaceCollapsed = ref(false)
  const workspaceTab = ref<WorkspaceTab>(DEFAULT_WORKSPACE_TAB)
  let initialized = false

  function setSidebarCollapsed(value: boolean): void {
    sidebarCollapsed.value = value
    persist(UI_STORAGE_KEYS.sidebarCollapsed, String(value))
  }

  function toggleSidebar(): void {
    setSidebarCollapsed(!sidebarCollapsed.value)
  }

  function setWorkspaceCollapsed(value: boolean): void {
    workspaceCollapsed.value = value
    persist(UI_STORAGE_KEYS.workspaceCollapsed, String(value))
  }

  function toggleWorkspace(): void {
    setWorkspaceCollapsed(!workspaceCollapsed.value)
  }

  function setWorkspaceTab(tab: WorkspaceTab): void {
    workspaceTab.value = tab
    persist(UI_STORAGE_KEYS.workspaceTab, tab)
  }

  function initializeUiState(): void {
    if (initialized) return
    initialized = true

    sidebarCollapsed.value = readBoolean(UI_STORAGE_KEYS.sidebarCollapsed, false)
    workspaceCollapsed.value = readBoolean(UI_STORAGE_KEYS.workspaceCollapsed, false)

    try {
      const storedTab = localStorage.getItem(UI_STORAGE_KEYS.workspaceTab)
      workspaceTab.value = isWorkspaceTab(storedTab) ? storedTab : DEFAULT_WORKSPACE_TAB
    } catch {
      workspaceTab.value = DEFAULT_WORKSPACE_TAB
    }
  }

  function resetUiState(): void {
    sidebarCollapsed.value = false
    workspaceCollapsed.value = false
    workspaceTab.value = DEFAULT_WORKSPACE_TAB
    persist(UI_STORAGE_KEYS.sidebarCollapsed, 'false')
    persist(UI_STORAGE_KEYS.workspaceCollapsed, 'false')
    persist(UI_STORAGE_KEYS.workspaceTab, DEFAULT_WORKSPACE_TAB)
  }

  return {
    sidebarCollapsed,
    workspaceCollapsed,
    workspaceTab,
    toggleSidebar,
    setSidebarCollapsed,
    toggleWorkspace,
    setWorkspaceCollapsed,
    setWorkspaceTab,
    resetUiState,
    initializeUiState,
  }
})
