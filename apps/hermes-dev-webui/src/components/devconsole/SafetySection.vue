<script setup lang="ts">
import { computed, onMounted } from 'vue'
import SafetyBadgeBar from './SafetyBadgeBar.vue'
import { useToolPolicyStore } from '@/stores/toolPolicy'
import { badgesByGroup, type SafetyBadge } from '@/lib/safetyBadges'
import { FROZEN_ROUTE_GOVERNANCE, FROZEN_PRODUCTION_GATEWAY_PID } from '@/lib/frozenBaseline'

/**
 * Dev Console → Safety Boundary panel (Phase 2E).
 *
 * Consolidates every invariant the dev console enforces: route governance,
 * production isolation, provider boundary, write boundary, and audit boundary.
 * Live safety flags come from GET /tools/policy; governance/PID numbers are the
 * frozen baseline verified by gates.
 */
const policy = useToolPolicyStore()

onMounted(() => {
  if (policy.policyState === 'idle') {
    void policy.loadPolicy()
  }
})

const GROUP_TITLE: Readonly<Record<SafetyBadge['group'], string>> = {
  production: 'Production isolation',
  environment: 'Environment',
  route: 'Route governance',
  provider: 'Provider boundary',
  write: 'Write boundary',
  audit: 'Audit boundary',
}

const groups = computed(() => {
  const order: SafetyBadge['group'][] = ['production', 'environment', 'route', 'provider', 'write', 'audit']
  return order
    .map((g) => ({ group: g, title: GROUP_TITLE[g], badges: badgesByGroup(g) }))
    .filter((entry) => entry.badges.length > 0)
})

const routeRows = computed(() => [
  { label: 'OpenAPI paths', value: FROZEN_ROUTE_GOVERNANCE.openApiPaths },
  { label: 'Runtime routes', value: FROZEN_ROUTE_GOVERNANCE.runtimeRoutes },
  { label: 'Tool GET routes', value: FROZEN_ROUTE_GOVERNANCE.toolGetRoutes },
  { label: 'Tool write HTTP route', value: FROZEN_ROUTE_GOVERNANCE.toolWriteRoutes },
  { label: 'Tool dry-run route', value: FROZEN_ROUTE_GOVERNANCE.toolDryRunRoutes },
  { label: 'Tool execution route', value: FROZEN_ROUTE_GOVERNANCE.toolExecutionRoutes },
])
</script>

<template>
  <section class="devconsole-section" aria-label="Safety Boundary">
    <div class="devconsole-section__intro">
      <h2>Safety Boundary</h2>
      <p>
        The invariants the dev console enforces by construction. Every badge is
        a guarantee — none require live probing. Route governance and the
        production gateway PID are the frozen baseline verified by the smoke
        preflight and the backend invariant tests; the dev console never acts on
        the production instance.
      </p>
    </div>

    <SafetyBadgeBar />

    <div v-for="entry in groups" :key="entry.group" class="devconsole-safety-group" :data-group="entry.group">
      <h3 class="devconsole-safety-group__title">{{ entry.title }}</h3>
      <SafetyBadgeBar :badges="entry.badges" />
    </div>

    <div class="devconsole-card">
      <h3>Route governance baseline</h3>
      <p class="devconsole-note" style="margin-top:0;">
        Frozen across Phase 2A → 2D-H1. Verified by
        <code>tests/test_dev_check_webui.py</code> and
        <code>tests/test_dev_web_0c06_closure.py</code>.
      </p>
      <dl class="devconsole-kv">
        <template v-for="row in routeRows" :key="row.label">
          <dt>{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </template>
      </dl>
    </div>

    <div class="devconsole-card">
      <h3>Production isolation</h3>
      <dl class="devconsole-kv">
        <dt>Production gateway PID</dt><dd>{{ FROZEN_PRODUCTION_GATEWAY_PID }} (read-only)</dd>
        <dt>Production gateway count</dt><dd>1</dd>
        <dt>Dev gateway</dt><dd>stopped</dd>
        <dt>Dashboard</dt><dd>not started</dd>
        <dt>Ports 5180 / 5181</dt><dd>dev WebUI / dev API only</dd>
      </dl>
      <p class="devconsole-note">
        If the live production gateway PID ever drifts from the baseline, the
        smoke harness fails closed — do not bypass the production gate.
      </p>
    </div>

    <div class="devconsole-card">
      <h3>Live policy flags</h3>
      <p v-if="policy.isPolicyLoading" class="devconsole-note">Loading…</p>
      <dl v-else-if="policy.policy" class="devconsole-kv">
        <dt>Read-only</dt><dd>{{ policy.policy.safety.readOnly ? 'Yes' : 'No' }}</dd>
        <dt>Write enabled</dt><dd>{{ policy.policy.safety.writeEnabled ? 'Yes' : 'No' }}</dd>
        <dt>Execution enabled</dt><dd>{{ policy.policy.execution.enabled ? 'Yes' : 'No' }}</dd>
        <dt>Provider schema sent</dt><dd>{{ policy.policy.execution.providerSchemaSent ? 'Yes' : 'No' }}</dd>
        <dt>Enabled allowlist</dt><dd>{{ policy.policy.enabledAllowlistCount }}</dd>
        <dt>Permanent denylist</dt><dd>{{ policy.policy.permanentDenylistCount }}</dd>
      </dl>
      <p v-else class="devconsole-note">Policy unavailable.</p>
    </div>
  </section>
</template>
