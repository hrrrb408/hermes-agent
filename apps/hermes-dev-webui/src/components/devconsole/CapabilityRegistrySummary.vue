<script setup lang="ts">
/**
 * Capability Registry summary (Phase 3C).
 *
 * Renders the frozen policy flags + live counts from the /status block. The
 * frozen flags (dynamicLoadingAllowed=false, remoteRegistryAllowed=false,
 * marketplaceAllowed=false, productionAllowed=false, devOnly=true) are surfaced
 * as explicit badges so the read-only "registry describes only / does not grant
 * permission" invariant is visible at a glance.
 */
import { computed } from 'vue'
import type { CapabilityRegistrySummary } from '@/types/api/capabilityRegistry'
import { CAPABILITY_FROZEN_FLAGS } from '@/stores/capabilityRegistry'

const props = defineProps<{ summary: CapabilityRegistrySummary | null }>()

const rows = computed(() => {
  const s = props.summary
  return [
    { label: 'Registry status', value: s?.status ?? '—' },
    { label: 'Registry version', value: s?.registryVersion ?? '—' },
    { label: 'Capability count', value: s?.capabilityCount ?? 0 },
    { label: 'Enabled', value: s?.enabledCount ?? 0 },
    { label: 'Disabled', value: s?.disabledCount ?? 0 },
    { label: 'Blocked', value: s?.blockedCount ?? 0 },
    { label: 'Planned', value: s?.plannedCount ?? 0 },
    { label: 'Deprecated', value: s?.deprecatedCount ?? 0 },
    { label: 'Route governance', value: s?.routeGovernanceExpected ?? '34/34/5/0/1/1' },
    {
      label: 'Validation',
      value: s ? `${s.validation.valid ? 'passed' : 'failed'} (${s.validation.errorCount} errors)` : '—',
    },
  ]
})

const flags = computed(() => [
  { label: 'Dev-only', value: CAPABILITY_FROZEN_FLAGS.devOnly, ok: CAPABILITY_FROZEN_FLAGS.devOnly === true },
  { label: 'Production allowed', value: CAPABILITY_FROZEN_FLAGS.productionAllowed, ok: CAPABILITY_FROZEN_FLAGS.productionAllowed === false },
  { label: 'Dynamic loading', value: CAPABILITY_FROZEN_FLAGS.dynamicLoadingAllowed, ok: CAPABILITY_FROZEN_FLAGS.dynamicLoadingAllowed === false },
  { label: 'Remote registry', value: CAPABILITY_FROZEN_FLAGS.remoteRegistryAllowed, ok: CAPABILITY_FROZEN_FLAGS.remoteRegistryAllowed === false },
  { label: 'Marketplace', value: CAPABILITY_FROZEN_FLAGS.marketplaceAllowed, ok: CAPABILITY_FROZEN_FLAGS.marketplaceAllowed === false },
])

const permCounts = computed(() => props.summary?.permissionClassCounts ?? {})
const trustCounts = computed(() => props.summary?.trustLevelCounts ?? {})
const categoryCounts = computed(() => props.summary?.categoryCounts ?? {})
</script>

<template>
  <div class="devconsole-card" data-testid="capability-registry-summary">
    <h3>Capability Registry — Summary</h3>
    <p class="devconsole-note" style="margin-top: 0">
      Static dev-only registry. It describes capabilities only — it does not
      grant permission, does not bypass Tool policy, Provider live gate, or
      Workflow approval. No plugin runtime, dynamic loading, remote registry, or
      marketplace.
    </p>

    <dl class="devconsole-kv">
      <template v-for="row in rows" :key="row.label">
        <dt>{{ row.label }}</dt>
        <dd>{{ row.value }}</dd>
      </template>
    </dl>

    <h4 style="margin-top: 1rem">Frozen policy flags</h4>
    <ul class="cap-flags" data-testid="capability-frozen-flags">
      <li v-for="flag in flags" :key="flag.label" :class="{ 'cap-flag--ok': flag.ok }">
        <strong>{{ flag.label }}:</strong>
        <span>{{ flag.value ? 'yes' : 'no' }}</span>
      </li>
    </ul>

    <div class="cap-counts">
      <div>
        <h5>Permission classes</h5>
        <ul class="cap-counts__list">
          <li v-for="(count, key) in permCounts" :key="key">{{ key }}: {{ count }}</li>
        </ul>
      </div>
      <div>
        <h5>Trust levels</h5>
        <ul class="cap-counts__list">
          <li v-for="(count, key) in trustCounts" :key="key">{{ key }}: {{ count }}</li>
        </ul>
      </div>
      <div>
        <h5>Categories</h5>
        <ul class="cap-counts__list">
          <li v-for="(count, key) in categoryCounts" :key="key">{{ key }}: {{ count }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>
