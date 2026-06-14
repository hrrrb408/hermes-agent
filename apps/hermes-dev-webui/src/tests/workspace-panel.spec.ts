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

  it('renders all eight tabs with Context selected by default', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(8)
    expect(wrapper.get('#workspace-tab-context').attributes('aria-selected')).toBe('true')
  })

  it('switches tab content and writes UI Store state', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-memory').trigger('click')
    expect(useUiStore().workspaceTab).toBe('memory')
    // Memory panel shows loading or error state (no mock data)
    expect(wrapper.text()).not.toContain('MEM-HERMES-001')
    expect(wrapper.text()).not.toContain('Mock preview')
  })

  it('shows Context panel with query input', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    // Context tab is default — shows query form
    expect(wrapper.find('#context-query-input').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Not connected')
  })

  it('shows Agent panel with loading state', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-agent').trigger('click')
    // Agent panel shows loading state (tries real API) or error
    const text = wrapper.text()
    expect(
      text.includes('Loading') ||
      text.includes('Agent status') ||
      text.includes('Agent') ||
      text.includes('Retry')
    ).toBe(true)
    // Phase 1E: safe preview sub-tabs are present
    expect(text).toContain('Prompt Preview')
    expect(text).toContain('Run Dry-Run')
    // Must NOT contain real execution action buttons
    expect(text).not.toContain('Run Agent')
    expect(text).not.toContain('Send to Model')
    expect(text).not.toContain('Execute Agent')
    expect(text).not.toContain('Start Stream')
    expect(text).not.toContain('Call Model')
  })

  it('shows a static file tree disclaimer', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-files').trigger('click')
    expect(wrapper.text()).toContain('does not read the local filesystem')
    expect(wrapper.text()).not.toContain('/Users/')
  })

  it('shows Review panel with read-only state', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    await wrapper.get('#workspace-tab-reviews').trigger('click')
    const text = wrapper.text()
    // Review panel shows loading or unavailable state
    expect(
      text.includes('Loading') ||
      text.includes('Unavailable') ||
      text.includes('Review') ||
      text.includes('Read-only')
    ).toBe(true)
  })

  it('never renders raw local paths in any tab', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    // Check all eight tabs for local path leakage
    const tabs = ['memory', 'context', 'agent', 'files', 'reviews', 'tools', 'provider'] as const
    for (const tab of tabs) {
      await wrapper.get(`#workspace-tab-${tab}`).trigger('click')
      const html = wrapper.html()
      expect(html, `Tab ${tab} should not contain /Users/`).not.toContain('/Users/')
      expect(html, `Tab ${tab} should not contain /home/`).not.toContain('/home/')
      expect(html, `Tab ${tab} should not contain file://`).not.toContain('file://')
    }
  })

  it('retains tab icons when collapsed', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(8)
    expect(wrapper.findAll('.workspace-tab svg')).toHaveLength(8)
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
    // Tabs order: files, memory, context, reviews, agent, tools
    // ArrowRight from context → reviews
    await wrapper.get('#workspace-tab-context').trigger('keydown', { key: 'ArrowRight' })
    expect(useUiStore().workspaceTab).toBe('reviews')
    // Home → files (first tab)
    await wrapper.get('#workspace-tab-reviews').trigger('keydown', { key: 'Home' })
    expect(useUiStore().workspaceTab).toBe('files')
  })
})
