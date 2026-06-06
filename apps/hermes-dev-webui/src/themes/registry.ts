/**
 * Theme Registry - read-only registry containing all five frozen themes.
 * Guarantees at compile time that every ThemeId has a definition.
 */
import type {
  ThemeDefinition,
  ThemeId,
} from './types'
import { DEFAULT_THEME_ID, THEME_IDS } from './types'

const _themes = {
  obsidian: {
    id: 'obsidian',
    name: 'Obsidian',
    localizedName: 'Obsidian',
    description: 'Modern dark professional developer tool aesthetic',
    category: 'modern',
    colorScheme: 'dark',
    previewColors: {
      background: '#1c1c22',
      foreground: '#e4e4e8',
      accent: '#7c8adb',
      secondary: '#3d3d4a',
    },
    density: 'compact',
    radius: 'medium',
    panelStyle: 'bordered',
    messageStyle: 'bubble',
    toolCardStyle: 'ide',
    motion: 'subtle',
    fontStyle: 'system',
    surfaceTexture: 'clean',
    ornamentStyle: 'none',
    dividerStyle: 'hairline',
    headingStyle: 'modern',
  } satisfies ThemeDefinition,

  paper: {
    id: 'paper',
    name: 'Paper',
    localizedName: 'Paper',
    description: 'Clean light document-reading aesthetic',
    category: 'modern',
    colorScheme: 'light',
    previewColors: {
      background: '#f7f5f2',
      foreground: '#2c2c30',
      accent: '#5b7a9d',
      secondary: '#d8d4cf',
    },
    density: 'comfortable',
    radius: 'small',
    panelStyle: 'paper',
    messageStyle: 'document',
    toolCardStyle: 'paper',
    motion: 'reduced',
    fontStyle: 'system',
    surfaceTexture: 'paper',
    ornamentStyle: 'none',
    dividerStyle: 'hairline',
    headingStyle: 'document',
  } satisfies ThemeDefinition,

  song: {
    id: 'song',
    name: 'Song',
    localizedName: '宋韵 Song',
    description: 'Song dynasty literati and Xuan paper aesthetic',
    category: 'eastern',
    colorScheme: 'light',
    previewColors: {
      background: '#f2ece0',
      foreground: '#2a2a2e',
      accent: '#4a6070',
      secondary: '#b85c38',
    },
    density: 'comfortable',
    radius: 'small',
    panelStyle: 'paper',
    messageStyle: 'scroll',
    toolCardStyle: 'paper',
    motion: 'reduced',
    fontStyle: 'serif',
    surfaceTexture: 'xuan-paper',
    ornamentStyle: 'seal',
    dividerStyle: 'book-rule',
    headingStyle: 'song-book',
  } satisfies ThemeDefinition,

  ink: {
    id: 'ink',
    name: 'Ink',
    localizedName: '墨境 Ink',
    description: 'Chinese ink-wash night aesthetic',
    category: 'eastern',
    colorScheme: 'dark',
    previewColors: {
      background: '#1a1a20',
      foreground: '#d6d2c8',
      accent: '#6b9e8a',
      secondary: '#a04030',
    },
    density: 'compact',
    radius: 'small',
    panelStyle: 'minimal',
    messageStyle: 'minimal',
    toolCardStyle: 'ink',
    motion: 'reduced',
    fontStyle: 'serif',
    surfaceTexture: 'ink-wash',
    ornamentStyle: 'brush',
    dividerStyle: 'brush-fade',
    headingStyle: 'ink-inscription',
  } satisfies ThemeDefinition,

  'sakura-night': {
    id: 'sakura-night',
    name: 'Sakura Night',
    localizedName: '夜樱 Sakura Night',
    description: 'Restrained Japanese night aesthetic',
    category: 'eastern',
    colorScheme: 'dark',
    previewColors: {
      background: '#1c1e2e',
      foreground: '#d0d0dc',
      accent: '#a890a8',
      secondary: '#c0a0b0',
    },
    density: 'comfortable',
    radius: 'large',
    panelStyle: 'soft-card',
    messageStyle: 'bubble',
    toolCardStyle: 'soft',
    motion: 'subtle',
    fontStyle: 'humanist',
    surfaceTexture: 'night-silk',
    ornamentStyle: 'sakura',
    dividerStyle: 'hairline',
    headingStyle: 'night-title',
  } satisfies ThemeDefinition,
} as const satisfies Readonly<Record<ThemeId, ThemeDefinition>>

/** Validate that every ThemeId has a corresponding entry */
function _assertCompleteRegistry(
  registry: Readonly<Record<string, ThemeDefinition>>,
): asserts registry is Readonly<Record<ThemeId, ThemeDefinition>> {
  const missing = THEME_IDS.filter((id) => !(id in registry))
  if (missing.length > 0) {
    throw new Error(`Theme registry missing IDs: ${missing.join(', ')}`)
  }
}

_assertCompleteRegistry(_themes)

/** Read-only theme registry */
export const themeRegistry: Readonly<Record<ThemeId, ThemeDefinition>> = _themes

/** Get a theme definition by ID, falling back to default for invalid IDs */
export function getTheme(id: string): ThemeDefinition {
  if (isThemeId(id)) {
    return themeRegistry[id]
  }
  return themeRegistry[DEFAULT_THEME_ID]
}

/** Type guard for ThemeId */
export function isThemeId(value: string): value is ThemeId {
  return THEME_IDS.includes(value as ThemeId)
}

/** Get all theme definitions as an array */
export function getAllThemes(): readonly ThemeDefinition[] {
  return THEME_IDS.map((id) => themeRegistry[id])
}
