/**
 * Phase 4A — Target B Readiness route-governance tests (frontend).
 *
 * Asserts the Target B Readiness region is a read-only client-side region
 * inside the existing Governance Hub DevConsole section — NOT a new SPA route
 * and NOT a new backend route. The SPA router still exposes exactly the three
 * pre-existing views (workspace / console / theme-lab) plus the catch-all
 * redirect. No /target-b, /readiness, or /scaffold route was added. The section
 * registry is unchanged (Target B lives inside Governance Hub). Cross-link
 * navigation from the Target B region stays a client-side section switch (no SPA
 * / backend route change).
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

describe('Target B Readiness route governance (Phase 4A)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the SPA router still has exactly three named views + one catch-all redirect (route count unchanged)', () => {
    const realRoutes = routes.filter((r) => !String(r.path).includes(':pathMatch'))
    expect(realRoutes).toHaveLength(3)
    const names = realRoutes.map((r) => r.name)
    expect(names).toEqual(expect.arrayContaining(['workspace', 'dev-console', 'theme-lab']))
  })

  it('no SPA route named or shaped for target b / readiness / scaffold was added', () => {
    for (const r of routes) {
      const path = String(r.name ?? '') + ' ' + String(r.path ?? '')
      expect(path).not.toMatch(/target[-_]?b/i)
      expect(path).not.toMatch(/readiness/i)
      expect(path).not.toMatch(/scaffold/i)
      expect(path).not.toMatch(/production[-_]?runtime/i)
    }
  })

  it('Governance Hub remains a first-class DevConsole section; no new section was added', () => {
    // The section registry is unchanged — Target B lives INSIDE the Governance Hub.
    expect(CONSOLE_SECTIONS).toEqual([
      'overview',
      'tools',
      'provider',
      'write',
      'audit',
      'safety',
      'workflow',
      'capabilities',
      'plugins',
      'runtimeGovernance',
      'humanReview',
      'governanceHub',
      'diagnostics',
    ])
    expect(CONSOLE_SECTION_LABELS.governanceHub).toBe('Governance Hub')
  })

  it('Runtime Governance and Human Review remain intact as sections', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('runtimeGovernance')).toBe(true)
    expect((CONSOLE_SECTIONS as readonly string[]).includes('humanReview')).toBe(true)
  })

  it('activating the governance hub section does NOT touch the SPA router', () => {
    const nav = useDevConsoleNavStore()
    const before = router.currentRoute.value.name
    nav.setSection('governanceHub')
    expect(nav.activeSection).toBe('governanceHub')
    expect(router.currentRoute.value.name).toBe(before)
  })

  it('the Target B region renders inside the Governance Hub section graph', () => {
    const wrapper = mount(GovernanceHubSection)
    expect(wrapper.find('[data-testid="governance-hub-target-b-region"]').exists()).toBe(true)
    const text = wrapper.find('[data-testid="governance-hub-target-b-region"]').text()
    expect(text).toContain('Target B')
    expect(text).toContain('SCAFFOLD')
  })

  it('Runtime Governance and Human Review sections still render intact (regression preserved)', () => {
    expect(mount(RuntimeGovernanceSection).find('[data-testid="runtime-governance-section"]').exists()).toBe(true)
    expect(mount(HumanReviewGovernanceSection).find('[data-testid="human-review-governance-section"]').exists()).toBe(true)
  })

  it('cross-link navigation from the Target B region stays a client-side section switch', async () => {
    const nav = useDevConsoleNavStore()
    const before = router.currentRoute.value.name
    nav.setSection('governanceHub')
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-target-b-view-runtime-governance"]').trigger('click')
    expect(nav.activeSection).toBe('runtimeGovernance')
    await wrapper.find('[data-testid="governance-hub-target-b-view-human-review"]').trigger('click')
    expect(nav.activeSection).toBe('humanReview')
    // No SPA router change at any point.
    expect(router.currentRoute.value.name).toBe(before)
  })
})
