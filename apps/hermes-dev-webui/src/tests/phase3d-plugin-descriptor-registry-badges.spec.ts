/**
 * Phase 3D — Plugin Descriptor badge tests.
 *
 * Asserts every trust level, status, and permission class renders a human-
 * readable text label (non-color identification) and that forbidden classes /
 * trust levels carry an explicit "Forbidden" / "Not executable" marker.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorTrustBadge from '@/components/devconsole/PluginDescriptorTrustBadge.vue'
import PluginDescriptorStatusBadge from '@/components/devconsole/PluginDescriptorStatusBadge.vue'
import PluginDescriptorPermissionBadge from '@/components/devconsole/PluginDescriptorPermissionBadge.vue'

const TRUST_LEVELS = [
  'trusted_builtin_code',
  'trusted_static_descriptor',
  'dev_reviewed_descriptor',
  'experimental_disabled_descriptor',
  'external_forbidden',
  'unknown_forbidden',
  'production_forbidden',
] as const

const STATUSES = [
  'planned',
  'declared',
  'validated',
  'visible',
  'disabled',
  'blocked',
  'deprecated',
  'removed',
] as const

const PERMISSION_CLASSES = [
  'READ_ONLY',
  'WRITE_PREVIEW',
  'WRITE_CONFIRM',
  'ROLLBACK_CONFIRM',
  'LIVE_PROVIDER_GATED',
  'ADMIN_FORBIDDEN',
  'EXTERNAL_FORBIDDEN',
  'PRODUCTION_FORBIDDEN',
] as const

describe('PluginDescriptor badges (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('every trust level renders a text label', () => {
    for (const tl of TRUST_LEVELS) {
      const wrapper = mount(PluginDescriptorTrustBadge, { props: { trustLevel: tl } })
      const label = wrapper.find('.plugin-badge__label')
      expect(label.exists()).toBe(true)
      expect(label.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('forbidden trust levels carry a Forbidden marker', () => {
    for (const tl of ['external_forbidden', 'unknown_forbidden', 'production_forbidden'] as const) {
      const wrapper = mount(PluginDescriptorTrustBadge, { props: { trustLevel: tl } })
      expect(wrapper.find('.plugin-badge--forbidden').exists()).toBe(true)
      expect(wrapper.text()).toContain('Forbidden')
    }
  })

  it('every status renders a text label', () => {
    for (const st of STATUSES) {
      const wrapper = mount(PluginDescriptorStatusBadge, { props: { status: st } })
      const label = wrapper.find('.plugin-badge__label')
      expect(label.exists()).toBe(true)
      expect(label.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('non-visible statuses carry a Not executable marker', () => {
    const wrapper = mount(PluginDescriptorStatusBadge, { props: { status: 'blocked' } })
    expect(wrapper.text()).toContain('Not executable')
  })

  it('every permission class renders a text label', () => {
    for (const pc of PERMISSION_CLASSES) {
      const wrapper = mount(PluginDescriptorPermissionBadge, { props: { permissionClass: pc } })
      const label = wrapper.find('.plugin-badge__label')
      expect(label.exists()).toBe(true)
      expect(label.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('forbidden permission classes carry a Forbidden marker', () => {
    for (const pc of ['ADMIN_FORBIDDEN', 'EXTERNAL_FORBIDDEN', 'PRODUCTION_FORBIDDEN'] as const) {
      const wrapper = mount(PluginDescriptorPermissionBadge, { props: { permissionClass: pc } })
      expect(wrapper.find('.plugin-badge--forbidden').exists()).toBe(true)
      expect(wrapper.text()).toContain('Forbidden')
    }
  })

  it('read-only permission does not carry a Forbidden marker', () => {
    const wrapper = mount(PluginDescriptorPermissionBadge, { props: { permissionClass: 'READ_ONLY' } })
    expect(wrapper.find('.plugin-badge--forbidden').exists()).toBe(false)
  })
})
