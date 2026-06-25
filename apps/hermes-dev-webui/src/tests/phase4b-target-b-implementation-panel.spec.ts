/**
 * Phase 4B — Target B Implementation panel rendering tests.
 *
 * Mounts the Governance Hub section and asserts the read-only **Target B
 * End-to-End Implementation** region renders every panel with the frozen,
 * gated, disabled state:
 *   - implementation banner (scaffold ready, execution disabled, production
 *     NO-GO, webui execute disabled, registry disabled, marketplace disabled,
 *     approval NO-GO, p0 resolved 0);
 *   - the 12 implementation layers (every one disabled);
 *   - the signed package schema preview (example only / not loaded / not
 *     executable);
 *   - the signature verification panel (production not authorized, fixture
 *     only, trusted false);
 *   - the permission matrix (15 permissions, every one DENIED_BY_DEFAULT) +
 *     non-executable capabilities;
 *   - the registry trust panel (DISABLED, network/fetch/marketplace off);
 *   - the sandbox broker panel (disabled, no spawn/network/write/secrets);
 *   - the approval gate panel (no trust token, fake/AI/metadata rejected);
 *   - the execution policy panel (allowed false, webui execute disabled);
 *   - the audit/rollback panel (in-memory only, rollout NO-GO);
 *   - the enablement blockers + forbidden/allowed actions;
 *   - and the layer filter (client-only toggle) + copy control work.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'

describe('Target B Implementation panel rendering (Phase 4B)', () => {
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
    return wrapper.find('[data-testid="governance-hub-target-b-impl-region"]')
  }

  it('renders the implementation region + banner with the disabled verdicts', () => {
    const r = region()
    expect(r.exists()).toBe(true)
    expect(r.find('[data-testid="governance-hub-target-b-impl-banner"]').exists()).toBe(true)
    const banner = r.find('[data-testid="governance-hub-target-b-impl-banner-lines"]').text()
    expect(banner).toContain('Implementation scaffold')
    expect(banner).toContain('Execution disabled')
    expect(banner).toContain('Production runtime NO-GO')
    expect(banner).toContain('WebUI execute disabled')
    expect(banner).toContain('Registry disabled')
    expect(banner).toContain('Marketplace disabled')
    expect(banner).toContain('Approval NO-GO')
    expect(banner).toContain('P0 resolved 0')
  })

  it('renders the status badges with the frozen disabled labels', () => {
    const r = region()
    const badges = r.find('[data-testid="governance-hub-target-b-impl-status-badges"]').text()
    expect(badges).toContain('IMPLEMENTATION SCAFFOLD')
    expect(badges).toContain('EXECUTION DISABLED')
    expect(badges).toContain('PRODUCTION NO-GO')
    expect(badges).toContain('WEBUI EXECUTION DISABLED')
    expect(badges).toContain('REGISTRY DISABLED')
    expect(badges).toContain('MARKETPLACE DISABLED')
    expect(badges).toContain('APPROVAL NO-GO')
    expect(badges).toContain('P0 RESOLVED 0')
  })

  it('renders the 12 implementation layers, every one disabled', () => {
    const r = region()
    const rows = r.findAll('tr[data-layer-key]')
    expect(rows.length).toBe(12)
    for (const row of rows) {
      expect(row.attributes('data-layer-status')).toMatch(/^(DESIGNED|SCAFFOLDED_DISABLED)$/)
      expect(row.find('[data-enabled="false"]').exists()).toBe(true)
      expect(row.attributes('data-execution-capable') ?? row.find('[data-execution-capable]').attributes('data-execution-capable')).toBe('false')
    }
  })

  it('the layer filter is a client-only toggle that changes the rendered rows', async () => {
    const r = region()
    const allRows = () => r.findAll('tr[data-layer-key]').length
    const initial = allRows()
    await r.find('[data-testid="governance-hub-target-b-impl-layer-filter-DESIGNED"]').trigger('click')
    const designedRows = r.findAll('tr[data-layer-key]')
    for (const row of designedRows) expect(row.attributes('data-layer-status')).toBe('DESIGNED')
    await r.find('[data-testid="governance-hub-target-b-impl-layer-filter-all"]').trigger('click')
    expect(allRows()).toBe(initial)
  })

  it('inspecting a layer expands its detail (client-only)', async () => {
    const r = region()
    const firstKey = r.find('tr[data-layer-key]').attributes('data-layer-key')!
    expect(r.find(`tr[data-layer-detail="${firstKey}"]`).exists()).toBe(false)
    await r.find(`[data-testid="governance-hub-target-b-impl-layer-inspect-${firstKey}"]`).trigger('click')
    expect(r.find(`tr[data-layer-detail="${firstKey}"]`).exists()).toBe(true)
  })

  it('renders the signed package schema preview as example-only / not loaded', () => {
    const r = region()
    const pkg = r.find('[data-testid="governance-hub-target-b-impl-package"]').text()
    expect(pkg).toContain('Example only')
    expect(pkg).toContain('Not loaded')
    expect(pkg).toContain('Not executable')
    expect(pkg).toContain('fixture-hmac-sha256')
    expect(pkg).toContain('https://registry.example.invalid')
  })

  it('renders the signature verification panel as production-not-authorized', () => {
    const r = region()
    const sig = r.find('[data-testid="governance-hub-target-b-impl-signature"]')
    expect(sig.exists()).toBe(true)
    expect(sig.find('[data-prod-verifier="false"]').exists()).toBe(true)
    expect(sig.find('[data-trusted="false"]').exists()).toBe(true)
    expect(sig.find('[data-unsigned-rejected="true"]').exists()).toBe(true)
    expect(sig.find('[data-forged-rejected="true"]').exists()).toBe(true)
  })

  it('renders the 15-permission matrix, every one DENIED_BY_DEFAULT', () => {
    const r = region()
    const rows = r.findAll('[data-testid="governance-hub-target-b-impl-permission-table"] tr[data-permission-key]')
    expect(rows.length).toBe(15)
    for (const row of rows) {
      expect(row.find('[data-permission-status="DENIED_BY_DEFAULT"]').exists()).toBe(true)
    }
  })

  it('renders the capabilities as non-executable', () => {
    const r = region()
    const caps = r.find('[data-testid="governance-hub-target-b-impl-capabilities"]').text()
    expect(caps).toContain('non-executable')
  })

  it('renders the registry trust panel as DISABLED', () => {
    const r = region()
    const reg = r.find('[data-testid="governance-hub-target-b-impl-registry"]')
    expect(reg.find('[data-registry-mode="DISABLED"]').exists()).toBe(true)
    expect(reg.find('[data-registry-network="false"]').exists()).toBe(true)
    expect(reg.find('[data-registry-fetch="false"]').exists()).toBe(true)
    expect(reg.find('[data-marketplace-enabled="false"]').exists()).toBe(true)
  })

  it('renders the sandbox broker panel as disabled', () => {
    const r = region()
    const sb = r.find('[data-testid="governance-hub-target-b-impl-sandbox"]')
    expect(sb.find('[data-broker-enabled="false"]').exists()).toBe(true)
    expect(sb.find('[data-sandbox-execution="false"]').exists()).toBe(true)
    expect(sb.find('[data-process-spawn="false"]').exists()).toBe(true)
    expect(sb.find('[data-sandbox-network="false"]').exists()).toBe(true)
    expect(sb.find('[data-fs-write="false"]').exists()).toBe(true)
    expect(sb.find('[data-sandbox-secrets="false"]').exists()).toBe(true)
  })

  it('renders the approval gate panel with no trust token', () => {
    const r = region()
    const ap = r.find('[data-testid="governance-hub-target-b-impl-approval"]')
    expect(ap.find('[data-human-approval-required="true"]').exists()).toBe(true)
    expect(ap.find('[data-trust-token-provisioned="false"]').exists()).toBe(true)
    expect(ap.find('[data-fake-approval-accepted="false"]').exists()).toBe(true)
    expect(ap.find('[data-ai-approval-accepted="false"]').exists()).toBe(true)
    expect(ap.find('[data-metadata-approval-accepted="false"]').exists()).toBe(true)
  })

  it('renders the execution policy panel as denied', () => {
    const r = region()
    const ep = r.find('[data-testid="governance-hub-target-b-impl-execution-policy"]')
    expect(ep.find('[data-policy-allowed="false"]').exists()).toBe(true)
    expect(ep.find('[data-can-execute="false"]').exists()).toBe(true)
    expect(ep.find('[data-webui-execute="false"]').exists()).toBe(true)
    expect(ep.find('[data-runtime-route="false"]').exists()).toBe(true)
    expect(ep.find('[data-prod-runtime="false"]').exists()).toBe(true)
    const reasons = ep.findAll('[data-testid="governance-hub-target-b-impl-policy-reasons"] [data-policy-reason]')
    expect(reasons.length).toBeGreaterThan(0)
  })

  it('renders the audit/rollback panel as in-memory only / NO-GO', () => {
    const r = region()
    const ar = r.find('[data-testid="governance-hub-target-b-impl-audit-rollback"]')
    expect(ar.find('[data-audit-persistence="in_memory_only"]').exists()).toBe(true)
    expect(ar.find('[data-audit-persisted="false"]').exists()).toBe(true)
    expect(ar.find('[data-kill-switch="DESIGN_READY_ONLY"]').exists()).toBe(true)
    expect(ar.find('[data-prod-rollback="false"]').exists()).toBe(true)
    expect(ar.find('[data-prod-rollout="NO-GO"]').exists()).toBe(true)
    expect(ar.find('[data-gateway-untouched="true"]').exists()).toBe(true)
  })

  it('renders every enablement blocker as unresolved', () => {
    const r = region()
    const blockers = r.findAll('[data-testid="governance-hub-target-b-impl-blockers"] [data-blocker-key]')
    expect(blockers.length).toBeGreaterThan(0)
    for (const b of blockers) {
      expect(b.attributes('data-blocker-resolved')).toBe('false')
    }
  })

  it('renders the forbidden + allowed action lists', () => {
    const r = region()
    const forbidden = r.findAll('[data-testid="governance-hub-target-b-impl-forbidden-actions"] [data-forbidden-action]')
    const allowed = r.findAll('[data-testid="governance-hub-target-b-impl-allowed-actions"] [data-allowed-action]')
    expect(forbidden.length).toBeGreaterThan(0)
    expect(allowed.length).toBeGreaterThan(0)
    expect(forbidden.map((f) => f.attributes('data-forbidden-action'))).toContain('run plugin from WebUI')
    expect(forbidden.map((f) => f.attributes('data-forbidden-action'))).toContain('real API key entry')
  })

  it('copying the implementation summary writes the summary text to the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const r = region()
    await r.find('[data-testid="governance-hub-target-b-impl-copy-summary"]').trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalled()
    const text = String(writeText.mock.calls[0]![0])
    expect(text).toContain('SCAFFOLD_READY')
    expect(text).toContain('34/34/5/0/1/1')
  })
})
