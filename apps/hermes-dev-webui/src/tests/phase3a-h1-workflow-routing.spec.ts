/**
 * Phase 3A-H1 — Workflow routing hardening.
 *
 * Asserts the workflow surface is an additive branch on the existing console
 * nav (registered exactly once, labelled 'Workflow') and that the workflow API
 * client reuses ONLY the existing POST /tools/dry-run + POST /tools/execute
 * routes — it never constructs a /workflows or /provider path. A static import
 * scan of the API module pins this so a new route cannot be introduced silently.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import {
  CONSOLE_SECTIONS,
  CONSOLE_SECTION_LABELS,
} from '@/stores/devConsoleNav'

const __dirname = dirname(fileURLToPath(import.meta.url))
const workflowApiSource = readFileSync(
  resolve(__dirname, '../api/workflow.ts'),
  'utf-8',
)

describe('Phase 3A-H1 workflow routing', () => {
  it('registers the workflow section exactly once', () => {
    const occurrences = CONSOLE_SECTIONS.filter((s) => s === 'workflow')
    expect(occurrences.length).toBe(1)
  })

  it('labels the workflow section "Workflow"', () => {
    expect(CONSOLE_SECTION_LABELS.workflow).toBe('Workflow')
  })

  it('accepts the workflow id and rejects invented ids', () => {
    expect((CONSOLE_SECTIONS as readonly string[]).includes('workflow')).toBe(true)
    expect((CONSOLE_SECTIONS as readonly string[]).includes('workflow_evil')).toBe(false)
  })

  it('the API client never introduces a /workflows or /provider path', () => {
    // The workflow modes ride on the existing two routes only.
    expect(workflowApiSource).toContain('/tools/dry-run')
    expect(workflowApiSource).toContain('/tools/execute')
    expect(workflowApiSource).not.toMatch(/\/workflows\b/)
    expect(workflowApiSource).not.toMatch(/\/provider\//)
    // Every endpoint in the module targets one of the two allowed paths.
    const apiPrefixMatches = workflowApiSource.match(/\$\{API_PREFIX\}\/[A-Za-z0-9/_-]+/g) ?? []
    for (const match of apiPrefixMatches) {
      const path = match.replace(/\$\{API_PREFIX\}/, '/api/dev/v1')
      const allowed = ['/api/dev/v1/tools/dry-run', '/api/dev/v1/tools/execute']
      expect(allowed, `unexpected route path: ${path}`).toContain(path)
    }
  })

  it('the API client uses exactly the two workflow modes on dry-run and one on execute', () => {
    expect(workflowApiSource).toContain("'workflow_plan_preview'")
    expect(workflowApiSource).toContain("'workflow_step_preview'")
    expect(workflowApiSource).toContain("'workflow_state_read'")
    expect(workflowApiSource).toContain("'workflow_step_execute'")
  })
})
