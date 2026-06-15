/**
 * Phase 2E-H1 — Lens 6: Accessibility / Keyboard / Responsive Boundary.
 *
 * Hardens the practical a11y baseline of the unified console (not full WCAG —
 * that remains a deferred P2): the vertical tablist semantics, roving tabindex
 * + Arrow/Home/End keyboard nav, focus-visible affordance, status
 * announcements (role=status / role=alert / aria-busy), non-color badge
 * redundancy, and the 820px responsive collapse. No backend, no production.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// Vitest runs with cwd = the dev-webui package root, so the stylesheet path is
// deterministic. (import.meta.url is not a file: URL under vitest's transform.)
const DEVCONSOLE_CSS = resolve(process.cwd(), 'src/styles/devconsole.css')

vi.mock('@/api/toolPolicy', () => ({ fetchToolPolicyStatus: vi.fn(), fetchToolCatalog: vi.fn() }))
vi.mock('@/api/toolAudit', () => ({ getAuditEvents: vi.fn(), getAuditEventsV2: vi.fn() }))
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({ runWritePreview: vi.fn(), executeWrite: vi.fn(), runRollbackPreview: vi.fn(), executeRollback: vi.fn() }))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn() }))

import DevConsoleNav from '@/components/devconsole/DevConsoleNav.vue'
import OverviewSection from '@/components/devconsole/OverviewSection.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BlockedReasonPanel from '@/components/common/BlockedReasonPanel.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

describe('Lens 6 — Accessibility / keyboard / responsive (Phase 2E-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the nav rail is a labelled vertical tablist with one tab per section', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav)
    const tablist = wrapper.find('[role="tablist"]')
    expect(tablist.exists()).toBe(true)
    expect(tablist.attributes('aria-orientation')).toBe('vertical')
    expect(wrapper.attributes('aria-label')).toBeTruthy()
    expect(wrapper.findAll('[role="tab"]').length).toBe(8)
  })

  it('exactly one tab is in the tab order (roving tabindex) and it is aria-selected', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav)
    const tabs = wrapper.findAll('[role="tab"]')
    const inOrder = tabs.filter((t) => t.attributes('tabindex') === '0')
    expect(inOrder.length).toBe(1)
    expect(inOrder[0]!.attributes('aria-selected')).toBe('true')
  })

  it('ArrowDown moves selection AND focus to the next tab', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav, { attachTo: document.body })
    await wrapper.find('#devconsole-nav-overview').trigger('keydown', { key: 'ArrowDown' })
    expect(nav.activeSection).toBe('tools')
    expect(document.activeElement?.id).toBe('devconsole-nav-tools')
  })

  it('LoadingState announces via role=status + aria-busy, ErrorState via role=alert', () => {
    const loading = mount(LoadingState, { props: { message: 'Loading…' } })
    expect(loading.attributes('role')).toBe('status')
    expect(loading.attributes('aria-busy')).toBe('true')

    const error = mount(ErrorState, { props: { message: 'Failed' } })
    expect(error.attributes('role')).toBe('alert')
  })

  it('ErrorState emits retry and EmptyState renders a hint', async () => {
    const error = mount(ErrorState, { props: { message: 'Failed' } })
    await error.find('[data-testid="dev-error-retry"]').trigger('click')
    expect(error.emitted('retry')).toBeTruthy()

    const empty = mount(EmptyState, { props: { message: 'No events', hint: 'Run a tool first' } })
    expect(empty.attributes('data-testid')).toBe('dev-empty-state')
    expect(empty.text()).toContain('Run a tool first')
  })

  it('BlockedReasonPanel conveys severity by TEXT, not color alone (non-color redundancy)', () => {
    const wrapper = mount(BlockedReasonPanel, { props: { code: 'blocked_write_path_traversal' } })
    expect(wrapper.attributes('role')).toBe('alert')
    // The severity word is rendered as text in addition to the data-severity tone.
    expect(wrapper.find('[data-severity="danger"]').exists()).toBe(true)
    expect(wrapper.text()).toMatch(/Blocked/)
  })

  it('safety badges carry visible text labels (status is not conveyed by color alone)', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    // SafetyBadgeBar is rendered inside OverviewSection; mount the overview to
    // inspect the rendered badge text labels.
    const wrapper = mount(OverviewSection)
    const badges = wrapper.findAll('[data-testid="dev-safety-badges"] .devconsole-badge')
    expect(badges.length).toBeGreaterThan(0)
    for (const b of badges) {
      expect(b.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('the devconsole stylesheet defines a responsive collapse at the 820px breakpoint', () => {
    const css = readFileSync(DEVCONSOLE_CSS, 'utf8')
    // The two-pane body collapses to a single column under 820px.
    expect(css).toMatch(/@media\s*\(max-width:\s*820px\)/)
    // The content area / pre blocks scroll horizontally rather than overflowing the page.
    expect(css).toMatch(/overflow-y:\s*auto/)
  })

  it('the nav rail exposes a focus-visible style (keyboard focus is visible)', () => {
    const css = readFileSync(DEVCONSOLE_CSS, 'utf8')
    expect(css).toMatch(/devconsole-nav__item:focus-visible/)
  })
})
