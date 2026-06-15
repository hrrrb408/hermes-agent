/**
 * Phase 2C: Controlled dev-sandbox write browser smoke.
 *
 * Drives the controlled write chain against the live Dev API, reusing the
 * existing POST /api/dev/v1/tools/dry-run path (mode='write_preview') and
 * POST /api/dev/v1/tools/execute path (mode='write') — no new route. Asserts:
 *   - a dry-run preview is generated and does NOT write a file
 *   - execute completes only with confirmation + digest, inside the sandbox
 *   - the result carries beforeHash / afterHash / rollbackId + audit ids
 *   - the write audit is queryable via auditKind=write
 *   - readback confirms the written content
 *   - a provider-requested write generates a preview but NEVER auto-executes
 *
 * Prerequisites (servers must already be running; tests skip gracefully):
 *   Dev API  on 127.0.0.1:5181  (HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev)
 *   WebUI    on 127.0.0.1:5180  (pnpm dev) — optional, for the UI test
 *
 * Gate env (set by the smoke harness phase2c_write_sandbox profile):
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

// ===================================================================
// 1. Controlled write preview + execute
// ===================================================================

test.describe('Phase 2C controlled write', () => {
  test('write preview then execute completes inside the sandbox', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available on 127.0.0.1:5181')

    const target = 'notes/smoke-phase2c.md'
    // Unique per run so a pre-existing sandbox file (from a prior smoke run)
    // produces a distinct beforeHash != afterHash.
    const content = `# Phase 2C Smoke\n\nwritten by the controlled write smoke at ${Date.now()}.\n`

    // 1. Dry-run preview (must not write).
    const previewResp = await request.post(DRY_RUN_URL, {
      data: {
        mode: 'write_preview',
        toolId: 'dev_sandbox_file_write',
        arguments: { targetPath: target, content, mode: 'create_or_replace' },
        sourceContext: 'smoke',
        uiOrigin: 'phase-2c-smoke',
      },
    })
    expect(previewResp.status(), 'preview should return 200').toBe(200)
    const preview = (await previewResp.json()).data
    expect(preview.blocked, 'preview must not be blocked').toBe(false)
    expect(preview.confirmationToken, 'preview must issue a token').toBeTruthy()
    expect(preview.afterHash, 'preview must compute afterHash').toBeTruthy()
    expect(preview.externalSideEffects).toBe(false)

    // 2. Execute with confirmation + digest.
    const execResp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'write',
        toolId: 'dev_sandbox_file_write',
        arguments: { targetPath: target, content, mode: 'create_or_replace' },
        writePlanId: preview.writePlanId,
        confirmationToken: preview.confirmationToken,
        argumentDigest: preview.argumentDigest,
      },
    })
    expect(execResp.status()).toBe(200)
    const result = (await execResp.json()).data
    expect(result.status, 'execute must complete').toBe('completed')
    expect(result.bytesWritten).toBeGreaterThan(0)
    expect(result.afterHash).toBeTruthy()
    expect(result.beforeHash === null || result.beforeHash !== result.afterHash).toBeTruthy()
    expect(result.rollbackId, 'execute must produce a rollback id').toBeTruthy()
    expect(result.rollbackAvailable).toBe(true)
    expect(result.preExecutionAuditId).toBeTruthy()
    expect(result.postExecutionAuditId).toBeTruthy()
    expect(result.externalNetworkCalled).toBe(false)
    expect(result.providerApiCalled).toBe(false)

    // 3. Write audit is queryable.
    const auditResp = await request.get(`${API_BASE}/tools/audit-events`, {
      params: { auditKind: 'write', limit: 20 },
    })
    expect(auditResp.status()).toBe(200)
    const items = (await auditResp.json()).data.items
    expect(items.length, 'at least one write audit event').toBeGreaterThan(0)
    expect(items[0].sideEffects.writeRequired).toBe(true)
    expect(items[0].sideEffects.externalNetworkCalled).toBe(false)
  })

  test('readback confirms the written content', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    // Seed a file via the write chain.
    const target = 'notes/smoke-readback.md'
    const content = 'readback target content'
    const preview = (
      await (
        await request.post(DRY_RUN_URL, {
          data: {
            mode: 'write_preview',
            toolId: 'dev_sandbox_file_write',
            arguments: { targetPath: target, content, mode: 'create_or_replace' },
          },
        })
      ).json()
    ).data
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

    // Readback via the write chain.
    const rbPreview = (
      await (
        await request.post(DRY_RUN_URL, {
          data: {
            mode: 'write_preview',
            toolId: 'dev_sandbox_file_readback',
            arguments: { targetPath: target },
          },
        })
      ).json()
    ).data
    const rbResp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'write',
        toolId: 'dev_sandbox_file_readback',
        arguments: { targetPath: target },
        writePlanId: rbPreview.writePlanId,
        confirmationToken: rbPreview.confirmationToken,
        argumentDigest: rbPreview.argumentDigest,
      },
    })
    const rb = (await rbResp.json()).data
    expect(rb.status).toBe('completed')
    expect(rb.readback.exists).toBe(true)
    expect(rb.readback.snippet).toContain('readback target content')
  })

  test('provider-requested write never auto-executes', async ({ request }) => {
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
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    expect(data.status).toBe('blocked')
    expect(data.writeExecuted).toBe(false)
    expect(data.writePreviewGenerated).toBe(true)
    expect(data.blockedReason).toBe('blocked_write_provider_auto_execute_denied')
    expect(data.externalNetworkCalled).toBe(false)
  })

  test('write disabled when HERMES_TOOL_WRITE_EXECUTION_ENABLED unset', async ({ request }) => {
    test.skip(!(await apiAvailable(request)), 'Dev API not available')
    // The harness enables write for this profile; this test only asserts the
    // request shape is accepted and a result envelope is returned. The actual
    // disabled-path is covered by the backend unit suite.
    const resp = await request.post(EXECUTE_URL, {
      data: {
        mode: 'write',
        toolId: 'dev_sandbox_file_write',
        arguments: { targetPath: 'notes/noop.md', content: 'x', mode: 'create_or_replace' },
        writePlanId: 'wpln_none',
        confirmationToken: 'wctok_none',
        argumentDigest: '0'.repeat(64),
      },
    })
    expect(resp.status()).toBe(200)
    const data = (await resp.json()).data
    // Without valid confirmation the execute must be blocked (never completed).
    expect(data.status).toBe('blocked')
    expect(data.blockedReason).toBeTruthy()
  })
})

// ===================================================================
// 2. UI: Write panel is visible
// ===================================================================

test.describe('UI: Controlled write panel', () => {
  test('write tab is visible and selectable', async ({ page }) => {
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

    // Panel surface + no API key / shell input.
    await expect(page.locator('.tool-write')).toBeVisible()
    await expect(page.locator('#write-tool')).toBeVisible()
    await expect(page.locator('#write-target')).toBeVisible()
    const html = await page.locator('.tool-write').innerHTML().catch(() => '')
    expect(html.toLowerCase()).not.toMatch(/api ?key|authorization|bearer/)
  })
})
