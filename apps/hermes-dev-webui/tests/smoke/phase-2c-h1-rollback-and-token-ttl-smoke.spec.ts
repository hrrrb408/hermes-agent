/**
 * Phase 2C-H1: Rollback execution + file-backed confirmation token TTL smoke.
 *
 * Drives the controlled rollback chain against the live Dev API, reusing the
 * existing POST /api/dev/v1/tools/dry-run (mode='rollback_preview') and
 * POST /api/dev/v1/tools/execute (mode='rollback') paths — no new route.
 * Asserts:
 *   - a write produces a rollbackId and a stored manifest
 *   - rollback preview + a rollback-scoped confirmation token are generated
 *   - rollback execute completes (delete_created_file + restore_previous_content)
 *   - token replay is blocked (single-use)
 *   - the audit viewer surfaces rollback + confirmation events
 *   - provider write preview still does not auto-execute
 *
 * Gate env (set by the smoke harness phase2c_h1_rollback_and_token_ttl profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 *   HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
 */
import { test, expect, type APIRequestContext } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const DRY_RUN_URL = `${API_BASE}/tools/dry-run`
const EXECUTE_URL = `${API_BASE}/tools/execute`

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

async function writeOnce(
  request: APIRequestContext,
  target: string,
  content: string,
): Promise<string> {
  const preview = (
    await (
      await request.post(DRY_RUN_URL, {
        data: { mode: 'write_preview', toolId: 'dev_sandbox_file_write', arguments: { targetPath: target, content, mode: 'create_or_replace' } },
      })
    ).json()
  ).data
  const exec = (
    await (
      await request.post(EXECUTE_URL, {
        data: {
          mode: 'write',
          toolId: 'dev_sandbox_file_write',
          arguments: { targetPath: target, content, mode: 'create_or_replace' },
          writePlanId: preview.writePlanId,
          confirmationToken: preview.confirmationToken,
          argumentDigest: preview.argumentDigest,
        },
      })
    ).json()
  ).data
  expect(exec.status).toBe('completed')
  return exec.rollbackId as string
}

test.describe('Phase 2C-H1 rollback + token TTL', () => {
  test('write then rollback delete_created_file', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')
    const rollbackId = await writeOnce(request, 'notes/h1-delete.md', 'created-by-h1')

    // Rollback preview.
    const rbPreview = (
      await (
        await request.post(DRY_RUN_URL, { data: { mode: 'rollback_preview', rollbackId } })
      ).json()
    ).data
    expect(rbPreview.blocked).toBe(false)
    expect(rbPreview.restoreMode).toBe('delete_created_file')
    expect(rbPreview.confirmationToken).toBeTruthy()
    expect(rbPreview.confirmationTokenScope).toBe('rollback_execute')
    expect(rbPreview.currentHash).toBe(rbPreview.afterHash)

    // Rollback execute.
    const rbExec = (
      await (
        await request.post(EXECUTE_URL, {
          data: { mode: 'rollback', rollbackId, confirmationToken: rbPreview.confirmationToken, argumentDigest: rbPreview.argumentDigest },
        })
      ).json()
    ).data
    expect(rbExec.status).toBe('completed')
    expect(rbExec.restoreMode).toBe('delete_created_file')
    expect(rbExec.finalHash).toBeNull()
    expect(rbExec.postExecutionAuditId).toBeTruthy()
    expect(rbExec.externalNetworkCalled).toBe(false)
  })

  test('rollback restore_previous_content', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    await writeOnce(request, 'notes/h1-restore.md', 'original')
    const rollbackId = await writeOnce(request, 'notes/h1-restore.md', 'REPLACED')

    const rbPreview = (
      await (await request.post(DRY_RUN_URL, { data: { mode: 'rollback_preview', rollbackId } })).json()
    ).data
    expect(rbPreview.restoreMode).toBe('restore_previous_content')
    expect(rbPreview.beforeHash).toBeTruthy()

    const rbExec = (
      await (
        await request.post(EXECUTE_URL, {
          data: { mode: 'rollback', rollbackId, confirmationToken: rbPreview.confirmationToken, argumentDigest: rbPreview.argumentDigest },
        })
      ).json()
    ).data
    expect(rbExec.status).toBe('completed')
    expect(rbExec.finalHash).toBe(rbPreview.beforeHash)
  })

  test('rollback token replay is blocked (single-use)', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const rollbackId = await writeOnce(request, 'notes/h1-replay.md', 'x')
    const rbPreview = (
      await (await request.post(DRY_RUN_URL, { data: { mode: 'rollback_preview', rollbackId } })).json()
    ).data
    const ctx = { mode: 'rollback', rollbackId, confirmationToken: rbPreview.confirmationToken, argumentDigest: rbPreview.argumentDigest }
    const first = (await (await request.post(EXECUTE_URL, { data: ctx })).json()).data
    expect(first.status).toBe('completed')
    const replay = (await (await request.post(EXECUTE_URL, { data: ctx })).json()).data
    expect(replay.status).toBe('blocked')
    expect(replay.blockedReason).toBeTruthy()
  })

  test('audit viewer surfaces rollback + confirmation events', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const rollbackId = await writeOnce(request, 'notes/h1-audit.md', 'x')
    const rbPreview = (
      await (await request.post(DRY_RUN_URL, { data: { mode: 'rollback_preview', rollbackId } })).json()
    ).data
    await request.post(EXECUTE_URL, {
      data: { mode: 'rollback', rollbackId, confirmationToken: rbPreview.confirmationToken, argumentDigest: rbPreview.argumentDigest },
    })
    const resp = await request.get(`${API_BASE}/tools/audit-events`, { params: { auditKind: 'write', limit: 50 } })
    const items = (await resp.json()).data.items
    const types = items.map((i: { eventType: string }) => i.eventType)
    expect(types).toContain('rollback_post_execution_audit')
  })

  test('provider write preview still does not auto-execute', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'provider_roundtrip',
        providerMode: 'fake',
        message: 'draft a sandbox note please',
        allowedToolIds: ['dev_sandbox_file_write'],
        providerWriteMode: 'preview_only',
      },
    })
    const data = (await resp.json()).data
    expect(data.status).toBe('blocked')
    expect(data.writeExecuted).toBe(false)
    expect(data.externalNetworkCalled).toBe(false)
  })
})

test.describe('UI: Rollback panel (Phase 2C-H1)', () => {
  test('rollback section is visible in the write panel', async ({ page }) => {
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
    const writeTab = page.locator('#workspace-tab-write')
    if (!(await writeTab.isVisible().catch(() => false))) {
      test.skip(true, 'Write tab not visible')
    }
    await writeTab.click()
    await page.waitForTimeout(300)
    await expect(page.locator('#write-rollback-id')).toBeVisible()
    const html = await page.locator('.tool-write').innerHTML().catch(() => '')
    expect(html.toLowerCase()).not.toMatch(/api ?key|authorization|bearer/)
  })
})
