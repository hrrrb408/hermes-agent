import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ThemeLabView from '@/views/ThemeLabView.vue'
import ThemeSwitcher from '@/components/theme/ThemeSwitcher.vue'
import ThemeShowcase from '@/components/theme/ThemeShowcase.vue'

describe('Theme Lab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountLab(stubThemeSwitcher = true) {
    return mount(ThemeLabView, {
      global: {
        stubs: {
          ThemeSwitcher: stubThemeSwitcher,
          RouterLink: {
            props: ['to'],
            template: '<a class="theme-lab__back" :href="to"><slot /></a>',
          },
        },
      },
    })
  }

  it('Theme Lab renders', () => {
    const wrapper = mountLab()
    expect(wrapper.find('.theme-lab').exists()).toBe(true)
    expect(wrapper.find('.theme-lab__title').text()).toContain('Hermes Dev WebUI')
  })

  it('Theme Switcher renders', () => {
    const wrapper = mountLab(false)
    expect(wrapper.findComponent(ThemeSwitcher).exists()).toBe(true)
  })

  it('user message example exists', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const userMsg = showcase.find('.message--user')
    expect(userMsg.exists()).toBe(true)
    expect(userMsg.text()).toContain('Hermes')
  })

  it('assistant message example exists', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const assistantMsg = showcase.find('.message--assistant')
    expect(assistantMsg.exists()).toBe(true)
    expect(assistantMsg.text()).toContain('Memory Context Loader')
  })

  it('running, success, error tool cards exist', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)

    const runningCard = showcase.find('.tool-card--running')
    expect(runningCard.exists()).toBe(true)
    expect(runningCard.text()).toContain('memory-context')

    const successCard = showcase.find('.tool-card--success')
    expect(successCard.exists()).toBe(true)
    expect(successCard.text()).toContain('read_file')

    const errorCard = showcase.find('.tool-card--error')
    expect(errorCard.exists()).toBe(true)
    expect(errorCard.text()).toContain('dev-check')
  })

  it('memory example exists', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const memory = showcase.find('.memory-entry')
    expect(memory.exists()).toBe(true)
    expect(memory.text()).toContain('MEM-HERMES-002')
  })

  it('context summary exists', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const context = showcase.find('.context-summary')
    expect(context.exists()).toBe(true)
    expect(context.text()).toContain('Runtime Memory Injection')
    expect(context.text()).toContain('Enabled')
  })

  it('status badges exist', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const badges = showcase.findAll('.status-badge')
    expect(badges.length).toBeGreaterThanOrEqual(8)

    const texts = badges.map((b) => b.text())
    expect(texts).toContain('Success')
    expect(texts).toContain('Warning')
    expect(texts).toContain('Error')
    expect(texts).toContain('Active')
  })

  it('Theme Lab badge exists', () => {
    const wrapper = mountLab()
    expect(wrapper.find('.theme-lab__badge').text()).toBe('Theme Lab')
  })

  /* ===== Theme Signature tests ===== */

  it('Theme Signature section exists', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const signature = showcase.find('.signature')
    expect(signature.exists()).toBe(true)
  })

  it('Theme Signature shows all structural properties', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const items = showcase.findAll('.signature__item')
    expect(items.length).toBe(8)

    const keys = items.map((item) => item.find('.signature__key').text())
    expect(keys).toContain('surfaceTexture')
    expect(keys).toContain('ornamentStyle')
    expect(keys).toContain('dividerStyle')
    expect(keys).toContain('headingStyle')
    expect(keys).toContain('density')
    expect(keys).toContain('messageStyle')
    expect(keys).toContain('toolCardStyle')
    expect(keys).toContain('panelStyle')
  })

  it('Theme Signature shows current theme values', () => {
    const wrapper = mountLab(false)
    const showcase = wrapper.findComponent(ThemeShowcase)
    const items = showcase.findAll('.signature__item')

    // Default theme is obsidian: clean surface, none ornament
    const keyValues: Record<string, string> = {}
    for (const item of items) {
      const key = item.find('.signature__key').text()
      const value = item.find('.signature__value').text()
      keyValues[key] = value
    }

    expect(keyValues['surfaceTexture']).toBe('clean')
    expect(keyValues['ornamentStyle']).toBe('none')
    expect(keyValues['headingStyle']).toBe('modern')
  })
})
