<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAgentStore } from '@/stores/workspacePanel'
import { useAgentPreviewStore } from '@/stores/agentPreview'
import AgentPreviewResult from './AgentPreviewResult.vue'
import AgentLiveRun from './AgentLiveRun.vue'

type AgentTab = 'status' | 'promptPreview' | 'dryRun' | 'liveRun'

const store = useAgentStore()
const previewStore = useAgentPreviewStore()

const activeTab = ref<AgentTab>('status')

onMounted(() => {
  store.loadStatus()
})

function setTab(tab: AgentTab): void {
  activeTab.value = tab
  if (tab === 'promptPreview') {
    previewStore.setMode('prompt')
  } else if (tab === 'dryRun') {
    previewStore.setMode('dryRun')
  }
}

function handleKeyDown(event: KeyboardEvent, tab: AgentTab): void {
  const tabs: AgentTab[] = ['status', 'promptPreview', 'dryRun', 'liveRun']
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
    setTab(nextTab)
    document.getElementById(`agent-tab-${nextTab}`)?.focus()
  }
}
</script>

<template>
  <section class="workspace-panel__section" aria-label="Agent Panel">
    <!-- Sub-tabs -->
    <div class="agent-tabs" role="tablist" aria-label="Agent panel tabs">
      <button
        id="agent-tab-status"
        type="button"
        role="tab"
        class="agent-tab"
        :class="{ 'agent-tab--active': activeTab === 'status' }"
        :aria-selected="activeTab === 'status'"
        :aria-controls="'agent-tabpanel-status'"
        :tabindex="activeTab === 'status' ? 0 : -1"
        @click="setTab('status')"
        @keydown="handleKeyDown($event, 'status')"
      >Status</button>
      <button
        id="agent-tab-promptPreview"
        type="button"
        role="tab"
        class="agent-tab"
        :class="{ 'agent-tab--active': activeTab === 'promptPreview' }"
        :aria-selected="activeTab === 'promptPreview'"
        :aria-controls="'agent-tabpanel-promptPreview'"
        :tabindex="activeTab === 'promptPreview' ? 0 : -1"
        @click="setTab('promptPreview')"
        @keydown="handleKeyDown($event, 'promptPreview')"
      >Prompt Preview</button>
      <button
        id="agent-tab-dryRun"
        type="button"
        role="tab"
        class="agent-tab"
        :class="{ 'agent-tab--active': activeTab === 'dryRun' }"
        :aria-selected="activeTab === 'dryRun'"
        :aria-controls="'agent-tabpanel-dryRun'"
        :tabindex="activeTab === 'dryRun' ? 0 : -1"
        @click="setTab('dryRun')"
        @keydown="handleKeyDown($event, 'dryRun')"
      >Run Dry-Run</button>
      <button
        id="agent-tab-liveRun"
        type="button"
        role="tab"
        class="agent-tab"
        :class="{ 'agent-tab--active': activeTab === 'liveRun' }"
        :aria-selected="activeTab === 'liveRun'"
        :aria-controls="'agent-tabpanel-liveRun'"
        :tabindex="activeTab === 'liveRun' ? 0 : -1"
        @click="setTab('liveRun')"
        @keydown="handleKeyDown($event, 'liveRun')"
      >Live Run</button>
    </div>

    <!-- Status Tab -->
    <div
      v-if="activeTab === 'status'"
      id="agent-tabpanel-status"
      role="tabpanel"
      aria-labelledby="agent-tab-status"
      tabindex="0"
    >
      <!-- Loading -->
      <div v-if="store.state === 'loading'" class="panel-loading" aria-busy="true">
        Loading agent status…
      </div>

      <!-- Error -->
      <div v-else-if="store.state === 'error'" class="panel-error" role="alert">
        <p>{{ store.error }}</p>
        <button type="button" class="panel-retry-btn" aria-label="Retry loading agent status" @click="store.loadStatus()">Retry</button>
      </div>

      <!-- Unavailable -->
      <div v-else-if="!store.status?.available" class="panel-empty">
        Agent status is not available.
      </div>

      <!-- Status content -->
      <template v-else-if="store.status">
        <div class="panel-header">
          <span class="panel-badge" :class="{ 'panel-badge--active': store.status.available }">
            {{ store.status.available ? 'Available' : 'Unavailable' }}
          </span>
          <span class="panel-badge">Read-only</span>
        </div>

        <article class="panel-card">
          <h4>Runtime</h4>
          <dl class="context-list">
            <div><dt>Entry</dt><dd>{{ store.status.runtime.entry }}</dd></div>
            <div><dt>Message send</dt><dd class="panel-flag panel-flag--disabled">{{ store.status.runtime.messageSendEnabled ? 'Enabled' : 'Disabled' }}</dd></div>
            <div><dt>Streaming</dt><dd class="panel-flag panel-flag--disabled">{{ store.status.runtime.streamingEnabled ? 'Enabled' : 'Disabled' }}</dd></div>
            <div><dt>Tool execution</dt><dd class="panel-flag panel-flag--disabled">{{ store.status.runtime.toolExecutionEnabled ? 'Enabled' : 'Disabled' }}</dd></div>
          </dl>
        </article>

        <article class="panel-card">
          <h4>Model</h4>
          <dl class="context-list">
            <div><dt>Configured</dt><dd>{{ store.status.model.configured ? 'Yes' : 'No' }}</dd></div>
            <div v-if="store.status.model.provider"><dt>Provider</dt><dd>{{ store.status.model.provider }}</dd></div>
            <div v-if="store.status.model.name"><dt>Model</dt><dd>{{ store.status.model.name }}</dd></div>
          </dl>
        </article>

        <article class="panel-card">
          <h4>Memory</h4>
          <dl class="context-list">
            <div><dt>Memory enabled</dt><dd :class="store.status.memory.enabled ? 'panel-flag--enabled' : 'panel-flag--disabled'">{{ store.status.memory.enabled ? 'Yes' : 'No' }}</dd></div>
            <div><dt>Context loader</dt><dd :class="store.status.memory.contextLoaderEnabled ? 'panel-flag--enabled' : 'panel-flag--disabled'">{{ store.status.memory.contextLoaderEnabled ? 'Enabled' : 'Disabled' }}</dd></div>
            <div><dt>Auto write</dt><dd class="panel-flag panel-flag--disabled">{{ store.status.memory.autoWriteEnabled ? 'Enabled' : 'Disabled' }}</dd></div>
            <div><dt>Review queue</dt><dd class="panel-flag panel-flag--disabled">{{ store.status.memory.reviewQueueEnabled ? 'Enabled' : 'Disabled' }}</dd></div>
          </dl>
        </article>
      </template>
    </div>

    <!-- Prompt Preview Tab -->
    <div
      v-if="activeTab === 'promptPreview'"
      id="agent-tabpanel-promptPreview"
      role="tabpanel"
      aria-labelledby="agent-tab-promptPreview"
      tabindex="0"
    >
      <form class="preview-form" @submit.prevent="previewStore.previewPrompt()">
        <div class="form-group">
          <label for="pp-session-id">Session ID <span class="form-optional">(optional)</span></label>
          <input id="pp-session-id" v-model="previewStore.promptForm.sessionId" type="text" class="form-input" maxlength="200" placeholder="Enter session ID" />
        </div>
        <div class="form-group">
          <label for="pp-message">Message <span class="form-required">*</span></label>
          <textarea id="pp-message" v-model="previewStore.promptForm.message" class="form-textarea" rows="3" maxlength="4000" placeholder="Enter message to preview prompt assembly" required></textarea>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.promptForm.includeHistory" type="checkbox" />
            <span>Include history</span>
          </label>
          <label v-if="previewStore.promptForm.includeHistory" class="form-inline">
            <span>Limit</span>
            <input v-model.number="previewStore.promptForm.historyLimit" type="number" class="form-input form-input--small" min="0" max="100" />
          </label>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.promptForm.includeMemoryContext" type="checkbox" />
            <span>Memory context</span>
          </label>
        </div>
        <div v-if="previewStore.promptForm.includeMemoryContext" class="form-row">
          <input v-model="previewStore.promptForm.memoryQuery" type="text" class="form-input form-input--small" placeholder="Memory query (optional)" maxlength="1000" />
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.promptForm.includeSystemPreview" type="checkbox" />
            <span>System preview</span>
          </label>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.promptForm.includeToolMetadata" type="checkbox" />
            <span>Tool metadata</span>
          </label>
        </div>
        <div class="form-actions">
          <button type="submit" class="preview-btn" :disabled="previewStore.isLoading">
            {{ previewStore.isLoading ? 'Previewing…' : 'Preview Prompt' }}
          </button>
          <button type="button" class="clear-btn" @click="previewStore.clear()">Clear</button>
        </div>
      </form>

      <!-- Loading -->
      <div v-if="previewStore.isLoading" class="panel-loading" aria-busy="true">Loading preview…</div>

      <!-- Error -->
      <div v-else-if="previewStore.status === 'error'" class="panel-error" role="alert">
        <p>{{ previewStore.error }}</p>
        <button type="button" class="panel-retry-btn" @click="previewStore.retry()">Retry</button>
      </div>

      <!-- Result -->
      <AgentPreviewResult v-else-if="previewStore.hasResult && previewStore.activeMode === 'prompt'" :result="previewStore.result!" />
    </div>

    <!-- Run Dry-Run Tab -->
    <div
      v-if="activeTab === 'dryRun'"
      id="agent-tabpanel-dryRun"
      role="tabpanel"
      aria-labelledby="agent-tab-dryRun"
      tabindex="0"
    >
      <form class="preview-form" @submit.prevent="previewStore.previewRun()">
        <div class="form-group">
          <label for="dr-session-id">Session ID <span class="form-optional">(optional)</span></label>
          <input id="dr-session-id" v-model="previewStore.dryRunForm.sessionId" type="text" class="form-input" maxlength="200" placeholder="Enter session ID" />
        </div>
        <div class="form-group">
          <label for="dr-message">Message <span class="form-required">*</span></label>
          <textarea id="dr-message" v-model="previewStore.dryRunForm.message" class="form-textarea" rows="3" maxlength="4000" placeholder="Enter message to preview agent run" required></textarea>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.dryRunForm.includeHistory" type="checkbox" />
            <span>Include history</span>
          </label>
          <label v-if="previewStore.dryRunForm.includeHistory" class="form-inline">
            <span>Limit</span>
            <input v-model.number="previewStore.dryRunForm.historyLimit" type="number" class="form-input form-input--small" min="0" max="100" />
          </label>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.dryRunForm.includeMemoryContext" type="checkbox" />
            <span>Memory context</span>
          </label>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.dryRunForm.toolsRequested" type="checkbox" />
            <span>Request tools</span>
            <span class="form-hint">(forced disabled)</span>
          </label>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.dryRunForm.streamRequested" type="checkbox" />
            <span>Request streaming</span>
            <span class="form-hint">(forced disabled)</span>
          </label>
        </div>
        <div class="form-row">
          <label class="form-toggle">
            <input v-model="previewStore.dryRunForm.autoMemoryRequested" type="checkbox" />
            <span>Request auto-memory</span>
            <span class="form-hint">(forced disabled)</span>
          </label>
        </div>
        <div class="form-actions">
          <button type="submit" class="preview-btn" :disabled="previewStore.isLoading">
            {{ previewStore.isLoading ? 'Previewing…' : 'Preview Agent Run' }}
          </button>
          <button type="button" class="clear-btn" @click="previewStore.clear()">Clear</button>
        </div>
      </form>

      <!-- Loading -->
      <div v-if="previewStore.isLoading" class="panel-loading" aria-busy="true">Loading dry-run…</div>

      <!-- Error -->
      <div v-else-if="previewStore.status === 'error'" class="panel-error" role="alert">
        <p>{{ previewStore.error }}</p>
        <button type="button" class="panel-retry-btn" @click="previewStore.retry()">Retry</button>
      </div>

      <!-- Result -->
      <AgentPreviewResult v-else-if="previewStore.hasResult && previewStore.activeMode === 'dryRun'" :result="previewStore.result!" />
    </div>

    <!-- Live Run Tab -->
    <div
      v-if="activeTab === 'liveRun'"
      id="agent-tabpanel-liveRun"
      role="tabpanel"
      aria-labelledby="agent-tab-liveRun"
      tabindex="0"
    >
      <AgentLiveRun />
    </div>
  </section>
</template>

<style scoped>
.agent-tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  margin-bottom: var(--space-3, 12px);
}

.agent-tab {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: none;
  background: transparent;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
  font-size: 0.8125rem;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.agent-tab:hover {
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
}

.agent-tab:focus-visible {
  outline: 2px solid var(--color-focus, #3b82f6);
  outline-offset: -2px;
}

.agent-tab--active {
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
  border-bottom-color: var(--color-accent, #3b82f6);
}

/* Form styles */
.preview-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.form-group label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
}

.form-optional {
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
  font-weight: normal;
}

.form-required {
  color: var(--color-error-text, #ef4444);
}

.form-input,
.form-textarea {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-input-bg, rgba(255, 255, 255, 0.05));
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
  font-size: 0.8125rem;
  font-family: inherit;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-focus, #3b82f6);
  box-shadow: 0 0 0 1px var(--color-focus, #3b82f6);
}

.form-input--small {
  width: 5rem;
}

.form-textarea {
  resize: vertical;
  min-height: 3rem;
}

.form-row {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}

.form-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-1, 4px);
  font-size: 0.8125rem;
  cursor: pointer;
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
}

.form-toggle input[type="checkbox"] {
  accent-color: var(--color-accent, #3b82f6);
}

.form-inline {
  display: flex;
  align-items: center;
  gap: var(--space-1, 4px);
  font-size: 0.8125rem;
}

.form-hint {
  font-size: 0.6875rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.4));
  font-style: italic;
}

.form-actions {
  display: flex;
  gap: var(--space-2, 8px);
  margin-top: var(--space-2, 8px);
}

.preview-btn {
  padding: var(--space-1, 4px) var(--space-3, 12px);
  border: 1px solid var(--color-accent, #3b82f6);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-accent, #3b82f6);
  color: white;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: opacity 0.15s;
}

.preview-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.preview-btn:focus-visible {
  outline: 2px solid var(--color-focus, #3b82f6);
  outline-offset: 2px;
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.clear-btn {
  padding: var(--space-1, 4px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: transparent;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
  font-size: 0.8125rem;
  cursor: pointer;
}

.clear-btn:hover {
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
  border-color: var(--color-text-secondary, rgba(255, 255, 255, 0.3));
}
</style>
