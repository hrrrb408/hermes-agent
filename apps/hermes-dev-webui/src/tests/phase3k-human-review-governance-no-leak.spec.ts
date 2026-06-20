/**
 * Phase 3K — Human Review Governance no-leak / no-approval HARDENING tests.
 *
 * Asserts the read-only surface:
 *   - exposes NO approval / authorization / execution / loading controls (no
 *     Approve / Reject / Authorize / Sign off / Resolve / Override / Enable /
 *     Run / Execute / Batch / Upload / Load / Fetch) — only harmless Filter +
 *     Inspect + Copy-ID UI selects;
 *   - exposes NO input that could carry an API key, secret, file, or arbitrary
 *     JSON for execution (no <input>, no <textarea>, no file picker, no select);
 *   - makes NO network call and NO write/exec API call (no fetch, no XHR);
 *   - leaks no secret, callable repr, shell command, SQL statement, production
 *     path, local plugin path, dynamic import path, external URL, download URL,
 *     install command, Authorization header, Bearer token, trust token, or raw
 *     fake-approval marker into the rendered DOM.
 *
 * Tests distinguish interactive BUTTON controls from explanatory TEXT: forbidden
 * action words may appear in descriptive text (e.g. "cannot approve") but never
 * as a button's visible text or accessible name.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import HumanReviewGovernanceSection from '@/components/devconsole/HumanReviewGovernanceSection.vue'
import { HUMAN_REVIEW_GATES } from '@/constants/humanReviewGovernanceManifest'

/**
 * Forbidden action verbs that must never appear as a BUTTON control (visible text
 * or accessible name). They MAY appear as descriptive explanatory text.
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

describe('Human Review Governance no-leak / no-approval HARDENING (Phase 3K)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders no <input>, <textarea>, <select>, or file-picker element', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.findAll('textarea').length).toBe(0)
    expect(wrapper.findAll('select').length).toBe(0)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })

  it('exposes no approval / authorization / execution / loading control on any button', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0) // Filter + Inspect + Copy-ID are present
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

  it('every button visible-text is one of the harmless allowed controls', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const allowedTexts = new Set([
      'All gates',
      'Partial evidence',
      'Pending human review',
      'Blocked by human review',
      'Governance-only / no evidence',
      'Inspect',
      'Copy ID',
      'Copied',
      'Unavailable',
    ])
    const distinct = new Set(wrapper.findAll('button').map((b) => b.text().trim()))
    for (const text of distinct) {
      expect(allowedTexts, `unexpected button text "${text}"`).toContain(text)
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
      const wrapper = mount(HumanReviewGovernanceSection)
      // Apply every filter.
      for (const key of [
        'all',
        'partial_evidence',
        'pending_human_review',
        'blocked_by_human_review',
        'governance_only',
      ]) {
        await wrapper.find(`[data-testid="human-review-filter-${key}"]`).trigger('click')
      }
      // Reset to All so every gate row is present for inspection.
      await wrapper.find('[data-testid="human-review-filter-all"]').trigger('click')
      // Inspect every gate.
      for (const g of HUMAN_REVIEW_GATES) {
        await wrapper.find(`[data-testid="human-review-inspect-${g.gateId}"]`).trigger('click')
      }
      // Copy the selected gate id.
      await wrapper.find('[data-testid="human-review-copy-gate-id"]').trigger('click')
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(xhrSpy).not.toHaveBeenCalled()
    } finally {
      fetchSpy.mockRestore()
      vi.unstubAllGlobals()
    }
  })

  it('the full section HTML contains no forbidden secret/path/fake-approval token', () => {
    const html = mount(HumanReviewGovernanceSection).html()
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('selecting every gate and rendering its detail leaks nothing', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    for (const g of HUMAN_REVIEW_GATES) {
      await wrapper.find(`[data-testid="human-review-inspect-${g.gateId}"]`).trigger('click')
      const html = wrapper.html()
      for (const token of FORBIDDEN_DOM_TOKENS) {
        if (html.includes(token)) {
          throw new Error(`forbidden token ${token} leaked for ${g.gateId}`)
        }
      }
    }
    expect(HUMAN_REVIEW_GATES.length).toBe(24)
  })

  it('every gate renders resolved=false / approved=false / production NO-GO', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    for (const g of HUMAN_REVIEW_GATES) {
      await wrapper.find(`[data-testid="human-review-inspect-${g.gateId}"]`).trigger('click')
      const html = wrapper.find('[data-testid="human-review-detail-gate"]').html()
      expect(html).toContain('resolved-false')
      expect(html).toContain('approved-false')
      expect(html).toContain('productionAuthorization-NO-GO')
    }
  })

  it('Copy writes the gate id to the clipboard and flips to a Copied state', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(HumanReviewGovernanceSection)
    await wrapper.find('[data-testid="human-review-copy-gate-id"]').trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalledWith('P0-15')
    const btn = wrapper.find('[data-testid="human-review-copy-gate-id"]')
    expect(btn.attributes('data-copy-state')).toBe('copied')
    expect(btn.text()).toContain('Copied')
  })

  it('Copy shows a harmless Unavailable state when the clipboard API is absent', async () => {
    vi.stubGlobal('navigator', {}) // no clipboard
    const wrapper = mount(HumanReviewGovernanceSection)
    await wrapper.find('[data-testid="human-review-copy-gate-id"]').trigger('click')
    await Promise.resolve()
    const btn = wrapper.find('[data-testid="human-review-copy-gate-id"]')
    expect(btn.attributes('data-copy-state')).toBe('unavailable')
    expect(btn.text()).toContain('Unavailable')
  })

  it('Copy never calls fetch even when the clipboard rejects', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const writeText = vi.fn().mockRejectedValue(new Error('clipboard denied'))
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(HumanReviewGovernanceSection)
      await wrapper.find('[data-testid="human-review-copy-gate-id"]').trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(writeText).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(wrapper.find('[data-testid="human-review-copy-gate-id"]').attributes('data-copy-state')).toBe(
        'unavailable',
      )
    } finally {
      vi.unstubAllGlobals()
    }
  })
})
