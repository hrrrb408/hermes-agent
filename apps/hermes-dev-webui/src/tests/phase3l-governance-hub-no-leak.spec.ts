/**
 * Phase 3L — Governance Hub no-leak / no-approval HARDENING tests.
 *
 * Asserts the read-only surface:
 *   - exposes NO approval / authorization / execution / loading controls (no
 *     Approve / Reject / Authorize / Sign off / Resolve / Override / Enable /
 *     Run / Execute / Batch / Upload / Load / Fetch) — only harmless Filter +
 *     Inspect + View-section + Copy UI selects;
 *   - exposes NO input that could carry an API key, secret, file, or arbitrary
 *     JSON for execution (no <input>, no <textarea>, no file picker, no select);
 *   - makes NO network call and NO write/exec API call (no fetch, no XHR);
 *   - leaks no secret, callable repr, shell command, SQL statement, production
 *     path, local plugin path, dynamic import path, external URL, download URL,
 *     install command, Authorization header, Bearer token, trust token, or raw
 *     fake-approval marker into the rendered DOM.
 *
 * Tests distinguish interactive BUTTON controls from explanatory TEXT: forbidden
 * action words may appear in descriptive text (e.g. the deferred list, the
 * forbidden-actions panel) but never as a button's visible text or accessible
 * name.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'
import { GOVERNANCE_HUB_MODULES } from '@/constants/governanceHubManifest'

/**
 * Forbidden action verbs that must never appear as a BUTTON control (visible text
 * or accessible name). They MAY appear as descriptive explanatory text (the
 * deferred list / forbidden-actions panel).
 */
const FORBIDDEN_BUTTON_WORDS = [
  'approve',
  'reject',
  'authorize',
  'signoff',
  'sign off',
  'resolve',
  'override',
  'rollout',
  'enable',
  'run',
  'execute',
  'exec',
  'batch',
  'upload',
  'load',
  'fetch',
  'install',
  'deploy',
  'start',
  'stop',
  'restart',
]

/** Secret / production-path / fake-approval tokens that must never render. */
const FORBIDDEN_DOM_TOKENS = [
  'sk-',
  'Bearer ',
  'Authorization:',
  'ghp_',
  'xox',
  'BEGIN PRIVATE KEY',
  'OPENAI_API_KEY',
  'db_password',
  'accessToken',
  '~/.hermes',
  '.hermes/',
  'state.db',
  'implementation_authorization=GO',
  'implementation authorization = go',
  'phase_3i_authorized=true',
  'production_approved=true',
  'route_exception_approved=true',
  'approved_by_ai=true',
  'trust_token=fake',
  'pythonImportPath',
  'shellCommand',
  'installCommand',
  'externalUrl',
  'downloadUrl',
  'pluginPackage',
  'dynamicModule',
  'evalCode',
  'execCode',
  'sqlStatement',
  'productionPath',
  'localPath',
  'remoteUrl',
]

describe('Governance Hub no-leak / no-approval HARDENING (Phase 3L)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders no <input>, <textarea>, <select>, or file-picker element', () => {
    const wrapper = mount(GovernanceHubSection)
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.findAll('textarea').length).toBe(0)
    expect(wrapper.findAll('select').length).toBe(0)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })

  it('exposes no approval / authorization / execution / loading control on any button', () => {
    const wrapper = mount(GovernanceHubSection)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0) // Filter + Inspect + View + Copy are present
    for (const btn of buttons) {
      const label = (btn.text() + ' ' + (btn.attributes('aria-label') ?? '')).toLowerCase()
      const tokenized = label.replace(/[^a-z0-9]+/g, ' ')
      for (const word of FORBIDDEN_BUTTON_WORDS) {
        expect(tokenized, `button "${btn.text()}" must not offer ${word}`).not.toMatch(
          new RegExp(`\\b${word.replace(/ /g, '\\s+')}\\b`),
        )
      }
    }
  })

  it('every button is a harmless read-only control (filter / inspect / view / copy)', () => {
    const wrapper = mount(GovernanceHubSection)
    const buttons = wrapper.findAll('button')
    // Every button must mention at least one harmless affordance in its text or
    // aria-label, and none offers a forbidden action.
    const ALLOWED = ['all modules', 'complete', 'implemented', 'read-only', 'inspect', 'selected', 'view', 'copy', 'copied', 'unavailable', 'summary',
      // Phase 4A — the Governance Hub now also renders the read-only Target B
      // Readiness region. These are that region's harmless read-only control
      // words (its client-side module filter + inspect + copy + cross-link
      // buttons). They are descriptors only — none is an approval /
      // authorization / execution / loading verb, so the forbidden-control guard
      // still rejects every dangerous action.
      'target b', 'readiness', 'designed', 'scaffolded', 'architecture', 'permission', 'registry', 'preview', 'disabled', 'runtime governance', 'human review',
      // Phase 4B — the Governance Hub now also renders the read-only Target B
      // Implementation region. These are that region's harmless read-only control
      // words (its client-side layer filter + inspect + copy buttons). They are
      // descriptors only — none is an approval / authorization / execution /
      // loading verb, so the forbidden-control guard still rejects every
      // dangerous action.
      'implementation', 'layers', 'signature', 'sandbox', 'approval', 'rollback', 'audit',
      // Target B Authorization region (Phase 4C) filter / inspect / copy / cross-link words.
      'authorization', 'authorized', 'design', 'package', 'gate']
    for (const btn of buttons) {
      const label = (btn.text() + ' ' + (btn.attributes('aria-label') ?? '')).toLowerCase()
      expect(ALLOWED.some((a) => label.includes(a)), `unexpected button "${btn.text()}"`).toBe(true)
    }
  })

  it('makes no network call and no write/exec API call on render + interaction', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called by the read-only surface')
    })
    const xhrSpy = vi.fn()
    vi.stubGlobal('XMLHttpRequest', function MockXHR() {
      return {
        open: xhrSpy,
        send: xhrSpy,
        setRequestHeader: xhrSpy,
        addEventListener: () => {},
      }
    })
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(GovernanceHubSection)
      // Apply every module filter.
      for (const key of ['all', 'COMPLETE', 'IMPLEMENTED', 'READ_ONLY']) {
        await wrapper.find(`[data-testid="governance-hub-module-filter-${key}"]`).trigger('click')
      }
      // Back to All so every module is present.
      await wrapper.find('[data-testid="governance-hub-module-filter-all"]').trigger('click')
      // Inspect every module.
      for (const m of GOVERNANCE_HUB_MODULES) {
        await wrapper.find(`[data-testid="governance-hub-module-inspect-${m.key}"]`).trigger('click')
      }
      // Cross-link navigation.
      await wrapper.find('[data-testid="governance-hub-cross-link-runtimeGovernance"]').trigger('click')
      await wrapper.find('[data-testid="governance-hub-cross-link-humanReview"]').trigger('click')
      // Module-board View link.
      await wrapper.find('[data-testid="governance-hub-module-link-runtimeGovernanceWebui"]').trigger('click')
      // Copy summary.
      await wrapper.find('[data-testid="governance-hub-copy-summary"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(xhrSpy).not.toHaveBeenCalled()
    } finally {
      fetchSpy.mockRestore()
      vi.unstubAllGlobals()
    }
  })

  it('the full section HTML contains no forbidden secret/path/fake-approval token', () => {
    const html = mount(GovernanceHubSection).html()
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('copying the summary never calls fetch even when the clipboard resolves', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(GovernanceHubSection)
      await wrapper.find('[data-testid="governance-hub-copy-summary"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(writeText).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('copying the summary never calls fetch even when the clipboard rejects', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const writeText = vi.fn().mockRejectedValue(new Error('clipboard denied'))
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(GovernanceHubSection)
      await wrapper.find('[data-testid="governance-hub-copy-summary"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(writeText).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
      const btn = wrapper.find('[data-testid="governance-hub-copy-summary"]')
      expect(btn.attributes('data-copy-state')).toBe('unavailable')
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('the copied text itself contains no secret / forbidden path / fake-approval marker', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-copy-summary"]').trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    const text = String(writeText.mock.calls[0]![0])
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(text, `copied text must not contain ${token}`).not.toContain(token)
    }
  })

  it('deferred list and forbidden-actions panel render as TEXT, never as buttons', () => {
    const wrapper = mount(GovernanceHubSection)
    // The deferred list is a <ul> of <li>, not buttons.
    const deferred = wrapper.find('[data-testid="governance-hub-deferred-list"]')
    expect(deferred.findAll('button').length).toBe(0)
    expect(deferred.findAll('li').length).toBeGreaterThan(0)
    const forbidden = wrapper.find('[data-testid="governance-hub-forbidden-actions-global"]')
    expect(forbidden.findAll('button').length).toBe(0)
    expect(forbidden.findAll('li').length).toBeGreaterThan(0)
  })
})
