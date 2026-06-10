/**
 * Phase 1G-02E: Tool Policy Integration Browser Smoke
 *
 * Validates the Tool Policy read-only panel against real Dev API.
 * Tests cover: Policy Overview, Catalog, Search/Filter/Sort/Pagination,
 * Tool Selection/Detail, Accessibility, Read-Only Boundary,
 * Network Safety, Error/Retry, and Theme/Viewport matrix.
 *
 * Prerequisites:
 *   - Dev API  on 127.0.0.1:5181  (HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev)
 *   - WebUI    on 127.0.0.1:5180  (pnpm dev)
 *
 * No screenshots, traces, videos, or HAR are captured by default.
 */
import { test, expect, type Page, type ConsoleMessage } from '@playwright/test'

// ─── Matrix definition ────────────────────────────────────────────────

const VIEWPORTS = [
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1280x800', width: 1280, height: 800 },
  { name: '1024x768', width: 1024, height: 768 },
  { name: '768x900',  width: 768,  height: 900 },
] as const

const THEMES = [
  { id: 'obsidian',     expectedScheme: 'dark'  },
  { id: 'paper',        expectedScheme: 'light' },
  { id: 'song',         expectedScheme: 'dark'  },
  { id: 'ink',          expectedScheme: 'light' },
  { id: 'sakura-night', expectedScheme: 'dark'  },
] as const

// ─── Helpers ───────────────────────────────────────────────────────────

interface ConsoleCollector {
  errors: ConsoleMessage[]
  pageErrors: Error[]
  corsErrors: string[]
  assetFailures: string[]
}

function createCollector(page: Page): ConsoleCollector {
  const collector: ConsoleCollector = {
    errors: [],
    pageErrors: [],
    corsErrors: [],
    assetFailures: [],
  }

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      collector.errors.push(msg)
    }
  })

  page.on('pageerror', (err) => {
    collector.pageErrors.push(err)
  })

  page.on('requestfailed', (req) => {
    const url = req.url()
    const failure = req.failure()?.errorText ?? 'unknown'
    if (failure.toLowerCase().includes('cors')) {
      collector.corsErrors.push(`${url}: ${failure}`)
    }
    collector.assetFailures.push(`${url}: ${failure}`)
  })

  page.on('response', (res) => {
    const url = res.url()
    const status = res.status()
    if (status >= 400 && (url.includes('/assets/') || url.includes('/api/'))) {
      collector.assetFailures.push(`${status} ${url}`)
    }
  })

  return collector
}

/** Filter known-harmless console errors */
function filterSignificantErrors(errors: ConsoleMessage[]): ConsoleMessage[] {
  return errors.filter((msg) => {
    const text = msg.text()
    if (text.includes('vite') && text.includes('ws')) return false
    if (text.includes('Failed to fetch') || text.includes('NetworkError')) return false
    if (text.includes('ERR_CONNECTION_REFUSED') || text.includes('net::ERR_CONNECTION_REFUSED')) return false
    if (text.includes('[vite]')) return false
    return true
  })
}

/**
 * Navigate to the app, set theme, open workspace panel, and click Tools tab.
 * Returns the console collector and request tracking arrays.
 */
async function setupToolsPanel(
  page: Page,
  themeId: string,
  viewport?: { width: number; height: number },
) {
  if (viewport) {
    await page.setViewportSize(viewport)
  }

  // Set theme via localStorage
  await page.goto('/')
  await page.evaluate((tid) => {
    localStorage.setItem('hermes-dev-webui.theme', tid)
    localStorage.setItem('hermes-dev-webui.follow-system', 'false')
  }, themeId)

  // Start collectors
  const collector = createCollector(page)
  const toolApiRequests: string[] = []

  page.on('request', (req) => {
    if (req.url().includes('/api/dev/v1/tools')) {
      toolApiRequests.push(`${req.method()} ${req.url()}`)
    }
  })

  // Navigate with theme
  await page.goto('/')
  await page.waitForLoadState('networkidle').catch(() => {})
  await page.waitForTimeout(500)

  // Ensure workspace panel is visible
  const workspacePanel = page.locator('#workspace-panel')
  const isPanelVisible = await workspacePanel.isVisible().catch(() => false)

  if (!isPanelVisible) {
    // Try to expand it
    const panelToggle = page.locator(
      '[aria-label*="workspace panel" i], [aria-label*="toggle workspace" i], [aria-label*="Workspace panel" i]',
    )
    if (await panelToggle.count() > 0) {
      await panelToggle.first().click()
      await page.waitForTimeout(300)
    }
  }

  // Click the Tools tab
  const toolsTab = page.locator('#workspace-tab-tools')
  await expect(toolsTab).toBeVisible({ timeout: 5000 })
  await toolsTab.click()
  await page.waitForTimeout(500)

  return { collector, toolApiRequests }
}

// ─── 1. Full functional integration test (obsidian, 1440×900) ─────────

test.describe('Tool Policy Full Integration', () => {
  test('Policy Overview loads from real API', async ({ page }) => {
    const { collector, toolApiRequests } = await setupToolsPanel(page, 'obsidian', {
      width: 1440,
      height: 900,
    })

    // ── Policy Overview should be default sub-tab ──
    const overviewTab = page.locator('#tool-policy-tab-overview')
    await expect(overviewTab).toHaveClass(/tool-policy-tab--active/)

    // ── Wait for policy data ──
    await page.waitForTimeout(1500)

    // ── Tool Policy panel section visible ──
    const panelSection = page.locator('section[aria-label="Tool Policy"]')
    await expect(panelSection).toBeVisible()

    // ── Safety notice from Overview ──
    const overviewContent = page.locator('.tool-policy-overview')
    await expect(overviewContent).toBeVisible()

    const overviewText = await overviewContent.innerText()
    expect(overviewText.toLowerCase()).toContain('read-only')

    // ── Wait for policy API to complete ──
    await page.waitForTimeout(1000)

    const fullText = await overviewContent.innerText()
    // Verify key safety messages appear after data loads
    expect(fullText.toLowerCase()).toContain('no tools are enabled')

    // ── Risk distribution ──
    const riskGrid = page.locator('.tp-risk-grid')
    await expect(riskGrid).toBeVisible()
    const riskText = await riskGrid.innerText()
    expect(riskText).toContain('R0')
    expect(riskText).toContain('R5')

    // ── API calls ──
    const policyCalls = toolApiRequests.filter((r) => r.includes('/tools/policy'))
    expect(policyCalls.length).toBeGreaterThanOrEqual(1)
    expect(policyCalls.every((r) => r.startsWith('GET'))).toBeTruthy()

    // ── Console quality ──
    expect(filterSignificantErrors(collector.errors)).toHaveLength(0)
    expect(collector.pageErrors).toHaveLength(0)
    expect(collector.corsErrors).toHaveLength(0)
  })

  test('Catalog loads with correct defaults from real API', async ({ page }) => {
    const { toolApiRequests } = await setupToolsPanel(page, 'obsidian', {
      width: 1440,
      height: 900,
    })

    // Switch to Catalog sub-tab
    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // ── Catalog should be visible ──
    const catalogPanel = page.locator('.tool-catalog')
    await expect(catalogPanel).toBeVisible()

    // ── Pagination info ──
    const pageText = await page.locator('.tc-page-info').innerText()
    expect(pageText).toContain('71 tools')
    expect(pageText).toContain('Page 1 of 3')

    // ── Tool list items ──
    const items = page.locator('.tc-item')
    const count = await items.count()
    expect(count).toBe(25) // default pageSize

    // ── Each item shows key fields ──
    const firstItem = items.first()
    await expect(firstItem.locator('.tc-item__name')).toBeVisible()
    await expect(firstItem.locator('.tc-item__risk')).toBeVisible()
    await expect(firstItem.locator('.tc-item__status')).toBeVisible()
    await expect(firstItem.locator('.tc-item__allowed')).toContainText('Allowed: No')

    // ── API calls ──
    const catalogCalls = toolApiRequests.filter((r) => r.includes('/tools/catalog'))
    expect(catalogCalls.length).toBeGreaterThanOrEqual(1)
    expect(catalogCalls.every((r) => r.startsWith('GET'))).toBeTruthy()
  })

  test('Search filters catalog correctly', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Type search
    const searchInput = page.locator('#tc-search')
    await searchInput.fill('clarify')
    await page.waitForTimeout(600) // debounce 300ms + API

    // Should contain clarify
    const items = page.locator('.tc-item')
    const count = await items.count()
    expect(count).toBeGreaterThanOrEqual(1)

    const names = await items.locator('.tc-item__name').allTextContents()
    expect(names.some((n) => n.includes('clarify'))).toBeTruthy()

    // Clear search
    await searchInput.clear()
    await page.waitForTimeout(500)
    const restoredCount = await page.locator('.tc-item').count()
    expect(restoredCount).toBe(25)
  })

  test('Risk filter works correctly', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Select R0
    const riskSelect = page.locator('#tc-risk')
    await riskSelect.selectOption('R0')
    await page.waitForTimeout(1000)

    // Should show only R0 tools (clarify is the only R0)
    const items = page.locator('.tc-item')
    const count = await items.count()
    expect(count).toBeGreaterThanOrEqual(1)

    // Verify all visible items have R0 badge
    const badges = await items.locator('.tc-item__risk').allTextContents()
    for (const badge of badges) {
      expect(badge.trim()).toBe('R0')
    }

    // Clear filter
    await riskSelect.selectOption('')
    await page.waitForTimeout(500)
    const restoredCount = await page.locator('.tc-item').count()
    expect(restoredCount).toBe(25)
  })

  test('Policy Status filter: Candidate shows candidates', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Select CANDIDATE
    const statusSelect = page.locator('#tc-status')
    await statusSelect.selectOption('CANDIDATE')
    await page.waitForTimeout(1000)

    const items = page.locator('.tc-item')
    const count = await items.count()
    expect(count).toBe(6) // 6 candidates

    // Verify all are candidate
    const notices = await items.locator('.tc-item__notice').allTextContents()
    for (const notice of notices) {
      expect(notice).toContain('Not enabled')
    }

    // Clear
    await statusSelect.selectOption('')
    await page.waitForTimeout(500)
  })

  test('Policy Status filter: Permanently Denied shows terminal', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Increase page size to fit all denied tools
    await page.locator('#tc-pagesize').selectOption('100')
    await page.waitForTimeout(500)

    const statusSelect = page.locator('#tc-status')
    await statusSelect.selectOption('PERMANENTLY_DENIED')
    await page.waitForTimeout(1000)

    const items = page.locator('.tc-item')
    const count = await items.count()
    expect(count).toBe(26) // 26 permanently denied

    // Verify terminal is in the list
    const names = await items.locator('.tc-item__name').allTextContents()
    expect(names).toContain('terminal')

    // Clear
    await statusSelect.selectOption('')
    await page.waitForTimeout(500)
  })

  test('Policy Status filter: Statically Allowed shows empty', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    const statusSelect = page.locator('#tc-status')
    await statusSelect.selectOption('STATICALLY_ALLOWED')
    await page.waitForTimeout(1000)

    // Should show empty
    const emptyMsg = page.locator('.panel-empty')
    await expect(emptyMsg).toBeVisible()
    const emptyText = await emptyMsg.innerText()
    expect(emptyText).toContain('No tools match the current filters')

    // Clear
    await statusSelect.selectOption('')
    await page.waitForTimeout(500)
  })

  test('Sort works correctly', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    const sortSelect = page.locator('#tc-sort')

    // Name Z-A
    await sortSelect.selectOption('nameDesc')
    await page.waitForTimeout(1000)
    const itemsZA = await page.locator('.tc-item .tc-item__name').first().innerText()

    // Name A-Z
    await sortSelect.selectOption('nameAsc')
    await page.waitForTimeout(1000)
    const itemsAZ = await page.locator('.tc-item .tc-item__name').first().innerText()

    // Z-A first should be alphabetically after A-Z first
    expect(itemsZA.localeCompare(itemsAZ)).toBeGreaterThanOrEqual(0)

    // Risk High-Low
    await sortSelect.selectOption('riskDesc')
    await page.waitForTimeout(1000)
    const firstRiskHigh = await page.locator('.tc-item .tc-item__risk').first().innerText()

    // Risk Low-High
    await sortSelect.selectOption('riskAsc')
    await page.waitForTimeout(1000)
    const firstRiskLow = await page.locator('.tc-item .tc-item__risk').first().innerText()

    // R5 > R0 numerically
    const riskOrder = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5']
    expect(riskOrder.indexOf(firstRiskHigh.trim())).toBeGreaterThanOrEqual(
      riskOrder.indexOf(firstRiskLow.trim()),
    )
  })

  test('Pagination works correctly', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Default: Page 1 of 3, 25 items
    await expect(page.locator('.tc-page-info')).toContainText('Page 1 of 3')

    // Go to page 2
    await page.locator('.tc-page-btn', { hasText: 'Next' }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('.tc-page-info')).toContainText('Page 2 of 3')

    // Go back to page 1
    await page.locator('.tc-page-btn', { hasText: 'Prev' }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('.tc-page-info')).toContainText('Page 1 of 3')

    // Change page size to 100
    await page.locator('#tc-pagesize').selectOption('100')
    await page.waitForTimeout(1000)
    await expect(page.locator('.tc-page-info')).toContainText('Page 1 of 1')
    const allItems = await page.locator('.tc-item').count()
    expect(allItems).toBe(71)

    // Reset page size
    await page.locator('#tc-pagesize').selectOption('25')
    await page.waitForTimeout(500)
  })

  test('Tool Selection shows correct detail for Candidate tool', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Search for clarify
    await page.locator('#tc-search').fill('clarify')
    await page.waitForTimeout(600)

    // Click on clarify
    await page.locator('.tc-item', { hasText: 'clarify' }).click()
    await page.waitForTimeout(300)

    // Detail should be visible
    const detail = page.locator('.tc-detail')
    await expect(detail).toBeVisible()

    const detailText = await detail.innerText()
    // Candidate checks
    expect(detailText).toContain('clarify')
    expect(detailText).toContain('Candidate Allowlisted')
    expect(detailText).toContain('Yes') // candidateAllowlisted = Yes
    expect(detailText).toContain('Allowed')
    expect(detailText).toContain('No') // allowed = No
    expect(detailText).toContain('Unavailable') // execution unavailable

    // Must NOT contain sensitive info
    expect(detailText).not.toContain('Handler')
    expect(detailText).not.toContain('Callable')
    expect(detailText).not.toContain('api_key')
    expect(detailText).not.toContain('secret')
  })

  test('Tool Selection shows correct detail for Denylisted tool', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Search for terminal
    await page.locator('#tc-search').fill('terminal')
    await page.waitForTimeout(600)

    // Click on terminal
    await page.locator('.tc-item', { hasText: 'terminal' }).click()
    await page.waitForTimeout(300)

    const detail = page.locator('.tc-detail')
    await expect(detail).toBeVisible()

    const detailText = await detail.innerText()
    expect(detailText).toContain('terminal')
    expect(detailText).toContain('Permanently Denied')
    expect(detailText).toContain('Yes') // permanentlyDenied = Yes
    expect(detailText).toContain('No') // allowed = No
    expect(detailText).toContain('Unavailable') // execution unavailable

    // Must NOT contain sensitive info
    expect(detailText).not.toContain('Handler')
    expect(detailText).not.toContain('api_key')
    expect(detailText).not.toContain('secret')
  })

  test('Keyboard navigation works in catalog', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Focus first item via click, then verify keyboard navigation
    const firstItem = page.locator('.tc-item').first()
    await firstItem.click()
    await page.waitForTimeout(200)

    // The list container handles keyboard events; press ArrowDown on it
    const listbox = page.locator('.tc-list')
    await listbox.focus()
    // Move focus back to first item via Home
    await page.keyboard.press('Home')
    await page.waitForTimeout(200)

    const firstId = await page.evaluate(() => document.activeElement?.id)
    expect(firstId).toContain('tool-item-')

    // ArrowDown should move to a different item
    await page.keyboard.press('ArrowDown')
    await page.waitForTimeout(200)

    const afterDownFocus = await page.evaluate(() => document.activeElement?.id)
    expect(afterDownFocus).toBeTruthy()
    expect(afterDownFocus).toContain('tool-item-')
    // Focus should have moved to a different tool item
    expect(afterDownFocus).not.toBe(firstId)

    // Enter should select
    await page.keyboard.press('Enter')
    await page.waitForTimeout(300)

    // Detail should be visible
    const detail = page.locator('.tc-detail')
    await expect(detail).toBeVisible()
  })
})

// ─── 2. HTTP Method Safety ─────────────────────────────────────────────

test.describe('HTTP Method Safety', () => {
  test('Only GET requests to /tools/ endpoints', async ({ page }) => {
    const methodLog: string[] = []

    page.on('request', (req) => {
      if (req.url().includes('/api/dev/v1/tools')) {
        methodLog.push(`${req.method()} ${req.url()}`)
      }
    })

    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    // Navigate through both sub-tabs
    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Search to trigger more requests
    await page.locator('#tc-search').fill('read')
    await page.waitForTimeout(600)
    await page.locator('#tc-search').clear()
    await page.waitForTimeout(600)

    // Verify all are GET
    for (const entry of methodLog) {
      expect(
        entry.startsWith('GET'),
        `Non-GET tool request found: ${entry}`,
      ).toBeTruthy()
    }

    // Verify no write endpoints
    const writePatterns = [
      /POST.*\/tools/,
      /PUT.*\/tools/,
      /PATCH.*\/tools/,
      /DELETE.*\/tools/,
      /\/tools\/schema\/preview/,
      /\/tools\/calls/,
    ]
    for (const entry of methodLog) {
      for (const pattern of writePatterns) {
        expect(
          pattern.test(entry),
          `Forbidden tool request: ${entry}`,
        ).toBeFalsy()
      }
    }
  })
})

// ─── 3. Network Safety (no external/Provider requests) ─────────────────

test.describe('Network Safety', () => {
  test('No external business or Provider requests', async ({ page }) => {
    const externalRequests: string[] = []

    page.on('request', (req) => {
      const url = req.url()
      // Allow only localhost and 127.0.0.1
      if (
        !url.includes('127.0.0.1') &&
        !url.includes('localhost') &&
        !url.startsWith('data:')
      ) {
        externalRequests.push(`${req.method()} ${url}`)
      }
    })

    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    // Exercise both tabs
    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    expect(externalRequests).toHaveLength(0)
  })
})

// ─── 4. Read-Only Boundary ─────────────────────────────────────────────

test.describe('Read-Only Boundary', () => {
  test('No mutation controls exist in Tools panel', async ({ page }) => {
    test.setTimeout(45_000)
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    // Forbidden action labels (as button/link/menuitem text)
    const forbiddenActions = [
      'Enable', 'Disable', 'Execute', 'Run Tool', 'Try Tool', 'Test Tool',
      'Preview Schema', 'Send Schema', 'Promote',
      'Add to Allowlist', 'Remove from Allowlist',
      'Add to Denylist', 'Remove from Denylist',
      'Edit Policy', 'Save Policy', 'Apply Policy',
    ]

    // Check that no buttons, links, or menuitems with these labels exist
    // Scope to the Tool Policy section only
    const toolSection = page.locator('section[aria-label="Tool Policy"]')

    for (const action of forbiddenActions) {
      const button = toolSection.locator(`button:has-text("${action}")`)
      const link = toolSection.locator(`a:has-text("${action}")`)
      const menuItem = toolSection.locator(`[role="menuitem"]:has-text("${action}")`)

      const btnCount = await button.count()
      const linkCount = await link.count()
      const menuItemCount = await menuItem.count()

      expect(
        btnCount + linkCount + menuItemCount,
        `Found forbidden control: "${action}"`,
      ).toBe(0)
    }

    // Also check in Catalog
    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    for (const action of forbiddenActions) {
      const button = toolSection.locator(`button:has-text("${action}")`)
      const btnCount = await button.count()
      expect(btnCount, `Found forbidden control in catalog: "${action}"`).toBe(0)
    }
  })
})

// ─── 5. Error / Retry ─────────────────────────────────────────────────

test.describe('Error and Retry', () => {
  test('Catalog error shows retry button', async ({ page }) => {
    test.setTimeout(45_000)

    // Intercept catalog requests to return error once
    let shouldFail = true
    await page.route('**/api/dev/v1/tools/catalog**', async (route) => {
      if (shouldFail) {
        shouldFail = false
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal Server Error' }),
        })
      } else {
        // Pass through to real API
        await route.continue()
      }
    })

    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Error should be visible
    const errorPanel = page.locator('.panel-error')
    await expect(errorPanel).toBeVisible()
    await expect(errorPanel).toHaveAttribute('role', 'alert')

    // Retry button
    const retryBtn = page.locator('.panel-retry-btn', { hasText: 'Retry' })
    await expect(retryBtn).toBeVisible()

    // Click retry — should now succeed (real API)
    await retryBtn.click()
    await page.waitForTimeout(1500)

    // Catalog should now be loaded
    const items = page.locator('.tc-item')
    await expect(items.first()).toBeVisible({ timeout: 5000 })
  })

  test('Rapid search settles to final result', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Rapidly type multiple search values
    const searchInput = page.locator('#tc-search')
    await searchInput.fill('r')
    await page.waitForTimeout(50)
    await searchInput.fill('re')
    await page.waitForTimeout(50)
    await searchInput.fill('rea')
    await page.waitForTimeout(50)
    await searchInput.fill('read')

    // Wait for debounce + API
    await page.waitForTimeout(1000)

    // Should show results for "read"
    const items = page.locator('.tc-item')
    const count = await items.count()
    expect(count).toBeGreaterThanOrEqual(1)

    // Verify "read_file" is in results (exact match of final search)
    const names = await items.locator('.tc-item__name').allTextContents()
    expect(names.some((n) => n.includes('read_file'))).toBeTruthy()

    // No abort errors displayed
    const errorPanel = page.locator('.panel-error')
    expect(await errorPanel.isVisible()).toBeFalsy()
  })
})

// ─── 6. Theme / Viewport Matrix ───────────────────────────────────────
// Layout and safety smoke across all 20 combinations.

for (const viewport of VIEWPORTS) {
  for (const theme of THEMES) {
    test(`${viewport.name} · ${theme.id} · tools panel layout`, async ({ page }) => {
      test.setTimeout(45_000)

      const { collector } = await setupToolsPanel(page, theme.id, {
        width: viewport.width,
        height: viewport.height,
      })

      // ── Tool Policy section visible ──
      const panelSection = page.locator('section[aria-label="Tool Policy"]')
      await expect(panelSection).toBeVisible()

      // ── Read-only badge ──
      const badge = panelSection.locator('.panel-badge')
      await expect(badge).toContainText('Read-only')

      // ── Sub-tabs visible ──
      const overviewTab = page.locator('#tool-policy-tab-overview')
      const catalogTab = page.locator('#tool-policy-tab-catalog')
      await expect(overviewTab).toBeVisible()
      await expect(catalogTab).toBeVisible()

      // ── Overview content ──
      await page.waitForTimeout(1500)
      const overviewContent = page.locator('.tool-policy-overview')
      if (await overviewContent.isVisible()) {
        const overviewText = await overviewContent.innerText()
        expect(overviewText.toLowerCase()).toContain('read-only')
      }

      // ── Switch to Catalog ──
      await catalogTab.click()
      await page.waitForTimeout(1500)

      const catalogPanel = page.locator('.tool-catalog')
      await expect(catalogPanel).toBeVisible()

      // ── Filters visible ──
      const filters = page.locator('.tc-filters')
      await expect(filters).toBeVisible()

      // ── Catalog list accessible ──
      const list = page.locator('.tc-list')
      if (await list.isVisible()) {
        const listItems = page.locator('.tc-item')
        const count = await listItems.count()
        expect(count).toBeGreaterThanOrEqual(1)
      }

      // ── Horizontal overflow check (document-level) ──
      const overflow = await page.evaluate(() => {
        const doc = document.documentElement
        return {
          scrollWidth: doc.scrollWidth,
          clientWidth: doc.clientWidth,
        }
      })
      expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 2)

      // Note: Panel-internal horizontal scroll is acceptable because the
      // catalog list + detail side-by-side layout is designed for scrolling
      // within the workspace panel container. Document-level overflow
      // (checked above) is the hard boundary.

      // ── Console / CORS / 404 ──
      expect(filterSignificantErrors(collector.errors)).toHaveLength(0)
      expect(collector.pageErrors).toHaveLength(0)
      expect(collector.corsErrors).toHaveLength(0)

      // Asset 404s (only for local assets)
      const assetOnly404s = collector.assetFailures.filter((f) =>
        f.includes('/assets/') || (f.includes('/api/') && !f.includes('127.0.0.1:5181')),
      )
      expect(assetOnly404s).toHaveLength(0)
    })
  }
}

// ─── 7. Accessibility ARIA checks ─────────────────────────────────────

test.describe('Accessibility', () => {
  test('Workspace Tools tab has correct ARIA', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    // Tools tab should be focusable
    const toolsTab = page.locator('#workspace-tab-tools')
    await expect(toolsTab).toBeVisible()
    expect(await toolsTab.getAttribute('role')).toBe('tab')
    expect(await toolsTab.getAttribute('aria-selected')).toBe('true')

    // Sub-tabs
    const overviewTab = page.locator('#tool-policy-tab-overview')
    expect(await overviewTab.getAttribute('role')).toBe('tab')
    expect(await overviewTab.getAttribute('aria-selected')).toBe('true')

    // Catalog tab
    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await catalogTab.click()
    await page.waitForTimeout(1500)

    // Catalog list should have listbox role
    const listbox = page.locator('.tc-list')
    expect(await listbox.getAttribute('role')).toBe('listbox')

    // Items should have option role
    const firstItem = listbox.locator('.tc-item').first()
    expect(await firstItem.getAttribute('role')).toBe('option')

    // Select a tool and verify detail has region role
    await firstItem.click()
    await page.waitForTimeout(300)

    const detail = page.locator('.tc-detail')
    await expect(detail).toBeVisible()
    expect(await detail.getAttribute('role')).toBe('region')
  })

  test('Sub-tab keyboard navigation', async ({ page }) => {
    await setupToolsPanel(page, 'obsidian', { width: 1440, height: 900 })

    // Focus the active sub-tab
    const activeTab = page.locator('.tool-policy-tab--active')
    await activeTab.focus()

    // ArrowRight should move to Catalog
    await page.keyboard.press('ArrowRight')
    await page.waitForTimeout(200)

    // Catalog should now be active
    const catalogTab = page.locator('#tool-policy-tab-catalog')
    await expect(catalogTab).toHaveClass(/tool-policy-tab--active/)

    // ArrowLeft should go back to Overview
    await page.keyboard.press('ArrowLeft')
    await page.waitForTimeout(200)

    const overviewTab = page.locator('#tool-policy-tab-overview')
    await expect(overviewTab).toHaveClass(/tool-policy-tab--active/)
  })
})
