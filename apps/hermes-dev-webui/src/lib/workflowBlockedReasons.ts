/**
 * Phase 3A Workflow blocked-reason catalogue.
 *
 * Lists the backend ``blocked_workflow_*`` reason codes the workflow surface
 * can emit, with the same shape the unified BlockedReasonPanel consumes. The
 * canonical entries are registered into the shared
 * :mod:`@/lib/blockedReasons` catalogue (single source of truth) so the panel
 * renders them with a safe explanation + next action. This module is the
 * workflow-specific index used by tests and the safety boundary UI.
 */

import { lookupBlockedReason, type BlockedReasonInfo } from '@/lib/blockedReasons'

/** Every workflow blocked-reason code emitted by the backend. */
export const WORKFLOW_BLOCKED_REASONS: readonly string[] = [
  'blocked_workflow_real_provider_not_allowed',
  'blocked_workflow_autonomous_write_not_allowed',
  'blocked_workflow_provider_write_not_allowed',
  'blocked_workflow_rollback_execute_not_allowed',
  'blocked_workflow_shell_not_allowed',
  'blocked_workflow_database_not_allowed',
  'blocked_workflow_external_service_not_allowed',
  'blocked_workflow_production_not_allowed',
  'blocked_workflow_plugin_dynamic_load_not_allowed',
  'blocked_workflow_step_type_not_allowed',
  'blocked_workflow_approval_required',
  'blocked_workflow_approval_expired',
  'blocked_workflow_approval_scope_mismatch',
  'blocked_workflow_approval_step_mismatch',
  'blocked_workflow_approval_digest_mismatch',
  'blocked_workflow_approval_already_used',
  'blocked_workflow_unsafe_path_not_allowed',
  'blocked_workflow_secret_input_not_allowed',
  'blocked_workflow_raw_token_input_not_allowed',
  'blocked_workflow_invalid_input',
  'blocked_workflow_store_unavailable',
] as const

/** Look up a workflow blocked reason (graceful fallback for unknown codes). */
export function lookupWorkflowBlockedReason(
  code: string | null | undefined,
): BlockedReasonInfo {
  return lookupBlockedReason(code)
}

/** True when *code* is a known workflow blocked reason. */
export function isWorkflowBlockedReason(
  code: string | null | undefined,
): boolean {
  return !!code && WORKFLOW_BLOCKED_REASONS.includes(code)
}
