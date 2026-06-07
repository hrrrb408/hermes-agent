import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import SessionSidebar from '@/components/layout/SessionSidebar.vue'
import { useSessionStore } from '@/stores/session'
import type { SessionListItem } from '@/types/api/session'

/** Create a minimal session list item for testing. */
function makeSession(overrides: Partial<SessionListItem> = {}): SessionListItem {
  return {
    id: 'test-session-1',
    title: 'Test session',
    source: 'cli',
    model: 'deepseek-chat',
    messageCount: 5,
    toolCallCount: 2,
    archived: false,
    startedAt: '2026-06-07T10:00:00Z',
    endedAt: null,
    lastActiveAt: '2026-06-07T10:30:00Z',
    preview: 'Hello world preview text',
    ...overrides,
  }
}

function mountSidebar(collapsed = false) {
  return mount(SessionSidebar, {
    props: { collapsed },
    global: { plugins: [createPinia()] },
  })
}

describe('SessionSidebar', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('shows session titles and previews while expanded', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    // Inject test data directly into the store
    store.sessions = [
      makeSession({ id: 's1', title: 'Workspace shell review', preview: 'Validate the three-column layout' }),
      makeSession({ id: 's2', title: 'Memory context notes', preview: 'Static preview' }),
    ]
    store.listStatus = 'success'
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Workspace shell review')
    expect(wrapper.text()).toContain('Validate the three-column layout')
  })

  it('hides session text while collapsed', async () => {
    const wrapper = mountSidebar(true)
    const store = useSessionStore()
    store.sessions = [makeSession({ id: 's1', title: 'Workspace shell review' })]
    store.listStatus = 'success'
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('Workspace shell review')
    expect(wrapper.get('[aria-label="Workspace shell review"]').attributes('title')).toBe('Workspace shell review')
  })

  it('exposes collapse state and controls', () => {
    const button = mountSidebar().get('[aria-label="Collapse sessions sidebar"]')
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(button.attributes('aria-controls')).toBe('session-sidebar')
  })

  it('selects a session via store action', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.sessions = [
      makeSession({ id: 's1', title: 'Session 1' }),
      makeSession({ id: 's2', title: 'Session 2' }),
    ]
    store.listStatus = 'success'
    await wrapper.vm.$nextTick()

    // Mock the store's selectSession to avoid API calls
    const selectSpy = vi.spyOn(store, 'selectSession').mockResolvedValue()
    await wrapper.findAll('.session-item')[1]?.trigger('click')
    expect(selectSpy).toHaveBeenCalledWith('s2')
  })

  it('shows empty state when no sessions', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.sessions = []
    store.listStatus = 'empty'
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('No development sessions found.')
  })

  it('marks current session semantically', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.sessions = [makeSession({ id: 's1', title: 'Active session' })]
    store.listStatus = 'success'
    store.selectedSessionId = 's1'
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[aria-current="page"]').text()).toContain('Active session')
  })

  it('keeps new session disabled and marked Preview', () => {
    const button = mountSidebar().get('.new-session-button')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-disabled')).toBe('true')
    expect(button.text()).toContain('Preview')
  })

  it('shows loading state', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.listStatus = 'loading'
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.session-list__loading').exists()).toBe(true)
    expect(wrapper.text()).toContain('Loading sessions')
  })

  it('shows error state with retry', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.listStatus = 'error'
    store.listError = 'Unable to load sessions.'
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.session-list__error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Unable to load sessions.')
    expect(wrapper.find('.session-list__retry').exists()).toBe(true)
  })

  it('shows load more button when hasMore is true', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.sessions = [makeSession({ id: 's1' })]
    store.listStatus = 'success'
    store.hasMore = true
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.session-list__load-more').exists()).toBe(true)
  })

  it('hides load more when hasMore is false', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    store.sessions = [makeSession({ id: 's1' })]
    store.listStatus = 'success'
    store.hasMore = false
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.session-list__load-more').exists()).toBe(false)
  })

  it('uses search to filter sessions via store', async () => {
    const wrapper = mountSidebar()
    const store = useSessionStore()
    const searchSpy = vi.spyOn(store, 'setSearchQuery')

    await wrapper.get('input[type="search"]').setValue('test query')
    expect(searchSpy).toHaveBeenCalledWith('test query')
  })
})
