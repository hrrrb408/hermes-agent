<script setup lang="ts">
import { onMounted } from 'vue'
import { useAgentStore } from '@/stores/workspacePanel'

const store = useAgentStore()

onMounted(() => {
  store.loadStatus()
})
</script>

<template>
  <section class="workspace-panel__section" aria-label="Agent Status">
    <!-- Loading -->
    <div v-if="store.state === 'loading'" class="panel-loading">
      Loading agent status…
    </div>

    <!-- Error -->
    <div v-else-if="store.state === 'error'" class="panel-error">
      <p>{{ store.error }}</p>
      <button type="button" class="panel-retry-btn" @click="store.loadStatus()">Retry</button>
    </div>

    <!-- Unavailable -->
    <div v-else-if="!store.status?.available" class="panel-empty">
      Agent status is not available.
    </div>

    <!-- Status content -->
    <template v-else-if="store.status">
      <!-- Header badges -->
      <div class="panel-header">
        <span class="panel-badge" :class="{ 'panel-badge--active': store.status.available }">
          {{ store.status.available ? 'Available' : 'Unavailable' }}
        </span>
        <span class="panel-badge">Read-only</span>
      </div>

      <!-- Runtime status -->
      <article class="panel-card">
        <h4>Runtime</h4>
        <dl class="context-list">
          <div><dt>Entry</dt><dd>{{ store.status.runtime.entry }}</dd></div>
          <div>
            <dt>Message send</dt>
            <dd class="panel-flag panel-flag--disabled">
              {{ store.status.runtime.messageSendEnabled ? 'Enabled' : 'Disabled' }}
            </dd>
          </div>
          <div>
            <dt>Streaming</dt>
            <dd class="panel-flag panel-flag--disabled">
              {{ store.status.runtime.streamingEnabled ? 'Enabled' : 'Disabled' }}
            </dd>
          </div>
          <div>
            <dt>Tool execution</dt>
            <dd class="panel-flag panel-flag--disabled">
              {{ store.status.runtime.toolExecutionEnabled ? 'Enabled' : 'Disabled' }}
            </dd>
          </div>
        </dl>
      </article>

      <!-- Model status -->
      <article class="panel-card">
        <h4>Model</h4>
        <dl class="context-list">
          <div><dt>Configured</dt><dd>{{ store.status.model.configured ? 'Yes' : 'No' }}</dd></div>
          <div v-if="store.status.model.provider"><dt>Provider</dt><dd>{{ store.status.model.provider }}</dd></div>
          <div v-if="store.status.model.name"><dt>Model</dt><dd>{{ store.status.model.name }}</dd></div>
        </dl>
      </article>

      <!-- Memory status -->
      <article class="panel-card">
        <h4>Memory</h4>
        <dl class="context-list">
          <div>
            <dt>Memory enabled</dt>
            <dd :class="store.status.memory.enabled ? 'panel-flag--enabled' : 'panel-flag--disabled'">
              {{ store.status.memory.enabled ? 'Yes' : 'No' }}
            </dd>
          </div>
          <div>
            <dt>Context loader</dt>
            <dd :class="store.status.memory.contextLoaderEnabled ? 'panel-flag--enabled' : 'panel-flag--disabled'">
              {{ store.status.memory.contextLoaderEnabled ? 'Enabled' : 'Disabled' }}
            </dd>
          </div>
          <div>
            <dt>Auto write</dt>
            <dd class="panel-flag panel-flag--disabled">
              {{ store.status.memory.autoWriteEnabled ? 'Enabled' : 'Disabled' }}
            </dd>
          </div>
          <div>
            <dt>Review queue</dt>
            <dd class="panel-flag panel-flag--disabled">
              {{ store.status.memory.reviewQueueEnabled ? 'Enabled' : 'Disabled' }}
            </dd>
          </div>
        </dl>
      </article>
    </template>
  </section>
</template>
