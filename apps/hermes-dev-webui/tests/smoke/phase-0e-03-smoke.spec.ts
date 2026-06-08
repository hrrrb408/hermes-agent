/**
 * Phase 0E-03: Playwright Smoke Matrix
 *
 * Validates Hermes Dev WebUI across 4 viewports × 5 themes = 20 combinations.
 * Checks: page load, theme application, network safety, console quality,
 * layout stability, read-only enforcement, and path redaction.
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

// Forbidden URL patterns — any matching request fails the test
const FORBIDDEN_PATTERNS = [
  /:5182\b/,
  /\/\/localhost(?![:/]|\b)/,         // bare "localhost" host (not 127.0.0.1)
  /\/\/0\.0\.0\.0/,
  /\/reviews\/.*\/(approve|reject)/,
  /POST.*\/api\/dev\/v1\/reviews/,
  /PATCH.*\/api\/dev\/v1\/reviews/,
  /DELETE.*\/api\/dev\/v1\/reviews/,
  /POST.*\/api\/dev\/v1\/memory(?!\/status)(?!\/categories)(?!\/items[^/])\b/,
  /PATCH.*\/api\/dev\/v1\/memory/,
  /DELETE.*\/api\/dev\/v1\/memory/,
  /POST.*\/api\/dev\/v1\/agent\/run/,
  /POST.*\/api\/dev\/v1\/tools/,
  /POST.*\/api\/dev\/v1\/sessions/,
  /POST.*\/api\/dev\/v1\/messages/,
  /POST.*\/api\/dev\/v1\/files/,
  /DELETE.*\/api\/dev\/v1\/files/,
] as const

// The ONLY allowed POST endpoint
const ALLOWED_POST_PATTERN = /POST.*\/api\/dev\/v1\/context\/preview/

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
    // Only track asset and API failures (not expected backend-offline responses)
    if (status >= 400 && (url.includes('/assets/') || url.includes('/api/'))) {
      collector.assetFailures.push(`${status} ${url}`)
    }
  })

  return collector
}

// ─── Smoke matrix ──────────────────────────────────────────────────────

for (const viewport of VIEWPORTS) {
  for (const theme of THEMES) {
    test(`${viewport.name} · ${theme.id}`, async ({ page }) => {
      test.setTimeout(45_000)

      // Set viewport
      await page.setViewportSize({ width: viewport.width, height: viewport.height })

      // ── Theme setup via localStorage ──
      // Navigate to base page first to set localStorage, then reload with theme.
      await page.goto('/')
      await page.evaluate((themeId) => {
        localStorage.setItem('hermes-dev-webui.theme', themeId)
        localStorage.setItem('hermes-dev-webui.follow-system', 'false')
      }, theme.id)

      // ── Start collectors ──
      const collector = createCollector(page)

      // Track forbidden requests
      const forbiddenRequests: string[] = []
      const allRequests: string[] = []

      page.on('request', (req) => {
        const method = req.method()
        const url = req.url()
        allRequests.push(`${method} ${url}`)

        // Check forbidden patterns
        for (const pattern of FORBIDDEN_PATTERNS) {
          if (pattern.test(`${method} ${url}`)) {
            forbiddenRequests.push(`${method} ${url} (matched ${pattern})`)
          }
        }

        // Check that POST is only to allowed endpoints
        if (method === 'POST' && url.includes('/api/dev/v1/')) {
          if (!ALLOWED_POST_PATTERN.test(`${method} ${url}`)) {
            forbiddenRequests.push(`${method} ${url} (unallowed POST)`)
          }
        }
      })

      // ── Navigate with theme active ──
      await page.goto('/')
      await page.waitForLoadState('networkidle').catch(() => {
        // networkidle may timeout if API is slow — that's OK for smoke
      })

      // Allow some time for the app to settle
      await page.waitForTimeout(1000)

      // ── 1. Page load ──
      // Verify the main app container exists
      const workspacePage = page.locator('.workspace-page')
      await expect(workspacePage).toBeVisible()

      // ── 2. Theme application ──
      const dataTheme = await page.evaluate(() =>
        document.documentElement.getAttribute('data-theme'),
      )
      expect(dataTheme).toBe(theme.id)

      // Verify color-scheme matches
      const colorScheme = await page.evaluate(() =>
        document.documentElement.style.colorScheme,
      )
      expect(colorScheme).toBe(theme.expectedScheme)

      // ── 3. Core UI visibility ──
      // Top status bar
      await expect(page.locator('.top-status-bar')).toBeVisible()

      // Session sidebar (visible or has collapse toggle)
      const sidebar = page.locator('.session-sidebar')
      // The toggle button's aria-label contains "sidebar" (e.g. "Collapse sessions sidebar")
      const sidebarToggle = page.locator('button[aria-controls="session-sidebar"]')

      if (viewport.width >= 1024) {
        // At desktop widths, sidebar nav should be visible
        await expect(sidebar).toBeVisible()
      } else {
        // At narrow widths, sidebar may be collapsed — verify either sidebar or toggle exists
        const sidebarVisible = await sidebar.isVisible().catch(() => false)
        const toggleVisible = await sidebarToggle.isVisible().catch(() => false)
        expect(sidebarVisible || toggleVisible).toBeTruthy()
      }

      // Main chat workspace
      await expect(page.locator('main.chat-workspace')).toBeVisible()

      // Workspace panel (or collapse affordance)
      const workspacePanel = page.locator('#workspace-panel')
      const panelVisible = await workspacePanel.isVisible().catch(() => false)
      const panelToggle = page.locator('[aria-label*="workspace panel" i], [aria-label*="Workspace panel" i]')
      const toggleVisible = await panelToggle.isVisible().catch(() => false)
      expect(panelVisible || toggleVisible).toBeTruthy()

      // ── 4. Forbidden requests ──
      expect(forbiddenRequests).toEqual([])

      // ── 6. Console quality ──
      // Filter out known acceptable console errors
      const significantErrors = collector.errors.filter((msg) => {
        const text = msg.text()
        // Vite dev mode HMR / WebSocket reconnect messages are acceptable
        if (text.includes('vite') && text.includes('ws')) return false
        // Dev API unreachable errors are acceptable (API may not be running)
        if (text.includes('Failed to fetch') || text.includes('NetworkError')) return false
        if (text.includes('ERR_CONNECTION_REFUSED')) return false
        if (text.includes('net::ERR_CONNECTION_REFUSED')) return false
        // Vite client overlay / HMR messages
        if (text.includes('[vite]')) return false
        return true
      })
      expect(significantErrors).toHaveLength(0)

      // Page errors
      expect(collector.pageErrors).toHaveLength(0)

      // CORS errors
      expect(collector.corsErrors).toHaveLength(0)

      // Asset 404s (filter API failures if backend is offline)
      const assetOnly404s = collector.assetFailures.filter(f =>
        f.includes('/assets/') || (f.includes('/api/') && !f.includes('127.0.0.1:5181')),
      )
      expect(assetOnly404s).toHaveLength(0)

      // ── 7. Layout / overflow ──
      const overflow = await page.evaluate(() => {
        const doc = document.documentElement
        return {
          scrollWidth: doc.scrollWidth,
          clientWidth: doc.clientWidth,
        }
      })
      // Allow 2px tolerance for sub-pixel rendering
      expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 2)

      // ── 8. Read-only UI ──
      // Send button must be disabled
      const sendButton = page.locator('.composer__send')
      if (await sendButton.count() > 0) {
        await expect(sendButton.first()).toBeDisabled()
      }

      // Attach button must be disabled
      const attachButton = page.locator('button[aria-label*="Attach" i]')
      if (await attachButton.count() > 0) {
        await expect(attachButton.first()).toBeDisabled()
      }

      // Composer textarea should exist and not submit
      const composer = page.locator('#workspace-composer')
      if (await composer.count() > 0) {
        await expect(composer.first()).toBeVisible()
      }

      // Verify "Read only" or "Read-only" text is present
      const readOnlyNotice = page.locator('text=/read.only/i')
      await expect(readOnlyNotice.first()).toBeVisible()

      // ── 9. Path redaction ──
      // Check page text does not contain raw filesystem paths
      const bodyText = await page.locator('body').innerText()
      const pathPatterns = [
        /\/Users\/[^\s]/,
        /\/home\/[^\s]/,
      ]
      for (const pattern of pathPatterns) {
        expect(
          pattern.test(bodyText),
          `Page text contains raw filesystem path matching ${pattern}`,
        ).toBeFalsy()
      }
      // file:// URIs are also forbidden in page text
      expect(bodyText).not.toContain('file://')
    })
  }
}

// ─── Cross-panel drill-down (one comprehensive check per viewport) ─────
// Exercises each workspace panel tab to verify the full API surface.
// Only runs once per viewport with the default theme (obsidian).

for (const viewport of VIEWPORTS) {
  test(`${viewport.name} · panel drill-down`, async ({ page }) => {
    test.setTimeout(45_000)

    await page.setViewportSize({ width: viewport.width, height: viewport.height })

    // Setup theme
    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('hermes-dev-webui.theme', 'obsidian')
      localStorage.setItem('hermes-dev-webui.follow-system', 'false')
    })

    // Track API requests
    const apiCalls: string[] = []
    page.on('request', (req) => {
      if (req.url().includes('127.0.0.1:5181')) {
        apiCalls.push(`${req.method()} ${req.url()}`)
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle').catch(() => {})

    // Ensure workspace panel is visible
    const workspacePanel = page.locator('#workspace-panel')
    const isPanelVisible = await workspacePanel.isVisible().catch(() => false)

    if (isPanelVisible || viewport.width >= 1024) {
      // If panel is collapsed, expand it
      if (!isPanelVisible) {
        const panelToggle = page.locator('[aria-label*="workspace panel" i], [aria-label*="toggle workspace" i], [aria-label*="Workspace panel" i]')
        if (await panelToggle.count() > 0) {
          await panelToggle.first().click()
          await page.waitForTimeout(300)
        }
      }

      // Click through each tab
      const tabIds = ['files', 'memory', 'context', 'reviews', 'agent']
      for (const tabId of tabIds) {
        const tab = page.locator(`#workspace-tab-${tabId}`)
        if (await tab.count() > 0) {
          await tab.first().click()
          await page.waitForTimeout(500)
        }
      }
    }

    // Wait for any API calls to complete
    await page.waitForTimeout(1000)

    // Verify no forbidden calls in the drill-down
    for (const call of apiCalls) {
      for (const pattern of FORBIDDEN_PATTERNS) {
        expect(
          pattern.test(call),
          `Drill-down found forbidden request: ${call}`,
        ).toBeFalsy()
      }
      if (call.startsWith('POST') && call.includes('/api/dev/v1/')) {
        expect(
          ALLOWED_POST_PATTERN.test(call),
          `Drill-down found unallowed POST: ${call}`,
        ).toBeTruthy()
      }
    }
  })
}
