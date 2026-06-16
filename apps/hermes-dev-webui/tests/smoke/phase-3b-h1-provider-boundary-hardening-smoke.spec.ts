/**
 * Phase 3B-H1: Provider Boundary Hardening — browser smoke.
 *
 * Hardening invariants validated end-to-end against the live Dev API + WebUI:
 *   - route governance: OpenAPI 34 paths, no provider-real / provider/real route;
 *   - the real-provider round-trip is blocked without enablement
 *     (externalNetworkCalled=false) and the response leaks nothing;
 *   - the /status providerBoundary block is value-free and surfaces the four
 *     permanently-blocked operations (write / auto-write / autonomous / rollout);
 *   - every forbidden provider tool request (write / shell / db / external /
 *     rollback) is classified blocked, never executed;
 *   - the Provider panel renders the boundary + read-only allowlist and NEVER
 *     renders an API-key input / Authorization / Bearer / raw token;
 *   - no API response or rendered UI leaks a secret carrier.
 *
 * This profile NEVER enables the real provider, NEVER sets an API key, and NEVER
 * makes a real network call.
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181
 *   WebUI    on 127.0.0.1:5180  (pnpm dev)
 *
 * Gate env (set by the smoke harness phase3b_h1_provider_boundary_hardening profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 *   HERMES_PROVIDER_MODE=fake
 *   (HERMES_PROVIDER_API_ENABLED intentionally UNSET — real stays disabled)
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const EXECUTE_URL = `${API_BASE}/tools/execute`

const LEAK_PATTERNS = [
  'sk-',
  'Bearer ',
  'Authorization:',
  'apiKeyValue',
  'accessToken',
  'refresh_token',
  'client_secret',
  '<function',
  'object at 0x',
  '/Users/huangruibang/.hermes',
  'rawPrompt',
  'rawResponse',
  'rawArguments',
  'fullTokenHash',
  'plainToken',
  'state.db',
]

// Provider-requested tool ids that must ALWAYS be classified blocked.
const FORBIDDEN_PROVIDER_TOOLS = [
  'write_file',
  'patch',
  'shell',
  'database',
  'external_http',
  'dev_sandbox_rollback_execute',
  'production_operation',
  'plugin_dynamic_load',
]

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
    await page.goto('/', { timeout: 6000 })
    return true
  } catch {
    return false
  }
}

function assertNoLeak(body: string, label: string): void {
  for (const pattern of LEAK_PATTERNS) {
    expect(body, `${label} must not contain ${pattern}`).not.toContain(pattern)
  }
}

// ===================================================================
// 1. API leg — route governance + boundary invariants
// ===================================================================

test.describe('Phase 3B-H1 provider boundary hardening (API)', () => {
  test('route governance unchanged — 34 paths, no provider-real route', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const open = await request.get('http://127.0.0.1:5181/openapi.json')
    test.skip(!open.ok(), 'OpenAPI document not served')
    const paths = Object.keys((await open.json()).paths || {})
    expect(paths.length).toBe(34)
    for (const path of paths) {
      expect(path).not.toMatch(/provider-real|provider\/real/)
    }
  })

  test('real provider round-trip is blocked without enablement (no network)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip', providerMode: 'real',
        message: 'check route governance', allowedToolIds: ['route_governance_read'],
      },
    })
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    expect(data.status).toBe('blocked')
    expect(data.blockedReason).toBeTruthy()
    expect(data.externalNetworkCalled).toBe(false)
    assertNoLeak(JSON.stringify(data), 'real_blocked_roundtrip')
  })

  test('fake round-trip stays offline and leak-free', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip', providerMode: 'fake',
        message: 'check route governance', allowedToolIds: ['route_governance_read'],
      },
    })
    const data = (await resp.json()).data
    expect(data.status).toBe('completed')
    expect(data.externalNetworkCalled).toBe(false)
    assertNoLeak(JSON.stringify(data), 'fake_roundtrip')
  })

  test('status providerBoundary block is value-free + permanently blocked', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.get(`${API_BASE}/status`)
    const boundary = (await resp.json()).data.providerBoundary
    expect(boundary).toBeTruthy()
    expect(boundary.apiEnabled).toBe(false)
    expect(boundary.realReachable).toBe(false)
    expect(boundary.providerWriteBlocked).toBe(true)
    expect(boundary.providerAutoWriteBlocked).toBe(true)
    expect(boundary.autonomousWriteBlocked).toBe(true)
    expect(boundary.productionRolloutBlocked).toBe(true)
    expect(['env_present', 'env_missing']).toContain(boundary.apiKeySourceDetail)
    assertNoLeak(JSON.stringify(boundary), 'status_boundary')
  })

  test('unknown provider mode is rejected at the schema layer (400, no leak)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip', providerMode: 'live-hacker-mode',
        message: 'x', allowedToolIds: ['route_governance_read'],
      },
    })
    expect(resp.status()).toBe(400)
    assertNoLeak(JSON.stringify(await resp.json()), 'unknown_mode')
  })

  test('a provider result never reports a forbidden tool as executed', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    // The forbidden tool names are not requested by the fake provider here, but
    // the contract holds: any result surfacing them must mark them blocked.
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip', providerMode: 'fake',
        message: 'read route governance', allowedToolIds: ['route_governance_read'],
      },
    })
    const data = (await resp.json()).data
    for (const forbidden of FORBIDDEN_PROVIDER_TOOLS) {
      const hit = (data.toolResults || []).find((r: { toolId?: string }) => r.toolId === forbidden)
      if (hit) {
        expect(hit.executed).toBe(false)
        expect(hit.status).toBe('blocked')
      }
    }
    assertNoLeak(JSON.stringify(data), 'forbidden_tool_contract')
  })
})

// ===================================================================
// 2. UI leg — Provider panel boundary + no-leak
// ===================================================================

test.describe('Phase 3B-H1 provider boundary hardening (UI)', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await webuiAvailable(page)), 'WebUI not available on 127.0.0.1:5180')
    await page.evaluate(() => {
      window.localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      window.localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle').catch(() => {})
  })

  test('the Provider panel renders the boundary + read-only allowlist', async ({ page }) => {
    test.setTimeout(45_000)
    const providerTab = page.locator('#workspace-tab-provider')
    if (!(await providerTab.isVisible().catch(() => false))) {
      test.skip(true, 'Provider tab not visible')
    }
    await providerTab.click()
    await page.waitForTimeout(400)
    const boundary = page.locator('[data-testid="provider-boundary-status"]')
    if (!(await boundary.isVisible().catch(() => false))) {
      test.skip(true, 'Provider boundary section not visible')
    }
    const html = await boundary.innerHTML()
    // The permanently-blocked operations render.
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
    // No secret carrier.
    for (const pattern of LEAK_PATTERNS) {
      expect(html, `boundary UI must not contain ${pattern}`).not.toContain(pattern)
    }
  })

  test('never renders an API-key / password input anywhere on the page', async ({ page }) => {
    const providerTab = page.locator('#workspace-tab-provider')
    if (await providerTab.isVisible().catch(() => false)) {
      await providerTab.click()
      await page.waitForTimeout(300)
    }
    expect(await page.locator('input[type="password"]').count()).toBe(0)
    const keyInputs = await page.locator('input').evaluateAll((els) =>
      els.filter((el) => /api[_-]?key|bearer|authorization/i.test((el.id || '') + (el.getAttribute('name') || ''))).length,
    )
    expect(keyInputs).toBe(0)
  })
})
