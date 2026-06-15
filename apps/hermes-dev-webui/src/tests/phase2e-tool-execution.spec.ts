/**
 * Phase 2E — Tool Execution section tests.
 *
 * The section reuses the existing ToolExecutePanel and adds a result→audit
 * cross-reference strip. Asserts the panel renders (regression), the read-only
 * tool surface is intact, and the cross-nav AuditIdLink appears after a
 * completed execute.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))

import { runDryRun, executeTool } from '@/api/toolExecute'
import ToolExecutionSection from '@/components/devconsole/ToolExecutionSection.vue'
import type { DryRunResultData, ExecuteResultData } from '@/types/api/toolExecute'

function dryData(): DryRunResultData {
  return {
    canonicalName: 'route_governance_read', exists: true, riskTier: 'R0',
    decision: 'would_allow', reasonCodes: [], policyNotes: [], redactedArgumentsPreview: {},
    forbiddenFields: [], missingRequiredFields: [], executionAllowed: false, dispatchAllowed: false,
    providerSchemaAllowed: false, auditWritten: true, dryRunDecisionDigest: 'sha256:abc',
    digestAlgorithm: 'sha256', digestPackageVersion: '1', canonicalizationVersion: 'json-sort-v1',
    confirmationToken: 'tok_secret', confirmationTokenId: 'ctok_1', confirmationTokenExpiresAt: '2026-06-15T01:00:00+00:00',
  }
}

function execData(): ExecuteResultData {
  return {
    canonicalName: 'route_governance_read', exists: true, riskTier: 'R0',
    decision: 'route_governance_read_execution_completed', reasonCodes: [], policyNotes: [],
    errorCode: null, executionAllowed: false, dispatchAllowed: false, providerSchemaAllowed: false,
    toolHandlerCalled: true, providerApiCalled: false, executionStarted: true, executionCompleted: true,
    executionAttempted: true, postExecutionAuditId: 'pexa_xyz123', executionStatus: 'completed',
    toolResult: { type: 'route_governance_read', message: 'ok', result: { openApiPaths: 34 } },
  } as ExecuteResultData
}

describe('ToolExecutionSection (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(runDryRun).mockReset()
    vi.mocked(executeTool).mockReset()
    window.localStorage.clear()
  })

  it('renders the reused ToolExecutePanel with the six-tool selector', () => {
    const wrapper = mount(ToolExecutionSection)
    const select = wrapper.find('#tool-execute-canonical')
    expect(select.exists()).toBe(true)
    expect(select.findAll('option')).toHaveLength(6)
  })

  it('exposes no API-key / shell-command inputs', () => {
    const wrapper = mount(ToolExecutionSection)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    expect(wrapper.html()).not.toMatch(/api[_-]?key/i)
  })

  it('shows the result→audit cross-reference strip after a completed execute', async () => {
    vi.mocked(runDryRun).mockResolvedValue({ data: dryData(), meta: { requestId: 'r1', timestamp: '2026-06-15T00:00:00+00:00' } })
    vi.mocked(executeTool).mockResolvedValue({ data: execData(), meta: { requestId: 'r2', timestamp: '2026-06-15T00:00:00+00:00' } })
    const wrapper = mount(ToolExecutionSection)
    // No cross-nav strip before any execute.
    expect(wrapper.find('[aria-label="Cross-reference to Audit Viewer"]').exists()).toBe(false)

    await wrapper.find('#tool-execute-canonical').setValue('route_governance_read')
    await wrapper.find('#tool-execute-dry-run').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('would_allow'))
    await wrapper.find('#tool-execute-run').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Completed'))

    const strip = wrapper.find('[aria-label="Cross-reference to Audit Viewer"]')
    expect(strip.exists()).toBe(true)
    // The post-exec audit id is surfaced as a clickable cross-nav chip.
    expect(strip.find('[data-testid="dev-audit-id-link"]').exists()).toBe(true)
  })
})
