/**
 * Frozen static Runtime Governance manifest — Phase 3J (frontend mirror).
 *
 * A tracked, reviewable, deterministic mirror of the Phase 3I dev-only
 * descriptor-backed fixture runtime governance state. It is the read-only data
 * source for the Dev WebUI Runtime Governance section. It carries ONLY safe,
 * value-free fields — no API key, Authorization, Bearer, secret, callable repr,
 * shell command, SQL statement, production path, local plugin path, dynamic
 * import path, external URL, download URL, or install command.
 *
 * Provenance: derived from the frozen backend constants in
 *   - hermes_cli/dev_web_runtime_governance.py      (schema, side effects, auth)
 *   - hermes_cli/dev_web_plugin_runtime_binding.py  (reviewed descriptors)
 *   - hermes_cli/dev_web_plugin_runtime.py          (runtime flags, allowlist)
 *   - hermes_cli/dev_web_p0_evidence.py             (P0 gates, authorization)
 *
 * The WebUI does NOT call the CLI, does NOT run the Python runtime, does NOT
 * spawn a process, does NOT fetch remote data, does NOT read or write files,
 * and does NOT access production or ~/.hermes. Every value here is static and
 * deterministic — no current time, no random id, no uuid, no network fetch.
 *
 * This manifest describes the governance state only — it never grants
 * permission, never loads a plugin, never executes a plugin, never authorizes
 * production, and never resolves a P0 gate. resolvedCount stays 0 and every
 * authorization verdict stays NO-GO / not-authorized no matter what renders.
 */

import type {
  RuntimeDescriptorRow,
  RuntimeFixtureAllowlistEntry,
  RuntimeP0EvidenceProjection,
  RuntimeAuthorizationVerdict,
  RuntimeSideEffectFlag,
  RuntimeCliExample,
  RUNTIME_DESCRIPTOR_BINDING_SOURCE,
  ROUTE_GOVERNANCE_BASELINE,
} from '@/types/api/runtimeGovernance'

/** Schema version (mirrors backend GOVERNANCE_VERSION). */
export const RUNTIME_GOVERNANCE_VERSION = 'phase-3i-runtime-governance-v1'

/** Frozen binding-source label (mirrors backend DESCRIPTOR_BINDING_SOURCE). */
export const RUNTIME_DESCRIPTOR_SOURCE: typeof RUNTIME_DESCRIPTOR_BINDING_SOURCE =
  'static_descriptor_registry'

/** Frozen reviewed-fixture descriptor version (mirrors backend _DESC_VERSION). */
export const RUNTIME_DESCRIPTOR_VERSION = 'phase-3i-fixture-descriptor-v1'

/** Frozen route-governance baseline (mirrors backend ROUTE_GOVERNANCE_BASELINE). */
export const RUNTIME_ROUTE_GOVERNANCE_BASELINE: typeof ROUTE_GOVERNANCE_BASELINE = '34/34/5/0/1/1'

/**
 * The frozen reviewed-fixture descriptor registry (mirrors backend
 * REVIEWED_FIXTURE_DESCRIPTORS). Six static records — each names an exact
 * (pluginId, operation) member of the fixture allowlist. No executable content,
 * no module path, no shell command, no real URL, no real secret, no production
 * path. These describe a fixture binding; they are never themselves executed.
 */
export const RUNTIME_REVIEWED_DESCRIPTORS: readonly RuntimeDescriptorRow[] = [
  {
    descriptorId: 'descriptor.fixture.echo_uppercase',
    pluginId: 'fixture.echo',
    operation: 'echo_uppercase',
    source: RUNTIME_DESCRIPTOR_SOURCE,
    version: RUNTIME_DESCRIPTOR_VERSION,
    displayName: 'Fixture Echo Uppercase Descriptor',
    description: 'Reviewed fixture descriptor binding fixture.echo / echo_uppercase.',
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    executable: false,
    remote: false,
    marketplace: false,
    production: false,
    routeChange: false,
    bindingAllowed: true,
  },
  {
    descriptorId: 'descriptor.fixture.normalize_text',
    pluginId: 'fixture.transform',
    operation: 'normalize_text',
    source: RUNTIME_DESCRIPTOR_SOURCE,
    version: RUNTIME_DESCRIPTOR_VERSION,
    displayName: 'Fixture Normalize Text Descriptor',
    description: 'Reviewed fixture descriptor binding fixture.transform / normalize_text.',
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    executable: false,
    remote: false,
    marketplace: false,
    production: false,
    routeChange: false,
    bindingAllowed: true,
  },
  {
    descriptorId: 'descriptor.fixture.validate_required_keys',
    pluginId: 'fixture.validate',
    operation: 'validate_required_keys',
    source: RUNTIME_DESCRIPTOR_SOURCE,
    version: RUNTIME_DESCRIPTOR_VERSION,
    displayName: 'Fixture Validate Required Keys Descriptor',
    description: 'Reviewed fixture descriptor binding fixture.validate / validate_required_keys.',
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    executable: false,
    remote: false,
    marketplace: false,
    production: false,
    routeChange: false,
    bindingAllowed: true,
  },
  {
    descriptorId: 'descriptor.fixture.count_items',
    pluginId: 'fixture.math',
    operation: 'count_items',
    source: RUNTIME_DESCRIPTOR_SOURCE,
    version: RUNTIME_DESCRIPTOR_VERSION,
    displayName: 'Fixture Count Items Descriptor',
    description: 'Reviewed fixture descriptor binding fixture.math / count_items.',
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    executable: false,
    remote: false,
    marketplace: false,
    production: false,
    routeChange: false,
    bindingAllowed: true,
  },
  {
    descriptorId: 'descriptor.fixture.redact_payload',
    pluginId: 'fixture.redact',
    operation: 'redact_payload',
    source: RUNTIME_DESCRIPTOR_SOURCE,
    version: RUNTIME_DESCRIPTOR_VERSION,
    displayName: 'Fixture Redact Payload Descriptor',
    description: 'Reviewed fixture descriptor binding fixture.redact / redact_payload.',
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    executable: false,
    remote: false,
    marketplace: false,
    production: false,
    routeChange: false,
    bindingAllowed: true,
  },
  {
    descriptorId: 'descriptor.fixture.fault',
    pluginId: 'fixture.fault',
    operation: 'deliberate_failure',
    source: RUNTIME_DESCRIPTOR_SOURCE,
    version: RUNTIME_DESCRIPTOR_VERSION,
    displayName: 'Fixture Deliberate Failure Descriptor',
    description: 'Reviewed fixture descriptor binding fixture.fault / deliberate_failure.',
    devOnly: true,
    fixtureOnly: true,
    reviewedFixture: true,
    executable: false,
    remote: false,
    marketplace: false,
    production: false,
    routeChange: false,
    bindingAllowed: true,
  },
]

/**
 * The supported dev-only fixture runtime allowlist (mirrors backend
 * FIXTURE_ALLOWLIST pairs reachable by the reviewed descriptors). Seven
 * (pluginId, operation) pairs. Each is a pure in-process fixture function —
 * never a real plugin, never loaded from disk, never fetched remotely.
 */
export const RUNTIME_FIXTURE_ALLOWLIST: readonly RuntimeFixtureAllowlistEntry[] = [
  { pluginId: 'fixture.echo', operation: 'echo_uppercase' },
  { pluginId: 'fixture.inspect', operation: 'summarize_keys' },
  { pluginId: 'fixture.fault', operation: 'deliberate_failure' },
  { pluginId: 'fixture.transform', operation: 'normalize_text' },
  { pluginId: 'fixture.validate', operation: 'validate_required_keys' },
  { pluginId: 'fixture.math', operation: 'count_items' },
  { pluginId: 'fixture.redact', operation: 'redact_payload' },
]

/** The frozen runtime flags (mirrors backend RUNTIME_FLAGS_FROZEN). */
export const RUNTIME_FLAGS_FROZEN: Readonly<Record<string, boolean>> = {
  dev_only: true,
  fixture_only: true,
  production_access: false,
  external_network: false,
  real_secret_read: false,
  route_change: false,
  runtime_store_write: false,
  arbitrary_plugin_load: false,
  remote_plugin_fetch: false,
  marketplace_access: false,
}

/**
 * The conservative P0 evidence projection (mirrors backend
 * evaluate_p0_evidence() over the 24 frozen gates). resolvedCount is always 0;
 * every authorization flag is frozen NO-GO / not-authorized.
 *
 * Gate distribution (24 total): 19 partial_evidence, 5 blocked_by_human_review,
 * 0 candidate_for_review, 0 governance_only, 0 no_evidence, 0 resolved.
 */
export const RUNTIME_P0_EVIDENCE: RuntimeP0EvidenceProjection = {
  totalGates: 24,
  resolvedCount: 0,
  partialEvidenceCount: 19,
  candidateForReviewCount: 0,
  blockedByHumanReviewCount: 5,
  governanceOnlyCount: 0,
  noEvidenceCount: 0,
  unresolvedCount: 24,
  implementationAuthorization: 'NO-GO',
  phase3iAuthorized: false,
  realRuntime: 'NO-GO',
  newRoute: 'NO-GO',
  productionRollout: 'NO-GO',
  classificationNote:
    'Dev-only descriptor-backed fixture execution is partial evidence only. ' +
    'It never resolves a P0 gate, never authorizes production, and never ' +
    'authorizes a real runtime. Resolution requires a valid out-of-band human ' +
    'approval the dev skeleton cannot produce.',
}

/**
 * The frozen authorization verdict block (mirrors backend
 * authorization_projection()). Every dimension is frozen — a governance pass
 * authorizes nothing.
 */
export const RUNTIME_AUTHORIZATION_VERDICTS: readonly RuntimeAuthorizationVerdict[] = [
  { key: 'implementationGate', label: 'Implementation Authorization', verdict: 'NO-GO', kind: 'gate' },
  { key: 'phase3iProductionGate', label: 'Phase 3I Production Authorization', verdict: 'NOT_AUTHORIZED', kind: 'gate' },
  { key: 'productionRuntimeGate', label: 'Production Runtime', verdict: 'NO-GO', kind: 'gate' },
  { key: 'newRouteGate', label: 'New Route', verdict: 'NO-GO', kind: 'gate' },
  { key: 'productionRolloutGate', label: 'Production Rollout', verdict: 'NO-GO', kind: 'gate' },
  { key: 'arbitraryPluginLoading', label: 'Arbitrary Plugin Loading', verdict: 'NO-GO', kind: 'dimension' },
  { key: 'localPluginDirectoryLoading', label: 'Local Plugin Directory Loading', verdict: 'NO-GO', kind: 'dimension' },
  { key: 'remoteRegistry', label: 'Remote Registry', verdict: 'NO-GO', kind: 'dimension' },
  { key: 'marketplace', label: 'Marketplace', verdict: 'NO-GO', kind: 'dimension' },
  { key: 'externalNetwork', label: 'External Network', verdict: 'NO-GO', kind: 'dimension' },
  { key: 'productionRollout', label: 'Production Rollout (supply chain)', verdict: 'NO-GO', kind: 'dimension' },
  { key: 'realApiKeyRead', label: 'Real API Key Read', verdict: 'false', kind: 'flag' },
]

/**
 * The frozen all-False side-effect surface (mirrors backend
 * side_effect_projection()). A governance pass performs none of these actions
 * no matter what renders or what untrusted metadata a request carries.
 */
export const RUNTIME_SIDE_EFFECT_FLAGS: readonly RuntimeSideEffectFlag[] = [
  { key: 'productionAccess', label: 'Production access', value: false },
  { key: 'externalNetwork', label: 'External network', value: false },
  { key: 'realSecretRead', label: 'Real secret read', value: false },
  { key: 'routeChange', label: 'Route change', value: false },
  { key: 'runtimeStoreWrite', label: 'Runtime store write', value: false },
  { key: 'auditStoreWrite', label: 'Audit store write', value: false },
  { key: 'arbitraryPluginLoad', label: 'Arbitrary plugin load', value: false },
  { key: 'localPluginDirectoryRead', label: 'Local plugin directory read', value: false },
  { key: 'remotePluginFetch', label: 'Remote plugin fetch', value: false },
  { key: 'marketplaceAccess', label: 'Marketplace access', value: false },
  { key: 'inputFileRead', label: 'Input file read', value: false },
  { key: 'outputFileWrite', label: 'Output file write', value: false },
]

/**
 * Read-only CLI command examples (mirrors backend COMMAND_EXAMPLES). These are
 * text-only documentation for the developer-facing CLI that runs OUTSIDE the
 * WebUI. The WebUI renders them as text — it never executes them, never spawns
 * a shell, and never writes the example to a file.
 */
export const RUNTIME_CLI_EXAMPLES: readonly RuntimeCliExample[] = [
  {
    command: 'hermes dev-runtime list',
    summary: 'List the frozen reviewed-fixture descriptors (no execution).',
    aliases: ['ls'],
  },
  {
    command: 'hermes dev-runtime show descriptor.fixture.echo_uppercase',
    summary: 'Inspect the registry→runtime binding for a descriptor (no execution).',
    aliases: ['inspect'],
  },
  {
    command: "hermes dev-runtime run descriptor.fixture.echo_uppercase --input '{\"text\":\"hello\"}'",
    summary: 'Run a reviewed-fixture descriptor (single). Dev-only partial evidence only.',
    aliases: ['exec'],
  },
  {
    command:
      "hermes dev-runtime batch --items '[{\"descriptor_id\":\"descriptor.fixture.echo_uppercase\",\"input\":{\"text\":\"hello\"}}]'",
    summary: 'Run a multi-descriptor batch (fail-closed, isolated). Dev-only partial evidence only.',
    aliases: [],
  },
  {
    command: "hermes dev-runtime audit descriptor.fixture.echo_uppercase --input '{\"text\":\"hello\"}'",
    summary: 'Project the redacted audit from a run / batch report (no re-execution).',
    aliases: [],
  },
  {
    command: 'hermes dev-runtime p0-report',
    summary: 'Print the conservative P0 evidence projection summary.',
    aliases: ['evidence'],
  },
]

/** Canonical CLI commands (mirrors backend COMMANDS). */
export const RUNTIME_CLI_COMMANDS: readonly string[] = [
  'list',
  'show',
  'run',
  'batch',
  'audit',
  'p0-report',
  'help',
]

/** Canonical CLI aliases (mirrors backend COMMAND_ALIASES). */
export const RUNTIME_CLI_ALIASES: Readonly<Record<string, string>> = {
  ls: 'list',
  inspect: 'show',
  exec: 'run',
  evidence: 'p0-report',
}
