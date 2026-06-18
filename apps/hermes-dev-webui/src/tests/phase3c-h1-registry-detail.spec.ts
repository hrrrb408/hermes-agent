/**
 * Phase 3C-H1 — Capability Registry detail drawer hardening.
 *
 * Asserts the detail drawer renders the safe record for every capability —
 * badges, runtime-gate list, bindings, the explicit "describes only / does
 * not grant permission" notice — and leaks nothing across all 46 entries.
 * Blocked capabilities surface their blocked reason. The drawer is read-only.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/capabilityRegistry', () => ({
  fetchCapabilityRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import CapabilityRegistrySection from '@/components/devconsole/CapabilityRegistrySection.vue'
import CapabilityRegistryDetailDrawer from '@/components/devconsole/CapabilityRegistryDetailDrawer.vue'
import { useCapabilityRegistryStore } from '@/stores/capabilityRegistry'
import { CAPABILITY_REGISTRY_MANIFEST } from '@/constants/capabilityRegistryManifest'

const FORBIDDEN_TOKENS = [
  'apiKey', 'Authorization', 'Bearer', 'shellCommand', 'pythonImportPath',
  'externalUrl', 'downloadUrl', 'pluginPackage', 'dynamicModule', 'evalCode',
  'execCode', 'sqlStatement', 'productionPath', 'callable', 'secret',
]

describe('Phase 3C-H1 — registry detail drawer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders nothing when no capability is selected', () => {
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: null } })
    expect(wrapper.find('[data-testid="capability-detail-drawer"]').exists()).toBe(false)
  })

  it('renders the describes-only notice + runtime gates for a selected capability', () => {
    const cap = CAPABILITY_REGISTRY_MANIFEST[0]!
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap } })
    expect(wrapper.find('[data-testid="capability-describes-only-notice"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="capability-runtime-gates"]').exists()).toBe(true)
    expect(wrapper.text()).toContain(cap.displayName)
    expect(wrapper.text()).toContain('does not grant permission')
  })

  it('runtime gates render every gate as yes/no', () => {
    const cap = CAPABILITY_REGISTRY_MANIFEST.find((c) => c.permissionClass === 'WRITE_CONFIRM')!
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap } })
    const gates = wrapper.find('[data-testid="capability-runtime-gates"]').text()
    expect(gates).toContain('Requires dry-run')
    expect(gates).toContain('Requires confirmation')
    expect(gates).toContain('Requires audit')
  })

  it('blocked capability surfaces its blocked reason', () => {
    const blocked = CAPABILITY_REGISTRY_MANIFEST.find((c) => c.status === 'blocked')!
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: blocked } })
    expect(blocked.blockedReason).toBeTruthy()
    expect(wrapper.text()).toContain('Blocked reason')
    expect(wrapper.text()).toContain(blocked.blockedReason!)
  })

  it('the drawer is read-only — no input / form / write control', () => {
    const cap = CAPABILITY_REGISTRY_MANIFEST[0]!
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap } })
    expect(wrapper.findAll('input').length).toBe(0)
    // Only the close button exists as an interactive control.
    expect(wrapper.findAll('button').length).toBe(1)
  })

  it('selecting every capability leaks nothing', async () => {
    const store = useCapabilityRegistryStore()
    const wrapper = mount(CapabilityRegistrySection)
    for (const cap of CAPABILITY_REGISTRY_MANIFEST) {
      store.selectCapability(cap.capabilityId)
      await wrapper.vm.$nextTick()
      const html = wrapper.html()
      for (const token of FORBIDDEN_TOKENS) {
        if (html.includes(token)) {
          throw new Error(`forbidden token ${token} leaked for ${cap.capabilityId}`)
        }
      }
    }
    expect(CAPABILITY_REGISTRY_MANIFEST.length).toBe(46)
  })

  it('emits close when the close button is clicked', async () => {
    const cap = CAPABILITY_REGISTRY_MANIFEST[0]!
    const wrapper = mount(CapabilityRegistryDetailDrawer, { props: { capability: cap } })
    await wrapper.find('button[aria-label="Close detail"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
