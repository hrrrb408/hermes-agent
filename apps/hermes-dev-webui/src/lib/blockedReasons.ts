/**
 * Unified blocked-reason catalogue (Phase 2E).
 *
 * Maps the backend's `blockedReason` strings to a human-readable explanation,
 * a safe next action, and a severity. Consumed by BlockedReasonPanel so every
 * console surface (execute / write / rollback / provider / audit) presents
 * blocked outcomes consistently and never suggests bypassing a safety boundary.
 *
 * The map is open-ended (Record<string, ...>) with a graceful fallback for
 * unknown codes so future backend additions degrade to a generic, safe message
 * rather than throwing or rendering a raw code with no guidance.
 */

export type BlockedReasonSeverity = 'info' | 'warn' | 'danger'

export type BlockedReasonSurface =
  | 'execute'
  | 'write'
  | 'rollback'
  | 'provider'
  | 'confirmation'
  | 'audit'
  | 'unknown'

export interface BlockedReasonInfo {
  /** The canonical backend code. */
  readonly code: string
  /** Short human-readable title. */
  readonly title: string
  /** Plain-language explanation of WHY this block fired. */
  readonly explanation: string
  /** The one safe next action the operator may take (never a bypass). */
  readonly safeNextAction: string
  /** Severity drives the badge tone. */
  readonly severity: BlockedReasonSeverity
  /** Which workflow surface this block belongs to. */
  readonly surface: BlockedReasonSurface
}

const CATALOGUE: Readonly<Record<string, BlockedReasonInfo>> = {
  // ── Execute surface ──
  blocked_tool_handler_call_not_enabled: {
    code: 'blocked_tool_handler_call_not_enabled',
    title: 'Handler call not enabled',
    explanation: 'Tool execution reached the policy gate but the handler-call gate is off, so the handler is not invoked.',
    safeNextAction: 'Enable the controlled-execution gate (HERMES_TOOL_HANDLER_CALL_ENABLED) in the dev environment if you intend to run this tool.',
    severity: 'info',
    surface: 'execute',
  },

  // ── Write surface ──
  blocked_write_execution_not_enabled: {
    code: 'blocked_write_execution_not_enabled',
    title: 'Write execution not enabled',
    explanation: 'The dev-sandbox write execution gate is off, so the write preview was produced but never applied.',
    safeNextAction: 'Set HERMES_TOOL_WRITE_EXECUTION_ENABLED=1 in the dev environment to execute writes inside the sandbox only.',
    severity: 'info',
    surface: 'write',
  },
  blocked_write_absolute_path: {
    code: 'blocked_write_absolute_path',
    title: 'Absolute path rejected',
    explanation: 'The target path is absolute. Write tools only accept sandbox-relative paths.',
    safeNextAction: 'Use a relative path like notes/example.md instead of an absolute path.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_path_traversal: {
    code: 'blocked_write_path_traversal',
    title: 'Path traversal rejected',
    explanation: 'The target path contains .. or other traversal sequences that would escape the sandbox root.',
    safeNextAction: 'Provide a flat or nested relative path that stays inside the sandbox root.',
    severity: 'danger',
    surface: 'write',
  },
  blocked_write_symlink_escape: {
    code: 'blocked_write_symlink_escape',
    title: 'Symlink escape rejected',
    explanation: 'The resolved target escapes the sandbox root via a symlink.',
    safeNextAction: 'Choose a non-symlinked target inside the sandbox root.',
    severity: 'danger',
    surface: 'write',
  },
  blocked_write_forbidden_target: {
    code: 'blocked_write_forbidden_target',
    title: 'Forbidden target',
    explanation: 'The target matches a protected pattern (.env, .claude, .git, *.db, *.jsonl, *.log, test-results, node_modules, dist, state.db, …).',
    safeNextAction: 'Pick a sandbox target that is not a protected file or directory.',
    severity: 'danger',
    surface: 'write',
  },
  blocked_write_empty_path: {
    code: 'blocked_write_empty_path',
    title: 'Empty target path',
    explanation: 'No target path was supplied.',
    safeNextAction: 'Enter a sandbox-relative target path.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_binary_content: {
    code: 'blocked_write_binary_content',
    title: 'Binary content rejected',
    explanation: 'Write tools accept UTF-8 text only; the supplied content is not valid UTF-8 text.',
    safeNextAction: 'Provide UTF-8 text content only.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_content_too_large: {
    code: 'blocked_write_content_too_large',
    title: 'Content too large',
    explanation: 'The content or resulting file exceeds the per-write / per-file size limit.',
    safeNextAction: 'Reduce the content size and retry the preview.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_confirmation_required: {
    code: 'blocked_write_confirmation_required',
    title: 'Confirmation required',
    explanation: 'A write preview requires an explicit confirmation before execution.',
    safeNextAction: 'Run the preview, then confirm and execute with a fresh confirmation token.',
    severity: 'info',
    surface: 'write',
  },
  blocked_write_confirmation_already_used: {
    code: 'blocked_write_confirmation_already_used',
    title: 'Confirmation already used',
    explanation: 'The confirmation token was single-use and has already been consumed.',
    safeNextAction: 'Re-run the write preview to obtain a new confirmation token.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_confirmation_scope_mismatch: {
    code: 'blocked_write_confirmation_scope_mismatch',
    title: 'Confirmation scope mismatch',
    explanation: 'The confirmation token is bound to a different write plan or scope.',
    safeNextAction: 'Re-run the write preview so the token matches the current plan.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_digest_mismatch: {
    code: 'blocked_write_digest_mismatch',
    title: 'Argument digest mismatch',
    explanation: 'The arguments changed between preview and execute, invalidating the confirmation token.',
    safeNextAction: 'Re-run the write preview with the final arguments.',
    severity: 'warn',
    surface: 'write',
  },
  blocked_write_provider_auto_execute_denied: {
    code: 'blocked_write_provider_auto_execute_denied',
    title: 'Provider auto-execute denied',
    explanation: 'A provider requested a write but auto-execution is never permitted; provider writes are preview-only.',
    safeNextAction: 'Review the provider write preview and execute it manually through the sandbox write flow if intended.',
    severity: 'info',
    surface: 'provider',
  },

  // ── Rollback surface ──
  blocked_rollback_manifest_not_found: {
    code: 'blocked_rollback_manifest_not_found',
    title: 'Rollback manifest not found',
    explanation: 'No stored rollback manifest exists for the given rollback id.',
    safeNextAction: 'Check the rollback id and that the originating write was executed.',
    severity: 'warn',
    surface: 'rollback',
  },
  blocked_rollback_current_hash_mismatch: {
    code: 'blocked_rollback_current_hash_mismatch',
    title: 'Current hash mismatch',
    explanation: 'The sandbox file changed since the write, so a rollback would clobber unrelated state.',
    safeNextAction: 'Inspect the current sandbox state; the rollback is intentionally refused to avoid data loss.',
    severity: 'danger',
    surface: 'rollback',
  },
  blocked_rollback_digest_mismatch: {
    code: 'blocked_rollback_digest_mismatch',
    title: 'Rollback digest mismatch',
    explanation: 'The rollback arguments changed between preview and execute.',
    safeNextAction: 'Re-run the rollback preview.',
    severity: 'warn',
    surface: 'rollback',
  },
  blocked_rollback_write_not_enabled: {
    code: 'blocked_rollback_write_not_enabled',
    title: 'Write execution not enabled',
    explanation: 'Rollback reuses the write execution gate, which is currently off.',
    safeNextAction: 'Set HERMES_TOOL_WRITE_EXECUTION_ENABLED=1 in the dev environment.',
    severity: 'info',
    surface: 'rollback',
  },
  blocked_rollback_confirmation_required: {
    code: 'blocked_rollback_confirmation_required',
    title: 'Rollback confirmation required',
    explanation: 'A rollback requires an explicit confirmation before execution.',
    safeNextAction: 'Run the rollback preview, then confirm and execute.',
    severity: 'info',
    surface: 'rollback',
  },
  blocked_rollback_already_executed: {
    code: 'blocked_rollback_already_executed',
    title: 'Rollback already executed',
    explanation: 'This rollback manifest was already executed and is marked consumed.',
    safeNextAction: 'No action needed — the rollback has already been applied.',
    severity: 'info',
    surface: 'rollback',
  },
  blocked_rollback_target_escape: {
    code: 'blocked_rollback_target_escape',
    title: 'Rollback target escapes sandbox',
    explanation: 'The rollback target resolves outside the sandbox root.',
    safeNextAction: 'The manifest is inconsistent with the current sandbox; do not force it.',
    severity: 'danger',
    surface: 'rollback',
  },
  blocked_rollback_symlink_escape: {
    code: 'blocked_rollback_symlink_escape',
    title: 'Rollback symlink escape',
    explanation: 'The rollback target escapes the sandbox via a symlink.',
    safeNextAction: 'Resolve the symlink situation in the sandbox before retrying.',
    severity: 'danger',
    surface: 'rollback',
  },
  blocked_rollback_manifest_tampered: {
    code: 'blocked_rollback_manifest_tampered',
    title: 'Rollback manifest tampered',
    explanation: 'The stored manifest failed an integrity check.',
    safeNextAction: 'Do not trust the manifest; re-execute the original write to regenerate it if needed.',
    severity: 'danger',
    surface: 'rollback',
  },
  blocked_rollback_forbidden_target: {
    code: 'blocked_rollback_forbidden_target',
    title: 'Rollback forbidden target',
    explanation: 'The rollback target matches a protected pattern.',
    safeNextAction: 'The manifest targets a protected path and is refused for safety.',
    severity: 'danger',
    surface: 'rollback',
  },

  // ── Provider surface ──
  blocked_provider_real_mode_not_enabled: {
    code: 'blocked_provider_real_mode_not_enabled',
    title: 'Real provider blocked',
    explanation: 'Real provider mode is disabled by default and requires explicit enablement plus a dev-home + PID gate.',
    safeNextAction: 'Use the fake provider mode for offline deterministic round-trips; real mode stays blocked by design.',
    severity: 'info',
    surface: 'provider',
  },
  blocked_provider_api_key_missing: {
    code: 'blocked_provider_api_key_missing',
    title: 'Provider key missing',
    explanation: 'No provider API key is configured in the dev environment (the UI never accepts a key).',
    safeNextAction: 'Configure the provider key in the dev environment if you are authorized to enable real mode.',
    severity: 'info',
    surface: 'provider',
  },
  blocked_provider_mode_not_supported: {
    code: 'blocked_provider_mode_not_supported',
    title: 'Provider mode not supported',
    explanation: 'The selected provider mode is not supported in this build.',
    safeNextAction: 'Select disabled or fake mode.',
    severity: 'warn',
    surface: 'provider',
  },
  blocked_provider_not_dev_home: {
    code: 'blocked_provider_not_dev_home',
    title: 'Not dev home',
    explanation: 'Real provider mode requires the dev HERMES_HOME; the current home is not the dev instance.',
    safeNextAction: 'Run the dev console against the dev HERMES_HOME.',
    severity: 'danger',
    surface: 'provider',
  },
  blocked_provider_production_gate_drift: {
    code: 'blocked_provider_production_gate_drift',
    title: 'Production gate drift',
    explanation: 'The production gateway PID does not match the pinned baseline, so real provider mode is refused.',
    safeNextAction: 'Investigate the gateway PID drift; do not bypass the production gate.',
    severity: 'danger',
    surface: 'provider',
  },
  blocked_provider_recursive_tool: {
    code: 'blocked_provider_recursive_tool',
    title: 'Recursive tool blocked',
    explanation: 'A provider-requested tool would itself call a provider, which is not permitted.',
    safeNextAction: 'The tool schema excludes recursive provider tools by design.',
    severity: 'warn',
    surface: 'provider',
  },
  provider_mode_disabled: {
    code: 'provider_mode_disabled',
    title: 'Provider disabled',
    explanation: 'The provider is in disabled mode; no provider schema is sent and no provider API is called.',
    safeNextAction: 'Switch to fake mode for an offline deterministic round-trip.',
    severity: 'info',
    surface: 'provider',
  },

  // ── Confirmation token surface ──
  blocked_confirmation_token_expired: {
    code: 'blocked_confirmation_token_expired',
    title: 'Confirmation token expired',
    explanation: 'The file-backed confirmation token TTL has elapsed.',
    safeNextAction: 'Re-run the preview to obtain a fresh confirmation token.',
    severity: 'warn',
    surface: 'confirmation',
  },
  blocked_confirmation_token_already_used: {
    code: 'blocked_confirmation_token_already_used',
    title: 'Confirmation token already used',
    explanation: 'Persistent single-use replay protection has marked this token consumed.',
    safeNextAction: 'Re-run the preview to obtain a new confirmation token.',
    severity: 'warn',
    surface: 'confirmation',
  },
  blocked_confirmation_token_invalid: {
    code: 'blocked_confirmation_token_invalid',
    title: 'Confirmation token invalid',
    explanation: 'The confirmation token is malformed or unrecognized.',
    safeNextAction: 'Re-run the preview to obtain a valid confirmation token.',
    severity: 'warn',
    surface: 'confirmation',
  },
  blocked_confirmation_token_not_found: {
    code: 'blocked_confirmation_token_not_found',
    title: 'Confirmation token not found',
    explanation: 'No matching confirmation token exists in the file-backed store.',
    safeNextAction: 'Re-run the preview to issue a new confirmation token.',
    severity: 'warn',
    surface: 'confirmation',
  },
  blocked_confirmation_token_digest_mismatch: {
    code: 'blocked_confirmation_token_digest_mismatch',
    title: 'Token digest mismatch',
    explanation: 'The confirmation token does not match the submitted argument digest.',
    safeNextAction: 'Re-run the preview so the token and digest agree.',
    severity: 'warn',
    surface: 'confirmation',
  },
  blocked_confirmation_token_scope_mismatch: {
    code: 'blocked_confirmation_token_scope_mismatch',
    title: 'Token scope mismatch',
    explanation: 'The confirmation token scope (write / rollback / provider) does not match the request.',
    safeNextAction: 'Re-run the preview for the correct workflow scope.',
    severity: 'warn',
    surface: 'confirmation',
  },

  // ── Audit / store surface ──
  blocked_audit_cursor_invalid: {
    code: 'blocked_audit_cursor_invalid',
    title: 'Invalid audit cursor',
    explanation: 'The opaque audit query cursor is malformed or tampered with.',
    safeNextAction: 'Restart the query from the first page without a cursor.',
    severity: 'warn',
    surface: 'audit',
  },
  blocked_audit_cursor_query_mismatch: {
    code: 'blocked_audit_cursor_query_mismatch',
    title: 'Cursor query mismatch',
    explanation: 'The cursor was issued for a different query than the one now requested.',
    safeNextAction: 'Re-issue the query without the stale cursor.',
    severity: 'warn',
    surface: 'audit',
  },
  blocked_audit_limit_too_large: {
    code: 'blocked_audit_limit_too_large',
    title: 'Audit limit too large',
    explanation: 'The requested page size exceeds the allowed maximum.',
    safeNextAction: 'Choose a smaller page size (1–100).',
    severity: 'warn',
    surface: 'audit',
  },
  blocked_audit_query_invalid: {
    code: 'blocked_audit_query_invalid',
    title: 'Invalid audit query',
    explanation: 'One or more audit query parameters are invalid.',
    safeNextAction: 'Correct the filter values and re-run the query.',
    severity: 'warn',
    surface: 'audit',
  },
}

/** Generic fallback for unknown / future backend codes. Never throws. */
const UNKNOWN_FALLBACK: BlockedReasonInfo = {
  code: 'unknown_blocked_reason',
  title: 'Blocked for safety',
  explanation: 'The operation was blocked by a safety boundary. The specific reason code is not in the console catalogue yet.',
  safeNextAction: 'Review the operation and the safety boundaries; do not attempt to bypass the block.',
  severity: 'warn',
  surface: 'unknown',
}

/**
 * Look up a blocked reason by code. Returns a graceful fallback for unknown,
 * empty, or null codes so the UI never throws or renders raw text unguided.
 */
export function lookupBlockedReason(code: string | null | undefined): BlockedReasonInfo {
  if (!code) return UNKNOWN_FALLBACK
  return CATALOGUE[code] ?? { ...UNKNOWN_FALLBACK, code }
}

/** All known blocked-reason codes (for the catalogue/coverage tests). */
export const KNOWN_BLOCKED_REASONS: readonly string[] = Object.keys(CATALOGUE)

/** True when the code is in the catalogue (false for null/empty/unknown). */
export function isKnownBlockedReason(code: string | null | undefined): boolean {
  return !!code && code in CATALOGUE
}
