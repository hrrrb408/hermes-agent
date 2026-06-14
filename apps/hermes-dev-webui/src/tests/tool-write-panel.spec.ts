/**
 * Tests for the ToolWritePanel component (Phase 2C).
 *
 * Covers rendering of the write-tool selector, target-path validation, content
 * input, dry-run preview surface, the execute-disabled-before-confirmation
 * invariant, the mocked execute result, rollback preview, blocked reason, and
 * the invariant that NO API key / shell-command input element exists.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ToolWritePanel from '@/components/workspace/ToolWritePanel.vue'
import { useToolWriteStore } from '@/stores/toolWrite'
import type { WritePreviewResultData, WriteExecuteResultData } from '@/types/api/toolWrite'

vi.mock('@/api/toolWrite', () => ({
  runWritePreview: vi.fn(),
  executeWrite: vi.fn(),
}))

function makePreview(overrides: Partial<WritePreviewResultData> = {}): WritePreviewResultData {
  return {
    mode: 'write_preview',
    writePlanId: 'wpln_test',
    writePreviewId: 'wprv_test',
    toolId: 'dev_sandbox_file_write',
    operation: 'create_or_replace',
    sandboxRootLabel: 'dev tool-write-sandbox',
    targetRelativePath: 'notes/example.md',
    beforeExists: false,
    beforeHash: null,
    afterHash: 'a'.repeat(64),
    contentDigest: 'b'.repeat(64),
    diffPreview: '+ hello',
    riskTier: 'dev_sandbox_write',
    readOnly: false,
    writeRequired: true,
    localSideEffects: true,
    externalSideEffects: false,
    providerRequired: false,
    requiresConfirmation: true,
    requiresWriteEnablement: true,
    requiresRollbackPlan: true,
    rollbackPreview: 'Rollback would delete the newly-created file.',
    blocked: false,
    blockedReason: null,
    warnings: [],
    argumentDigest: 'c'.repeat(64),
    confirmationToken: 'wctok_test',
    requiresUserConfirmation: true,
    writeExecuted: false,
    ...overrides,
  }
}

function makeResult(overrides: Partial<WriteExecuteResultData> = {}): WriteExecuteResultData {
  return {
    mode: 'write',
    executionId: 'wexe_test',
    toolId: 'dev_sandbox_file_write',
    status: 'completed',
    writePlanId: 'wpln_test',
    writePreviewId: 'wprv_test',
    rollbackId: 'wrbk_test',
    operation: 'create_or_replace',
    targetRelativePath: 'notes/example.md',
    beforeHash: null,
    afterHash: 'a'.repeat(64),
    contentDigest: 'b'.repeat(64),
    bytesWritten: 5,
    linesChanged: 0,
    diffPreview: '+ hello',
    rollbackAvailable: true,
    readOnly: false,
    writeRequired: true,
    localSideEffects: true,
    externalSideEffects: false,
    providerSchemaSent: false,
    providerApiCalled: false,
    externalNetworkCalled: false,
    blockedReason: null,
    preExecutionAuditId: 'wau_pre',
    postExecutionAuditId: 'wau_post',
    warnings: [],
    readback: { exists: true, sizeBytes: 5, contentHash: 'a'.repeat(64), snippet: 'hello' },
    ...overrides,
  }
}

describe('ToolWritePanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountPanel() {
    return mount(ToolWritePanel, { attachTo: document.body })
  }

  it('renders the panel with write-tool selector and target path input', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('#write-tool').exists()).toBe(true)
    expect(wrapper.find('#write-target').exists()).toBe(true)
    expect(wrapper.text()).toContain('Controlled Write Tools')
  })

  it('offers all four write tools', () => {
    const wrapper = mountPanel()
    const options = wrapper.findAll('#write-tool option')
    const values = options.map((o) => o.attributes('value'))
    expect(values).toEqual([
      'dev_sandbox_file_write',
      'dev_sandbox_file_append',
      'dev_sandbox_file_patch',
      'dev_sandbox_file_readback',
    ])
  })

  it('renders the sandbox-only badge and safety flags', () => {
    const wrapper = mountPanel()
    expect(wrapper.text()).toContain('Sandbox only')
    expect(wrapper.text()).toContain('Write required')
    expect(wrapper.text()).toContain('true')
    expect(wrapper.text()).toContain('HERMES_TOOL_WRITE_EXECUTION_ENABLED')
  })

  it('rejects an absolute target path with a validation error', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.setTargetPath('/etc/passwd')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Absolute paths are not allowed')
    // Preview button is disabled for an unsafe target.
    const btn = wrapper.find('button.tool-write__btn--primary')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('rejects a traversal target path', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.setTargetPath('../escape.md')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Path traversal')
  })

  it('rejects a forbidden .env target', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.setTargetPath('bad/.env')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Forbidden target')
  })

  it('renders the content input for the write tool', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('#write-content').exists()).toBe(true)
  })

  it('disables the execute button before confirmation even with a preview', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.setTargetPath('notes/example.md')
    store.preview = makePreview()
    store.status = 'previewed'
    store.explicitConfirmed = false
    await wrapper.vm.$nextTick()
    const executeBtn = wrapper.findAll('button').find((b) => b.text().includes('Execute write'))!
    expect(executeBtn.attributes('disabled')).toBeDefined()
  })

  it('enables the execute button after explicit confirmation', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.setTargetPath('notes/example.md')
    store.preview = makePreview()
    store.status = 'previewed'
    store.explicitConfirmed = true
    await wrapper.vm.$nextTick()
    const executeBtn = wrapper.findAll('button').find((b) => b.text().includes('Execute write'))!
    expect(executeBtn.attributes('disabled')).toBeUndefined()
  })

  it('renders the diff preview and rollback preview after a successful preview', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.preview = makePreview()
    store.status = 'previewed'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Diff preview')
    expect(wrapper.text()).toContain('Rollback preview')
    expect(wrapper.text()).toContain('delete the newly-created file')
  })

  it('renders the execute result, rollback id, and audit ids after a mocked success', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.executeResult = makeResult()
    store.status = 'completed'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('wrbk_test')
    expect(wrapper.text()).toContain('wau_pre')
    expect(wrapper.text()).toContain('wau_post')
    expect(wrapper.text()).toContain('External network')
  })

  it('renders the blocked reason on a blocked result', async () => {
    const wrapper = mountPanel()
    const store = useToolWriteStore()
    store.executeResult = makeResult({ status: 'blocked', blockedReason: 'blocked_write_execution_not_enabled' })
    store.status = 'blocked'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('blocked_write_execution_not_enabled')
  })

  it('never renders an API key or shell-command input', () => {
    const wrapper = mountPanel()
    const html = wrapper.html().toLowerCase()
    for (const forbidden of ['api key', 'apikey', 'api-key', 'authorization', 'bearer', 'secret', 'password']) {
      expect(html).not.toContain(forbidden)
    }
    // No input element whose id/name/placeholder references a key/shell/command.
    const inputs = wrapper.findAll('input')
    for (const input of inputs) {
      const id = (input.attributes('id') || '').toLowerCase()
      const placeholder = (input.attributes('placeholder') || '').toLowerCase()
      expect(id + placeholder).not.toMatch(/key|token|secret|auth|command|shell/)
    }
  })
})
