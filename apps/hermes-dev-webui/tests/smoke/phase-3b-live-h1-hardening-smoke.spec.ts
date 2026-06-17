/**
 * Phase 3B-Live-Enablement H1: strict manual one-shot live gate HARDENING smoke.
 *
 * Hardening pass over the live boundary (HARDENING-3B-LIVE-H1-001). It exercises
 * the live gate ONLY in its blocked / default state. It NEVER enables the real
 * provider, NEVER sets an API key, NEVER issues a live approval, and NEVER makes
 * a real network call.
 *
 * Asserts the hardening invariants:
 *   - live status visible + disabled by default + approval-required
 *   - kill switch inactive by default
 *   - real-mode round-trip with NO approval is blocked (externalNetworkCalled=false)
 *   - a round-trip is also blocked under a disabled mode + missing approval
 *   - the frozen caps render (1 / 1000 / 200 / 5c / 0 retry) with fail-closed flag
 *   - provider write / autonomous / streaming / multi-provider stay blocked
 *   - the live block is value-free (no API-key input, no Authorization / Bearer)
 *   - route governance unchanged (34 paths, no provider_live route)
 *
 * Gate env (set by the smoke harness phase3b_live_h1_hardening profile):
 *   HERMES_PROVIDER_MODE=fake (HERMES_PROVIDER_API_ENABLED intentionally UNSET)
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

test.describe('Phase 3B-Live-Enablement H1 hardening (API)', () => {
  test('live gate disabled + approval-required + kill switch inactive', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const live = (await (await request.get(`${API_BASE}/status`)).json()).data.providerBoundary
      .providerLive
    expect(live.liveEnabled).toBe(false)
    expect(live.approvalRequired).toBe(true)
    expect(live.killSwitchActive).toBe(false)
    expect(live.toolExecutionDisabled).toBe(true)
    expect(live.manualOneShot).toBe(false)
  })

  test('permanently blocked flags hold', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const live = (await (await request.get(`${API_BASE}/status`)).json()).data.providerBoundary
      .providerLive
    expect(live.providerWriteBlocked).toBe(true)
    expect(live.autonomousWriteBlocked).toBe(true)
    expect(live.productionRolloutBlocked).toBe(true)
    expect(live.streamingBlocked).toBe(true)
    expect(live.multiProviderBlocked).toBe(true)
  })

  test('frozen caps render with fail-closed flag', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const b = (await (await request.get(`${API_BASE}/status`)).json()).data.providerBoundary
      .providerLive.budget
    expect(b.maxRequests).toBe(1)
    expect(b.maxTotalTokens).toBe(1000)
    expect(b.maxOutputTokens).toBe(200)
    expect(b.maxBudgetCents).toBe(5)
    expect(b.maxRetries).toBe(0)
    expect(b.failClosedOnCounterError).toBe(true)
  })

  test('real-mode round-trip blocked without approval (no network)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
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
    expect(data.externalNetworkCalled).toBe(false)
    expect(data.blockedReason).toBeTruthy()
  })

  test('live block carries no secret value', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const live = (await (await request.get(`${API_BASE}/status`)).json()).data.providerBoundary
      .providerLive
    const blob = JSON.stringify(live)
    for (const needle of ['sk-', 'Bearer ', 'Authorization']) {
      expect(blob).not.toContain(needle)
    }
  })

  test('route governance unchanged — no provider_live route', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const open = await request.get('http://127.0.0.1:5181/openapi.json')
    expect(open.status()).toBe(200)
    const paths = (await open.json()).paths
    expect(Object.keys(paths).length).toBe(34)
    for (const path of Object.keys(paths)) {
      expect(path).not.toMatch(/provider_live|provider-live|live-approval|live-roundtrip/)
    }
  })
})

test.describe('UI: Phase 3B-Live-Enablement H1 hardening', () => {
  test('live status visible, disabled, no API-key input, no leak', async ({ page }) => {
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

    const live = page.locator('[data-testid="provider-live-status"]')
    await expect(live).toBeVisible({ timeout: 10_000 })
    const html = (await live.innerHTML()).toLowerCase()
    expect(html).toContain('live provider enablement')
    expect(html).toContain('approval')
    expect(html).not.toMatch(/api ?key|authorization|bearer|sk-/)
    expect(await page.locator('input[type="password"]').count()).toBe(0)
  })
})
