<script setup lang="ts">
/**
 * Runtime Governance safety / side-effect matrix (Phase 3J).
 *
 * Read-only projection of the frozen all-False side-effect surface. Every flag
 * is False and is rendered as a static label — there is no toggle, no input,
 * and no way to override a flag. A governance pass performs none of these
 * actions no matter what renders.
 */
import { Check, X } from '@lucide/vue'
import type { RuntimeSideEffectFlag } from '@/types/api/runtimeGovernance'

defineProps<{
  flags: readonly RuntimeSideEffectFlag[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="runtime-safety-matrix">
    <h3>Side-effect invariants (all false)</h3>
    <p class="rtgov-muted">
      The frozen no-side-effect surface projected by every governance report.
      Every value is a plain boolean and cannot be overridden by metadata.
    </p>
    <ul class="rtgov-safety" data-testid="runtime-safety-list">
      <li
        v-for="flag in flags"
        :key="flag.key"
        class="rtgov-safety__item"
        :data-side-effect-key="flag.key"
      >
        <span class="rtgov-safety__label">{{ flag.label }}</span>
        <span class="rtgov-safety__value" :data-side-effect="flag.value">
          <X v-if="flag.value === false" :size="13" aria-hidden="true" />
          <Check v-else :size="13" aria-hidden="true" />
          {{ String(flag.value) }}
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.rtgov-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-safety {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.rtgov-safety__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-safety__label {
  color: var(--color-text, #e6e6ec);
}
.rtgov-safety__value {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  color: var(--color-success, #6ec48e);
  font-weight: 600;
}
</style>
