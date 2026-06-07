import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { UI_STORAGE_KEYS, useUiStore } from '@/stores/ui'
import { useThemeStore } from '@/stores/theme'

describe('UI Store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('uses expanded defaults and Context tab', () => {
    const store = useUiStore()
    expect(store.sidebarCollapsed).toBe(false)
    expect(store.workspaceCollapsed).toBe(false)
    expect(store.workspaceTab).toBe('context')
  })

  it('toggles and sets sidebar state', () => {
    const store = useUiStore()
    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(true)
    store.setSidebarCollapsed(false)
    expect(store.sidebarCollapsed).toBe(false)
  })

  it('toggles and sets workspace state', () => {
    const store = useUiStore()
    store.toggleWorkspace()
    expect(store.workspaceCollapsed).toBe(true)
    store.setWorkspaceCollapsed(false)
    expect(store.workspaceCollapsed).toBe(false)
  })

  it('sets and persists the workspace tab', () => {
    const store = useUiStore()
    store.setWorkspaceTab('memory')
    expect(store.workspaceTab).toBe('memory')
    expect(localStorage.getItem(UI_STORAGE_KEYS.workspaceTab)).toBe('memory')
  })

  it('persists collapsed states', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    store.setWorkspaceCollapsed(true)
    expect(localStorage.getItem(UI_STORAGE_KEYS.sidebarCollapsed)).toBe('true')
    expect(localStorage.getItem(UI_STORAGE_KEYS.workspaceCollapsed)).toBe('true')
  })

  it('restores valid persisted state', () => {
    localStorage.setItem(UI_STORAGE_KEYS.sidebarCollapsed, 'true')
    localStorage.setItem(UI_STORAGE_KEYS.workspaceCollapsed, 'true')
    localStorage.setItem(UI_STORAGE_KEYS.workspaceTab, 'agent')
    const store = useUiStore()
    store.initializeUiState()
    expect(store.sidebarCollapsed).toBe(true)
    expect(store.workspaceCollapsed).toBe(true)
    expect(store.workspaceTab).toBe('agent')
  })

  it('falls back for invalid persisted values', () => {
    localStorage.setItem(UI_STORAGE_KEYS.sidebarCollapsed, 'yes')
    localStorage.setItem(UI_STORAGE_KEYS.workspaceCollapsed, '1')
    localStorage.setItem(UI_STORAGE_KEYS.workspaceTab, 'settings')
    const store = useUiStore()
    store.initializeUiState()
    expect(store.sidebarCollapsed).toBe(false)
    expect(store.workspaceCollapsed).toBe(false)
    expect(store.workspaceTab).toBe('context')
  })

  it('initializes only once', () => {
    localStorage.setItem(UI_STORAGE_KEYS.sidebarCollapsed, 'true')
    const store = useUiStore()
    store.initializeUiState()
    localStorage.setItem(UI_STORAGE_KEYS.sidebarCollapsed, 'false')
    store.initializeUiState()
    expect(store.sidebarCollapsed).toBe(true)
  })

  it('resets all UI state and persistence', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    store.setWorkspaceCollapsed(true)
    store.setWorkspaceTab('files')
    store.resetUiState()
    expect(store.sidebarCollapsed).toBe(false)
    expect(store.workspaceCollapsed).toBe(false)
    expect(store.workspaceTab).toBe('context')
    expect(localStorage.getItem(UI_STORAGE_KEYS.workspaceTab)).toBe('context')
  })

  it('does not alter Theme Store state', () => {
    const themeStore = useThemeStore()
    const uiStore = useUiStore()
    themeStore.setTheme('ink')
    uiStore.toggleSidebar()
    uiStore.setWorkspaceTab('agent')
    expect(themeStore.activeThemeId).toBe('ink')
  })
})
