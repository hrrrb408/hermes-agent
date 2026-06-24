<script setup lang="ts">
/**
 * Governance Hub deferred / still-not-authorized panel (Phase 3L).
 *
 * Read-only list of every capability that remains NO-GO / not-authorized. Each
 * item is rendered as explanatory TEXT only — never as an interactive control.
 * Frozen so a governance pass can never drop or drain one. There is no
 * interactive control here.
 */
import { Lock } from '@lucide/vue'

defineProps<{
  items: readonly string[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-deferred-panel">
    <h2>Deferred / still not authorized</h2>
    <p class="ghub-muted">
      Every capability below remains NO-GO / not-authorized. None can be enabled,
      approved, or rolled out from this read-only surface. Listed read-only for
      traceability — these words are explanatory text, never interactive controls.
    </p>
    <ul class="ghub-deferred" data-testid="governance-hub-deferred-list">
      <li v-for="item in items" :key="item" :data-deferred-item="item">
        <Lock :size="12" aria-hidden="true" />
        <span>{{ item }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ghub-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-deferred {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-deferred li {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #8a8a94);
  background: var(--color-surface, #101015);
}
</style>
