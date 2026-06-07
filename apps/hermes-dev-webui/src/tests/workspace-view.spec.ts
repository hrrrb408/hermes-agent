import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import WorkspaceView from '@/views/WorkspaceView.vue'
import { useUiStore } from '@/stores/ui'

describe('WorkspaceView', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  function mountWorkspace() {
    return mount(WorkspaceView, {
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

  it('renders the workspace root and semantic regions', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.find('.workspace-page').exists()).toBe(true)
    expect(wrapper.find('header.top-status-bar').exists()).toBe(true)
    expect(wrapper.find('nav[aria-label="Sessions"]').exists()).toBe(true)
    expect(wrapper.find('main.chat-workspace').exists()).toBe(true)
    expect(wrapper.find('aside[aria-label="Workspace context"]').exists()).toBe(true)
  })

  it('always renders the central workspace and Composer', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.find('.chat-workspace').exists()).toBe(true)
    expect(wrapper.find('.composer').exists()).toBe(true)
    expect(wrapper.get('textarea').attributes('aria-label')).toBe('Message composer preview')
  })

  it('keeps attachment and send controls disabled', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.get('[aria-label="Attach file - Preview only"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[aria-label="Send message - Preview only"]').attributes('disabled')).toBeDefined()
  })

  it('toggles both side regions independently', async () => {
    const wrapper = mountWorkspace()
    await wrapper.get('[aria-label="Collapse sessions sidebar"]').trigger('click')
    expect(useUiStore().sidebarCollapsed).toBe(true)
    expect(wrapper.find('.workspace-page--sidebar-collapsed').exists()).toBe(true)

    await wrapper.get('[aria-label="Collapse workspace panel"]').trigger('click')
    expect(useUiStore().workspaceCollapsed).toBe(true)
    expect(wrapper.find('.workspace-page--panel-collapsed').exists()).toBe(true)
    expect(wrapper.find('.chat-workspace').exists()).toBe(true)
  })

  it('shows default workspace title when no session is selected', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.get('.chat-workspace__header h1').text()).toBe('Hermes Dev Workspace')
  })

  it('shows read-only indicator in composer', () => {
    const text = mountWorkspace().text()
    expect(text).toContain('Read only')
    expect(text).toContain('Messages not available')
  })

  it('does not expose production paths or running claims', () => {
    const text = mountWorkspace().text()
    expect(text).not.toContain('/Users/huangruibang')
    expect(text).not.toContain('Gateway running')
  })

  it('shows session selection prompt when no session is selected', () => {
    const text = mountWorkspace().text()
    expect(text).toContain('Select a session from the sidebar')
  })
})
