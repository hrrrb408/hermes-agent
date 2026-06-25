/**
 * Phase 4C — Target B Authorization package panel rendering tests.
 *
 * Mounts the Governance Hub section and asserts the read-only **Target B
 * Authorization Package** region renders every panel with the frozen, blocked,
 * fail-closed state:
 *   - authorization banner (readiness BLOCKED, execution disabled, production
 *     NO-GO, trust token not provisioned, P0 resolved 0, pending 5);
 *   - the 11 authorization layers (every one unauthorized);
 *   - human approval panel (missing; fake / AI / metadata rejected);
 *   - trust token panel (not provisioned);
 *   - trusted publisher panel (empty);
 *   - production signature verifier panel (not authorized);
 *   - sandbox lifecycle panel (not approved; no spawn / network / write / secrets);
 *   - registry / network / secret policy panels (registry disabled; network
 *     allowlist missing; secret policy default deny);
 *   - rollback / incident panel (design-ready only; rollout NO-GO);
 *   - route authorization panel (not authorized; deltas 0; baseline unchanged);
 *   - P0 gate coverage panel (5 pending gates; resolved delta 0);
 *   - enablement readiness panel (BLOCKED; blockers list);
 *   - the layer filter (client-only toggle) + copy control work.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'

describe('Target B Authorization package panel rendering (Phase 4C)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  function region() {
    const wrapper = mount(GovernanceHubSection)
    return wrapper.find('[data-testid="governance-hub-target-b-authz-region"]')
  }

  it('renders the authorization region + banner with the BLOCKED verdicts', () => {
    const r = region()
    expect(r.exists()).toBe(true)
    expect(r.find('[data-testid="governance-hub-target-b-authz-banner"]').exists()).toBe(true)
    const banner = r.find('[data-testid="governance-hub-target-b-authz-banner-lines"]').text()
    expect(banner).toContain('Readiness BLOCKED')
    expect(banner).toContain('Target B execution disabled')
    expect(banner).toContain('Production runtime NO-GO')
    expect(banner).toContain('Trust token not provisioned')
    expect(banner).toContain('P0 resolved 0')
  })

  it('renders the status badges with the frozen blocked labels', () => {
    const r = region()
    const badges = r.find('[data-testid="governance-hub-target-b-authz-status-badges"]').text()
    expect(badges).toContain('AUTHORIZATION PACKAGE')
    expect(badges).toContain('READINESS BLOCKED')
    expect(badges).toContain('PRODUCTION NO-GO')
    expect(badges).toContain('TRUST TOKEN NOT PROVISIONED')
    expect(badges).toContain('P0 RESOLVED 0')
  })

  it('renders the 11 authorization layers, every one unauthorized', () => {
    const r = region()
    const rows = r.findAll('tr[data-layer-key]')
    expect(rows.length).toBe(11)
    for (const row of rows) {
      expect(row.find('[data-authorized="false"]').exists()).toBe(true)
    }
  })

  it('the layer filter is a client-only toggle that changes the rendered rows', async () => {
    const r = region()
    const initial = r.findAll('tr[data-layer-key]').length
    await r.find('[data-testid="governance-hub-target-b-authz-layer-filter-DESIGN_READY_ONLY"]').trigger('click')
    const designRows = r.findAll('tr[data-layer-key]')
    for (const row of designRows) expect(row.attributes('data-layer-status')).toBe('DESIGN_READY_ONLY')
    await r.find('[data-testid="governance-hub-target-b-authz-layer-filter-all"]').trigger('click')
    expect(r.findAll('tr[data-layer-key]').length).toBe(initial)
  })

  it('inspecting a layer expands its detail (client-only)', async () => {
    const r = region()
    const firstKey = r.find('tr[data-layer-key]').attributes('data-layer-key')!
    expect(r.find(`tr[data-layer-detail="${firstKey}"]`).exists()).toBe(false)
    await r.find(`[data-testid="governance-hub-target-b-authz-layer-inspect-${firstKey}"]`).trigger('click')
    expect(r.find(`tr[data-layer-detail="${firstKey}"]`).exists()).toBe(true)
  })

  it('renders the human approval panel as missing / rejected', () => {
    const r = region()
    const ap = r.find('[data-testid="governance-hub-target-b-authz-human-approval"]')
    expect(ap.find('[data-approval-present="false"]').exists()).toBe(true)
    expect(ap.find('[data-fake-rejected="true"]').exists()).toBe(true)
    expect(ap.find('[data-ai-rejected="true"]').exists()).toBe(true)
    expect(ap.find('[data-metadata-rejected="true"]').exists()).toBe(true)
  })

  it('renders the trust token panel as not provisioned', () => {
    const r = region()
    const tt = r.find('[data-testid="governance-hub-target-b-authz-trust-token"]')
    expect(tt.find('[data-token-provisioned="false"]').exists()).toBe(true)
    expect(tt.find('[data-token-valid="false"]').exists()).toBe(true)
    expect(tt.find('[data-fake-token-rejected="true"]').exists()).toBe(true)
    expect(tt.find('[data-no-secret-read="true"]').exists()).toBe(true)
  })

  it('renders the trusted publisher panel as empty', () => {
    const r = region()
    const tp = r.find('[data-testid="governance-hub-target-b-authz-trusted-publishers"]')
    expect(tp.find('[data-publishers-count="0"]').exists()).toBe(true)
    expect(tp.find('[data-unknown-rejected="true"]').exists()).toBe(true)
    expect(tp.find('[data-wildcard-rejected="true"]').exists()).toBe(true)
  })

  it('renders the production signature verifier panel as not authorized', () => {
    const r = region()
    const ps = r.find('[data-testid="governance-hub-target-b-authz-production-signature"]')
    expect(ps.find('[data-prod-verifier="false"]').exists()).toBe(true)
    expect(ps.find('[data-fixture-only="true"]').exists()).toBe(true)
    expect(ps.find('[data-forged-rejected="true"]').exists()).toBe(true)
  })

  it('renders the sandbox lifecycle panel as not approved', () => {
    const r = region()
    const sb = r.find('[data-testid="governance-hub-target-b-authz-sandbox"]')
    expect(sb.find('[data-lifecycle-approved="false"]').exists()).toBe(true)
    expect(sb.find('[data-worker-start="false"]').exists()).toBe(true)
    expect(sb.find('[data-sbx-spawn="false"]').exists()).toBe(true)
    expect(sb.find('[data-sbx-network="false"]').exists()).toBe(true)
    expect(sb.find('[data-sbx-secrets="false"]').exists()).toBe(true)
  })

  it('renders the registry / network / secret policy panels as disabled / deny', () => {
    const r = region()
    const pol = r.find('[data-testid="governance-hub-target-b-authz-policies"]')
    expect(pol.find('[data-registry-disabled="true"]').exists()).toBe(true)
    expect(pol.find('[data-registry-fetch="false"]').exists()).toBe(true)
    expect(pol.find('[data-network-allowlist="false"]').exists()).toBe(true)
    expect(pol.find('[data-no-socket="true"]').exists()).toBe(true)
    expect(pol.find('[data-secret-policy="true"]').exists()).toBe(true)
    expect(pol.find('[data-secret-policy="true"]').text()).toContain('default deny')
    expect(pol.find('[data-no-secret-read="true"]').exists()).toBe(true)
  })

  it('renders the rollback / incident panel as design-ready only / NO-GO', () => {
    const r = region()
    const rb = r.find('[data-testid="governance-hub-target-b-authz-rollback"]')
    expect(rb.find('[data-rollback-approved="false"]').exists()).toBe(true)
    expect(rb.find('[data-kill-switch="DESIGN_READY_ONLY"]').exists()).toBe(true)
    expect(rb.find('[data-rollout="NO-GO"]').exists()).toBe(true)
    expect(rb.find('[data-rb-gateway="true"]').exists()).toBe(true)
  })

  it('renders the route authorization panel as not authorized / unchanged', () => {
    const r = region()
    const rt = r.find('[data-testid="governance-hub-target-b-authz-route"]')
    expect(rt.find('[data-route-authorized="false"]').exists()).toBe(true)
    expect(rt.find('[data-routes-registered="0"]').exists()).toBe(true)
    expect(rt.find('[data-openapi-delta="0"]').exists()).toBe(true)
    expect(rt.find('[data-runtime-delta="0"]').exists()).toBe(true)
    expect(rt.find('[data-route-baseline="34/34/5/0/1/1"]').exists()).toBe(true)
    expect(rt.find('[data-backend-changed="false"]').exists()).toBe(true)
  })

  it('renders the P0 gate coverage panel with 5 unresolved gates and delta 0', () => {
    const r = region()
    const p0 = r.find('[data-testid="governance-hub-target-b-authz-p0"]')
    const gates = p0.findAll('tr[data-gate-id]')
    expect(gates.length).toBe(5)
    for (const g of gates) {
      expect(g.find('[data-gate-resolved="false"]').exists()).toBe(true)
    }
    expect(p0.find('[data-resolved-delta="0"]').exists()).toBe(true)
    expect(p0.find('[data-p0-resolved="0"]').exists()).toBe(true)
  })

  it('renders the enablement readiness panel as BLOCKED', () => {
    const r = region()
    const er = r.find('[data-testid="governance-hub-target-b-authz-readiness"]')
    expect(er.find('[data-readiness="BLOCKED"]').exists()).toBe(true)
    expect(er.find('[data-enablement-allowed="false"]').exists()).toBe(true)
    expect(er.find('[data-all-gates-pass="false"]').exists()).toBe(true)
    const blockers = er.findAll('[data-testid="governance-hub-target-b-authz-readiness-blockers"] [data-blocker]')
    expect(blockers.length).toBeGreaterThan(0)
  })

  it('renders every enablement blocker as unresolved', () => {
    const r = region()
    const blockers = r.findAll('[data-testid="governance-hub-target-b-authz-blockers"] [data-blocker-key]')
    expect(blockers.length).toBe(11)
    for (const b of blockers) {
      expect(b.attributes('data-blocker-resolved')).toBe('false')
    }
  })

  it('renders the forbidden + allowed action lists', () => {
    const r = region()
    const forbidden = r.findAll('[data-testid="governance-hub-target-b-authz-forbidden-actions"] [data-forbidden-action]')
    const allowed = r.findAll('[data-testid="governance-hub-target-b-authz-allowed-actions"] [data-allowed-action]')
    expect(forbidden.length).toBeGreaterThan(0)
    expect(allowed.length).toBeGreaterThan(0)
    expect(forbidden.map((f) => f.attributes('data-forbidden-action'))).toContain('provision trust token')
    expect(forbidden.map((f) => f.attributes('data-forbidden-action'))).toContain('real API key entry')
  })

  it('copying the authorization summary writes the summary text to the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const r = region()
    await r.find('[data-testid="governance-hub-target-b-authz-copy-summary"]').trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalled()
    const text = String(writeText.mock.calls[0]![0])
    expect(text).toContain('BLOCKED')
    expect(text).toContain('34/34/5/0/1/1')
  })
})
