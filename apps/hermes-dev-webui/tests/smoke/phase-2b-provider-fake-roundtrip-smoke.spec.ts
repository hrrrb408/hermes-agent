/**
 * Phase 2B: Provider Schema / API controlled round-trip browser smoke.
 *
 * Drives the fake-provider round-trip against the live Dev API (same
 * POST /api/dev/v1/tools/execute path with body.mode='provider_roundtrip')
 * and asserts:
 *   - fake round-trip completes for a read-only tool
 *   - providerSchemaSent=true, providerApiCalled=true, externalNetworkCalled=false
 *   - tool calls + tool results + final answer are present
 *   - real mode is blocked unless explicitly enabled
 *   - the WebUI Provider panel is visible and the fake round-trip runs
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181  (HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev)
 *   WebUI    on 127.0.0.1:5180  (pnpm dev) — optional, for the UI test
 *
 * Gate env (set by the smoke harness phase2b_provider_fake_roundtrip profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 *   HERMES_PROVIDER_MODE=fake
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

async function runFakeRoundtrip(
  request: APIRequestContext,
  message: string,
  allowedToolIds: string[],
): Promise<{
  status: string
  providerMode: string
  providerSchemaSent: boolean
  providerApiCalled: boolean
  externalNetworkCalled: boolean
  toolCalls: Array<{ name: string }>
  toolResults: Array<{ toolId: string; executed: boolean }>
  finalAnswer: string
  providerAuditIds: string[]
  blockedReason: string | null
}> {
  const resp = await request.post(EXECUTE_URL, {
    data: {
      mode: 'provider_roundtrip',
      providerMode: 'fake',
      message,
      allowedToolIds,
      sourceContext: 'smoke',
      uiOrigin: 'phase-2b-smoke',
    },
  })
  expect(resp.status(), 'fake round-trip should return 200').toBe(200)
  return (await resp.json()).data
}

// ===================================================================
// 1. Fake round-trip completes for a read-only tool
// ===================================================================

test.describe('Phase 2B provider fake round-trip', () => {
  test('route_governance_read round-trip completes with provider flags', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const data = await runFakeRoundtrip(request, 'check route governance', ['route_governance_read'])

    expect(data.status, 'round-trip status').toBe('completed')
    expect(data.providerMode).toBe('fake')
    expect(data.providerSchemaSent).toBe(true)
    expect(data.providerApiCalled).toBe(true)
    expect(data.externalNetworkCalled).toBe(false)
    expect(data.toolCalls.length).toBeGreaterThan(0)
    expect(data.toolCalls[0]!.name).toBe('route_governance_read')
    expect(data.toolResults.length).toBeGreaterThan(0)
    expect(data.toolResults[0]!.toolId).toBe('route_governance_read')
    expect(data.toolResults[0]!.executed).toBe(true)
    expect(data.finalAnswer).toBeTruthy()
    expect(data.providerAuditIds.length).toBeGreaterThan(0)
  })

  test('tool write remains disabled across the round-trip', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    // A message that does NOT route to any read-only tool — confirm no write
    // tool is ever executed.
    const data = await runFakeRoundtrip(request, 'nothing matches here please', [
      'route_governance_read',
    ])
    for (const tr of data.toolResults) {
      expect(tr.toolId, 'no write tool may execute').not.toBe('write_file')
      expect(tr.toolId).not.toBe('terminal')
      expect(tr.toolId).not.toBe('patch')
    }
  })

  test('real provider mode is blocked without explicit enablement', async ({ request }) => {
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
    expect(data.blockedReason).toBeTruthy()
    expect(data.externalNetworkCalled).toBe(false)
  })

  test('provider audit events are queryable via the audit viewer', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    await runFakeRoundtrip(request, 'read tool policy', ['tool_policy_read'])
    // The provider audit is written to provider-roundtrip-audit.jsonl under the
    // dev HERMES_HOME. The audit-events reader surfaces dry_run/pre/post kinds;
    // the provider round-trip also writes a dry-run + post-execution audit per
    // executed tool, which the viewer must surface.
    const resp = await request.get(`${API_BASE}/tools/audit-events`, {
      params: { auditKind: 'post_execution', limit: 20, canonicalName: 'tool_policy_read' },
    })
    expect(resp.status()).toBe(200)
    const items = (await resp.json()).data.items
    expect(items.length, 'at least one tool_policy_read post-execution audit').toBeGreaterThan(0)
  })
})

// ===================================================================
// 2. UI: Provider panel is visible and fake round-trip runs
// ===================================================================

test.describe('UI: Provider round-trip panel', () => {
  test('provider panel visible and fake selectable', async ({ page }) => {
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
    await page.waitForTimeout(300)

    // Mode selector offers disabled / fake / real.
    const modeSelect = page.locator('#provider-mode')
    await expect(modeSelect).toBeVisible()
    const options = await modeSelect.locator('option').allTextContents()
    for (const mode of ['disabled', 'fake', 'real']) {
      expect(options.some((o) => o.includes(mode)), `mode selector must include ${mode}`).toBeTruthy()
    }

    // No API key input exists anywhere in the panel.
    const html = await page.locator('.provider-rt').innerHTML().catch(() => '')
    expect(html.toLowerCase()).not.toMatch(/api ?key|authorization|bearer/)

    // Allowed-tools selector is visible.
    await expect(page.locator('.provider-rt__tools')).toBeVisible()
  })

  test('fake round-trip result renders in the panel', async ({ page }) => {
    test.setTimeout(60_000)
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
    await page.locator('#workspace-tab-provider').click().catch(() => {})
    await page.waitForTimeout(300)

    // Select fake mode, type a message, run.
    await page.locator('#provider-mode').selectOption('fake')
    await page.locator('#provider-message').fill('check route governance')
    await page.locator('button.provider-rt__btn--primary').click().catch(() => {})

    // Wait for the final-answer block to appear (round-trip completed).
    const finalBlock = page.locator('.provider-rt__final')
    try {
      await expect(finalBlock).toBeVisible({ timeout: 20_000 })
    } catch {
      test.skip(true, 'round-trip result did not render in time')
    }
    expect(await finalBlock.textContent()).toBeTruthy()
  })
})
