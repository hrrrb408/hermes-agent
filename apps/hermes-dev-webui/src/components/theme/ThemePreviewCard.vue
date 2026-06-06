<script setup lang="ts">
import type { ThemeDefinition } from '@/themes/types'

defineProps<{
  theme: ThemeDefinition
  isActive: boolean
}>()

defineEmits<{
  select: [themeId: string]
}>()
</script>

<template>
  <button
    class="theme-preview-card"
    :class="{ 'theme-preview-card--active': isActive }"
    :aria-selected="isActive"
    :aria-label="`${theme.localizedName} theme`"
    role="option"
    @click="$emit('select', theme.id)"
  >
    <div class="theme-preview-card__colors">
      <span
        class="theme-preview-card__swatch"
        :style="{ background: theme.previewColors.background }"
      ></span>
      <span
        class="theme-preview-card__swatch"
        :style="{ background: theme.previewColors.foreground }"
      ></span>
      <span
        class="theme-preview-card__swatch"
        :style="{ background: theme.previewColors.accent }"
      ></span>
      <span
        v-if="theme.previewColors.secondary"
        class="theme-preview-card__swatch"
        :style="{ background: theme.previewColors.secondary }"
      ></span>
    </div>

    <div class="theme-preview-card__info">
      <span class="theme-preview-card__name">{{ theme.localizedName }}</span>
      <span class="theme-preview-card__scheme">
        {{ theme.colorScheme === 'dark' ? 'Dark' : 'Light' }}
      </span>
    </div>

    <p class="theme-preview-card__desc">{{ theme.description }}</p>
  </button>
</template>

<style scoped>
.theme-preview-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
  text-align: left;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    background var(--transition-fast);
}

.theme-preview-card:hover {
  border-color: var(--color-border-strong);
  background: var(--color-hover-bg);
}

.theme-preview-card--active {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus);
}

.theme-preview-card__colors {
  display: flex;
  gap: var(--space-1);
  height: 28px;
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.theme-preview-card__swatch {
  flex: 1;
  border-radius: 2px;
}

.theme-preview-card__info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.theme-preview-card__name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.theme-preview-card__scheme {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-neutral-soft);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.theme-preview-card__desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.4;
}
</style>
