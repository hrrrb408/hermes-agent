import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SessionSidebar from '@/components/layout/SessionSidebar.vue'

function mountSidebar(collapsed = false) {
  return mount(SessionSidebar, {
    props: {
      collapsed,
      selectedSessionId: 'workspace-shell',
    },
  })
}

describe('SessionSidebar', () => {
  it('shows titles and previews while expanded', () => {
    const wrapper = mountSidebar()
    expect(wrapper.text()).toContain('Workspace shell review')
    expect(wrapper.text()).toContain('Validate the three-column layout')
  })

  it('hides session text while collapsed', () => {
    const wrapper = mountSidebar(true)
    expect(wrapper.text()).not.toContain('Workspace shell review')
    expect(wrapper.get('[aria-label="Workspace shell review"]').attributes('title')).toBe('Workspace shell review')
  })

  it('exposes collapse state and controls', () => {
    const button = mountSidebar().get('[aria-label="Collapse sessions sidebar"]')
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(button.attributes('aria-controls')).toBe('session-sidebar')
  })

  it('emits a static session selection', async () => {
    const wrapper = mountSidebar()
    await wrapper.findAll('.session-item')[1]?.trigger('click')
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ id: 'memory-context' })
  })

  it('filters only local preview sessions', async () => {
    const wrapper = mountSidebar()
    await wrapper.get('input[type="search"]').setValue('theme regression')
    expect(wrapper.findAll('.session-item')).toHaveLength(1)
    expect(wrapper.text()).toContain('Theme regression pass')
  })

  it('marks current session semantically', () => {
    expect(mountSidebar().get('[aria-current="page"]').text()).toContain('Workspace shell review')
  })

  it('keeps new session disabled and marked Preview', () => {
    const button = mountSidebar().get('.new-session-button')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-disabled')).toBe('true')
    expect(button.text()).toContain('Preview')
  })
})
