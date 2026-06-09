/**
 * Tests for Agent Run store (Phase 1F — Live Run).
 *
 * Covers:
 * - Initial state
 * - Form validation
 * - Run creation
 * - SSE event handling
 * - Stream text accumulation
 * - Usage tracking
 * - Terminal states
 * - Cancellation
 * - Reset/cleanup
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentRunStore } from '@/stores/agentRun'

// ── Mock the API module ──

vi.mock('@/api/agentRun', () => ({
  createAgentRun: vi.fn(),
  getAgentRunStatus: vi.fn(),
  cancelAgentRun: vi.fn(),
  connectAgentRunEvents: vi.fn(),
}))

import { createAgentRun } from '@/api/agentRun'

describe('AgentRunStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  // ── Initial State ──

  describe('initial state', () => {
    it('starts with null runId', () => {
      const store = useAgentRunStore()
      expect(store.runId).toBeNull()
    })

    it('starts with idle creation state', () => {
      const store = useAgentRunStore()
      expect(store.creationState).toBe('idle')
    })

    it('starts with disconnected connection', () => {
      const store = useAgentRunStore()
      expect(store.connectionStatus).toBe('disconnected')
    })

    it('starts with empty stream text', () => {
      const store = useAgentRunStore()
      expect(store.streamText).toBe('')
    })

    it('starts with no usage', () => {
      const store = useAgentRunStore()
      expect(store.usage).toBeNull()
    })

    it('starts with kill switch disabled', () => {
      const store = useAgentRunStore()
      expect(store.killSwitchEnabled).toBe(false)
    })
  })

  // ── Computed ──

  describe('computed', () => {
    it('isCreating is true when creationState is creating', () => {
      const store = useAgentRunStore()
      store.creationState = 'creating'
      expect(store.isCreating).toBe(true)
    })

    it('canCreate is true when idle', () => {
      const store = useAgentRunStore()
      store.creationState = 'idle'
      expect(store.canCreate).toBe(true)
    })

    it('canCreate is true when error', () => {
      const store = useAgentRunStore()
      store.creationState = 'error'
      expect(store.canCreate).toBe(true)
    })

    it('canCancel is false when no status', () => {
      const store = useAgentRunStore()
      expect(store.canCancel).toBe(false)
    })

    it('canCancel is true when running and not cancelling', () => {
      const store = useAgentRunStore()
      store.status = 'RUNNING'
      store.isCancelling = false
      expect(store.canCancel).toBe(true)
    })

    it('isTerminal is true for COMPLETED', () => {
      const store = useAgentRunStore()
      store.status = 'COMPLETED'
      expect(store.isTerminal).toBe(true)
    })

    it('isTerminal is true for CANCELLED', () => {
      const store = useAgentRunStore()
      store.status = 'CANCELLED'
      expect(store.isTerminal).toBe(true)
    })

    it('isTerminal is true for FAILED', () => {
      const store = useAgentRunStore()
      store.status = 'FAILED'
      expect(store.isTerminal).toBe(true)
    })

    it('isTerminal is false for RUNNING', () => {
      const store = useAgentRunStore()
      store.status = 'RUNNING'
      expect(store.isTerminal).toBe(false)
    })
  })

  // ── Form Validation ──

  describe('form validation (createRun)', () => {
    it('rejects empty session ID', async () => {
      const store = useAgentRunStore()
      store.form.sessionId = ''
      store.form.message = 'Hello'
      store.form.confirmationText = 'RUN'
      store.form.dryRunPreviewed = true
      store.form.acknowledgedCallLlm = true
      store.form.acknowledgedWriteSession = true

      await store.createRun()

      expect(store.creationState).toBe('error')
      expect(store.creationError).toContain('Session ID')
      expect(createAgentRun).not.toHaveBeenCalled()
    })

    it('rejects empty message', async () => {
      const store = useAgentRunStore()
      store.form.sessionId = 'session-1'
      store.form.message = ''
      store.form.confirmationText = 'RUN'
      store.form.dryRunPreviewed = true
      store.form.acknowledgedCallLlm = true
      store.form.acknowledgedWriteSession = true

      await store.createRun()

      expect(store.creationState).toBe('error')
      expect(store.creationError).toContain('Message')
      expect(createAgentRun).not.toHaveBeenCalled()
    })

    it('rejects wrong confirmation text', async () => {
      const store = useAgentRunStore()
      store.form.sessionId = 'session-1'
      store.form.message = 'Hello'
      store.form.confirmationText = 'WRONG'
      store.form.dryRunPreviewed = true
      store.form.acknowledgedCallLlm = true
      store.form.acknowledgedWriteSession = true

      await store.createRun()

      expect(store.creationState).toBe('error')
      expect(store.creationError).toContain('RUN')
      expect(createAgentRun).not.toHaveBeenCalled()
    })

    it('rejects when dry run not previewed', async () => {
      const store = useAgentRunStore()
      store.form.sessionId = 'session-1'
      store.form.message = 'Hello'
      store.form.confirmationText = 'RUN'
      store.form.dryRunPreviewed = false
      store.form.acknowledgedCallLlm = true
      store.form.acknowledgedWriteSession = true

      await store.createRun()

      expect(store.creationState).toBe('error')
      expect(store.creationError).toContain('Dry Run')
      expect(createAgentRun).not.toHaveBeenCalled()
    })

    it('rejects when effects not acknowledged', async () => {
      const store = useAgentRunStore()
      store.form.sessionId = 'session-1'
      store.form.message = 'Hello'
      store.form.confirmationText = 'RUN'
      store.form.dryRunPreviewed = true
      store.form.acknowledgedCallLlm = false
      store.form.acknowledgedWriteSession = true

      await store.createRun()

      expect(store.creationState).toBe('error')
      expect(store.creationError).toContain('effects')
      expect(createAgentRun).not.toHaveBeenCalled()
    })
  })

  // ── SSE Event Handling ──

  describe('SSE event handling', () => {
    it('accumulates message.delta events', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 1,
        timestamp: '2026-01-01T00:00:00Z',
        type: 'message.delta',
        data: { delta: 'Hello' },
      })

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 2,
        timestamp: '2026-01-01T00:00:01Z',
        type: 'message.delta',
        data: { delta: ' world' },
      })

      expect(store.streamText).toBe('Hello world')
    })

    it('updates usage from usage.updated event', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 3,
        timestamp: '2026-01-01T00:00:02Z',
        type: 'usage.updated',
        data: {
          usage: {
            inputTokens: 100,
            outputTokens: 50,
            totalTokens: 150,
            cachedTokens: null,
            cost: null,
            costEstimated: false,
          },
        },
      })

      expect(store.usage).toEqual({
        inputTokens: 100,
        outputTokens: 50,
        totalTokens: 150,
        cachedTokens: null,
        cost: null,
        costEstimated: false,
      })
    })

    it('sets status to COMPLETED on run.completed', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'
      store.status = 'RUNNING'

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 10,
        timestamp: '2026-01-01T00:00:10Z',
        type: 'run.completed',
        data: {},
      })

      expect(store.status).toBe('COMPLETED')
      expect(store.isTerminal).toBe(true)
      expect(store.connectionStatus).toBe('disconnected')
    })

    it('sets status to FAILED on run.failed with errorCode', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'
      store.status = 'RUNNING'

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 10,
        timestamp: '2026-01-01T00:00:10Z',
        type: 'run.failed',
        data: { errorCode: 'AGENT_PROVIDER_TIMEOUT' },
      })

      expect(store.status).toBe('FAILED')
      expect(store.error).toBe('AGENT_PROVIDER_TIMEOUT')
    })

    it('sets status to CANCELLED on run.cancelled', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'
      store.status = 'CANCELLING'

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 10,
        timestamp: '2026-01-01T00:00:10Z',
        type: 'run.cancelled',
        data: {},
      })

      expect(store.status).toBe('CANCELLED')
    })

    it('ignores events from different runId', () => {
      const store = useAgentRunStore()
      store.runId = 'run-correct'

      store.handleSSEEvent({
        runId: 'run-wrong',
        sequence: 1,
        timestamp: '2026-01-01T00:00:00Z',
        type: 'message.delta',
        data: { delta: 'Should be ignored' },
      })

      expect(store.streamText).toBe('')
    })

    it('tracks lastEventId', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'

      store.handleSSEEvent({
        runId: 'run-test',
        sequence: 42,
        timestamp: '2026-01-01T00:00:00Z',
        type: 'message.delta',
        data: { delta: 'test' },
      })

      expect(store.lastEventId).toBe('42')
    })
  })

  // ── Reset / Cleanup ──

  describe('reset and cleanup', () => {
    it('reset clears run state but keeps form defaults', () => {
      const store = useAgentRunStore()
      store.runId = 'run-test'
      store.status = 'COMPLETED'
      store.streamText = 'Some response'
      store.form.sessionId = 'session-1'
      store.form.message = 'Hello'

      store.reset()

      expect(store.runId).toBeNull()
      expect(store.status).toBeNull()
      expect(store.streamText).toBe('')
      expect(store.creationState).toBe('idle')
      // Form sessionId and message preserved
      expect(store.form.sessionId).toBe('session-1')
      expect(store.form.message).toBe('Hello')
      // Confirmation fields reset
      expect(store.form.confirmationText).toBe('')
      expect(store.form.dryRunPreviewed).toBe(false)
    })

    it('fullReset clears everything', () => {
      const store = useAgentRunStore()
      store.form.sessionId = 'session-1'
      store.form.message = 'Hello'

      store.fullReset()

      expect(store.form.sessionId).toBe('')
      expect(store.form.message).toBe('')
      expect(store.creationState).toBe('idle')
    })
  })

  // ── Safety ──

  describe('safety', () => {
    it('kill switch disabled is reflected in state', () => {
      const store = useAgentRunStore()
      expect(store.killSwitchEnabled).toBe(false)
    })
  })
})
