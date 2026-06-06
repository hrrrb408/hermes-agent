import { describe, it, expect } from 'vitest'
import {
  themeRegistry,
  getTheme,
  isThemeId,
  getAllThemes,
} from '@/themes/registry'
import {
  THEME_IDS,
  DEFAULT_THEME_ID,
} from '@/themes/types'
import type {
  ThemeId,
  ThemeCategory,
  ThemeColorScheme,
  SurfaceTexture,
  OrnamentStyle,
  DividerStyle,
  HeadingStyle,
} from '@/themes/types'

describe('Theme Registry', () => {
  it('default theme ID is obsidian', () => {
    expect(DEFAULT_THEME_ID).toBe('obsidian')
  })

  it('contains exactly five themes', () => {
    expect(Object.keys(themeRegistry)).toHaveLength(5)
    expect(THEME_IDS).toHaveLength(5)
  })

  it('all five theme IDs exist', () => {
    const expected: ThemeId[] = [
      'obsidian', 'paper', 'song', 'ink', 'sakura-night',
    ]
    for (const id of expected) {
      expect(themeRegistry[id]).toBeDefined()
    }
  })

  it('no duplicate IDs', () => {
    const ids = Object.keys(themeRegistry)
    const uniqueIds = new Set(ids)
    expect(ids.length).toBe(uniqueIds.size)
  })

  it('each theme contains complete ThemeDefinition', () => {
    const requiredFields = [
      'id', 'name', 'localizedName', 'description', 'category',
      'colorScheme', 'previewColors', 'density', 'radius', 'panelStyle',
      'messageStyle', 'toolCardStyle', 'motion', 'fontStyle',
      'surfaceTexture', 'ornamentStyle', 'dividerStyle', 'headingStyle',
    ] as const

    for (const id of THEME_IDS) {
      const theme = themeRegistry[id]
      for (const field of requiredFields) {
        expect(theme[field], `Theme "${id}" missing field "${field}"`).toBeDefined()
      }
    }
  })

  it('each theme has correct category', () => {
    const categoryMap: Record<ThemeId, ThemeCategory> = {
      obsidian: 'modern',
      paper: 'modern',
      song: 'eastern',
      ink: 'eastern',
      'sakura-night': 'eastern',
    }

    for (const id of THEME_IDS) {
      expect(themeRegistry[id].category).toBe(categoryMap[id])
    }
  })

  it('each theme has correct colorScheme', () => {
    const schemeMap: Record<ThemeId, ThemeColorScheme> = {
      obsidian: 'dark',
      paper: 'light',
      song: 'light',
      ink: 'dark',
      'sakura-night': 'dark',
    }

    for (const id of THEME_IDS) {
      expect(themeRegistry[id].colorScheme).toBe(schemeMap[id])
    }
  })

  it('invalid theme ID falls back to Obsidian', () => {
    const theme = getTheme('nonexistent')
    expect(theme.id).toBe('obsidian')
  })

  it('isThemeId returns true for valid IDs', () => {
    expect(isThemeId('obsidian')).toBe(true)
    expect(isThemeId('sakura-night')).toBe(true)
    expect(isThemeId('invalid')).toBe(false)
    expect(isThemeId('')).toBe(false)
  })

  it('getAllThemes returns all five in order', () => {
    const all = getAllThemes()
    expect(all).toHaveLength(5)
    expect(all[0]!.id).toBe('obsidian')
    expect(all[4]!.id).toBe('sakura-night')
  })

  it('previewColors contain background, foreground, and accent', () => {
    for (const id of THEME_IDS) {
      const colors = themeRegistry[id].previewColors
      expect(colors.background).toBeTruthy()
      expect(colors.foreground).toBeTruthy()
      expect(colors.accent).toBeTruthy()
    }
  })

  /* ===== Structural type completeness checks ===== */

  const validSurfaceTextures: SurfaceTexture[] = [
    'clean', 'paper', 'xuan-paper', 'ink-wash', 'night-silk',
  ]
  const validOrnamentStyles: OrnamentStyle[] = [
    'none', 'seal', 'brush', 'sakura',
  ]
  const validDividerStyles: DividerStyle[] = [
    'hairline', 'book-rule', 'brush-fade',
  ]
  const validHeadingStyles: HeadingStyle[] = [
    'modern', 'document', 'song-book', 'ink-inscription', 'night-title',
  ]

  it('every theme has a valid surfaceTexture', () => {
    for (const id of THEME_IDS) {
      const texture = themeRegistry[id].surfaceTexture
      expect(
        validSurfaceTextures.includes(texture),
        `Theme "${id}" has invalid surfaceTexture: "${texture}"`,
      ).toBe(true)
    }
  })

  it('every theme has a valid ornamentStyle', () => {
    for (const id of THEME_IDS) {
      const ornament = themeRegistry[id].ornamentStyle
      expect(
        validOrnamentStyles.includes(ornament),
        `Theme "${id}" has invalid ornamentStyle: "${ornament}"`,
      ).toBe(true)
    }
  })

  it('every theme has a valid dividerStyle', () => {
    for (const id of THEME_IDS) {
      const divider = themeRegistry[id].dividerStyle
      expect(
        validDividerStyles.includes(divider),
        `Theme "${id}" has invalid dividerStyle: "${divider}"`,
      ).toBe(true)
    }
  })

  it('every theme has a valid headingStyle', () => {
    for (const id of THEME_IDS) {
      const heading = themeRegistry[id].headingStyle
      expect(
        validHeadingStyles.includes(heading),
        `Theme "${id}" has invalid headingStyle: "${heading}"`,
      ).toBe(true)
    }
  })

  it('Eastern themes use non-default surface textures', () => {
    expect(themeRegistry.song.surfaceTexture).toBe('xuan-paper')
    expect(themeRegistry.ink.surfaceTexture).toBe('ink-wash')
    expect(themeRegistry['sakura-night'].surfaceTexture).toBe('night-silk')
  })

  it('Eastern themes use non-none ornament styles', () => {
    expect(themeRegistry.song.ornamentStyle).toBe('seal')
    expect(themeRegistry.ink.ornamentStyle).toBe('brush')
    expect(themeRegistry['sakura-night'].ornamentStyle).toBe('sakura')
  })

  it('Eastern themes use non-hairline divider styles (except sakura-night)', () => {
    expect(themeRegistry.song.dividerStyle).toBe('book-rule')
    expect(themeRegistry.ink.dividerStyle).toBe('brush-fade')
    expect(themeRegistry['sakura-night'].dividerStyle).toBe('hairline')
  })

  it('Eastern themes use distinct heading styles', () => {
    expect(themeRegistry.song.headingStyle).toBe('song-book')
    expect(themeRegistry.ink.headingStyle).toBe('ink-inscription')
    expect(themeRegistry['sakura-night'].headingStyle).toBe('night-title')
  })

  it('modern themes use clean surface and none ornament', () => {
    expect(themeRegistry.obsidian.surfaceTexture).toBe('clean')
    expect(themeRegistry.obsidian.ornamentStyle).toBe('none')
    expect(themeRegistry.obsidian.dividerStyle).toBe('hairline')
    expect(themeRegistry.obsidian.headingStyle).toBe('modern')

    expect(themeRegistry.paper.surfaceTexture).toBe('paper')
    expect(themeRegistry.paper.ornamentStyle).toBe('none')
    expect(themeRegistry.paper.dividerStyle).toBe('hairline')
    expect(themeRegistry.paper.headingStyle).toBe('document')
  })

  /* ===== Zen and Ukiyo non-existence checks ===== */

  it('Zen is no longer registered', () => {
    expect(isThemeId('zen')).toBe(false)
    expect(() => getTheme('zen')).not.toThrow()
    expect(getTheme('zen').id).toBe('obsidian') // falls back
  })

  it('Ukiyo is no longer registered', () => {
    expect(isThemeId('ukiyo')).toBe(false)
    expect(() => getTheme('ukiyo')).not.toThrow()
    expect(getTheme('ukiyo').id).toBe('obsidian') // falls back
  })
})
