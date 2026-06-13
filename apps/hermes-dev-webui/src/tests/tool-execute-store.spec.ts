/**
 * Tests for the Tool Execute Pinia store (Phase 1G-04-30).
 *
 * Covers the dry-run → confirm → execute state machine and the
 * confirmation-token safety invariants (raw token never persisted,
 * never exposed in store state).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolExecuteStore } from '@/stores/toolExecute'

// ── Mock the API module ──

vi.mock('@/api/toolExecute', () => ({
  runDryRun: vi.fn(),
  executeTool: vi.fn(),
}))

import { runDryRun, executeTool } from '@/api/toolExecute'
import type { DryRunResultData, ExecuteResultData } from '@/types/api/toolExecute'

// ── Test data factories ──

function makeDryRunData(overrides: Partial<DryRunResultData> = {}): DryRunResultData {
  return {
    canonicalName: 'clarify',
    exists: true,
    riskTier: 'R0',
    decision: 'would_allow',
    reasonCodes: [],
    policyNotes: [],
    redactedArgumentsPreview: {},
    forbiddenFields: [],
    missingRequiredFields: [],
    executionAllowed: false,
    dispatchAllowed: false,
    providerSchemaAllowed: false,
    auditWritten: true,
    dryRunDecisionDigest: 'sha256:abcdef1234567890',
    digestAlgorithm: 'sha256',
    digestPackageVersion: '1',
    canonicalizationVersion: 'json-sort-v1',
    confirmationToken: 'raw-confirmation-token-secret',
    confirmationTokenId: 'ctok_abc',
    confirmationTokenExpiresAt: '2026-06-13T01:00:00+00:00',
    ...overrides,
  }
}

function makeExecuteData(overrides: Partial<ExecuteResultData> = {}): ExecuteResultData {
  return {
    canonicalName: 'clarify',
    exists: true,
    riskTier: 'R0',
    decision: 'clarify_execution_completed',
    reasonCodes: [],
    policyNotes: [],
    errorCode: null,
    executionAllowed: false,
    dispatchAllowed: false,
    providerSchemaAllowed: false,
    toolHandlerCalled: true,
    providerApiCalled: false,
    executionStarted: true,
    executionCompleted: true,
    executionAttempted: true,
    handlerCallId: 'thc_abc',
    handlerCallStatus: 'completed',
    executionStatus: 'completed',
    postExecutionAuditId: 'pexa_abc',
    postExecutionAuditStatus: 'written',
    sideEffects: {
      providerSchemaSent: false,
      providerApiCalled: false,
      externalSideEffects: false,
    },
    toolResult: { type: 'clarify', message: 'Which option?', questions: [] },
    ...overrides,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
})

describe('toolExecuteStore — initial state', () => {
  it('starts idle with canonicalName=clarify', () => {
    const store = useToolExecuteStore()
    expect(store.status).toBe('idle')
    expect(store.canonicalName).toBe('clarify')
    expect(store.executeResult).toBeNull()
    expect(store.dryRunResult).toBeNull()
  })

  it('does not expose a raw confirmation token property', () => {
    const store = useToolExecuteStore()
    // The raw token must never be a property on the store.
    expect((store as unknown as Record<string, unknown>).confirmationToken).toBeUndefined()
    expect((store as unknown as Record<string, unknown>)._confirmationToken).toBeUndefined()
  })
})

describe('toolExecuteStore — dry-run flow', () => {
  it('transitions to confirmation_required on a would_allow dry-run with token', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    expect(store.status).toBe('confirmation_required')
    expect(store.dryRunResult?.decision).toBe('would_allow')
    expect(store.confirmationTokenId).toBe('ctok_abc')
    expect(store.dryRunDecisionDigest).toBe('sha256:abcdef1234567890')
  })

  it('never persists the raw token to localStorage', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    const stored = JSON.stringify(Object.keys(localStorage))
    expect(stored).not.toContain('raw-confirmation-token-secret')
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      expect(localStorage.getItem(k ?? '')).not.toContain('raw-confirmation-token-secret')
    }
  })

  it('sets error state on dry-run failure', async () => {
    vi.mocked(runDryRun).mockRejectedValue({
      code: 'NETWORK_ERROR',
      message: 'Unable to connect.',
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    expect(store.status).toBe('error')
    expect(store.error).toBe('Unable to connect.')
  })

  it('uses dry_run_ready when no token is issued', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData({ confirmationToken: null, confirmationTokenId: null }),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    expect(store.status).toBe('dry_run_ready')
  })
})

describe('toolExecuteStore — execute flow', () => {
  it('blocks execute without a confirmation', async () => {
    const store = useToolExecuteStore()
    await store.runExecute()
    expect(store.status).toBe('error')
    expect(store.error).toContain('confirmation')
  })

  it('transitions to completed on clarify_execution_completed', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData(),
      meta: { requestId: 'r2', timestamp: 't2' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    await store.runExecute()
    expect(store.status).toBe('completed')
    expect(store.isCompleted).toBe(true)
    expect(store.executeResult?.handlerCallId).toBe('thc_abc')
    expect(store.executeResult?.postExecutionAuditId).toBe('pexa_abc')
    expect(store.sideEffects?.providerSchemaSent).toBe(false)
    expect(store.sideEffects?.providerApiCalled).toBe(false)
    expect(store.sideEffects?.externalSideEffects).toBe(false)
  })

  it('transitions to blocked on a non-completed decision', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData({ decision: 'blocked_tool_handler_call_not_enabled', toolHandlerCalled: false, executionStarted: false, executionCompleted: false, handlerCallId: null, postExecutionAuditId: null }),
      meta: { requestId: 'r2', timestamp: 't2' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    await store.runExecute()
    expect(store.status).toBe('blocked')
    expect(store.isBlocked).toBe(true)
    expect(store.isHandlerCallBlocked).toBe(true)
    expect(store.executeDecision).toBe('blocked_tool_handler_call_not_enabled')
  })

  it('does not allow a second execute after completion (token consumed)', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    vi.mocked(executeTool).mockResolvedValue({
      data: makeExecuteData(),
      meta: { requestId: 'r2', timestamp: 't2' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    await store.runExecute()
    expect(store.status).toBe('completed')
    // Second execute without re-running dry-run must block at the store guard.
    await store.runExecute()
    expect(store.status).toBe('error')
  })
})

describe('toolExecuteStore — reset', () => {
  it('clears all state', async () => {
    vi.mocked(runDryRun).mockResolvedValue({
      data: makeDryRunData(),
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    const store = useToolExecuteStore()
    await store.runDryRun()
    store.reset()
    expect(store.status).toBe('idle')
    expect(store.dryRunResult).toBeNull()
    expect(store.confirmationTokenId).toBeNull()
  })
})
