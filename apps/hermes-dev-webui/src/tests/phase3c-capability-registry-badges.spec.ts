/**
 * Phase 3C — Capability Registry badge tests.
 *
 * Asserts permission / trust / status badges render a text label (not color
 * alone), forbidden classes carry an explicit marker, and live-gated badges
 * are distinguishable.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import CapabilityPermissionBadge from '@/components/devconsole/CapabilityPermissionBadge.vue'
import CapabilityTrustBadge from '@/components/devconsole/CapabilityTrustBadge.vue'
import CapabilityStatusBadge from '@/components/devconsole/CapabilityStatusBadge.vue'

describe('CapabilityPermissionBadge (Phase 3C)', () => {
  it('READ_ONLY renders a non-color label', () => {
    const text = mount(CapabilityPermissionBadge, { props: { permissionClass: 'READ_ONLY' } }).text()
    expect(text).toContain('Read-only')
  })

  it('WRITE_CONFIRM renders a non-color label', () => {
    const text = mount(CapabilityPermissionBadge, { props: { permissionClass: 'WRITE_CONFIRM' } }).text()
    expect(text).toContain('Write confirm')
  })

  it('LIVE_PROVIDER_GATED renders the live label', () => {
    const text = mount(CapabilityPermissionBadge, { props: { permissionClass: 'LIVE_PROVIDER_GATED' } }).text()
    expect(text).toContain('Live provider gated')
  })

  it.each(['ADMIN_FORBIDDEN', 'EXTERNAL_FORBIDDEN', 'PRODUCTION_FORBIDDEN'] as const)(
    '%s carries an explicit Forbidden marker',
    (pc) => {
      const text = mount(CapabilityPermissionBadge, { props: { permissionClass: pc } }).text()
      expect(text).toContain('Forbidden')
    },
  )
})

describe('CapabilityTrustBadge (Phase 3C)', () => {
  it('BUILTIN_VERIFIED renders a non-color label', () => {
    const text = mount(CapabilityTrustBadge, { props: { trustLevel: 'BUILTIN_VERIFIED' } }).text()
    expect(text).toContain('Built-in verified')
  })

  it('DEV_STATIC_MANIFEST renders a non-color label', () => {
    const text = mount(CapabilityTrustBadge, { props: { trustLevel: 'DEV_STATIC_MANIFEST' } }).text()
    expect(text).toContain('Dev static manifest')
  })

  it.each(['EXTERNAL_FORBIDDEN', 'UNKNOWN_FORBIDDEN'] as const)(
    '%s carries an explicit Forbidden marker',
    (tl) => {
      const text = mount(CapabilityTrustBadge, { props: { trustLevel: tl } }).text()
      expect(text).toContain('Forbidden')
    },
  )
})

describe('CapabilityStatusBadge (Phase 3C)', () => {
  it('enabled renders a non-color label', () => {
    const text = mount(CapabilityStatusBadge, { props: { status: 'enabled' } }).text()
    expect(text).toContain('Enabled')
  })

  it('disabled renders a Not-executable marker', () => {
    const text = mount(CapabilityStatusBadge, { props: { status: 'disabled' } }).text()
    expect(text).toContain('Disabled')
    expect(text).toContain('Not executable')
  })

  it('blocked renders a Not-executable marker', () => {
    const text = mount(CapabilityStatusBadge, { props: { status: 'blocked' } }).text()
    expect(text).toContain('Blocked')
    expect(text).toContain('Not executable')
  })

  it('planned and deprecated render non-color labels', () => {
    expect(mount(CapabilityStatusBadge, { props: { status: 'planned' } }).text()).toContain('Planned')
    expect(mount(CapabilityStatusBadge, { props: { status: 'deprecated' } }).text()).toContain('Deprecated')
  })
})
