/**
 * Theme Store - Pinia store for theme state management.
 * Handles localStorage persistence, system theme following,
 * and delegates DOM mutations to theme-manager.
 *
 * Behavior contract:
 * - setTheme() is a USER action: it disables followSystem, persists
 *   the choice, and stops the system listener. System theme changes
 *   will NOT override the user's pick.
 * - setFollowSystem(true) re-enables system tracking and immediately
 *   applies the current system theme (dark→obsidian, light→paper).
 * - setFollowSystem(false) stops the listener and keeps the current theme.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ThemeDefinition, ThemeId } from '@/themes/types'
import { DEFAULT_THEME_ID, STORAGE_KEY_THEME, STORAGE_KEY_FOLLOW_SYSTEM } from '@/themes/types'
import { getAllThemes, getTheme, isThemeId } from '@/themes/registry'
import { applyTheme } from '@/themes/theme-manager'

export const useThemeStore = defineStore('theme', () => {
  const activeThemeId = ref<ThemeId>(DEFAULT_THEME_ID)
  const followSystem = ref(false)

  let systemMediaQuery: MediaQueryList | null = null
  let systemListener: ((e: MediaQueryListEvent) => void) | null = null

  const activeTheme = computed<ThemeDefinition>(() => getTheme(activeThemeId.value))
  const availableThemes = computed<readonly ThemeDefinition[]>(() => getAllThemes())

  /**
   * User-initiated theme selection.
   * Disables followSystem so system changes do not override this choice.
   */
  function setTheme(themeId: ThemeId): void {
    if (followSystem.value) {
      followSystem.value = false
      persistFollowSystem(false)
      stopSystemListener()
    }

    activeThemeId.value = themeId
    applyTheme(getTheme(themeId))
    persistToStorage(themeId)
  }

  /**
   * Enable or disable system theme following.
   * When enabled: starts listener and immediately applies system mapping.
   * When disabled: stops listener, keeps current theme.
   */
  function setFollowSystem(enabled: boolean): void {
    followSystem.value = enabled
    persistFollowSystem(enabled)

    if (enabled) {
      startSystemListener()
      applySystemTheme()
    } else {
      stopSystemListener()
    }
  }

  /**
   * Initialize theme on app startup.
   * Priority: saved followSystem > saved theme > default (obsidian).
   */
  function initializeTheme(): void {
    const savedFollow = readFollowSystem()
    const savedId = readFromStorage()

    if (savedFollow) {
      followSystem.value = true
      startSystemListener()
      applySystemTheme()
      if (savedId) {
        persistToStorage(getSystemMappedId())
      }
    } else if (savedId) {
      activeThemeId.value = savedId
      applyTheme(getTheme(savedId))
    } else {
      activeThemeId.value = DEFAULT_THEME_ID
      applyTheme(getTheme(DEFAULT_THEME_ID))
    }
  }

  /** Clean up system listener (e.g. on component unmount) */
  function disposeSystemListener(): void {
    stopSystemListener()
  }

  function applySystemTheme(): void {
    const id = getSystemMappedId()
    activeThemeId.value = id
    applyTheme(getTheme(id))
  }

  function getSystemMappedId(): ThemeId {
    if (typeof window === 'undefined') return DEFAULT_THEME_ID
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    return mq.matches ? 'obsidian' : 'paper'
  }

  function startSystemListener(): void {
    if (typeof window === 'undefined') return
    if (systemListener) return // guard: no double registration

    systemMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    systemListener = () => {
      applySystemTheme()
    }
    systemMediaQuery.addEventListener('change', systemListener)
  }

  function stopSystemListener(): void {
    if (systemMediaQuery && systemListener) {
      systemMediaQuery.removeEventListener('change', systemListener)
    }
    systemMediaQuery = null
    systemListener = null
  }

  function persistToStorage(id: ThemeId): void {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY_THEME, id)
    } catch {
      // localStorage unavailable - silently degrade
    }
  }

  function readFromStorage(): ThemeId | null {
    if (typeof window === 'undefined') return null
    try {
      const stored = localStorage.getItem(STORAGE_KEY_THEME)
      if (stored && isThemeId(stored)) return stored
    } catch {
      // localStorage unavailable
    }
    return null
  }

  function persistFollowSystem(enabled: boolean): void {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY_FOLLOW_SYSTEM, enabled ? 'true' : 'false')
    } catch {
      // silently degrade
    }
  }

  function readFollowSystem(): boolean {
    if (typeof window === 'undefined') return false
    try {
      const stored = localStorage.getItem(STORAGE_KEY_FOLLOW_SYSTEM)
      return stored === 'true'
    } catch {
      return false
    }
  }

  return {
    activeThemeId,
    followSystem,
    activeTheme,
    availableThemes,
    setTheme,
    setFollowSystem,
    initializeTheme,
    disposeSystemListener,
  }
})
