<script setup lang="ts">
import { Beaker, Box, Database, Radio, Sparkles } from '@lucide/vue'
import { RouterLink } from 'vue-router'
import ThemeSwitcher from '@/components/theme/ThemeSwitcher.vue'
</script>

<template>
  <header class="top-status-bar" role="banner">
    <div class="top-status-bar__brand">
      <Box :size="16" aria-hidden="true" />
      <strong>Hermes Dev WebUI</strong>
      <span class="top-status-bar__section">Workspace</span>
    </div>

    <div class="top-status-bar__statuses" aria-label="Static preview status">
      <span class="status-item"><Sparkles :size="13" aria-hidden="true" />Model: deepseek-chat · Mock</span>
      <span class="status-item">Agent: Preview</span>
      <span class="status-item"><Radio :size="13" aria-hidden="true" />Gateway: Not connected</span>
      <span class="status-item"><Database :size="13" aria-hidden="true" />Memory: Mock</span>
    </div>

    <div class="top-status-bar__actions">
      <span class="environment-label">Dev</span>
      <span class="home-label">hermes-home-dev</span>
      <ThemeSwitcher class="top-status-bar__theme" />
      <RouterLink class="theme-lab-link" to="/theme-lab" aria-label="Open Theme Lab">
        <Beaker :size="15" aria-hidden="true" />
        <span>Theme Lab</span>
      </RouterLink>
    </div>
  </header>
</template>
