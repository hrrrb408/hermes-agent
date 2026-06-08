import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright Smoke Test Configuration for Hermes Dev WebUI (Phase 0E-03).
 *
 * Prerequisites:
 *   Dev API  running on 127.0.0.1:5181
 *   WebUI    running on 127.0.0.1:5180
 *
 * This config intentionally disables all artifact capture by default.
 * Do NOT change screenshot/video/trace to "on" without updating .gitignore.
 */
export default defineConfig({
  testDir: './tests/smoke',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [['list']],

  use: {
    baseURL: 'http://127.0.0.1:5180',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },

  projects: [
    {
      name: 'smoke-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
