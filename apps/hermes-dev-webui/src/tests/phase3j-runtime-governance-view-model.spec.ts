/**
 * Phase 3J — Runtime Governance view-model tests.
 *
 * Asserts the pure view-model projections are deterministic, carry the frozen
 * descriptor set, the frozen P0 counts, the all-false side-effect surface, the
 * all-NO-GO authorization verdicts, and that the defense-in-depth redactor
 * masks every secret-shaped / production-path-shaped substring (redaction
 * corpus L).
 */
import { describe, it, expect } from 'vitest'

import {
  buildRuntimeGovernanceViewModel,
  buildSummaryCards,
  buildDescriptorRows,
  buildDescriptorBindingDetail,
  buildStatusBadges,
  buildBoundaryItems,
  buildDeniedPreview,
  findDescriptorRow,
  redactRuntimeValue,
  sanitizeRuntimeGovernanceDisplayText,
  allSideEffectsFalse,
  allVerdictsNoGo,
  DEFAULT_DESCRIPTOR_ID,
} from '@/lib/runtimeGovernanceViewModel'
import {
  RUNTIME_REVIEWED_DESCRIPTORS,
  RUNTIME_SIDE_EFFECT_FLAGS,
  RUNTIME_AUTHORIZATION_VERDICTS,
  RUNTIME_FLAGS_FROZEN,
} from '@/constants/runtimeGovernanceManifest'

const EXPECTED_IDS = [
  'descriptor.fixture.echo_uppercase',
  'descriptor.fixture.normalize_text',
  'descriptor.fixture.validate_required_keys',
  'descriptor.fixture.count_items',
  'descriptor.fixture.redact_payload',
  'descriptor.fixture.fault',
]

describe('runtimeGovernanceViewModel (Phase 3J)', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildRuntimeGovernanceViewModel()
    const b = buildRuntimeGovernanceViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('projects exactly six reviewed descriptors with the expected ids', () => {
    const vm = buildRuntimeGovernanceViewModel()
    expect(vm.descriptorCount).toBe(6)
    expect(vm.descriptors.map((d) => d.descriptorId)).toEqual(EXPECTED_IDS)
  })

  it('every descriptor is dev-only / fixture-only / reviewed and not executable/remote/marketplace/production', () => {
    const rows = buildDescriptorRows()
    for (const r of rows) {
      expect(r.devOnly).toBe(true)
      expect(r.fixtureOnly).toBe(true)
      expect(r.reviewedFixture).toBe(true)
      expect(r.executable).toBe(false)
      expect(r.remote).toBe(false)
      expect(r.marketplace).toBe(false)
      expect(r.production).toBe(false)
      expect(r.routeChange).toBe(false)
      expect(r.bindingAllowed).toBe(true)
      expect(r.source).toBe('static_descriptor_registry')
    }
  })

  it('projects the frozen P0 evidence (24 / 0 / 19 / 5)', () => {
    const vm = buildRuntimeGovernanceViewModel()
    const p0 = vm.p0Evidence
    expect(p0.totalGates).toBe(24)
    expect(p0.resolvedCount).toBe(0)
    expect(p0.partialEvidenceCount).toBe(19)
    expect(p0.blockedByHumanReviewCount).toBe(5)
    expect(p0.candidateForReviewCount).toBe(0)
    expect(p0.governanceOnlyCount).toBe(0)
    expect(p0.noEvidenceCount).toBe(0)
    expect(p0.unresolvedCount).toBe(24)
    expect(p0.implementationAuthorization).toBe('NO-GO')
    expect(p0.phase3iAuthorized).toBe(false)
    expect(p0.realRuntime).toBe('NO-GO')
    expect(p0.newRoute).toBe('NO-GO')
    expect(p0.productionRollout).toBe('NO-GO')
  })

  it('projects the all-false side-effect surface (12 flags)', () => {
    const vm = buildRuntimeGovernanceViewModel()
    expect(vm.sideEffectFlags.length).toBe(12)
    expect(allSideEffectsFalse(vm.sideEffectFlags)).toBe(true)
  })

  it('side effects cannot be overridden — the projection ignores any caller mutation', () => {
    // A caller mutating a returned-shallow-copy flag must not change the invariant.
    const vm = buildRuntimeGovernanceViewModel()
    const tampered = [...vm.sideEffectFlags, { key: 'x', label: 'x', value: true }]
    // The frozen source is still all false.
    expect(allSideEffectsFalse(vm.sideEffectFlags)).toBe(true)
    // And the tampered local copy is correctly detected as NOT all-false.
    expect(allSideEffectsFalse(tampered)).toBe(false)
  })

  it('every authorization verdict is NO-GO / NOT_AUTHORIZED / false', () => {
    const vm = buildRuntimeGovernanceViewModel()
    expect(allVerdictsNoGo(vm.authorizationVerdicts)).toBe(true)
    const keys = vm.authorizationVerdicts.map((v) => v.key)
    expect(keys).toContain('implementationGate')
    expect(keys).toContain('phase3iProductionGate')
    expect(keys).toContain('arbitraryPluginLoading')
    expect(keys).toContain('remoteRegistry')
    expect(keys).toContain('marketplace')
  })

  it('projects seven fixture allowlist pairs', () => {
    const vm = buildRuntimeGovernanceViewModel()
    expect(vm.fixtureAllowlistCount).toBe(7)
    expect(vm.fixtureAllowlist.map((f) => `${f.pluginId}/${f.operation}`)).toContain(
      'fixture.echo/echo_uppercase',
    )
  })

  it('default descriptor binding resolves to echo_uppercase', () => {
    expect(DEFAULT_DESCRIPTOR_ID).toBe('descriptor.fixture.echo_uppercase')
    const binding = buildDescriptorBindingDetail(DEFAULT_DESCRIPTOR_ID)
    expect(binding).toBeDefined()
    expect(binding!.pluginId).toBe('fixture.echo')
    expect(binding!.operation).toBe('echo_uppercase')
    expect(binding!.bindingAllowed).toBe(true)
    expect(binding!.denialReasons).toEqual([])
    expect(binding!.source).toBe('static_descriptor_registry')
  })

  it('an unknown descriptor id resolves to undefined (no binding, no execution)', () => {
    expect(buildDescriptorBindingDetail('descriptor.fixture.does_not_exist')).toBeUndefined()
    expect(buildDescriptorBindingDetail(null)).toBeUndefined()
    expect(findDescriptorRow('descriptor.fixture.does_not_exist')).toBeUndefined()
  })

  it('summary cards are deterministic and include the frozen counts', () => {
    const cards = buildSummaryCards()
    expect(cards.length).toBeGreaterThanOrEqual(9)
    const labels = cards.map((c) => c.label)
    expect(labels).toContain('Reviewed descriptors')
    expect(labels).toContain('P0 resolved')
    expect(labels).toContain('Side effects')
    expect(labels).toContain('Backend routes changed')
    const resolved = cards.find((c) => c.label === 'P0 resolved')!
    expect(resolved.value).toBe(0)
    const routes = cards.find((c) => c.label === 'Backend routes changed')!
    expect(routes.value).toBe('no')
    const sideEffects = cards.find((c) => c.label === 'Side effects')!
    expect(String(sideEffects.value)).toContain('false')
  })

  it('route governance baseline and backend-routes-unchanged flag', () => {
    const vm = buildRuntimeGovernanceViewModel()
    expect(vm.routeGovernanceBaseline).toBe('34/34/5/0/1/1')
    expect(vm.backendRoutesChanged).toBe(false)
    expect(vm.schemaVersion).toBe('phase-3i-runtime-governance-v1')
  })

  describe('defense-in-depth redactor (corpus L)', () => {
    const CORPUS = [
      'sk-FAKE-SECRET-DO-NOT-LEAK-12345678',
      'Authorization: Bearer fake-token',
      '~/.hermes',
      '~/.hermes/production/state.db',
      '/fake/production/state.db',
      'implementation_authorization=GO',
      'ghp_fakegithubtoken',
      'xox-fake-slack-token',
      '-----BEGIN PRIVATE KEY-----',
      'BEGIN PRIVATE KEY fake',
      'OPENAI_API_KEY=fake',
      'db_password=fake',
      'accessToken=fake',
      'phase_3i_authorized=true',
      'production_approved=true',
      'route_exception_approved=true',
    ]

    it.each(CORPUS)('masks secret-shaped value %s', (value) => {
      expect(redactRuntimeValue(value)).toBe('[REDACTED]')
    })

    it('sanitizeRuntimeGovernanceDisplayText is a stable alias of redactRuntimeValue', () => {
      for (const c of CORPUS) {
        expect(sanitizeRuntimeGovernanceDisplayText(c)).toBe('[REDACTED]')
      }
    })

    it('leaves safe descriptor text intact', () => {
      expect(redactRuntimeValue('Reviewed fixture descriptor binding fixture.echo / echo_uppercase.')).toContain(
        'fixture.echo',
      )
    })

    it('every projected descriptor description is free of raw secret stems', () => {
      const rows = buildDescriptorRows()
      for (const r of rows) {
        for (const c of CORPUS) {
          expect(r.description).not.toContain(c)
        }
      }
    })

    it('the static manifest carries no secret-shaped descriptor text', () => {
      for (const d of RUNTIME_REVIEWED_DESCRIPTORS) {
        for (const c of CORPUS) {
          expect(d.description).not.toContain(c)
          expect(d.displayName).not.toContain(c)
        }
      }
    })
  })

  describe('new view-model projections (status badges / boundary / denied preview)', () => {
    it('buildStatusBadges projects the five frozen header badges', () => {
      const badges = buildStatusBadges()
      expect(badges.map((b) => b.label)).toEqual([
        'DEV-ONLY',
        'READ-ONLY',
        'FIXTURE-ONLY',
        'NO PRODUCTION',
        'NO WEBUI EXECUTION',
      ])
    })

    it('buildBoundaryItems projects the frozen boundary rows with safe kinds', () => {
      const items = buildBoundaryItems()
      expect(items.length).toBeGreaterThan(0)
      for (const it of items) {
        expect(it.kind === 'lock' || it.kind === 'ban').toBe(true)
        expect(it.label.trim().length).toBeGreaterThan(0)
      }
      const labels = items.map((i) => i.label)
      expect(labels.some((l) => /arbitrary plugin loading/i.test(l))).toBe(true)
      expect(labels.some((l) => /local plugin directory loading/i.test(l))).toBe(true)
      expect(labels.some((l) => /remote registry/i.test(l))).toBe(true)
      expect(labels.some((l) => /marketplace/i.test(l))).toBe(true)
      expect(labels.some((l) => /production rollout/i.test(l))).toBe(true)
    })

    it('buildDeniedPreview projects the frozen denial reasons', () => {
      const preview = buildDeniedPreview()
      expect(preview.denied).toBe(true)
      expect(preview.denialReasons).toContain('descriptor_not_in_static_registry')
      expect(preview.denialReasons).toContain('descriptor_registry_lookup')
    })
  })

  describe('view-model immutability (external mutation cannot reach the canonical manifest)', () => {
    it('the canonical manifest exports are frozen', () => {
      expect(Object.isFrozen(RUNTIME_REVIEWED_DESCRIPTORS)).toBe(true)
      expect(Object.isFrozen(RUNTIME_REVIEWED_DESCRIPTORS[0])).toBe(true)
      expect(Object.isFrozen(RUNTIME_SIDE_EFFECT_FLAGS)).toBe(true)
      expect(Object.isFrozen(RUNTIME_AUTHORIZATION_VERDICTS)).toBe(true)
      expect(Object.isFrozen(RUNTIME_FLAGS_FROZEN)).toBe(true)
    })

    it('mutating a returned descriptor row does not mutate the canonical manifest', () => {
      const before = RUNTIME_REVIEWED_DESCRIPTORS[0]!.description
      const rows = buildDescriptorRows()
      rows[0]!.description = 'tampered'
      expect(rows[0]!.description).toBe('tampered') // local copy is independently mutable
      expect(RUNTIME_REVIEWED_DESCRIPTORS[0]!.description).toBe(before) // canonical untouched
    })

    it('mutating a returned binding (runtimeFlags) does not mutate the canonical flags', () => {
      const binding = buildDescriptorBindingDetail(DEFAULT_DESCRIPTOR_ID)!
      binding.runtimeFlags.production_access = true
      expect(binding.runtimeFlags.production_access).toBe(true) // local copy
      // Canonical frozen flags are untouched.
      expect(() => {
        // Direct canonical mutation throws in strict mode (frozen) — wrap to prove it.
        ;(RUNTIME_FLAGS_FROZEN as Record<string, boolean>).production_access = false
      }).toThrow()
    })

    it('mutating a returned side-effect array/flag does not flip the canonical invariant', () => {
      const vm = buildRuntimeGovernanceViewModel()
      vm.sideEffectFlags[0]!.value = true
      vm.sideEffectFlags.push({ key: 'x', label: 'x', value: true })
      // The returned (tampered) collection is no longer all-false…
      expect(allSideEffectsFalse(vm.sideEffectFlags)).toBe(false)
      // …but a fresh build is still all-false — the canonical source never changed.
      expect(allSideEffectsFalse(buildRuntimeGovernanceViewModel().sideEffectFlags)).toBe(true)
    })

    it('mutating a returned authorization verdict does not flip the canonical NO-GO', () => {
      const vm = buildRuntimeGovernanceViewModel()
      vm.authorizationVerdicts[0]!.verdict = 'GO'
      // Fresh build still every-NO-GO.
      expect(allVerdictsNoGo(buildRuntimeGovernanceViewModel().authorizationVerdicts)).toBe(true)
    })
  })
})
