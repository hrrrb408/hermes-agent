/**
 * Phase 3C-H1 — Capability badge accessibility / non-color hardening.
 *
 * Asserts every permission / trust / status badge renders a human-readable
 * TEXT label (never color alone), exposes a `title` attribute for screen
 * readers, and carries an explicit text marker for the forbidden / not-
 * executable classes so status is never communicated by hue alone.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import CapabilityPermissionBadge from '@/components/devconsole/CapabilityPermissionBadge.vue'
import CapabilityTrustBadge from '@/components/devconsole/CapabilityTrustBadge.vue'
import CapabilityStatusBadge from '@/components/devconsole/CapabilityStatusBadge.vue'

const PERMISSION_LABELS: Record<string, string> = {
  READ_ONLY: 'Read-only',
  WRITE_PREVIEW: 'Write preview',
  WRITE_CONFIRM: 'Write confirm',
  ROLLBACK_CONFIRM: 'Rollback confirm',
  LIVE_PROVIDER_GATED: 'Live provider gated',
  ADMIN_FORBIDDEN: 'Admin forbidden',
  EXTERNAL_FORBIDDEN: 'External forbidden',
  PRODUCTION_FORBIDDEN: 'Production forbidden',
}

const TRUST_LABELS: Record<string, string> = {
  BUILTIN_VERIFIED: 'Built-in verified',
  DEV_STATIC_MANIFEST: 'Dev static manifest',
  EXPERIMENTAL_DISABLED: 'Experimental disabled',
  EXTERNAL_FORBIDDEN: 'External forbidden',
  UNKNOWN_FORBIDDEN: 'Unknown forbidden',
}

const STATUS_LABELS: Record<string, string> = {
  enabled: 'Enabled',
  disabled: 'Disabled',
  blocked: 'Blocked',
  planned: 'Planned',
  deprecated: 'Deprecated',
}

describe('Phase 3C-H1 — permission badge a11y', () => {
  it.each(Object.keys(PERMISSION_LABELS))('%s renders a non-color text label', (pc) => {
    const wrapper = mount(CapabilityPermissionBadge, { props: { permissionClass: pc as never } })
    expect(wrapper.text()).toContain(PERMISSION_LABELS[pc])
    // Not color-only: a label element carries the text.
    expect(wrapper.find('.cap-badge__label').text()).toBe(PERMISSION_LABELS[pc])
  })

  it.each(Object.keys(PERMISSION_LABELS))('%s exposes a title attribute', (pc) => {
    const wrapper = mount(CapabilityPermissionBadge, { props: { permissionClass: pc as never } })
    expect(wrapper.attributes('title')).toContain('Permission class')
    expect(wrapper.attributes('title')).toContain(pc)
  })

  it.each(['ADMIN_FORBIDDEN', 'EXTERNAL_FORBIDDEN', 'PRODUCTION_FORBIDDEN'])(
    '%s carries an explicit Forbidden text marker',
    (pc) => {
      const wrapper = mount(CapabilityPermissionBadge, { props: { permissionClass: pc as never } })
      expect(wrapper.text()).toContain('Forbidden')
    },
  )
})

describe('Phase 3C-H1 — trust badge a11y', () => {
  it.each(Object.keys(TRUST_LABELS))('%s renders a non-color text label', (tl) => {
    const wrapper = mount(CapabilityTrustBadge, { props: { trustLevel: tl as never } })
    expect(wrapper.text()).toContain(TRUST_LABELS[tl])
    expect(wrapper.find('.cap-badge__label').text()).toBe(TRUST_LABELS[tl])
  })

  it.each(Object.keys(TRUST_LABELS))('%s exposes a title attribute', (tl) => {
    const wrapper = mount(CapabilityTrustBadge, { props: { trustLevel: tl as never } })
    expect(wrapper.attributes('title')).toContain('Trust level')
    expect(wrapper.attributes('title')).toContain(tl)
  })

  it.each(['EXTERNAL_FORBIDDEN', 'UNKNOWN_FORBIDDEN'])(
    '%s carries an explicit Forbidden text marker',
    (tl) => {
      const wrapper = mount(CapabilityTrustBadge, { props: { trustLevel: tl as never } })
      expect(wrapper.text()).toContain('Forbidden')
    },
  )
})

describe('Phase 3C-H1 — status badge a11y', () => {
  it.each(Object.keys(STATUS_LABELS))('%s renders a non-color text label', (st) => {
    const wrapper = mount(CapabilityStatusBadge, { props: { status: st as never } })
    expect(wrapper.text()).toContain(STATUS_LABELS[st])
    expect(wrapper.find('.cap-badge__label').text()).toBe(STATUS_LABELS[st])
  })

  it.each(Object.keys(STATUS_LABELS))('%s exposes a title attribute', (st) => {
    const wrapper = mount(CapabilityStatusBadge, { props: { status: st as never } })
    expect(wrapper.attributes('title')).toContain('Status')
    expect(wrapper.attributes('title')).toContain(st)
  })

  it.each(['disabled', 'blocked', 'planned', 'deprecated'])(
    '%s carries an explicit Not-executable marker',
    (st) => {
      const wrapper = mount(CapabilityStatusBadge, { props: { status: st as never } })
      expect(wrapper.text()).toContain('Not executable')
    },
  )

  it('enabled status does NOT carry the not-executable marker', () => {
    const wrapper = mount(CapabilityStatusBadge, { props: { status: 'enabled' } })
    expect(wrapper.text()).not.toContain('Not executable')
  })
})
