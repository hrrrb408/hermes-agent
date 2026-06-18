/**
 * Phase 3C-H1 — Capability Registry mirror consistency (frontend).
 *
 * Bounds the P2 risk that the tracked TS manifest mirror drifts from the
 * backend. Asserts the mirror carries the expected capability IDs, the frozen
 * count (46), the registry version, the forbidden-field set, and that a drift
 * detector fails on a divergent fixture. (The cross-boundary backend↔frontend
 * ID equality is pinned in the backend H1 manifest-consistency test.)
 */
import { describe, it, expect } from 'vitest'

import {
  CAPABILITY_REGISTRY_MANIFEST,
  CAPABILITY_REGISTRY_VERSION,
  CAPABILITY_FORBIDDEN_FIELDS,
} from '@/constants/capabilityRegistryManifest'

const EXPECTED_FORBIDDEN = [
  'pythonImportPath', 'callable', 'shellCommand', 'externalUrl', 'downloadUrl',
  'pluginPackage', 'dynamicModule', 'evalCode', 'execCode', 'sqlStatement',
  'productionPath', 'apiKey', 'Authorization', 'secret',
] as const

function detectMirrorDrift(baseline: readonly string[], candidate: readonly string[]): boolean {
  return baseline.length === candidate.length && baseline.every((id, i) => id === candidate[i])
}

describe('Phase 3C-H1 — Capability Registry mirror (frontend)', () => {
  it('has the frozen capability count of 46', () => {
    expect(CAPABILITY_REGISTRY_MANIFEST.length).toBe(46)
  })

  it('carries the pinned first and last capability IDs', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    expect(ids[0]).toBe('registry.capability_registry_status')
    expect(ids[ids.length - 1]).toBe('capability.forbidden.autonomous_write')
  })

  it('has unique capability IDs', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('exposes the pinned registry version', () => {
    expect(CAPABILITY_REGISTRY_VERSION).toBe('phase3c-static-v1')
  })

  it('every entry is dev-only and not production-allowed', () => {
    for (const cap of CAPABILITY_REGISTRY_MANIFEST) {
      expect(cap.devOnly, cap.capabilityId).toBe(true)
      expect(cap.productionAllowed, cap.capabilityId).toBe(false)
      expect(cap.redactionApplied, cap.capabilityId).toBe(true)
    }
  })

  it('every entry carries only safe (non-forbidden) field names', () => {
    for (const cap of CAPABILITY_REGISTRY_MANIFEST) {
      for (const key of Object.keys(cap)) {
        expect(CAPABILITY_FORBIDDEN_FIELDS, cap.capabilityId).not.toContain(key)
      }
    }
  })

  it('the forbidden-field set is exactly the frozen set', () => {
    expect([...CAPABILITY_FORBIDDEN_FIELDS].sort()).toEqual([...EXPECTED_FORBIDDEN].sort())
  })

  it('includes the expected forbidden capability IDs', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    for (const forbidden of [
      'capability.forbidden.dynamic_plugin_load',
      'capability.forbidden.remote_registry',
      'capability.forbidden.marketplace',
      'capability.forbidden.shell',
      'capability.forbidden.production_operation',
    ]) {
      expect(ids).toContain(forbidden)
    }
  })

  it('no LIVE_PROVIDER_GATED capability is enabled by default', () => {
    for (const cap of CAPABILITY_REGISTRY_MANIFEST) {
      if (cap.permissionClass === 'LIVE_PROVIDER_GATED') {
        expect(cap.status, cap.capabilityId).not.toBe('enabled')
        expect(cap.disabledByDefault, cap.capabilityId).toBe(true)
      }
    }
  })
})

describe('Phase 3C-H1 — mirror drift detector', () => {
  it('passes when the candidate matches the baseline', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    expect(detectMirrorDrift(ids, [...ids])).toBe(true)
  })

  it('fails on a reordered fixture', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    const drifted = [...ids].reverse()
    expect(detectMirrorDrift(ids, drifted)).toBe(false)
  })

  it('fails on a missing fixture', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    expect(detectMirrorDrift(ids, ids.slice(0, -1))).toBe(false)
  })

  it('fails on a renamed fixture', () => {
    const ids = CAPABILITY_REGISTRY_MANIFEST.map((c) => c.capabilityId)
    const drifted = [...ids]
    drifted[3] = 'registry.different_id'
    expect(detectMirrorDrift(ids, drifted)).toBe(false)
  })
})
