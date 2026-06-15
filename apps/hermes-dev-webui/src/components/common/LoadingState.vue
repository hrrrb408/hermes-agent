<script setup lang="ts">
/**
 * Reusable loading state (Phase 2E).
 *
 * Wraps the existing `.panel-loading` surface so every console section renders
 * a consistent, accessible loading affordance (aria-busy + polite live region).
 */
withDefaults(
  defineProps<{
    message?: string
  }>(),
  {
    message: 'Loading…',
  },
)
</script>

<template>
  <div class="panel-loading dev-state dev-state--loading" role="status" aria-busy="true" aria-live="polite" data-testid="dev-loading-state">
    {{ message }}
  </div>
</template>
