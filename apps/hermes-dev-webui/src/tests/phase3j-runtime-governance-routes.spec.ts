/**
 * Phase 3J — Runtime Governance route-governance tests (frontend).
 *
 * Asserts the Runtime Governance surface is a client-side DevConsole SECTION
 * inside the existing /console view — NOT a new SPA route and NOT a new backend
 * route. The SPA router still exposes exactly the three pre-existing views
 * (workspace / console / theme-lab) plus the catch-all redirect. No
 * /runtime-governance, /dev-runtime, or /plugins/runtime-governance route was
 * added.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import { routes, router } from '@/router'
import { CONSOLE_SECTIONS, CONSOLE_SECTION_LABELS, useDevConsoleNavStore } from '@/stores/devConsoleNav'
import RuntimeGovernanceSection from '@/components/devconsole/RuntimeGovernanceSection.vue'

describe('Runtime Governance route governance (Phase 3J)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the SPA router still has exactly three named views + one catch-all redirect', () => {
    const realRoutes = routes.filter((r) => !String(r.path).includes(':pathMatch'))
    expect(realRoutes).toHaveLength(3)
    const names = realRoutes.map((r) => r.name)
    expect(names).toEqual(expect.arrayContaining(['workspace', 'dev-console', 'theme-lab']))
  })

  it('no SPA route named or shaped for runtime governance was added', () => {
    for (const r of routes) {
      const path = String(r.name ?? '') + ' ' + String(r.path ?? '')
      expect(path).not.toMatch(/runtime[-_]?governance/i)
      expect(path).not.toMatch(/dev-runtime/i)
      expect(path.toLowerCase()).not.toContain('/plugins/runtime-governance')
    }
  })

  it('Runtime Governance is a first-class DevConsole section, not a route', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('runtimeGovernance')).toBe(true)
    expect(CONSOLE_SECTION_LABELS.runtimeGovernance).toBe('Runtime Governance')
  })

  it('the nav store can activate the runtime governance section (no route change)', async () => {
    const nav = useDevConsoleNavStore()
    const before = router.currentRoute.value.name
    nav.setSection('runtimeGovernance')
    expect(nav.activeSection).toBe('runtimeGovernance')
    // Activating a section does NOT touch the SPA router.
    expect(router.currentRoute.value.name).toBe(before)
  })

  it('the Runtime Governance section renders inside the console view graph', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.find('[data-testid="runtime-governance-section"]').exists()).toBe(true)
    // It carries the read-only + no-new-route boundary language.
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('read-only')
    expect(text).toContain('no backend route was added')
  })
})
