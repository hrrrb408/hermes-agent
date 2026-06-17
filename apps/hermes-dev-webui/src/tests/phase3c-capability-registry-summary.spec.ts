/**
 * Phase 3C — Capability Registry summary tests.
 *
 * Asserts the summary renders counts + frozen policy flags
 * (dynamicLoadingAllowed=false, remoteRegistryAllowed=false,
 * marketplaceAllowed=false, productionAllowed=false, devOnly=true) and the
 * route-governance baseline string.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import CapabilityRegistrySummary from '@/components/devconsole/CapabilityRegistrySummary.vue'
import type { CapabilityRegistrySummary as Summary } from '@/types/api/capabilityRegistry'

function makeSummary(overrides: Partial<Summary> = {}): Summary {
  return {
    status: 'enabled',
    registryVersion: 'phase3c-static-v1',
    loaded: true,
    validationPassed: true,
    capabilityCount: 46,
    enabledCount: 25,
    disabledCount: 2,
    blockedCount: 19,
    plannedCount: 0,
    deprecatedCount: 0,
    permissionClassCounts: { READ_ONLY: 20, ADMIN_FORBIDDEN: 12 },
    trustLevelCounts: { BUILTIN_VERIFIED: 25 },
    categoryCounts: { tool: 10, registry: 14 },
    devOnly: true,
    productionAllowed: false,
    dynamicLoadingAllowed: false,
    remoteRegistryAllowed: false,
    marketplaceAllowed: false,
    routeGovernanceExpected: '34/34/5/0/1/1',
    validation: { valid: true, errorCount: 0, warningCount: 0 },
    redactionApplied: true,
    ...overrides,
  }
}

describe('CapabilityRegistrySummary (Phase 3C)', () => {
  it('renders capability count and status', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    const text = wrapper.text()
    expect(text).toContain('46')
    expect(text).toContain('enabled')
    expect(text).toContain('phase3c-static-v1')
  })

  it('renders the route-governance baseline 34/34/5/0/1/1', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    expect(wrapper.text()).toContain('34/34/5/0/1/1')
  })

  it('renders frozen policy flags as no/yes', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    const flags = wrapper.find('[data-testid="capability-frozen-flags"]').text()
    expect(flags).toContain('Dev-only')
    expect(flags).toContain('Production allowed')
    expect(flags).toContain('Dynamic loading')
    expect(flags).toContain('Remote registry')
    expect(flags).toContain('Marketplace')
    // Frozen: dynamic loading / remote / marketplace / production = no; dev-only = yes
    expect(flags.toLowerCase()).toContain('dynamic loading:no')
    expect(flags.toLowerCase()).toContain('remote registry:no')
    expect(flags.toLowerCase()).toContain('marketplace:no')
    expect(flags.toLowerCase()).toContain('production allowed:no')
    expect(flags.toLowerCase()).toContain('dev-only:yes')
  })

  it('renders permission/trust/category counts', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    const text = wrapper.text()
    expect(text).toContain('READ_ONLY: 20')
    expect(text).toContain('BUILTIN_VERIFIED: 25')
    expect(text).toContain('tool: 10')
  })

  it('renders gracefully when summary is null', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: null } })
    const text = wrapper.text()
    expect(text).toContain('Registry status')
    // Frozen flags still render (they are constants).
    expect(text.toLowerCase()).toContain('dynamic loading:no')
  })
})
