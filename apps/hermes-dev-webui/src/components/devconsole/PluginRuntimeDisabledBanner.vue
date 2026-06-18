<script setup lang="ts">
/**
 * Plugin runtime disabled banner (Phase 3D).
 *
 * Surfaces the frozen, read-only policy that there is NO plugin runtime, NO
 * plugin loader, NO dynamic loading, NO local plugin directory loading, NO
 * remote registry / marketplace / external plugin fetch, NO provider-generated
 * plugin, NO LLM-generated plugin install, and NO plugin execution. Every line
 * carries an explicit text label (non-color identification).
 */
import { PowerOff, Ban, Download, Globe, ShoppingBag, PackagePlus, Bot, Cpu } from '@lucide/vue'
import type { Component } from 'vue'

interface DisabledRow {
  readonly icon: Component
  readonly label: string
}

const ROWS: readonly DisabledRow[] = [
  { icon: PowerOff, label: 'Plugin runtime disabled — no plugin is executed' },
  { icon: Cpu, label: 'Plugin loader not implemented — no plugin code is loaded' },
  { icon: Ban, label: 'Dynamic loading disabled — no importlib / path-based load' },
  { icon: PackagePlus, label: 'Local plugin directory loading disabled' },
  { icon: Globe, label: 'Remote registry disabled — no remote manifest fetch' },
  { icon: ShoppingBag, label: 'Marketplace disabled' },
  { icon: Download, label: 'External plugin fetch disabled' },
  { icon: Bot, label: 'No provider-generated plugin; no LLM-generated plugin install' },
]
</script>

<template>
  <aside
    class="plugin-runtime-disabled-banner"
    role="status"
    aria-live="polite"
    data-testid="plugin-runtime-disabled-banner"
  >
    <header class="plugin-runtime-disabled-banner__header">
      <PowerOff :size="16" aria-hidden="true" />
      <h3>Plugin runtime disabled (descriptor-only registry)</h3>
    </header>
    <p class="plugin-runtime-disabled-banner__note">
      This registry is descriptor-only. It describes future plugin descriptors —
      it does not grant permission, does not load a plugin, and does not execute
      a plugin. Every descriptor is disabled by default.
    </p>
    <ul class="plugin-runtime-disabled-banner__list">
      <li v-for="row in ROWS" :key="row.label">
        <component :is="row.icon" :size="13" aria-hidden="true" />
        <span>{{ row.label }}</span>
      </li>
    </ul>
  </aside>
</template>
