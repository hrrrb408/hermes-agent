<script setup lang="ts">
import { Loader2, Paperclip, Send, ShieldCheck, AlertCircle, RefreshCw } from '@lucide/vue'
import { useSessionStore } from '@/stores/session'
import type { MessageContent, MessageRole } from '@/types/api/message'

const store = useSessionStore()

function formatTime(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return ''
  }
}

/** Get a human-readable label for a message role. */
function getRoleLabel(role: MessageRole): string {
  switch (role) {
    case 'user': return 'You'
    case 'assistant': return 'Assistant'
    case 'tool': return 'Tool'
    case 'system': return 'System'
    default: return 'Unknown'
  }
}

/** Get CSS class modifier for a message role. */
function getRoleClass(role: MessageRole): string {
  switch (role) {
    case 'user': return 'message--user'
    case 'assistant': return 'message--assistant'
    case 'tool': return 'message--tool'
    case 'system': return 'message--system'
    default: return 'message--unknown'
  }
}

/** Extract display text from message content. */
function getContentText(content: MessageContent): string {
  if (content.type === 'text') return content.text
  if (content.type === 'empty') return ''
  if (content.type === 'unsupported') return '[Unsupported message content]'
  return ''
}

/** Check if content is text type. */
function isTextContent(content: MessageContent): boolean {
  return content.type === 'text'
}

/** Retry loading messages. */
function retryMessages(): void {
  if (store.selectedSessionId) {
    store.loadMessages(store.selectedSessionId)
  }
}
</script>

<template>
  <main class="chat-workspace">
    <header class="chat-workspace__header">
      <div>
        <h1>{{ store.selectedSession?.title ?? 'Hermes Dev Workspace' }}</h1>
        <p>{{ store.selectedSession ? `Session · ${store.selectedSession.source}` : 'Phase 0C · Read-only message integration' }}</p>
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
        <p class="workspace-empty-state__eyebrow">Phase 0C · Read-only message integration</p>
        <h2 id="workspace-empty-title">Hermes Dev Workspace</h2>
        <p>Select a session from the sidebar to view its messages.</p>
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
          <AlertCircle :size="20" aria-hidden="true" />
        </div>
        <p class="workspace-empty-state__eyebrow">Error</p>
        <h2>Unable to load session</h2>
        <p>{{ store.detailError ?? 'An unexpected error occurred.' }}</p>
      </section>

      <!-- Session loaded — show messages -->
      <div v-else-if="store.selectedSession" class="chat-messages">
        <!-- Session summary bar -->
        <div class="chat-messages__summary" aria-label="Session summary">
          <span>{{ store.selectedSession.title ?? 'Untitled session' }}</span>
          <span>{{ store.messageTotal }} messages</span>
          <span v-if="store.selectedSession.lastActiveAt">{{ formatTime(store.selectedSession.lastActiveAt) }}</span>
        </div>

        <!-- Messages loading -->
        <section
          v-if="store.isMessageLoading"
          class="workspace-empty-state"
          aria-busy="true"
          aria-live="polite"
        >
          <div class="workspace-empty-state__mark">
            <Loader2 :size="20" class="session-list__spinner" aria-hidden="true" />
          </div>
          <p class="workspace-empty-state__eyebrow">Loading messages...</p>
        </section>

        <!-- Messages error -->
        <section
          v-else-if="store.hasMessageError"
          class="workspace-empty-state"
          role="alert"
        >
          <div class="workspace-empty-state__mark">
            <AlertCircle :size="20" aria-hidden="true" />
          </div>
          <p class="workspace-empty-state__eyebrow">Error</p>
          <h2>Unable to load messages</h2>
          <p>{{ store.messageError ?? 'An unexpected error occurred.' }}</p>
          <button class="workspace-retry-btn" aria-label="Retry loading messages" @click="retryMessages">
            <RefreshCw :size="14" aria-hidden="true" />
            Retry
          </button>
        </section>

        <!-- Messages empty -->
        <section
          v-else-if="store.isMessageEmpty"
          class="workspace-empty-state"
          aria-labelledby="msg-empty-title"
        >
          <div class="workspace-empty-state__mark">
            <ShieldCheck :size="20" aria-hidden="true" />
          </div>
          <p class="workspace-empty-state__eyebrow">No messages</p>
          <h2 id="msg-empty-title">This session has no messages</h2>
          <p>Messages are read-only in Dev WebUI.</p>
        </section>

        <!-- Message list -->
        <ol
          v-else
          class="message-list"
          aria-label="Session messages"
        >
          <li
            v-for="msg in store.messages"
            :key="msg.id"
            :class="['message', getRoleClass(msg.role)]"
            :aria-label="`${getRoleLabel(msg.role)} message`"
          >
            <div class="message__header">
              <span class="message__role">{{ getRoleLabel(msg.role) }}</span>
              <time v-if="msg.timestamp" class="message__time" :datetime="msg.timestamp">
                {{ formatTime(msg.timestamp) }}
              </time>
            </div>

            <div class="message__body">
              <!-- Tool call info -->
              <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="message__tool-calls">
                <div v-for="tc in msg.toolCalls" :key="tc.id" class="tool-call-card">
                  <span class="tool-call-card__name">{{ tc.function.name }}</span>
                </div>
              </div>

              <!-- Tool message with tool name -->
              <div v-if="msg.role === 'tool' && msg.toolName" class="message__tool-info">
                Tool: {{ msg.toolName }}
              </div>

              <!-- Content -->
              <div
                v-if="isTextContent(msg.content)"
                class="message__text"
              >{{ getContentText(msg.content) }}</div>
              <div v-else-if="msg.content.type === 'empty'" class="message__empty">
                [Empty message]
              </div>
              <div v-else class="message__unsupported">
                [Unsupported message content]
              </div>
            </div>
          </li>
        </ol>

        <!-- Load more -->
        <div v-if="store.messageHasMore && !store.isMessageLoading && !store.hasMessageError" class="chat-messages__load-more">
          <button
            class="workspace-retry-btn"
            :disabled="store.isMessageLoadingMore"
            aria-label="Load more messages"
            @click="store.loadMoreMessages()"
          >
            <Loader2 v-if="store.isMessageLoadingMore" :size="14" class="session-list__spinner" aria-hidden="true" />
            <span>{{ store.isMessageLoadingMore ? 'Loading...' : 'Load more messages' }}</span>
          </button>
        </div>

        <!-- Read-only notice -->
        <div class="chat-messages__readonly-notice">
          Messages are read-only in Dev WebUI
        </div>
      </div>
    </div>

    <form class="composer" @submit.prevent>
      <label class="composer__label" for="workspace-composer">Message composer</label>
      <textarea
        id="workspace-composer"
        rows="3"
        aria-label="Message composer preview"
        placeholder="Messages are read-only in Dev WebUI..."
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

<style scoped>
/* ── Message list ── */

.chat-messages {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.chat-messages__summary {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 16px;
  font-size: 0.8em;
  color: var(--color-text-tertiary, #888);
  border-bottom: 1px solid var(--color-border, rgba(128, 128, 128, 0.15));
  flex-shrink: 0;
}

.message-list {
  list-style: none;
  margin: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1 1 auto;
}

/* ── Message item ── */

.message {
  padding: 10px 14px;
  border-radius: var(--radius-md, 6px);
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.12));
  max-width: 85%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.message--user {
  align-self: flex-end;
  background: var(--color-user-msg-bg, rgba(59, 130, 246, 0.08));
  border-color: var(--color-user-msg-border, rgba(59, 130, 246, 0.15));
}

.message--assistant {
  align-self: flex-start;
  background: var(--color-assistant-msg-bg, transparent);
  max-width: 95%;
}

.message--tool,
.message--system,
.message--unknown {
  align-self: flex-start;
  background: var(--color-system-msg-bg, rgba(128, 128, 128, 0.05));
  font-size: 0.9em;
  border-style: dashed;
}

.message__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.message__role {
  font-size: 0.75em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary, #666);
}

.message__time {
  font-size: 0.7em;
  color: var(--color-text-tertiary, #999);
  white-space: nowrap;
}

.message__body {
  line-height: 1.5;
}

.message__text {
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.message__empty {
  color: var(--color-text-tertiary, #999);
  font-style: italic;
}

.message__unsupported {
  color: var(--color-text-tertiary, #999);
  font-style: italic;
}

.message__tool-info {
  font-size: 0.85em;
  color: var(--color-text-secondary, #666);
  margin-bottom: 4px;
}

/* ── Tool call card ── */

.message__tool-calls {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.tool-call-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--color-tool-card-bg, rgba(128, 128, 128, 0.06));
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.1));
  border-radius: var(--radius-sm, 4px);
  font-size: 0.8em;
  font-family: var(--font-mono, monospace);
}

.tool-call-card__name {
  font-weight: 500;
  color: var(--color-text-secondary, #555);
}

/* ── Load more ── */

.chat-messages__load-more {
  display: flex;
  justify-content: center;
  padding: 12px;
  flex-shrink: 0;
}

.chat-messages__readonly-notice {
  text-align: center;
  padding: 8px;
  font-size: 0.75em;
  color: var(--color-text-tertiary, #999);
  flex-shrink: 0;
  border-top: 1px solid var(--color-border, rgba(128, 128, 128, 0.08));
}

/* ── Retry button ── */

.workspace-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.2));
  border-radius: var(--radius-sm, 4px);
  background: transparent;
  color: var(--color-text-primary, inherit);
  cursor: pointer;
  font-size: 0.85em;
  transition: background 0.15s;
}

.workspace-retry-btn:hover {
  background: var(--color-hover, rgba(128, 128, 128, 0.06));
}

.workspace-retry-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
