import { describe, it, expect, beforeEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ThemePicker from '@/components/theme/ThemePicker.vue'
import ThemePreviewCard from '@/components/theme/ThemePreviewCard.vue'
import type { ThemeDefinition } from '@/themes/types'

describe('Theme Picker', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountPicker() {
    return mount(ThemePicker, {
      global: {
        components: {
          ThemePreviewCard,
        },
      },
      attachTo: document.body,
    })
  }

  function getThemeId(card: VueWrapper<unknown>): string {
    const props = card.props() as Record<string, unknown>
    const theme = props.theme as ThemeDefinition
    return theme.id
  }

  function isActive(card: VueWrapper<unknown>): boolean {
    const props = card.props() as Record<string, unknown>
    return props.isActive as boolean
  }

  it('groups themes by Modern and Eastern', async () => {
    const wrapper = mountPicker()
    const trigger = wrapper.find('.theme-picker__trigger')
    await trigger.trigger('click')

    const groups = wrapper.findAll('.theme-picker__group')
    expect(groups).toHaveLength(2)

    const labels = groups.map((g) => g.find('.theme-picker__group-label').text())
    expect(labels).toContain('现代 Modern')
    expect(labels).toContain('东方 Eastern')
  })

  it('Modern contains Obsidian and Paper', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const modernGroup = wrapper.findAll('.theme-picker__group')[0]!
    const cards = modernGroup.findAllComponents(ThemePreviewCard)
    const names = cards.map(getThemeId)
    expect(names).toContain('obsidian')
    expect(names).toContain('paper')
  })

  it('Eastern contains Song, Ink, and Sakura Night', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const easternGroup = wrapper.findAll('.theme-picker__group')[1]!
    const cards = easternGroup.findAllComponents(ThemePreviewCard)
    const names = cards.map(getThemeId)
    expect(names).toContain('song')
    expect(names).toContain('ink')
    expect(names).toContain('sakura-night')
  })

  it('does not contain Zen or Ukiyo', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const names = cards.map(getThemeId)
    expect(names).not.toContain('zen')
    expect(names).not.toContain('ukiyo')
  })

  it('clicking a card switches the theme', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const songCard = cards.find((c) => getThemeId(c) === 'song')
    expect(songCard).toBeTruthy()
    await songCard!.trigger('click')

    expect(document.documentElement.getAttribute('data-theme')).toBe('song')
  })

  it('Song is labeled as a dark theme', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const songCard = cards.find((c) => getThemeId(c) === 'song')
    expect(songCard).toBeTruthy()
    expect(songCard!.find('.theme-preview-card__scheme').text()).toBe('Dark')
  })

  it('Ink is labeled as a light theme', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const inkCard = cards.find((c) => getThemeId(c) === 'ink')
    expect(inkCard).toBeTruthy()
    expect(inkCard!.find('.theme-preview-card__scheme').text()).toBe('Light')
  })

  it('Sakura Night is labeled as a dark theme', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const sakuraCard = cards.find((c) => getThemeId(c) === 'sakura-night')
    expect(sakuraCard).toBeTruthy()
    expect(sakuraCard!.find('.theme-preview-card__scheme').text()).toBe('Dark')
  })

  it('current theme shows selected state', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const obsidianCard = cards.find((c) => getThemeId(c) === 'obsidian')
    expect(obsidianCard).toBeTruthy()
    expect(isActive(obsidianCard!)).toBe(true)
  })

  it('Escape closes the picker', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')
    expect(wrapper.find('.theme-picker__dropdown').exists()).toBe(true)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.theme-picker__dropdown').exists()).toBe(false)
  })

  it('clicking outside closes the picker', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')
    expect(wrapper.find('.theme-picker__dropdown').exists()).toBe(true)

    document.dispatchEvent(new MouseEvent('click'))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.theme-picker__dropdown').exists()).toBe(false)
  })

  it('supports keyboard selection on cards', async () => {
    const wrapper = mountPicker()
    await wrapper.find('.theme-picker__trigger').trigger('click')

    const cards = wrapper.findAllComponents(ThemePreviewCard)
    const inkCard = cards.find((c) => getThemeId(c) === 'ink')
    expect(inkCard).toBeTruthy()

    await inkCard!.trigger('click')
    expect(document.documentElement.getAttribute('data-theme')).toBe('ink')
  })

  it('has correct aria states', async () => {
    const wrapper = mountPicker()
    const trigger = wrapper.find('.theme-picker__trigger')
    expect(trigger.attributes('aria-haspopup')).toBe('listbox')

    await trigger.trigger('click')
    expect(trigger.attributes('aria-expanded')).toBe('true')

    const dropdown = wrapper.find('.theme-picker__dropdown')
    expect(dropdown.attributes('role')).toBe('listbox')
  })
})
