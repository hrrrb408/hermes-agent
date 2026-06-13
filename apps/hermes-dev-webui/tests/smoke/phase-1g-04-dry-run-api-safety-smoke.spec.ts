/**
 * Phase 1G-04-05: Tool Dry-Run API Browser / Network / A11y Safety Smoke
 *
 * Validates the Dry-Run API safety boundaries in browser, network, and a11y contexts.
 * Tests cover: API smoke, secret redaction, unknown tools, validation errors,
 * network safety (no external provider requests, no execute/dispatch/audit writes),
 * UI non-exposure (no new execution UI), and A11y regression.
 *
 * Prerequisites:
 *   - Dev API  on 127.0.0.1:5181  (HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev)
 *   - WebUI    on 127.0.0.1:5180  (pnpm dev) — required for browser/network/UI tests,
 *                                    optional for API-only tests
 *
 * No screenshots, traces, videos, or HAR are captured by default.
 */
import { test, expect } from '@playwright/test'

// ─── Constants ─────────────────────────────────────────────────────────

const API_BASE = 'http://127.0.0.1:5181/api/dev/v1'
const DRY_RUN_URL = `${API_BASE}/tools/dry-run`

/** A known R0 tool (not denylisted, lowest risk tier) — clarify is the sole R0 tool */
const SAFE_TOOL = 'clarify'

/** A known R1 candidate-allowlisted tool — read_file is R1 */
const CANDIDATE_TOOL = 'read_file'

/** Fake secrets for redaction testing — never use real values */
const FAKE_SECRETS = {
  apiKey: 'sk-test-fake-redacted-value',
  bearerToken: 'Bearer fake-token-for-redaction-test',
  password: 'fake-password-value',
} as const

/** Provider domains that must never appear in network requests */
const PROVIDER_DOMAINS = [
  'api.openai.com',
  'openai.com',
  'api.anthropic.com',
  'anthropic.com',
  'api.x.ai',
  'x.ai',
  'api.groq.com',
  'generativelanguage.googleapis.com',
  'openrouter.ai',
  'api.openrouter.ai',
  'zai.ai',
  'api.zai.ai',
] as const

/** Forbidden API path patterns (execution/dispatch/audit writes) */
const FORBIDDEN_PATH_PATTERNS = [
  /\/api\/dev\/v1\/tools\/execute/i,
  /\/api\/dev\/v1\/tools\/dispatch/i,
  /\/api\/dev\/v1\/tools\/audit/i,
  /\/api\/dev\/v1\/tools\/run(?!.*dry-run)/i,
  /\/api\/dev\/v1\/tools\/invoke/i,
  /\/api\/dev\/v1\/tools\/call/i,
  /\/api\/dev\/v1\/provider-schema/i,
] as const

/** Forbidden UI action labels */
const FORBIDDEN_UI_LABELS = [
  'Execute Tool',
  'Run Tool',
  'Dispatch Tool',
  'Send Provider Schema',
  'Enable Tool Execution',
  'Enable Execution',
  'Write Audit',
  'Approve Execution',
] as const

// ─── Helpers ───────────────────────────────────────────────────────────

/** Assert all four execution-flags are false on a response data object */
function assertNoExecutionFlags(data: Record<string, unknown>): void {
  expect(data.executionAllowed, 'executionAllowed must be false').toBe(false)
  expect(data.dispatchAllowed, 'dispatchAllowed must be false').toBe(false)
  expect(data.providerSchemaAllowed, 'providerSchemaAllowed must be false').toBe(false)
  expect(data.auditWritten, 'auditWritten must be false').toBe(false)
}

// ===================================================================
// 1. API Smoke — Dry-Run returns safe decision without execution
// ===================================================================

test.describe('API Smoke', () => {
  test('renders a safe dry-run decision without execution flags', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: { canonicalName: SAFE_TOOL },
    })
    expect(resp.status(), 'Dry-Run POST should return 200').toBe(200)

    const body = await resp.json()

    // Response envelope
    expect(body, 'Response must have data').toHaveProperty('data')
    expect(body, 'Response must have meta').toHaveProperty('meta')
    expect(body.meta, 'Meta must have requestId').toHaveProperty('requestId')
    expect(body.meta, 'Meta must have timestamp').toHaveProperty('timestamp')

    // Data fields
    const data = body.data
    expect(data.canonicalName).toBe(SAFE_TOOL)
    expect(data.exists).toBe(true)
    expect(data.decision).toBeTruthy()
    expect(typeof data.decision).toBe('string')
    expect(data.riskTier).toBe('R0')
    expect(Array.isArray(data.reasonCodes)).toBe(true)
    expect(Array.isArray(data.policyNotes)).toBe(true)
    expect(data.redactedArgumentsPreview).toBeDefined()
    expect(Array.isArray(data.forbiddenFields)).toBe(true)
    expect(Array.isArray(data.missingRequiredFields)).toBe(true)

    // Decision must be one of the known values
    const validDecisions = ['would_allow', 'would_block', 'would_redact', 'requires_review']
    expect(validDecisions).toContain(data.decision)

    // Execution flags invariant
    assertNoExecutionFlags(data)
  })

  test('candidate tool returns would_allow with R1 tier', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: { canonicalName: CANDIDATE_TOOL },
    })
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    const data = body.data

    expect(data.exists).toBe(true)
    expect(data.riskTier).toBe('R1')
    expect(data.decision).toBe('would_allow')
    assertNoExecutionFlags(data)
  })

  test('dry-run POST is not counted as tool write', async ({ request }) => {
    // Verify the dry-run endpoint exists and is a POST
    const resp = await request.post(DRY_RUN_URL, {
      data: { canonicalName: SAFE_TOOL },
    })
    expect(resp.status()).toBe(200)

    // Verify OpenAPI spec has no tool write routes
    const specResp = await request.get('http://127.0.0.1:5181/openapi.json')
    expect(specResp.ok()).toBe(true)
    const spec = await specResp.json()

    const toolPaths = Object.keys(spec.paths).filter((p: string) =>
      p.startsWith('/api/dev/v1/tools'),
    )

    // Check no write routes (PUT, PATCH, DELETE). The only allowed tool
    // POST routes are the non-mutating dry-run and the controlled execute
    // gate (Phase 1G-04-11+); neither is a tool write route.
    const allowedToolPosts = ['dry-run', 'execute']
    for (const path of toolPaths) {
      const methods = Object.keys(spec.paths[path])
      for (const method of methods) {
        const m = method.toLowerCase()
        if (m === 'put' || m === 'patch' || m === 'delete') {
          expect.fail(`Tool write route found: ${m.toUpperCase()} ${path}`)
        }
        if (m === 'post' && !allowedToolPosts.some((p) => path.includes(p))) {
          expect.fail(`Tool write route found: POST ${path}`)
        }
      }
    }

    // Verify dry-run route exists
    expect(toolPaths).toContain('/api/dev/v1/tools/dry-run')
  })
})

// ===================================================================
// 2. Redaction Smoke — Secret values are never returned raw
// ===================================================================

test.describe('Redaction Smoke', () => {
  test('secret arguments are redacted in response', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: {
        canonicalName: CANDIDATE_TOOL,
        argumentsPreview: {
          api_key: FAKE_SECRETS.apiKey,
          authorization: FAKE_SECRETS.bearerToken,
          password: FAKE_SECRETS.password,
          safe_query: 'normal value',
        },
      },
    })
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    const text = JSON.stringify(body)

    // No raw secrets in response text
    expect(text, 'Response must not contain raw API key').not.toContain(FAKE_SECRETS.apiKey)
    expect(text, 'Response must not contain raw Bearer token').not.toContain(
      FAKE_SECRETS.bearerToken,
    )
    expect(text, 'Response must not contain raw password').not.toContain(FAKE_SECRETS.password)

    // Redaction markers present
    const redacted = body.data.redactedArgumentsPreview
    expect(redacted.api_key).toBe('[REDACTED]')
    expect(redacted.authorization).toBe('[REDACTED]')
    expect(redacted.password).toBe('[REDACTED]')
    expect(redacted.safe_query).toBe('normal value')

    // Forbidden fields should list the redacted keys
    expect(body.data.forbiddenFields).toBeDefined()
    const forbidden = body.data.forbiddenFields as string[]
    expect(forbidden.length, 'Should flag at least one forbidden field').toBeGreaterThanOrEqual(1)

    // Execution flags still false
    assertNoExecutionFlags(body.data)
  })
})

// ===================================================================
// 3. Unknown Tool Smoke — Unknown tools return safe response
// ===================================================================

test.describe('Unknown Tool Smoke', () => {
  test('unknown tool returns 200 with exists=false and would_block', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: { canonicalName: 'nonexistent_tool_xyz_abc_123' },
    })
    // Must be 200 (not 404, not 500)
    expect(resp.status(), 'Unknown tool must return 200, not 404 or 500').toBe(200)

    const body = await resp.json()
    const data = body.data

    expect(data.exists, 'exists must be false').toBe(false)
    expect(data.decision, 'decision must be would_block').toBe('would_block')
    expect(data.reasonCodes, 'reasonCodes must include WOULD_BLOCK_UNKNOWN_TOOL').toContain(
      'WOULD_BLOCK_UNKNOWN_TOOL',
    )
    expect(data.riskTier, 'riskTier must be null for unknown tool').toBeNull()

    // Not an error response — must have data, not an error envelope
    expect(body.error == null, 'Response must not have error envelope').toBeTruthy()

    // Execution flags still false
    assertNoExecutionFlags(data)
  })
})

// ===================================================================
// 4. Validation Error Smoke — Input errors return 400 safely
// ===================================================================

test.describe('Validation Error Smoke', () => {
  test('missing canonicalName returns 400', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: { argumentsPreview: {} },
    })
    expect(resp.status(), 'Missing canonicalName must return 400').toBe(400)

    const body = await resp.json()
    expect(body.error, 'Error envelope must exist').toBeDefined()
    expect(body.error.code, 'Error must have code').toBeDefined()
    expect(body.error.message, 'Error must have message').toBeDefined()
    expect(body.error.code).toBe('TOOL_DRY_RUN_INVALID_CANONICAL_NAME')

    // No stack trace leakage
    const text = JSON.stringify(body)
    expect(text, 'Must not contain traceback').not.toContain('Traceback')
    expect(text, 'Must not contain file paths').not.toContain('File "')
    expect(text, 'Must not contain stack frames').not.toContain('stack')

    // No provider information leakage
    const lowerText = text.toLowerCase()
    expect(lowerText, 'Must not leak provider names').not.toContain('openai')
    expect(lowerText, 'Must not leak provider names').not.toContain('anthropic')
    expect(lowerText, 'Must not leak provider config').not.toContain('api_key')

    // No execution triggered
    expect(text, 'Must not claim execution').not.toContain('executionAllowed')
  })

  test('non-object argumentsPreview returns 400', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: { canonicalName: 'test', argumentsPreview: 'not-an-object' },
    })
    expect(resp.status(), 'Non-object argumentsPreview must return 400').toBe(400)

    const body = await resp.json()
    expect(body.error.code).toBe('TOOL_DRY_RUN_INVALID_ARGUMENTS')
  })

  test('empty body returns 400 or 422', async ({ request }) => {
    const resp = await request.post(DRY_RUN_URL, {
      data: '',
      headers: { 'Content-Type': 'application/json' },
    })
    expect([400, 422], 'Empty body must return 400 or 422').toContain(resp.status())
  })
})

// ===================================================================
// 5. Network Safety Smoke — No external provider or execution requests
// ===================================================================

test.describe('Network Safety', () => {
  test('no external provider requests during dry-run API call', async ({ page }) => {
    test.setTimeout(30_000)

    const externalRequests: string[] = []
    const forbiddenRequests: string[] = []
    const providerRequests: string[] = []

    // Monitor all browser network requests
    page.on('request', (req) => {
      const url = req.url()
      const method = req.method()

      // Track external (non-localhost) requests
      if (
        !url.includes('127.0.0.1') &&
        !url.includes('localhost') &&
        !url.startsWith('data:')
      ) {
        externalRequests.push(`${method} ${url}`)

        // Check for provider domains
        for (const domain of PROVIDER_DOMAINS) {
          if (url.includes(domain)) {
            providerRequests.push(`${method} ${url}`)
          }
        }
      }

      // Check for forbidden API path patterns
      for (const pattern of FORBIDDEN_PATH_PATTERNS) {
        if (pattern.test(url)) {
          forbiddenRequests.push(`${method} ${url}`)
        }
      }
    })

    // Navigate to the API server itself to establish same-origin context
    // This avoids CORS issues from about:blank (null origin)
    await page.goto('http://127.0.0.1:5181/api/dev/v1/status')
    await page.waitForTimeout(300)

    // Make a dry-run API call from the browser via fetch
    const fetchResult = await page.evaluate(async (url: string) => {
      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ canonicalName: 'clarify' }),
        })
        return { status: resp.status, ok: resp.ok }
      } catch (err) {
        return { status: 0, ok: false, error: String(err) }
      }
    }, DRY_RUN_URL)

    expect(fetchResult.ok, 'Browser fetch to dry-run API must succeed').toBe(true)
    expect(fetchResult.status, 'Dry-Run API must return 200 from browser').toBe(200)

    // Wait for any pending requests
    await page.waitForTimeout(500)

    // No external requests at all
    expect(externalRequests, 'No external network requests allowed').toEqual([])

    // No provider domain requests
    expect(providerRequests, 'No provider domain requests allowed').toEqual([])

    // No forbidden API patterns
    expect(forbiddenRequests, 'No execute/dispatch/audit write requests allowed').toEqual([])
  })

  test('no execute/dispatch/audit write requests in network traffic', async ({ page }) => {
    test.setTimeout(30_000)

    const writeLikeRequests: string[] = []

    page.on('request', (req) => {
      const url = req.url()
      const method = req.method()

      // Track any POST to tool paths that isn't dry-run
      if (
        url.includes('/api/dev/v1/tools') &&
        method === 'POST' &&
        !url.includes('dry-run')
      ) {
        writeLikeRequests.push(`${method} ${url}`)
      }

      // Track PUT/PATCH/DELETE to tool paths
      if (
        url.includes('/api/dev/v1/tools') &&
        ['PUT', 'PATCH', 'DELETE'].includes(method)
      ) {
        writeLikeRequests.push(`${method} ${url}`)
      }
    })

    // Navigate and make a dry-run call
    await page.goto('about:blank')
    await page.waitForTimeout(300)

    await page.evaluate(async (url: string) => {
      try {
        await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ canonicalName: 'read_file' }),
        })
      } catch {
        // Network error is OK — we're testing request patterns
      }
    }, DRY_RUN_URL)

    await page.waitForTimeout(500)

    expect(writeLikeRequests, 'No tool write-like POST requests allowed').toEqual([])
  })

  test('dry-run POST is classified as dry-run bucket, not write or execution', async ({
    request,
  }) => {
    // Verify via OpenAPI spec that dry-run is not a write or execution route
    const specResp = await request.get('http://127.0.0.1:5181/openapi.json')
    expect(specResp.ok()).toBe(true)
    const spec = await specResp.json()

    const toolPaths = Object.keys(spec.paths).filter((p: string) =>
      p.startsWith('/api/dev/v1/tools'),
    )

    // Phase 1G-04-30: 7 tool routes = 5 GET (policy, catalog, schemas,
    // schemas/{name}, audit-events) + 1 dry-run POST + 1 execute POST.
    expect(toolPaths.length, 'Must have exactly 7 tool routes').toBe(7)

    // Verify GET routes
    const getRoutes = toolPaths.filter((p: string) => {
      const methods = spec.paths[p]
      return 'get' in methods
    })
    expect(getRoutes.length, 'Must have 5 tool GET routes').toBe(5)

    // Verify dry-run + execute POST (both non-write controlled routes)
    const postRoutes = toolPaths.filter((p: string) => {
      const methods = spec.paths[p]
      return 'post' in methods
    })
    expect(postRoutes.length, 'Must have exactly 2 tool POST routes').toBe(2)
    expect(postRoutes).toContain('/api/dev/v1/tools/dry-run')
    expect(postRoutes).toContain('/api/dev/v1/tools/execute')

    // Phase 1G-04-11+: /tools/execute is an intentional controlled execution
    // gate. What must NOT appear are generic dispatch / invoke / call routes.
    const forbiddenIndicators = ['dispatch', 'invoke', 'call']
    for (const path of toolPaths) {
      for (const indicator of forbiddenIndicators) {
        expect(
          path.toLowerCase(),
          `Tool path must not contain forbidden indicator "${indicator}"`,
        ).not.toContain(indicator)
      }
      // "run" is OK only in dry-run context
      if (path.toLowerCase().includes('run') && !path.toLowerCase().includes('dry-run')) {
        expect.fail(`Tool execution route found: ${path}`)
      }
    }
  })
})

// ===================================================================
// 6. UI Non-Exposure Smoke — No new Dry-Run or execution UI
// ===================================================================

test.describe('UI Non-Exposure', () => {
  test('no Execute/Dispatch/Provider-Schema buttons exist in Tools panel', async ({ page }) => {
    test.setTimeout(45_000)

    // Navigate to app — skip if WebUI not running
    try {
      await page.goto('/', { timeout: 5000 })
    } catch {
      test.skip(true, 'WebUI not available on 127.0.0.1:5180. UI non-exposure smoke skipped because Dry-Run UI is not implemented and no stable UI entry exists. Network/API smoke still covers no-execution boundary.')
    }
    await page.evaluate(() => {
      localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle').catch(() => {})
    await page.waitForTimeout(500)

    // Try to open workspace and Tools tab
    const workspacePanel = page.locator('#workspace-panel')
    const isPanelVisible = await workspacePanel.isVisible().catch(() => false)

    if (!isPanelVisible) {
      const panelToggle = page.locator(
        '[aria-label*="workspace panel" i], [aria-label*="toggle workspace" i], [aria-label*="Workspace panel" i]',
      )
      if ((await panelToggle.count()) > 0) {
        await panelToggle.first().click()
        await page.waitForTimeout(300)
      }
    }

    // Check if Tools tab exists
    const toolsTab = page.locator('#workspace-tab-tools')
    const tabVisible = await toolsTab.isVisible().catch(() => false)

    if (!tabVisible) {
      // Tools tab not available — skip UI non-exposure test with explicit note
      test.skip(true, 'Tools tab not available in current UI. UI non-exposure limited to page-level scan.')
    }

    await toolsTab.click()
    await page.waitForTimeout(1000)

    // Scan the full page for forbidden action labels
    for (const label of FORBIDDEN_UI_LABELS) {
      const button = page.locator(`button:has-text("${label}")`)
      const link = page.locator(`a:has-text("${label}")`)
      const menuItem = page.locator(`[role="menuitem"]:has-text("${label}")`)

      const btnCount = await button.count()
      const linkCount = await link.count()
      const menuItemCount = await menuItem.count()

      expect(
        btnCount + linkCount + menuItemCount,
        `Forbidden UI control found: "${label}"`,
      ).toBe(0)
    }

    // No Dry-Run UI panel should exist (not implemented yet)
    const dryRunPanel = page.locator('#tool-dry-run-panel, .tool-dry-run, [aria-label*="Dry Run" i], [aria-label*="Tool Dry-Run" i]')
    const dryRunPanelCount = await dryRunPanel.count()
    expect(dryRunPanelCount, 'No Dry-Run UI panel should exist').toBe(0)
  })

  test('no misleading execution text in existing Tools panel', async ({ page }) => {
    test.setTimeout(45_000)

    try {
      await page.goto('/', { timeout: 5000 })
    } catch {
      test.skip(true, 'WebUI not available on 127.0.0.1:5180. UI non-exposure smoke skipped.')
    }
    await page.evaluate(() => {
      localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle').catch(() => {})
    await page.waitForTimeout(500)

    // Open workspace and Tools tab
    const workspacePanel = page.locator('#workspace-panel')
    const isPanelVisible = await workspacePanel.isVisible().catch(() => false)

    if (!isPanelVisible) {
      const panelToggle = page.locator(
        '[aria-label*="workspace panel" i], [aria-label*="toggle workspace" i], [aria-label*="Workspace panel" i]',
      )
      if ((await panelToggle.count()) > 0) {
        await panelToggle.first().click()
        await page.waitForTimeout(300)
      }
    }

    const toolsTab = page.locator('#workspace-tab-tools')
    const tabVisible = await toolsTab.isVisible().catch(() => false)
    if (!tabVisible) {
      test.skip(true, 'Tools tab not available in current UI.')
    }

    await toolsTab.click()
    await page.waitForTimeout(1000)

    // Verify the Tools section contains "read-only" or "no tools are enabled" safety text
    const toolSection = page.locator('section[aria-label="Tool Policy"]')
    const sectionVisible = await toolSection.isVisible().catch(() => false)

    if (sectionVisible) {
      const sectionText = await toolSection.innerText()
      const lower = sectionText.toLowerCase()

      // Must indicate read-only status
      expect(
        lower.includes('read-only') || lower.includes('no tools are enabled'),
        'Tools panel must indicate read-only or disabled status',
      ).toBe(true)

      // Must NOT indicate execution availability
      expect(lower, 'Must not claim execution available').not.toContain('execution available')
      expect(lower, 'Must not claim tool execution enabled').not.toContain('execution enabled')
      expect(lower, 'Must not have Execute button text').not.toContain('execute tool')
    }
  })
})

// ===================================================================
// 7. A11y Safety Smoke — No A11y regression from Dry-Run API
// ===================================================================

test.describe('A11y Safety', () => {
  test('existing Tools panel landmarks are present and accessible', async ({ page }) => {
    test.setTimeout(45_000)

    try {
      await page.goto('/', { timeout: 5000 })
    } catch {
      test.skip(true, 'WebUI not available on 127.0.0.1:5180. A11y verification limited to existing UI non-exposure checks.')
    }
    await page.evaluate(() => {
      localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle').catch(() => {})
    await page.waitForTimeout(500)

    // Open workspace and Tools tab
    const workspacePanel = page.locator('#workspace-panel')
    const isPanelVisible = await workspacePanel.isVisible().catch(() => false)

    if (!isPanelVisible) {
      const panelToggle = page.locator(
        '[aria-label*="workspace panel" i], [aria-label*="toggle workspace" i], [aria-label*="Workspace panel" i]',
      )
      if ((await panelToggle.count()) > 0) {
        await panelToggle.first().click()
        await page.waitForTimeout(300)
      }
    }

    const toolsTab = page.locator('#workspace-tab-tools')
    const tabVisible = await toolsTab.isVisible().catch(() => false)
    if (!tabVisible) {
      test.skip(true, 'Tools tab not available — A11y check limited to page-level.')
    }

    await toolsTab.click()
    await page.waitForTimeout(1000)

    // Tool Policy section should have accessible label
    const toolSection = page.locator('section[aria-label="Tool Policy"]')
    const sectionVisible = await toolSection.isVisible().catch(() => false)
    if (sectionVisible) {
      const ariaLabel = await toolSection.getAttribute('aria-label')
      expect(ariaLabel, 'Tool Policy section must have aria-label').toBeTruthy()
    }

    // Check for unlabeled buttons in the tools area
    const toolsArea = page.locator('#workspace-panel')
    const buttons = toolsArea.locator('button')
    const buttonCount = await buttons.count()

    for (let i = 0; i < buttonCount; i++) {
      const btn = buttons.nth(i)
      const ariaLabel = await btn.getAttribute('aria-label')
      const textContent = await btn.textContent()
      const title = await btn.getAttribute('title')
      const hasLabel =
        (ariaLabel && ariaLabel.trim().length > 0) ||
        (textContent && textContent.trim().length > 0) ||
        (title && title.trim().length > 0)

      expect(hasLabel, `Button at index ${i} must have accessible label`).toBe(true)
    }

    // No dangerous Execute-type buttons
    const allButtons = page.locator('button')
    const allBtnCount = await allButtons.count()
    for (let i = 0; i < allBtnCount; i++) {
      const btn = allButtons.nth(i)
      const text = (await btn.textContent()) ?? ''
      const ariaLabelAttr = (await btn.getAttribute('aria-label')) ?? ''

      for (const forbidden of FORBIDDEN_UI_LABELS) {
        expect(
          text.toLowerCase(),
          `Button must not contain "${forbidden}"`,
        ).not.toContain(forbidden.toLowerCase())
        expect(
          ariaLabelAttr.toLowerCase(),
          `Button aria-label must not contain "${forbidden}"`,
        ).not.toContain(forbidden.toLowerCase())
      }
    }
  })
})

// ===================================================================
// 8. Execution Flag Invariant — All responses have false flags
// ===================================================================

test.describe('Execution Flag Invariant', () => {
  const testCases = [
    { name: 'R0 tool', tool: 'clarify', expectedDecision: 'would_allow' },
    { name: 'R1 tool', tool: 'read_file', expectedDecision: 'would_allow' },
    { name: 'denylisted tool', tool: 'terminal', expectedDecision: 'would_block' },
    { name: 'unknown tool', tool: 'nonexistent_tool_xyz', expectedExists: false },
  ] as const

  for (const tc of testCases) {
    test(`${tc.name}: all execution flags false`, async ({ request }) => {
      const resp = await request.post(DRY_RUN_URL, {
        data: { canonicalName: tc.tool },
      })
      expect(resp.status()).toBe(200)
      const body = await resp.json()
      const data = body.data

      if ('expectedExists' in tc) {
        expect(data.exists).toBe(tc.expectedExists)
      } else {
        expect(data.exists).toBe(true)
        expect(data.decision).toBe(tc.expectedDecision)
      }

      assertNoExecutionFlags(data)
    })
  }
})
