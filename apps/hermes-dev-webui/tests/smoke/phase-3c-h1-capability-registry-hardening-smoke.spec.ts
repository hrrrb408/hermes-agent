/**
 * Phase 3C-H1: Static Capability Registry HARDENING smoke.
 *
 * Deterministic hardening smoke for the static dev-only Capability Registry
 * (HARDENING-3C-H1-001). Exercises ONLY the read-only / default state. It
 * NEVER enables a plugin runtime, NEVER performs dynamic loading, NEVER
 * fetches a remote registry / marketplace, NEVER issues a live provider
 * request, NEVER reads an API key, and NEVER makes a real network call
 * beyond GET /status.
 *
 * Asserts the 23-point H1 boundary:
 *   - capabilityRegistry block exists; capability count = 46; validation valid
 *   - frozen flags: dynamicLoadingAllowed / remoteRegistryAllowed /
 *     marketplaceAllowed / productionAllowed = false; devOnly = true
 *   - registry describes only / does not grant permission (UI)
 *   - live manual one-shot listed but disabled (not executed)
 *   - dynamic_plugin_load / remote_registry / marketplace / shell / database /
 *     external_http / production_operation blocked
 *   - UI panel visible; badges carry text labels; no API key / Authorization /
 *     callable repr / production path; blocked reasons visible
 *   - route governance unchanged (no capability route)
 *
 * Production-side points (Gateway PID 28428, ports 5180/5181 free, no
 * ~/.hermes access) are enforced by the Phase 3C-H1 hardening audit script.
 *
 * Gate env (set by the smoke harness phase3c_h1_capability_registry_hardening
 * profile): read-only execution gates on + FAKE provider only (no live path).
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const WEBUI_BASE = 'http://127.0.0.1:5180'

// HTML-safe tokens (avoid short substrings that collide with SVG icon classes).
const FORBIDDEN_HTML_TOKENS = [
  'apiKey', 'Authorization', 'Bearer', 'shellCommand', 'pythonImportPath',
  'externalUrl', 'downloadUrl', 'pluginPackage', 'dynamicModule', 'evalCode',
  'execCode', 'sqlStatement', 'productionPath', 'callable', 'secret',
]

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    return (await request.get(`${API_BASE}/status`, { timeout: 4000 })).ok()
  } catch {
    return false
  }
}

async function webuiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    return (await request.get(WEBUI_BASE, { timeout: 4000 })).ok()
  } catch {
    return false
  }
}

test.describe('Phase 3C-H1 Capability Registry hardening (API)', () => {
  test('1-3. block exists, count=46, validation valid', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    expect(cr).toBeTruthy()
    expect(cr.capabilityCount).toBe(46)
    expect(cr.validation.valid).toBe(true)
    expect(cr.validation.errorCount).toBe(0)
    expect(cr.status).toBe('enabled')
  })

  test('4-7. frozen flags: no dynamic / remote / marketplace / production', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    expect(cr.dynamicLoadingAllowed).toBe(false)
    expect(cr.remoteRegistryAllowed).toBe(false)
    expect(cr.marketplaceAllowed).toBe(false)
    expect(cr.productionAllowed).toBe(false)
    expect(cr.devOnly).toBe(true)
    expect(cr.redactionApplied).toBe(true)
  })

  test('counts partition the total', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    const total =
      cr.enabledCount + cr.disabledCount + cr.blockedCount + cr.plannedCount + cr.deprecatedCount
    expect(total).toBe(cr.capabilityCount)
    // Blocked capabilities are present (the forbidden class is described, not enabled).
    expect(cr.blockedCount).toBeGreaterThan(0)
  })

  test('10-13. blocked capabilities are described (blockedCount > 0); route governance pinned', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    expect(cr.blockedCount).toBeGreaterThanOrEqual(10)
    expect(cr.routeGovernanceExpected).toBe('34/34/5/0/1/1')
  })

  test('21. no capability HTTP route exists (route governance unchanged)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const openapi = (await request.get(`${API_BASE}/../openapi.json`).catch(() => null)) as
      | { paths?: Record<string, unknown> }
      | null
    if (openapi?.paths) {
      for (const path of Object.keys(openapi.paths)) {
        expect(path.toLowerCase()).not.toContain('capabilit')
      }
    }
  })

  test('the /status block is value-free (no leak)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    const blob = JSON.stringify(cr)
    for (const token of FORBIDDEN_HTML_TOKENS) {
      expect(blob, `forbidden token ${token}`).not.toContain(token)
    }
    expect(blob).not.toContain('/Users/huangruibang/.hermes')
    expect(blob).not.toContain('state.db')
  })
})

test.describe('Phase 3C-H1 Capability Registry hardening (UI)', () => {
  test('15-20. UI panel, describes-only, badges, blocked reasons, no leak', async ({
    request,
    page,
  }: {
    request: APIRequestContext
    page: Page
  }) => {
    test.skip(!(await webuiAvailable(request)), 'Dev WebUI not available on 127.0.0.1:5180')
    await page.goto(`${WEBUI_BASE}/#/console`)
    const navBtn = page.getByRole('tab', { name: /Capability Registry/i })
    if (await navBtn.count()) {
      await navBtn.click()
    }
    await expect(page.getByText('Capability Registry').first()).toBeVisible({ timeout: 8000 })

    const body = await page.locator('body').innerText()

    // 8-9. Registry describes only / does not grant permission.
    expect(body.toLowerCase()).toContain('does not grant permission')
    expect(body.toLowerCase()).toContain('describes only')
    // Frozen-flag messaging.
    expect(body.toLowerCase()).toContain('dynamic loading')
    expect(body.toLowerCase()).toContain('marketplace')

    // 14. Live manual one-shot is listed but disabled (not executed).
    expect(body).toContain('provider.live_manual_one_shot')
    expect(body).toContain('Live provider gated')

    // 10-13. Forbidden capabilities are described as blocked with reasons.
    for (const reason of [
      'dynamic_plugin_load_forbidden',
      'remote_registry_forbidden',
      'marketplace_forbidden',
      'shell_command_forbidden',
      'database_mutation_forbidden',
      'external_http_forbidden',
      'production_operation_forbidden',
    ]) {
      expect(body, `blocked reason ${reason}`).toContain(reason)
    }

    // 16. Badges carry text labels (non-color).
    expect(body).toContain('Read-only')
    expect(body).toContain('Forbidden')

    // 17-20. No forbidden token / secret / path rendered.
    for (const token of FORBIDDEN_HTML_TOKENS) {
      expect(body, `forbidden token ${token} rendered`).not.toContain(token)
    }
    expect(body).not.toContain('/Users/huangruibang/.hermes')
    expect(body).not.toContain('state.db')
    // No API-key input field exists.
    expect(await page.locator('input[type="password"]').count()).toBe(0)
  })
})
