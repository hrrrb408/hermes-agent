<script setup lang="ts">
/**
 * Phase 3A workflow safety boundary panel.
 *
 * Renders the frozen Phase 3A capability boundary as a read-only table. Every
 * capability is labelled Allowed / Blocked / Required / Enabled so the operator
 * can see at a glance what the workflow may and may not do.
 */
import { computed } from 'vue'
import { BOUNDARY_ROWS, formatBoundaryValue } from '@/lib/workflowFormatters'
import type { WorkflowSafetyBoundary } from '@/lib/workflowTypes'

const props = defineProps<{
  boundary: WorkflowSafetyBoundary
}>()

const rows = computed(() =>
  BOUNDARY_ROWS.map((row) => ({
    key: row.key,
    label: row.label,
    value: formatBoundaryValue(props.boundary[row.key]),
    raw: props.boundary[row.key],
  })),
)

function tone(raw: string): 'positive' | 'negative' | 'neutral' {
  if (raw === 'allowed' || raw === 'enabled') return 'positive'
  if (raw === 'blocked') return 'negative'
  return 'neutral'
}
</script>

<template>
  <section
    class="wf-boundary"
    aria-label="Workflow safety boundary"
    data-testid="dev-workflow-safety-boundary"
  >
    <h3 class="wf-boundary__title">Safety boundary</h3>
    <p class="wf-boundary__hint">
      Dev-only, manual, approval-gated. No real provider, no autonomous write,
      no shell / database / external service write, no production rollout.
    </p>
    <ul class="wf-boundary__list">
      <li
        v-for="row in rows"
        :key="row.key"
        class="wf-boundary__row"
        :data-capability="row.key"
      >
        <span class="wf-boundary__label">{{ row.label }}</span>
        <span
          class="wf-boundary__value"
          :data-tone="tone(row.raw)"
          :data-testid="`dev-workflow-boundary-${row.key}`"
        >{{ row.value }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.wf-boundary {
  display: grid;
  gap: var(--space-2, 8px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}
.wf-boundary__title {
  margin: 0;
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-boundary__hint {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
  line-height: 1.5;
}
.wf-boundary__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.wf-boundary__row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  padding: 2px 0;
  font-size: var(--font-size-xs, 0.75rem);
}
.wf-boundary__label {
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-boundary__value {
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-boundary__value[data-tone='positive'] {
  color: var(--color-success, #6fb98f);
}
.wf-boundary__value[data-tone='negative'] {
  color: var(--color-error, #e5656b);
}
</style>
