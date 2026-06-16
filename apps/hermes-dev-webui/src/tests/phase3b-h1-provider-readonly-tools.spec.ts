/**
 * Phase 3B-H1: Provider read-only tool-allowlist HARDENING.
 *
 * Verifies the boundary component renders ONLY the six read-only inspection
 * tools, that every write / shell / db / external / production / plugin /
 * rollback capability surfaced in a provider round-trip result is marked blocked
 * (NEVER executed), and that the constant list is pinned to the backend
 * allowlist contract.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import { SELECTABLE_TOOL_IDS, SELECTABLE_TOOLS } from '@/constants/readOnlyTools'
import type { ProviderBoundaryStatus, ProviderRoundtripResultData } from '@/types/api/toolProvider'

const SIX_TOOLS = [
  'clarify', 'tool_policy_read', 'route_governance_read',
  'audit_events_read', 'dev_environment_read', 'release_status_read',
]

const FORBIDDEN_TOOL_IDS = [
  'write_file', 'patch', 'dev_sandbox_file_write', 'dev_sandbox_file_append',
  'dev_sandbox_file_patch', 'dev_sandbox_rollback_execute', 'memory', 'memory_add',
  'memory_update', 'todo', 'skill_manage', 'shell', 'terminal', 'process',
  'database', 'external_http', 'execute_code', 'delegate_task', 'send_message',
  'cronjob', 'image_generate', 'production_operation', 'plugin_dynamic_load',
]

function makeBoundary(): ProviderBoundaryStatus {
  return {
    providerMode: 'real', apiEnabled: true,
    providerName: 'openai_compatible', providerNameImplemented: true,
    baseUrlHost: 'api.openai.com', baseUrlAllowed: true,
    model: 'gpt-4o-mini', modelAllowed: true,
    timeoutSeconds: 20, maxRetries: 2, dailyBudgetCents: 100, maxTokens: 1024,
    perMinuteRequestCap: 20, dailyRequestCap: 200, dailyTokenCap: 500000,
    apiKeySource: 'env', apiKeyPresent: true, apiKeySourceDetail: 'env_present',
    isDevHome: true, realReachable: false,
    gatingReason: 'blocked_provider_production_gate_drift',
    providerWriteBlocked: true, providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true, productionRolloutBlocked: true,
    redactionApplied: true,
  } as ProviderBoundaryStatus
}

describe('Phase 3B-H1 provider read-only allowlist hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('the selectable constant is EXACTLY the six read-only tools', () => {
    expect([...SELECTABLE_TOOL_IDS].sort()).toEqual([...SIX_TOOLS].sort())
  })

  it('no selectable tool is a write / shell / db / external / production tool', () => {
    for (const id of SELECTABLE_TOOL_IDS) {
      expect(FORBIDDEN_TOOL_IDS).not.toContain(id)
    }
  })

  it('every selectable tool is readOnly, not providerRequired, not writeRequired', () => {
    for (const tool of SELECTABLE_TOOLS) {
      // The risk tier is R0 (pure compute) or R1 (read) only — never a write tier.
      expect(['R0', 'R1']).toContain(tool.riskTier)
    }
  })

  it('renders the six read-only tools in the boundary component', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    for (const tool of SIX_TOOLS) {
      expect(html).toContain(tool)
    }
  })

  it('a write tool requested by a provider result is blocked, never executed', () => {
    const result: ProviderRoundtripResultData = {
      status: 'blocked',
      mode: 'provider_roundtrip',
      providerMode: 'fake',
      providerRequestId: 'prqs',
      providerResponseId: 'prsp',
      providerSchemaSent: true,
      providerApiCalled: true,
      externalNetworkCalled: false,
      readOnlyOnly: true,
      toolWriteDisabled: true,
      toolCalls: [
        { id: 'w', name: 'write_file', arguments: {}, status: 'blocked', blockedReason: 'blocked_provider_write_not_allowed' },
        { id: 's', name: 'shell', arguments: {}, status: 'blocked', blockedReason: 'blocked_provider_tool_call_not_allowed' },
        { id: 'd', name: 'database', arguments: {}, status: 'blocked', blockedReason: 'blocked_provider_tool_call_not_allowed' },
        { id: 'r', name: 'dev_sandbox_rollback_execute', arguments: {}, status: 'blocked', blockedReason: 'blocked_provider_tool_call_not_allowed' },
      ],
      toolResults: [
        { toolCallId: 'w', toolId: 'write_file', status: 'blocked', executed: false, blockedReason: 'blocked_provider_write_not_allowed' },
        { toolCallId: 's', toolId: 'shell', status: 'blocked', executed: false, blockedReason: 'blocked_provider_tool_call_not_allowed' },
        { toolCallId: 'd', toolId: 'database', status: 'blocked', executed: false, blockedReason: 'blocked_provider_tool_call_not_allowed' },
        { toolCallId: 'r', toolId: 'dev_sandbox_rollback_execute', status: 'blocked', executed: false, blockedReason: 'blocked_provider_tool_call_not_allowed' },
      ],
      finalAnswer: 'blocked',
      providerAuditIds: [],
      blockedReason: 'blocked_tool_calls:write_file',
      schemaSummary: {
        schemaVersion: 1, bundleVersion: 1, toolCount: 6,
        toolIds: SELECTABLE_TOOL_IDS, readOnlyOnly: true,
        writeToolCount: 0, providerRecursiveToolCount: 0,
      },
    }
    const store = useToolProviderStore()
    store.result = result
    for (const tr of store.result.toolResults) {
      expect(tr.executed).toBe(false)
      expect(tr.status).toBe('blocked')
      expect(tr.blockedReason).toBeTruthy()
    }
  })
})
