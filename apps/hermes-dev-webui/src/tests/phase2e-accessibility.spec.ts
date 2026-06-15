/**
 * Phase 2E — accessibility + keyboard + no-leak smoke tests.
 *
 * Asserts the dev console nav rail is a keyboard-operable tablist (roving
 * tabindex + Arrow/Home/End), and that no console section surfaces an API-key,
 * shell-command, raw-token, full-hash, secret, callable-repr, or production-path
 * affordance.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolPolicy', () => ({ fetchToolPolicyStatus: vi.fn(), fetchToolCatalog: vi.fn() }))
vi.mock('@/api/toolAudit', () => ({ getAuditEvents: vi.fn(), getAuditEventsV2: vi.fn() }))
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({ runWritePreview: vi.fn(), executeWrite: vi.fn(), runRollbackPreview: vi.fn(), executeRollback: vi.fn() }))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn() }))

import DevConsoleNav from '@/components/devconsole/DevConsoleNav.vue'
import OverviewSection from '@/components/devconsole/OverviewSection.vue'
import SafetySection from '@/components/devconsole/SafetySection.vue'
import DiagnosticsSection from '@/components/devconsole/DiagnosticsSection.vue'
import ToolExecutionSection from '@/components/devconsole/ToolExecutionSection.vue'
import ProviderSection from '@/components/devconsole/ProviderSection.vue'
import WriteRollbackSection from '@/components/devconsole/WriteRollbackSection.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

describe('Dev Console accessibility (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the nav as a keyboard-operable tablist with roving tabindex', () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav)
    const tablist = wrapper.find('[role="tablist"]')
    expect(tablist.exists()).toBe(true)
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.length).toBe(8)
    // Active (overview) is in the tab order; others are not.
    const active = tabs.find((t) => t.attributes('aria-selected') === 'true')
    expect(active?.attributes('tabindex')).toBe('0')
  })

  it('ArrowDown moves selection down the rail', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    expect(nav.activeSection).toBe('overview')
    const wrapper = mount(DevConsoleNav, { attachTo: document.body })
    const overview = wrapper.find('#devconsole-nav-overview')
    await overview.trigger('keydown', { key: 'ArrowDown' })
    expect(nav.activeSection).toBe('tools')
  })

  it('Home / End jump to the first / last section', async () => {
    const nav = useDevConsoleNavStore()
    nav.initializeNavState()
    const wrapper = mount(DevConsoleNav, { attachTo: document.body })
    await wrapper.find('#devconsole-nav-overview').trigger('keydown', { key: 'End' })
    expect(nav.activeSection).toBe('diagnostics')
    await wrapper.find('#devconsole-nav-diagnostics').trigger('keydown', { key: 'Home' })
    expect(nav.activeSection).toBe('overview')
  })

  it('no section renders an API-key / shell-command / password input', () => {
    const sections = [
      OverviewSection,
      SafetySection,
      DiagnosticsSection,
      ToolExecutionSection,
      ProviderSection,
      WriteRollbackSection,
    ]
    for (const Section of sections) {
      const wrapper = mount(Section)
      expect(wrapper.findAll('input[type="password"]').length, `${Section.name}`).toBe(0)
      expect(wrapper.html(), `${Section.name}`).not.toMatch(/api[_-]?key\s*input|shell[_-]?command|data-shell-input/i)
    }
  })

  it('no section surfaces raw tokens / full hashes / callable reprs / production path', () => {
    const sections = [OverviewSection, SafetySection, DiagnosticsSection]
    for (const Section of sections) {
      const wrapper = mount(Section)
      const html = wrapper.html()
      expect(html, `${Section.name}`).not.toMatch(/sk-[A-Za-z0-9_-]{16,}/)
      expect(html, `${Section.name}`).not.toMatch(/Bearer /)
      expect(html, `${Section.name}`).not.toMatch(/<function|object at 0x/)
      expect(html, `${Section.name}`).not.toMatch(/rawArguments|fullTokenHash|plainToken|tokenSecret/)
      expect(wrapper.text(), `${Section.name}`).not.toContain('/Users/huangruibang/.hermes')
    }
  })
})
