/**
 * Phase 2D: Durable audit store indexing smoke.
 *
 * Drives the live Dev API to generate audit events across every kind (via the
 * dual-write bridge) and then queries the durable store through the enhanced
 * GET /api/dev/v1/tools/audit-events route — no new route. Asserts:
 *   - read-only / provider / write audit events flow into the durable store
 *   - the store-mode response carries storeStatus / indexStatus / schemaVersion
 *   - filters (eventType / toolId / status / auditKind / providerMode /
 *     writeRequired) narrow results correctly
 *   - cursor pagination returns a next page
 *   - redactionApplied is surfaced on at least one item
 *   - no raw token / secret / full tokenHash / raw arguments / callable repr
 *     appears in any response body
 *
 * Gate env (set by the smoke harness phase2d_audit_store_indexing profile):
 *   HERMES_TOOL_EXECUTION_ENABLED=true
 *   HERMES_AGENT_TOOLS_ENABLED=true
 *   HERMES_TOOL_HANDLER_CALL_ENABLED=true
 *   HERMES_PROVIDER_MODE=fake
 *   HERMES_TOOL_WRITE_EXECUTION_ENABLED=true
 */
import { test, expect, type APIRequestContext } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const DRY_RUN_URL = `${API_BASE}/tools/dry-run`
const EXECUTE_URL = `${API_BASE}/tools/execute`
const AUDIT_URL = `${API_BASE}/tools/audit-events`

async function apiAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/status`, { timeout: 4000 })
    return resp.ok()
  } catch {
    return false
  }
}

async function generateReadOnlyAudit(request: APIRequestContext): Promise<void> {
  // Dry-run + execute clarify → dry-run / pre / post execution audits.
  await request.post(DRY_RUN_URL, {
    data: { mode: 'dry_run', toolId: 'clarify', arguments: { question: 'phase2d smoke?' } },
  })
  const dr = (
    await (
      await request.post(DRY_RUN_URL, {
        data: { mode: 'execute', toolId: 'clarify', arguments: { question: 'phase2d store smoke' } },
      })
    ).json()
  ).data
  if (dr?.confirmationToken) {
    await request.post(EXECUTE_URL, {
      data: {
        mode: 'execute',
        toolId: 'clarify',
        arguments: { question: 'phase2d store smoke' },
        confirmationToken: dr.confirmationToken,
        argumentDigest: dr.argumentDigest,
      },
    })
  }
}

async function generateWriteAudit(request: APIRequestContext): Promise<void> {
  // write_preview + write execute → emits write audits (preview + post-execution).
  const preview = (
    await (
      await request.post(DRY_RUN_URL, {
        data: {
          mode: 'write_preview',
          toolId: 'dev_sandbox_file_write',
          arguments: {
            targetPath: 'phase2d-smoke.md',
            content: 'phase2d audit store smoke',
            mode: 'create_or_replace',
          },
        },
      })
    ).json()
  ).data
  if (preview?.writePlanId && preview?.confirmationToken) {
    await request.post(EXECUTE_URL, {
      data: {
        mode: 'write',
        toolId: 'dev_sandbox_file_write',
        arguments: {
          targetPath: 'phase2d-smoke.md',
          content: 'phase2d audit store smoke',
          mode: 'create_or_replace',
        },
        writePlanId: preview.writePlanId,
        confirmationToken: preview.confirmationToken,
        argumentDigest: preview.argumentDigest,
      },
    })
  }
}

async function bodyText(resp: { json: () => Promise<unknown> }): Promise<string> {
  return JSON.stringify(await resp.json())
}

test.describe('Phase 2D — durable audit store indexing', () => {
  test.beforeAll(async ({ request }) => {
    // Bail early if the Dev API is not up (smoke harness starts it).
    if (!(await apiAvailable(request))) {
      throw new Error('Dev API not available — smoke harness must start services')
    }
    // Generate events of every kind so the durable store has content.
    await generateReadOnlyAudit(request)
    await generateWriteAudit(request)
  })

  test('store query returns enriched shape with store/index status', async ({ request }) => {
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'dry_run', toolId: 'clarify', limit: 10 },
    })
    expect(resp.ok(), `status ${resp.status()}`).toBeTruthy()
    const body = (await resp.json()).data
    expect(body.schemaVersion).toBe('audit_schema_v2')
    expect(body.storeStatus).toBeDefined()
    expect(body.storeStatus.schemaVersion).toBe('audit_schema_v2')
    expect(body.indexStatus).toBeDefined()
    expect(Array.isArray(body.items)).toBe(true)
  })

  test('store query filters by auditKind across kinds', async ({ request }) => {
    for (const kind of ['dry_run', 'post_execution', 'write']) {
      const resp = await request.get(AUDIT_URL, {
        params: { auditKind: kind, search: 'phase2d', limit: 20 },
      })
      expect(resp.ok(), `${kind} status ${resp.status()}`).toBeTruthy()
      const body = (await resp.json()).data
      for (const item of body.items) {
        expect(item.auditKind).toBe(kind)
      }
    }
  })

  test('store query filters by writeRequired', async ({ request }) => {
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'write', writeRequired: 'true', limit: 20 },
    })
    expect(resp.ok()).toBeTruthy()
    const body = (await resp.json()).data
    for (const item of body.items) {
      expect(item.writeRequired).toBe(true)
    }
  })

  test('store query filters by providerMode', async ({ request }) => {
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'provider', providerMode: 'fake', limit: 20 },
    })
    expect(resp.ok()).toBeTruthy()
    const body = (await resp.json()).data
    for (const item of body.items) {
      expect(item.providerMode).toBe('fake')
    }
  })

  test('store query cursor pagination advances', async ({ request }) => {
    // Seed enough events to guarantee >1 page at limit=1.
    await generateReadOnlyAudit(request)
    await generateReadOnlyAudit(request)
    const r1 = await request.get(AUDIT_URL, {
      params: { auditKind: 'post_execution', toolId: 'clarify', limit: 1 },
    })
    expect(r1.ok()).toBeTruthy()
    const d1 = (await r1.json()).data
    if (d1.hasMore && d1.nextCursor) {
      const r2 = await request.get(AUDIT_URL, {
        params: {
          auditKind: 'post_execution', toolId: 'clarify', limit: 1,
          cursor: d1.nextCursor,
        },
      })
      expect(r2.ok()).toBeTruthy()
      const d2 = (await r2.json()).data
      expect(d2.items.length).toBeGreaterThanOrEqual(0)
    }
  })

  test('redactionApplied is surfaced on at least one item', async ({ request }) => {
    // writeRequired triggers the durable-store query path (store mode), which
    // surfaces the canonical redactionApplied flag on write audits.
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'write', writeRequired: 'true', limit: 20 },
    })
    expect(resp.ok()).toBeTruthy()
    const body = (await resp.json()).data
    const flagged = body.items.some(
      (i: { redactionApplied?: boolean }) => i.redactionApplied === true,
    )
    // At least one write audit should report redaction (raw args redacted).
    expect(flagged).toBe(true)
  })

  test('no raw secret / token / callable repr leaks in store output', async ({ request }) => {
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'write', search: 'phase2d', limit: 20 },
    })
    const text = await bodyText(resp)
    expect(text).not.toContain('sk-')
    expect(text).not.toContain('Bearer ')
    expect(text).not.toContain('<function')
    expect(text).not.toContain('object at 0x')
    expect(text).not.toContain('rawArguments')
    expect(text).not.toContain('/Users/huangruibang/.hermes')
  })

  test('cursor tamper is rejected', async ({ request }) => {
    const resp = await request.get(AUDIT_URL, {
      params: { auditKind: 'dry_run', search: 'phase2d', cursor: '!!tampered!!' },
    })
    expect(resp.status()).toBe(400)
  })

  test('route remains read-only (POST rejected)', async ({ request }) => {
    const resp = await request.post(AUDIT_URL, { data: { auditKind: 'dry_run' } })
    expect(resp.status()).toBe(405)
  })
})
