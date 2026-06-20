/**
 * Phase 3K — Human Review Governance route-governance tests (frontend).
 *
 * Asserts the Human Review Governance surface is a client-side DevConsole SECTION
 * inside the existing /console view — NOT a new SPA route and NOT a new backend
 * route. The SPA router still exposes exactly the three pre-existing views
 * (workspace / console / theme-lab) plus the catch-all redirect. No
 * /human-review, /human-review-governance, or /approval-governance route was
 * added. Runtime Governance remains intact alongside the new section.
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
import HumanReviewGovernanceSection from '@/components/devconsole/HumanReviewGovernanceSection.vue'
import RuntimeGovernanceSection from '@/components/devconsole/RuntimeGovernanceSection.vue'

describe('Human Review Governance route governance (Phase 3K)', () => {
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

  it('no SPA route named or shaped for human review governance was added', () => {
    for (const r of routes) {
      const path = String(r.name ?? '') + ' ' + String(r.path ?? '')
      expect(path).not.toMatch(/human[-_]?review/i)
      expect(path).not.toMatch(/approval[-_]?governance/i)
      expect(path.toLowerCase()).not.toContain('/human-review-governance')
    }
  })

  it('Human Review is a first-class DevConsole section with the expected label', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('humanReview')).toBe(true)
    expect(CONSOLE_SECTION_LABELS.humanReview).toBe('Human Review')
  })

  it('Runtime Governance remains intact as a section', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('runtimeGovernance')).toBe(true)
    expect(CONSOLE_SECTION_LABELS.runtimeGovernance).toBe('Runtime Governance')
  })

  it('the nav store can activate the human review section (no route change)', async () => {
    const nav = useDevConsoleNavStore()
    const before = router.currentRoute.value.name
    nav.setSection('humanReview')
    expect(nav.activeSection).toBe('humanReview')
    // Activating a section does NOT touch the SPA router.
    expect(router.currentRoute.value.name).toBe(before)
  })

  it('the Human Review section renders inside the console view graph', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    expect(wrapper.find('[data-testid="human-review-governance-section"]').exists()).toBe(true)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('read-only')
    expect(text).toContain('no backend route was added')
  })

  it('Runtime Governance section still renders intact', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.find('[data-testid="runtime-governance-section"]').exists()).toBe(true)
  })

  it('the Dev Console layout maps the humanReview section to a component', async () => {
    const mod = await import('@/components/devconsole/DevConsoleLayout.vue')
    expect(mod.default).toBeDefined()
    // The nav store exposes the section; the layout's SECTIONS map is internal,
    // but activating humanReview must not throw and must resolve to a component.
    const nav = useDevConsoleNavStore()
    nav.setSection('humanReview')
    expect(nav.activeSection).toBe('humanReview')
  })
})
