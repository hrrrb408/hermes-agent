/**
 * Phase 2E-H1 — Lens 3: Workflow Continuity Boundary.
 *
 * Verifies the five console workflows (read-only / provider / write / rollback /
 * audit) stay coherent inside the console wrappers: each surfaces the correct
 * result→audit cross-reference strip and the unified BlockedReasonPanel for a
 * blocked outcome, without losing state or leaking internals. Store state is
 * set directly (deterministic; no live API).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolPolicy', () => ({ fetchToolPolicyStatus: vi.fn(), fetchToolCatalog: vi.fn() }))
vi.mock('@/api/toolAudit', () => ({ getAuditEvents: vi.fn(), getAuditEventsV2: vi.fn() }))
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({ runWritePreview: vi.fn(), executeWrite: vi.fn(), runRollbackPreview: vi.fn(), executeRollback: vi.fn() }))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn(), fetchProviderBoundary: vi.fn().mockResolvedValue(null) }))

import ToolExecutionSection from '@/components/devconsole/ToolExecutionSection.vue'
import ProviderSection from '@/components/devconsole/ProviderSection.vue'
import WriteRollbackSection from '@/components/devconsole/WriteRollbackSection.vue'
import { useToolExecuteStore } from '@/stores/toolExecute'
import { useToolProviderStore } from '@/stores/toolProvider'
import { useToolWriteStore } from '@/stores/toolWrite'

describe('Lens 3 — Workflow continuity (Phase 2E-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('Read-only: a completed execute surfaces its pre/post-exec audit cross-references', () => {
    const store = useToolExecuteStore()
    store.executeResult = {
      postExecutionAuditId: 'pexa_aaa',
      preExecutionAuditId: 'prex_bbb',
      executeRequestId: 'req_ccc',
      dryRunRequestId: 'dry_ddd',
    } as never

    const wrapper = mount(ToolExecutionSection)
    const links = wrapper.findAll('[data-testid="dev-audit-id-link"]')
    expect(links.length).toBeGreaterThanOrEqual(4)
    const labels = links.map((l) => l.text()).join(' ')
    expect(labels).toContain('post-exec audit')
    expect(labels).toContain('pre-exec audit')
  })

  it('Read-only: no executeResult → no cross-reference strip (clean empty state)', () => {
    const store = useToolExecuteStore()
    store.executeResult = null as never
    const wrapper = mount(ToolExecutionSection)
    expect(wrapper.find('.devconsole-crossnav').exists()).toBe(false)
  })

  it('Provider: a blocked round-trip renders the unified BlockedReasonPanel with a safe explanation', () => {
    const store = useToolProviderStore()
    store.result = { blockedReason: 'blocked_provider_real_mode_not_enabled', providerAuditIds: [] } as never

    // Stub the reused panel to isolate the Phase 2E wrapper (the panel has its
    // own extensive tests). The BlockedReasonPanel is rendered by the wrapper.
    const wrapper = mount(ProviderSection, { global: { stubs: ['ProviderRoundtripPanel'] } })
    const panel = wrapper.find('[data-testid="dev-blocked-reason"]')
    expect(panel.exists()).toBe(true)
    expect(panel.text()).toContain('Real provider blocked')
    // The panel never suggests bypassing the real-mode gate.
    expect(panel.text().toLowerCase()).not.toContain('bypass')
  })

  it('Provider: a completed fake round-trip surfaces the provider audit cross-references', () => {
    const store = useToolProviderStore()
    store.result = {
      blockedReason: null,
      providerAuditIds: ['prov_a1', 'prov_a2'],
    } as never

    const wrapper = mount(ProviderSection, { global: { stubs: ['ProviderRoundtripPanel'] } })
    const links = wrapper.findAll('[data-testid="dev-audit-id-link"]')
    expect(links.length).toBe(2)
    for (const l of links) expect(l.text()).toContain('provider audit')
    // No blocked panel for a successful round-trip.
    expect(wrapper.find('[data-testid="dev-blocked-reason"]').exists()).toBe(false)
  })

  it('Write: an executed write surfaces the rollback manifest + write audit cross-references', () => {
    const store = useToolWriteStore()
    store.executeResult = {
      mode: 'write',
      status: 'completed',
      rollbackId: 'rbid_write_1',
      preExecutionAuditId: 'prex_w',
      postExecutionAuditId: 'pexa_w',
      blockedReason: null,
    } as never

    const wrapper = mount(WriteRollbackSection)
    const labels = wrapper.findAll('[data-testid="dev-audit-id-link"]').map((l) => l.text()).join(' ')
    expect(labels).toContain('rollback manifest')
    expect(labels).toContain('write post-exec audit')
    expect(labels).toContain('write pre-exec audit')
  })

  it('Write: a forbidden-path block renders the unified panel under its real backend code', () => {
    const store = useToolWriteStore()
    store.executeResult = {
      mode: 'write',
      status: 'blocked',
      blockedReason: 'blocked_write_forbidden_path',
      rollbackId: null,
      preExecutionAuditId: null,
      postExecutionAuditId: null,
    } as never

    const wrapper = mount(WriteRollbackSection)
    const panel = wrapper.find('[data-testid="dev-blocked-reason"]')
    expect(panel.exists()).toBe(true)
    // The real backend code is rendered (not the prior mismatched _forbidden_target).
    expect(panel.text()).toContain('blocked_write_forbidden_path')
    // The explanation is rendered (the section overrides the title to "Write blocked").
    expect(panel.text()).toContain('protected pattern')
  })

  it('Rollback: an executed rollback surfaces the rollback audit cross-references', () => {
    const store = useToolWriteStore()
    store.rollbackResult = {
      preExecutionAuditId: 'prex_rb',
      postExecutionAuditId: 'pexa_rb',
      blockedReason: null,
    } as never

    const wrapper = mount(WriteRollbackSection)
    const labels = wrapper.findAll('[data-testid="dev-audit-id-link"]').map((l) => l.text()).join(' ')
    expect(labels).toContain('rollback post-exec audit')
    expect(labels).toContain('rollback pre-exec audit')
  })

  it('Rollback: a hash-mismatch block renders the unified danger panel', () => {
    const store = useToolWriteStore()
    store.rollbackResult = {
      blockedReason: 'blocked_rollback_current_hash_mismatch',
      preExecutionAuditId: null,
      postExecutionAuditId: null,
    } as never

    const wrapper = mount(WriteRollbackSection)
    const panel = wrapper.find('[data-testid="dev-blocked-reason"]')
    expect(panel.exists()).toBe(true)
    // The explanation is rendered (the section overrides the title to "Rollback blocked").
    expect(panel.text()).toContain('sandbox file changed')
    // Severity is danger → the Blocked badge text is present (non-color redundancy).
    expect(panel.find('[data-severity="danger"]').exists()).toBe(true)
  })
})
