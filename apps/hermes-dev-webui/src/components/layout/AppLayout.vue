<script setup lang="ts">
import { ref } from 'vue'
import ChatWorkspaceShell from './ChatWorkspaceShell.vue'
import SessionSidebar from './SessionSidebar.vue'
import TopStatusBar from './TopStatusBar.vue'
import WorkspacePanel from './WorkspacePanel.vue'
import { defaultShellSession, type ShellSessionItem } from '@/mocks/workspace-shell'
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()
const selectedSession = ref<ShellSessionItem>(defaultShellSession)
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
        :selected-session-id="selectedSession.id"
        @toggle="uiStore.toggleSidebar"
        @select="selectedSession = $event"
      />
      <ChatWorkspaceShell :session="selectedSession" />
      <WorkspacePanel :collapsed="uiStore.workspaceCollapsed" @toggle="uiStore.toggleWorkspace" />
    </div>
  </div>
</template>
