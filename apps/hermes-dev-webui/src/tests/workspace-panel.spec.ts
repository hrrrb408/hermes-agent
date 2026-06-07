import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import WorkspacePanel from '@/components/layout/WorkspacePanel.vue'
import { useUiStore } from '@/stores/ui'

describe('WorkspacePanel', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('renders all four tabs with Context selected by default', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(4)
    expect(wrapper.get('#workspace-tab-context').attributes('aria-selected')).toBe('true')
  })

  it('switches tab content and writes UI Store state', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-memory').trigger('click')
    expect(useUiStore().workspaceTab).toBe('memory')
    expect(wrapper.text()).toContain('MEM-HERMES-001')
    expect(wrapper.text()).toContain('Mock preview')
  })

  it('shows static Context connection state', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    expect(wrapper.text()).toContain('Runtime injection')
    expect(wrapper.text()).toContain('Not connected')
  })

  it('shows static Agent preview state', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-agent').trigger('click')
    expect(wrapper.text()).toContain('Agent state')
    expect(wrapper.text()).toContain('Preview')
  })

  it('shows a static file tree disclaimer', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-files').trigger('click')
    expect(wrapper.text()).toContain('does not read the local filesystem')
    expect(wrapper.text()).not.toContain('/Users/')
  })

  it('retains tab icons when collapsed', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(4)
    expect(wrapper.findAll('.workspace-tab svg')).toHaveLength(4)
    expect(wrapper.find('[role="tabpanel"]').exists()).toBe(false)
  })

  it('expands and selects a collapsed tab', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    await wrapper.get('#workspace-tab-files').trigger('click')
    expect(useUiStore().workspaceTab).toBe('files')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })

  it('associates the active tab and panel', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tab = wrapper.get('#workspace-tab-context')
    const panel = wrapper.get('#workspace-tabpanel-context')
    expect(tab.attributes('aria-controls')).toBe('workspace-tabpanel-context')
    expect(panel.attributes('aria-labelledby')).toBe('workspace-tab-context')
  })

  it('supports arrow-key tab navigation', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-context').trigger('keydown', { key: 'ArrowRight' })
    expect(useUiStore().workspaceTab).toBe('agent')
    await wrapper.get('#workspace-tab-agent').trigger('keydown', { key: 'Home' })
    expect(useUiStore().workspaceTab).toBe('files')
  })
})
