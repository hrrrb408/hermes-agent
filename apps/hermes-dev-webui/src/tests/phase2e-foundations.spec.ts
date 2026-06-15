/**
 * Phase 2E foundation-lib unit tests.
 *
 * Covers the pure, Vue-free modules that back the unified developer console:
 * formatters, safetyBadges, blockedReasons, and frozenBaseline.
 */
import { describe, it, expect } from 'vitest'
import {
  formatBytes,
  truncateHash,
  formatCount,
  formatTimestamp,
  formatFlag,
} from '@/lib/formatters'
import {
  SAFETY_BADGES,
  getSafetyBadge,
  badgesByGroup,
  type SafetyBadge,
} from '@/lib/safetyBadges'
import {
  lookupBlockedReason,
  KNOWN_BLOCKED_REASONS,
  isKnownBlockedReason,
} from '@/lib/blockedReasons'
import {
  FROZEN_ROUTE_GOVERNANCE,
  FROZEN_PRODUCTION_GATEWAY_PID,
  FROZEN_PHASE_TIMELINE,
  FROZEN_STATIC_ALLOWLIST,
  FROZEN_STATIC_WRITE_TOOLS,
} from '@/lib/frozenBaseline'

describe('formatters', () => {
  it('formatBytes renders bytes / KB / MB / GB boundaries', () => {
    expect(formatBytes(0)).toBe('0 bytes')
    expect(formatBytes(512)).toBe('512 bytes')
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(1_572_864)).toBe('1.5 MB')
    expect(formatBytes(1_610_612_736)).toBe('1.5 GB')
  })

  it('formatBytes guards non-finite / negative', () => {
    expect(formatBytes(Number.NaN)).toBe('—')
    expect(formatBytes(-1)).toBe('—')
  })

  it('truncateHash is lossy and never shows full long hashes', () => {
    const full = 'a'.repeat(64)
    expect(truncateHash(full)).toHaveLength(17) // 16 chars + ellipsis
    expect(truncateHash('short')).toBe('short')
    expect(truncateHash(null)).toBe('—')
    expect(truncateHash('')).toBe('—')
    expect(truncateHash(undefined)).toBe('—')
  })

  it('formatCount renders finite numbers and dashes otherwise', () => {
    expect(formatCount(7)).toBe('7')
    expect(formatCount(null)).toBe('—')
    expect(formatCount(Number.POSITIVE_INFINITY)).toBe('—')
  })

  it('formatTimestamp renders valid ISO and passes through invalid', () => {
    const out = formatTimestamp('2026-06-15T10:30:00Z')
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    expect(formatTimestamp(null)).toBe('—')
    expect(formatTimestamp('not-a-date')).toBe('not-a-date')
  })

  it('formatFlag renders Yes / No / —', () => {
    expect(formatFlag(true)).toBe('Yes')
    expect(formatFlag(false)).toBe('No')
    expect(formatFlag(null)).toBe('—')
  })
})

describe('safetyBadges', () => {
  it('exposes the invariant dev-console badges', () => {
    expect(SAFETY_BADGES.length).toBeGreaterThan(0)
    const ids = SAFETY_BADGES.map((b) => b.id)
    // The spec-mandated badges must all be present.
    for (const id of [
      'production-untouched',
      'dev-hermes-home',
      'no-prod-home-access',
      'route-tool-write-zero',
      'real-provider-blocked',
      'provider-write-preview-only',
      'sandbox-write-only',
      'audit-store-dev-only',
    ]) {
      expect(ids, `missing badge ${id}`).toContain(id)
    }
  })

  it('every badge has a unique id, a label, and a valid tone', () => {
    const ids = new Set<string>()
    for (const b of SAFETY_BADGES) {
      expect(ids.has(b.id), `duplicate badge id ${b.id}`).toBe(false)
      ids.add(b.id)
      expect(b.label.length).toBeGreaterThan(0)
      expect(b.description.length).toBeGreaterThan(0)
      expect(['ok', 'warn', 'danger', 'info']).toContain(b.tone)
      expect(['production', 'environment', 'route', 'provider', 'write', 'audit']).toContain(b.group)
    }
  })

  it('getSafetyBadge finds by id and returns undefined for unknown', () => {
    expect(getSafetyBadge('production-untouched')?.label).toBe('Production untouched')
    expect(getSafetyBadge('does-not-exist')).toBeUndefined()
  })

  it('badgesByGroup filters deterministically', () => {
    const production = badgesByGroup('production' as SafetyBadge['group'])
    expect(production.length).toBeGreaterThan(0)
    expect(production.every((b) => b.group === 'production')).toBe(true)
  })
})

describe('blockedReasons', () => {
  it('covers the spec-mandated blocked codes', () => {
    const required = [
      'blocked_provider_real_mode_not_enabled',
      'provider_mode_disabled',
      'blocked_write_execution_not_enabled',
      'blocked_write_path_traversal',
      'blocked_write_absolute_path',
      'blocked_write_symlink_escape',
      'blocked_write_forbidden_path',
      'blocked_write_provider_auto_execute_denied',
      'blocked_rollback_current_hash_mismatch',
      'blocked_rollback_already_executed',
      'blocked_confirmation_token_expired',
      'blocked_confirmation_token_already_used',
      'blocked_audit_cursor_invalid',
      'blocked_audit_cursor_query_mismatch',
    ]
    for (const code of required) {
      expect(KNOWN_BLOCKED_REASONS, `missing blocked code ${code}`).toContain(code)
    }
  })

  it('lookupBlockedReason returns full info for a known code', () => {
    const info = lookupBlockedReason('blocked_write_path_traversal')
    expect(info.code).toBe('blocked_write_path_traversal')
    expect(info.title.length).toBeGreaterThan(0)
    expect(info.explanation.length).toBeGreaterThan(0)
    expect(info.safeNextAction.length).toBeGreaterThan(0)
    expect(info.severity).toBe('danger')
    expect(info.surface).toBe('write')
  })

  it('lookupBlockedReason never throws and returns a safe fallback for unknown/empty', () => {
    const unknown = lookupBlockedReason('blocked_some_future_code_xyz')
    expect(unknown.title.length).toBeGreaterThan(0)
    expect(unknown.safeNextAction.length).toBeGreaterThan(0)
    expect(unknown.code).toBe('blocked_some_future_code_xyz')

    expect(lookupBlockedReason(null).code).toBe('unknown_blocked_reason')
    expect(lookupBlockedReason('').code).toBe('unknown_blocked_reason')
    expect(lookupBlockedReason(undefined).code).toBe('unknown_blocked_reason')
  })

  it('no blocked-reason safe action ever instructs bypassing a boundary', () => {
    for (const code of KNOWN_BLOCKED_REASONS) {
      const action = lookupBlockedReason(code).safeNextAction
      // "bypass"/"disable"/"skip"/"override" may appear only inside a negation
      // (e.g. "do not bypass the production gate") — never as an imperative.
      const stripped = action.replace(/(?:do not|don't|never|not) (bypass|disable|skip|override|force)/gi, '')
      expect(stripped, `${code} action must not instruct bypass`).not.toMatch(/\b(bypass|override)\b/i)
    }
  })

  it('isKnownBlockedReason distinguishes known from unknown', () => {
    expect(isKnownBlockedReason('blocked_write_path_traversal')).toBe(true)
    expect(isKnownBlockedReason('nope')).toBe(false)
    expect(isKnownBlockedReason(null)).toBe(false)
    expect(isKnownBlockedReason('')).toBe(false)
  })
})

describe('frozenBaseline', () => {
  it('pins the frozen route-governance baseline (34/34/5/0/1/1)', () => {
    expect(FROZEN_ROUTE_GOVERNANCE.openApiPaths).toBe(34)
    expect(FROZEN_ROUTE_GOVERNANCE.runtimeRoutes).toBe(34)
    expect(FROZEN_ROUTE_GOVERNANCE.toolGetRoutes).toBe(5)
    expect(FROZEN_ROUTE_GOVERNANCE.toolWriteRoutes).toBe(0)
    expect(FROZEN_ROUTE_GOVERNANCE.toolDryRunRoutes).toBe(1)
    expect(FROZEN_ROUTE_GOVERNANCE.toolExecutionRoutes).toBe(1)
  })

  it('pins the production gateway PID baseline (28428)', () => {
    expect(FROZEN_PRODUCTION_GATEWAY_PID).toBe(28428)
  })

  it('records the sealed phase timeline with 2E and 2E-H1 completed, 3 not started', () => {
    const byPhase = new Map(FROZEN_PHASE_TIMELINE.map((e) => [e.phase, e.status]))
    expect(byPhase.get('Phase 1G')).toBe('SEALED')
    expect(byPhase.get('Phase 2')).toBe('UNLOCKED')
    expect(byPhase.get('Phase 2D-H1')).toBe('completed')
    expect(byPhase.get('Phase 2E')).toBe('completed')
    expect(byPhase.get('Phase 2E-H1')).toBe('completed')
    expect(byPhase.get('Phase 3')).toBe('not_started')
  })

  it('pins the static read-only allowlist and write tools', () => {
    expect(FROZEN_STATIC_ALLOWLIST).toContain('clarify')
    expect(FROZEN_STATIC_ALLOWLIST).toContain('route_governance_read')
    expect(FROZEN_STATIC_WRITE_TOOLS).toContain('dev_sandbox_file_write')
    expect(FROZEN_STATIC_WRITE_TOOLS).toContain('dev_sandbox_rollback_execute')
  })
})
