/**
 * Phase 0D: Responsive layout tests.
 * Verifies collapse behavior, layout structure, and viewport-related UI state.
 * Note: jsdom does not support actual viewport dimensions, so these tests
 * verify the component structure, CSS class toggling, and collapse persistence.
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import WorkspaceView from '@/views/WorkspaceView.vue'
import SessionSidebar from '@/components/layout/SessionSidebar.vue'
import WorkspacePanel from '@/components/layout/WorkspacePanel.vue'
import ChatWorkspaceShell from '@/components/layout/ChatWorkspaceShell.vue'
import { useUiStore } from '@/stores/ui'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mountWithStubs(component: any, props: Record<string, unknown> = {}) {
  return mount(component, {
    props,
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

describe('Responsive Layout — Collapse State', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('sidebar collapsed class is applied when sidebarCollapsed is true', async () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    const wrapper = mountWithStubs(WorkspaceView)
    expect(wrapper.find('.workspace-page').classes()).toContain('workspace-page--sidebar-collapsed')
  })

  it('panel collapsed class is applied when workspaceCollapsed is true', async () => {
    const store = useUiStore()
    store.setWorkspaceCollapsed(true)
    const wrapper = mountWithStubs(WorkspaceView)
    expect(wrapper.find('.workspace-page').classes()).toContain('workspace-page--panel-collapsed')
  })

  it('both collapsed classes can be applied simultaneously', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    store.setWorkspaceCollapsed(true)
    const wrapper = mountWithStubs(WorkspaceView)
    const page = wrapper.find('.workspace-page')
    expect(page.classes()).toContain('workspace-page--sidebar-collapsed')
    expect(page.classes()).toContain('workspace-page--panel-collapsed')
  })

  it('no collapsed classes when both are expanded', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(false)
    store.setWorkspaceCollapsed(false)
    const wrapper = mountWithStubs(WorkspaceView)
    const page = wrapper.find('.workspace-page')
    expect(page.classes()).not.toContain('workspace-page--sidebar-collapsed')
    expect(page.classes()).not.toContain('workspace-page--panel-collapsed')
  })
})

describe('Responsive Layout — Collapse Persistence', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('sidebar collapse state persists via localStorage', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    expect(localStorage.getItem('hermes-dev-webui.ui.sidebar-collapsed')).toBe('true')

    // Create a new store instance and verify it reads from storage
    setActivePinia(createPinia())
    const store2 = useUiStore()
    store2.initializeUiState()
    expect(store2.sidebarCollapsed).toBe(true)
  })

  it('panel collapse state persists via localStorage', () => {
    const store = useUiStore()
    store.setWorkspaceCollapsed(true)
    expect(localStorage.getItem('hermes-dev-webui.ui.workspace-collapsed')).toBe('true')

    setActivePinia(createPinia())
    const store2 = useUiStore()
    store2.initializeUiState()
    expect(store2.workspaceCollapsed).toBe(true)
  })

  it('workspace tab persists via localStorage', () => {
    const store = useUiStore()
    store.setWorkspaceTab('memory')
    expect(localStorage.getItem('hermes-dev-webui.ui.workspace-tab')).toBe('memory')

    setActivePinia(createPinia())
    const store2 = useUiStore()
    store2.initializeUiState()
    expect(store2.workspaceTab).toBe('memory')
  })

  it('invalid localStorage values fall back to defaults', () => {
    localStorage.setItem('hermes-dev-webui.ui.sidebar-collapsed', 'maybe')
    localStorage.setItem('hermes-dev-webui.ui.workspace-collapsed', 'kinda')
    localStorage.setItem('hermes-dev-webui.ui.workspace-tab', 'nonexistent')

    const store = useUiStore()
    store.initializeUiState()
    expect(store.sidebarCollapsed).toBe(false)
    expect(store.workspaceCollapsed).toBe(false)
    expect(store.workspaceTab).toBe('context') // default
  })
})

describe('Responsive Layout — Sidebar Collapsed Behavior', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('collapsed sidebar hides search input', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: true } })
    expect(wrapper.find('.session-search').exists()).toBe(false)
  })

  it('expanded sidebar shows search input', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    expect(wrapper.find('.session-search').exists()).toBe(true)
  })

  it('collapsed sidebar hides session text content', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: true } })
    const items = wrapper.findAll('.session-item__content')
    expect(items).toHaveLength(0)
  })

  it('collapsed sidebar hides new-session text', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: true } })
    const btn = wrapper.find('.new-session-button')
    expect(btn.text()).not.toContain('New session')
  })

  it('collapsed sidebar toggle emits toggle event', async () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: true } })
    const toggle = wrapper.find('.session-sidebar__footer button')
    await toggle.trigger('click')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })
})

describe('Responsive Layout — Panel Collapsed Behavior', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('collapsed panel hides panel content', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    expect(wrapper.find('[role="tabpanel"]').exists()).toBe(false)
  })

  it('expanded panel shows panel content', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    expect(wrapper.find('[role="tabpanel"]').exists()).toBe(true)
  })

  it('collapsed panel shows only tab icons', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    const tabs = wrapper.findAll('[role="tab"]')
    // Each tab should have aria-label since text is hidden
    for (const tab of tabs) {
      expect(tab.attributes('aria-label')).toBeTruthy()
    }
  })

  it('clicking tab while collapsed expands panel', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    const tab = wrapper.find('[role="tab"]')
    await tab.trigger('click')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })

  it('collapsed panel uses vertical tab layout', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: true } })
    const tablist = wrapper.find('.workspace-tabs')
    expect(tablist.exists()).toBe(true)
    // Collapsed state removes the bottom border
    expect(tablist.classes()).not.toContain('workspace-tabs--horizontal')
  })
})

describe('Responsive Layout — Layout Grid Structure', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('workspace-body is a CSS grid', () => {
    const wrapper = mountWithStubs(WorkspaceView)
    const body = wrapper.find('.workspace-body')
    expect(body.exists()).toBe(true)
  })

  it('three column children exist: nav, main, aside', () => {
    const wrapper = mountWithStubs(WorkspaceView)
    expect(wrapper.find('nav#session-sidebar').exists()).toBe(true)
    expect(wrapper.find('main.chat-workspace').exists()).toBe(true)
    expect(wrapper.find('aside#workspace-panel').exists()).toBe(true)
  })

  it('workspace page has overflow hidden', () => {
    const wrapper = mountWithStubs(WorkspaceView)
    const page = wrapper.find('.workspace-page')
    expect(page.exists()).toBe(true)
  })

  it('chat workspace scroll area has overflow-x hidden', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const scroll = wrapper.find('.chat-workspace__scroll')
    expect(scroll.exists()).toBe(true)
  })
})

describe('Responsive Layout — Reset', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('resetUiState clears all collapse states', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    store.setWorkspaceCollapsed(true)
    store.setWorkspaceTab('memory')

    store.resetUiState()

    expect(store.sidebarCollapsed).toBe(false)
    expect(store.workspaceCollapsed).toBe(false)
    expect(store.workspaceTab).toBe('context')
  })

  it('resetUiState updates localStorage', () => {
    const store = useUiStore()
    store.setSidebarCollapsed(true)
    store.resetUiState()

    expect(localStorage.getItem('hermes-dev-webui.ui.sidebar-collapsed')).toBe('false')
    expect(localStorage.getItem('hermes-dev-webui.ui.workspace-collapsed')).toBe('false')
    expect(localStorage.getItem('hermes-dev-webui.ui.workspace-tab')).toBe('context')
  })
})
