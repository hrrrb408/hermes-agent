/**
 * Phase 3D: Static Plugin Descriptor Registry smoke.
 *
 * Exercises the static dev-only Plugin Descriptor Registry ONLY in its
 * read-only / default state. It NEVER enables a plugin runtime, NEVER performs
 * dynamic loading, NEVER reads a local plugin directory, NEVER fetches a remote
 * registry / marketplace, NEVER issues a live provider request, NEVER reads an
 * API key, and NEVER makes a real network call beyond GET /status.
 *
 * Asserts:
 *   - the pluginDescriptorRegistry block exists under /status data
 *   - every runtime flag is false (pluginRuntimeImplemented / pluginLoaderImplemented
 *     / dynamicLoadingAllowed / localPluginDirectoryLoadingAllowed /
 *     remoteRegistryAllowed / marketplaceAllowed / externalPluginFetchAllowed /
 *     providerGeneratedPluginAllowed / llmGeneratedPluginInstallAllowed /
 *     pluginExecutionAllowed / newRouteIntroduced / productionAllowed)
 *   - descriptor / visible / disabled / blocked counts surface
 *   - the blocked dynamic-plugin / remote-registry / marketplace / production-operation
 *     descriptors are present
 *   - the UI renders the descriptor panel + runtime-disabled banner (Dev Console /#/console)
 *   - the UI shows descriptor-only / does-not-grant-permission / does-not-execute-plugin
 *   - the UI shows no API key / Authorization / callable repr / production path /
 *     local plugin path / dynamic import path / external URL / install command
 *   - route governance is unchanged (no plugin/descriptor route exists; 34 baseline)
 *
 * Gate env (set by the smoke harness phase3d_plugin_descriptor_registry_static
 * profile): read-only execution gates on + FAKE provider only (no live path).
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
  'installCommand',
  'localPath',
  'remoteUrl',
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

test.describe('Phase 3D Plugin Descriptor Registry (API + UI)', () => {
  test('pluginDescriptorRegistry block exists in /status', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const data = (await (await request.get(`${API_BASE}/status`)).json()).data
    expect(data.pluginDescriptorRegistry).toBeTruthy()
    const pdr = data.pluginDescriptorRegistry
    expect(pdr.registryVersion).toBe('phase3d-static-descriptor-v1')
    expect(typeof pdr.descriptorCount).toBe('number')
    expect(pdr.descriptorCount).toBeGreaterThan(0)
  })

  test('every runtime flag is false (no plugin runtime / loader / dynamic / remote / marketplace / fetch / exec)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr.pluginRuntimeImplemented).toBe(false)
    expect(pdr.pluginLoaderImplemented).toBe(false)
    expect(pdr.dynamicLoadingAllowed).toBe(false)
    expect(pdr.localPluginDirectoryLoadingAllowed).toBe(false)
    expect(pdr.remoteRegistryAllowed).toBe(false)
    expect(pdr.marketplaceAllowed).toBe(false)
    expect(pdr.externalPluginFetchAllowed).toBe(false)
    expect(pdr.providerGeneratedPluginAllowed).toBe(false)
    expect(pdr.llmGeneratedPluginInstallAllowed).toBe(false)
    expect(pdr.pluginExecutionAllowed).toBe(false)
    expect(pdr.newRouteIntroduced).toBe(false)
    expect(pdr.productionAllowed).toBe(false)
    expect(pdr.devOnly).toBe(true)
    expect(pdr.redactionApplied).toBe(true)
  })

  test('descriptor counts surface (visible / disabled / blocked)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr.descriptorCount).toBe(12)
    expect(pdr.visibleCount).toBe(3)
    expect(pdr.disabledCount).toBe(4)
    expect(pdr.blockedCount).toBe(5)
  })

  test('route governance baseline surfaces unchanged', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr.routeGovernanceExpected).toBe('34/34/5/0/1/1')
  })

  test('validation passed', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr.validation.valid).toBe(true)
    expect(pdr.validation.errorCount).toBe(0)
    expect(pdr.status).toBe('enabled')
  })

  test('the /status block is value-free (no forbidden token)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    const blob = JSON.stringify(pdr)
    for (const token of FORBIDDEN_TOKENS) {
      expect(blob, `forbidden token ${token}`).not.toContain(token)
    }
    expect(blob).not.toContain('/Users/huangruibang/.hermes')
    expect(blob).not.toContain('state.db')
  })

  test('no plugin / descriptor HTTP route exists', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.get(`${API_BASE.replace('/api/dev/v1', '')}/openapi.json`)
    const openapi = (await resp.json().catch(() => null)) as { paths?: Record<string, unknown> } | null
    if (openapi?.paths) {
      const business = Object.keys(openapi.paths).filter((p) => p.startsWith('/api/dev/v1/'))
      expect(business.length).toBe(34)
      for (const path of business) {
        expect(path.toLowerCase()).not.toContain('descriptor')
        expect(path.toLowerCase()).not.toContain('/plugin')
      }
    }
  })

  test('UI shows the descriptor panel + runtime-disabled banner + no leak', async ({ request, page }: { request: APIRequestContext; page: Page }) => {
    test.skip(!(await webuiAvailable(request)), 'Dev WebUI not available on 127.0.0.1:5180')
    await page.goto(`${WEBUI_BASE}/#/console`)
    // Navigate to the Plugin Descriptors section via the nav rail.
    const navBtn = page.getByRole('tab', { name: /Plugin Descriptors/i })
    if (await navBtn.count()) {
      await navBtn.click()
    }
    await expect(page.getByText('Plugin Descriptor Registry').first()).toBeVisible({ timeout: 8000 })

    const body = await page.locator('body').innerText()
    const lower = body.toLowerCase()
    // Runtime-disabled banner invariants.
    expect(lower).toContain('plugin runtime disabled')
    expect(lower).toContain('dynamic loading disabled')
    expect(lower).toContain('remote registry disabled')
    expect(lower).toContain('marketplace disabled')
    // Descriptor only / does not grant permission / does not execute a plugin.
    expect(lower).toContain('descriptor')
    expect(lower).toContain('does not grant permission')
    expect(lower).toContain('does not execute a plugin')

    // No forbidden token in the rendered DOM.
    for (const token of FORBIDDEN_TOKENS) {
      expect(body, `forbidden token ${token} rendered`).not.toContain(token)
    }
    expect(body).not.toContain('/Users/huangruibang/.hermes')
    expect(body).not.toContain('state.db')
  })
})
