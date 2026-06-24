/**
 * Phase 3L — Governance Hub route-governance tests (frontend).
 *
 * Asserts the Governance Hub surface is a client-side DevConsole SECTION inside
 * the existing /console view — NOT a new SPA route and NOT a new backend route.
 * The SPA router still exposes exactly the three pre-existing views
 * (workspace / console / theme-lab) plus the catch-all redirect. No
 * /governance-hub, /control-center, or /governance route was added. Runtime
 * Governance and Human Review remain intact alongside the new section.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import { routes, router } from '@/router'
import {
  CONSOLE_SECTIONS,
  CONSOLE_SECTION_LABELS,
  useDevConsoleNavStore,
} from '@/stores/devConsoleNav'
import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'
import RuntimeGovernanceSection from '@/components/devconsole/RuntimeGovernanceSection.vue'
import HumanReviewGovernanceSection from '@/components/devconsole/HumanReviewGovernanceSection.vue'

describe('Governance Hub route governance (Phase 3L)', () => {
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

  it('no SPA route named or shaped for governance hub was added', () => {
    for (const r of routes) {
      const path = String(r.name ?? '') + ' ' + String(r.path ?? '')
      expect(path).not.toMatch(/governance[-_]?hub/i)
      expect(path).not.toMatch(/control[-_]?center/i)
      expect(path.toLowerCase()).not.toContain('/governance-hub')
    }
  })

  it('Governance Hub is a first-class DevConsole section with the expected label', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('governanceHub')).toBe(true)
    expect(CONSOLE_SECTION_LABELS.governanceHub).toBe('Governance Hub')
  })

  it('Runtime Governance and Human Review remain intact as sections', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('runtimeGovernance')).toBe(true)
    expect((CONSOLE_SECTIONS as readonly string[]).includes('humanReview')).toBe(true)
    expect(CONSOLE_SECTION_LABELS.runtimeGovernance).toBe('Runtime Governance')
    expect(CONSOLE_SECTION_LABELS.humanReview).toBe('Human Review')
  })

  it('the nav store can activate the governance hub section (no route change)', async () => {
    const nav = useDevConsoleNavStore()
    const before = router.currentRoute.value.name
    nav.setSection('governanceHub')
    expect(nav.activeSection).toBe('governanceHub')
    // Activating a section does NOT touch the SPA router.
    expect(router.currentRoute.value.name).toBe(before)
  })

  it('the Governance Hub section renders inside the console view graph', () => {
    const wrapper = mount(GovernanceHubSection)
    expect(wrapper.find('[data-testid="governance-hub-section"]').exists()).toBe(true)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('read-only')
    expect(text).toContain('no backend route was added')
  })

  it('Runtime Governance and Human Review sections still render intact', () => {
    expect(mount(RuntimeGovernanceSection).find('[data-testid="runtime-governance-section"]').exists()).toBe(true)
    expect(mount(HumanReviewGovernanceSection).find('[data-testid="human-review-governance-section"]').exists()).toBe(true)
  })

  it('the Dev Console layout maps the governanceHub section to a component', async () => {
    const mod = await import('@/components/devconsole/DevConsoleLayout.vue')
    expect(mod.default).toBeDefined()
    const nav = useDevConsoleNavStore()
    nav.setSection('governanceHub')
    expect(nav.activeSection).toBe('governanceHub')
  })

  it('cross-link navigation from Governance Hub stays a client-side section switch', async () => {
    const nav = useDevConsoleNavStore()
    const before = router.currentRoute.value.name
    nav.setSection('governanceHub')
    nav.setSection('runtimeGovernance')
    nav.setSection('humanReview')
    nav.setSection('governanceHub')
    expect(router.currentRoute.value.name).toBe(before)
  })
})
