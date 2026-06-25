/**
 * Phase 4B — Target B Implementation view-model tests.
 *
 * Asserts the pure Target B implementation projections are deterministic and
 * carry the frozen, gated scaffold state:
 *   - the summary (implementation SCAFFOLD_READY, execution DISABLED, every
 *     authorization NO-GO, P0 24 / 19 / 0 / 5);
 *   - the 12 implementation layers (every one disabled / non-executing /
 *     non-networking / non-production);
 *   - the signed plugin package schema preview (fake / not loaded / not
 *     executable);
 *   - the 15-permission model (every one DENIED_BY_DEFAULT) + 6 non-executable
 *     capabilities;
 *   - the signature verification projection (production not authorized, fixture
 *     only, unsigned/forged rejected);
 *   - the registry trust projection (DISABLED, network/fetch/marketplace off);
 *   - the sandbox broker projection (disabled, no spawn/network/write/secrets);
 *   - the approval gate (human approval required, no trust token, fake/AI/
 *     metadata rejected);
 *   - the execution policy (allowed false, webui execute disabled, runtime
 *     route disabled, production runtime disabled, p0ResolvedCount 0);
 *   - the audit/rollback projection (in-memory only, kill switch design-ready
 *     only, production rollout NO-GO);
 *   - immutability (an external mutation cannot reach the canonical manifest,
 *     cannot flip a NO-GO, cannot flip a disabled capability, cannot grant a
 *     permission, cannot enable a disabled execution flag, cannot raise P0
 *     resolved above 0); and
 *   - the defense-in-depth redactor masks every secret-shaped /
 *     production-path-shaped / fake-authorization-shaped substring.
 */
import { describe, it, expect } from 'vitest'

import {
  buildTargetBImplementationViewModel,
  buildTargetBImplementationSummary,
  buildTargetBImplementationSummaryCards,
  buildTargetBImplementationSummaryText,
  buildTargetBImplementationLayers,
  buildTargetBPackageSchema,
  buildTargetBImplementationPermissionModel,
  buildTargetBCapabilityModel,
  buildTargetBSignatureVerification,
  buildTargetBRegistryTrust,
  buildTargetBSandboxBroker,
  buildTargetBApprovalGate,
  buildTargetBExecutionPolicy,
  buildTargetBAuditRollback,
  filterTargetBImplementationLayers,
  allTargetBImplementationVerdictsNoGo,
  allTargetBImplementationLayersDisabled,
  allTargetBImplementationPermissionsDenied,
  redactTargetBImplementationValue,
} from '@/lib/targetBImplementationViewModel'
import {
  TARGET_B_IMPLEMENTATION_SUMMARY,
  TARGET_B_IMPLEMENTATION_LAYERS,
  TARGET_B_PERMISSION_ENTRIES,
  TARGET_B_SIGNATURE_VERIFICATION,
  TARGET_B_REGISTRY_TRUST,
  TARGET_B_SANDBOX_BROKER,
  TARGET_B_APPROVAL_GATE,
  TARGET_B_EXECUTION_POLICY,
  TARGET_B_IMPLEMENTATION_BLOCKERS,
} from '@/constants/targetBImplementationManifest'

describe('targetBImplementation view-model (Phase 4B) — determinism + summary', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildTargetBImplementationViewModel()
    const b = buildTargetBImplementationViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('the frozen summary is SCAFFOLD_READY / DISABLED with every authorization NO-GO', () => {
    const s = buildTargetBImplementationSummary()
    expect(s.targetName).toBe('Target B — Production Runtime / Real Plugin Ecosystem')
    expect(s.implementationStatus).toBe('SCAFFOLD_READY')
    expect(s.executionStatus).toBe('DISABLED')
    expect(s.productionRuntime).toBe('NO-GO')
    expect(s.arbitraryPluginLoading).toBe('NO-GO')
    expect(s.remoteRegistry).toBe('NO-GO')
    expect(s.marketplace).toBe('NO-GO')
    expect(s.webuiExecution).toBe('NO-GO')
    expect(s.approvalAuthorization).toBe('NO-GO')
    expect(s.productionRollout).toBe('NO-GO')
    expect(s.p0Total).toBe(24)
    expect(s.p0PartialEvidence).toBe(19)
    expect(s.p0Resolved).toBe(0)
    expect(s.p0PendingHumanReview).toBe(5)
    expect(s.pendingHumanReviewGates).toEqual(['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22'])
    expect(allTargetBImplementationVerdictsNoGo(s)).toBe(true)
  })

  it('the summary forbids any GO / COMPLETE / authorized / enabled value', () => {
    const text = JSON.stringify(buildTargetBImplementationSummary()).toLowerCase()
    expect(text).not.toContain('"go"')
    expect(text).not.toContain('complete')
    expect(text).not.toContain('authorized')
    expect(text).not.toContain('"enabled"')
    expect(text).not.toContain('"approved"')
  })

  it('summary cards include the required NO-GO verdicts and frozen counts', () => {
    const cards = buildTargetBImplementationSummaryCards()
    const byLabel = new Map(cards.map((c) => [c.label, c]))
    expect(byLabel.get('Execution')!.value).toBe('DISABLED')
    expect(byLabel.get('Production runtime')!.value).toBe('NO-GO')
    expect(byLabel.get('WebUI execution')!.value).toBe('NO-GO')
    expect(byLabel.get('Remote registry')!.value).toBe('NO-GO')
    expect(byLabel.get('Marketplace')!.value).toBe('NO-GO')
    expect(byLabel.get('Approval / authorization')!.value).toBe('NO-GO')
    expect(byLabel.get('Production rollout')!.value).toBe('NO-GO')
    expect(byLabel.get('P0 resolved')!.value).toBe(0)
    expect(byLabel.get('Implementation layers')!.value).toBe(12)
    expect(byLabel.get('Route governance')!.value).toBe('34/34/5/0/1/1')
  })
})

describe('targetBImplementation view-model — implementation layers', () => {
  it('projects the required 12 implementation layers', () => {
    const rows = buildTargetBImplementationLayers()
    expect(rows.length).toBe(12)
    const names = rows.map((r) => r.layer)
    for (const required of [
      'Shared Common Helpers',
      'Signed Plugin Package Schema',
      'Plugin Signature Verification',
      'Permission / Capability Model',
      'Registry Trust Policy',
      'Sandbox Broker',
      'Approval / Authorization Gate',
      'Execution Policy Gate',
      'Runtime Orchestrator',
      'Audit Trail',
      'Rollback / Kill Switch',
      'End-to-End Readiness Report',
    ]) {
      expect(names, `missing layer ${required}`).toContain(required)
    }
  })

  it('every layer is disabled / non-executing / non-networking / non-production', () => {
    const rows = buildTargetBImplementationLayers()
    expect(allTargetBImplementationLayersDisabled(rows)).toBe(true)
    for (const l of rows) {
      expect(l.enabled).toBe(false)
      expect(l.executionCapable).toBe(false)
      expect(l.networkCapable).toBe(false)
      expect(l.productionCapable).toBe(false)
    }
  })

  it('every layer status is designed / scaffolded-disabled (never enabled)', () => {
    for (const l of buildTargetBImplementationLayers()) {
      expect(l.status === 'DESIGNED' || l.status === 'SCAFFOLDED_DISABLED').toBe(true)
    }
  })

  it('the client-side filter returns all layers for "all" and a strict subset otherwise', () => {
    expect(filterTargetBImplementationLayers('all').length).toBe(
      buildTargetBImplementationLayers().length,
    )
    const designed = filterTargetBImplementationLayers('DESIGNED')
    const scaffolded = filterTargetBImplementationLayers('SCAFFOLDED_DISABLED')
    for (const l of designed) expect(l.status).toBe('DESIGNED')
    for (const l of scaffolded) expect(l.status).toBe('SCAFFOLDED_DISABLED')
    expect(designed.length + scaffolded.length).toBe(
      filterTargetBImplementationLayers('all').length,
    )
  })
})

describe('targetBImplementation view-model — package schema preview', () => {
  it('is example-only, not loaded, not executable', () => {
    const s = buildTargetBPackageSchema()
    expect(s.exampleOnly).toBe(true)
    expect(s.notLoaded).toBe(true)
    expect(s.notExecutable).toBe(true)
    expect(s.registrySource).toBe('https://registry.example.invalid')
    expect(s.entrypoints.length).toBeGreaterThan(0)
    expect(s.signatureAlgorithm).toBe('fixture-hmac-sha256')
    expect(s.signature).not.toContain('PRIVATE KEY')
  })
})

describe('targetBImplementation view-model — permission + capability model', () => {
  it('projects the required 15 permissions, every one DENIED_BY_DEFAULT', () => {
    const model = buildTargetBImplementationPermissionModel()
    expect(model.defaultDisposition).toBe('DENIED_BY_DEFAULT')
    expect(model.anyGranted).toBe(false)
    expect(model.dangerousPermissionsDenied).toBe(true)
    expect(allTargetBImplementationPermissionsDenied(model.entries)).toBe(true)
    expect(model.entries.length).toBe(15)
    const keys = model.entries.map((p) => p.key)
    for (const required of [
      'filesystem.read',
      'filesystem.write',
      'network.http',
      'network.registry',
      'secrets.read',
      'provider.read',
      'provider.write',
      'ui.render',
      'tool.invoke',
      'database.read',
      'database.write',
      'process.spawn',
      'runtime.execute',
      'plugin.install',
      'marketplace.fetch',
    ]) {
      expect(keys, `missing permission ${required}`).toContain(required)
    }
    for (const p of model.entries) {
      expect(p.currentStatus).toBe('DENIED_BY_DEFAULT')
      expect(p.grantable).toBe(false)
    }
  })

  it('the capability model is non-executable metadata', () => {
    const model = buildTargetBCapabilityModel()
    expect(model.anyExecutable).toBe(false)
    expect(model.entries.length).toBe(6)
    for (const c of model.entries) {
      expect(c.executable).toBe(false)
    }
  })
})

describe('targetBImplementation view-model — layer projections', () => {
  it('signature verification: production not authorized, fixture only, rejects', () => {
    const s = buildTargetBSignatureVerification()
    expect(s.verifierInterfaceImplemented).toBe(true)
    expect(s.productionVerifierAuthorized).toBe(false)
    expect(s.fixtureVerifierOnly).toBe(true)
    expect(s.trusted).toBe(false)
    expect(s.productionApproved).toBe(false)
    expect(s.unsignedRejected).toBe(true)
    expect(s.forgedRejected).toBe(true)
    expect(s.marketplaceRejected).toBe(true)
    expect(s.unknownPublisherRejected).toBe(true)
    expect(s.productionAuthorization).toBe('NO-GO')
  })

  it('registry trust: DISABLED, network/fetch/marketplace off', () => {
    const r = buildTargetBRegistryTrust()
    expect(r.registryMode).toBe('DISABLED')
    expect(r.networkEnabled).toBe(false)
    expect(r.fetchEnabled).toBe(false)
    expect(r.marketplaceEnabled).toBe(false)
    expect(r.allowUnsigned).toBe(false)
    expect(r.trustedPublishersCount).toBe(0)
    expect(r.registryUrlExample).toBe('https://registry.example.invalid')
    expect(r.productionAuthorization).toBe('NO-GO')
  })

  it('sandbox broker: disabled, no spawn/network/write/secrets', () => {
    const s = buildTargetBSandboxBroker()
    expect(s.brokerInterfaceImplemented).toBe(true)
    expect(s.brokerEnabled).toBe(false)
    expect(s.executionAllowed).toBe(false)
    expect(s.processSpawnAllowed).toBe(false)
    expect(s.networkAllowed).toBe(false)
    expect(s.filesystemWriteAllowed).toBe(false)
    expect(s.secretsAllowed).toBe(false)
    expect(s.productionAuthorization).toBe('NO-GO')
  })

  it('approval gate: human approval required, no token, fake/AI/metadata rejected', () => {
    const g = buildTargetBApprovalGate()
    expect(g.humanApprovalRequired).toBe(true)
    expect(g.trustTokenProvisioned).toBe(false)
    expect(g.humanApprovalValid).toBe(false)
    expect(g.fakeApprovalAccepted).toBe(false)
    expect(g.aiApprovalAccepted).toBe(false)
    expect(g.metadataApprovalAccepted).toBe(false)
    expect(g.productionAuthorization).toBe('NO-GO')
  })

  it('execution policy: allowed false, webui execute disabled, runtime route disabled', () => {
    const e = buildTargetBExecutionPolicy()
    expect(e.allowed).toBe(false)
    expect(e.canExecutePlugin).toBe(false)
    expect(e.canLoadPluginPackage).toBe(false)
    expect(e.canFetchRegistry).toBe(false)
    expect(e.canRenderWebuiExecuteControl).toBe(false)
    expect(e.webuiExecuteEnabled).toBe(false)
    expect(e.runtimeRouteEnabled).toBe(false)
    expect(e.productionRuntimeEnabled).toBe(false)
    expect(e.p0ResolvedCount).toBe(0)
    expect(e.routeGovernanceBaseline).toBe('34/34/5/0/1/1')
    expect(e.reasons.length).toBeGreaterThan(0)
    expect(e.productionAuthorization).toBe('NO-GO')
  })

  it('audit/rollback: in-memory only, kill switch design-ready, rollout NO-GO', () => {
    const ar = buildTargetBAuditRollback()
    expect(ar.auditPersistence).toBe('in_memory_only')
    expect(ar.auditPersisted).toBe(false)
    expect(ar.auditJsonlWritten).toBe(false)
    expect(ar.killSwitchReady).toBe('DESIGN_READY_ONLY')
    expect(ar.productionRollbackAuthorized).toBe(false)
    expect(ar.productionRollout).toBe('NO-GO')
    expect(ar.productionGatewayUntouched).toBe(true)
  })
})

describe('targetBImplementation view-model — summary text', () => {
  it('is deterministic, states DISABLED / NO-GO / prerequisite evidence, frozen counts', () => {
    const text = buildTargetBImplementationSummaryText()
    expect(text).toContain('SCAFFOLD_READY')
    expect(text).toContain('DISABLED')
    expect(text).toContain('NO-GO')
    expect(text).toContain('34/34/5/0/1/1')
    expect(text).toContain('12')
    expect(text.toLowerCase()).toContain('does not authorize target b')
    expect(buildTargetBImplementationSummaryText()).toBe(text)
  })
})

describe('targetBImplementation view-model — immutability', () => {
  it('the canonical manifest exports are frozen', () => {
    expect(Object.isFrozen(TARGET_B_IMPLEMENTATION_SUMMARY)).toBe(true)
    expect(Object.isFrozen(TARGET_B_IMPLEMENTATION_LAYERS)).toBe(true)
    expect(Object.isFrozen(TARGET_B_IMPLEMENTATION_LAYERS[0])).toBe(true)
    expect(Object.isFrozen(TARGET_B_PERMISSION_ENTRIES)).toBe(true)
    expect(Object.isFrozen(TARGET_B_SIGNATURE_VERIFICATION)).toBe(true)
    expect(Object.isFrozen(TARGET_B_REGISTRY_TRUST)).toBe(true)
    expect(Object.isFrozen(TARGET_B_SANDBOX_BROKER)).toBe(true)
    expect(Object.isFrozen(TARGET_B_APPROVAL_GATE)).toBe(true)
    expect(Object.isFrozen(TARGET_B_EXECUTION_POLICY)).toBe(true)
    expect(Object.isFrozen(TARGET_B_IMPLEMENTATION_BLOCKERS)).toBe(true)
  })

  it('mutating a returned summary cannot flip execution / production / rollout / p0', () => {
    const s = buildTargetBImplementationSummary()
    s.executionStatus = 'ENABLED' as unknown as 'DISABLED'
    s.productionRuntime = 'GO' as unknown as 'NO-GO'
    s.productionRollout = 'GO' as unknown as 'NO-GO'
    s.p0Resolved = 24 as unknown as 0
    const fresh = buildTargetBImplementationSummary()
    expect(fresh.executionStatus).toBe('DISABLED')
    expect(fresh.productionRuntime).toBe('NO-GO')
    expect(fresh.productionRollout).toBe('NO-GO')
    expect(fresh.p0Resolved).toBe(0)
  })

  it('mutating a returned layer cannot enable a capability', () => {
    const before = TARGET_B_IMPLEMENTATION_LAYERS[0]!.enabled
    const rows = buildTargetBImplementationLayers()
    rows[0]!.enabled = true
    rows[0]!.executionCapable = true
    rows.length = 0
    expect(TARGET_B_IMPLEMENTATION_LAYERS[0]!.enabled).toBe(before)
    const fresh = buildTargetBImplementationLayers()
    expect(fresh.length).toBe(TARGET_B_IMPLEMENTATION_LAYERS.length)
    expect(fresh[0]!.enabled).toBe(false)
  })

  it('mutating a returned permission model cannot grant a permission', () => {
    const model = buildTargetBImplementationPermissionModel()
    model.defaultDisposition = 'GRANTED' as unknown as 'DENIED_BY_DEFAULT'
    model.anyGranted = true as unknown as false
    model.entries[0]!.currentStatus = 'GRANTED' as unknown as 'DENIED_BY_DEFAULT'
    const fresh = buildTargetBImplementationPermissionModel()
    expect(fresh.defaultDisposition).toBe('DENIED_BY_DEFAULT')
    expect(fresh.anyGranted).toBe(false)
    expect(fresh.entries[0]!.currentStatus).toBe('DENIED_BY_DEFAULT')
  })

  it('mutating a returned execution policy cannot enable webui execute or a route', () => {
    const e = buildTargetBExecutionPolicy()
    e.allowed = true as unknown as false
    e.webuiExecuteEnabled = true as unknown as false
    e.runtimeRouteEnabled = true as unknown as false
    e.productionRuntimeEnabled = true as unknown as false
    const fresh = buildTargetBExecutionPolicy()
    expect(fresh.allowed).toBe(false)
    expect(fresh.webuiExecuteEnabled).toBe(false)
    expect(fresh.runtimeRouteEnabled).toBe(false)
    expect(fresh.productionRuntimeEnabled).toBe(false)
  })

  it('mutating a returned approval gate cannot provision a token or accept fake approval', () => {
    const g = buildTargetBApprovalGate()
    g.trustTokenProvisioned = true as unknown as false
    g.fakeApprovalAccepted = true as unknown as false
    g.productionAuthorization = 'GO' as unknown as 'NO-GO'
    const fresh = buildTargetBApprovalGate()
    expect(fresh.trustTokenProvisioned).toBe(false)
    expect(fresh.fakeApprovalAccepted).toBe(false)
    expect(fresh.productionAuthorization).toBe('NO-GO')
  })

  it('mutating returned registry / sandbox / signature projections cannot enable anything', () => {
    const r = buildTargetBRegistryTrust()
    r.networkEnabled = true as unknown as false
    r.marketplaceEnabled = true as unknown as false
    const sb = buildTargetBSandboxBroker()
    sb.brokerEnabled = true as unknown as false
    sb.processSpawnAllowed = true as unknown as false
    const sv = buildTargetBSignatureVerification()
    sv.productionVerifierAuthorized = true as unknown as false
    sv.trusted = true as unknown as false
    expect(buildTargetBRegistryTrust().networkEnabled).toBe(false)
    expect(buildTargetBSandboxBroker().brokerEnabled).toBe(false)
    expect(buildTargetBSignatureVerification().productionVerifierAuthorized).toBe(false)
    expect(buildTargetBSignatureVerification().trusted).toBe(false)
  })
})

describe('targetBImplementation view-model — defense-in-depth redactor (corpus)', () => {
  const CORPUS = [
    'sk-FAKE-SECRET-DO-NOT-LEAK-12345678',
    'Authorization: Bearer fake-token',
    'ghp_fakegithubtoken',
    'xox-fake-slack-token',
    'BEGIN PRIVATE KEY fake',
    'OPENAI_API_KEY=fake',
    'db_password=fake',
    'accessToken=fake',
    '~/.hermes',
    '/fake/production/state.db',
    'implementation_authorization=GO',
    'phase_3i_authorized=true',
    'production_approved=true',
    'route_exception_approved=true',
    'approved_by_ai=true',
    'trust_token=fake',
    'registry_token=fake',
    'plugin_signature=fake-private-key',
    'target_b_authorized=true',
    'production_runtime_go=true',
  ]

  it.each(CORPUS)('masks secret-shaped / fake-authorization value %s', (value) => {
    expect(redactTargetBImplementationValue(value)).toBe('[REDACTED]')
  })

  it('leaves safe Target B implementation text intact', () => {
    expect(redactTargetBImplementationValue('Target B: IMPLEMENTATION SCAFFOLD')).toContain('SCAFFOLD')
    expect(redactTargetBImplementationValue('Execution disabled')).toContain('disabled')
    expect(redactTargetBImplementationValue('https://registry.example.invalid')).toContain(
      'registry.example.invalid',
    )
  })

  it('the static manifest carries no secret-shaped / fake-authorization text', () => {
    const texts: string[] = []
    texts.push(TARGET_B_IMPLEMENTATION_SUMMARY.targetName)
    for (const r of TARGET_B_IMPLEMENTATION_SUMMARY.requiredBeforeEnable) texts.push(r)
    for (const l of TARGET_B_IMPLEMENTATION_LAYERS) texts.push(l.layer, l.requiredGate)
    for (const b of TARGET_B_IMPLEMENTATION_BLOCKERS) texts.push(b.detail)
    for (const c of CORPUS) {
      for (const text of texts) {
        expect(text).not.toContain(c)
      }
    }
  })
})
