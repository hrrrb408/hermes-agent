/**
 * Phase 3C: Static Capability Registry smoke.
 *
 * Exercises the static dev-only Capability Registry ONLY in its read-only /
 * default state. It NEVER enables a plugin runtime, NEVER performs dynamic
 * loading, NEVER fetches a remote registry / marketplace, NEVER issues a live
 * provider request, NEVER reads an API key, and NEVER makes a real network
 * call beyond GET /status.
 *
 * Asserts:
 *   - the capabilityRegistry block exists under /status data
 *   - registry status + capability counts are visible
 *   - dynamicLoadingAllowed / remoteRegistryAllowed / marketplaceAllowed = false
 *   - productionAllowed = false
 *   - the UI renders the registry panel (Dev Console /#/console)
 *   - the UI shows no API key / Authorization / callable repr / production path
 *   - route governance is unchanged (no capability route exists)
 *
 * Gate env (set by the smoke harness phase3c_capability_registry_static profile):
 *   read-only execution gates on + FAKE provider only (no live path).
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const WEBUI_BASE = 'http://127.0.0.1:5180'

const FORBIDDEN_TOKENS = [
  'apiKey',
  'Authorization',
  'Bearer',
  'shellCommand',
  'pythonImportPath',
  'externalUrl',
  'downloadUrl',
  'pluginPackage',
  'dynamicModule',
  'evalCode',
  'execCode',
  'sqlStatement',
  'productionPath',
  'callable',
  'secret',
]

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

async function webuiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(WEBUI_BASE, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

test.describe('Phase 3C Capability Registry (API + UI)', () => {
  test('capabilityRegistry block exists in /status', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const data = (await (await request.get(`${API_BASE}/status`)).json()).data
    expect(data.capabilityRegistry).toBeTruthy()
    const cr = data.capabilityRegistry
    expect(cr.registryVersion).toBe('phase3c-static-v1')
    expect(typeof cr.capabilityCount).toBe('number')
    expect(cr.capabilityCount).toBeGreaterThan(0)
  })

  test('frozen policy flags hold (no dynamic loading / remote / marketplace / production)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    expect(cr.dynamicLoadingAllowed).toBe(false)
    expect(cr.remoteRegistryAllowed).toBe(false)
    expect(cr.marketplaceAllowed).toBe(false)
    expect(cr.productionAllowed).toBe(false)
    expect(cr.devOnly).toBe(true)
    expect(cr.redactionApplied).toBe(true)
  })

  test('route governance baseline surfaces unchanged', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    expect(cr.routeGovernanceExpected).toBe('34/34/5/0/1/1')
  })

  test('validation passed and counts are consistent', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    expect(cr.validation.valid).toBe(true)
    expect(cr.validation.errorCount).toBe(0)
    expect(cr.status).toBe('enabled')
    expect(cr.enabledCount + cr.disabledCount + cr.blockedCount + cr.plannedCount + cr.deprecatedCount).toBe(
      cr.capabilityCount,
    )
  })

  test('the /status block is value-free (no forbidden token)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const cr = (await (await request.get(`${API_BASE}/status`)).json()).data.capabilityRegistry
    const blob = JSON.stringify(cr)
    for (const token of FORBIDDEN_TOKENS) {
      expect(blob, `forbidden token ${token}`).not.toContain(token)
    }
    expect(blob).not.toContain('/Users/huangruibang/.hermes')
    expect(blob).not.toContain('state.db')
  })

  test('no capability HTTP route exists', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const openapi = (await (await request.get(`${API_BASE}/../openapi.json`)).json().catch(() => null)) as
      | { paths?: Record<string, unknown> }
      | null
    if (openapi?.paths) {
      for (const path of Object.keys(openapi.paths)) {
        expect(path.toLowerCase()).not.toContain('capabilit')
      }
    }
  })

  test('UI shows the registry panel + frozen flags + no leak', async ({ request, page }: { request: APIRequestContext; page: Page }) => {
    test.skip(!(await webuiAvailable(request)), 'Dev WebUI not available on 127.0.0.1:5180')
    await page.goto(`${WEBUI_BASE}/#/console`)
    // Navigate to the Capability Registry section via the nav rail.
    const navBtn = page.getByRole('tab', { name: /Capability Registry/i })
    if (await navBtn.count()) {
      await navBtn.click()
    }
    await expect(page.getByText('Capability Registry').first()).toBeVisible({ timeout: 8000 })

    const body = await page.locator('body').innerText()
    // Frozen policy flags are surfaced.
    expect(body.toLowerCase()).toContain('dynamic loading')
    expect(body.toLowerCase()).toContain('marketplace')
    // Registry describes only / does not grant permission.
    expect(body.toLowerCase()).toContain('does not grant permission')

    // No forbidden token in the rendered DOM.
    for (const token of FORBIDDEN_TOKENS) {
      expect(body, `forbidden token ${token} rendered`).not.toContain(token)
    }
  })
})
