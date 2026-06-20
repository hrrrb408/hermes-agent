/**
 * Phase 3J — Runtime Governance no-leak / no-execution HARDENING tests.
 *
 * Asserts the read-only surface:
 *   - exposes NO execution controls (Run / Execute / Batch / Approve / Authorize
 *     / Enable / Load / Upload / Fetch / Install) — only harmless Inspect +
 *     denied-preview UI selects;
 *   - exposes NO input that could carry an API key, secret, file, or arbitrary
 *     JSON for execution (no <input>, no <textarea>, no file picker);
 *   - makes NO network call and NO write/exec API call (no fetch, no XHR);
 *   - leaks no secret, callable repr, shell command, SQL statement, production
 *     path, local plugin path, dynamic import path, external URL, download URL,
 *     install command, Authorization header, Bearer token, or raw token into the
 *     rendered DOM — including when every descriptor is selected.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import RuntimeGovernanceSection from '@/components/devconsole/RuntimeGovernanceSection.vue'
import { RUNTIME_REVIEWED_DESCRIPTORS } from '@/constants/runtimeGovernanceManifest'

/** Forbidden action words that must never appear as a button control. */
const FORBIDDEN_BUTTON_WORDS = [
  'run',
  'execute',
  'exec',
  'batch',
  'approve',
  'authorize',
  'enable',
  'load',
  'upload',
  'fetch',
  'install',
  'deploy',
  'start',
  'stop',
  'restart',
  'rollout',
]

/** Secret / production-path / execution-surface tokens that must never render. */
const FORBIDDEN_DOM_TOKENS = [
  'sk-',
  'Bearer ',
  'Authorization:',
  'ghp_',
  'xox',
  'BEGIN PRIVATE KEY',
  'OPENAI_API_KEY',
  '~/.hermes',
  '.hermes/',
  'state.db',
  'implementation_authorization=go',
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
  'callable',
  'localPath',
  'remoteUrl',
  'accessToken',
]

describe('RuntimeGovernance no-leak / no-execution HARDENING (Phase 3J)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders no <input>, <textarea>, or file-picker element', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.findAll('textarea').length).toBe(0)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })

  it('exposes no execution / approval / loading control buttons', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0) // Inspect + denied-preview are present
    for (const btn of buttons) {
      const label = (btn.text() + ' ' + (btn.attributes('aria-label') ?? '')).toLowerCase().trim()
      for (const word of FORBIDDEN_BUTTON_WORDS) {
        // Match as a whole token so "Inspect"/"Preview" are not false positives.
        const tokenized = label.replace(/[^a-z0-9]+/g, ' ')
        expect(tokenized, `button "${btn.text()}" must not offer ${word}`).not.toMatch(
          new RegExp(`\\b${word}\\b`),
        )
      }
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
      const wrapper = mount(RuntimeGovernanceSection)
      // Interact with every harmless control.
      for (const d of RUNTIME_REVIEWED_DESCRIPTORS) {
        await wrapper.find(`[data-testid="runtime-inspect-${d.descriptorId}"]`).trigger('click')
      }
      await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
      await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
      // Copy is a clipboard-only affordance — it must not become a network call.
      const firstCopy = wrapper.find('[data-testid="runtime-cli-list"] li').find('button')
      await firstCopy.trigger('click')
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(xhrSpy).not.toHaveBeenCalled()
    } finally {
      fetchSpy.mockRestore()
      vi.unstubAllGlobals()
    }
  })

  it('the full section HTML contains no forbidden secret/path/execution token', () => {
    const html = mount(RuntimeGovernanceSection).html()
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('selecting every descriptor and rendering its binding leaks nothing', async () => {
    const wrapper = mount(RuntimeGovernanceSection)
    for (const d of RUNTIME_REVIEWED_DESCRIPTORS) {
      await wrapper.find(`[data-testid="runtime-inspect-${d.descriptorId}"]`).trigger('click')
      const html = wrapper.html()
      for (const token of FORBIDDEN_DOM_TOKENS) {
        if (html.includes(token)) {
          throw new Error(`forbidden token ${token} leaked for ${d.descriptorId}`)
        }
      }
    }
    expect(RUNTIME_REVIEWED_DESCRIPTORS.length).toBe(6)
  })

  it('the denied-state preview leaks no secret or production path', async () => {
    const wrapper = mount(RuntimeGovernanceSection)
    await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
    const html = wrapper.html()
    for (const token of FORBIDDEN_DOM_TOKENS) {
      expect(html, `forbidden token ${token} in denied state`).not.toContain(token)
    }
  })

  it('P0 resolved count stays 0 and Implementation Authorization stays NO-GO in the DOM', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.find('[data-testid="runtime-p0-resolved"]').text()).toBe('0')
    expect(wrapper.find('[data-testid="runtime-p0-implementation-gate"]').text()).toBe('NO-GO')
    expect(wrapper.find('[data-testid="runtime-p0-phase3i-gate"]').text()).toBe('NOT_AUTHORIZED')
  })
})
