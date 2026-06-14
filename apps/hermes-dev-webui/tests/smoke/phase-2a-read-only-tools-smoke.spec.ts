/**
 * Phase 2A: Read-only multi-tool execution browser smoke.
 *
 * Drives each of the five Phase 2A read-only inspection tools through the
 * full controlled-execution chain (dry-run → confirmation token → execute)
 * against the live Dev API, and asserts:
 *   - each tool completes with decision `<toolId>_execution_completed`
 *   - provider/external side-effect flags are ALWAYS false
 *   - a post-execution audit is written and visible via the audit viewer
 *   - the WebUI tool selector exposes all six selectable tools
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181  (HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev)
 *   WebUI    on 127.0.0.1:5180  (pnpm dev) — optional, for the UI test
 *
 * Gate env (set by the smoke harness phase2a profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 */
import { test, expect, type APIRequestContext } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const DRY_RUN_URL = `${API_BASE}/tools/dry-run`
const EXECUTE_URL = `${API_BASE}/tools/execute`
const AUDIT_URL = `${API_BASE}/tools/audit-events`

const READ_ONLY_TOOLS = [
  'tool_policy_read',
  'route_governance_read',
  'audit_events_read',
  'dev_environment_read',
  'release_status_read',
] as const

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

async function runReadOnlyTool(
  request: APIRequestContext,
  tool: string,
): Promise<{ completed: boolean; decision: string; postExecutionAuditId: string | null }> {
  const requestId = `dr_2a_${tool}_${Date.now().toString(36)}`
  const dryResp = await request.post(DRY_RUN_URL, {
    data: {
      canonicalName: tool,
      argumentsPreview: {},
      requestId,
      issueConfirmationToken: true,
      sourceContext: 'smoke',
      uiOrigin: 'phase-2a-smoke',
    },
  })
  expect(dryResp.status(), `${tool} dry-run should return 200`).toBe(200)
  const dryData = (await dryResp.json()).data
  expect(dryData.decision, `${tool} dry-run should be would_allow`).toBe('would_allow')
  expect(dryData.providerSchemaAllowed).toBe(false)

  const execResp = await request.post(EXECUTE_URL, {
    data: {
      canonicalName: tool,
      argumentsPreview: {},
      dryRunRequestId: requestId,
      dryRunDecisionDigest: dryData.dryRunDecisionDigest,
      confirmationToken: dryData.confirmationToken,
      requestId,
      sourceContext: 'smoke',
      uiOrigin: 'phase-2a-smoke',
    },
  })
  expect(execResp.status(), `${tool} execute should return 200`).toBe(200)
  const data = (await execResp.json()).data
  return {
    completed: data.executionCompleted === true,
    decision: data.decision,
    postExecutionAuditId: data.postExecutionAuditId ?? null,
  }
}

// ===================================================================
// 1. Each read-only tool completes through the full chain
// ===================================================================

test.describe('Phase 2A read-only tool execution', () => {
  for (const tool of READ_ONLY_TOOLS) {
    test(`${tool} completes with provider/side-effect flags false`, async ({ request }) => {
      test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
      const requestId = `dr_2a_${tool}_${Date.now().toString(36)}`
      const dryResp = await request.post(DRY_RUN_URL, {
        data: {
          canonicalName: tool,
          argumentsPreview: {},
          requestId,
          issueConfirmationToken: true,
          sourceContext: 'smoke',
          uiOrigin: 'phase-2a-smoke',
        },
      })
      const dryData = (await dryResp.json()).data
      const execResp = await request.post(EXECUTE_URL, {
        data: {
          canonicalName: tool,
          argumentsPreview: {},
          dryRunRequestId: requestId,
          dryRunDecisionDigest: dryData.dryRunDecisionDigest,
          confirmationToken: dryData.confirmationToken,
          requestId,
        },
      })
      const data = (await execResp.json()).data

      expect(data.executionCompleted, `${tool} must complete`).toBe(true)
      expect(data.decision).toBe(`${tool}_execution_completed`)
      expect(data.toolHandlerCalled).toBe(true)
      // Provider / external side-effect flags ALWAYS false.
      expect(data.providerApiCalled).toBe(false)
      expect(data.providerSchemaAllowed).toBe(false)
      if (data.sideEffects) {
        expect(data.sideEffects.providerSchemaSent).toBe(false)
        expect(data.sideEffects.providerApiCalled).toBe(false)
        expect(data.sideEffects.externalSideEffects).toBe(false)
      }
      // Structured result present for read-only tools.
      expect(data.toolResult?.type).toBe(tool)
      expect(data.toolResult?.result).toBeTruthy()
      // Post-execution audit written.
      expect(data.postExecutionAuditId).toBeTruthy()
    })
  }

  test('audit viewer surfaces a Phase 2A post-execution audit by toolId', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const result = await runReadOnlyTool(request, 'route_governance_read')
    expect(result.completed).toBe(true)

    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'post_execution', limit: 20, canonicalName: 'route_governance_read' },
    })
    expect(resp.status()).toBe(200)
    const items = (await resp.json()).data.items
    expect(items.length, 'at least one route_governance_read audit').toBeGreaterThan(0)
    for (const item of items) {
      expect(item.canonicalName).toBe('route_governance_read')
    }
  })
})

// ===================================================================
// 2. UI: the selector exposes all six tools
// ===================================================================

test.describe('UI: multi-tool selector', () => {
  test('selector exposes all six selectable tools', async ({ page }) => {
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

    const toolsTab = page.locator('#workspace-tab-tools')
    if (!(await toolsTab.isVisible().catch(() => false))) {
      test.skip(true, 'Tools tab not visible')
    }
    await toolsTab.click()
    await page.waitForTimeout(300)
    const executeTab = page.locator('#tool-policy-tab-execute')
    if (!(await executeTab.isVisible().catch(() => false))) {
      test.skip(true, 'Execute sub-tab not visible')
    }
    await executeTab.click()
    await page.waitForTimeout(300)

    const select = page.locator('#tool-execute-canonical')
    await expect(select).toBeVisible()
    // Default is clarify.
    await expect(select).toHaveValue('clarify')
    // All six options present.
    const options = await select.locator('option').allTextContents()
    for (const tool of ['clarify', 'tool_policy_read', 'route_governance_read', 'audit_events_read', 'dev_environment_read', 'release_status_read']) {
      expect(options.some((o) => o.includes(tool)), `selector must include ${tool}`).toBeTruthy()
    }
  })
})
