/**
 * Phase 2E-H1 — Lens 5: Blocked Reason / Error State Boundary.
 *
 * Pins the contract that the frontend blocked-reason catalogue covers every
 * STABLE backend blocked-reason code (sourced from a backend audit of
 * hermes_cli/dev_web_*.py — literal constant strings, not dynamic f-strings).
 * Dynamic message strings and f-strings deliberately fall through to the safe
 * unknown-code fallback, which never suggests bypassing a boundary.
 *
 * Also covers the unified Empty / Loading / Error state invariants.
 */
import { describe, it, expect } from 'vitest'
import {
  lookupBlockedReason,
  KNOWN_BLOCKED_REASONS,
  isKnownBlockedReason,
  type BlockedReasonInfo,
} from '@/lib/blockedReasons'

// Stable backend blocked-reason codes (audit of hermes_cli/dev_web_*.py). These
// are the literal constant strings the backend assigns to the `blockedReason`
// response field. Dynamic f-strings / message strings are excluded by design —
// they degrade to the safe unknown fallback.
const BACKEND_STABLE_CODES: readonly string[] = [
  // Execute surface (dev_web_tool_handler_call.py / dev_web_tool_handler_lookup.py)
  'blocked_tool_handler_call_not_enabled',
  'blocked_dispatch_not_enabled',
  // Write surface (dev_web_write_plan.py)
  'blocked_write_execution_not_enabled',
  'blocked_write_tool_not_allowlisted',
  'blocked_write_tool_not_supported',
  'blocked_write_path_traversal',
  'blocked_write_absolute_path',
  'blocked_write_symlink_escape',
  'blocked_write_forbidden_path',
  'blocked_write_file_too_large',
  'blocked_write_content_too_large',
  'blocked_write_binary_content',
  'blocked_write_missing_rollback_plan',
  'blocked_write_digest_mismatch',
  'blocked_write_confirmation_required',
  'blocked_write_provider_auto_execute_denied',
  'blocked_write_patch_no_unique_match',
  // Rollback surface (dev_web_write_rollback.py)
  'blocked_rollback_manifest_not_found',
  'blocked_rollback_already_executed',
  'blocked_rollback_current_hash_mismatch',
  'blocked_rollback_manifest_tampered',
  'blocked_rollback_target_escape',
  'blocked_rollback_symlink_escape',
  'blocked_rollback_confirmation_required',
  'blocked_rollback_digest_mismatch',
  'blocked_rollback_write_not_enabled',
  'blocked_rollback_forbidden_target',
  // Provider surface (dev_web_provider_request.py / dev_web_provider_roundtrip.py)
  'blocked_provider_real_mode_not_enabled',
  'blocked_provider_api_key_missing',
  'blocked_provider_mode_not_supported',
  'blocked_provider_not_dev_home',
  'blocked_provider_production_gate_drift',
  'blocked_provider_recursive_tool',
  'provider_mode_disabled',
  'provider_schema_boundary_violation',
  'execution_blocked',
  // Confirmation surface (dev_web_confirmation_store.py)
  'blocked_confirmation_token_not_found',
  'blocked_confirmation_token_invalid',
  'blocked_confirmation_token_expired',
  'blocked_confirmation_token_already_used',
  'blocked_confirmation_token_scope_mismatch',
  'blocked_confirmation_token_digest_mismatch',
  // Audit surface (dev_web_audit_query.py)
  'blocked_audit_cursor_invalid',
  'blocked_audit_cursor_query_mismatch',
  'blocked_audit_limit_too_large',
  'blocked_audit_query_invalid',
]

describe('Lens 5 — Blocked reason / error state (Phase 2E-H1)', () => {
  it('the catalogue covers every STABLE backend blocked-reason code (no drift)', () => {
    const missing = BACKEND_STABLE_CODES.filter((code) => !KNOWN_BLOCKED_REASONS.includes(code))
    expect(missing, `catalogue missing stable backend codes: ${missing.join(', ')}`).toEqual([])
  })

  it('the forbidden-path code is catalogued under its real backend name (not forbidden_target)', () => {
    // Regression guard: the catalogue MUST key on `blocked_write_forbidden_path`
    // (the backend canonical code), never the prior mismatched `..._forbidden_target`.
    expect(KNOWN_BLOCKED_REASONS).toContain('blocked_write_forbidden_path')
    expect(KNOWN_BLOCKED_REASONS).not.toContain('blocked_write_forbidden_target')
    const info = lookupBlockedReason('blocked_write_forbidden_path')
    expect(info.severity).toBe('danger')
    expect(info.surface).toBe('write')
  })

  it('every catalogued code has a complete, non-empty safe explanation', () => {
    for (const code of KNOWN_BLOCKED_REASONS) {
      const info: BlockedReasonInfo = lookupBlockedReason(code)
      expect(info.code, code).toBe(code)
      expect(info.title.length, `${code} title`).toBeGreaterThan(0)
      expect(info.explanation.length, `${code} explanation`).toBeGreaterThan(0)
      expect(info.safeNextAction.length, `${code} safeNextAction`).toBeGreaterThan(0)
      expect(['info', 'warn', 'danger'], `${code} severity`).toContain(info.severity)
      expect(['execute', 'write', 'rollback', 'provider', 'confirmation', 'audit', 'unknown'], `${code} surface`).toContain(info.surface)
    }
  })

  it('no safe-action ever instructs bypassing a boundary (known + unknown)', () => {
    const codes = [...KNOWN_BLOCKED_REASONS, 'blocked_some_future_code_xyz', null, '']
    for (const code of codes) {
      const action = lookupBlockedReason(code as string | null).safeNextAction
      // "bypass"/"override"/"disable"/"force" may appear only inside a negation
      // (e.g. "do not bypass the production gate"), never as an imperative.
      const stripped = action.replace(/(?:do not|don't|never|not) (bypass|disable|skip|override|force)/gi, '')
      expect(stripped, `${code} action must not instruct bypass`).not.toMatch(/\b(bypass|override)\b/i)
    }
  })

  it('unknown / empty / null codes degrade to a safe generic fallback that never throws', () => {
    const samples = ['blocked_future_unknown_code', null, '', undefined]
    for (const code of samples) {
      const info = lookupBlockedReason(code as string | null | undefined)
      expect(info.title.length).toBeGreaterThan(0)
      expect(info.explanation.length).toBeGreaterThan(0)
      expect(info.safeNextAction.length).toBeGreaterThan(0)
      // The fallback never suggests the block is bypassable.
      expect(info.safeNextAction.toLowerCase()).not.toContain('bypass')
    }
    // A non-empty unknown code is echoed back so the operator can correlate it,
    // but empty/null collapses to the canonical unknown sentinel.
    expect(lookupBlockedReason('blocked_future_unknown_code').code).toBe('blocked_future_unknown_code')
    expect(lookupBlockedReason(null).code).toBe('unknown_blocked_reason')
  })

  it('isKnownBlockedReason distinguishes known stable codes from unknown', () => {
    expect(isKnownBlockedReason('blocked_write_forbidden_path')).toBe(true)
    expect(isKnownBlockedReason('blocked_rollback_current_hash_mismatch')).toBe(true)
    expect(isKnownBlockedReason('blocked_audit_cursor_invalid')).toBe(true)
    // A dynamic backend message string is NOT a known stable code.
    expect(isKnownBlockedReason('tool call is not a mapping')).toBe(false)
    expect(isKnownBlockedReason(null)).toBe(false)
    expect(isKnownBlockedReason('')).toBe(false)
  })
})
