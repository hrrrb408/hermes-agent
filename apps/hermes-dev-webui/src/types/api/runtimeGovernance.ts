/**
 * Runtime Governance read-only view-model types (Phase 3J).
 *
 * Pure, value-free TypeScript shapes for the Dev WebUI read-only surface over
 * the Phase 3I dev-only descriptor-backed fixture runtime. These types mirror
 * the deterministic, redacted JSON projections emitted by the backend runtime
 * governance module (hermes_cli/dev_web_runtime_governance.py) — they carry
 * ONLY safe fields: no API key, Authorization, Bearer, secret, callable repr,
 * shell command, SQL statement, production path, local plugin path, dynamic
 * import path, external URL, download URL, or install command.
 *
 * Nothing here grants permission, loads a plugin, executes a plugin, or
 * performs a side effect. Every descriptor is dev-only / fixture-only /
 * reviewed-fixture; every authorization verdict is frozen NO-GO /
 * not-authorized; every side-effect flag is frozen False.
 */

/** Schema version mirrored from the backend governance envelope. */
export const RUNTIME_GOVERNANCE_SCHEMA_VERSION = 'phase-3i-runtime-governance-v1' as const

/** Frozen provenance label for every reviewed-fixture descriptor binding. */
export const RUNTIME_DESCRIPTOR_BINDING_SOURCE = 'static_descriptor_registry' as const

/** Frozen route-governance baseline (OpenAPI / Runtime / GET / write / dry-run / execute). */
export const ROUTE_GOVERNANCE_BASELINE = '34/34/5/0/1/1' as const

/** A single reviewed-fixture descriptor (metadata only — never executed). */
export interface RuntimeDescriptorRow {
  readonly descriptorId: string
  readonly pluginId: string
  readonly operation: string
  readonly source: typeof RUNTIME_DESCRIPTOR_BINDING_SOURCE
  readonly version: string
  readonly displayName: string
  readonly description: string
  readonly devOnly: true
  readonly fixtureOnly: true
  readonly reviewedFixture: true
  readonly executable: false
  readonly remote: false
  readonly marketplace: false
  readonly production: false
  readonly routeChange: false
  readonly bindingAllowed: true
}

/** A supported fixture runtime (pluginId, operation) allowlist entry. */
export interface RuntimeFixtureAllowlistEntry {
  readonly pluginId: string
  readonly operation: string
}

/** The binding detail projected for a selected descriptor (no execution). */
export interface RuntimeDescriptorBindingDetail {
  readonly descriptorId: string
  readonly pluginId: string
  readonly operation: string
  readonly source: typeof RUNTIME_DESCRIPTOR_BINDING_SOURCE
  readonly devOnly: true
  readonly fixtureOnly: true
  readonly reviewedFixture: true
  readonly bindingAllowed: true
  readonly denialReasons: readonly []
  readonly triggeredGuards: readonly string[]
  readonly runtimeFlags: Readonly<Record<string, boolean>>
  readonly redactedDescriptor: Readonly<{ redactionApplied: true }>
}

/** A frozen authorization verdict dimension projected for display. */
export interface RuntimeAuthorizationVerdict {
  readonly key: string
  readonly label: string
  readonly verdict: string
  readonly kind: 'gate' | 'dimension' | 'flag'
}

/** A frozen side-effect flag projected for display (always False). */
export interface RuntimeSideEffectFlag {
  readonly key: string
  readonly label: string
  readonly value: false
}

/** The conservative P0 evidence summary (resolvedCount always 0). */
export interface RuntimeP0EvidenceProjection {
  readonly totalGates: 24
  readonly resolvedCount: 0
  readonly partialEvidenceCount: number
  readonly candidateForReviewCount: number
  readonly blockedByHumanReviewCount: number
  readonly governanceOnlyCount: number
  readonly noEvidenceCount: number
  readonly unresolvedCount: 24
  readonly implementationAuthorization: 'NO-GO'
  readonly phase3iAuthorized: false
  readonly realRuntime: 'NO-GO'
  readonly newRoute: 'NO-GO'
  readonly productionRollout: 'NO-GO'
  readonly classificationNote: string
}

/** A read-only CLI command example (text only — never executed from the WebUI). */
export interface RuntimeCliExample {
  readonly command: string
  readonly summary: string
  readonly aliases: readonly string[]
}

/**
 * A frozen boundary-banner row. `kind` selects the icon; `label` is the explicit
 * non-color text that conveys the boundary (status is never color-only).
 */
export interface RuntimeBoundaryItem {
  readonly kind: 'lock' | 'ban'
  readonly label: string
}

/** A read-only status chip projected into the page header (non-color text). */
export interface RuntimeStatusBadge {
  readonly label: string
}

/** The denied-binding preview projected for an unknown / unsafe descriptor id. */
export interface RuntimeDeniedPreview {
  readonly denied: true
  readonly denialReasons: readonly string[]
}

/** A summary card projected for the Runtime Governance overview. */
export interface RuntimeSummaryCard {
  readonly label: string
  readonly value: string | number
  readonly sub?: string
  readonly tone: 'ok' | 'warn' | 'danger' | 'info'
}

/** The full read-only Runtime Governance view model. */
export interface RuntimeGovernanceViewModel {
  readonly schemaVersion: typeof RUNTIME_GOVERNANCE_SCHEMA_VERSION
  readonly descriptors: readonly RuntimeDescriptorRow[]
  readonly descriptorCount: number
  readonly fixtureAllowlist: readonly RuntimeFixtureAllowlistEntry[]
  readonly fixtureAllowlistCount: number
  readonly p0Evidence: RuntimeP0EvidenceProjection
  readonly authorizationVerdicts: readonly RuntimeAuthorizationVerdict[]
  readonly sideEffectFlags: readonly RuntimeSideEffectFlag[]
  readonly runtimeFlags: Readonly<Record<string, boolean>>
  readonly cliExamples: readonly RuntimeCliExample[]
  readonly routeGovernanceBaseline: typeof ROUTE_GOVERNANCE_BASELINE
  readonly backendRoutesChanged: false
}
