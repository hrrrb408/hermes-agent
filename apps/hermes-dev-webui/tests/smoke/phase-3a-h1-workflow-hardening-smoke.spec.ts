/**
 * Phase 3A-H1: Workflow hardening — browser smoke.
 *
 * Hardening invariants validated end-to-end against the live Dev API + WebUI:
 *   - route governance: the workflow modes ride ONLY on /tools/dry-run and
 *     /tools/execute (no /workflows, no /provider path);
 *   - every forbidden step type is blocked at the API with a blocked_workflow_
 *     reason;
 *   - the sandbox-write step NEVER executes a write and the rollback-reference
 *     step NEVER executes a rollback;
 *   - the approval is single-use (a replayed token is rejected);
 *   - no API response or rendered UI leaks a secret / raw token / full hash /
 *     raw argument / callable repr / production path.
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181
 *   WebUI    on 127.0.0.1:5180  (pnpm dev)
 *
 * Gate env (set by the smoke harness phase3a_h1_workflow_hardening profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 *   HERMES_PROVIDER_MODE=fake
 *   HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const CONSOLE_URL = 'http://127.0.0.1:5180/#/console'

const LEAK_PATTERNS = [
  'sk-',
  'Bearer ',
  '<function',
  'object at 0x',
  '/Users/huangruibang/.hermes',
  'rawArguments',
  'fullTokenHash',
  'plainToken',
  'tokenSecret',
  'state.db',
]

const FORBIDDEN_STEP_TYPES = [
  'real_provider_roundtrip',
  'provider_write_execute',
  'sandbox_write_execute',
  'rollback_execute',
  'shell_command',
  'database_mutation',
  'external_http_request',
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
    await page.goto(CONSOLE_URL, { timeout: 6000 })
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

async function postJson(request: APIRequestContext, path: string, body: unknown) {
  return request.post(`${API_BASE}${path}`, { data: body })
}

// ===================================================================
// 1. API leg — route governance + hardening invariants
// ===================================================================

test.describe('Phase 3A-H1 — workflow hardening (API)', () => {
  test('OpenAPI exposes no /workflows or /provider route path', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.get(`${API_BASE}/../openapi.json`)
    test.skip(!resp.ok(), 'OpenAPI document not served')
    const spec = await resp.json()
    const paths = Object.keys(spec.paths || {}).filter((p: string) => p.startsWith('/api/dev/v1'))
    for (const path of paths) {
      expect(path, `unexpected workflow route: ${path}`).not.toContain('/workflows')
      expect(path, `unexpected provider route: ${path}`).not.toMatch(/\/provider\//)
    }
  })

  test('every forbidden step type is blocked with a blocked_workflow_ reason', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    for (const stepType of FORBIDDEN_STEP_TYPES) {
      const resp = await postJson(request, '/tools/dry-run', {
        mode: 'workflow_plan_preview', title: 'bad', steps: [{ stepType }],
      })
      const data = (await resp.json()).data
      expect(data.steps.length, stepType).toBe(0)
      expect(data.blockedSteps[0].blockedReason, stepType).toMatch(/^blocked_workflow_/)
      assertNoLeak(await resp.text(), `forbidden:${stepType}`)
    }
  })

  test('write preview + rollback reference never execute; approval is single-use', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const plan = await postJson(request, '/tools/dry-run', {
      mode: 'workflow_plan_preview', title: 'harden',
      steps: [
        { stepType: 'read_only_tool', toolId: 'dev_environment_read' },
        { stepType: 'sandbox_write_preview', toolId: 'dev_sandbox_file_write', targetRelativePath: 'wf/harden.md', content: 'c' },
        { stepType: 'rollback_reference' },
      ],
    })
    const pData = (await plan.json()).data
    const wfx = pData.workflowExecutionId

    // Execute without approval is blocked.
    const noToken = await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[0].stepId })
    expect(noToken.status()).toBe(400)

    // Step 0 (read-only) preview → approve → execute; replay rejected.
    const pv0 = (await (await postJson(request, '/tools/dry-run', { mode: 'workflow_step_preview', workflowExecutionId: wfx, stepId: pData.steps[0].stepId })).json()).data
    expect(pv0.approvalId).toMatch(/^cft_/)
    const ex0 = await (await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[0].stepId, approvalToken: pv0.approvalToken })).json()
    expect(ex0.data.result.type).toBe('dev_environment_read')
    const replay = await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[0].stepId, approvalToken: pv0.approvalToken })
    expect(replay.status()).toBe(400)

    // Step 1 (write preview) NEVER writes.
    const pv1 = (await (await postJson(request, '/tools/dry-run', { mode: 'workflow_step_preview', workflowExecutionId: wfx, stepId: pData.steps[1].stepId })).json()).data
    const ex1 = await (await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[1].stepId, approvalToken: pv1.approvalToken })).json()
    expect(ex1.data.result.workflowWriteExecuted).toBe(false)
    expect(ex1.data.result.autoWriteBlocked).toBe(true)
    assertNoLeak(JSON.stringify(ex1), 'write_preview_execute')

    // Step 2 (rollback reference) NEVER rolls back.
    const pv2 = (await (await postJson(request, '/tools/dry-run', { mode: 'workflow_step_preview', workflowExecutionId: wfx, stepId: pData.steps[2].stepId })).json()).data
    const ex2 = await (await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[2].stepId, approvalToken: pv2.approvalToken })).json()
    expect(ex2.data.result.workflowRollbackExecuted).toBe(false)
    expect(ex2.data.executionStatus).toBe('completed')
  })

  test('unsafe path + secret carriers never leak in a plan response', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await postJson(request, '/tools/dry-run', {
      mode: 'workflow_plan_preview', title: 'leak',
      steps: [{
        stepType: 'sandbox_write_preview', toolId: 'dev_sandbox_file_write',
        targetRelativePath: '/etc/passwd', content: 'c',
        apiKey: 'k', rawArguments: { x: 1 }, fullTokenHash: 'h',
      }],
    })
    const data = (await resp.json()).data
    expect(data.steps.length).toBe(0)
    assertNoLeak(JSON.stringify(data), 'unsafe_path_plan')
  })
})

// ===================================================================
// 2. UI leg — the Workflow console section stays leak-free
// ===================================================================

test.describe('Phase 3A-H1 — workflow hardening (UI)', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await webuiAvailable(page)), 'WebUI not available on 127.0.0.1:5180')
    await page.evaluate(() => {
      window.localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      window.localStorage.setItem('hermes-dev-webui.follow-system', 'false')
      window.localStorage.removeItem('hermes-dev-webui.devconsole.section')
    })
    await page.goto(CONSOLE_URL)
    await page.waitForLoadState('networkidle').catch(() => {})
  })

  test('the Workflow section renders every high-risk capability as Blocked', async ({ page }) => {
    await page.locator('#devconsole-nav-workflow').click()
    await page.waitForTimeout(200)
    const boundary = await page.locator('[data-testid="dev-workflow-safety-boundary"]').textContent()
    expect(boundary).toContain('Real provider')
    expect(boundary).toContain('Blocked')
    expect(boundary).toContain('Allowed')
  })

  test('building a plan keeps the rendered DOM leak-free', async ({ page }) => {
    await page.locator('#devconsole-nav-workflow').click()
    await page.waitForTimeout(200)
    await expect(page.locator('[data-testid="dev-workflow-build-plan-btn"]')).toBeVisible()
    await page.locator('[data-testid="dev-workflow-build-plan-btn"]').click()
    await page.waitForTimeout(500)
    const html = await page.locator('.devconsole__content').innerHTML()
    for (const pattern of LEAK_PATTERNS) {
      expect(html, `workflow UI must not contain ${pattern}`).not.toContain(pattern)
    }
  })

  test('never renders an API-key / shell-command / password input', async ({ page }) => {
    await page.locator('#devconsole-nav-workflow').click()
    await page.waitForTimeout(150)
    expect(await page.locator('input[type="password"]').count()).toBe(0)
    const keyInputs = await page.locator('input').evaluateAll((els) =>
      els.filter((el) => /api[_-]?key|shell|command/i.test((el.id || '') + (el.getAttribute('name') || ''))).length,
    )
    expect(keyInputs).toBe(0)
  })
})
