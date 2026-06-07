<script setup lang="ts">
import { Loader2, Paperclip, Send, ShieldCheck } from '@lucide/vue'
import { useSessionStore } from '@/stores/session'

const store = useSessionStore()

function formatTime(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return ''
  }
}
</script>

<template>
  <main class="chat-workspace">
    <header class="chat-workspace__header">
      <div>
        <h1>{{ store.selectedSession?.title ?? 'Hermes Dev Workspace' }}</h1>
        <p>{{ store.selectedSession ? `Session · ${store.selectedSession.source}` : 'Phase 0C · Session integration' }}</p>
      </div>
      <div class="chat-workspace__meta">
        <span v-if="store.selectedSession?.model">{{ store.selectedSession.model }}</span>
        <span>Read only</span>
      </div>
    </header>

    <div class="chat-workspace__scroll">
      <!-- No session selected -->
      <section
        v-if="!store.selectedSessionId"
        class="workspace-empty-state"
        aria-labelledby="workspace-empty-title"
      >
        <div class="workspace-empty-state__mark">
          <ShieldCheck :size="20" aria-hidden="true" />
        </div>
        <p class="workspace-empty-state__eyebrow">Phase 0C · Session read-only integration</p>
        <h2 id="workspace-empty-title">Hermes Dev Workspace</h2>
        <p>Select a session from the sidebar to view its details.</p>
      </section>

      <!-- Session selected, detail loading -->
      <section
        v-else-if="store.isDetailLoading"
        class="workspace-empty-state"
        aria-busy="true"
        aria-live="polite"
      >
        <div class="workspace-empty-state__mark">
          <Loader2 :size="20" class="session-list__spinner" aria-hidden="true" />
        </div>
        <p class="workspace-empty-state__eyebrow">Loading session detail...</p>
      </section>

      <!-- Session selected, detail error -->
      <section
        v-else-if="store.hasDetailError"
        class="workspace-empty-state"
        role="alert"
      >
        <div class="workspace-empty-state__mark">
          <ShieldCheck :size="20" aria-hidden="true" />
        </div>
        <p class="workspace-empty-state__eyebrow">Error</p>
        <h2>Unable to load session</h2>
        <p>{{ store.detailError ?? 'An unexpected error occurred.' }}</p>
      </section>

      <!-- Session detail loaded — show safe summary -->
      <section
        v-else-if="store.selectedSession"
        class="workspace-empty-state"
        aria-labelledby="workspace-detail-title"
      >
        <div class="workspace-empty-state__mark">
          <ShieldCheck :size="20" aria-hidden="true" />
        </div>
        <p class="workspace-empty-state__eyebrow">Session Detail</p>
        <h2 id="workspace-detail-title">{{ store.selectedSession.title ?? 'Untitled session' }}</h2>
        <ul class="workspace-capabilities" aria-label="Session details">
          <li>Source: {{ store.selectedSession.source }}</li>
          <li v-if="store.selectedSession.model">Model: {{ store.selectedSession.model }}</li>
          <li>Messages: {{ store.selectedSession.messageCount }}</li>
          <li v-if="store.selectedSession.lastActiveAt">Last active: {{ formatTime(store.selectedSession.lastActiveAt) }}</li>
          <li v-if="store.selectedSession.archived">Archived</li>
        </ul>
        <p class="workspace-empty-state__note">Message history integration will be available in Phase 0C-04.</p>
      </section>
    </div>

    <form class="composer" @submit.prevent>
      <label class="composer__label" for="workspace-composer">Message composer</label>
      <textarea
        id="workspace-composer"
        rows="3"
        aria-label="Message composer preview"
        placeholder="Draft a message for the future Agent connection..."
        @keydown.enter.exact.prevent
      ></textarea>
      <div class="composer__footer">
        <span>Read only · Messages not available</span>
        <div class="composer__actions">
          <button type="button" disabled aria-label="Attach file - Preview only" title="Attachment is unavailable in Phase 0C">
            <Paperclip :size="17" aria-hidden="true" />
          </button>
          <button class="composer__send" type="submit" disabled aria-label="Send message - Preview only">
            <Send :size="15" aria-hidden="true" />
            <span>Send · Preview</span>
          </button>
        </div>
      </div>
    </form>
  </main>
</template>
