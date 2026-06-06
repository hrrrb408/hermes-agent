/**
 * Theme Manager - centralized root element attribute management.
 * All data-attribute and color-scheme mutations go through here.
 * No component should modify root element attributes directly.
 */
import type { ThemeDefinition } from './types'
import { getTheme } from './registry'

const ROOT = (): HTMLElement => document.documentElement

/** Mapping from ThemeDefinition fields to root data-attributes */
const DATA_ATTRIBUTES = {
  'data-theme': 'id',
  'data-density': 'density',
  'data-message-style': 'messageStyle',
  'data-panel-style': 'panelStyle',
  'data-tool-card-style': 'toolCardStyle',
  'data-motion': 'motion',
  'data-font-style': 'fontStyle',
  'data-surface-texture': 'surfaceTexture',
  'data-ornament-style': 'ornamentStyle',
  'data-divider-style': 'dividerStyle',
  'data-heading-style': 'headingStyle',
} as const

/** Apply a theme to the DOM root element */
export function applyTheme(theme: ThemeDefinition): void {
  const root = ROOT()

  for (const [attr, field] of Object.entries(DATA_ATTRIBUTES)) {
    root.setAttribute(attr, theme[field])
  }

  root.style.colorScheme = theme.colorScheme
}

/** Apply a theme by ID (invalid IDs fall back to default) */
export function applyThemeById(id: string): void {
  const theme = getTheme(id)
  applyTheme(theme)
}

/** Read the current data-theme attribute */
export function getCurrentThemeId(): string {
  return ROOT().getAttribute('data-theme') ?? 'obsidian'
}

/** Remove all theme attributes (cleanup for testing) */
export function clearTheme(): void {
  const root = ROOT()
  for (const attr of Object.keys(DATA_ATTRIBUTES)) {
    root.removeAttribute(attr)
  }
  root.style.removeProperty('color-scheme')
}
