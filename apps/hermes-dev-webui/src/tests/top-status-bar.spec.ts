import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import TopStatusBar from '@/components/layout/TopStatusBar.vue'
import ThemeSwitcher from '@/components/theme/ThemeSwitcher.vue'

describe('TopStatusBar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountBar() {
    return mount(TopStatusBar, {
      global: {
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a class="theme-lab-link" :href="to"><slot /></a>',
          },
        },
      },
    })
  }

  it('shows explicit static preview statuses', () => {
    const text = mountBar().text()
    expect(text).toContain('Mock')
    expect(text).toContain('Preview')
    expect(text).toContain('Not connected')
  })

  it('does not claim the Gateway is running', () => {
    expect(mountBar().text()).not.toContain('Gateway running')
  })

  it('shows only the safe development home label', () => {
    const text = mountBar().text()
    expect(text).toContain('hermes-home-dev')
    expect(text).not.toContain('/Users/')
  })

  it('contains the shared Theme Switcher', () => {
    expect(mountBar().findComponent(ThemeSwitcher).exists()).toBe(true)
  })

  it('contains an accessible Theme Lab link', () => {
    const link = mountBar().get('.theme-lab-link')
    expect(link.attributes('href')).toBe('/theme-lab')
    expect(link.text()).toContain('Theme Lab')
  })

  it('renders status text alongside decorative icons', () => {
    const wrapper = mountBar()
    expect(wrapper.find('[aria-label="Static preview status"]').text()).toContain('Gateway: Not connected')
    expect(wrapper.findAll('svg[aria-hidden="true"]').length).toBeGreaterThan(0)
  })
})
