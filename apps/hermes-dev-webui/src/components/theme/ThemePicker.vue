<script setup lang="ts">
import { ref, onUnmounted, watch } from 'vue'
import { ChevronDown } from '@lucide/vue'
import { useThemeStore } from '@/stores/theme'
import { THEME_CATEGORIES } from '@/themes/types'
import type { ThemeId } from '@/themes/types'
import ThemePreviewCard from './ThemePreviewCard.vue'

const store = useThemeStore()
const pickerRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)

function togglePicker(): void {
  isOpen.value = !isOpen.value
}

function closePicker(): void {
  isOpen.value = false
}

function selectTheme(themeId: string): void {
  store.setTheme(themeId as ThemeId)
  closePicker()
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    closePicker()
  }
}

function handleClickOutside(e: MouseEvent): void {
  if (pickerRef.value && !pickerRef.value.contains(e.target as Node)) {
    closePicker()
  }
}

watch(isOpen, (open) => {
  if (open) {
    document.addEventListener('keydown', handleKeydown)
    document.addEventListener('click', handleClickOutside)
  } else {
    document.removeEventListener('keydown', handleKeydown)
    document.removeEventListener('click', handleClickOutside)
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="pickerRef" class="theme-picker">
    <button
      class="theme-picker__trigger"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
      @click="togglePicker"
    >
      <span class="theme-picker__trigger-name">{{ store.activeTheme.localizedName }}</span>
      <ChevronDown
        class="theme-picker__chevron"
        :class="{ 'theme-picker__chevron--open': isOpen }"
        :size="14"
      />
    </button>

    <div v-if="isOpen" class="theme-picker__dropdown" role="listbox" aria-label="Theme selection">
      <div
        v-for="category in THEME_CATEGORIES"
        :key="category.id"
        class="theme-picker__group"
      >
        <span class="theme-picker__group-label">{{ category.localizedLabel }}</span>
        <div class="theme-picker__group-themes">
          <ThemePreviewCard
            v-for="themeId in category.themes"
            :key="themeId"
            :theme="store.availableThemes.find((t) => t.id === themeId)!"
            :is-active="store.activeThemeId === themeId"
            @select="selectTheme"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.theme-picker {
  position: relative;
}

.theme-picker__trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast);
}

.theme-picker__trigger:hover {
  border-color: var(--color-border-strong);
  background: var(--color-hover-bg);
}

.theme-picker__chevron {
  transition: transform var(--transition-fast);
}

.theme-picker__chevron--open {
  transform: rotate(180deg);
}

.theme-picker__dropdown {
  position: absolute;
  top: calc(100% + var(--space-2));
  right: 0;
  z-index: 100;
  min-width: 420px;
  padding: var(--space-4);
  background: var(--color-elevated-bg);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-floating);
}

.theme-picker__group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.theme-picker__group:not(:last-child) {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: var(--border-width) solid var(--color-divider);
}

.theme-picker__group-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.theme-picker__group-themes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-2);
}
</style>
