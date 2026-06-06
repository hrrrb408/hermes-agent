<script setup lang="ts">
import { Palette } from '@lucide/vue'
import { useThemeStore } from '@/stores/theme'
import ThemePicker from './ThemePicker.vue'

const store = useThemeStore()
</script>

<template>
  <div class="theme-switcher">
    <Palette class="theme-switcher__icon" :size="16" aria-hidden="true" />
    <div class="theme-switcher__info">
      <span class="theme-switcher__label">Theme</span>
      <span class="theme-switcher__scheme">
        {{ store.activeTheme.colorScheme === 'dark' ? 'Dark' : 'Light' }}
      </span>
    </div>
    <div class="theme-switcher__preview">
      <span
        class="theme-switcher__dot"
        :style="{ background: store.activeTheme.previewColors.background }"
      ></span>
      <span
        class="theme-switcher__dot"
        :style="{ background: store.activeTheme.previewColors.accent }"
      ></span>
    </div>
    <ThemePicker />
  </div>
</template>

<style scoped>
.theme-switcher {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
}

.theme-switcher__icon {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.theme-switcher__info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.theme-switcher__label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.theme-switcher__scheme {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.theme-switcher__preview {
  display: flex;
  gap: 3px;
}

.theme-switcher__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
}
</style>
