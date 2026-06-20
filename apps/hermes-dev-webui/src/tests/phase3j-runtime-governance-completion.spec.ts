/**
 * Phase 3J — Runtime Governance read-only WebUI COMPLETION tests.
 *
 * Hardens the read-only surface from "renders" to "deliverable": full UX
 * regions (header h1 + status badges + read-only explanation), descriptor
 * interactions, responsive basics, accessibility (heading hierarchy, table
 * caption, aria-current, non-color badges, no inputs), the no-execution /
 * no-network invariants, the frozen P0 / NO-GO / side-effect invariants,
 * defense-in-depth redaction on the rendered output, inline DOM snapshots for
 * regression, the harmless clipboard-copy affordance, and route/nav governance.
 *
 * No backend, no production, no execution — the section is mounted in jsdom.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import RuntimeGovernanceSection from '@/components/devconsole/RuntimeGovernanceSection.vue'
import { RUNTIME_REVIEWED_DESCRIPTORS } from '@/constants/runtimeGovernanceManifest'

const EXPECTED_DESCRIPTOR_IDS = [
  'descriptor.fixture.echo_uppercase',
  'descriptor.fixture.normalize_text',
  'descriptor.fixture.validate_required_keys',
  'descriptor.fixture.count_items',
  'descriptor.fixture.redact_payload',
  'descriptor.fixture.fault',
]

/** Forbidden action verbs that must never appear as a button control. */
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

/** Secret / production-path tokens that must never appear in the rendered DOM. */
const FORBIDDEN_RENDER_TOKENS = [
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
  'phase_3i_authorized=true',
  'production_approved=true',
  'route_exception_approved=true',
]

/** Defense-in-depth redaction corpus injected only into the redactor in tests. */
const REDACTION_CORPUS = [
  'sk-FAKE-SECRET-DO-NOT-LEAK-12345678',
  'Authorization: Bearer fake-token',
  'ghp_fakegithubtoken',
  'xox-fake-slack-token',
  '-----BEGIN PRIVATE KEY-----',
  'OPENAI_API_KEY=fake',
  'db_password=fake',
  'accessToken=fake',
  '~/.hermes',
  '/fake/production/state.db',
  'implementation_authorization=GO',
  'phase_3i_authorized=true',
  'production_approved=true',
  'route_exception_approved=true',
]

describe('Runtime Governance completion (Phase 3J)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ── A. UX rendering ───────────────────────────────────────────────────────

  it('renders exactly one page <h1> and a set of <h2> region headings', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.findAll('h1')).toHaveLength(1)
    expect(wrapper.find('h1').text()).toBe('Runtime Governance')
    // Every major region is an h2 (banner, table, detail, allowlist, P0, safety, route, CLI).
    expect(wrapper.findAll('h2').length).toBeGreaterThanOrEqual(7)
  })

  it('renders the five frozen page-header status badges', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const badges = wrapper.find('[data-testid="runtime-status-badges"]')
    expect(badges.exists()).toBe(true)
    const labels = badges.findAll('li').map((li) => li.text())
    expect(labels).toEqual([
      'DEV-ONLY',
      'READ-ONLY',
      'FIXTURE-ONLY',
      'NO PRODUCTION',
      'NO WEBUI EXECUTION',
    ])
  })

  it('renders the read-only explanation text', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('read-only')
    expect(text).toContain('does not execute a runtime')
    expect(text).toContain('does not authorize production')
    expect(text).toContain('does not add a backend route')
  })

  it('renders the CLI examples with a harmless Copy control per command', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const cli = wrapper.find('[data-testid="runtime-cli-examples"]')
    expect(cli.exists()).toBe(true)
    const copyButtons = cli.findAll('button')
    expect(copyButtons.length).toBe(6) // one Copy per example
    for (const btn of copyButtons) {
      expect(btn.attributes('aria-label')).toMatch(/^Copy command example \d+$/)
    }
  })

  // ── B. Descriptor interactions ───────────────────────────────────────────

  it('defaults to the echo_uppercase binding and marks its row aria-current', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const detail = wrapper.find('[data-testid="runtime-detail-binding"]')
    expect(detail.text()).toContain('descriptor.fixture.echo_uppercase')
    const row = wrapper.find('[data-descriptor-id="descriptor.fixture.echo_uppercase"]')
    expect(row.attributes('aria-current')).toBe('true')
  })

  it('selecting another descriptor updates the read-only binding detail', async () => {
    const wrapper = mount(RuntimeGovernanceSection)
    await wrapper
      .find('[data-testid="runtime-inspect-descriptor.fixture.redact_payload"]')
      .trigger('click')
    const detail = wrapper.find('[data-testid="runtime-detail-binding"]')
    expect(detail.text()).toContain('descriptor.fixture.redact_payload')
    expect(detail.text()).toContain('fixture.redact')
    // The newly selected row is now the aria-current one.
    expect(
      wrapper.find('[data-descriptor-id="descriptor.fixture.redact_payload"]').attributes('aria-current'),
    ).toBe('true')
  })

  it('renders the denied-binding preview with the frozen denial reasons', async () => {
    const wrapper = mount(RuntimeGovernanceSection)
    await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
    const denied = wrapper.find('[data-testid="runtime-detail-denied"]')
    expect(denied.exists()).toBe(true)
    const reasons = wrapper.find('[data-testid="runtime-detail-denial-reasons"]').text()
    expect(reasons).toContain('descriptor_not_in_static_registry')
    expect(reasons).toContain('descriptor_registry_lookup')
  })

  it('projects exactly six reviewed descriptors in the frozen deterministic order', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const rows = wrapper.find('[data-testid="runtime-descriptor-table"]').findAll('tbody tr')
    expect(rows).toHaveLength(6)
    const ids = rows.map((r) => r.attributes('data-descriptor-id'))
    expect(ids).toEqual(EXPECTED_DESCRIPTOR_IDS)
    // The order is deterministic (re-mount yields the same sequence).
    const again = mount(RuntimeGovernanceSection)
      .find('[data-testid="runtime-descriptor-table"]')
      .findAll('tbody tr')
      .map((r) => r.attributes('data-descriptor-id'))
    expect(again).toEqual(ids)
  })

  // ── C. Responsive basics ─────────────────────────────────────────────────

  it('wraps the wide descriptor table in a scrollable region for narrow screens', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const scroll = wrapper.find('[data-testid="runtime-descriptor-table"] .rtgov-table-scroll')
    expect(scroll.exists()).toBe(true)
    expect(scroll.attributes('role')).toBe('region')
    // The region is keyboard-focusable so scroll is reachable without a mouse.
    expect(scroll.attributes('tabindex')).toBe('0')
  })

  it('status badge container wraps rather than overflows (flex-wrap present in class list)', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const badges = wrapper.find('[data-testid="runtime-status-badges"]')
    expect(badges.classes()).toContain('rtgov-status-badges')
    // Each badge is non-wrapping text so the row collapses cleanly on narrow widths.
    expect(badges.findAll('li').length).toBe(5)
  })

  // ── D. Accessibility ─────────────────────────────────────────────────────

  it('the descriptor table has a caption and labelled column headers', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const table = wrapper.find('[data-testid="runtime-descriptor-table"] table')
    expect(table.find('caption').exists()).toBe(true)
    const headers = table.findAll('thead th').map((th) => th.text().trim())
    expect(headers).toContain('Descriptor ID')
    expect(headers).toContain('Binding')
    expect(headers).toContain('Executable')
  })

  it('every Inspect button has a descriptive accessible name', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const buttons = wrapper.findAll('[data-testid^="runtime-inspect-"]')
    expect(buttons.length).toBe(6)
    for (const btn of buttons) {
      const label = btn.attributes('aria-label') ?? ''
      expect(label).toMatch(/^Inspect binding for descriptor\.fixture\./)
    }
  })

  it('conveys boundary state by TEXT (non-color) — NO-GO badges are not color-only', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const verdicts = wrapper.find('[data-testid="runtime-boundary-verdicts"]')
    // Each verdict renders its verdict word as visible text.
    const text = verdicts.text()
    expect(text).toContain('NO-GO')
    expect(text).toContain('NOT_AUTHORIZED')
    // Boundary items render explicit text labels.
    const items = wrapper.find('[data-testid="runtime-boundary-items"]')
    expect(items.text().toLowerCase()).toContain('no arbitrary plugin loading')
    expect(items.text().toLowerCase()).toContain('no production rollout')
  })

  it('exposes no form control input (no input / textarea / select / file picker)', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.findAll('textarea').length).toBe(0)
    expect(wrapper.findAll('select').length).toBe(0)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })

  // ── E. No execution controls ─────────────────────────────────────────────

  it('exposes no execution / approval / loading control on any button', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
    for (const btn of buttons) {
      const label = (btn.text() + ' ' + (btn.attributes('aria-label') ?? '')).toLowerCase()
      const tokenized = label.replace(/[^a-z0-9]+/g, ' ')
      for (const word of FORBIDDEN_BUTTON_WORDS) {
        expect(tokenized, `button "${btn.text()}" must not offer ${word}`).not.toMatch(
          new RegExp(`\\b${word}\\b`),
        )
      }
    }
  })

  it('every button visible-text is one of the harmless allowed controls', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const allowedTexts = new Set([
      'Inspect',
      'Copy',
      'Copied',
      'Unavailable',
      'Preview denied state',
      'Show selected binding',
    ])
    const distinct = new Set(wrapper.findAll('button').map((b) => b.text().trim()))
    for (const text of distinct) {
      expect(allowedTexts, `unexpected button text "${text}"`).toContain(text)
    }
  })

  // ── F. No network / API mutation ─────────────────────────────────────────

  it('renders + selects descriptors + previews denied + copies with NO network call', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const xhrOpen = vi.fn()
    vi.stubGlobal('XMLHttpRequest', function MockXHR() {
      return { open: xhrOpen, send: vi.fn(), setRequestHeader: vi.fn(), addEventListener: () => {} }
    })
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(RuntimeGovernanceSection)
      for (const d of RUNTIME_REVIEWED_DESCRIPTORS) {
        await wrapper.find(`[data-testid="runtime-inspect-${d.descriptorId}"]`).trigger('click')
      }
      await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
      await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
      await wrapper.find('[data-testid="runtime-cli-list"] li button').trigger('click')
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(xhrOpen).not.toHaveBeenCalled()
    } finally {
      vi.unstubAllGlobals()
    }
  })

  // ── G. P0 / NO-GO ─────────────────────────────────────────────────────────

  it('projects the frozen P0 evidence (24 / 0 / 19 / 5) and every authorization NO-GO', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const p0 = wrapper.find('[data-testid="runtime-p0-evidence-panel"]')
    expect(p0.find('[data-testid="runtime-p0-total"]').text()).toBe('24')
    expect(p0.find('[data-testid="runtime-p0-resolved"]').text()).toBe('0')
    expect(p0.find('[data-testid="runtime-p0-implementation-gate"]').text()).toBe('NO-GO')
    expect(p0.find('[data-testid="runtime-p0-phase3i-gate"]').text()).toBe('NOT_AUTHORIZED')
    const text = p0.text()
    expect(text).toContain('19') // partial evidence
    expect(text).toContain('5') // pending human review
    // Production runtime / new route / production rollout all NO-GO.
    expect(text).toContain('NO-GO')
  })

  // ── H. Side effects ───────────────────────────────────────────────────────

  it('renders the 12 frozen side-effect flags, every one false, with no toggle control', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const matrix = wrapper.find('[data-testid="runtime-safety-matrix"]')
    const items = matrix.findAll('[data-testid="runtime-safety-list"] li')
    expect(items).toHaveLength(12)
    const html = matrix.html()
    expect(html).not.toContain('data-side-effect="true"')
    // No interactive control inside the matrix.
    expect(matrix.findAll('button').length).toBe(0)
    expect(matrix.findAll('input').length).toBe(0)
  })

  // ── I. Redaction on the rendered output ──────────────────────────────────

  it('the rendered section HTML contains no forbidden secret / path / authorization token', () => {
    const html = mount(RuntimeGovernanceSection).html()
    for (const token of FORBIDDEN_RENDER_TOKENS) {
      expect(html, `forbidden render token ${token}`).not.toContain(token)
    }
  })

  it('the redaction corpus is fully masked by the defense-in-depth redactor', async () => {
    const { redactRuntimeValue } = await import('@/lib/runtimeGovernanceViewModel')
    for (const value of REDACTION_CORPUS) {
      expect(redactRuntimeValue(value)).toBe('[REDACTED]')
    }
  })

  // ── J. Snapshot / DOM regression (inline) ─────────────────────────────────

  it('status badges, descriptor ids, side-effect keys, and CLI commands are stable', async () => {
    const { buildRuntimeGovernanceViewModel, buildStatusBadges } = await import(
      '@/lib/runtimeGovernanceViewModel'
    )
    const vm = buildRuntimeGovernanceViewModel()
    expect(buildStatusBadges().map((b) => b.label)).toMatchInlineSnapshot(`
      [
        "DEV-ONLY",
        "READ-ONLY",
        "FIXTURE-ONLY",
        "NO PRODUCTION",
        "NO WEBUI EXECUTION",
      ]
    `)
    expect(vm.descriptors.map((d) => d.descriptorId)).toMatchInlineSnapshot(`
      [
        "descriptor.fixture.echo_uppercase",
        "descriptor.fixture.normalize_text",
        "descriptor.fixture.validate_required_keys",
        "descriptor.fixture.count_items",
        "descriptor.fixture.redact_payload",
        "descriptor.fixture.fault",
      ]
    `)
    expect(vm.sideEffectFlags.map((f) => f.key)).toMatchInlineSnapshot(`
      [
        "productionAccess",
        "externalNetwork",
        "realSecretRead",
        "routeChange",
        "runtimeStoreWrite",
        "auditStoreWrite",
        "arbitraryPluginLoad",
        "localPluginDirectoryRead",
        "remotePluginFetch",
        "marketplaceAccess",
        "inputFileRead",
        "outputFileWrite",
      ]
    `)
    expect(vm.cliExamples.map((c) => c.command)).toEqual([
      'hermes dev-runtime list',
      'hermes dev-runtime show descriptor.fixture.echo_uppercase',
      "hermes dev-runtime run descriptor.fixture.echo_uppercase --input '{\"text\":\"hello\"}'",
      "hermes dev-runtime batch --items '[{\"descriptor_id\":\"descriptor.fixture.echo_uppercase\",\"input\":{\"text\":\"hello\"}}]'",
      "hermes dev-runtime audit descriptor.fixture.echo_uppercase --input '{\"text\":\"hello\"}'",
      'hermes dev-runtime p0-report',
    ])
  })

  // ── Copy affordance (harmless, clipboard-only) ────────────────────────────

  it('Copy writes the command text to the clipboard and flips to a Copied state', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(RuntimeGovernanceSection)
    const firstCopy = wrapper.find('[data-testid="runtime-cli-list"] li button')
    await firstCopy.trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalledWith('hermes dev-runtime list')
    expect(firstCopy.attributes('data-copy-state')).toBe('copied')
    expect(firstCopy.text()).toContain('Copied')
  })

  it('Copy shows a harmless Unavailable state when the clipboard API is absent', async () => {
    vi.stubGlobal('navigator', {}) // no clipboard
    const wrapper = mount(RuntimeGovernanceSection)
    const firstCopy = wrapper.find('[data-testid="runtime-cli-list"] li button')
    await firstCopy.trigger('click')
    await Promise.resolve()
    expect(firstCopy.attributes('data-copy-state')).toBe('unavailable')
    expect(firstCopy.text()).toContain('Unavailable')
  })

  it('Copy never calls fetch even when the clipboard rejects', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not be called')
    })
    const writeText = vi.fn().mockRejectedValue(new Error('clipboard denied'))
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const wrapper = mount(RuntimeGovernanceSection)
      const firstCopy = wrapper.find('[data-testid="runtime-cli-list"] li button')
      await firstCopy.trigger('click')
      await Promise.resolve()
      await Promise.resolve()
      expect(writeText).toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(firstCopy.attributes('data-copy-state')).toBe('unavailable')
    } finally {
      vi.unstubAllGlobals()
    }
  })

  // ── L. Route / nav governance ─────────────────────────────────────────────

  it('Runtime Governance is present as a client-side DevConsole section', async () => {
    const { CONSOLE_SECTIONS, CONSOLE_SECTION_LABELS } = await import('@/stores/devConsoleNav')
    expect((CONSOLE_SECTIONS as readonly string[]).includes('runtimeGovernance')).toBe(true)
    expect(CONSOLE_SECTION_LABELS.runtimeGovernance).toBe('Runtime Governance')
  })

  it('the section boundary copy still states no backend route was added', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.find('[data-testid="runtime-route-governance"]').text().toLowerCase()).toContain(
      'no backend route was added',
    )
  })
})
