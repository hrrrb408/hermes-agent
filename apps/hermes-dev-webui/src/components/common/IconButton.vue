<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    title?: string
    disabled?: boolean
    expanded?: boolean
    controls?: string
  }>(),
  {
    title: undefined,
    disabled: false,
    expanded: undefined,
    controls: undefined,
  },
)
</script>

<template>
  <button
    class="icon-button"
    type="button"
    :aria-label="label"
    :title="title ?? label"
    :disabled="disabled"
    :aria-expanded="expanded"
    :aria-controls="controls"
  >
    <slot />
  </button>
</template>

<style scoped>
.icon-button {
  width: 32px;
  height: 32px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  border: var(--border-width) solid transparent;
  border-radius: var(--radius-md);
  transition:
    color var(--transition-fast),
    border-color var(--transition-fast),
    background-color var(--transition-fast);
}

.icon-button:hover:not(:disabled) {
  color: var(--color-text-primary);
  border-color: var(--workspace-divider);
  background: var(--workspace-hover-bg);
}

.icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}
</style>
