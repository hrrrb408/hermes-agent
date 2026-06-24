/**
 * Phase 4A — Target B Readiness view-model tests.
 *
 * Asserts the pure Target B readiness projections are deterministic and carry
 * the frozen, disabled scaffold state:
 *   - the summary (readiness SCAFFOLD_READY, execution DISABLED, every
 *     authorization NO-GO, P0 24 / 0 / 5);
 *   - the 16 architecture modules (every one disabled / non-executing /
 *     non-networking / non-production / no route);
 *   - the plugin package schema preview (fake / not loaded / not executable);
 *   - the 12-permission model (every one DENIED_BY_DEFAULT);
 *   - the registry protocol preview (.invalid URL, fetch / network / marketplace
 *     disabled, signature required, unsigned disallowed);
 *   - the WebUI execution preview (canSubmit false, no execute button, no
 *     runtime route, PREVIEW_ONLY_DISABLED);
 *   - the approval gate (human approval required, no trust token, fake / AI /
 *     metadata approval rejected, production authorization NO-GO);
 *   - immutability (an external mutation cannot reach the canonical manifest,
 *     cannot flip a NO-GO, cannot flip a disabled capability, cannot grant a
 *     permission, cannot enable a disabled execution step, cannot enable
 *     canSubmit, cannot raise P0 resolved above 0); and
 *   - the defense-in-depth redactor masks every secret-shaped /
 *     production-path-shaped / fake-authorization-shaped substring — including
 *     the Target-B authorization markers (registry_token, plugin_signature, …).
 */
import { describe, it, expect } from 'vitest'

import {
  buildTargetBReadinessViewModel,
  buildTargetBReadinessSummary,
  buildTargetBReadinessSummaryCards,
  buildTargetBReadinessSummaryText,
  buildTargetBArchitectureModules,
  buildTargetBPluginPackageSchema,
  buildTargetBPermissionModel,
  buildTargetBRegistryProtocol,
  buildTargetBWebUIExecution,
  buildTargetBApprovalGate,
  buildTargetBEnablementBlockers,
  buildTargetBTargetARelationship,
  buildTargetBReadinessChecklist,
  filterTargetBModules,
  allTargetBVerdictsNoGo,
  allTargetBModulesDisabled,
  allTargetBPermissionsDenied,
  redactTargetBValue,
} from '@/lib/targetBReadinessViewModel'
import {
  TARGET_B_READINESS_SUMMARY,
  TARGET_B_ARCHITECTURE_MODULES,
  TARGET_B_PERMISSION_ENTRIES,
  TARGET_B_WEBUI_EXECUTION,
  TARGET_B_APPROVAL_GATE,
  TARGET_B_READINESS_CHECKLIST,
  TARGET_B_ENABLEMENT_BLOCKERS,
} from '@/constants/targetBReadinessManifest'

describe('targetBReadiness view-model (Phase 4A) — determinism + summary', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildTargetBReadinessViewModel()
    const b = buildTargetBReadinessViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('the frozen summary is SCAFFOLD_READY / DISABLED with every authorization NO-GO', () => {
    const s = buildTargetBReadinessSummary()
    expect(s.targetName).toBe('Target B — Production Runtime / Real Plugin Ecosystem')
    expect(s.readinessStatus).toBe('SCAFFOLD_READY')
    expect(s.executionStatus).toBe('DISABLED')
    expect(s.productionRuntime).toBe('NO-GO')
    expect(s.arbitraryPluginLoading).toBe('NO-GO')
    expect(s.remoteRegistry).toBe('NO-GO')
    expect(s.marketplace).toBe('NO-GO')
    expect(s.webuiExecution).toBe('NO-GO')
    expect(s.approvalAuthorization).toBe('NO-GO')
    expect(s.productionRollout).toBe('NO-GO')
    expect(s.p0Total).toBe(24)
    expect(s.p0Resolved).toBe(0)
    expect(s.p0PendingHumanReview).toBe(5)
    expect(s.requiredBeforeEnable.length).toBeGreaterThan(0)
    expect(allTargetBVerdictsNoGo(s)).toBe(true)
  })

  it('the summary forbids any GO / COMPLETE / authorized / enabled value', () => {
    const text = JSON.stringify(buildTargetBReadinessSummary()).toLowerCase()
    expect(text).not.toContain('"go"')
    expect(text).not.toContain('complete')
    expect(text).not.toContain('authorized')
    expect(text).not.toContain('enabled')
    expect(text).not.toContain('approved')
  })

  it('summary cards include the required NO-GO verdicts and frozen counts', () => {
    const cards = buildTargetBReadinessSummaryCards()
    const byLabel = new Map(cards.map((c) => [c.label, c]))
    expect(byLabel.get('Execution')!.value).toBe('DISABLED')
    expect(byLabel.get('Production runtime')!.value).toBe('NO-GO')
    expect(byLabel.get('Remote registry')!.value).toBe('NO-GO')
    expect(byLabel.get('Marketplace')!.value).toBe('NO-GO')
    expect(byLabel.get('WebUI execution')!.value).toBe('NO-GO')
    expect(byLabel.get('Approval / authorization')!.value).toBe('NO-GO')
    expect(byLabel.get('Production rollout')!.value).toBe('NO-GO')
    expect(byLabel.get('P0 resolved')!.value).toBe(0)
    expect(byLabel.get('Route governance')!.value).toBe('34/34/5/0/1/1')
  })
})

describe('targetBReadiness view-model — architecture modules', () => {
  it('projects the required architecture modules', () => {
    const rows = buildTargetBArchitectureModules()
    expect(rows.length).toBeGreaterThanOrEqual(16)
    const names = rows.map((r) => r.module)
    for (const required of [
      'Plugin Package Format',
      'Plugin Signature Verification',
      'Plugin Permission Model',
      'Plugin Capability Declaration',
      'Remote Registry Protocol',
      'Registry Trust Policy',
      'Marketplace Policy',
      'Runtime Sandbox Boundary',
      'Execution Broker',
      'WebUI Execution Request Flow',
      'Approval / Authorization Gate',
      'Audit Trail',
      'Rollback / Kill Switch',
      'Secret Handling Boundary',
      'Network Policy',
      'Production Rollout Plan',
    ]) {
      expect(names, `missing module ${required}`).toContain(required)
    }
  })

  it('every module is disabled / non-executing / non-networking / non-production / no route', () => {
    const rows = buildTargetBArchitectureModules()
    expect(allTargetBModulesDisabled(rows)).toBe(true)
    for (const m of rows) {
      expect(m.enabled).toBe(false)
      expect(m.executionCapable).toBe(false)
      expect(m.networkCapable).toBe(false)
      expect(m.productionCapable).toBe(false)
      expect(m.routeImpact).toBe('none')
    }
  })

  it('every module status is designed / scaffolded-disabled (never enabled)', () => {
    for (const m of buildTargetBArchitectureModules()) {
      expect(m.status === 'DESIGNED' || m.status === 'SCAFFOLDED_DISABLED').toBe(true)
    }
  })

  it('the client-side filter returns all modules for "all" and a strict subset otherwise', () => {
    expect(filterTargetBModules('all').length).toBe(buildTargetBArchitectureModules().length)
    const designed = filterTargetBModules('DESIGNED')
    const scaffolded = filterTargetBModules('SCAFFOLDED_DISABLED')
    for (const m of designed) expect(m.status).toBe('DESIGNED')
    for (const m of scaffolded) expect(m.status).toBe('SCAFFOLDED_DISABLED')
    expect(designed.length + scaffolded.length).toBe(filterTargetBModules('all').length)
  })
})

describe('targetBReadiness view-model — plugin package schema preview', () => {
  it('is example-only, not loaded, not executable', () => {
    const s = buildTargetBPluginPackageSchema()
    expect(s.exampleOnly).toBe(true)
    expect(s.notLoaded).toBe(true)
    expect(s.notExecutable).toBe(true)
    expect(s.registrySource).toBe('https://registry.example.invalid')
    expect(s.entrypoints.length).toBeGreaterThan(0)
    // No real secret / signature material is carried.
    expect(s.signature).not.toContain('PRIVATE KEY')
  })
})

describe('targetBReadiness view-model — permission model', () => {
  it('projects the required permissions, every one DENIED_BY_DEFAULT', () => {
    const model = buildTargetBPermissionModel()
    expect(model.defaultDisposition).toBe('DENIED_BY_DEFAULT')
    expect(model.anyGranted).toBe(false)
    expect(allTargetBPermissionsDenied(model.entries)).toBe(true)
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
    ]) {
      expect(keys, `missing permission ${required}`).toContain(required)
    }
    for (const p of model.entries) {
      expect(p.currentStatus).toBe('DENIED_BY_DEFAULT')
    }
  })
})

describe('targetBReadiness view-model — registry protocol preview', () => {
  it('uses a reserved .invalid URL and stays disabled', () => {
    const r = buildTargetBRegistryProtocol()
    expect(r.registryUrlExample).toBe('https://registry.example.invalid')
    expect(r.fetchEnabled).toBe(false)
    expect(r.networkEnabled).toBe(false)
    expect(r.trustPolicyRequired).toBe(true)
    expect(r.signatureRequired).toBe(true)
    expect(r.allowUnsigned).toBe(false)
    expect(r.marketplaceEnabled).toBe(false)
  })
})

describe('targetBReadiness view-model — WebUI execution preview', () => {
  it('is preview-only disabled with no submit, no execute button, no runtime route', () => {
    const e = buildTargetBWebUIExecution()
    expect(e.visibleInWebUI).toBe(true)
    expect(e.executeButtonEnabled).toBe(false)
    expect(e.approvalRequired).toBe(true)
    expect(e.runtimeRouteAvailable).toBe(false)
    expect(e.canSubmit).toBe(false)
    expect(e.status).toBe('PREVIEW_ONLY_DISABLED')
    expect(e.flow.length).toBeGreaterThan(0)
    for (const step of e.flow) {
      expect(step.enabled).toBe(false)
    }
  })

  it('the flow includes the disabled select / validate / approve / execute / audit steps', () => {
    const keys = buildTargetBWebUIExecution().flow.map((s) => s.key)
    for (const required of ['selectPackage', 'validateSignature', 'requestApproval', 'execute', 'audit']) {
      expect(keys, `missing flow step ${required}`).toContain(required)
    }
  })
})

describe('targetBReadiness view-model — approval gate', () => {
  it('requires human approval and rejects fake / AI / metadata approval', () => {
    const g = buildTargetBApprovalGate()
    expect(g.humanApprovalRequired).toBe(true)
    expect(g.trustTokenProvisioned).toBe(false)
    expect(g.fakeApprovalAccepted).toBe(false)
    expect(g.aiApprovalAccepted).toBe(false)
    expect(g.metadataApprovalAccepted).toBe(false)
    expect(g.productionAuthorization).toBe('NO-GO')
  })
})

describe('targetBReadiness view-model — enablement blockers + Target A relationship + checklist', () => {
  it('every enablement blocker stays unresolved', () => {
    const blockers = buildTargetBEnablementBlockers()
    expect(blockers.length).toBeGreaterThan(0)
    for (const b of blockers) {
      expect(b.resolved).toBe(false)
    }
  })

  it('the Target A relationship states prerequisite evidence, no authorization, stays disabled', () => {
    const rel = buildTargetBTargetARelationship()
    const joined = rel.map((r) => r.statement).join(' ').toLowerCase()
    expect(joined).toContain('prerequisite evidence')
    expect(joined).toContain('does not authorize')
    expect(joined).toContain('remains disabled')
  })

  it('the readiness checklist has ready and blocked items and never claims production-ready', () => {
    const items = buildTargetBReadinessChecklist()
    expect(items.length).toBeGreaterThan(0)
    const statuses = items.map((i) => i.status)
    expect(statuses).toContain('ready')
    expect(statuses).toContain('blocked')
    for (const item of items) {
      expect(item.status === 'ready' || item.status === 'blocked').toBe(true)
      expect(item.evidenceSummary.toLowerCase()).not.toContain('production ready')
      expect(item.evidenceSummary.toLowerCase()).not.toContain('authorized')
    }
  })
})

describe('targetBReadiness view-model — summary text', () => {
  it('is deterministic, states DISABLED / NO-GO / prerequisite evidence, and carries the frozen counts', () => {
    const text = buildTargetBReadinessSummaryText()
    expect(text).toContain('SCAFFOLD_READY')
    expect(text.toLowerCase()).toContain('readiness scaffold')
    expect(text).toContain('DISABLED')
    expect(text).toContain('NO-GO')
    expect(text).toContain('34/34/5/0/1/1')
    expect(text.toLowerCase()).toContain('does not authorize target b')
    expect(buildTargetBReadinessSummaryText()).toBe(text)
  })
})

describe('targetBReadiness view-model — immutability', () => {
  it('the canonical manifest exports are frozen', () => {
    expect(Object.isFrozen(TARGET_B_READINESS_SUMMARY)).toBe(true)
    expect(Object.isFrozen(TARGET_B_ARCHITECTURE_MODULES)).toBe(true)
    expect(Object.isFrozen(TARGET_B_ARCHITECTURE_MODULES[0])).toBe(true)
    expect(Object.isFrozen(TARGET_B_PERMISSION_ENTRIES)).toBe(true)
    expect(Object.isFrozen(TARGET_B_WEBUI_EXECUTION)).toBe(true)
    expect(Object.isFrozen(TARGET_B_APPROVAL_GATE)).toBe(true)
    expect(Object.isFrozen(TARGET_B_READINESS_CHECKLIST)).toBe(true)
    expect(Object.isFrozen(TARGET_B_ENABLEMENT_BLOCKERS)).toBe(true)
  })

  it('mutating a returned summary cannot flip execution / production / rollout', () => {
    const s = buildTargetBReadinessSummary()
    s.executionStatus = 'ENABLED' as unknown as 'DISABLED'
    s.productionRuntime = 'GO' as unknown as 'NO-GO'
    s.productionRollout = 'GO' as unknown as 'NO-GO'
    s.p0Resolved = 24 as unknown as 0
    const fresh = buildTargetBReadinessSummary()
    expect(fresh.executionStatus).toBe('DISABLED')
    expect(fresh.productionRuntime).toBe('NO-GO')
    expect(fresh.productionRollout).toBe('NO-GO')
    expect(fresh.p0Resolved).toBe(0)
  })

  it('mutating a returned architecture module cannot enable a capability', () => {
    const before = TARGET_B_ARCHITECTURE_MODULES[0]!.enabled
    const rows = buildTargetBArchitectureModules()
    rows[0]!.enabled = true
    rows[0]!.executionCapable = true
    rows.length = 0
    expect(TARGET_B_ARCHITECTURE_MODULES[0]!.enabled).toBe(before)
    const fresh = buildTargetBArchitectureModules()
    expect(fresh.length).toBe(TARGET_B_ARCHITECTURE_MODULES.length)
    expect(fresh[0]!.enabled).toBe(false)
    expect(fresh[0]!.executionCapable).toBe(false)
  })

  it('mutating a returned permission model cannot grant a permission', () => {
    const model = buildTargetBPermissionModel()
    model.defaultDisposition = 'GRANTED' as unknown as 'DENIED_BY_DEFAULT'
    model.anyGranted = true as unknown as false
    model.entries[0]!.currentStatus = 'GRANTED' as unknown as 'DENIED_BY_DEFAULT'
    const fresh = buildTargetBPermissionModel()
    expect(fresh.defaultDisposition).toBe('DENIED_BY_DEFAULT')
    expect(fresh.anyGranted).toBe(false)
    expect(fresh.entries[0]!.currentStatus).toBe('DENIED_BY_DEFAULT')
  })

  it('mutating a returned execution preview cannot enable canSubmit or a step', () => {
    const e = buildTargetBWebUIExecution()
    e.canSubmit = true as unknown as false
    e.executeButtonEnabled = true as unknown as false
    e.runtimeRouteAvailable = true as unknown as false
    e.flow[0]!.enabled = true as unknown as false
    const fresh = buildTargetBWebUIExecution()
    expect(fresh.canSubmit).toBe(false)
    expect(fresh.executeButtonEnabled).toBe(false)
    expect(fresh.runtimeRouteAvailable).toBe(false)
    expect(fresh.flow[0]!.enabled).toBe(false)
  })

  it('mutating a returned approval gate cannot provision a trust token or accept fake approval', () => {
    const g = buildTargetBApprovalGate()
    g.trustTokenProvisioned = true as unknown as false
    g.fakeApprovalAccepted = true as unknown as false
    g.productionAuthorization = 'GO' as unknown as 'NO-GO'
    const fresh = buildTargetBApprovalGate()
    expect(fresh.trustTokenProvisioned).toBe(false)
    expect(fresh.fakeApprovalAccepted).toBe(false)
    expect(fresh.productionAuthorization).toBe('NO-GO')
  })

  it('mutating a returned registry protocol cannot enable network / fetch / marketplace', () => {
    const r = buildTargetBRegistryProtocol()
    r.networkEnabled = true as unknown as false
    r.fetchEnabled = true as unknown as false
    r.marketplaceEnabled = true as unknown as false
    r.allowUnsigned = true as unknown as false
    const fresh = buildTargetBRegistryProtocol()
    expect(fresh.networkEnabled).toBe(false)
    expect(fresh.fetchEnabled).toBe(false)
    expect(fresh.marketplaceEnabled).toBe(false)
    expect(fresh.allowUnsigned).toBe(false)
  })
})

describe('targetBReadiness view-model — defense-in-depth redactor (corpus)', () => {
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
    expect(redactTargetBValue(value)).toBe('[REDACTED]')
  })

  it('leaves safe Target B readiness text intact', () => {
    expect(redactTargetBValue('Target B: READINESS SCAFFOLD')).toContain('SCAFFOLD')
    expect(redactTargetBValue('Execution disabled')).toContain('disabled')
    expect(redactTargetBValue('https://registry.example.invalid')).toContain('registry.example.invalid')
  })

  it('the static manifest carries no secret-shaped / fake-authorization text', () => {
    const texts: string[] = []
    texts.push(TARGET_B_READINESS_SUMMARY.targetName)
    for (const r of TARGET_B_READINESS_SUMMARY.requiredBeforeEnable) texts.push(r)
    for (const m of TARGET_B_ARCHITECTURE_MODULES) texts.push(m.futureImplementationNotes, m.requiredGate)
    for (const b of TARGET_B_ENABLEMENT_BLOCKERS) texts.push(b.detail)
    for (const c of CORPUS) {
      for (const text of texts) {
        expect(text).not.toContain(c)
      }
    }
  })
})
