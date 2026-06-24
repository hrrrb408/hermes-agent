<script setup lang="ts">
/**
 * Governance Hub production safety panel (Phase 3L).
 *
 * Read-only projection of the frozen production-safety boundary. Every flag is
 * False. Static wording only — the frontend does NOT inspect a live process. The
 * exact production gateway PID is deliberately NOT carried here
 * (environment-specific); the surface states the gateway is expected unchanged
 * and untouched. There is no interactive control here.
 */
import { Check } from '@lucide/vue'
import type { GovernanceProductionSafety } from '@/types/api/governanceHub'

defineProps<{
  safety: GovernanceProductionSafety
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-production-safety-panel">
    <h2>Production safety summary</h2>
    <p class="ghub-muted">
      Static wording only — the frontend does not check a live process. Every flag
      below is frozen false: no production process is affected, no production state
      is touched, and there is no production home access (not even metadata) or
      production state database access.
    </p>
    <ul class="ghub-safety" data-testid="governance-hub-safety-list">
      <li :data-safety-key="`productionGatewayTouched-${safety.productionGatewayTouched}`">
        <Check :size="13" aria-hidden="true" />
        Production Gateway expected unchanged and not touched
      </li>
      <li :data-safety-key="`devGatewayStarted-${safety.devGatewayStarted}`">
        <Check :size="13" aria-hidden="true" />
        Dev Gateway remains stopped (not started)
      </li>
      <li :data-safety-key="`dashboardStarted-${safety.dashboardStarted}`">
        <Check :size="13" aria-hidden="true" />
        Dashboard not started
      </li>
      <li :data-safety-key="`ports5180And5181Bound-${safety.ports5180And5181Bound}`">
        <Check :size="13" aria-hidden="true" />
        Ports 5180 / 5181 remain free (not bound)
      </li>
      <li :data-safety-key="`productionHomeAccess-${safety.productionHomeAccess}`">
        <Check :size="13" aria-hidden="true" />
        No production home access (not even metadata)
      </li>
      <li :data-safety-key="`productionStateDbAccess-${safety.productionStateDbAccess}`">
        <Check :size="13" aria-hidden="true" />
        No production state database access
      </li>
      <li :data-safety-key="`externalNetwork-${safety.externalNetwork}`">
        <Check :size="13" aria-hidden="true" />
        No external network
      </li>
      <li :data-safety-key="`realSecretRead-${safety.realSecretRead}`">
        <Check :size="13" aria-hidden="true" />
        No real secret / API key read
      </li>
    </ul>
    <p class="ghub-muted">{{ safety.note }}</p>
  </div>
</template>

<style scoped>
.ghub-muted {
  margin: 0 0 var(--space-2, 8px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-safety {
  list-style: none;
  margin: 0 0 var(--space-3, 12px);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-safety li {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.ghub-safety li :deep(svg) {
  color: var(--color-success, #6ec48e);
}
</style>
