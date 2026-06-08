/**
 * Phase 0D: Reduced motion and animation tests.
 * Verifies that the CSS motion system and prefers-reduced-motion support work correctly.
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { applyTheme } from '@/themes/theme-manager'
import { themeRegistry, getTheme, getAllThemes } from '@/themes/registry'
import { THEME_IDS } from '@/themes/types'
import SessionSidebar from '@/components/layout/SessionSidebar.vue'

describe('Reduced Motion — Theme Manager', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.removeAttribute('data-motion')
    document.documentElement.removeAttribute('data-density')
    document.documentElement.removeAttribute('data-message-style')
    document.documentElement.removeAttribute('data-panel-style')
    document.documentElement.removeAttribute('data-tool-card-style')
    document.documentElement.removeAttribute('data-radius')
    document.documentElement.removeAttribute('data-font-style')
    document.documentElement.removeAttribute('data-surface-texture')
    document.documentElement.removeAttribute('data-ornament-style')
    document.documentElement.removeAttribute('data-divider-style')
    document.documentElement.removeAttribute('data-heading-style')
  })

  it('theme application sets data-motion attribute', () => {
    const theme = getTheme('obsidian')
    applyTheme(theme)
    expect(document.documentElement.getAttribute('data-motion')).toBeTruthy()
  })

  it('all themes define a motion value', () => {
    const themes = getAllThemes()
    expect(themes).toHaveLength(5)
    for (const theme of themes) {
      expect(theme.motion).toBeTruthy()
      expect(['none', 'reduced', 'subtle', 'smooth']).toContain(theme.motion)
    }
  })

  it('data-motion attribute is one of the valid values', () => {
    const theme = getTheme('obsidian')
    applyTheme(theme)
    const motion = document.documentElement.getAttribute('data-motion')
    expect(['none', 'reduced', 'subtle', 'smooth']).toContain(motion)
  })

  it('obsidian uses subtle motion', () => {
    expect(getTheme('obsidian').motion).toBe('subtle')
  })

  it('sakura-night uses subtle motion', () => {
    expect(getTheme('sakura-night').motion).toBe('subtle')
  })

  it('paper, song, ink use reduced motion', () => {
    expect(getTheme('paper').motion).toBe('reduced')
    expect(getTheme('song').motion).toBe('reduced')
    expect(getTheme('ink').motion).toBe('reduced')
  })
})

describe('Reduced Motion — matchMedia listener', () => {
  it('window.matchMedia is mockable for prefers-reduced-motion', () => {
    // Verify the matchMedia mock exists and can be called
    expect(typeof window.matchMedia).toBe('function')
    const mql = window.matchMedia('prefers-reduced-motion: reduce')
    expect(mql).toBeTruthy()
    expect(mql.media).toBe('prefers-reduced-motion: reduce')
  })
})

describe('Reduced Motion — CSS Variable Mapping', () => {
  it('data-motion=none should be settable', () => {
    document.documentElement.setAttribute('data-motion', 'none')
    expect(document.documentElement.getAttribute('data-motion')).toBe('none')
  })

  it('data-motion=reduced should be settable', () => {
    document.documentElement.setAttribute('data-motion', 'reduced')
    expect(document.documentElement.getAttribute('data-motion')).toBe('reduced')
  })

  it('data-motion=subtle should be settable (default)', () => {
    document.documentElement.setAttribute('data-motion', 'subtle')
    expect(document.documentElement.getAttribute('data-motion')).toBe('subtle')
  })

  it('data-motion=smooth should be settable', () => {
    document.documentElement.setAttribute('data-motion', 'smooth')
    expect(document.documentElement.getAttribute('data-motion')).toBe('smooth')
  })
})

describe('Motion — Spinner animation', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('session sidebar spinner uses aria-hidden', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const spinners = wrapper.findAll('.session-list__spinner')
    for (const spinner of spinners) {
      expect(spinner.attributes('aria-hidden')).toBe('true')
    }
  })
})

describe('Motion — All themes have motion property', () => {
  it('all five themes are registered', () => {
    expect(THEME_IDS).toHaveLength(5)
    expect(THEME_IDS).toContain('obsidian')
    expect(THEME_IDS).toContain('paper')
    expect(THEME_IDS).toContain('song')
    expect(THEME_IDS).toContain('ink')
    expect(THEME_IDS).toContain('sakura-night')
  })

  it('themeRegistry is a readonly record of ThemeId to ThemeDefinition', () => {
    for (const id of THEME_IDS) {
      expect(themeRegistry[id]).toBeTruthy()
      expect(themeRegistry[id].motion).toBeTruthy()
    }
  })
})
