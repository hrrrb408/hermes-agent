<script setup lang="ts">
import { Paperclip, Send, ShieldCheck } from '@lucide/vue'
import { workspaceCapabilities, type ShellSessionItem } from '@/mocks/workspace-shell'

defineProps<{
  session: ShellSessionItem
}>()
</script>

<template>
  <main class="chat-workspace">
    <header class="chat-workspace__header">
      <div>
        <h1>{{ session.title }}</h1>
        <p>Static workspace shell</p>
      </div>
      <div class="chat-workspace__meta">
        <span>{{ session.model }}</span>
        <span>Preview only</span>
      </div>
    </header>

    <div class="chat-workspace__scroll">
      <section class="workspace-empty-state" aria-labelledby="workspace-empty-title">
        <div class="workspace-empty-state__mark">
          <ShieldCheck :size="20" aria-hidden="true" />
        </div>
        <p class="workspace-empty-state__eyebrow">Phase 0B · Static preview</p>
        <h2 id="workspace-empty-title">Hermes Dev Workspace</h2>
        <p>Agent connection will be added in Phase 1.</p>
        <ul class="workspace-capabilities" aria-label="Future workspace capabilities">
          <li v-for="capability in workspaceCapabilities" :key="capability">{{ capability }}</li>
        </ul>
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
        <span>Preview shell · Agent not connected</span>
        <div class="composer__actions">
          <button type="button" disabled aria-label="Attach file - Preview only" title="Attachment is unavailable in Phase 0B">
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
