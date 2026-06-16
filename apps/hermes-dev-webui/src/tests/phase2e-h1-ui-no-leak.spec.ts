/**
 * Phase 2E-H1 — Lens 8: UI No-leak / Safety Boundary.
 *
 * Adversarial no-leak sweep across every console surface, the lib catalogue,
 * and the frozen baseline. The UI must never render: API keys, raw tokens, full
 * token hashes, raw arguments, secrets, callable/function reprs, audit-store /
 * token-store / rollback-manifest internals, or production paths.
 *
 * Safety terms may appear ONLY inside safety statements, negative assertions,
 * the blocked-reason catalogue, or mock placeholders — never as live data.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolPolicy', () => ({ fetchToolPolicyStatus: vi.fn(), fetchToolCatalog: vi.fn() }))
vi.mock('@/api/toolAudit', () => ({ getAuditEvents: vi.fn(), getAuditEventsV2: vi.fn() }))
vi.mock('@/api/toolExecute', () => ({ runDryRun: vi.fn(), executeTool: vi.fn() }))
vi.mock('@/api/toolWrite', () => ({ runWritePreview: vi.fn(), executeWrite: vi.fn(), runRollbackPreview: vi.fn(), executeRollback: vi.fn() }))
vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn(), fetchProviderBoundary: vi.fn().mockResolvedValue(null) }))

import OverviewSection from '@/components/devconsole/OverviewSection.vue'
import SafetySection from '@/components/devconsole/SafetySection.vue'
import DiagnosticsSection from '@/components/devconsole/DiagnosticsSection.vue'
import ToolExecutionSection from '@/components/devconsole/ToolExecutionSection.vue'
import ProviderSection from '@/components/devconsole/ProviderSection.vue'
import WriteRollbackSection from '@/components/devconsole/WriteRollbackSection.vue'
import AuditViewerSection from '@/components/devconsole/AuditViewerSection.vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import { SAFETY_BADGES } from '@/lib/safetyBadges'
import { KNOWN_BLOCKED_REASONS, lookupBlockedReason } from '@/lib/blockedReasons'
import { FROZEN_STATIC_ALLOWLIST, FROZEN_STATIC_WRITE_TOOLS } from '@/lib/frozenBaseline'

// Patterns that must NEVER appear as live data in the rendered console.
const LEAK_PATTERNS: ReadonlyArray<RegExp> = [
  /sk-[A-Za-z0-9_-]{16,}/, // real-looking API keys
  /Bearer\s+\S+/i,
  /Authorization\s*:\s*\S+/i,
  /<function|<bound method|object at 0x/,
  /rawArguments|fullTokenHash|plainToken|tokenSecret/,
  /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/,
]
const PRODUCTION_PATH = '/Users/huangruibang/.hermes'

function assertNoLeak(html: string, label: string): void {
  for (const pat of LEAK_PATTERNS) {
    expect(html, `${label} leaked ${pat}`).not.toMatch(pat)
  }
  expect(html, `${label} leaked production path`).not.toContain(PRODUCTION_PATH)
}

describe('Lens 8 — UI no-leak / safety (Phase 2E-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('no console section leaks secrets / tokens / callable reprs / production paths', () => {
    const sections = [
      OverviewSection,
      SafetySection,
      DiagnosticsSection,
      ToolExecutionSection,
      ProviderSection,
      WriteRollbackSection,
      AuditViewerSection,
    ]
    for (const Section of sections) {
      const wrapper = mount(Section)
      assertNoLeak(wrapper.html(), Section.__name ?? Section.name ?? 'section')
    }
  })

  it('no section renders an API-key / shell-command / password input affordance', () => {
    const sections = [OverviewSection, SafetySection, DiagnosticsSection, ToolExecutionSection, ProviderSection, WriteRollbackSection, AuditViewerSection]
    for (const Section of sections) {
      const wrapper = mount(Section)
      expect(wrapper.findAll('input[type="password"]').length, `${Section.__name}`).toBe(0)
      expect(wrapper.html(), `${Section.__name}`).not.toMatch(/api[_-]?key\s*input|shell[_-]?command|data-shell-input/i)
    }
  })

  it('AuditIdLink never displays a long id at full length (lossy by design)', () => {
    const long = 'x'.repeat(80)
    const wrapper = mount(AuditIdLink, { props: { id: long, label: 'audit' } })
    expect(wrapper.text()).not.toContain(long)
    // The truncated prefix + ellipsis is shown.
    expect(wrapper.text()).toContain('…')
  })

  it('the blocked-reason catalogue never embeds a raw arg / secret / production path in its text', () => {
    for (const code of KNOWN_BLOCKED_REASONS) {
      const info = lookupBlockedReason(code)
      const blob = `${info.title} ${info.explanation} ${info.safeNextAction}`
      expect(blob, `${code}`).not.toMatch(/sk-[A-Za-z0-9_-]{16,}/)
      expect(blob, `${code}`).not.toContain(PRODUCTION_PATH)
      // Catalogue text may name protected patterns abstractly (.env, .claude)
      // but must never embed a real secret value.
      expect(blob, `${code}`).not.toMatch(/<function|object at 0x/)
    }
  })

  it('safety-badge descriptions describe invariants, never live secrets or production internals', () => {
    for (const badge of SAFETY_BADGES) {
      const blob = `${badge.label} ${badge.description}`
      expect(blob, badge.id).not.toMatch(/sk-[A-Za-z0-9_-]{16,}/)
      // The production home is referenced only as a negative ("never read/written").
      expect(blob, badge.id).not.toMatch(/read.*~\/\.hermes|write.*~\/\.hermes/i)
    }
  })

  it('the frozen baseline static lists carry only tool names, never secrets', () => {
    for (const tool of [...FROZEN_STATIC_ALLOWLIST, ...FROZEN_STATIC_WRITE_TOOLS]) {
      expect(tool).toMatch(/^[a-z0-9_]+$/)
    }
  })
})
