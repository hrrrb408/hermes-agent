<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, MessageSquare, Plus, Search } from '@lucide/vue'
import IconButton from '@/components/common/IconButton.vue'
import { shellSessions, type ShellSessionItem } from '@/mocks/workspace-shell'

const props = defineProps<{
  collapsed: boolean
  selectedSessionId: string
}>()

const emit = defineEmits<{
  toggle: []
  select: [session: ShellSessionItem]
}>()

const query = ref('')

const filteredSessions = computed(() => {
  const normalized = query.value.trim().toLowerCase()
  if (!normalized) return shellSessions
  return shellSessions.filter((session) =>
    `${session.title} ${session.preview} ${session.model}`.toLowerCase().includes(normalized),
  )
})
</script>

<template>
  <nav
    id="session-sidebar"
    class="session-sidebar"
    :class="{ 'session-sidebar--collapsed': props.collapsed }"
    aria-label="Sessions"
  >
    <div class="session-sidebar__toolbar">
      <button
        class="new-session-button"
        type="button"
        disabled
        aria-disabled="true"
        title="New session will be available in a later phase"
      >
        <Plus :size="16" aria-hidden="true" />
        <span v-if="!props.collapsed">New session</span>
        <small v-if="!props.collapsed">Preview</small>
      </button>
    </div>

    <div v-if="!props.collapsed" class="session-search">
      <Search :size="14" aria-hidden="true" />
      <input v-model="query" type="search" aria-label="Search preview sessions" placeholder="Search sessions" />
    </div>

    <div class="session-sidebar__heading">
      <span v-if="!props.collapsed">Recent sessions</span>
      <MessageSquare v-else :size="16" aria-hidden="true" />
    </div>

    <div class="session-list">
      <button
        v-for="session in filteredSessions"
        :key="session.id"
        class="session-item"
        :class="{ 'session-item--active': session.id === props.selectedSessionId }"
        type="button"
        :aria-current="session.id === props.selectedSessionId ? 'page' : undefined"
        :aria-label="props.collapsed ? session.title : undefined"
        :title="props.collapsed ? session.title : undefined"
        @click="emit('select', session)"
      >
        <MessageSquare class="session-item__icon" :size="16" aria-hidden="true" />
        <span v-if="!props.collapsed" class="session-item__content">
          <span class="session-item__row">
            <strong>{{ session.title }}</strong>
            <time>{{ session.time }}</time>
          </span>
          <span class="session-item__preview">{{ session.preview }}</span>
          <span class="session-item__model">{{ session.model }}</span>
        </span>
        <span v-if="session.id === props.selectedSessionId" class="session-item__current" aria-hidden="true">●</span>
      </button>

      <p v-if="filteredSessions.length === 0 && !props.collapsed" class="session-list__empty">
        No preview sessions match.
      </p>
    </div>

    <div class="session-sidebar__footer">
      <IconButton
        :label="props.collapsed ? 'Expand sessions sidebar' : 'Collapse sessions sidebar'"
        :expanded="!props.collapsed"
        controls="session-sidebar"
        @click="emit('toggle')"
      >
        <ChevronRight v-if="props.collapsed" :size="17" aria-hidden="true" />
        <ChevronLeft v-else :size="17" aria-hidden="true" />
      </IconButton>
      <span v-if="!props.collapsed">Collapse sidebar</span>
    </div>
  </nav>
</template>
