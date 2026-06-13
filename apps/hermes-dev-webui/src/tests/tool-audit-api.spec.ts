/**
 * Tests for the Tool Audit + Tool Execute API client modules (Phase 1G-04-30).
 *
 * Covers query string construction, the GET/POST dispatch, and the
 * invariant that the raw confirmation token passes straight through to
 * execute without being logged or persisted.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

import { getAuditEvents } from '@/api/toolAudit'
import { runDryRun, executeTool } from '@/api/toolExecute'

// ── Mock the shared client ──

vi.mock('@/api/client', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  isDevApiError: vi.fn((err: unknown) =>
    err !== null && typeof err === 'object' && 'code' in (err as object),
  ),
}))

import { apiGet, apiPost } from '@/api/client'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('toolAudit API', () => {
  it('builds a GET request with auditKind and optional params', async () => {
    vi.mocked(apiGet).mockResolvedValue({
      data: {
        auditKind: 'post_execution',
        items: [],
        nextCursor: null,
        limit: 50,
        hasMore: false,
        skippedMalformed: 0,
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    await getAuditEvents({ auditKind: 'post_execution', limit: 25, canonicalName: 'clarify' })
    expect(apiGet).toHaveBeenCalledOnce()
    const path = vi.mocked(apiGet).mock.calls[0]![0]
    expect(path).toContain('/api/dev/v1/tools/audit-events')
    expect(path).toContain('auditKind=post_execution')
    expect(path).toContain('limit=25')
    expect(path).toContain('canonicalName=clarify')
  })

  it('omits empty optional params', async () => {
    vi.mocked(apiGet).mockResolvedValue({
      data: {
        auditKind: 'dry_run',
        items: [],
        nextCursor: null,
        limit: 50,
        hasMore: false,
        skippedMalformed: 0,
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    await getAuditEvents({ auditKind: 'dry_run' })
    const path = vi.mocked(apiGet).mock.calls[0]![0]
    expect(path).toContain('auditKind=dry_run')
    expect(path).not.toContain('cursor=')
    expect(path).not.toContain('canonicalName=')
  })
})

describe('toolExecute API', () => {
  it('dispatches a POST dry-run with issueConfirmationToken', async () => {
    vi.mocked(apiPost).mockResolvedValue({
      data: {
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
        dryRunDecisionDigest: 'sha256:abc',
        digestAlgorithm: 'sha256',
        digestPackageVersion: '1',
        canonicalizationVersion: 'json-sort-v1',
      },
      meta: { requestId: 'r1', timestamp: 't1' },
    })
    await runDryRun({ canonicalName: 'clarify', issueConfirmationToken: true })
    expect(apiPost).toHaveBeenCalledOnce()
    const callArgs = vi.mocked(apiPost).mock.calls[0]!
    const path = callArgs[0]
    const body = callArgs[1]
    expect(path).toContain('/api/dev/v1/tools/dry-run')
    expect(body).toMatchObject({ canonicalName: 'clarify', issueConfirmationToken: true })
  })

  it('passes the raw confirmation token straight through to execute (no logging)', async () => {
    vi.mocked(apiPost).mockResolvedValue({
      data: {
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
      },
      meta: { requestId: 'r2', timestamp: 't2' },
    })
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    await executeTool({
      canonicalName: 'clarify',
      dryRunRequestId: 'dr_1',
      dryRunDecisionDigest: 'sha256:abc',
      confirmationToken: 'raw-secret-in-memory-only',
    })
    const body = vi.mocked(apiPost).mock.calls[0]![1]
    expect(body).toMatchObject({ confirmationToken: 'raw-secret-in-memory-only' })
    // The token must never be logged.
    expect(consoleSpy).not.toHaveBeenCalled()
    expect(JSON.stringify(consoleSpy.mock.calls)).not.toContain('raw-secret-in-memory-only')
    consoleSpy.mockRestore()
  })
})
