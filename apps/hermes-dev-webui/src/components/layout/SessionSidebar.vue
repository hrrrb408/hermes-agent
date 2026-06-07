<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { AlertCircle, ChevronLeft, ChevronRight, Loader2, MessageSquare, Plus, RefreshCw, Search } from '@lucide/vue'
import IconButton from '@/components/common/IconButton.vue'
import { useSessionStore } from '@/stores/session'
import type { SessionListItem } from '@/types/api/session'

const props = defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const store = useSessionStore()

const localSearch = ref('')
let searchCleanup: (() => void) | null = null

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    const now = Date.now()
    const diffMs = now - date.getTime()
    const diffMinutes = Math.floor(diffMs / 60_000)

    if (diffMinutes < 1) return 'Now'
    if (diffMinutes < 60) return `${diffMinutes}m`
    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) return `${diffHours}h`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d`
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

function handleSearchInput(): void {
  store.setSearchQuery(localSearch.value)
}

function handleRetry(): void {
  store.reloadSessions()
}

function handleSelectSession(session: SessionListItem): void {
  store.selectSession(session.id)
}

function handleLoadMore(): void {
  store.loadMoreSessions()
}

onMounted(() => {
  // Initialize store if not already loaded
  if (store.listStatus === 'idle') {
    store.initialize()
  }
})

onUnmounted(() => {
  if (searchCleanup) {
    searchCleanup()
    searchCleanup = null
  }
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
      <input
        v-model="localSearch"
        type="search"
        aria-label="Search session title or ID"
        placeholder="Search title or ID"
        @input="handleSearchInput"
      />
    </div>

    <div class="session-sidebar__heading">
      <span v-if="!props.collapsed">Recent sessions</span>
      <MessageSquare v-else :size="16" aria-hidden="true" />
    </div>

    <div
      class="session-list"
      :aria-busy="store.isLoading"
    >
      <!-- Loading state -->
      <div v-if="store.isLoading && !props.collapsed" class="session-list__loading" aria-live="polite">
        <Loader2 :size="18" class="session-list__spinner" aria-hidden="true" />
        <span>Loading sessions...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="store.hasError && !props.collapsed" class="session-list__error" role="alert">
        <AlertCircle :size="18" aria-hidden="true" />
        <span>{{ store.listError || 'Unable to load sessions.' }}</span>
        <button
          type="button"
          class="session-list__retry"
          @click="handleRetry"
        >
          <RefreshCw :size="14" aria-hidden="true" />
          Retry
        </button>
      </div>

      <!-- Empty state -->
      <p
        v-else-if="store.isEmpty && !store.searchQuery && !props.collapsed"
        class="session-list__empty"
        aria-live="polite"
      >
        No development sessions found.
        <button
          type="button"
          class="session-list__retry"
          @click="handleRetry"
        >
          <RefreshCw :size="14" aria-hidden="true" />
          Refresh
        </button>
      </p>

      <!-- Search empty state -->
      <p
        v-else-if="store.isEmpty && store.searchQuery && !props.collapsed"
        class="session-list__empty"
        aria-live="polite"
      >
        No sessions match "{{ store.searchQuery }}".
      </p>

      <!-- Session items (shown when loading more, success, or has data) -->
      <template v-else>
        <button
          v-for="session in store.sessions"
          :key="session.id"
          class="session-item"
          :class="{ 'session-item--active': session.id === store.selectedSessionId }"
          type="button"
          :aria-current="session.id === store.selectedSessionId ? 'page' : undefined"
          :aria-label="props.collapsed ? (session.title ?? 'Untitled session') : undefined"
          :title="props.collapsed ? (session.title ?? 'Untitled session') : undefined"
          @click="handleSelectSession(session)"
        >
          <MessageSquare class="session-item__icon" :size="16" aria-hidden="true" />
          <span v-if="!props.collapsed" class="session-item__content">
            <span class="session-item__row">
              <strong>{{ session.title ?? 'Untitled session' }}</strong>
              <time>{{ formatRelativeTime(session.lastActiveAt ?? session.startedAt) }}</time>
            </span>
            <span class="session-item__preview">{{ session.preview ?? session.source }}</span>
            <span class="session-item__model">{{ session.model ?? session.source }}</span>
          </span>
          <span v-if="session.id === store.selectedSessionId" class="session-item__current" aria-hidden="true">●</span>
        </button>

        <!-- Load more -->
        <button
          v-if="store.hasMore && !props.collapsed"
          class="session-list__load-more"
          type="button"
          :disabled="store.isLoadingMore"
          @click="handleLoadMore"
        >
          <Loader2 v-if="store.isLoadingMore" :size="14" class="session-list__spinner" aria-hidden="true" />
          {{ store.isLoadingMore ? 'Loading...' : 'Load more' }}
        </button>
      </template>
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
