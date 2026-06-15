/**
 * Phase 3A: Dev-only Agent Workflow MVP — browser smoke.
 *
 * Validates the dev-only, manual, approval-gated workflow end-to-end against
 * the live Dev API + WebUI:
 *   - the workflow_plan_preview / workflow_step_preview / workflow_step_execute
 *     / workflow_state_read modes work as branches on the existing
 *     /tools/dry-run + /tools/execute routes (NO new route);
 *   - the full plan → preview → approve → execute lifecycle runs over HTTP;
 *   - forbidden step types are blocked; real provider is blocked;
 *   - write / rollback steps never execute (preview / reference only);
 *   - the Workflow console section renders, the safety boundary is correct,
 *     and no secret / token / production path / callable repr leaks.
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181
 *   WebUI    on 127.0.0.1:5180  (pnpm dev)
 *
 * Gate env (set by the smoke harness phase3a_workflow_mvp profile):
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
// 1. API leg — the workflow modes work + are leak-free
// ===================================================================

test.describe('Phase 3A — workflow API modes', () => {
  test('plan preview materializes an execution and stays leak-free', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await postJson(request, '/tools/dry-run', {
      mode: 'workflow_plan_preview',
      title: 'Smoke workflow',
      goal: 'inspect',
      steps: [
        { stepType: 'read_only_tool', toolId: 'dev_environment_read' },
        { stepType: 'fake_provider_roundtrip', providerMode: 'fake', message: 'hi', allowedToolIds: ['tool_policy_read'] },
        { stepType: 'sandbox_write_preview', toolId: 'dev_sandbox_file_write', targetRelativePath: 'workflow-demo/smoke.md', content: 'preview only' },
        { stepType: 'manual_note', note: 'operator review note' },
      ],
    })
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    expect(data.steps.length).toBe(4)
    expect(data.blockedSteps.length).toBe(0)
    expect(data.workflowExecutionId).toBeTruthy()
    expect(data.executionStatus).toBe('running')
    assertNoLeak(await resp.text(), 'workflow_plan_preview')
  })

  test('forbidden step types are blocked', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    for (const stepType of ['real_provider_roundtrip', 'shell_command', 'database_mutation', 'production_operation']) {
      const resp = await postJson(request, '/tools/dry-run', {
        mode: 'workflow_plan_preview', title: 'bad', steps: [{ stepType }],
      })
      const data = (await resp.json()).data
      expect(data.steps.length, stepType).toBe(0)
      expect(data.blockedSteps[0].blockedReason, stepType).toMatch(/^blocked_workflow_/)
    }
  })

  test('full lifecycle: preview → approve → execute; write/rollback never execute', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const plan = await postJson(request, '/tools/dry-run', {
      mode: 'workflow_plan_preview', title: 'lifecycle',
      steps: [
        { stepType: 'read_only_tool', toolId: 'dev_environment_read' },
        { stepType: 'sandbox_write_preview', toolId: 'dev_sandbox_file_write', targetRelativePath: 'wf/smoke.md', content: 'c' },
      ],
    })
    const pData = (await plan.json()).data
    const wfx = pData.workflowExecutionId

    // Execute without approval is blocked.
    const noToken = await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[0].stepId })
    expect(noToken.status()).toBe(400)

    // Preview → issues token → execute the read-only step.
    const pv0 = (await (await postJson(request, '/tools/dry-run', { mode: 'workflow_step_preview', workflowExecutionId: wfx, stepId: pData.steps[0].stepId })).json()).data
    expect(pv0.approvalToken).toBeTruthy()
    const ex0 = await (await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[0].stepId, approvalToken: pv0.approvalToken })).json()
    expect(ex0.data.result.type).toBe('dev_environment_read')

    // Replay blocked (single-use).
    const replay = await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[0].stepId, approvalToken: pv0.approvalToken })
    expect(replay.status()).toBe(400)

    // The write-preview step records a preview only — never executes the write.
    const pv1 = (await (await postJson(request, '/tools/dry-run', { mode: 'workflow_step_preview', workflowExecutionId: wfx, stepId: pData.steps[1].stepId })).json()).data
    const ex1 = await (await postJson(request, '/tools/execute', { mode: 'workflow_step_execute', workflowExecutionId: wfx, stepId: pData.steps[1].stepId, approvalToken: pv1.approvalToken })).json()
    expect(ex1.data.result.workflowWriteExecuted).toBe(false)
    expect(ex1.data.result.autoWriteBlocked).toBe(true)
    assertNoLeak(JSON.stringify(ex1), 'workflow_step_execute')
  })

  test('audit viewer can find workflow events', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const resp = await request.get(`${API_BASE}/tools/audit-events?auditKind=internal&eventType=workflow_plan_created&limit=5`)
    expect(resp.status()).toBe(200)
  })
})

// ===================================================================
// 2. UI leg — the Workflow console section
// ===================================================================

test.describe('Phase 3A — workflow console UI', () => {
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

  test('the Workflow section renders with the safety boundary', async ({ page }) => {
    await page.locator('#devconsole-nav-workflow').click()
    await page.waitForTimeout(200)
    const content = await page.locator('.devconsole__content').textContent()
    expect(content).toContain('Workflow')
    expect(content).toContain('No real provider')
    // Safety boundary: real provider / shell / production are Blocked.
    const boundary = await page.locator('[data-testid="dev-workflow-safety-boundary"]').textContent()
    expect(boundary).toContain('Blocked')
    expect(boundary).toContain('Allowed')
  })

  test('a workflow plan can be built and previewed in the UI', async ({ page }) => {
    await page.locator('#devconsole-nav-workflow').click()
    await page.waitForTimeout(200)
    await expect(page.locator('[data-testid="dev-workflow-build-plan-btn"]')).toBeVisible()
    await page.locator('[data-testid="dev-workflow-build-plan-btn"]').click()
    await page.waitForTimeout(500)
    // The plan preview or safety boundary remains leak-free.
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
