/**
 * Theme system type definitions.
 * All visual variant types are strict unions - no arbitrary strings.
 */

export type ThemeId =
  | 'obsidian'
  | 'paper'
  | 'song'
  | 'ink'
  | 'sakura-night'

export type ThemeCategory = 'modern' | 'eastern'

export type ThemeColorScheme = 'light' | 'dark'

export type ThemeDensity = 'compact' | 'comfortable' | 'spacious'

export type ThemeRadius = 'sharp' | 'small' | 'medium' | 'large'

export type PanelStyle =
  | 'bordered'
  | 'paper'
  | 'minimal'
  | 'soft-card'
  | 'lattice-window'

export type MessageStyle =
  | 'minimal'
  | 'document'
  | 'scroll'
  | 'bubble'
  | 'framed-document'

export type ToolCardStyle =
  | 'ide'
  | 'paper'
  | 'ink'
  | 'record'
  | 'soft'
  | 'lacquer-label'

export type MotionStyle = 'none' | 'reduced' | 'subtle' | 'smooth'

export type FontStyle = 'system' | 'serif' | 'humanist' | 'mono-accent'

/** Surface texture controls background pattern and panel surface feel */
export type SurfaceTexture =
  | 'clean'
  | 'paper'
  | 'xuan-paper'
  | 'ink-wash'
  | 'night-silk'
  | 'lacquer-screen'

/** Ornament style controls small decorative accents (seal, mark, motif) */
export type OrnamentStyle =
  | 'none'
  | 'seal'
  | 'brush'
  | 'sakura'
  | 'garden-shadow'

/** Divider style controls how section dividers and rule lines appear */
export type DividerStyle =
  | 'hairline'
  | 'book-rule'
  | 'brush-fade'
  | 'architectural-beam'

/** Heading style controls heading typography and decoration */
export type HeadingStyle =
  | 'modern'
  | 'document'
  | 'song-book'
  | 'ink-inscription'
  | 'night-title'
  | 'framed-title'

export interface ThemePreviewColors {
  readonly background: string
  readonly foreground: string
  readonly accent: string
  readonly secondary?: string
}

export interface ThemeDefinition {
  readonly id: ThemeId
  readonly name: string
  readonly localizedName: string
  readonly description: string
  readonly category: ThemeCategory
  readonly colorScheme: ThemeColorScheme
  readonly previewColors: ThemePreviewColors
  readonly density: ThemeDensity
  readonly radius: ThemeRadius
  readonly panelStyle: PanelStyle
  readonly messageStyle: MessageStyle
  readonly toolCardStyle: ToolCardStyle
  readonly motion: MotionStyle
  readonly fontStyle: FontStyle
  readonly surfaceTexture: SurfaceTexture
  readonly ornamentStyle: OrnamentStyle
  readonly dividerStyle: DividerStyle
  readonly headingStyle: HeadingStyle
}

/** Ordered list of all valid theme IDs */
export const THEME_IDS: readonly ThemeId[] = [
  'obsidian',
  'paper',
  'song',
  'ink',
  'sakura-night',
] as const

/** Category grouping for the Theme Picker */
export const THEME_CATEGORIES: ReadonlyArray<{
  readonly id: ThemeCategory
  readonly label: string
  readonly localizedLabel: string
  readonly themes: readonly ThemeId[]
}> = [
  {
    id: 'modern',
    label: 'Modern',
    localizedLabel: '现代 Modern',
    themes: ['obsidian', 'paper'],
  },
  {
    id: 'eastern',
    label: 'Eastern',
    localizedLabel: '东方 Eastern',
    themes: ['song', 'ink', 'sakura-night'],
  },
] as const

/** Default theme ID */
export const DEFAULT_THEME_ID: ThemeId = 'obsidian'

/** localStorage keys */
export const STORAGE_KEY_THEME = 'hermes-dev-webui.theme'
export const STORAGE_KEY_FOLLOW_SYSTEM = 'hermes-dev-webui.follow-system'
