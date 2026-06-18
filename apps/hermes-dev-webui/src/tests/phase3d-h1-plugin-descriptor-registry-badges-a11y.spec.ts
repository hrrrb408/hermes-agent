/**
 * Phase 3D-H1 — Plugin Descriptor badge accessibility HARDENING tests.
 *
 * Re-asserts every trust level, status, and permission class renders a
 * human-readable text label (non-color identification) so badges are never
 * color-only. Forbidden classes / trust levels carry an explicit "Forbidden"
 * marker; non-visible statuses carry a "Not executable" marker. Icons are
 * marked aria-hidden so screen readers announce the text label.
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

describe('PluginDescriptor badges a11y HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('every trust level renders a non-empty text label (not color-only)', () => {
    for (const tl of TRUST_LEVELS) {
      const wrapper = mount(PluginDescriptorTrustBadge, { props: { trustLevel: tl } })
      const label = wrapper.find('.plugin-badge__label')
      expect(label.exists(), `trust ${tl} has a label`).toBe(true)
      expect(label.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('every status renders a non-empty text label (not color-only)', () => {
    for (const st of STATUSES) {
      const wrapper = mount(PluginDescriptorStatusBadge, { props: { status: st } })
      const label = wrapper.find('.plugin-badge__label')
      expect(label.exists(), `status ${st} has a label`).toBe(true)
      expect(label.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('every permission class renders a non-empty text label (not color-only)', () => {
    for (const pc of PERMISSION_CLASSES) {
      const wrapper = mount(PluginDescriptorPermissionBadge, { props: { permissionClass: pc } })
      const label = wrapper.find('.plugin-badge__label')
      expect(label.exists(), `permission ${pc} has a label`).toBe(true)
      expect(label.text().trim().length).toBeGreaterThan(0)
    }
  })

  it('forbidden trust levels carry a Forbidden text marker', () => {
    for (const tl of ['external_forbidden', 'unknown_forbidden', 'production_forbidden'] as const) {
      const wrapper = mount(PluginDescriptorTrustBadge, { props: { trustLevel: tl } })
      expect(wrapper.find('.plugin-badge--forbidden').exists()).toBe(true)
      expect(wrapper.text()).toContain('Forbidden')
    }
  })

  it('forbidden permission classes carry a Forbidden text marker', () => {
    for (const pc of ['ADMIN_FORBIDDEN', 'EXTERNAL_FORBIDDEN', 'PRODUCTION_FORBIDDEN'] as const) {
      const wrapper = mount(PluginDescriptorPermissionBadge, { props: { permissionClass: pc } })
      expect(wrapper.find('.plugin-badge--forbidden').exists()).toBe(true)
      expect(wrapper.text()).toContain('Forbidden')
    }
  })

  it('non-visible statuses carry a Not-executable text marker', () => {
    for (const st of ['disabled', 'blocked', 'deprecated', 'removed'] as const) {
      const wrapper = mount(PluginDescriptorStatusBadge, { props: { status: st } })
      expect(wrapper.text()).toContain('Not executable')
    }
  })

  it('read-only permission does not carry a Forbidden marker', () => {
    const wrapper = mount(PluginDescriptorPermissionBadge, { props: { permissionClass: 'READ_ONLY' } })
    expect(wrapper.find('.plugin-badge--forbidden').exists()).toBe(false)
  })

  it('decorative icons are hidden from assistive tech (aria-hidden)', () => {
    const wrapper = mount(PluginDescriptorTrustBadge, { props: { trustLevel: 'trusted_static_descriptor' } })
    const icons = wrapper.findAll('svg')
    for (const icon of icons) {
      expect(icon.attributes('aria-hidden')).toBe('true')
    }
  })
})
