<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useToolPolicyStore, type ToolPolicySubTab } from '@/stores/toolPolicy'
import ToolPolicyOverview from './ToolPolicyOverview.vue'
import ToolCatalog from './ToolCatalog.vue'

const store = useToolPolicyStore()

onMounted(() => {
  if (store.policyState === 'idle') {
    store.loadPolicy()
  }
})

onUnmounted(() => {
  store.abortAllRequests()
})

function setSubTab(tab: ToolPolicySubTab): void {
  store.activeSubTab = tab
  if (tab === 'catalog' && store.catalogState === 'idle') {
    store.loadCatalog()
  }
}

function handleSubTabKeyDown(event: KeyboardEvent, tab: ToolPolicySubTab): void {
  const tabs: ToolPolicySubTab[] = ['overview', 'catalog']
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()

  const currentIndex = tabs.indexOf(tab)
  let nextIndex = currentIndex
  if (event.key === 'Home') nextIndex = 0
  if (event.key === 'End') nextIndex = tabs.length - 1
  if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
  if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length

  const nextTab = tabs[nextIndex]
  if (nextTab) {
    setSubTab(nextTab)
    document.getElementById(`tool-policy-tab-${nextTab}`)?.focus()
  }
}
</script>

<template>
  <section class="workspace-panel__section" aria-label="Tool Policy">
    <div class="panel-header">
      <span class="panel-badge">Read-only</span>
    </div>

    <!-- Sub-tab navigation -->
    <div class="tool-policy-tabs" role="tablist" aria-label="Tool policy panel tabs">
      <button
        id="tool-policy-tab-overview"
        type="button"
        role="tab"
        class="tool-policy-tab"
        :class="{ 'tool-policy-tab--active': store.activeSubTab === 'overview' }"
        :aria-selected="store.activeSubTab === 'overview'"
        aria-controls="tool-policy-tabpanel-overview"
        :tabindex="store.activeSubTab === 'overview' ? 0 : -1"
        @click="setSubTab('overview')"
        @keydown="handleSubTabKeyDown($event, 'overview')"
      >
        Policy Overview
      </button>
      <button
        id="tool-policy-tab-catalog"
        type="button"
        role="tab"
        class="tool-policy-tab"
        :class="{ 'tool-policy-tab--active': store.activeSubTab === 'catalog' }"
        :aria-selected="store.activeSubTab === 'catalog'"
        aria-controls="tool-policy-tabpanel-catalog"
        :tabindex="store.activeSubTab === 'catalog' ? 0 : -1"
        @click="setSubTab('catalog')"
        @keydown="handleSubTabKeyDown($event, 'catalog')"
      >
        Catalog
      </button>
    </div>

    <!-- Overview sub-panel -->
    <div
      v-if="store.activeSubTab === 'overview'"
      id="tool-policy-tabpanel-overview"
      role="tabpanel"
      aria-labelledby="tool-policy-tab-overview"
      tabindex="0"
    >
      <ToolPolicyOverview />
    </div>

    <!-- Catalog sub-panel -->
    <div
      v-if="store.activeSubTab === 'catalog'"
      id="tool-policy-tabpanel-catalog"
      role="tabpanel"
      aria-labelledby="tool-policy-tab-catalog"
      tabindex="0"
    >
      <ToolCatalog />
    </div>
  </section>
</template>

<style scoped>
.tool-policy-tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  margin-bottom: var(--space-3, 12px);
}

.tool-policy-tab {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: none;
  background: transparent;
  color: var(--color-text-secondary, #a0a0aa);
  font-size: var(--font-size-sm, 0.8125rem);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color var(--transition-fast, 120ms ease), border-color var(--transition-fast, 120ms ease);
}

.tool-policy-tab:hover {
  color: var(--color-text-primary, #e4e4e8);
}

.tool-policy-tab:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: -2px;
}

.tool-policy-tab--active {
  color: var(--color-text-primary, #e4e4e8);
  border-bottom-color: var(--color-accent, #7c8adb);
}
</style>
