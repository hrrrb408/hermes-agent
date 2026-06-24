/**
 * Target B Readiness pure view-model projections (Phase 4A).
 *
 * Pure, deterministic, side-effect-free functions that turn the frozen static
 * manifest (@/constants/targetBReadinessManifest) into the read-only shapes the
 * Target B Readiness region renders. No current time, no random id, no uuid,
 * no network fetch, no file read, no file write, no process spawn, no CLI call,
 * no backend call.
 *
 * Every projection is value-free and defense-in-depth redacted: a conservative
 * sanitizer masks any secret-shaped / production-path-shaped /
 * fake-approval-shaped / Target-B-authorization marker substring so a future
 * editor adding a secret or a fake authorization to the manifest can never leak
 * it through this surface. The manifest itself carries no secrets and no fake
 * authorizations today.
 *
 * Mutating any returned value can never reach the frozen canonical manifest,
 * can never flip a frozen NO-GO verdict, can never flip a frozen disabled
 * capability, can never grant a DENIED_BY_DEFAULT permission, can never enable
 * a disabled execution step, can never enable the canSubmit flag, and can never
 * raise P0 resolved above 0.
 */

import {
  TARGET_B_READINESS_VERSION,
  TARGET_B_READINESS_PHASE_LABEL,
  TARGET_B_ROUTE_GOVERNANCE_BASELINE,
  TARGET_B_READINESS_SUMMARY,
  TARGET_B_ARCHITECTURE_MODULES,
  TARGET_B_PLUGIN_PACKAGE_SCHEMA,
  TARGET_B_PERMISSION_ENTRIES,
  TARGET_B_REGISTRY_PROTOCOL,
  TARGET_B_WEBUI_EXECUTION,
  TARGET_B_APPROVAL_GATE,
  TARGET_B_ENABLEMENT_BLOCKERS,
  TARGET_B_TARGET_A_RELATIONSHIP,
  TARGET_B_READINESS_CHECKLIST,
  TARGET_B_STATUS_BADGES,
  TARGET_B_BOUNDARY_ITEMS,
  TARGET_B_FORBIDDEN_ACTIONS,
  TARGET_B_ALLOWED_UI_ACTIONS,
} from '@/constants/targetBReadinessManifest'
import type {
  TargetBReadinessViewModel,
  TargetBReadinessSummary,
  TargetBArchitectureModule,
  PluginPackageSchemaPreview,
  PluginPermissionModel,
  TargetBPermissionEntry,
  RegistryProtocolPreview,
  WebUIExecutionPreview,
  ApprovalGateModel,
  TargetBEnablementBlocker,
  TargetBTargetARelationship,
  TargetBReadinessCheckItem,
  TargetBStatusBadge,
  TargetBBoundaryItem,
  TargetBSummaryCard,
  TargetBModuleFilterKey,
} from '@/types/api/targetBReadiness'

/**
 * Secret / production-path / fake-authorization stems a defense-in-depth
 * redactor masks. These are *patterns* (not real values) — they exist only to
 * scrub a substring should one ever reach this surface. Mirrors the
 * conservative spirit of the backend redact_sandbox_payload: prefer masking
 * over exposing. Comparison is case-insensitive, so stems are written in their
 * canonical lower-case form.
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
  'approved_by_ai=true',
  'trust_token=fake',
  'trust_token=',
  'target_b_authorized=true',
  'target_b_authorized=',
  'production_runtime_go=true',
  'production_runtime_go=',
  'registry_token=fake',
  'registry_token=',
  'plugin_signature=fake-private-key',
  'plugin_signature=',
]

/** Mask placeholder emitted by the defense-in-depth redactor. */
const REDACTED = '[REDACTED]'

/**
 * Defense-in-depth redactor. Masks any secret-shaped / production-path-shaped /
 * fake-authorization-shaped substring in *value*. Pure and total — never
 * throws, never reads files or the network. Applied only to free-text fields
 * projected for display.
 */
export function redactTargetBValue(value: string): string {
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
 * Stable public alias for {@link redactTargetBValue}. Sanitizes free-text a
 * caller intends to display on the Target B readiness surface so a future
 * editor adding a secret-shaped / fake-authorization substring can never leak
 * it through this view.
 */
export function sanitizeTargetBReadinessDisplayText(value: string): string {
  return redactTargetBValue(value)
}

/** True iff every authorization verdict in the summary is frozen NO-GO. */
export function allTargetBVerdictsNoGo(summary: TargetBReadinessSummary): boolean {
  return (
    summary.productionRuntime === 'NO-GO' &&
    summary.arbitraryPluginLoading === 'NO-GO' &&
    summary.remoteRegistry === 'NO-GO' &&
    summary.marketplace === 'NO-GO' &&
    summary.webuiExecution === 'NO-GO' &&
    summary.approvalAuthorization === 'NO-GO' &&
    summary.productionRollout === 'NO-GO'
  )
}

/** True iff every architecture capability is disabled / non-executing / non-networking. */
export function allTargetBModulesDisabled(
  modules: readonly TargetBArchitectureModule[],
): boolean {
  return (
    modules.length > 0 &&
    modules.every(
      (m) =>
        m.enabled === false &&
        m.executionCapable === false &&
        m.networkCapable === false &&
        m.productionCapable === false &&
        m.routeImpact === 'none',
    )
  )
}

/** True iff every permission is denied by default. */
export function allTargetBPermissionsDenied(
  entries: readonly TargetBPermissionEntry[],
): boolean {
  return (
    entries.length > 0 && entries.every((p) => p.currentStatus === 'DENIED_BY_DEFAULT')
  )
}

/** Project the frozen summary (defensive copy + redacted free-text). Deterministic. */
export function buildTargetBReadinessSummary(): TargetBReadinessSummary {
  const s = TARGET_B_READINESS_SUMMARY
  return {
    ...s,
    targetName: redactTargetBValue(s.targetName),
    requiredBeforeEnable: s.requiredBeforeEnable.map((r) => redactTargetBValue(r)),
  }
}

/**
 * Project the architecture module board (free-text fields defense-in-depth
 * redacted). Every nested collection is a fresh defensive copy, so mutating a
 * returned module can never reach the frozen canonical manifest.
 */
export function buildTargetBArchitectureModules(): readonly TargetBArchitectureModule[] {
  return TARGET_B_ARCHITECTURE_MODULES.map((m) => ({
    ...m,
    module: redactTargetBValue(m.module),
    requiredGate: redactTargetBValue(m.requiredGate),
    futureImplementationNotes: redactTargetBValue(m.futureImplementationNotes),
  }))
}

/**
 * Project the plugin package schema preview (free-text fields redacted).
 * Defensive copy — the returned object and its nested arrays are fresh.
 */
export function buildTargetBPluginPackageSchema(): PluginPackageSchemaPreview {
  const s = TARGET_B_PLUGIN_PACKAGE_SCHEMA
  return {
    packageId: redactTargetBValue(s.packageId),
    version: redactTargetBValue(s.version),
    descriptor: redactTargetBValue(s.descriptor),
    capabilities: s.capabilities.map((c) => redactTargetBValue(c)),
    permissions: s.permissions.map((p) => redactTargetBValue(p)),
    entrypoints: s.entrypoints.map((e) => redactTargetBValue(e)),
    signature: redactTargetBValue(s.signature),
    publisher: redactTargetBValue(s.publisher),
    registrySource: redactTargetBValue(s.registrySource),
    checksum: redactTargetBValue(s.checksum),
    sandboxProfile: redactTargetBValue(s.sandboxProfile),
    minimumHermesVersion: redactTargetBValue(s.minimumHermesVersion),
    exampleOnly: true,
    notLoaded: true,
    notExecutable: true,
  }
}

/** Project the frozen permission model (free-text redacted). Defensive copy. */
export function buildTargetBPermissionModel(): PluginPermissionModel {
  const entries: readonly TargetBPermissionEntry[] = TARGET_B_PERMISSION_ENTRIES.map((p) => ({
    key: p.key,
    label: redactTargetBValue(p.label),
    currentStatus: p.currentStatus,
  }))
  return {
    entries,
    defaultDisposition: 'DENIED_BY_DEFAULT',
    anyGranted: false,
  }
}

/** Project the frozen registry protocol preview (defensive copy). Deterministic. */
export function buildTargetBRegistryProtocol(): RegistryProtocolPreview {
  return { ...TARGET_B_REGISTRY_PROTOCOL }
}

/** Project the frozen WebUI execution preview (free-text redacted). Defensive copy. */
export function buildTargetBWebUIExecution(): WebUIExecutionPreview {
  const e = TARGET_B_WEBUI_EXECUTION
  return {
    visibleInWebUI: true,
    executeButtonEnabled: false,
    approvalRequired: true,
    runtimeRouteAvailable: false,
    canSubmit: false,
    status: 'PREVIEW_ONLY_DISABLED',
    flow: e.flow.map((step) => ({
      key: step.key,
      label: redactTargetBValue(step.label),
      enabled: false,
      note: redactTargetBValue(step.note),
    })),
  }
}

/** Project the frozen approval gate model (defensive copy). Deterministic. */
export function buildTargetBApprovalGate(): ApprovalGateModel {
  return { ...TARGET_B_APPROVAL_GATE }
}

/** Project the enablement blockers (free-text redacted). Defensive copy. */
export function buildTargetBEnablementBlockers(): readonly TargetBEnablementBlocker[] {
  return TARGET_B_ENABLEMENT_BLOCKERS.map((b) => ({
    key: b.key,
    label: redactTargetBValue(b.label),
    resolved: false,
    detail: redactTargetBValue(b.detail),
  }))
}

/** Project the Target A relationship (free-text redacted). Defensive copy. */
export function buildTargetBTargetARelationship(): readonly TargetBTargetARelationship[] {
  return TARGET_B_TARGET_A_RELATIONSHIP.map((r) => ({
    key: r.key,
    statement: redactTargetBValue(r.statement),
  }))
}

/** Project the readiness checklist (free-text redacted). Defensive copy. */
export function buildTargetBReadinessChecklist(): readonly TargetBReadinessCheckItem[] {
  return TARGET_B_READINESS_CHECKLIST.map((i) => ({
    id: i.id,
    label: redactTargetBValue(i.label),
    status: i.status,
    enablementBlocked: i.enablementBlocked,
    evidenceSummary: redactTargetBValue(i.evidenceSummary),
  }))
}

/** Project the frozen status badges (defensive copy). Deterministic. */
export function buildTargetBStatusBadges(): readonly TargetBStatusBadge[] {
  return TARGET_B_STATUS_BADGES.map((b) => ({ label: redactTargetBValue(b.label) }))
}

/** Project the frozen boundary-banner rows (free-text redacted). Defensive copy. */
export function buildTargetBBoundaryItems(): readonly TargetBBoundaryItem[] {
  return TARGET_B_BOUNDARY_ITEMS.map((row) => ({
    kind: row.kind,
    label: redactTargetBValue(row.label),
  }))
}

/** Project the forbidden-actions list (defensive copy). */
export function buildTargetBForbiddenActions(): readonly string[] {
  return [...TARGET_B_FORBIDDEN_ACTIONS]
}

/** Project the allowed-UI-actions list (defensive copy). */
export function buildTargetBAllowedUiActions(): readonly string[] {
  return [...TARGET_B_ALLOWED_UI_ACTIONS]
}

/** Summary cards for the Target B readiness overview. Deterministic. */
export function buildTargetBReadinessSummaryCards(): readonly TargetBSummaryCard[] {
  const s = TARGET_B_READINESS_SUMMARY
  return [
    { label: 'Target B status', value: s.readinessStatus, sub: 'architecture + disabled scaffold', tone: 'info' },
    { label: 'Execution', value: s.executionStatus, sub: 'no runtime, no execution', tone: 'danger' },
    { label: 'Production runtime', value: s.productionRuntime, sub: 'no approved sandbox model', tone: 'danger' },
    { label: 'Remote registry', value: s.remoteRegistry, sub: 'no registry fetched', tone: 'danger' },
    { label: 'Marketplace', value: s.marketplace, sub: 'not reachable', tone: 'danger' },
    { label: 'WebUI execution', value: s.webuiExecution, sub: 'preview only', tone: 'danger' },
    { label: 'Approval / authorization', value: s.approvalAuthorization, sub: 'no trust token provisioned', tone: 'danger' },
    { label: 'Production rollout', value: s.productionRollout, sub: 'no approved plan', tone: 'danger' },
    { label: 'P0 gates', value: s.p0Total, sub: '24 frozen gates', tone: 'info' },
    { label: 'P0 resolved', value: s.p0Resolved, sub: 'always 0 — requires human approval', tone: 'warn' },
    { label: 'Route governance', value: TARGET_B_ROUTE_GOVERNANCE_BASELINE, sub: 'unchanged', tone: 'ok' },
  ]
}

/** Client-side module filter options rendered as harmless client-side toggles. */
export const TARGET_B_MODULE_FILTER_OPTIONS: readonly {
  readonly key: TargetBModuleFilterKey
  readonly label: string
}[] = [
  { key: 'all', label: 'All modules' },
  { key: 'DESIGNED', label: 'Designed' },
  { key: 'SCAFFOLDED_DISABLED', label: 'Scaffolded (disabled)' },
]

/** Select the architecture modules matching a client-side status filter. Pure. */
export function filterTargetBModules(
  filterKey: TargetBModuleFilterKey,
): readonly TargetBArchitectureModule[] {
  const modules = buildTargetBArchitectureModules()
  if (filterKey === 'all') return modules
  return modules.filter((m) => m.status === filterKey)
}

/**
 * A deterministic, redacted plain-text snapshot of the Target B readiness
 * summary, used by the Copy control. Pure — operates on the frozen summary and
 * registry projection only, performs no network call and writes no file.
 */
export function buildTargetBReadinessSummaryText(): string {
  const s = TARGET_B_READINESS_SUMMARY
  const r = TARGET_B_REGISTRY_PROTOCOL
  const lines = [
    `Hermes Dev WebUI — Target B Readiness Scaffold (${TARGET_B_READINESS_PHASE_LABEL})`,
    'READ-ONLY readiness scaffold — no execution, no approval, no authorization, no network, no new route.',
    `Target B: ${s.readinessStatus} — execution ${s.executionStatus}.`,
    `Production runtime: ${s.productionRuntime} | Arbitrary plugin loading: ${s.arbitraryPluginLoading} | Remote registry: ${s.remoteRegistry} | Marketplace: ${s.marketplace}`,
    `WebUI execution: ${s.webuiExecution} | Approval / authorization: ${s.approvalAuthorization} | Production rollout: ${s.productionRollout}`,
    `P0 gates: total ${s.p0Total} | resolved ${s.p0Resolved} | pending human review ${s.p0PendingHumanReview}`,
    `Route governance: ${TARGET_B_ROUTE_GOVERNANCE_BASELINE} (unchanged).`,
    `Registry preview: ${r.registryUrlExample} — fetch ${r.fetchEnabled} | network ${r.networkEnabled} | marketplace ${r.marketplaceEnabled} | signature required ${r.signatureRequired}.`,
    'Target A complete is prerequisite evidence only — it does NOT authorize Target B.',
  ]
  return lines.map((l) => redactTargetBValue(l)).join('\n')
}

/** Assemble the full read-only Target B Readiness view model. Deterministic. */
export function buildTargetBReadinessViewModel(): TargetBReadinessViewModel {
  return {
    schemaVersion: TARGET_B_READINESS_VERSION,
    phase: TARGET_B_READINESS_PHASE_LABEL,
    summary: buildTargetBReadinessSummary(),
    summaryCards: buildTargetBReadinessSummaryCards(),
    architectureModules: buildTargetBArchitectureModules(),
    pluginPackageSchema: buildTargetBPluginPackageSchema(),
    permissionModel: buildTargetBPermissionModel(),
    registryProtocol: buildTargetBRegistryProtocol(),
    webuiExecution: buildTargetBWebUIExecution(),
    approvalGate: buildTargetBApprovalGate(),
    enablementBlockers: buildTargetBEnablementBlockers(),
    targetARelationship: buildTargetBTargetARelationship(),
    readinessChecklist: buildTargetBReadinessChecklist(),
    statusBadges: buildTargetBStatusBadges(),
    boundaryItems: buildTargetBBoundaryItems(),
    forbiddenActions: buildTargetBForbiddenActions(),
    allowedUiActions: buildTargetBAllowedUiActions(),
    routeGovernanceBaseline: TARGET_B_ROUTE_GOVERNANCE_BASELINE,
    backendRoutesChanged: false,
  }
}
