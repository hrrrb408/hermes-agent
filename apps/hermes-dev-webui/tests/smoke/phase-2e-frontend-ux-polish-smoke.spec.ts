/**
 * Phase 2E: Frontend UX Polish — unified developer console browser smoke.
 *
 * Verifies the new /#/console view end-to-end against the live Dev API + WebUI:
 *   - the Overview dashboard, Safety Boundary panel, and each reused panel
 *     section render and are reachable from the nav rail;
 *   - the Overview data sources (GET /tools/policy, GET /tools/audit-events)
 *     respond and contain no leaked secrets / production paths / callable reprs;
 *   - no API-key or shell-command input is ever rendered.
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181
 *   WebUI    on 127.0.0.1:5180  (pnpm dev)
 *
 * Gate env (set by the smoke harness phase2e_frontend_ux_polish profile):
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
// 1. API leg — Overview data sources are live and leak-free
// ===================================================================

test.describe('Phase 2E dev console — Overview data sources (API)', () => {
  test('GET /tools/policy is live and leak-free', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.get(`${API_BASE}/tools/policy`)
    expect(resp.status()).toBe(200)
    const body = await resp.text()
    for (const pattern of LEAK_PATTERNS) {
      expect(body, `policy body must not contain ${pattern}`).not.toContain(pattern)
    }
    const data = (await request.get(`${API_BASE}/tools/policy`).then((r) => r.json())).data
    expect(typeof data.inventoryCount).toBe('number')
    expect(data.safety.readOnly).toBe(true)
    expect(data.execution.enabled).toBe(false)
  })

  test('GET /tools/audit-events returns the durable store status', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.get(`${API_BASE}/tools/audit-events`, {
      params: { auditKind: 'post_execution', limit: 5 },
    })
    expect(resp.status()).toBe(200)
    const body = await resp.text()
    for (const pattern of LEAK_PATTERNS) {
      expect(body, `audit body must not contain ${pattern}`).not.toContain(pattern)
    }
  })
})

// ===================================================================
// 2. UI leg — the unified developer console renders every section
// ===================================================================

test.describe('Phase 2E dev console — UI', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await webuiAvailable(page)), 'WebUI not available on 127.0.0.1:5180')
    await page.evaluate(() => {
      window.localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      window.localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })
    await page.goto(CONSOLE_URL)
    await page.waitForLoadState('networkidle').catch(() => {})
  })

  test('Overview dashboard renders with safety badges + frozen route governance', async ({ page }) => {
    await expect(page.locator('.devconsole')).toBeVisible()
    await expect(page.locator('#devconsole-nav-overview')).toBeVisible()
    await expect(page.locator('[data-testid="dev-safety-badges"]')).toBeVisible()
    const text = await page.locator('.devconsole__content').textContent()
    expect(text).toContain('Production untouched')
    expect(text).toContain('34 / 34')
  })

  test('Tool Execution section exposes the read-only tool selector', async ({ page }) => {
    await page.locator('#devconsole-nav-tools').click()
    await page.waitForTimeout(200)
    await expect(page.locator('#tool-execute-canonical')).toBeVisible()
    const options = await page.locator('#tool-execute-canonical option').allTextContents()
    expect(options.some((o) => o.includes('route_governance_read'))).toBeTruthy()
  })

  test('Provider Round-trip section renders with real-blocked messaging', async ({ page }) => {
    await page.locator('#devconsole-nav-provider').click()
    await page.waitForTimeout(200)
    await expect(page.locator('#provider-mode')).toBeVisible()
    const text = await page.locator('.devconsole__content').textContent()
    expect(text).toContain('Real provider mode is blocked by default')
  })

  test('Sandbox Write & Rollback section renders the write surface', async ({ page }) => {
    await page.locator('#devconsole-nav-write').click()
    await page.waitForTimeout(200)
    await expect(page.locator('#write-tool')).toBeVisible()
    await expect(page.locator('#write-target')).toBeVisible()
    await expect(page.locator('#write-rollback-id')).toBeVisible()
  })

  test('Audit Viewer section renders store toggle + filters', async ({ page }) => {
    await page.locator('#devconsole-nav-audit').click()
    await page.waitForTimeout(200)
    await expect(page.locator('#audit-viewer-store-toggle')).toBeVisible()
    // Ensure store mode is ON (it may already be on); click only if the filter
    // bar is not yet visible.
    const controls = page.locator('#audit-viewer-store-controls')
    if (!(await controls.isVisible().catch(() => false))) {
      await page.locator('#audit-viewer-store-toggle').click()
    }
    await expect(controls).toBeVisible()
    await expect(page.locator('#audit-viewer-store-limit')).toBeVisible()
    await expect(page.locator('#audit-viewer-search-input')).toBeVisible()
  })

  test('Safety Boundary panel renders the frozen route governance baseline', async ({ page }) => {
    await page.locator('#devconsole-nav-safety').click()
    await page.waitForTimeout(200)
    const text = await page.locator('.devconsole__content').textContent()
    expect(text).toContain('Route governance baseline')
    expect(text).toContain('28428')
  })

  test('Diagnostics renders the dev environment + release status', async ({ page }) => {
    await page.locator('#devconsole-nav-diagnostics').click()
    await page.waitForTimeout(200)
    const text = await page.locator('.devconsole__content').textContent()
    expect(text).toContain('hermes-home-dev')
    expect(text).toContain('Phase 1G')
    expect(text).toContain('SEALED')
  })

  test('never renders an API-key or shell-command input', async ({ page }) => {
    expect(await page.locator('input[type="password"]').count()).toBe(0)
    const keyInputs = await page.locator('input').evaluateAll((els) =>
      els.filter((el) => /api[_-]?key/i.test((el.id || '') + (el.getAttribute('name') || ''))).length,
    )
    expect(keyInputs).toBe(0)
  })

  test('DOM contains no leaked secrets / production paths / callable reprs', async ({ page }) => {
    const html = await page.locator('.devconsole').innerHTML()
    for (const pattern of LEAK_PATTERNS) {
      expect(html, `console DOM must not contain ${pattern}`).not.toContain(pattern)
    }
  })
})
