<script setup lang="ts">
import { Activity, Brain, ChevronLeft, ChevronRight, FolderTree, Layers } from '@lucide/vue'
import IconButton from '@/components/common/IconButton.vue'
import AgentPanel from '@/components/workspace/AgentPanel.vue'
import ContextPanel from '@/components/workspace/ContextPanel.vue'
import FilesPlaceholder from '@/components/workspace/FilesPlaceholder.vue'
import MemoryPanel from '@/components/workspace/MemoryPanel.vue'
import { useUiStore, type WorkspaceTab } from '@/stores/ui'

const props = defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const uiStore = useUiStore()

const tabs = [
  { id: 'files', label: 'Files', icon: FolderTree },
  { id: 'memory', label: 'Memory', icon: Brain },
  { id: 'context', label: 'Context', icon: Layers },
  { id: 'agent', label: 'Agent', icon: Activity },
] as const

function selectTab(tab: WorkspaceTab): void {
  uiStore.setWorkspaceTab(tab)
  if (props.collapsed) emit('toggle')
}

function moveTab(event: KeyboardEvent, tab: WorkspaceTab): void {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()

  const currentIndex = tabs.findIndex((item) => item.id === tab)
  let nextIndex = currentIndex
  if (event.key === 'Home') nextIndex = 0
  if (event.key === 'End') nextIndex = tabs.length - 1
  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
  }
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    nextIndex = (currentIndex + 1) % tabs.length
  }

  const nextTab = tabs[nextIndex]
  if (!nextTab) return
  selectTab(nextTab.id)
  document.getElementById(`workspace-tab-${nextTab.id}`)?.focus()
}
</script>

<template>
  <aside
    id="workspace-panel"
    class="workspace-panel"
    :class="{ 'workspace-panel--collapsed': props.collapsed }"
    aria-label="Workspace context"
  >
    <header class="workspace-panel__header">
      <div v-if="!props.collapsed">
        <h2>Workspace</h2>
        <p>Static context surfaces</p>
      </div>
      <IconButton
        :label="props.collapsed ? 'Expand workspace panel' : 'Collapse workspace panel'"
        :expanded="!props.collapsed"
        controls="workspace-panel"
        @click="emit('toggle')"
      >
        <ChevronLeft v-if="props.collapsed" :size="17" aria-hidden="true" />
        <ChevronRight v-else :size="17" aria-hidden="true" />
      </IconButton>
    </header>

    <div class="workspace-tabs" role="tablist" aria-label="Workspace panels" aria-orientation="vertical">
      <button
        v-for="tab in tabs"
        :id="`workspace-tab-${tab.id}`"
        :key="tab.id"
        class="workspace-tab"
        :class="{ 'workspace-tab--active': uiStore.workspaceTab === tab.id }"
        type="button"
        role="tab"
        :aria-label="props.collapsed ? `${tab.label} workspace tab` : undefined"
        :aria-selected="uiStore.workspaceTab === tab.id"
        :aria-controls="`workspace-tabpanel-${tab.id}`"
        :tabindex="uiStore.workspaceTab === tab.id ? 0 : -1"
        @click="selectTab(tab.id)"
        @keydown="moveTab($event, tab.id)"
      >
        <component :is="tab.icon" :size="16" aria-hidden="true" />
        <span v-if="!props.collapsed">{{ tab.label }}</span>
      </button>
    </div>

    <div
      v-if="!props.collapsed"
      :id="`workspace-tabpanel-${uiStore.workspaceTab}`"
      class="workspace-panel__content"
      role="tabpanel"
      :aria-labelledby="`workspace-tab-${uiStore.workspaceTab}`"
      tabindex="0"
    >
      <FilesPlaceholder v-if="uiStore.workspaceTab === 'files'" />
      <MemoryPanel v-else-if="uiStore.workspaceTab === 'memory'" />
      <ContextPanel v-else-if="uiStore.workspaceTab === 'context'" />
      <AgentPanel v-else />
    </div>
  </aside>
</template>
