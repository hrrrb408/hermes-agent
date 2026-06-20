<script setup lang="ts">
/**
 * Runtime Governance descriptor table (Phase 3J).
 *
 * Read-only list of the frozen reviewed-fixture descriptors. Each row carries
 * only safe metadata and a single harmless "Inspect binding" action that opens
 * the read-only detail panel. There is NO Run / Execute / Batch / Approve /
 * Authorize / Enable / Load / Upload / Fetch control — the WebUI executes
 * nothing. Every descriptor is dev-only / fixture-only / reviewed-fixture and
 * carries executable=false, remote=false, marketplace=false, production=false,
 * routeChange=false.
 */
import type { RuntimeDescriptorRow } from '@/types/api/runtimeGovernance'

defineProps<{
  descriptors: readonly RuntimeDescriptorRow[]
  selectedId?: string | null
}>()

const emit = defineEmits<{ (e: 'select', descriptorId: string): void }>()
</script>

<template>
  <div class="devconsole-card" data-testid="runtime-descriptor-table">
    <h3>Reviewed fixture descriptors</h3>
    <p class="rtgov-muted">
      The frozen reviewed-fixture descriptor registry (static_descriptor_registry).
      Each row is a static, reviewed, dev-only, fixture-only record — never
      executed, never remote, never marketplace, never production, never a route change.
    </p>
    <table class="rtgov-table">
      <thead>
        <tr>
          <th scope="col">Descriptor ID</th>
          <th scope="col">Plugin / Operation</th>
          <th scope="col">Source</th>
          <th scope="col">Dev-only</th>
          <th scope="col">Fixture-only</th>
          <th scope="col">Reviewed</th>
          <th scope="col">Executable</th>
          <th scope="col">Remote</th>
          <th scope="col">Marketplace</th>
          <th scope="col">Production</th>
          <th scope="col">Route change</th>
          <th scope="col">Binding</th>
          <th scope="col"><span class="sr-only">Inspect binding</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="d in descriptors"
          :key="d.descriptorId"
          :class="{ 'rtgov-row--selected': d.descriptorId === selectedId }"
          :data-descriptor-id="d.descriptorId"
        >
          <th scope="row">
            <code class="rtgov-table__code">{{ d.descriptorId }}</code>
          </th>
          <td>
            <div class="rtgov-table__pair">
              <code>{{ d.pluginId }}</code>
              <span class="rtgov-muted">/</span>
              <code>{{ d.operation }}</code>
            </div>
          </td>
          <td><code>{{ d.source }}</code></td>
          <td :data-flag="`devOnly-${d.devOnly}`">{{ d.devOnly }}</td>
          <td :data-flag="`fixtureOnly-${d.fixtureOnly}`">{{ d.fixtureOnly }}</td>
          <td :data-flag="`reviewedFixture-${d.reviewedFixture}`">{{ d.reviewedFixture }}</td>
          <td :data-flag="`executable-${d.executable}`">{{ d.executable }}</td>
          <td :data-flag="`remote-${d.remote}`">{{ d.remote }}</td>
          <td :data-flag="`marketplace-${d.marketplace}`">{{ d.marketplace }}</td>
          <td :data-flag="`production-${d.production}`">{{ d.production }}</td>
          <td :data-flag="`routeChange-${d.routeChange}`">{{ d.routeChange }}</td>
          <td :data-flag="`bindingAllowed-${d.bindingAllowed}`">{{ d.bindingAllowed ? 'allowed' : 'denied' }}</td>
          <td>
            <button
              type="button"
              class="rtgov-inspect-btn"
              :aria-pressed="d.descriptorId === selectedId"
              :aria-label="`Inspect binding for ${d.descriptorId}`"
              :data-testid="`runtime-inspect-${d.descriptorId}`"
              @click="emit('select', d.descriptorId)"
            >
              Inspect
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.rtgov-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
}
.rtgov-table th,
.rtgov-table td {
  border: 1px solid var(--color-border, #2a2a33);
  padding: var(--space-2, 8px);
  text-align: left;
  vertical-align: top;
}
.rtgov-table thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
}
.rtgov-table__code {
  font-family: var(--font-mono, ui-monospace, monospace);
}
.rtgov-table__pair {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1, 4px);
}
.rtgov-row--selected {
  background: var(--color-surface-raised, #1c1c24);
}
.rtgov-inspect-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.rtgov-inspect-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
