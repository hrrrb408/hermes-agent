import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '@/stores/theme'
import { STORAGE_KEY_THEME, STORAGE_KEY_FOLLOW_SYSTEM } from '@/themes/types'

function mockMatchMedia(dark: boolean) {
  const addEventListenerSpy = vi.fn()
  const removeEventListenerSpy = vi.fn()
  vi.spyOn(window, 'matchMedia').mockReturnValue({
    matches: dark,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: addEventListenerSpy,
    removeEventListener: removeEventListenerSpy,
    dispatchEvent: vi.fn(),
  })
  return { addEventListenerSpy, removeEventListenerSpy }
}

describe('Theme Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('initial theme is obsidian', () => {
    const store = useThemeStore()
    expect(store.activeThemeId).toBe('obsidian')
  })

  it('setTheme updates activeThemeId', () => {
    const store = useThemeStore()
    store.setTheme('song')
    expect(store.activeThemeId).toBe('song')
  })

  it('setTheme calls theme manager to update DOM', () => {
    const store = useThemeStore()
    store.setTheme('song')
    expect(document.documentElement.getAttribute('data-theme')).toBe('song')
  })

  it('setTheme writes to localStorage', () => {
    const store = useThemeStore()
    store.setTheme('ink')
    expect(localStorage.getItem(STORAGE_KEY_THEME)).toBe('ink')
  })

  it('initializeTheme restores saved theme', () => {
    localStorage.setItem(STORAGE_KEY_THEME, 'ink')
    const store = useThemeStore()
    store.initializeTheme()
    expect(store.activeThemeId).toBe('ink')
  })

  it('initializeTheme falls back to obsidian for invalid localStorage', () => {
    localStorage.setItem(STORAGE_KEY_THEME, 'nonexistent')
    const store = useThemeStore()
    store.initializeTheme()
    expect(store.activeThemeId).toBe('obsidian')
  })

  it('followSystem dark maps to obsidian', () => {
    mockMatchMedia(true)
    localStorage.setItem(STORAGE_KEY_FOLLOW_SYSTEM, 'true')
    const store = useThemeStore()
    store.initializeTheme()
    expect(store.activeThemeId).toBe('obsidian')
  })

  it('followSystem light maps to paper', () => {
    mockMatchMedia(false)
    localStorage.setItem(STORAGE_KEY_FOLLOW_SYSTEM, 'true')
    const store = useThemeStore()
    store.initializeTheme()
    expect(store.activeThemeId).toBe('paper')
  })

  it('followSystem=true: setTheme(song) disables followSystem', () => {
    mockMatchMedia(true)
    const store = useThemeStore()
    store.setFollowSystem(true)
    expect(store.followSystem).toBe(true)

    // User picks a theme through the picker
    store.setTheme('song')
    expect(store.activeThemeId).toBe('song')
    expect(store.followSystem).toBe(false)
    expect(localStorage.getItem(STORAGE_KEY_FOLLOW_SYSTEM)).toBe('false')
  })

  it('after user picks theme, system change does not override', () => {
    const { addEventListenerSpy } = mockMatchMedia(true)
    const store = useThemeStore()
    store.setFollowSystem(true)
    expect(store.followSystem).toBe(true)

    // User picks song
    store.setTheme('song')
    expect(store.followSystem).toBe(false)

    // Simulate system theme change - listener was removed
    expect(addEventListenerSpy).toHaveBeenCalledTimes(1)
    // The listener was removed by setTheme → stopSystemListener
    // So no further system events can fire
  })

  it('re-enabling followSystem immediately maps to current system theme', () => {
    mockMatchMedia(false) // system is light
    const store = useThemeStore()
    store.initializeTheme()
    store.setTheme('ink') // user picks ink
    expect(store.followSystem).toBe(false)

    // User re-enables followSystem
    store.setFollowSystem(true)
    expect(store.followSystem).toBe(true)
    // Should immediately map to paper (system is light)
    expect(store.activeThemeId).toBe('paper')
  })

  it('system listener is not registered twice', () => {
    const { addEventListenerSpy } = mockMatchMedia(false)
    const store = useThemeStore()
    store.setFollowSystem(true)
    store.setFollowSystem(true) // call again

    expect(addEventListenerSpy).toHaveBeenCalledTimes(1)
  })

  it('closing followSystem cleans up listener', () => {
    const { removeEventListenerSpy } = mockMatchMedia(false)
    const store = useThemeStore()
    store.setFollowSystem(true)
    store.setFollowSystem(false)

    expect(removeEventListenerSpy).toHaveBeenCalled()
    expect(store.followSystem).toBe(false)
    expect(localStorage.getItem(STORAGE_KEY_FOLLOW_SYSTEM)).toBe('false')
  })

  it('activeTheme computed returns correct definition', () => {
    const store = useThemeStore()
    store.setTheme('song')
    expect(store.activeTheme.id).toBe('song')
    expect(store.activeTheme.name).toBe('Song')
  })

  it('availableThemes returns all five', () => {
    const store = useThemeStore()
    expect(store.availableThemes).toHaveLength(5)
  })

  it('disposeSystemListener cleans up without error', () => {
    const store = useThemeStore()
    expect(() => store.disposeSystemListener()).not.toThrow()
  })
})
