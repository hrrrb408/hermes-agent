/**
 * Runtime constants for Tool Policy types.
 *
 * These are read-only display constants derived from the TypeScript union types.
 * They do NOT modify any backend contract or Store safety semantics.
 */

import type { ToolCapability, ToolPolicyStatus, ToolRiskLevel } from './toolPolicy'

/** All known ToolCapability values for filter dropdowns. */
export const TOOL_CAPABILITIES: readonly ToolCapability[] = [
  'PURE_COMPUTE',
  'LOCAL_FILE_READ',
  'LOCAL_FILE_WRITE',
  'DATABASE_READ',
  'DATABASE_WRITE',
  'NETWORK_READ',
  'NETWORK_WRITE',
  'PROCESS_EXECUTION',
  'CODE_EXECUTION',
  'BROWSER_CONTROL',
  'DESKTOP_CONTROL',
  'CREDENTIAL_USE',
  'REMOTE_STATE_MUTATION',
  'MESSAGE_SEND',
  'MEDIA_GENERATION',
  'ADMINISTRATIVE_ACTION',
  'SCHEDULING',
  'SUB_AGENT_EXECUTION',
] as const

/** All known ToolPolicyStatus values for filter dropdowns. */
export const TOOL_POLICY_STATUSES: readonly ToolPolicyStatus[] = [
  'PERMANENTLY_DENIED',
  'CANDIDATE',
  'UNLISTED',
  'STATICALLY_ALLOWED',
] as const

/** All ToolRiskLevel values for filter dropdowns. */
export const TOOL_RISK_LEVELS: readonly ToolRiskLevel[] = [
  'R0',
  'R1',
  'R2',
  'R3',
  'R4',
  'R5',
] as const

/** Human-readable labels for risk levels. */
export const RISK_LABELS: Readonly<Record<ToolRiskLevel, string>> = {
  R0: 'Pure compute',
  R1: 'Local read-only',
  R2: 'External read-only',
  R3: 'State-changing',
  R4: 'High-impact execution',
  R5: 'Administrative / critical',
} as const

/** Human-readable labels for capability names. */
export const CAPABILITY_LABELS: Readonly<Record<ToolCapability, string>> = {
  PURE_COMPUTE: 'Pure compute',
  LOCAL_FILE_READ: 'Local file read',
  LOCAL_FILE_WRITE: 'Local file write',
  DATABASE_READ: 'Database read',
  DATABASE_WRITE: 'Database write',
  NETWORK_READ: 'Network read',
  NETWORK_WRITE: 'Network write',
  PROCESS_EXECUTION: 'Process execution',
  CODE_EXECUTION: 'Code execution',
  BROWSER_CONTROL: 'Browser control',
  DESKTOP_CONTROL: 'Desktop control',
  CREDENTIAL_USE: 'Credential use',
  REMOTE_STATE_MUTATION: 'Remote state mutation',
  MESSAGE_SEND: 'Message send',
  MEDIA_GENERATION: 'Media generation',
  ADMINISTRATIVE_ACTION: 'Administrative action',
  SCHEDULING: 'Scheduling',
  SUB_AGENT_EXECUTION: 'Sub-agent execution',
} as const

/** Human-readable labels for policy statuses. */
export const POLICY_STATUS_LABELS: Readonly<Record<ToolPolicyStatus, string>> = {
  PERMANENTLY_DENIED: 'Permanently denied',
  CANDIDATE: 'Candidate',
  UNLISTED: 'Unlisted',
  STATICALLY_ALLOWED: 'Statically allowed',
} as const
