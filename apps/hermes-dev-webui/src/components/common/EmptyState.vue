<script setup lang="ts">
/**
 * Reusable empty state (Phase 2E).
 *
 * Wraps the existing `.panel-empty` surface with an optional hint line so
 * console sections present "no data yet" consistently.
 */
defineProps<{
  message: string
  hint?: string
}>()
</script>

<template>
  <div class="panel-empty dev-state dev-state--empty" data-testid="dev-empty-state">
    <p>{{ message }}</p>
    <p v-if="hint" class="dev-state__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.dev-state__hint {
  margin-top: var(--space-1, 4px);
  color: var(--color-text-muted, #6a6a74);
}
</style>
