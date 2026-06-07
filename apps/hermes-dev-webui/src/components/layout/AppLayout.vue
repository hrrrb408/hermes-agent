<script setup lang="ts">
import { onMounted } from 'vue'
import ChatWorkspaceShell from './ChatWorkspaceShell.vue'
import SessionSidebar from './SessionSidebar.vue'
import TopStatusBar from './TopStatusBar.vue'
import WorkspacePanel from './WorkspacePanel.vue'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()
const sessionStore = useSessionStore()

onMounted(() => {
  if (sessionStore.listStatus === 'idle') {
    sessionStore.initialize()
  }
})
</script>

<template>
  <div
    class="workspace-page"
    :class="{
      'workspace-page--sidebar-collapsed': uiStore.sidebarCollapsed,
      'workspace-page--panel-collapsed': uiStore.workspaceCollapsed,
    }"
  >
    <TopStatusBar />
    <div class="workspace-body">
      <SessionSidebar
        :collapsed="uiStore.sidebarCollapsed"
        @toggle="uiStore.toggleSidebar"
      />
      <ChatWorkspaceShell />
      <WorkspacePanel :collapsed="uiStore.workspaceCollapsed" @toggle="uiStore.toggleWorkspace" />
    </div>
  </div>
</template>
