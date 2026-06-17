/**
 * Phase 3C — Capability Registry detail drawer tests.
 *
 * Asserts the drawer renders the full safe record, badges, runtime gates,
 * bindings, and the explicit "registry describes only / does not grant
 * permission" notice. Asserts it is absent when no capability is selected.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import CapabilityRegistryDetailDrawer from '@/components/devconsole/CapabilityRegistryDetailDrawer.vue'
import type { CapabilityDetail } from '@/types/api/capabilityRegistry'

function cap(overrides: Partial<CapabilityDetail> = {}): CapabilityDetail {
  return {
    capabilityId: 'provider.live_manual_one_shot',
    displayName: 'Provider Live Manual One-shot',
    description: 'Strict manual single-use live provider gate.',
    category: 'provider',
    status: 'disabled',
    permissionClass: 'LIVE_PROVIDER_GATED',
    trustLevel: 'BUILTIN_VERIFIED',
    executionMode: 'manual_live',
    routeExposure: 'existing_route_only',
    requiresApproval: true,
    requiresDryRun: false,
    requiresConfirmation: true,
    requiresAudit: true,
    requiresBudget: true,
    requiresKillSwitch: true,
    devOnly: true,
    productionAllowed: false,
    disabledByDefault: true,
    blockedReason: null,
    providerBinding: 'live_manual_one_shot',
    redactionApplied: true,
    ...overrides,
  }
}

describe('CapabilityRegistryDetailDrawer (Phase 3C)', () => {
  it('does not render when capability is null', () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: null } })
    expect(wrapper.find('[data-testid="capability-detail-drawer"]').exists()).toBe(false)
  })

  it('renders the safe record fields', () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap() } })
    const text = wrapper.text()
    expect(text).toContain('Provider Live Manual One-shot')
    expect(text).toContain('provider.live_manual_one_shot')
    expect(text).toContain('manual_live')
    expect(text).toContain('existing_route_only')
    expect(text).toContain('live_manual_one_shot') // provider binding
  })

  it('renders the runtime gates', () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap() } })
    const gates = wrapper.find('[data-testid="capability-runtime-gates"]').text().toLowerCase()
    expect(gates).toContain('requires approval:yes')
    expect(gates).toContain('requires budget:yes')
    expect(gates).toContain('requires kill switch:yes')
    expect(gates).toContain('dev-only:yes')
    expect(gates).toContain('production allowed:no')
  })

  it('renders the describes-only / does-not-grant-permission notice', () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap() } })
    const notice = wrapper.find('[data-testid="capability-describes-only-notice"]').text().toLowerCase()
    expect(notice).toContain('does not grant permission')
  })

  it('renders the blocked reason when present', () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, {
      props: { capability: cap({ status: 'blocked', permissionClass: 'ADMIN_FORBIDDEN', blockedReason: 'provider_write_forbidden' }) },
    })
    expect(wrapper.text()).toContain('provider_write_forbidden')
  })

  it('emits close when the close button is clicked', async () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap() } })
    await wrapper.find('.cap-drawer__close').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
