<script setup lang="ts">
import type { AgentPreviewResult } from '@/types/api/agent'

defineProps<{
  result: AgentPreviewResult
}>()
</script>

<template>
  <section class="preview-result" aria-live="polite">
    <!-- Header -->
    <div class="preview-result__header">
      <span class="panel-badge panel-badge--info">Dry-run only</span>
      <span class="panel-badge panel-badge--safe">{{ result.operation }}</span>
    </div>

    <!-- No-effects list -->
    <article class="panel-card">
      <h4>No Side Effects</h4>
      <ul class="no-effects-list">
        <li v-for="(effect, idx) in result.noEffects" :key="idx">{{ effect }}</li>
      </ul>
    </article>

    <!-- Safety flags -->
    <article class="panel-card">
      <h4>Safety</h4>
      <dl class="context-list">
        <div><dt>Read-only</dt><dd class="panel-flag panel-flag--enabled">{{ result.safety.readOnly ? 'Yes' : 'No' }}</dd></div>
        <div><dt>Side effects</dt><dd class="panel-flag panel-flag--disabled">{{ result.safety.sideEffects ? 'Yes' : 'None' }}</dd></div>
        <div><dt>LLM called</dt><dd class="panel-flag panel-flag--disabled">{{ result.safety.llmCalled ? 'Yes' : 'No' }}</dd></div>
        <div><dt>Tools executed</dt><dd class="panel-flag panel-flag--disabled">{{ result.safety.toolsExecuted ? 'Yes' : 'No' }}</dd></div>
        <div><dt>Session written</dt><dd class="panel-flag panel-flag--disabled">{{ result.safety.sessionWritten ? 'Yes' : 'No' }}</dd></div>
        <div><dt>Memory written</dt><dd class="panel-flag panel-flag--disabled">{{ result.safety.memoryWritten ? 'Yes' : 'No' }}</dd></div>
        <div><dt>Review queued</dt><dd class="panel-flag panel-flag--disabled">{{ result.safety.reviewQueued ? 'Yes' : 'No' }}</dd></div>
      </dl>
    </article>

    <!-- Session -->
    <article class="panel-card">
      <h4>Session</h4>
      <dl class="context-list">
        <div><dt>ID</dt><dd>{{ result.session.sessionId || '(none)' }}</dd></div>
        <div><dt>Exists</dt><dd>{{ result.session.exists ? 'Yes' : 'No' }}</dd></div>
        <div><dt>History included</dt><dd>{{ result.session.historyIncluded ? 'Yes' : 'No' }}</dd></div>
        <div><dt>History messages</dt><dd>{{ result.session.historyMessageCount }}</dd></div>
        <div v-if="result.session.historyTruncated"><dt>Truncated</dt><dd>Yes</dd></div>
      </dl>
    </article>

    <!-- Model -->
    <article class="panel-card">
      <h4>Model</h4>
      <dl class="context-list">
        <div><dt>Name</dt><dd>{{ result.model.name || '(default)' }}</dd></div>
        <div><dt>Provider</dt><dd>{{ result.model.provider || '(default)' }}</dd></div>
        <div v-if="result.model.temperature != null"><dt>Temperature</dt><dd>{{ result.model.temperature }}</dd></div>
        <div v-if="result.model.maxOutputTokens != null"><dt>Max tokens</dt><dd>{{ result.model.maxOutputTokens }}</dd></div>
      </dl>
    </article>

    <!-- Prompt metadata -->
    <article class="panel-card">
      <h4>Prompt</h4>
      <dl class="context-list">
        <div><dt>Sections</dt><dd>{{ result.prompt.sectionCount }}</dd></div>
        <div><dt>Characters</dt><dd>{{ result.prompt.characterCount }}</dd></div>
      </dl>
      <details class="section-details">
        <summary>Section breakdown</summary>
        <dl class="context-list">
          <div v-for="section in result.prompt.sections" :key="section.type">
            <dt>{{ section.type }}</dt>
            <dd>
              <span v-if="section.included">{{ section.characterCount }} chars</span>
              <span v-else class="panel-flag panel-flag--disabled">Not included</span>
              <span v-if="section.messageCount != null"> ({{ section.messageCount }} msgs)</span>
            </dd>
          </div>
        </dl>
      </details>
    </article>

    <!-- Memory context -->
    <article v-if="result.memoryContext.enabled" class="panel-card">
      <h4>Memory Context</h4>
      <dl class="context-list">
        <div><dt>Categories</dt><dd>{{ result.memoryContext.categoryCount }}</dd></div>
        <div><dt>Memories</dt><dd>{{ result.memoryContext.memoryCount }}</dd></div>
      </dl>
      <ul v-if="result.memoryContext.items.length" class="memory-items-list">
        <li v-for="item in result.memoryContext.items" :key="item.memoryId">
          <strong>{{ item.memoryId }}</strong> — {{ item.title }}
          <span class="memory-score">score: {{ item.score }}</span>
          <p v-if="item.summaryPreview" class="memory-summary">{{ item.summaryPreview }}</p>
        </li>
      </ul>
    </article>

    <!-- Capabilities -->
    <article class="panel-card">
      <h4>Capabilities</h4>
      <dl class="context-list">
        <div>
          <dt>LLM call</dt>
          <dd>
            <span v-if="result.capabilities.llmCallForcedDisabled" class="panel-flag panel-flag--disabled">Forced disabled</span>
          </dd>
        </div>
        <div>
          <dt>Streaming</dt>
          <dd>
            <span v-if="result.capabilities.streamingRequested" class="panel-flag panel-flag--disabled">Requested → </span>
            <span class="panel-flag panel-flag--disabled">{{ result.capabilities.streamingForcedDisabled ? 'Forced disabled' : 'Unavailable' }}</span>
          </dd>
        </div>
        <div>
          <dt>Tools</dt>
          <dd>
            <span v-if="result.capabilities.toolsRequested" class="panel-flag panel-flag--disabled">Requested → </span>
            <span class="panel-flag panel-flag--disabled">{{ result.capabilities.toolExecutionForcedDisabled ? 'Forced disabled' : 'Unavailable' }}</span>
          </dd>
        </div>
        <div>
          <dt>Auto-memory</dt>
          <dd>
            <span v-if="result.capabilities.autoMemoryRequested" class="panel-flag panel-flag--disabled">Requested → </span>
            <span class="panel-flag panel-flag--disabled">{{ result.capabilities.memoryWriteForcedDisabled ? 'Forced disabled' : 'Unavailable' }}</span>
          </dd>
        </div>
        <div><dt>Session write</dt><dd class="panel-flag panel-flag--disabled">Unavailable</dd></div>
        <div><dt>Review queue</dt><dd class="panel-flag panel-flag--disabled">Unavailable</dd></div>
      </dl>
    </article>

    <!-- Checks -->
    <article class="panel-card">
      <h4>Checks</h4>
      <ul class="checks-list">
        <li v-for="check in result.checks" :key="check.code" class="check-item check-item--pass">
          <span class="check-icon">✓</span>
          {{ check.message }}
        </li>
      </ul>
    </article>

    <!-- Warnings -->
    <article v-if="result.warnings.length" class="panel-card">
      <h4>Warnings</h4>
      <ul class="warnings-list">
        <li v-for="(warning, idx) in result.warnings" :key="idx">{{ warning }}</li>
      </ul>
    </article>

    <!-- User message preview (for prompt preview only) -->
    <article v-if="result.userMessagePreview" class="panel-card">
      <h4>User Message Preview</h4>
      <p class="preview-text">{{ result.userMessagePreview }}</p>
    </article>
  </section>
</template>

<style scoped>
.preview-result__header {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: center;
  margin-bottom: var(--space-3, 12px);
}

.panel-badge--info {
  background: var(--color-badge-bg, rgba(59, 130, 246, 0.15));
  color: var(--color-badge-text, #3b82f6);
}

.panel-badge--safe {
  background: var(--color-success-bg, rgba(34, 197, 94, 0.15));
  color: var(--color-success-text, #22c55e);
}

.no-effects-list,
.checks-list,
.warnings-list,
.memory-items-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.no-effects-list li,
.checks-list li,
.warnings-list li {
  padding: var(--space-1, 4px) 0;
  border-bottom: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
}

.no-effects-list li:last-child,
.checks-list li:last-child,
.warnings-list li:last-child {
  border-bottom: none;
}

.check-item {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}

.check-icon {
  font-weight: bold;
  color: var(--color-success-text, #22c55e);
}

.memory-items-list li {
  padding: var(--space-2, 8px) 0;
  border-bottom: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
}

.memory-score {
  font-size: 0.75rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
  margin-left: var(--space-2, 8px);
}

.memory-summary {
  font-size: 0.75rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
  margin: var(--space-1, 4px) 0 0;
}

.section-details {
  margin-top: var(--space-2, 8px);
}

.section-details summary {
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
}

.preview-text {
  font-size: 0.8125rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 6rem;
  overflow-y: auto;
}

.warnings-list li {
  color: var(--color-warning-text, #f59e0b);
}
</style>
