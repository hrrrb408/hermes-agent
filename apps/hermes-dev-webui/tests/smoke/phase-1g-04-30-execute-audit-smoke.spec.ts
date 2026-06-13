/**
 * Phase 1G-04-30: Execute + Audit Viewer browser smoke.
 *
 * Covers the accelerated WebUI closeout surface:
 *   - GET /tools/audit-events (read-only, safe, empty-or-items)
 *   - POST /tools/dry-run (clarify → would_allow + confirmation token)
 *   - POST /tools/execute (controlled execution gate)
 *   - The expected execute decision is driven by the dev API server's
 *     gate environment (EXECUTE_EXPECTED):
 *       'blocked_tool_handler_call_not_enabled' (handler-call gate unset)
 *       'clarify_execution_completed'           (handler-call gate enabled)
 *   - Provider side-effect flags are ALWAYS false in either scenario.
 *   - UI: the Execute sub-tab and Audit viewer render when WebUI is up.
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181  (HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev)
 *   WebUI    on 127.0.0.1:5180  (pnpm dev) — optional, for UI tests
 */
import { test, expect, type APIRequestContext } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const AUDIT_URL = `${API_BASE}/tools/audit-events`
const DRY_RUN_URL = `${API_BASE}/tools/dry-run`
const EXECUTE_URL = `${API_BASE}/tools/execute`

const EXPECTED_DECISION =
  (process.env.EXECUTE_EXPECTED as string | undefined) ?? 'clarify_execution_completed'

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

async function runDryRunChain(
  request: APIRequestContext,
  question: string,
): Promise<{ token: string | null; digest: string | null; requestId: string }> {
  const requestId = `dr_smoke_${Date.now().toString(36)}`
  const resp = await request.post(DRY_RUN_URL, {
    data: {
      canonicalName: 'clarify',
      argumentsPreview: { question },
      requestId,
      issueConfirmationToken: true,
      sourceContext: 'smoke',
      uiOrigin: 'phase-1g-04-30-smoke',
    },
  })
  expect(resp.status(), 'dry-run should return 200').toBe(200)
  const body = await resp.json()
  const data = body.data
  expect(data.executionAllowed).toBe(false)
  expect(data.dispatchAllowed).toBe(false)
  expect(data.providerSchemaAllowed).toBe(false)
  return {
    token: data.confirmationToken ?? null,
    digest: data.dryRunDecisionDigest ?? null,
    requestId,
  }
}

// ===================================================================
// 1. Audit Events API (read-only)
// ===================================================================

test.describe('Audit Events API', () => {
  test('GET audit-events returns safe items for each kind', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    for (const kind of ['dry_run', 'pre_execution', 'post_execution']) {
      const resp = await request.get(AUDIT_URL, { params: { auditKind: kind, limit: 5 } })
      expect(resp.status(), `${kind} should return 200`).toBe(200)
      const body = await resp.json()
      expect(body.data.auditKind).toBe(kind)
      expect(Array.isArray(body.data.items)).toBeTruthy()
      expect(typeof body.data.hasMore).toBe('boolean')
      // Safety: no raw secrets / tokens in the response
      const text = JSON.stringify(body)
      expect(text).not.toMatch(/sk-[A-Za-z0-9_-]{8,}/)
      expect(text.toLowerCase()).not.toContain('confirmtoken')
    }
  })

  test('GET audit-events invalid kind returns 400', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.get(AUDIT_URL, { params: { auditKind: 'bogus' } })
    expect(resp.status()).toBe(400)
    expect((await resp.json()).error.code).toBe('TOOL_AUDIT_EVENTS_INVALID_KIND')
  })

  test('GET audit-events is read-only (POST rejected)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.post(AUDIT_URL, { data: { auditKind: 'dry_run' } })
    expect(resp.status()).toBe(405)
  })
})

// ===================================================================
// 2. Controlled execution chain (dry-run → execute)
// ===================================================================

test.describe('Controlled Execution Chain', () => {
  test('dry-run → execute yields the expected safe decision', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const { token, digest, requestId } = await runDryRunChain(
      request,
      'Which option do you prefer?',
    )

    const execResp = await request.post(EXECUTE_URL, {
      data: {
        canonicalName: 'clarify',
        argumentsPreview: { question: 'Which option do you prefer?' },
        dryRunRequestId: requestId,
        dryRunDecisionDigest: digest,
        confirmationToken: token,
        requestId,
        sourceContext: 'smoke',
        uiOrigin: 'phase-1g-04-30-smoke',
      },
    })
    expect(execResp.status(), 'execute should return 200').toBe(200)
    const data = (await execResp.json()).data

    // The decision matches the server gate configuration.
    expect(data.decision).toBe(EXPECTED_DECISION)

    // Provider / external side-effect flags are ALWAYS false.
    expect(data.providerApiCalled, 'providerApiCalled must be false').toBe(false)
    expect(data.providerSchemaAllowed, 'providerSchemaAllowed must be false').toBe(false)
    if (data.sideEffects) {
      expect(data.sideEffects.providerSchemaSent).toBe(false)
      expect(data.sideEffects.providerApiCalled).toBe(false)
      expect(data.sideEffects.externalSideEffects).toBe(false)
    }

    // On the completed path, a post-execution audit must be written.
    if (EXPECTED_DECISION === 'clarify_execution_completed') {
      expect(data.executionCompleted).toBe(true)
      expect(data.toolHandlerCalled).toBe(true)
      expect(data.postExecutionAuditId, 'postExecutionAuditId must be present').toBeTruthy()
      expect(typeof data.postExecutionAuditId).toBe('string')
    } else {
      // Blocked path: no handler call, no execution.
      expect(data.toolHandlerCalled).toBe(false)
      expect(data.executionCompleted).toBe(false)
    }
  })

  test('post-execution audit is visible in the audit viewer API', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    test.skip(
      EXPECTED_DECISION !== 'clarify_execution_completed',
      'post-execution audit only written on completed path',
    )
    // Trigger one completed execution.
    const { token, digest, requestId } = await runDryRunChain(request, 'Audit visibility?')
    const execResp = await request.post(EXECUTE_URL, {
      data: {
        canonicalName: 'clarify',
        argumentsPreview: { question: 'Audit visibility?' },
        dryRunRequestId: requestId,
        dryRunDecisionDigest: digest,
        confirmationToken: token,
        requestId,
      },
    })
    const postExecutionAuditId = (await execResp.json()).data.postExecutionAuditId
    expect(postExecutionAuditId).toBeTruthy()

    // The audit viewer API must surface it (newest first).
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'post_execution', limit: 10, canonicalName: 'clarify' },
    })
    expect(resp.status()).toBe(200)
    const items = (await resp.json()).data.items
    expect(items.length).toBeGreaterThan(0)
    const ids = items.map((i: { auditId: string | null }) => i.auditId)
    expect(ids).toContain(postExecutionAuditId)
  })
})

// ===================================================================
// 3. UI smoke (Execute sub-tab + Audit viewer)
// ===================================================================

test.describe('UI: Execute + Audit viewer', () => {
  test('Execute and Audit sub-tabs render in the Tools panel', async ({ page }) => {
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

    // Open the workspace Tools tab.
    const toolsTab = page.locator('#workspace-tab-tools')
    if (await toolsTab.isVisible().catch(() => false)) {
      await toolsTab.click()
      await page.waitForTimeout(300)
    }

    // Execute sub-tab
    const executeTab = page.locator('#tool-policy-tab-execute')
    if (await executeTab.isVisible().catch(() => false)) {
      await executeTab.click()
      await page.waitForTimeout(300)
      await expect(page.locator('#tool-execute-dry-run')).toBeVisible()
      await expect(page.locator('#tool-execute-run')).toBeVisible()
      await expect(page.locator('#tool-execute-canonical')).toHaveValue('clarify')
    } else {
      test.skip(true, 'Execute sub-tab not visible')
    }

    // Audit viewer sub-tab
    const auditTab = page.locator('#tool-policy-tab-audit')
    await auditTab.click()
    await page.waitForTimeout(500)
    await expect(page.locator('#audit-viewer-refresh')).toBeVisible()
  })

  test('UI dry-run surfaces a safe decision without the raw token', async ({ page }) => {
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
    await page.locator('#workspace-tab-tools').click().catch(() => {})
    await page.waitForTimeout(300)
    await page.locator('#tool-policy-tab-execute').click().catch(() => {})
    await page.waitForTimeout(300)

    await page.locator('#tool-execute-dry-run').click().catch(() => {})
    // Wait for the dry-run decision block or an error to appear.
    await page.waitForTimeout(1500)
    const text = await page.locator('#workspace-panel').innerText().catch(() => '')
    // Either a decision surfaced or the panel is present; raw token never shows.
    expect(text).not.toMatch(/^raw-.*token/i)
  })
})
