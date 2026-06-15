/**
 * Phase 2E-H1: Console Hardening — browser smoke for the hardened invariants.
 *
 * Validates the Phase 2E-H1 hardening changes against the live Dev API + WebUI:
 *   - the Overview phase-status card shows Phase 2E "Completed" (was "In
 *     progress") — the stale-baseline fix;
 *   - the Diagnostics phase timeline lists Phase 2E-H1 as completed;
 *   - keyboard navigation (ArrowDown) moves the active nav section in a real
 *     browser (roving tabindex is operable end-to-end);
 *   - no console section leaks secrets / tokens / production paths / callable
 *     reprs into the DOM.
 *
 * The blocked-reason catalogue fix (blocked_write_forbidden_path) is
 * deterministically pinned by the vitest suite; this smoke focuses on the
 * browser-rendered phase-status, keyboard, and no-leak invariants.
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181
 *   WebUI    on 127.0.0.1:5180  (pnpm dev)
 *
 * Gate env (set by the smoke harness phase2e_h1_frontend_ux_hardening profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 *   HERMES_PROVIDER_MODE=fake
 *   HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const CONSOLE_URL = 'http://127.0.0.1:5180/#/console'

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

async function webuiAvailable(page: Page): Promise<boolean> {
  try {
    await page.goto(CONSOLE_URL, { timeout: 6000 })
    return true
  } catch {
    return false
  }
}

// Patterns that must NEVER appear in any dev-console payload / DOM.
const LEAK_PATTERNS = [
  'sk-',
  'Bearer ',
  '<function',
  'object at 0x',
  '/Users/huangruibang/.hermes',
  'rawArguments',
  'fullTokenHash',
  'plainToken',
]

// ===================================================================
// 1. API leg — the hardened invariants are live and leak-free
// ===================================================================

test.describe('Phase 2E-H1 — Overview data sources (API)', () => {
  test('GET /tools/policy + /tools/audit-events remain leak-free', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    for (const path of ['/tools/policy', '/tools/audit-events?auditKind=post_execution&limit=5']) {
      const resp = await request.get(`${API_BASE}${path}`)
      expect(resp.status(), path).toBe(200)
      const body = await resp.text()
      for (const pattern of LEAK_PATTERNS) {
        expect(body, `${path} must not contain ${pattern}`).not.toContain(pattern)
      }
    }
  })
})

// ===================================================================
// 2. UI leg — the hardened console invariants
// ===================================================================

test.describe('Phase 2E-H1 — hardened console UI', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await webuiAvailable(page)), 'WebUI not available on 127.0.0.1:5180')
    await page.evaluate(() => {
      window.localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      window.localStorage.setItem('hermes-dev-webui.follow-system', 'false')
      // Reset the persisted console section so each test starts on Overview.
      window.localStorage.removeItem('hermes-dev-webui.devconsole.section')
    })
    await page.goto(CONSOLE_URL)
    await page.waitForLoadState('networkidle').catch(() => {})
  })

  test('Overview shows Phase 2E as Completed (stale-baseline fix)', async ({ page }) => {
    await expect(page.locator('.devconsole')).toBeVisible()
    const text = await page.locator('.devconsole__content').textContent()
    expect(text).toContain('Completed')
    expect(text).not.toContain('In progress')
    // Frozen route governance still reads 34/34.
    expect(text).toContain('34 / 34')
  })

  test('Diagnostics timeline lists Phase 2E-H1 as completed', async ({ page }) => {
    await page.locator('#devconsole-nav-diagnostics').click()
    await page.waitForTimeout(200)
    const text = await page.locator('.devconsole__content').textContent()
    expect(text).toContain('Phase 2E-H1')
    expect(text).toContain('SEALED')
    // Phase 3 remains not started.
    expect(text).toContain('Phase 3')
  })

  test('keyboard ArrowDown moves the active nav section (roving tabindex operable)', async ({ page }) => {
    await expect(page.locator('#devconsole-nav-overview')).toBeVisible()
    // Start on Overview (aria-selected), focus it, ArrowDown → active becomes tools.
    await page.locator('#devconsole-nav-overview').focus()
    await page.keyboard.press('ArrowDown')
    await expect(page.locator('#devconsole-nav-tools')).toHaveAttribute('aria-selected', 'true')
    // The tools section content is now rendered.
    await expect(page.locator('#tool-execute-canonical')).toBeVisible()
  })

  test('no console section leaks secrets / production paths / callable reprs into the DOM', async ({ page }) => {
    // Visit every section and sweep the rendered DOM for leak patterns.
    for (const section of ['overview', 'tools', 'provider', 'write', 'audit', 'safety', 'diagnostics']) {
      await page.locator(`#devconsole-nav-${section}`).click()
      await page.waitForTimeout(120)
      const html = await page.locator('.devconsole').innerHTML()
      for (const pattern of LEAK_PATTERNS) {
        expect(html, `section ${section} must not contain ${pattern}`).not.toContain(pattern)
      }
    }
  })

  test('never renders an API-key or shell-command input across the console', async ({ page }) => {
    await page.locator('#devconsole-nav-overview').click()
    expect(await page.locator('input[type="password"]').count()).toBe(0)
    const keyInputs = await page.locator('input').evaluateAll((els) =>
      els.filter((el) => /api[_-]?key/i.test((el.id || '') + (el.getAttribute('name') || ''))).length,
    )
    expect(keyInputs).toBe(0)
  })
})
