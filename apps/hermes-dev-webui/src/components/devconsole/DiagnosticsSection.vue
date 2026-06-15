<script setup lang="ts">
import {
  FROZEN_PHASE_TIMELINE,
  FROZEN_PRODUCTION_GATEWAY_PID,
  FROZEN_RELEASE_IDS,
  FROZEN_ROUTE_GOVERNANCE,
  FROZEN_STATIC_ALLOWLIST,
  FROZEN_STATIC_WRITE_TOOLS,
} from '@/lib/frozenBaseline'

/**
 * Dev Console → Diagnostics section (Phase 2E).
 *
 * Dev environment + release status. These values are the frozen baseline
 * (verified by gates) — the section does NOT execute `dev_environment_read` /
 * `release_status_read` live, because doing so would consume confirmation
 * tokens and pollute the audit trail. The smoke preflight + backend invariant
 * tests continuously verify the live values against this baseline.
 */
const devHome = '/Users/huangruibang/Code/hermes-home-dev'
const sourceRoot = '/Users/huangruibang/Code/hermes-agent-dev'
</script>

<template>
  <section class="devconsole-section" aria-label="Diagnostics">
    <div class="devconsole-section__intro">
      <h2>Diagnostics</h2>
      <p>
        Dev environment + release status. Values are the frozen baseline
        verified by the smoke preflight and backend invariant tests. The console
        does not execute the read-only inspection tools live from this view —
        that would consume confirmation tokens and write spurious audit events.
      </p>
    </div>

    <div class="devconsole-card">
      <h3>Dev environment</h3>
      <dl class="devconsole-kv">
        <dt>Source root</dt><dd>{{ sourceRoot }}</dd>
        <dt>Dev HERMES_HOME</dt><dd>{{ devHome }}</dd>
        <dt>Production home</dt><dd>~/.hermes — never accessed</dd>
        <dt>Dev API</dt><dd>127.0.0.1:5181</dd>
        <dt>Dev WebUI</dt><dd>127.0.0.1:5180</dd>
        <dt>Production gateway PID</dt><dd>{{ FROZEN_PRODUCTION_GATEWAY_PID }} (read-only)</dd>
        <dt>Bind</dt><dd>127.0.0.1 only</dd>
      </dl>
    </div>

    <div class="devconsole-card">
      <h3>Release status</h3>
      <dl class="devconsole-kv">
        <dt>Phase 1G</dt><dd>{{ FROZEN_RELEASE_IDS.phase1gStatus }}</dd>
        <dt>Phase 2</dt><dd>{{ FROZEN_RELEASE_IDS.phase2Status }}</dd>
        <dt>Phase 2E</dt><dd>{{ FROZEN_RELEASE_IDS.phase2eStatus }}</dd>
        <dt>Phase 3</dt><dd>{{ FROZEN_RELEASE_IDS.phase3Status }}</dd>
      </dl>
      <h4 class="devconsole-note" style="margin: var(--space-3, 12px) 0 var(--space-1, 4px); text-transform: uppercase; letter-spacing: 0.05em;">Phase timeline</h4>
      <ul class="devconsole-note" style="margin:0; padding-left: var(--space-4, 16px); line-height: 1.7;">
        <li v-for="entry in FROZEN_PHASE_TIMELINE" :key="entry.phase">
          <strong>{{ entry.phase }}</strong> — {{ entry.status }}
        </li>
      </ul>
    </div>

    <div class="devconsole-card">
      <h3>Route governance (frozen baseline)</h3>
      <dl class="devconsole-kv">
        <dt>OpenAPI / runtime</dt><dd>{{ FROZEN_ROUTE_GOVERNANCE.openApiPaths }} / {{ FROZEN_ROUTE_GOVERNANCE.runtimeRoutes }}</dd>
        <dt>Tool GET</dt><dd>{{ FROZEN_ROUTE_GOVERNANCE.toolGetRoutes }}</dd>
        <dt>Tool write HTTP route</dt><dd>{{ FROZEN_ROUTE_GOVERNANCE.toolWriteRoutes }}</dd>
        <dt>Tool dry-run / execute</dt><dd>{{ FROZEN_ROUTE_GOVERNANCE.toolDryRunRoutes }} / {{ FROZEN_ROUTE_GOVERNANCE.toolExecutionRoutes }}</dd>
      </dl>
      <p class="devconsole-note">Verified by <code>tests/test_dev_check_webui.py</code> + <code>tests/test_dev_web_0c06_closure.py</code>.</p>
    </div>

    <div class="devconsole-card">
      <h3>Static allowlist (read-only)</h3>
      <p class="devconsole-note">{{ FROZEN_STATIC_ALLOWLIST.length }} tools.</p>
      <ul class="devconsole-note" style="margin: var(--space-2, 8px) 0 0; padding-left: var(--space-4, 16px);">
        <li v-for="tool in FROZEN_STATIC_ALLOWLIST" :key="tool"><code>{{ tool }}</code></li>
      </ul>
    </div>

    <div class="devconsole-card">
      <h3>Static write tools (sandbox)</h3>
      <p class="devconsole-note">{{ FROZEN_STATIC_WRITE_TOOLS.length }} tools.</p>
      <ul class="devconsole-note" style="margin: var(--space-2, 8px) 0 0; padding-left: var(--space-4, 16px);">
        <li v-for="tool in FROZEN_STATIC_WRITE_TOOLS" :key="tool"><code>{{ tool }}</code></li>
      </ul>
    </div>
  </section>
</template>
