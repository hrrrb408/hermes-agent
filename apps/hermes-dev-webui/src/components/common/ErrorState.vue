<script setup lang="ts">
/**
 * Reusable error state (Phase 2E).
 *
 * Wraps the existing `.panel-error` / `.panel-retry-btn` surfaces with an
 * accessible alert role and an optional retry action (emitted to the parent so
 * the parent decides what "retry" means for its section).
 */
withDefaults(
  defineProps<{
    message: string
    retryLabel?: string
  }>(),
  {
    retryLabel: 'Retry',
  },
)

defineEmits<{
  retry: []
}>()
</script>

<template>
  <div class="panel-error dev-state dev-state--error" role="alert" data-testid="dev-error-state">
    <p>{{ message }}</p>
    <button
      type="button"
      class="panel-retry-btn"
      data-testid="dev-error-retry"
      aria-label="Retry the failed request"
      @click="$emit('retry')"
    >
      {{ retryLabel }}
    </button>
  </div>
</template>
