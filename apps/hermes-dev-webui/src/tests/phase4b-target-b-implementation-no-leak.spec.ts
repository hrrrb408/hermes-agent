/**
 * Phase 4B — Target B Implementation no-leak / no-approval HARDENING tests.
 *
 * Asserts the read-only Governance Hub surface (now including the Target B
 * Implementation region):
 *   - exposes NO approval / authorization / execution / loading / install /
 *     fetch / registry / marketplace controls (no Approve / Reject / Authorize
 *     / Sign off / Resolve / Override / Enable / Run / Execute / Batch / Upload
 *     / Load / Fetch / Install / Marketplace / API-key / trust-token / signature
 *     upload control) — only harmless Filter + Inspect + View-section + Copy UI
 *     selects;
 *   - exposes NO input that could carry an API key, secret, file, JSON, trust
 *     token, or signature for execution (no <input>, no <textarea>, no file
 *     picker, no <select>);
 *   - renders the execution policy as disabled TEXT only — never as an
 *     interactive execute / run button;
 *   - makes NO network call and NO write/exec API call (no fetch, no XHR)
 *     during render, filter, inspect, copy, and view-section interactions;
 *   - leaks no secret, callable repr, shell command, SQL statement, production
 *     path, production home path, production state path, external URL, download
 *     URL, install command, Authorization header, Bearer token, registry token,
 *     real signature material, or Target-B fake-authorization marker into the
 *     DOM or the copied summary.
 *
 * Tests distinguish interactive BUTTON controls from explanatory TEXT: forbidden
 * action words may appear in descriptive text (the layer board, the permission
 * model, the forbidden-actions list, the execution-policy reasons) but never as
 * a button's visible text or accessible name.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'

/**
 * Forbidden action verbs that must never appear as a BUTTON control (visible text
 * or accessible name). They MAY appear as descriptive explanatory text (the
 * layer board / permission model / execution-policy reasons / forbidden list).
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
  'marketplace',
]

/** Secret / production-path / fake-authorization tokens that must never render. */
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
  'registry_token=fake',
  'plugin_signature=fake-private-key',
  'target_b_authorized=true',
  'production_runtime_go=true',
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

/** Harmless affordances a button MAY mention (visible text or aria-label). */
const ALLOWED_BUTTON_WORDS = [
  // Governance Hub module-board filter buttons (pre-existing regions).
  'all modules',
  'complete',
  'implemented',
  'read-only',
  'selected',
  // Target B Readiness region (Phase 4A) filter / inspect / copy / cross-link.
  'designed',
  'scaffolded',
  'inspect',
  'view',
  'copy',
  'copied',
  'unavailable',
  'summary',
  'readiness',
  'target b',
  'target a',
  'runtime governance',
  'human review',
  'disabled',
  'preview',
  'modules',
  // Target B Implementation region (Phase 4B) filter / inspect / copy / cross-link.
  'layers',
  'implementation',
]

describe('Target B Implementation no-leak / no-approval HARDENING (Phase 4B)', () => {
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

  it('exposes no approval / execution / loading / install / marketplace control on any button', () => {
    const wrapper = mount(GovernanceHubSection)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
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
    for (const btn of buttons) {
      const label = (btn.text() + ' ' + (btn.attributes('aria-label') ?? '')).toLowerCase()
      expect(
        ALLOWED_BUTTON_WORDS.some((a) => label.includes(a)),
        `unexpected button "${btn.text()}"`,
      ).toBe(true)
    }
  })

  it('the execution policy is TEXT-only — there is no execute / run button in the implementation region', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = wrapper.find('[data-testid="governance-hub-target-b-impl-region"]')
    const policy = region.find('[data-testid="governance-hub-target-b-impl-execution-policy"]')
    expect(policy.exists()).toBe(true)
    // The execution policy panel has no buttons.
    expect(policy.findAll('button').length).toBe(0)
    // The permission table and layer board carry no action buttons either.
    expect(
      region.find('[data-testid="governance-hub-target-b-impl-permission-table"]').findAll('button').length,
    ).toBe(0)
    // No form / submit control exists for execution.
    expect(region.find('form').exists()).toBe(false)
  })

  it('makes no network call during render + Target B implementation interactions', async () => {
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
      const region = wrapper.find('[data-testid="governance-hub-target-b-impl-region"]')
      // Apply every implementation layer filter.
      for (const key of ['all', 'DESIGNED', 'SCAFFOLDED_DISABLED']) {
        await region.find(`[data-testid="governance-hub-target-b-impl-layer-filter-${key}"]`).trigger('click')
      }
      // Inspect every layer.
      for (const l of region.findAll('tbody tr[data-layer-key]')) {
        const key = l.attributes('data-layer-key')!
        await region.find(`[data-testid="governance-hub-target-b-impl-layer-inspect-${key}"]`).trigger('click')
      }
      // Copy summary + cross-link view buttons.
      await region.find('[data-testid="governance-hub-target-b-impl-copy-summary"]').trigger('click')
      await region.find('[data-testid="governance-hub-target-b-impl-view-runtime-governance"]').trigger('click')
      await region.find('[data-testid="governance-hub-target-b-impl-view-human-review"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(xhrSpy).not.toHaveBeenCalled()
    } finally {
      fetchSpy.mockRestore()
      vi.unstubAllGlobals()
    }
  })

  it('the full section HTML contains no forbidden secret/path/fake-authorization token', () => {
    const html = mount(GovernanceHubSection).html()
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('copying the implementation summary never calls fetch even when the clipboard resolves', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(GovernanceHubSection)
      await wrapper.find('[data-testid="governance-hub-target-b-impl-copy-summary"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(writeText).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('copying the implementation summary never calls fetch even when the clipboard rejects', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const writeText = vi.fn().mockRejectedValue(new Error('clipboard denied'))
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(GovernanceHubSection)
      await wrapper.find('[data-testid="governance-hub-target-b-impl-copy-summary"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(writeText).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
      const btn = wrapper.find('[data-testid="governance-hub-target-b-impl-copy-summary"]')
      expect(btn.attributes('data-copy-state')).toBe('unavailable')
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('the copied implementation summary contains no secret / forbidden path / fake-authorization marker', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-target-b-impl-copy-summary"]').trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    const text = String(writeText.mock.calls[0]![0])
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(text, `copied text must not contain ${token}`).not.toContain(token)
    }
  })

  it('the layer board / permission matrix / execution policy render as TEXT, never as approval/execute buttons', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = wrapper.find('[data-testid="governance-hub-target-b-impl-region"]')
    expect(region.find('[data-testid="governance-hub-target-b-impl-permission-table"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-execution-policy"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-signature"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-registry"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-sandbox"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-approval"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-audit-rollback"]').findAll('button').length).toBe(0)
    expect(region.find('[data-testid="governance-hub-target-b-impl-forbidden-actions"]').findAll('button').length).toBe(0)
  })
})
