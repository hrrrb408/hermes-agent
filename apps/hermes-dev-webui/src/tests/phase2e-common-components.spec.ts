/**
 * Phase 2E reusable common-component tests.
 *
 * Covers LoadingState / EmptyState / ErrorState / BlockedReasonPanel /
 * AuditIdLink — the unified state + cross-navigation surface used across the
 * dev console sections.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import LoadingState from '@/components/common/LoadingState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import BlockedReasonPanel from '@/components/common/BlockedReasonPanel.vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'

describe('LoadingState', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders an accessible aria-busy loading region with text', () => {
    const wrapper = mount(LoadingState, { props: { message: 'Loading audit store…' } })
    expect(wrapper.find('[data-testid="dev-loading-state"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Loading audit store…')
    expect(wrapper.attributes('aria-busy')).toBe('true')
    expect(wrapper.attributes('role')).toBe('status')
  })

  it('defaults to a Loading… message', () => {
    const wrapper = mount(LoadingState)
    expect(wrapper.text()).toContain('Loading')
  })
})

describe('EmptyState', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders the message and optional hint', () => {
    const wrapper = mount(EmptyState, { props: { message: 'No audit events yet.', hint: 'Run a read-only tool to generate one.' } })
    expect(wrapper.find('[data-testid="dev-empty-state"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('No audit events yet.')
    expect(wrapper.text()).toContain('Run a read-only tool')
  })
})

describe('ErrorState', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders an alert with the message', () => {
    const wrapper = mount(ErrorState, { props: { message: 'Failed to load policy.' } })
    expect(wrapper.attributes('role')).toBe('alert')
    expect(wrapper.text()).toContain('Failed to load policy.')
  })

  it('emits retry when the retry button is clicked', async () => {
    const wrapper = mount(ErrorState, { props: { message: 'boom' } })
    await wrapper.find('[data-testid="dev-error-retry"]').trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
    expect(wrapper.emitted('retry')!.length).toBe(1)
  })
})

describe('BlockedReasonPanel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders a known code with explanation + safe next action', () => {
    const wrapper = mount(BlockedReasonPanel, { props: { code: 'blocked_write_path_traversal' } })
    expect(wrapper.find('[data-testid="dev-blocked-reason"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Path traversal rejected')
    expect(wrapper.text()).toContain('blocked_write_path_traversal')
    expect(wrapper.text()).toContain('Next safe action')
    // danger tone surfaces for traversal
    expect(wrapper.find('[data-severity="danger"]').exists()).toBe(true)
  })

  it('renders a safe fallback for unknown codes without throwing', () => {
    const wrapper = mount(BlockedReasonPanel, { props: { code: 'blocked_some_future_xyz' } })
    expect(wrapper.find('[data-testid="dev-blocked-reason"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Blocked for safety')
    // must never instruct bypass
    expect(wrapper.text()).not.toMatch(/^\s*bypass/i)
  })

  it('renders a safe fallback for empty/null codes', () => {
    const wrapper = mount(BlockedReasonPanel, { props: { code: null } })
    expect(wrapper.find('[data-testid="dev-blocked-reason-code"]').text()).toBe('unknown_blocked_reason')
  })
})

describe('AuditIdLink', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders a lossy chip and emits the full id on click', async () => {
    const fullId = 'pexa_' + 'a'.repeat(40)
    const wrapper = mount(AuditIdLink, { props: { id: fullId, label: 'audit' } })
    const chip = wrapper.find('[data-testid="dev-audit-id-link"]')
    expect(chip.exists()).toBe(true)
    // displayed value is truncated, not the full id
    expect(chip.text()).toContain('…')
    expect(chip.text()).not.toContain('a'.repeat(40))
    await chip.trigger('click')
    expect(wrapper.emitted('navigate')).toBeTruthy()
    expect(wrapper.emitted('navigate')![0]).toEqual([fullId])
  })

  it('renders nothing for a null/empty id', () => {
    const wrapper = mount(AuditIdLink, { props: { id: null } })
    expect(wrapper.find('[data-testid="dev-audit-id-link"]').exists()).toBe(false)
  })
})
