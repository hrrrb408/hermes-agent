/**
 * Type definitions for the Phase 2C controlled write tools.
 *
 * Models the write-preview (dry-run) response returned by
 * POST /api/dev/v1/tools/dry-run with body.mode='write_preview' and the write
 * execution response returned by POST /api/dev/v1/tools/execute with
 * body.mode='write'. Both reuse existing routes — no new route is added.
 *
 * Safety:
 *   - No API key, raw token, full tokenHash, raw arguments, or secret ever
 *     appears in these types. The backend redacts everything before return.
 *   - The confirmation token is an opaque single-use credential bound to the
 *     write plan + argument digest; it carries no secret material.
 */

/** The four Phase 2C controlled write tools. */
export type WriteToolId =
  | 'dev_sandbox_file_write'
  | 'dev_sandbox_file_append'
  | 'dev_sandbox_file_patch'
  | 'dev_sandbox_file_readback'

export const WRITE_TOOL_IDS: readonly WriteToolId[] = [
  'dev_sandbox_file_write',
  'dev_sandbox_file_append',
  'dev_sandbox_file_patch',
  'dev_sandbox_file_readback',
]

/** Operation performed by a write tool. */
export type WriteOperation = 'create_or_replace' | 'append' | 'patch' | 'readback'

/** Arguments for a write tool. */
export interface WriteToolArguments {
  readonly targetPath: string
  readonly content?: string
  readonly mode?: 'create_or_replace'
  readonly search?: string
  readonly replace?: string
}

/** Readback summary embedded in a completed write result. */
export interface WriteReadbackView {
  readonly exists: boolean
  readonly sizeBytes: number
  readonly contentHash: string | null
  readonly snippet: string
}

/** Safe write-preview (dry-run) response data. */
export interface WritePreviewResultData {
  readonly mode: 'write_preview'
  readonly writePlanId: string
  readonly writePreviewId: string
  readonly toolId: WriteToolId
  readonly operation: WriteOperation
  readonly sandboxRootLabel: string
  readonly targetRelativePath: string
  readonly beforeExists: boolean
  readonly beforeHash: string | null
  readonly afterHash: string | null
  readonly contentDigest: string | null
  readonly diffPreview: string
  readonly riskTier: string
  readonly readOnly: false
  readonly writeRequired: true
  readonly localSideEffects: true
  readonly externalSideEffects: false
  readonly providerRequired: false
  readonly requiresConfirmation: true
  readonly requiresWriteEnablement: true
  readonly requiresRollbackPlan: true
  readonly rollbackPreview: string
  readonly blocked: boolean
  readonly blockedReason: string | null
  readonly warnings: readonly string[]
  readonly argumentDigest: string
  readonly confirmationToken: string | null
  readonly requiresUserConfirmation: boolean
  readonly writeExecuted: false
}

/** Request body for the write-preview branch of the dry-run route. */
export interface WritePreviewRequest {
  readonly mode: 'write_preview'
  readonly toolId: WriteToolId
  readonly arguments: WriteToolArguments
}

/** Safe write execution response data. */
export interface WriteExecuteResultData {
  readonly mode: 'write'
  readonly executionId: string
  readonly toolId: WriteToolId
  readonly status: 'completed' | 'blocked'
  readonly writePlanId: string | null
  readonly writePreviewId: string | null
  readonly rollbackId: string | null
  readonly operation: WriteOperation
  readonly targetRelativePath: string
  readonly beforeHash: string | null
  readonly afterHash: string | null
  readonly contentDigest: string | null
  readonly bytesWritten: number
  readonly linesChanged: number
  readonly diffPreview: string
  readonly rollbackAvailable: boolean
  readonly readOnly: false
  readonly writeRequired: true
  readonly localSideEffects: true
  readonly externalSideEffects: false
  readonly providerSchemaSent: false
  readonly providerApiCalled: false
  readonly externalNetworkCalled: false
  readonly blockedReason: string | null
  readonly preExecutionAuditId: string | null
  readonly postExecutionAuditId: string | null
  readonly warnings: readonly string[]
  readonly readback?: WriteReadbackView
}

/** Request body for the write branch of the execute route. */
export interface WriteExecuteRequest {
  readonly mode: 'write'
  readonly toolId: WriteToolId
  readonly arguments: WriteToolArguments
  readonly writePlanId: string
  readonly confirmationToken: string
  readonly argumentDigest: string
}
