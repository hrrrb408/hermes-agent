<script setup lang="ts">
/**
 * Governance Hub route governance panel (Phase 3L).
 *
 * Read-only projection of the frozen route-governance baseline. Exact counts
 * (34/34/5/0/1/1); every "new route" flag is frozen at 0. The Governance Hub
 * adds no backend route, no approval route, no execution route, and no production
 * rollout route. There is no interactive control here.
 */
import type { GovernanceRouteSummary } from '@/types/api/governanceHub'

defineProps<{
  route: GovernanceRouteSummary
  baseline: string
  backendRoutesChanged: false
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-route-panel">
    <h2>Route governance summary</h2>
    <p class="ghub-muted">
      The frozen backend route-governance baseline — unchanged by this read-only
      surface. OpenAPI / Runtime / Tool GET / Tool write / dry-run / execute.
    </p>
    <table class="ghub-route" data-testid="governance-hub-route-table">
      <caption class="ghub-route__caption">
        Route governance counts (read-only). Frozen baseline unchanged.
      </caption>
      <thead>
        <tr>
          <th scope="col">Dimension</th>
          <th scope="col">Count</th>
        </tr>
      </thead>
      <tbody>
        <tr data-route-key="openapiPaths"><td>OpenAPI paths</td><td :data-route-count="route.openapiPaths">{{ route.openapiPaths }}</td></tr>
        <tr data-route-key="runtimeRoutes"><td>Runtime routes</td><td :data-route-count="route.runtimeRoutes">{{ route.runtimeRoutes }}</td></tr>
        <tr data-route-key="toolGetRoutes"><td>Tool GET</td><td :data-route-count="route.toolGetRoutes">{{ route.toolGetRoutes }}</td></tr>
        <tr data-route-key="toolWriteHttpRoutes"><td>Tool write HTTP route</td><td :data-route-count="route.toolWriteHttpRoutes">{{ route.toolWriteHttpRoutes }}</td></tr>
        <tr data-route-key="toolDryRunRoutes"><td>Tool dry-run route</td><td :data-route-count="route.toolDryRunRoutes">{{ route.toolDryRunRoutes }}</td></tr>
        <tr data-route-key="toolExecutionRoutes"><td>Tool execution route</td><td :data-route-count="route.toolExecutionRoutes">{{ route.toolExecutionRoutes }}</td></tr>
        <tr data-route-key="newHttpRoutes"><td>New HTTP route</td><td :data-route-count="route.newHttpRoutes">{{ route.newHttpRoutes }}</td></tr>
        <tr data-route-key="newToolWriteRoutes"><td>New Tool write route</td><td :data-route-count="route.newToolWriteRoutes">{{ route.newToolWriteRoutes }}</td></tr>
        <tr data-route-key="newProviderRoutes"><td>New Provider route</td><td :data-route-count="route.newProviderRoutes">{{ route.newProviderRoutes }}</td></tr>
        <tr data-route-key="newPluginRoutes"><td>New plugin route</td><td :data-route-count="route.newPluginRoutes">{{ route.newPluginRoutes }}</td></tr>
        <tr data-route-key="newRuntimeRoutes"><td>New runtime route</td><td :data-route-count="route.newRuntimeRoutes">{{ route.newRuntimeRoutes }}</td></tr>
      </tbody>
    </table>
    <ul class="ghub-route__notes" data-testid="governance-hub-route-notes">
      <li><code>{{ route.format }}</code> — frozen baseline unchanged</li>
      <li>No backend route added</li>
      <li>No approval / authorization route</li>
      <li>No runtime execution route</li>
      <li>No production rollout route</li>
    </ul>
    <p class="ghub-muted">
      The Governance Hub is a client-side section inside the existing
      <code>/console</code> view. No backend route was added for it.
    </p>
  </div>
</template>

<style scoped>
.ghub-muted {
  margin: 0 0 var(--space-2, 8px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-route {
  width: 100%;
  max-width: 480px;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
  margin-bottom: var(--space-3, 12px);
}
.ghub-route__caption {
  text-align: left;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  padding: var(--space-1, 4px) 0;
}
.ghub-route th,
.ghub-route td {
  text-align: left;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-bottom: 1px solid var(--color-border, #2a2a33);
}
.ghub-route thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
  font-size: var(--font-size-xs, 12px);
}
.ghub-route td:last-child {
  text-align: right;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.ghub-route__notes {
  list-style: disc;
  margin: 0 0 var(--space-2, 8px);
  padding-left: var(--space-4, 16px);
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-sm, 13px);
}
.ghub-route__notes li {
  line-height: 1.6;
}
</style>
