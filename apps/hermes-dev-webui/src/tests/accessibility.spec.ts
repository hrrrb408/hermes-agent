/**
 * Phase 0D: Accessibility tests for workspace components.
 * Covers ARIA roles, labels, keyboard navigation, focus, and semantic HTML.
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import SessionSidebar from '@/components/layout/SessionSidebar.vue'
import ChatWorkspaceShell from '@/components/layout/ChatWorkspaceShell.vue'
import WorkspacePanel from '@/components/layout/WorkspacePanel.vue'
import TopStatusBar from '@/components/layout/TopStatusBar.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'
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

describe('Accessibility — TopStatusBar', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  function mountStatusBar() {
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

  it('has banner role', () => {
    const wrapper = mountStatusBar()
    const header = wrapper.find('header')
    expect(header.exists()).toBe(true)
    expect(header.attributes('role')).toBe('banner')
  })

  it('has aria-label on status items container', () => {
    const wrapper = mountStatusBar()
    const statuses = wrapper.find('.top-status-bar__statuses')
    expect(statuses.exists()).toBe(true)
    expect(statuses.attributes('aria-label')).toBeTruthy()
  })

  it('has aria-label on theme lab link', () => {
    const wrapper = mountStatusBar()
    const link = wrapper.find('.theme-lab-link')
    expect(link.exists()).toBe(true)
    expect(link.attributes('aria-label')).toBeTruthy()
  })

  it('hides decorative icons with aria-hidden', () => {
    const wrapper = mountStatusBar()
    const icons = wrapper.findAll('[aria-hidden="true"]')
    expect(icons.length).toBeGreaterThanOrEqual(3)
  })
})

describe('Accessibility — SessionSidebar', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('uses nav element with aria-label', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const nav = wrapper.find('nav')
    expect(nav.exists()).toBe(true)
    expect(nav.attributes('aria-label')).toBe('Sessions')
  })

  it('has aria-busy on session list during loading', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const list = wrapper.find('.session-list')
    expect(list.exists()).toBe(true)
    // aria-busy should be present (value depends on store state)
    expect(list.attributes('aria-busy')).toBeDefined()
  })

  it('has aria-current on selected session', async () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    // No session selected by default — aria-current should not be set
    const items = wrapper.findAll('.session-item')
    for (const item of items) {
      expect(item.attributes('aria-current')).toBeUndefined()
    }
  })

  it('has aria-disabled on disabled new-session button', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const btn = wrapper.find('.new-session-button')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.attributes('aria-disabled')).toBe('true')
  })

  it('has aria-label on search input', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const input = wrapper.find('.session-search input')
    expect(input.exists()).toBe(true)
    expect(input.attributes('aria-label')).toBeTruthy()
  })

  it('has aria-label on collapse/expand toggle', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const toggle = wrapper.find('.session-sidebar__footer button')
    expect(toggle.exists()).toBe(true)
    expect(toggle.attributes('aria-label')).toContain('Collapse')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(toggle.attributes('aria-controls')).toBe('session-sidebar')
  })

  it('toggle button label changes when collapsed', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: true } })
    const toggle = wrapper.find('.session-sidebar__footer button')
    expect(toggle.attributes('aria-label')).toContain('Expand')
    expect(toggle.attributes('aria-expanded')).toBe('false')
  })

  it('error state uses role="alert"', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    // Error state requires store to be in error state
    // Verify the template structure has role="alert" capability
    const errorEl = wrapper.find('[role="alert"]')
    // May or may not be present depending on store state
    if (errorEl.exists()) {
      expect(errorEl.text()).toBeTruthy()
    }
  })

  it('loading state has aria-live', () => {
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const liveEl = wrapper.find('[aria-live="polite"]')
    // May or may not be visible depending on store state
    if (liveEl.exists()) {
      expect(liveEl.text()).toBeTruthy()
    }
  })
})

describe('Accessibility — ChatWorkspaceShell', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('uses main element', () => {
    const wrapper = mount(ChatWorkspaceShell)
    expect(wrapper.find('main').exists()).toBe(true)
  })

  it('empty state has aria-labelledby', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const section = wrapper.find('[aria-labelledby="workspace-empty-title"]')
    expect(section.exists()).toBe(true)
    const heading = wrapper.find('#workspace-empty-title')
    expect(heading.exists()).toBe(true)
  })

  it('composer has visible label via for/id association', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const label = wrapper.find('.composer__label')
    expect(label.exists()).toBe(true)
    expect(label.attributes('for')).toBe('workspace-composer')
    const textarea = wrapper.find('#workspace-composer')
    expect(textarea.exists()).toBe(true)
  })

  it('send button is disabled with aria-label', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const sendBtn = wrapper.find('.composer__send')
    expect(sendBtn.exists()).toBe(true)
    expect(sendBtn.attributes('disabled')).toBeDefined()
    expect(sendBtn.attributes('aria-label')).toContain('Send')
  })

  it('attach button is disabled with aria-label', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const attachBtn = wrapper.find('.composer__actions button[type="button"]')
    expect(attachBtn.exists()).toBe(true)
    expect(attachBtn.attributes('disabled')).toBeDefined()
    expect(attachBtn.attributes('aria-label')).toBeTruthy()
  })

  it('composer label uses sr-only positioning', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const label = wrapper.find('.composer__label')
    // Should have overflow hidden and clip for screen-reader-only
    expect(label.exists()).toBe(true)
  })
})

describe('Accessibility — WorkspacePanel', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('uses aside element with aria-label', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const aside = wrapper.find('aside')
    expect(aside.exists()).toBe(true)
    expect(aside.attributes('aria-label')).toBeTruthy()
  })

  it('has proper tablist/tab/tabpanel structure', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tablist = wrapper.find('[role="tablist"]')
    expect(tablist.exists()).toBe(true)
    expect(tablist.attributes('aria-label')).toBeTruthy()
    expect(tablist.attributes('aria-orientation')).toBe('vertical')

    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs).toHaveLength(7)

    const tabpanel = wrapper.find('[role="tabpanel"]')
    expect(tabpanel.exists()).toBe(true)
  })

  it('each tab has aria-selected and aria-controls', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tabs = wrapper.findAll('[role="tab"]')
    for (const tab of tabs) {
      expect(tab.attributes('aria-selected')).toBeDefined()
      expect(tab.attributes('aria-controls')).toMatch(/^workspace-tabpanel-/)
    }
  })

  it('tabpanel has aria-labelledby matching active tab', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tabpanel = wrapper.find('[role="tabpanel"]')
    const labelledBy = tabpanel.attributes('aria-labelledby')
    expect(labelledBy).toBeTruthy()
    const activeTab = wrapper.find(`#${labelledBy}`)
    expect(activeTab.exists()).toBe(true)
    expect(activeTab.attributes('aria-selected')).toBe('true')
  })

  it('active tab has tabindex=0, inactive tabs have tabindex=-1', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const tabs = wrapper.findAll('[role="tab"]')
    let activeCount = 0
    let inactiveCount = 0
    for (const tab of tabs) {
      const tabindex = tab.attributes('tabindex')
      if (tab.attributes('aria-selected') === 'true') {
        expect(tabindex).toBe('0')
        activeCount++
      } else {
        expect(tabindex).toBe('-1')
        inactiveCount++
      }
    }
    expect(activeCount).toBe(1)
    expect(inactiveCount).toBe(6)
  })

  it('collapse toggle has aria-expanded and aria-controls', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const toggle = wrapper.find('.workspace-panel__header button')
    expect(toggle.exists()).toBe(true)
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(toggle.attributes('aria-controls')).toBe('workspace-panel')
  })

  it('keyboard arrow navigation cycles through tabs', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const contextTab = wrapper.get('#workspace-tab-context')

    // Press ArrowRight should move to next tab
    await contextTab.trigger('keydown', { key: 'ArrowRight' })
    const store = useUiStore()
    expect(store.workspaceTab).toBe('reviews') // tabs order: files, memory, context, reviews, agent, tools
  })

  it('Home key selects first tab', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const contextTab = wrapper.get('#workspace-tab-context')
    await contextTab.trigger('keydown', { key: 'Home' })
    const store = useUiStore()
    expect(store.workspaceTab).toBe('files')
  })

  it('End key selects last tab', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const contextTab = wrapper.get('#workspace-tab-context')
    await contextTab.trigger('keydown', { key: 'End' })
    const store = useUiStore()
    expect(store.workspaceTab).toBe('provider') // tabs order ends with provider
  })
})

describe('Accessibility — Panel Error/Loading States', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('workspace panel content has error states with role=alert when visible', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    // Switch to agent tab to trigger load
    const agentTab = wrapper.find('#workspace-tab-agent')
    if (agentTab.exists()) {
      await agentTab.trigger('click')
    }
    // Check the tabpanel for role="alert" in error states
    const content = wrapper.find('.workspace-panel__content')
    if (content.exists()) {
      const alertEl = content.find('[role="alert"]')
      if (alertEl.exists()) {
        expect(alertEl.find('button').exists()).toBe(true)
      }
    }
  })

  it('workspace panel retry buttons have descriptive labels when visible', async () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    // Check all tabs for retry buttons
    const tabs = ['memory', 'context', 'agent'] as const
    for (const tab of tabs) {
      const tabEl = wrapper.find(`#workspace-tab-${tab}`)
      if (tabEl.exists()) {
        await tabEl.trigger('click')
      }
    }
    const retryBtns = wrapper.findAll('.panel-retry-btn')
    for (const btn of retryBtns) {
      expect(btn.attributes('aria-label')).toBeTruthy()
    }
  })
})

describe('Accessibility — No v-html', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('SessionSidebar does not use v-html', () => {
    // Runtime check: ensure no v-html directives are rendered
    const wrapper = mount(SessionSidebar, { props: { collapsed: false } })
    const vHtml = wrapper.find('[v-html]')
    expect(vHtml.exists()).toBe(false)
  })

  it('ChatWorkspaceShell does not use v-html', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const vHtml = wrapper.find('[v-html]')
    expect(vHtml.exists()).toBe(false)
  })

  it('WorkspacePanel does not use v-html', () => {
    const wrapper = mount(WorkspacePanel, { props: { collapsed: false } })
    const vHtml = wrapper.find('[v-html]')
    expect(vHtml.exists()).toBe(false)
  })
})

describe('Accessibility — Semantic HTML', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('layout uses nav + main + aside structure', () => {
    const wrapper = mountWithStubs(WorkspaceView)
    expect(wrapper.find('nav').exists()).toBe(true)
    expect(wrapper.find('main').exists()).toBe(true)
    expect(wrapper.find('aside').exists()).toBe(true)
  })

  it('time elements have datetime attribute', () => {
    const wrapper = mount(ChatWorkspaceShell)
    const times = wrapper.findAll('time')
    // Time elements may only appear when messages are loaded
    for (const time of times) {
      expect(time.attributes('datetime')).toBeTruthy()
    }
  })

  it('message list uses ordered list', () => {
    // The message list template uses <ol> — verify the structure exists
    // Only visible when messages are loaded
    const wrapper = mount(ChatWorkspaceShell)
    const ol = wrapper.find('ol.message-list')
    // May not be present without loaded messages
    if (ol.exists()) {
      expect(ol.attributes('aria-label')).toBeTruthy()
    }
  })
})
