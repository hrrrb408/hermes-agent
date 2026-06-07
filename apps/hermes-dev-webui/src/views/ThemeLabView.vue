<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
import { RouterLink } from 'vue-router'
import ThemeSwitcher from '@/components/theme/ThemeSwitcher.vue'
import ThemeShowcase from '@/components/theme/ThemeShowcase.vue'
</script>

<template>
  <div class="theme-lab">
    <header class="theme-lab__header">
      <div class="theme-lab__title-area">
        <h1 class="theme-lab__title">Hermes Dev WebUI</h1>
        <span class="theme-lab__badge">Theme Lab</span>
      </div>
      <p class="theme-lab__desc">
        Visual reference for all five themes. Switch themes to verify color, typography,
        density, panel, message, and tool card rendering.
      </p>
      <div class="theme-lab__switcher-row">
        <ThemeSwitcher />
        <RouterLink class="theme-lab__back" to="/">
          <ArrowLeft :size="15" aria-hidden="true" />
          Back to Workspace
        </RouterLink>
      </div>
    </header>

    <main class="theme-lab__main">
      <ThemeShowcase />
    </main>

    <footer class="theme-lab__footer">
      <span class="theme-lab__footer-text">
        Hermes Dev WebUI Phase 0A - Theme Lab
      </span>
    </footer>
  </div>
</template>

<style scoped>
.theme-lab {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.theme-lab__header {
  padding: var(--space-6) var(--space-8);
  border-bottom: var(--lab-header-border);
  background: var(--color-panel-bg);
  position: relative;
}

.theme-lab__title-area {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.theme-lab__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.theme-lab__badge {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-accent);
  background: var(--color-accent-soft);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.theme-lab__desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  max-width: 60ch;
  margin-bottom: var(--space-4);
}

.theme-lab__switcher-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.theme-lab__back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-secondary);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
}

.theme-lab__main {
  flex: 1;
  padding: var(--space-6) var(--lab-content-padding-inline);
  max-width: var(--lab-content-max-width);
  width: 100%;
  margin: 0 auto;
  position: relative;
}

.theme-lab__footer {
  padding: var(--space-4) var(--space-8);
  border-top: var(--border-width) solid var(--color-divider);
}

.theme-lab__footer-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
</style>
