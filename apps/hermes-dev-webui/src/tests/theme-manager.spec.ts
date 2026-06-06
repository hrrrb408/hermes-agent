import { describe, it, expect, beforeEach } from 'vitest'
import { applyTheme, applyThemeById, getCurrentThemeId, clearTheme } from '@/themes/theme-manager'
import { getTheme } from '@/themes/registry'
import { THEME_IDS } from '@/themes/types'

describe('Theme Manager', () => {
  beforeEach(() => {
    clearTheme()
  })

  it('sets data-theme attribute', () => {
    const theme = getTheme('song')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-theme')).toBe('song')
  })

  it('sets data-density attribute', () => {
    const theme = getTheme('ink')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-density')).toBe('compact')
  })

  it('sets data-message-style attribute', () => {
    const theme = getTheme('ink')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-message-style')).toBe('minimal')
  })

  it('sets data-panel-style attribute', () => {
    const theme = getTheme('ink')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-panel-style')).toBe('minimal')
  })

  it('sets data-tool-card-style attribute', () => {
    const theme = getTheme('sakura-night')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-tool-card-style')).toBe('soft')
  })

  it('sets data-motion attribute', () => {
    const theme = getTheme('ink')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-motion')).toBe('reduced')
  })

  it('sets data-font-style attribute', () => {
    const theme = getTheme('song')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-font-style')).toBe('serif')
  })

  it('sets data-surface-texture attribute', () => {
    applyTheme(getTheme('song'))
    expect(document.documentElement.getAttribute('data-surface-texture')).toBe('xuan-paper')

    applyTheme(getTheme('ink'))
    expect(document.documentElement.getAttribute('data-surface-texture')).toBe('ink-wash')

    applyTheme(getTheme('sakura-night'))
    expect(document.documentElement.getAttribute('data-surface-texture')).toBe('night-silk')
  })

  it('sets data-ornament-style attribute', () => {
    applyTheme(getTheme('song'))
    expect(document.documentElement.getAttribute('data-ornament-style')).toBe('seal')

    applyTheme(getTheme('ink'))
    expect(document.documentElement.getAttribute('data-ornament-style')).toBe('brush')

    applyTheme(getTheme('sakura-night'))
    expect(document.documentElement.getAttribute('data-ornament-style')).toBe('sakura')
  })

  it('sets data-divider-style attribute', () => {
    applyTheme(getTheme('song'))
    expect(document.documentElement.getAttribute('data-divider-style')).toBe('book-rule')

    applyTheme(getTheme('ink'))
    expect(document.documentElement.getAttribute('data-divider-style')).toBe('brush-fade')
  })

  it('sets data-heading-style attribute', () => {
    applyTheme(getTheme('song'))
    expect(document.documentElement.getAttribute('data-heading-style')).toBe('song-book')

    applyTheme(getTheme('ink'))
    expect(document.documentElement.getAttribute('data-heading-style')).toBe('ink-inscription')

    applyTheme(getTheme('sakura-night'))
    expect(document.documentElement.getAttribute('data-heading-style')).toBe('night-title')
  })

  it('sets color-scheme to dark for dark themes', () => {
    applyTheme(getTheme('obsidian'))
    expect(document.documentElement.style.colorScheme).toBe('dark')
  })

  it('sets color-scheme to light for light themes', () => {
    applyTheme(getTheme('paper'))
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('applyThemeById works with valid IDs', () => {
    applyThemeById('song')
    expect(document.documentElement.getAttribute('data-theme')).toBe('song')
  })

  it('applyThemeById falls back for invalid IDs', () => {
    applyThemeById('nonexistent')
    expect(document.documentElement.getAttribute('data-theme')).toBe('obsidian')
  })

  it('getCurrentThemeId reads from DOM', () => {
    applyThemeById('ink')
    expect(getCurrentThemeId()).toBe('ink')
  })

  it('all themes apply all required attributes including structural attributes', () => {
    const requiredAttrs = [
      'data-theme',
      'data-density',
      'data-message-style',
      'data-panel-style',
      'data-tool-card-style',
      'data-motion',
      'data-font-style',
      'data-surface-texture',
      'data-ornament-style',
      'data-divider-style',
      'data-heading-style',
    ]

    for (const id of THEME_IDS) {
      clearTheme()
      applyThemeById(id)
      for (const attr of requiredAttrs) {
        const val = document.documentElement.getAttribute(attr)
        expect(val, `Theme "${id}" did not set "${attr}"`).toBeTruthy()
      }
      expect(
        document.documentElement.style.colorScheme,
        `Theme "${id}" did not set color-scheme`,
      ).toBeTruthy()
    }
  })

  it('clearTheme removes all data attributes', () => {
    applyThemeById('song')
    clearTheme()
    expect(document.documentElement.getAttribute('data-theme')).toBeNull()
    expect(document.documentElement.getAttribute('data-surface-texture')).toBeNull()
    expect(document.documentElement.getAttribute('data-ornament-style')).toBeNull()
    expect(document.documentElement.getAttribute('data-divider-style')).toBeNull()
    expect(document.documentElement.getAttribute('data-heading-style')).toBeNull()
  })
})
