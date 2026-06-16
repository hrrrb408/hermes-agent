/**
 * Phase 3B: Real Provider Read-only Boundary browser smoke.
 *
 * Exercises the fake provider + blocked-real mode ONLY. It NEVER enables the
 * real provider, NEVER sets an API key, and NEVER makes a real network call.
 *
 * Asserts:
 *   - fake round-trip completes (externalNetworkCalled=false)
 *   - real provider mode is blocked without enablement (externalNetworkCalled=false)
 *   - the /status providerBoundary block is surfaced (disabled / apiEnabled=false /
 *     realReachable=false / providerWriteBlocked=true) and carries no secret
 *   - the Provider panel renders the Phase 3B boundary status with the
 *     permanently-blocked flags + read-only allowlist
 *   - NO API-key input exists anywhere in the panel
 *
 * Gate env (set by the smoke harness phase3b_provider_readonly_boundary profile):
 *   HERMES_PROVIDER_MODE=fake
 *   (HERMES_PROVIDER_API_ENABLED intentionally UNSET — real stays disabled)
 */
import { test, expect, type APIRequestContext } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const EXECUTE_URL = `${API_BASE}/tools/execute`

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

// ===================================================================
// 1. Blocked-real path (no real provider, no key, no network)
// ===================================================================

test.describe('Phase 3B provider read-only boundary (API)', () => {
  test('real provider mode is blocked without enablement', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip',
        providerMode: 'real',
        message: 'x',
        allowedToolIds: ['route_governance_read'],
      },
    })
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    expect(data.status).toBe('blocked')
    expect(data.blockedReason).toBeTruthy()
    expect(data.externalNetworkCalled).toBe(false)
  })

  test('fake provider round-trip still works', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip',
        providerMode: 'fake',
        message: 'check route governance',
        allowedToolIds: ['route_governance_read'],
      },
    })
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    expect(data.status).toBe('completed')
    expect(data.externalNetworkCalled).toBe(false)
  })

  test('status surfaces the real-provider boundary block (no secret)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.get(`${API_BASE}/status`)
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    const boundary = data.providerBoundary
    expect(boundary).toBeTruthy()
    // Real provider disabled by default in this profile.
    expect(boundary.apiEnabled).toBe(false)
    expect(boundary.realReachable).toBe(false)
    expect(boundary.providerWriteBlocked).toBe(true)
    expect(boundary.providerAutoWriteBlocked).toBe(true)
    expect(boundary.autonomousWriteBlocked).toBe(true)
    expect(boundary.productionRolloutBlocked).toBe(true)
    // Value-free key marker only.
    expect(['env_present', 'env_missing']).toContain(boundary.apiKeySourceDetail)
    // No secret may appear in the boundary block.
    const blob = JSON.stringify(boundary)
    for (const needle of ['sk-', 'Bearer ', 'Authorization']) {
      expect(blob).not.toContain(needle)
    }
  })

  test('route governance unchanged — no provider-real route', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    // The OpenAPI is served at /openapi.json (no /api/dev/v1 prefix).
    const open = await request.get('http://127.0.0.1:5181/openapi.json')
    expect(open.status()).toBe(200)
    const paths = (await open.json()).paths
    expect(Object.keys(paths).length).toBe(34)
    for (const path of Object.keys(paths)) {
      expect(path).not.toMatch(/provider-real|provider\/real/)
    }
  })
})

// ===================================================================
// 2. UI: boundary status + no-leak
// ===================================================================

test.describe('UI: Phase 3B provider boundary', () => {
  test('boundary status visible with blocked flags + read-only allowlist', async ({ page }) => {
    test.setTimeout(45_000)
    try {
      await page.goto('/', { timeout: 6000 })
    } catch {
      test.skip(true, 'WebUI not available on 127.0.0.1:5180')
    }
    await page.evaluate(() => {
      localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle').catch(() => {})

    const providerTab = page.locator('#workspace-tab-provider')
    if (!(await providerTab.isVisible().catch(() => false))) {
      test.skip(true, 'Provider tab not visible')
    }
    await providerTab.click()
    await page.waitForTimeout(400)

    // The boundary status section renders.
    const boundary = page.locator('[data-testid="provider-boundary-status"]')
    await expect(boundary).toBeVisible({ timeout: 10_000 })

    // The permanently-blocked operations render.
    const html = await boundary.innerHTML()
    expect(html).toContain('Provider write')
    expect(html).toContain('Autonomous write')
    expect(html).toContain('Production rollout')

    // The read-only allowlist is visible.
    for (const tool of [
      'clarify', 'tool_policy_read', 'route_governance_read',
      'audit_events_read', 'dev_environment_read', 'release_status_read',
    ]) {
      expect(html).toContain(tool)
    }

    // No API-key input, no Authorization / Bearer / raw token anywhere.
    const lowered = html.toLowerCase()
    expect(lowered).not.toMatch(/api ?key|authorization|bearer|sk-/)
    expect(await page.locator('input[type="password"]').count()).toBe(0)
  })
})
