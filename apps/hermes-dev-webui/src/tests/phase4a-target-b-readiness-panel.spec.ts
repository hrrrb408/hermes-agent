/**
 * Phase 4A — Target B Readiness region rendering tests.
 *
 * Mounts the Governance Hub and asserts the Target B Readiness region renders
 * the full disabled-scaffold picture read-only: the readiness banner, summary
 * cards, the 16 architecture modules, the plugin package schema preview, the
 * permission model matrix, the registry protocol preview, the WebUI execution
 * preview (disabled flow, NO execute / run button), the approval gate, the
 * enablement blockers, the Target A relationship, and the readiness checklist.
 * Also covers accessibility (headings, labelled regions, captions) and that
 * every authorization verdict stays NO-GO / disabled.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

function findRegion(wrapper: ReturnType<typeof mount>) {
  return wrapper.find('[data-testid="governance-hub-target-b-region"]')
}

describe('Target B Readiness region (Phase 4A) — banner + summary', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders the region with a heading and the SCAFFOLD_READY verdict', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    expect(region.exists()).toBe(true)
    expect(region.find('[data-testid="governance-hub-target-b-heading"]').text()).toContain('Target B')
    const banner = region.find('[data-testid="governance-hub-target-b-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.find('[data-target-b-verdict="SCAFFOLD_READY"]').text()).toContain('SCAFFOLD')
  })

  it('the status banner shows the required disabled / NO-GO lines', () => {
    const wrapper = mount(GovernanceHubSection)
    const lines = findRegion(wrapper)
      .find('[data-testid="governance-hub-target-b-banner-lines"]')
      .text()
    expect(lines).toContain('Target B readiness scaffold')
    expect(lines).toContain('Execution disabled')
    expect(lines).toContain('Production runtime NO-GO')
    expect(lines).toContain('Registry disabled')
    expect(lines).toContain('Marketplace disabled')
    expect(lines).toContain('WebUI execute disabled')
    expect(lines).toContain('Approval required')
  })

  it('renders the summary cards with frozen NO-GO / disabled verdicts', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper).text()
    expect(text).toContain('Execution')
    expect(text).toContain('Production runtime')
    expect(text).toContain('Remote registry')
    expect(text).toContain('Marketplace')
    expect(text).toContain('WebUI execution')
    expect(text).toContain('Approval / authorization')
    expect(text).toContain('Production rollout')
  })
})

describe('Target B Readiness region — architecture modules', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the required architecture modules', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper)
      .find('[data-testid="governance-hub-target-b-architecture-table"]')
      .text()
    for (const module of [
      'Plugin Package Format',
      'Plugin Signature Verification',
      'Plugin Permission Model',
      'Remote Registry Protocol',
      'Runtime Sandbox Boundary',
      'Execution Broker',
      'WebUI Execution Request Flow',
      'Approval / Authorization Gate',
      'Audit Trail',
      'Rollback / Kill Switch',
      'Secret Handling Boundary',
      'Network Policy',
      'Production Rollout Plan',
    ]) {
      expect(text, `missing module ${module}`).toContain(module)
    }
  })

  it('every module row is disabled / non-executing / non-networking / non-production', () => {
    const wrapper = mount(GovernanceHubSection)
    const rows = findRegion(wrapper).findAll(
      '[data-testid="governance-hub-target-b-architecture-table"] tbody tr[data-module-key]',
    )
    expect(rows.length).toBeGreaterThanOrEqual(16)
    for (const row of rows) {
      expect(row.find('[data-enabled="false"]').exists()).toBe(true)
      expect(row.find('[data-execution-capable="false"]').exists()).toBe(true)
      expect(row.find('[data-network-capable="false"]').exists()).toBe(true)
      expect(row.find('[data-production-capable="false"]').exists()).toBe(true)
      expect(row.text()).toContain('none')
    }
  })

  it('the client-side status filter narrows the rendered modules', async () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const allCount = region.findAll('tbody tr[data-module-key]').length
    await region.find('[data-testid="governance-hub-target-b-module-filter-DESIGNED"]').trigger('click')
    const designedCount = region.findAll('tbody tr[data-module-key]').length
    for (const row of region.findAll('tbody tr[data-module-key]')) {
      expect(row.attributes('data-module-status')).toBe('DESIGNED')
    }
    await region.find('[data-testid="governance-hub-target-b-module-filter-SCAFFOLDED_DISABLED"]').trigger('click')
    const scaffoldedCount = region.findAll('tbody tr[data-module-key]').length
    for (const row of region.findAll('tbody tr[data-module-key]')) {
      expect(row.attributes('data-module-status')).toBe('SCAFFOLDED_DISABLED')
    }
    await region.find('[data-testid="governance-hub-target-b-module-filter-all"]').trigger('click')
    expect(region.findAll('tbody tr[data-module-key]').length).toBe(allCount)
    expect(designedCount + scaffoldedCount).toBe(allCount)
  })

  it('inspecting a module toggles its detail row (client-only, no network)', async () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const firstInspect = region.find('tbody tr[data-module-key] button[data-testid^="governance-hub-target-b-module-inspect-"]')
    expect(firstInspect.exists()).toBe(true)
    expect(region.findAll('tbody tr[data-module-detail]').length).toBe(0)
    await firstInspect.trigger('click')
    expect(region.findAll('tbody tr[data-module-detail]').length).toBe(1)
    await firstInspect.trigger('click')
    expect(region.findAll('tbody tr[data-module-detail]').length).toBe(0)
  })
})

describe('Target B Readiness region — plugin package + permission model', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the plugin package schema preview with not-loaded / not-executable markers', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const markers = region.find('[data-testid="governance-hub-target-b-plugin-package-markers"]').text()
    expect(markers).toContain('Example only')
    expect(markers).toContain('Not loaded')
    expect(markers).toContain('Not executable')
    expect(markers).toContain('No file read')
    expect(markers).toContain('No install')
    const fields = region.find('[data-testid="governance-hub-target-b-plugin-package-fields"]').text()
    expect(fields).toContain('https://registry.example.invalid')
  })

  it('renders every permission as DENIED_BY_DEFAULT', () => {
    const wrapper = mount(GovernanceHubSection)
    const rows = findRegion(wrapper).findAll(
      '[data-testid="governance-hub-target-b-permission-table"] tbody tr[data-permission-key]',
    )
    expect(rows.length).toBe(12)
    for (const row of rows) {
      expect(row.find('[data-permission-status="DENIED_BY_DEFAULT"]').exists()).toBe(true)
    }
  })
})

describe('Target B Readiness region — registry + execution preview + approval gate', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the registry preview disabled with a .invalid URL and signature required', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const registry = region.find('[data-testid="governance-hub-target-b-registry"]')
    expect(registry.find('[data-registry-url]').text()).toContain('registry.example.invalid')
    expect(registry.find('[data-registry-fetch="false"]').exists()).toBe(true)
    expect(registry.find('[data-registry-network="false"]').exists()).toBe(true)
    expect(registry.find('[data-marketplace-enabled="false"]').exists()).toBe(true)
    expect(registry.find('[data-signature-required="true"]').exists()).toBe(true)
    expect(registry.find('[data-allow-unsigned="false"]').exists()).toBe(true)
  })

  it('renders the WebUI execution preview disabled with NO execute / run button', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const execution = region.find('[data-testid="governance-hub-target-b-execution"]')
    expect(execution.find('[data-execute-button-enabled]').text()).toContain('false')
    expect(execution.find('[data-runtime-route-available]').text()).toContain('false')
    expect(execution.find('[data-can-submit]').text()).toContain('false')
    expect(execution.find('[data-execution-status]').text()).toContain('PREVIEW_ONLY_DISABLED')
    const flow = execution.find('[data-testid="governance-hub-target-b-execution-flow"]')
    expect(flow.findAll('li').length).toBeGreaterThan(0)
    for (const li of flow.findAll('li')) {
      expect(li.attributes('data-flow-enabled')).toBe('false')
    }
  })

  it('renders the approval gate with no trust token and rejected fake / AI / metadata approval', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const gate = region.find('[data-testid="governance-hub-target-b-approval"]')
    expect(gate.find('[data-human-approval-required]').text()).toContain('true')
    expect(gate.find('[data-trust-token-provisioned]').text()).toContain('false')
    expect(gate.find('[data-fake-approval-accepted]').text()).toContain('false')
    expect(gate.find('[data-ai-approval-accepted]').text()).toContain('false')
    expect(gate.find('[data-metadata-approval-accepted]').text()).toContain('false')
    expect(gate.find('[data-production-authorization="NO-GO"]').exists()).toBe(true)
  })

  it('renders every enablement blocker as unresolved', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const blockers = region.findAll('[data-testid="governance-hub-target-b-enablement-blockers"] li[data-blocker-key]')
    expect(blockers.length).toBeGreaterThan(0)
    for (const li of blockers) {
      expect(li.attributes('data-blocker-resolved')).toBe('false')
    }
  })
})

describe('Target B Readiness region — Target A relationship + checklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the Target A relationship (prerequisite evidence, no authorization)', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper)
      .find('[data-testid="governance-hub-target-b-target-a-relationship"]')
      .text()
      .toLowerCase()
    expect(text).toContain('prerequisite evidence')
    expect(text).toContain('does not authorize')
    expect(text).toContain('remains disabled')
  })

  it('cross-link buttons switch sections client-side', async () => {
    const nav = useDevConsoleNavStore()
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    await region.find('[data-testid="governance-hub-target-b-view-runtime-governance"]').trigger('click')
    expect(nav.activeSection).toBe('runtimeGovernance')
    await region.find('[data-testid="governance-hub-target-b-view-human-review"]').trigger('click')
    expect(nav.activeSection).toBe('humanReview')
  })

  it('renders the readiness checklist with ready and blocked items', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    const items = region.findAll('[data-testid="governance-hub-target-b-readiness-list"] li[data-readiness-id]')
    expect(items.length).toBeGreaterThan(0)
    const statuses = items.map((li) => li.attributes('data-readiness-status'))
    expect(statuses).toContain('ready')
    expect(statuses).toContain('blocked')
  })
})

describe('Target B Readiness region — accessibility + invariants', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the region has accessible headings, a labelled banner, and table captions', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    expect(region.find('h2').exists()).toBe(true)
    expect(region.findAll('h3').length).toBeGreaterThanOrEqual(5)
    expect(region.find('[data-testid="governance-hub-target-b-banner"]').attributes('aria-label')).toBeTruthy()
    expect(region.find('[data-testid="governance-hub-target-b-architecture-table"] caption').exists()).toBe(true)
    expect(region.find('[data-testid="governance-hub-target-b-permission-table"] caption').exists()).toBe(true)
  })

  it('the region text exposes the frozen P0 counts and route governance', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper).text()
    expect(text).toContain('24')
    expect(text).toContain('34/34/5/0/1/1')
    expect(text).toContain('NO-GO')
  })

  it('renders no unlabeled interactive input on the region', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    expect(region.findAll('input').length).toBe(0)
    expect(region.findAll('textarea').length).toBe(0)
    expect(region.findAll('select').length).toBe(0)
  })
})
