/**
 * Phase 3C — Capability Registry table tests.
 *
 * Asserts the table renders capability rows, badges, blocked reasons, and a
 * per-row Detail action. Also covers read-only tool rows, LIVE_PROVIDER_GATED
 * rows, and ADMIN/EXTERNAL/PRODUCTION forbidden rows.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import CapabilityRegistryTable from '@/components/devconsole/CapabilityRegistryTable.vue'
import type { CapabilityDetail } from '@/types/api/capabilityRegistry'

function cap(overrides: Partial<CapabilityDetail> = {}): CapabilityDetail {
  return {
    capabilityId: 'tool.read.x',
    displayName: 'X',
    description: 'desc',
    category: 'tool',
    status: 'enabled',
    permissionClass: 'READ_ONLY',
    trustLevel: 'BUILTIN_VERIFIED',
    executionMode: 'read_only',
    routeExposure: 'existing_route_only',
    requiresApproval: false,
    requiresDryRun: false,
    requiresConfirmation: false,
    requiresAudit: true,
    requiresBudget: false,
    requiresKillSwitch: false,
    devOnly: true,
    productionAllowed: false,
    disabledByDefault: false,
    blockedReason: null,
    redactionApplied: true,
    ...overrides,
  }
}

describe('CapabilityRegistryTable (Phase 3C)', () => {
  it('renders one row per capability', () => {
    const caps = [cap({ capabilityId: 'tool.read.a' }), cap({ capabilityId: 'tool.read.b' })]
    const wrapper = mount(CapabilityRegistryTable, { props: { capabilities: caps } })
    expect(wrapper.findAll('tbody tr').length).toBe(2)
  })

  it('renders a read-only tool capability', () => {
    const wrapper = mount(CapabilityRegistryTable, {
      props: { capabilities: [cap({ capabilityId: 'tool.read.clarify', displayName: 'Clarify' })] },
    })
    const text = wrapper.text()
    expect(text).toContain('Clarify')
    expect(text).toContain('tool.read.clarify')
    expect(text).toContain('Read-only')
  })

  it('renders a LIVE_PROVIDER_GATED capability', () => {
    const wrapper = mount(CapabilityRegistryTable, {
      props: {
        capabilities: [
          cap({
            capabilityId: 'provider.live_manual_one_shot',
            displayName: 'Provider Live Manual One-shot',
            category: 'provider',
            status: 'disabled',
            permissionClass: 'LIVE_PROVIDER_GATED',
            executionMode: 'manual_live',
          }),
        ],
      },
    })
    const text = wrapper.text()
    expect(text).toContain('Live provider gated')
    expect(text).toContain('provider.live_manual_one_shot')
  })

  it('renders ADMIN_FORBIDDEN / EXTERNAL_FORBIDDEN / PRODUCTION_FORBIDDEN blocked rows', () => {
    const caps = [
      cap({ capabilityId: 'capability.forbidden.shell', status: 'blocked', permissionClass: 'ADMIN_FORBIDDEN', trustLevel: 'EXTERNAL_FORBIDDEN', blockedReason: 'shell_command_forbidden' }),
      cap({ capabilityId: 'capability.forbidden.marketplace', status: 'blocked', permissionClass: 'EXTERNAL_FORBIDDEN', trustLevel: 'EXTERNAL_FORBIDDEN', blockedReason: 'marketplace_forbidden' }),
      cap({ capabilityId: 'capability.forbidden.production_operation', status: 'blocked', permissionClass: 'PRODUCTION_FORBIDDEN', trustLevel: 'EXTERNAL_FORBIDDEN', blockedReason: 'production_operation_forbidden' }),
    ]
    const wrapper = mount(CapabilityRegistryTable, { props: { capabilities: caps } })
    const text = wrapper.text()
    expect(text).toContain('Admin forbidden')
    expect(text).toContain('External forbidden')
    expect(text).toContain('Production forbidden')
    expect(text).toContain('shell_command_forbidden')
    expect(text).toContain('marketplace_forbidden')
    expect(text).toContain('production_operation_forbidden')
  })

  it('emits select with the capabilityId when Detail is clicked', async () => {
    const wrapper = mount(CapabilityRegistryTable, {
      props: { capabilities: [cap({ capabilityId: 'tool.read.clarify' })] },
    })
    await wrapper.find('.cap-view-btn').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual(['tool.read.clarify'])
  })

  it('marks blocked rows with the blocked-reason class', () => {
    const wrapper = mount(CapabilityRegistryTable, {
      props: {
        capabilities: [cap({ status: 'blocked', permissionClass: 'ADMIN_FORBIDDEN', blockedReason: 'x_forbidden' })],
      },
    })
    expect(wrapper.find('tbody tr').classes()).toContain('cap-row--blocked')
  })
})
