/**
 * Runtime Governance pure view-model projections (Phase 3J).
 *
 * Pure, deterministic, side-effect-free functions that turn the frozen static
 * manifest (@/constants/runtimeGovernanceManifest) into the read-only shapes the
 * Runtime Governance section renders. No current time, no random id, no uuid,
 * no network fetch, no file read, no file write, no process spawn, no CLI call.
 *
 * Every projection is value-free and defense-in-depth redacted: a conservative
 * sanitizer masks any secret-shaped / production-path-shaped substring so a
 * future editor adding a secret to the manifest can never leak it through this
 * surface. The manifest itself carries no secrets today.
 */

import {
  RUNTIME_GOVERNANCE_VERSION,
  RUNTIME_REVIEWED_DESCRIPTORS,
  RUNTIME_FIXTURE_ALLOWLIST,
  RUNTIME_P0_EVIDENCE,
  RUNTIME_AUTHORIZATION_VERDICTS,
  RUNTIME_SIDE_EFFECT_FLAGS,
  RUNTIME_FLAGS_FROZEN,
  RUNTIME_CLI_EXAMPLES,
  RUNTIME_ROUTE_GOVERNANCE_BASELINE,
  RUNTIME_STATUS_BADGES,
  RUNTIME_BOUNDARY_ITEMS,
  RUNTIME_DENIED_PREVIEW,
} from '@/constants/runtimeGovernanceManifest'
import type {
  RuntimeGovernanceViewModel,
  RuntimeDescriptorRow,
  RuntimeDescriptorBindingDetail,
  RuntimeSummaryCard,
  RuntimeBoundaryItem,
  RuntimeStatusBadge,
  RuntimeDeniedPreview,
} from '@/types/api/runtimeGovernance'

/**
 * Secret / production-path stems a defense-in-depth redactor masks. These are
 * *patterns* (not real values) — they exist only to scrub a substring should
 * one ever reach this surface. Mirrors the conservative spirit of the backend
 * redact_sandbox_payload: prefer masking over exposing. Comparison is
 * case-insensitive, so stems are written in their canonical lower-case form.
 */
const REDACT_STEMS: readonly string[] = [
  'sk-',
  'bearer ',
  'authorization:',
  'ghp_',
  'xox',
  'begin private key',
  '~/.hermes',
  '.hermes/',
  'state.db',
  'implementation_authorization=go',
  'implementation authorization = go',
  'openai_api_key',
  'db_password',
  'accesstoken',
  'phase_3i_authorized=true',
  'production_approved=true',
  'route_exception_approved=true',
]

/** Mask placeholder emitted by the defense-in-depth redactor. */
const REDACTED = '[REDACTED]'

/**
 * Defense-in-depth redactor. Masks any secret-shaped / production-path-shaped
 * substring in *value*. Pure and total — never throws, never reads files or
 * the network. Applied only to free-text fields projected for display.
 */
export function redactRuntimeValue(value: string): string {
  if (typeof value !== 'string' || value.length === 0) return ''
  for (const stem of REDACT_STEMS) {
    if (value.toLowerCase().includes(stem.toLowerCase())) {
      // Mask the whole value once any stem matches — conservative.
      return REDACTED
    }
  }
  return value
}

/**
 * Stable public alias for {@link redactRuntimeValue}. Sanitizes free-text a
 * caller intends to display on the Runtime Governance surface so a future
 * editor adding a secret-shaped substring can never leak it through this view.
 */
export function sanitizeRuntimeGovernanceDisplayText(value: string): string {
  return redactRuntimeValue(value)
}

/** True iff every side-effect flag is False (the frozen invariant). */
export function allSideEffectsFalse(
  flags: readonly { value: boolean }[],
): boolean {
  return flags.length > 0 && flags.every((f) => f.value === false)
}

/** True iff every authorization verdict is NO-GO / not-authorized / false. */
const NO_GO_VERDICTS = new Set(['NO-GO', 'NOT_AUTHORIZED', 'false'])
export function allVerdictsNoGo(
  verdicts: readonly { verdict: string }[],
): boolean {
  return (
    verdicts.length > 0 && verdicts.every((v) => NO_GO_VERDICTS.has(v.verdict))
  )
}

/** Build the read-only descriptor rows (descriptions defense-in-depth redacted). */
export function buildDescriptorRows(): readonly RuntimeDescriptorRow[] {
  return RUNTIME_REVIEWED_DESCRIPTORS.map((d) => ({
    ...d,
    description: redactRuntimeValue(d.description),
  }))
}

/** Look up a descriptor row by id (membership only; returns undefined if absent). */
export function findDescriptorRow(
  descriptorId: string | null,
): RuntimeDescriptorRow | undefined {
  if (!descriptorId) return undefined
  return RUNTIME_REVIEWED_DESCRIPTORS.find((d) => d.descriptorId === descriptorId)
}

/** The default descriptor selected on first render (echo_uppercase). */
export const DEFAULT_DESCRIPTOR_ID = 'descriptor.fixture.echo_uppercase'

/**
 * Project the binding detail for a descriptor (no execution). Mirrors the
 * backend show projection's safe fields. A reviewed descriptor always binds
 * (bindingAllowed true, no denial reasons); an unknown id yields undefined and
 * the section renders the denied/empty state.
 *
 * Every nested collection is a fresh defensive copy, so mutating a returned
 * binding (or its runtimeFlags / triggeredGuards) can never reach the frozen
 * canonical manifest.
 */
export function buildDescriptorBindingDetail(
  descriptorId: string | null,
): RuntimeDescriptorBindingDetail | undefined {
  const row = findDescriptorRow(descriptorId)
  if (!row) return undefined
  return {
    descriptorId: row.descriptorId,
    pluginId: row.pluginId,
    operation: row.operation,
    source: row.source,
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    bindingAllowed: true,
    denialReasons: [],
    triggeredGuards: ['descriptor_registry_lookup', 'fixture_allowlist_binding'],
    runtimeFlags: { ...RUNTIME_FLAGS_FROZEN },
    redactedDescriptor: { redactionApplied: true },
  }
}

/** Summary cards for the Runtime Governance overview. Deterministic. */
export function buildSummaryCards(): readonly RuntimeSummaryCard[] {
  return [
    {
      label: 'Reviewed descriptors',
      value: RUNTIME_REVIEWED_DESCRIPTORS.length,
      sub: 'static_descriptor_registry',
      tone: 'info',
    },
    {
      label: 'Supported fixture plugins',
      value: RUNTIME_FIXTURE_ALLOWLIST.length,
      sub: 'dev-only fixture allowlist',
      tone: 'info',
    },
    {
      label: 'Supported operations',
      value: RUNTIME_FIXTURE_ALLOWLIST.length,
      sub: 'fixture allowlist pairs',
      tone: 'info',
    },
    {
      label: 'P0 gates',
      value: RUNTIME_P0_EVIDENCE.totalGates,
      sub: 'inherited',
      tone: 'info',
    },
    {
      label: 'P0 resolved',
      value: RUNTIME_P0_EVIDENCE.resolvedCount,
      sub: 'always 0 — requires human approval',
      tone: 'warn',
    },
    {
      label: 'Partial evidence',
      value: RUNTIME_P0_EVIDENCE.partialEvidenceCount,
      sub: 'real code/test evidence, not approved',
      tone: 'warn',
    },
    {
      label: 'Pending human review',
      value: RUNTIME_P0_EVIDENCE.blockedByHumanReviewCount,
      sub: 'blocked_by_human_review',
      tone: 'warn',
    },
    {
      label: 'Side effects',
      value: 'all false',
      sub: 'frozen no-side-effect surface',
      tone: 'ok',
    },
    {
      label: 'Backend routes changed',
      value: 'no',
      sub: RUNTIME_ROUTE_GOVERNANCE_BASELINE,
      tone: 'ok',
    },
  ]
}

/**
 * Project the frozen page-header status badges (defensive copy). Non-color text
 * labels that convey the read-only boundary at a glance.
 */
export function buildStatusBadges(): readonly RuntimeStatusBadge[] {
  return RUNTIME_STATUS_BADGES.map((b) => ({ label: b.label }))
}

/**
 * Project the frozen boundary-banner rows (defensive copy). Each item carries an
 * icon `kind` (lock | ban) and an explicit non-color text label.
 */
export function buildBoundaryItems(): readonly RuntimeBoundaryItem[] {
  return RUNTIME_BOUNDARY_ITEMS.map((row) => ({ kind: row.kind, label: row.label }))
}

/**
 * Project the frozen denied-binding preview (defensive copy). Used when an
 * unknown / unsafe descriptor id is selected — no fixture runs, no binding is
 * resolved, and the denial reasons are surfaced verbatim.
 */
export function buildDeniedPreview(): RuntimeDeniedPreview {
  return { denied: true, denialReasons: [...RUNTIME_DENIED_PREVIEW.denialReasons] }
}

/** Assemble the full read-only Runtime Governance view model. Deterministic. */
export function buildRuntimeGovernanceViewModel(): RuntimeGovernanceViewModel {
  const descriptors = buildDescriptorRows()
  return {
    schemaVersion: RUNTIME_GOVERNANCE_VERSION,
    descriptors,
    descriptorCount: descriptors.length,
    fixtureAllowlist: RUNTIME_FIXTURE_ALLOWLIST.map((f) => ({ pluginId: f.pluginId, operation: f.operation })),
    fixtureAllowlistCount: RUNTIME_FIXTURE_ALLOWLIST.length,
    p0Evidence: { ...RUNTIME_P0_EVIDENCE },
    authorizationVerdicts: RUNTIME_AUTHORIZATION_VERDICTS.map((v) => ({ ...v })),
    sideEffectFlags: RUNTIME_SIDE_EFFECT_FLAGS.map((f) => ({ ...f })),
    runtimeFlags: { ...RUNTIME_FLAGS_FROZEN },
    cliExamples: RUNTIME_CLI_EXAMPLES.map((c) => ({ ...c, aliases: [...c.aliases] })),
    routeGovernanceBaseline: RUNTIME_ROUTE_GOVERNANCE_BASELINE,
    backendRoutesChanged: false,
  }
}
