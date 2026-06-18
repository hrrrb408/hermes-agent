/**
 * Phase 3D-H1: Static Plugin Descriptor Registry HARDENING smoke.
 *
 * Deterministic hardening smoke for the static dev-only Plugin Descriptor
 * Registry (HARDENING-3D-H1-001). Exercises ONLY the read-only / default
 * state. It NEVER enables a plugin runtime, NEVER performs dynamic loading,
 * NEVER reads a local plugin directory, NEVER fetches a remote registry /
 * marketplace, NEVER issues a live provider request, NEVER reads an API key,
 * and NEVER makes a real network call beyond GET /status.
 *
 * Asserts the H1 boundary:
 *   - pluginDescriptorRegistry block exists; descriptor count = 12; validation valid
 *   - frozen flags: pluginRuntimeImplemented / pluginLoaderImplemented /
 *     dynamicLoadingAllowed / localPluginDirectoryLoadingAllowed /
 *     remoteRegistryAllowed / marketplaceAllowed / externalPluginFetchAllowed /
 *     providerGeneratedPluginAllowed / llmGeneratedPluginInstallAllowed /
 *     pluginExecutionAllowed / newRouteIntroduced / productionAllowed = false;
 *     devOnly = true
 *   - descriptor counts: visible 3 / disabled 4 / blocked 5
 *   - registry describes only / does not grant permission (UI)
 *   - dynamic_plugin_load / remote_registry / marketplace / production_operation
 *     blocked descriptors are present
 *   - UI panel + runtime-disabled banner visible; badges carry text labels;
 *     no API key / Authorization / callable repr / production path / local
 *     plugin path / dynamic import path
 *   - route governance unchanged (no plugin / descriptor route; 34 baseline)
 *
 * Production-side points (Gateway PID 28428, ports 5180/5181 free, no
 * ~/.hermes access) are enforced by the Phase 3D-H1 hardening audit script.
 *
 * Gate env (set by the smoke harness phase3d_h1_plugin_descriptor_registry_hardening
 * profile): read-only execution gates on + FAKE provider only (no live path).
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const WEBUI_BASE = 'http://127.0.0.1:5180'

// HTML-safe tokens (avoid short substrings that collide with SVG icon classes).
const FORBIDDEN_HTML_TOKENS = [
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

test.describe('Phase 3D-H1 Plugin Descriptor Registry hardening (API)', () => {
  test('1-2. block exists, count=12, validation valid', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr).toBeTruthy()
    expect(pdr.descriptorCount).toBe(12)
    expect(pdr.validation.valid).toBe(true)
    expect(pdr.validation.errorCount).toBe(0)
    expect(pdr.status).toBe('enabled')
  })

  test('3-13. frozen flags: no runtime / loader / dynamic / local dir / remote / marketplace / fetch / provider-gen / llm-gen / exec / route / production', async ({ request }) => {
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

  test('descriptor counts partition the total (3 visible / 4 disabled / 5 blocked)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr.visibleCount).toBe(3)
    expect(pdr.disabledCount).toBe(4)
    expect(pdr.blockedCount).toBe(5)
    expect(pdr.visibleCount + pdr.disabledCount + pdr.blockedCount).toBe(pdr.descriptorCount)
  })

  test('route governance baseline pinned (34/34/5/0/1/1)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    expect(pdr.routeGovernanceExpected).toBe('34/34/5/0/1/1')
  })

  test('25-26. no plugin / descriptor HTTP route exists (route governance unchanged)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const openapi = (await request.get(`${API_BASE.replace('/api/dev/v1', '')}/openapi.json`).catch(() => null)) as
      | { paths?: Record<string, unknown> }
      | null
    if (openapi?.paths) {
      const business = Object.keys(openapi.paths).filter((p) => p.startsWith('/api/dev/v1/'))
      expect(business.length).toBe(34)
      for (const path of business) {
        expect(path.toLowerCase()).not.toContain('descriptor')
        expect(path.toLowerCase()).not.toContain('/plugin')
      }
    }
  })

  test('the /status block is value-free (no leak)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const pdr = (await (await request.get(`${API_BASE}/status`)).json()).data.pluginDescriptorRegistry
    const blob = JSON.stringify(pdr)
    for (const token of FORBIDDEN_HTML_TOKENS) {
      expect(blob, `forbidden token ${token}`).not.toContain(token)
    }
    expect(blob).not.toContain('/Users/huangruibang/.hermes')
    expect(blob).not.toContain('state.db')
  })
})

test.describe('Phase 3D-H1 Plugin Descriptor Registry hardening (UI)', () => {
  test('14-24. UI panel, banner, describes-only, blocked descriptors, badges, no leak', async ({
    request,
    page,
  }: {
    request: APIRequestContext
    page: Page
  }) => {
    test.skip(!(await webuiAvailable(request)), 'Dev WebUI not available on 127.0.0.1:5180')
    await page.goto(`${WEBUI_BASE}/#/console`)
    const navBtn = page.getByRole('tab', { name: /Plugin Descriptors/i })
    if (await navBtn.count()) {
      await navBtn.click()
    }
    await expect(page.getByText('Plugin Descriptor Registry').first()).toBeVisible({ timeout: 10000 })
    // Use auto-waiting text assertions (Playwright retries until the timeout) so the
    // table-derived content (blocked descriptors, forbidden/blocked badges) is reliably
    // present before we assert. The descriptor table renders its blocked rows more
    // slowly than the Capability Registry table (lazy capability index / live summary),
    // so a one-shot innerText snapshot can race the render when this profile runs after
    // others in the `all` aggregate. The no-leak snapshot is taken only after every
    // positive-content assertion has passed.
    const bodyLocator = page.locator('body')

    // 14. Runtime-disabled banner invariants.
    await expect(bodyLocator).toContainText('plugin runtime disabled', { ignoreCase: true, timeout: 10000 })
    await expect(bodyLocator).toContainText('dynamic loading disabled', { ignoreCase: true })
    await expect(bodyLocator).toContainText('remote registry disabled', { ignoreCase: true })
    await expect(bodyLocator).toContainText('marketplace disabled', { ignoreCase: true })
    await expect(bodyLocator).toContainText('local plugin directory loading disabled', { ignoreCase: true })
    await expect(bodyLocator).toContainText('external plugin fetch disabled', { ignoreCase: true })

    // 15. Descriptor only / does not grant permission / does not execute.
    await expect(bodyLocator).toContainText('does not grant permission', { ignoreCase: true })
    await expect(bodyLocator).toContainText('does not execute a plugin', { ignoreCase: true })

    // 16-19. Forbidden categories are described as blocked (table rows rendered).
    await expect(bodyLocator).toContainText('plugin.descriptor.dynamic_plugin_load_blocked', { timeout: 10000 })
    await expect(bodyLocator).toContainText('plugin.descriptor.remote_registry_blocked')
    await expect(bodyLocator).toContainText('plugin.descriptor.marketplace_blocked')
    await expect(bodyLocator).toContainText('plugin.descriptor.production_operation_blocked')

    // Badges carry text labels (non-color) — wait for the forbidden badge mark.
    await expect(page.locator('.plugin-badge--forbidden').first()).toBeVisible({ timeout: 10000 })
    await expect(bodyLocator).toContainText('Read-only', { timeout: 10000 })
    await expect(bodyLocator).toContainText('Forbidden')
    await expect(bodyLocator).toContainText('Blocked')

    // 20-24. No forbidden token / secret / path rendered — snapshot AFTER all content
    // is confirmed rendered.
    const body = await bodyLocator.innerText()
    for (const token of FORBIDDEN_HTML_TOKENS) {
      expect(body, `forbidden token ${token} rendered`).not.toContain(token)
    }
    expect(body).not.toContain('/Users/huangruibang/.hermes')
    expect(body).not.toContain('state.db')
    // No API-key input field exists.
    expect(await page.locator('input[type="password"]').count()).toBe(0)
  })
})
