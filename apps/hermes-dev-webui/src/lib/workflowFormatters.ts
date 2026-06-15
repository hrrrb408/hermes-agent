/**
 * Phase 3A Workflow formatters.
 *
 * Pure helpers that render workflow step types / statuses / safety boundary
 * values into safe, localized, human-readable strings. No secrets, no tokens,
 * no raw arguments are ever formatted here — only public metadata.
 */

import type {
  WorkflowExecutionStatus,
  WorkflowStepStatus,
  WorkflowStepType,
  WorkflowSafetyBoundary,
} from '@/lib/workflowTypes'

const STEP_TYPE_LABELS: Readonly<Record<WorkflowStepType, string>> = {
  read_only_tool: 'Read-only tool',
  fake_provider_roundtrip: 'Fake provider round-trip',
  sandbox_write_preview: 'Sandbox write preview',
  rollback_reference: 'Rollback reference',
  manual_note: 'Manual note',
  audit_query: 'Audit query',
}

export function formatStepType(type: WorkflowStepType | string | null | undefined): string {
  if (!type) return 'Unknown'
  return STEP_TYPE_LABELS[type as WorkflowStepType] ?? type
}

const STEP_STATUS_LABELS: Readonly<Record<WorkflowStepStatus, string>> = {
  draft: 'Draft',
  planned: 'Planned',
  previewed: 'Previewed',
  approval_required: 'Approval required',
  approved: 'Approved',
  ready: 'Ready',
  running: 'Running',
  completed: 'Completed',
  blocked: 'Blocked',
  failed: 'Failed',
  skipped: 'Skipped',
}

export function formatStepStatus(
  status: WorkflowStepStatus | string | null | undefined,
): string {
  if (!status) return '—'
  return STEP_STATUS_LABELS[status as WorkflowStepStatus] ?? status
}

/** Coarse tone for a step status, for non-color badge rendering. */
export function stepStatusTone(
  status: WorkflowStepStatus | string | null | undefined,
): 'positive' | 'negative' | 'neutral' | 'progress' {
  switch (status) {
    case 'completed':
    case 'approved':
    case 'ready':
      return 'positive'
    case 'blocked':
    case 'failed':
      return 'negative'
    case 'running':
    case 'previewed':
    case 'approval_required':
      return 'progress'
    default:
      return 'neutral'
  }
}

const EXEC_STATUS_LABELS: Readonly<Record<WorkflowExecutionStatus, string>> = {
  draft: 'Draft',
  running: 'Running',
  paused: 'Paused',
  completed: 'Completed',
  failed: 'Failed',
  blocked: 'Blocked',
}

export function formatExecutionStatus(
  status: WorkflowExecutionStatus | string | null | undefined,
): string {
  if (!status) return '—'
  return EXEC_STATUS_LABELS[status as WorkflowExecutionStatus] ?? status
}

/** Map a safety-boundary capability value to a safe label. */
export function formatBoundaryValue(value: string | null | undefined): string {
  if (!value) return 'unknown'
  switch (value) {
    case 'blocked':
      return 'Blocked'
    case 'allowed':
      return 'Allowed'
    case 'required':
      return 'Required'
    case 'enabled':
      return 'Enabled'
    default:
      return value
  }
}

/** The ordered capability rows for the safety boundary panel. */
export interface BoundaryRow {
  readonly key: keyof WorkflowSafetyBoundary
  readonly label: string
}

export const BOUNDARY_ROWS: readonly BoundaryRow[] = [
  { key: 'realProvider', label: 'Real provider' },
  { key: 'providerAutoWrite', label: 'Provider auto-write' },
  { key: 'autonomousWrite', label: 'Autonomous write' },
  { key: 'writeExecute', label: 'Write execute' },
  { key: 'rollbackExecute', label: 'Rollback execute' },
  { key: 'shellCommand', label: 'Shell command' },
  { key: 'databaseMutation', label: 'Database mutation' },
  { key: 'externalServiceWrite', label: 'External service write' },
  { key: 'productionRollout', label: 'Production rollout' },
  { key: 'sandboxWritePreview', label: 'Sandbox write preview' },
  { key: 'rollbackReference', label: 'Rollback reference' },
  { key: 'fakeProvider', label: 'Fake provider' },
  { key: 'manualApproval', label: 'Manual approval' },
  { key: 'audit', label: 'Audit' },
] as const

/** Whether a step may be executed from the workflow (preview/reference only
 *  for write/rollback — never the actual write/rollback). */
export function isExecutableStepType(
  type: WorkflowStepType | string | null | undefined,
): boolean {
  switch (type) {
    case 'read_only_tool':
    case 'fake_provider_roundtrip':
    case 'sandbox_write_preview':
    case 'rollback_reference':
    case 'manual_note':
    case 'audit_query':
      return true
    default:
      return false
  }
}
