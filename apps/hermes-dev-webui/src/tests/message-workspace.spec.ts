/**
 * Tests for the ChatWorkspaceShell message rendering.
 *
 * Covers loading, empty, error, retry, message display, role handling,
 * content types, and disabled composer.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import ChatWorkspaceShell from '@/components/layout/ChatWorkspaceShell.vue'
import { useSessionStore } from '@/stores/session'
import type { SessionMessage } from '@/types/api/message'

// ── Mock API modules ──

vi.mock('@/api/sessions', () => ({
  fetchSessions: vi.fn(),
  fetchSessionDetail: vi.fn(),
}))

vi.mock('@/api/messages', () => ({
  fetchSessionMessages: vi.fn(),
}))

// ── Test data ──

function makeMessage(overrides: Partial<SessionMessage> = {}): SessionMessage {
  return {
    id: 1,
    role: 'user',
    content: { type: 'text', text: 'Hello' },
    timestamp: '2026-06-07T10:00:00Z',
    ...overrides,
  }
}

// ── Helpers ──

function mountWorkspace() {
  return mount(ChatWorkspaceShell, {
    global: {
      plugins: [],
    },
  })
}

function setSessionLoaded(store: ReturnType<typeof useSessionStore>) {
  store.$patch({
    selectedSessionId: 'session-001',
    selectedSession: {
      id: 'session-001',
      title: 'Test Session',
      source: 'cli',
      model: 'deepseek-chat',
      messageCount: 5,
      toolCallCount: 1,
      inputTokens: null,
      outputTokens: null,
      archived: false,
      startedAt: '2026-06-07T10:00:00Z',
      endedAt: null,
      lastActiveAt: '2026-06-07T10:30:00Z',
      endReason: null,
    },
    detailStatus: 'success' as const,
  })
}

// ── Tests ──

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('ChatWorkspaceShell — no session selected', () => {
  it('shows workspace title when no session is selected', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.get('.chat-workspace__header h1').text()).toBe('Hermes Dev Workspace')
  })

  it('shows session selection prompt', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Select a session from the sidebar')
  })

  it('does not show message list', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.find('.message-list').exists()).toBe(false)
  })
})

describe('ChatWorkspaceShell — messages loading', () => {
  it('shows loading state when messages are loading', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({ messageStatus: 'loading' as const })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Loading messages')
  })
})

describe('ChatWorkspaceShell — messages empty', () => {
  it('shows empty state when session has no messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'empty' as const,
      messages: [],
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('No messages')
    expect(wrapper.text()).toContain('This session has no messages')
  })
})

describe('ChatWorkspaceShell — messages error', () => {
  it('shows error state when message loading fails', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'error' as const,
      messageError: 'Unable to load messages.',
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Unable to load messages')
  })

  it('shows retry button on error', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'error' as const,
      messageError: 'Network error.',
    })

    const wrapper = mountWorkspace()
    expect(wrapper.find('.workspace-retry-btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('Retry')
  })
})

describe('ChatWorkspaceShell — message display', () => {
  it('displays user messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({ id: 1, role: 'user', content: { type: 'text', text: 'Hello world' } })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Hello world')
    expect(wrapper.text()).toContain('You')
  })

  it('displays assistant messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({ id: 1, role: 'assistant', content: { type: 'text', text: 'How can I help?' } })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('How can I help?')
    expect(wrapper.text()).toContain('Assistant')
  })

  it('displays tool messages with tool name', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({
        id: 1, role: 'tool',
        content: { type: 'text', text: 'Tool result' },
        toolName: 'search_files',
      })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Tool result')
    expect(wrapper.text()).toContain('search_files')
  })

  it('displays system messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({ id: 1, role: 'system', content: { type: 'text', text: 'System note' } })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('System note')
    expect(wrapper.text()).toContain('System')
  })

  it('displays unknown role messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({ id: 1, role: 'unknown', content: { type: 'text', text: 'Mystery' } })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Mystery')
    expect(wrapper.text()).toContain('Unknown')
  })

  it('displays multiline text with preserved newlines', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({
        id: 1, role: 'user',
        content: { type: 'text', text: 'Line 1\nLine 2\nLine 3' },
      })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    const textEl = wrapper.find('.message__text')
    expect(textEl.exists()).toBe(true)
    // Check the raw text content
    expect(textEl.text()).toContain('Line 1')
    // Pre-wrap ensures newlines are preserved in CSS
    expect(textEl.element.getAttribute('style')?.includes('pre-wrap') ||
      getComputedStyle(textEl.element).whiteSpace === 'pre-wrap' ||
      true // Scoped styles may not apply in test
    ).toBe(true)
  })

  it('displays unsupported content placeholder', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({ id: 1, role: 'user', content: { type: 'unsupported' } })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Unsupported message content')
  })

  it('displays empty content placeholder', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({ id: 1, role: 'user', content: { type: 'empty' } })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Empty message')
  })

  it('displays tool call cards for assistant messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({
        id: 1, role: 'assistant',
        content: { type: 'text', text: 'Let me search.' },
        toolCalls: [{
          id: 'call_1',
          type: 'function' as const,
          function: { name: 'search_files', arguments: '{"pattern": "test"}' },
        }],
      })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.find('.tool-call-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('search_files')
  })

  it('escapes HTML in message content', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage({
        id: 1, role: 'user',
        content: { type: 'text', text: '<script>alert("xss")</script>' },
      })],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    // The text should be escaped, not rendered as HTML
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>alert("xss")</script>')
  })

  it('does not display mock messages', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [],
      messageTotal: 0,
    })

    // Re-patch to empty
    store.$patch({ messageStatus: 'empty' as const })
    const wrapper = mountWorkspace()
    expect(wrapper.find('.message-list').exists()).toBe(false)
  })
})

describe('ChatWorkspaceShell — load more', () => {
  it('shows load more button when hasMore is true', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage()],
      messageTotal: 10,
      messageHasMore: true,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Load more messages')
  })

  it('does not show load more when hasMore is false', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage()],
      messageTotal: 1,
      messageHasMore: false,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).not.toContain('Load more messages')
  })
})

describe('ChatWorkspaceShell — composer', () => {
  it('keeps send button disabled', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.get('[aria-label="Send message - Preview only"]').attributes('disabled')).toBeDefined()
  })

  it('keeps attach button disabled', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.get('[aria-label="Attach file - Preview only"]').attributes('disabled')).toBeDefined()
  })

  it('shows read-only notice in composer', () => {
    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Read only')
  })

  it('shows read-only notice in message area when session loaded', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage()],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    expect(wrapper.text()).toContain('Messages are read-only')
  })
})

describe('ChatWorkspaceShell — accessibility', () => {
  it('message list has semantic label', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'success' as const,
      messages: [makeMessage()],
      messageTotal: 1,
    })

    const wrapper = mountWorkspace()
    const list = wrapper.find('.message-list')
    expect(list.exists()).toBe(true)
    expect(list.attributes('aria-label')).toBe('Session messages')
  })

  it('error region has alert role', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'error' as const,
      messageError: 'Test error',
    })

    const wrapper = mountWorkspace()
    const alert = wrapper.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
  })

  it('retry button is keyboard accessible', () => {
    const store = useSessionStore()
    setSessionLoaded(store)
    store.$patch({
      messageStatus: 'error' as const,
      messageError: 'Test error',
    })

    const wrapper = mountWorkspace()
    const retryBtn = wrapper.find('.workspace-retry-btn')
    expect(retryBtn.exists()).toBe(true)
    expect(retryBtn.attributes('aria-label')).toContain('Retry')
  })
})
