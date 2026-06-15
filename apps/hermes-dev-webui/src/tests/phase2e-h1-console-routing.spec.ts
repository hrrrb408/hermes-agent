/**
 * Phase 2E-H1 — Lens 1: Console Routing / Navigation State Boundary.
 *
 * Hardens the routing + navigation-state invariants of the unified developer
 * console: the additive `/#/console` route, the unchanged `/#/` workbench,
 * the nav rail tablist (roving tabindex + Arrow/Home/End), section persistence
 * + restore, invalid-section fallback, and the KeepAlive dynamic-component
 * fallback. No backend, no production access.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/toolPolicy', () => ({ fetchToolPolicyStatus: vi.fn(), fetchToolCatalog: vi.fn() }))
vi.mock('@/api/toolAudit', () => ({ getAuditEvents: vi.fn(), getAuditEventsV2: vi.fn() }))
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({ runWritePreview: vi.fn(), executeWrite: vi.fn(), runRollbackPreview: vi.fn(), executeRollback: vi.fn() }))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn() }))

import App from '@/App.vue'
import { routes } from '@/router'
import DevConsoleNav from '@/components/devconsole/DevConsoleNav.vue'
import DevConsoleLayout from '@/components/devconsole/DevConsoleLayout.vue'
import { useDevConsoleNavStore, CONSOLE_SECTIONS } from '@/stores/devConsoleNav'

async function mountAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router] } })
  return { router, wrapper }
}

describe('Lens 1 — Console routing / navigation state (Phase 2E-H1)', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('exposes the additive /console route and preserves the / workbench', async () => {
    const consoleMount = await mountAt('/console')
    expect(consoleMount.wrapper.find('.devconsole').exists()).toBe(true)

    const workbench = await mountAt('/')
    expect(workbench.wrapper.find('.workspace-page').exists()).toBe(true)
  })

  it('redirects unknown routes to the workbench (never to the console)', async () => {
    const { router, wrapper } = await mountAt('/totally-unknown')
    expect(router.currentRoute.value.path).toBe('/')
    expect(wrapper.find('.workspace-page').exists()).toBe(true)
    expect(wrapper.find('.devconsole').exists()).toBe(false)
  })

  it('the console nav is a vertical tablist with roving tabindex (active tab in tab order)', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav)
    const tablist = wrapper.find('[role="tablist"]')
    expect(tablist.exists()).toBe(true)
    expect(tablist.attributes('aria-orientation')).toBe('vertical')

    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.length).toBe(CONSOLE_SECTIONS.length)
    const active = tabs.find((t) => t.attributes('aria-selected') === 'true')
    expect(active?.attributes('tabindex')).toBe('0')
    // All non-active tabs are removed from the tab order (roving).
    for (const t of tabs) {
      if (t.attributes('aria-selected') !== 'true') {
        expect(t.attributes('tabindex')).toBe('-1')
      }
    }
  })

  it('ArrowUp/ArrowDown/ArrowLeft/ArrowRight move selection along the rail', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    expect(nav.activeSection).toBe('overview')
    const wrapper = mount(DevConsoleNav, { attachTo: document.body })

    await wrapper.find('#devconsole-nav-overview').trigger('keydown', { key: 'ArrowDown' })
    expect(nav.activeSection).toBe('tools')
    await wrapper.find('#devconsole-nav-tools').trigger('keydown', { key: 'ArrowRight' })
    expect(nav.activeSection).toBe('provider')
    await wrapper.find('#devconsole-nav-provider').trigger('keydown', { key: 'ArrowUp' })
    expect(nav.activeSection).toBe('tools')
    await wrapper.find('#devconsole-nav-tools').trigger('keydown', { key: 'ArrowLeft' })
    expect(nav.activeSection).toBe('overview')
  })

  it('Home / End jump to the first / last section and wrap-around works', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav, { attachTo: document.body })

    await wrapper.find('#devconsole-nav-overview').trigger('keydown', { key: 'End' })
    expect(nav.activeSection).toBe('diagnostics')
    await wrapper.find('#devconsole-nav-diagnostics').trigger('keydown', { key: 'Home' })
    expect(nav.activeSection).toBe('overview')
    // Wrap-around: ArrowDown on the last item returns to the first.
    await wrapper.find('#devconsole-nav-overview').trigger('keydown', { key: 'End' })
    await wrapper.find('#devconsole-nav-diagnostics').trigger('keydown', { key: 'ArrowDown' })
    expect(nav.activeSection).toBe('overview')
  })

  it('persists the active section and restores it across store re-init', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    nav.setSection('audit')
    expect(window.localStorage.getItem('hermes-dev-webui.devconsole.section')).toBe('audit')

    const nav2 = useDevConsoleNavStore()
    nav2.initializeNavState()
    expect(nav2.activeSection).toBe('audit')
  })

  it('falls back to overview for an invalid persisted section (no stale state)', () => {
    window.localStorage.setItem('hermes-dev-webui.devconsole.section', 'bogus-section')
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    expect(nav.activeSection).toBe('overview')
  })

  it('the layout resolves an unknown active section to the Overview (safe dynamic-component fallback)', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    // Force an invalid value past the type system to exercise the computed fallback.
    ;(nav as unknown as { activeSection: string }).activeSection = 'nope'
    // DevConsoleLayout renders a <RouterLink> + ThemeSwitcher in the top bar;
    // stub them so the mount does not require a router/global plugin context.
    const wrapper = mount(DevConsoleLayout, {
      global: { stubs: ['RouterLink', 'ThemeSwitcher'] },
    })
    // The fallback component is OverviewSection, which renders the Overview heading.
    expect(wrapper.find('[aria-label="Overview"]').exists()).toBe(true)
  })

  it('every nav item has an accessible name (icon aria-hidden + visible label)', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav)
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.length).toBeGreaterThan(0)
    for (const tab of tabs) {
      // Visible label text is present…
      expect(tab.text().trim().length).toBeGreaterThan(0)
      // …and any decorative icon is hidden from assistive tech.
      for (const svg of tab.findAll('svg')) {
        expect(svg.attributes('aria-hidden')).toBe('true')
      }
    }
  })
})
