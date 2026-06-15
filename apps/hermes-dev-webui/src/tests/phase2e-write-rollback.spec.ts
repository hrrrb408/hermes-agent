/**
 * Phase 2E — Sandbox Write & Rollback section tests.
 *
 * The section reuses the existing ToolWritePanel (write preview/execute + rollback
 * preview/execute) and adds unified BlockedReasonPanel surfaces for blocked
 * write/rollback outcomes. Asserts the write surface renders with sandbox-only
 * flags, the rollback manifest input is present, and no protected-path / raw
 * write affordance leaks.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolWrite', () => ({
  runWritePreview: vi.fn(),
  executeWrite: vi.fn(),
  runRollbackPreview: vi.fn(),
  executeRollback: vi.fn(),
}))

import WriteRollbackSection from '@/components/devconsole/WriteRollbackSection.vue'
import { useToolWriteStore } from '@/stores/toolWrite'

describe('WriteRollbackSection (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the write tool selector, target path, and sandbox-only flags', () => {
    const wrapper = mount(WriteRollbackSection)
    expect(wrapper.find('#write-tool').exists()).toBe(true)
    expect(wrapper.find('#write-target').exists()).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('Sandbox only')
    expect(text).toContain('Write required')
    expect(text).toContain('Requires confirmation')
  })

  it('renders the rollback manifest id input', () => {
    const wrapper = mount(WriteRollbackSection)
    expect(wrapper.find('#write-rollback-id').exists()).toBe(true)
  })

  it('exposes no API-key / shell-command / production-path inputs', () => {
    const wrapper = mount(WriteRollbackSection)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    expect(wrapper.html()).not.toMatch(/api[_-]?key/i)
    // The intro never references the production home.
    expect(wrapper.text()).not.toContain('/Users/huangruibang/.hermes')
  })

  it('renders the BlockedReasonPanel when a write is blocked', () => {
    const store = useToolWriteStore()
    // Simulate a blocked execute result surfaced by the store.
    store.executeResult = {
      mode: 'write', executionId: 'exe_1', toolId: 'dev_sandbox_file_write',
      status: 'blocked', writePlanId: null, writePreviewId: null, rollbackId: null,
      operation: 'create_or_replace', targetRelativePath: 'notes/x.md',
      beforeHash: null, afterHash: null, contentDigest: null, bytesWritten: 0, linesChanged: 0,
      diffPreview: '', rollbackAvailable: false,
      readOnly: false, writeRequired: true, localSideEffects: true, externalSideEffects: false,
      providerSchemaSent: false, providerApiCalled: false, externalNetworkCalled: false,
      blockedReason: 'blocked_write_path_traversal', preExecutionAuditId: null, postExecutionAuditId: null,
      warnings: [],
    } as never

    const wrapper = mount(WriteRollbackSection)
    const panel = wrapper.find('[data-testid="dev-blocked-reason"]')
    expect(panel.exists()).toBe(true)
    // The code + explanation are rendered (title is the section override).
    expect(panel.text()).toContain('blocked_write_path_traversal')
    expect(panel.text()).toContain('traversal sequences')
  })
})
