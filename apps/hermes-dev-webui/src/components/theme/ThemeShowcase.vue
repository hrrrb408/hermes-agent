<script setup lang="ts">
import { ref, computed } from 'vue'
import { Settings, Copy } from '@lucide/vue'
import { useThemeStore } from '@/stores/theme'

const store = useThemeStore()

const activeTab = ref<'files' | 'memory' | 'context' | 'agent'>('files')
const expandedTool = ref<string | null>(null)

function toggleTool(toolId: string): void {
  expandedTool.value = expandedTool.value === toolId ? null : toolId
}

const tabs = [
  { id: 'files' as const, label: 'Files' },
  { id: 'memory' as const, label: 'Memory' },
  { id: 'context' as const, label: 'Context' },
  { id: 'agent' as const, label: 'Agent' },
]

/** Theme Signature - debug info showing current theme's structural properties */
const themeSignature = computed(() => {
  const t = store.activeTheme
  return [
    { key: 'surfaceTexture', value: t.surfaceTexture },
    { key: 'ornamentStyle', value: t.ornamentStyle },
    { key: 'dividerStyle', value: t.dividerStyle },
    { key: 'headingStyle', value: t.headingStyle },
    { key: 'density', value: t.density },
    { key: 'messageStyle', value: t.messageStyle },
    { key: 'toolCardStyle', value: t.toolCardStyle },
    { key: 'panelStyle', value: t.panelStyle },
  ]
})
</script>

<template>
  <div class="showcase">
    <!-- Theme Signature -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Theme Signature</h2>
      <div class="signature">
        <span
          v-for="item in themeSignature"
          :key="item.key"
          class="signature__item"
        >
          <span class="signature__key">{{ item.key }}</span>
          <span class="signature__value">{{ item.value }}</span>
        </span>
      </div>
      <div class="showcase__divider" aria-hidden="true"></div>
    </section>

    <!-- Background & Panels -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Background & Panels</h2>
      <div class="showcase__grid-3">
        <div class="showcase__panel theme-panel">
          <span class="showcase__panel-label">Panel</span>
        </div>
        <div class="showcase__panel theme-panel theme-panel--elevated">
          <span class="showcase__panel-label">Elevated</span>
        </div>
        <div class="showcase__panel theme-panel theme-panel--hover">
          <span class="showcase__panel-label">Hover</span>
        </div>
      </div>
      <div class="showcase__divider" aria-hidden="true"></div>
    </section>

    <!-- Typography -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Typography</h2>
      <div class="showcase__type-stack">
        <h1>Heading One - Primary Title</h1>
        <h2>Heading Two - Section Title</h2>
        <h3>Heading Three - Subsection</h3>
        <p class="showcase__body">
          Body text for reading. This demonstrates the default paragraph style used for
          assistant replies, status messages, and general UI content across the workbench.
        </p>
        <p class="showcase__body-reading">
          Reading text uses the reading font. 适用于中英文混排场景，
          showing how font stacks handle CJK characters alongside Latin text.
        </p>
        <p class="showcase__text-secondary">Secondary text for metadata and labels</p>
        <p class="showcase__text-muted">Muted text for timestamps and hints</p>
        <p class="showcase__text-code"><code>code inline: memory_context.load()</code></p>
        <p class="showcase__text-numbers">42 sessions &middot; 1.2k tokens &middot; 0.92 relevance</p>
      </div>
    </section>

    <!-- Buttons -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Buttons</h2>
      <div class="showcase__button-row">
        <button class="btn btn--primary">Primary</button>
        <button class="btn btn--secondary">Secondary</button>
        <button class="btn btn--ghost">Ghost</button>
        <button class="btn btn--danger">Danger</button>
        <button class="btn btn--icon" aria-label="Settings icon">
          <Settings :size="16" />
        </button>
        <button class="btn btn--primary" disabled>Disabled</button>
      </div>
    </section>

    <!-- Form Elements -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Form Elements</h2>
      <div class="showcase__form-stack">
        <div class="form-field">
          <label class="form-field__label">Label</label>
          <input class="form-field__input" type="text" placeholder="Search sessions..." />
        </div>
        <div class="form-field">
          <label class="form-field__label">Input with focus</label>
          <input class="form-field__input" type="text" value="Focused input state" />
        </div>
        <div class="form-field form-field--error">
          <label class="form-field__label">Error state</label>
          <input class="form-field__input" type="text" value="Invalid input" />
          <span class="form-field__error">This field is required</span>
        </div>
        <div class="form-field">
          <label class="form-field__label">Disabled</label>
          <input class="form-field__input" type="text" disabled placeholder="Not available" />
        </div>
        <div class="form-field">
          <label class="form-field__label">Textarea</label>
          <textarea class="form-field__input form-field__textarea" placeholder="Multi-line input..."></textarea>
        </div>
      </div>
    </section>

    <!-- Tabs -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Tabs</h2>
      <div class="tabs" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tabs__item"
          :class="{ 'tabs__item--active': activeTab === tab.id }"
          role="tab"
          :aria-selected="activeTab === tab.id"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
    </section>

    <!-- User Message -->
    <section class="showcase__section">
      <h2 class="showcase__heading">User Message</h2>
      <div class="message message--user">
        <div class="message__content">
          <p>请检查当前 Hermes 分层记忆系统的状态，并告诉我下一步应该优先开发什么。</p>
        </div>
        <span class="message__time">14:32</span>
      </div>
    </section>

    <!-- Assistant Message -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Assistant Message</h2>
      <div class="message message--assistant">
        <div class="message__content assistant-content">
          <h3>Memory Context Loader</h3>
          <p>
            The Memory Context Loader scans hierarchical memory categories and injects
            relevant context into the agent's system prompt before each response cycle.
          </p>
          <ol>
            <li>Query category indexes for matched keywords</li>
            <li>Rank results by relevance score</li>
            <li>Inject top-K memories into context window</li>
          </ol>
          <p>Current status: <strong>active</strong>. Next steps:</p>
          <ul>
            <li>Implement review queue approval flow</li>
            <li>Add truncation safeguards for long context</li>
          </ul>
          <blockquote>
            <p>Memory records should be self-contained summaries that remain useful
            even when the original conversation context is no longer available.</p>
          </blockquote>
          <p>See <code>agent/runtime_memory_writer.py</code> for the decision logic, and
          <code>agent/memory_review_queue.py</code> for storage management.</p>
        </div>
      </div>
    </section>

    <!-- Code Block -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Code Block</h2>
      <div class="code-block">
        <div class="code-block__header">
          <span class="code-block__filename">memory_loader.py</span>
          <button class="code-block__copy" aria-label="Copy code"><Copy :size="12" /> Copy</button>
        </div>
        <pre class="code-block__body"><code>def load_context(
    categories: list[str],
    query: str,
    top_k: int = 5,
) -> list[MemoryRecord]:
    """Load relevant memories for the given query."""
    results: list[MemoryRecord] = []
    for category in categories:
        index = load_index(category)
        hits = index.search(query, top_k=top_k)
        results.extend(hits)
    return sorted(results, key=lambda r: r.score, reverse=True)</code></pre>
      </div>
    </section>

    <!-- Tool Call Cards -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Tool Call Cards</h2>
      <div class="showcase__tool-cards">
        <!-- Running -->
        <div class="tool-card tool-card--running" @click="toggleTool('running')">
          <div class="tool-card__header">
            <span class="tool-card__status-dot"></span>
            <span class="tool-card__name">memory-context</span>
            <span class="tool-card__time">2.1s</span>
          </div>
          <div class="tool-card__params">categories: ["hermes"], query: "dev status"</div>
          <div v-if="expandedTool === 'running'" class="tool-card__output">
            Loading 3 memories from category "hermes"...
          </div>
        </div>

        <!-- Success -->
        <div class="tool-card tool-card--success" @click="toggleTool('success')">
          <div class="tool-card__header">
            <span class="tool-card__status-dot"></span>
            <span class="tool-card__name">read_file</span>
            <span class="tool-card__time">0.4s</span>
          </div>
          <div class="tool-card__params">path: "agent/runtime_memory_writer.py"</div>
          <div v-if="expandedTool === 'success'" class="tool-card__output">
            File loaded successfully. 248 lines, 9 functions found.
          </div>
        </div>

        <!-- Error -->
        <div class="tool-card tool-card--error" @click="toggleTool('error')">
          <div class="tool-card__header">
            <span class="tool-card__status-dot"></span>
            <span class="tool-card__name">dev-check</span>
            <span class="tool-card__time">1.8s</span>
          </div>
          <div class="tool-card__params">check: "gateway-status"</div>
          <div v-if="expandedTool === 'error'" class="tool-card__output">
            Error: Gateway process not found. Is the dev gateway running?
          </div>
        </div>
      </div>
    </section>

    <!-- Memory Entry -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Memory Entry</h2>
      <div class="memory-entry">
        <div class="memory-entry__header">
          <span class="memory-entry__category">hermes</span>
          <span class="memory-entry__id">MEM-HERMES-002</span>
          <span class="status-badge status-badge--active">Active</span>
        </div>
        <p class="memory-entry__summary">
          Hermes supports dynamic hierarchical memory routing and Runtime Context injection
          for conversation-aware memory retrieval.
        </p>
        <div class="memory-entry__meta">
          <span>Relevance: 0.92</span>
        </div>
      </div>
      <div class="memory-entry memory-entry--archived">
        <div class="memory-entry__header">
          <span class="memory-entry__category">hermes</span>
          <span class="memory-entry__id">MEM-HERMES-001</span>
          <span class="status-badge status-badge--archived">Archived</span>
        </div>
        <p class="memory-entry__summary">
          Initial memory system design notes. Superseded by MEM-HERMES-002.
        </p>
        <div class="memory-entry__meta">
          <span>Skipped: archived</span>
        </div>
      </div>
    </section>

    <!-- Context Summary -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Context Summary</h2>
      <div class="context-summary">
        <div class="context-summary__row">
          <span class="context-summary__label">Runtime Memory Injection</span>
          <span class="status-badge status-badge--active">Enabled</span>
        </div>
        <div class="context-summary__row">
          <span class="context-summary__label">Matched Categories</span>
          <span class="context-summary__value">1</span>
        </div>
        <div class="context-summary__row">
          <span class="context-summary__label">Loaded Memories</span>
          <span class="context-summary__value">2</span>
        </div>
        <div class="context-summary__row">
          <span class="context-summary__label">Skipped Archived</span>
          <span class="context-summary__value">1</span>
        </div>
        <div class="context-summary__row">
          <span class="context-summary__label">Truncated</span>
          <span class="context-summary__value">No</span>
        </div>
      </div>
    </section>

    <!-- Status Badges -->
    <section class="showcase__section">
      <h2 class="showcase__heading">Status Badges</h2>
      <div class="showcase__badge-row">
        <span class="status-badge status-badge--success">Success</span>
        <span class="status-badge status-badge--warning">Warning</span>
        <span class="status-badge status-badge--error">Error</span>
        <span class="status-badge status-badge--neutral">Neutral</span>
        <span class="status-badge status-badge--running">Running</span>
        <span class="status-badge status-badge--active">Active</span>
        <span class="status-badge status-badge--archived">Archived</span>
        <span class="status-badge status-badge--dev">Development</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.showcase {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  position: relative;
  z-index: 1;
}

.showcase__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.showcase__heading {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Signature */
.signature {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.signature__item {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-neutral-soft);
  font-family: var(--font-code);
  font-size: var(--font-size-xs);
}

.signature__key {
  color: var(--color-text-muted);
}

.signature__value {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

/* Panels */
.showcase__grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.showcase__panel {
  padding: var(--space-4);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
}

.showcase__panel--elevated {
  background: var(--color-elevated-bg);
}

.showcase__panel--hover {
  background: var(--color-hover-bg);
  border-color: var(--color-border-strong);
}

.showcase__panel-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.showcase__divider {
  height: 1px;
  background: var(--color-divider);
  margin-top: var(--space-2);
}

/* Typography */
.showcase__type-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.showcase__body {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  line-height: var(--content-line-height);
  max-width: var(--content-max-width);
}

.showcase__body-reading {
  font-family: var(--font-reading);
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  line-height: var(--content-line-height);
  max-width: var(--content-max-width);
}

.showcase__text-secondary {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.showcase__text-muted {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.showcase__text-code {
  font-family: var(--font-code);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.showcase__text-numbers {
  font-family: var(--font-code);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

/* Buttons */
.showcase__button-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-md);
  transition:
    background var(--transition-fast),
    color var(--transition-fast),
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.btn--primary {
  background: var(--color-accent);
  color: var(--color-text-inverse);
}

.btn--primary:hover {
  background: var(--color-accent-hover);
}

.btn--secondary {
  border: var(--border-width) solid var(--color-border);
  background: var(--color-panel-bg);
  color: var(--color-text-primary);
}

.btn--secondary:hover {
  border-color: var(--color-border-strong);
  background: var(--color-hover-bg);
}

.btn--ghost {
  background: transparent;
  color: var(--color-accent);
}

.btn--ghost:hover {
  background: var(--color-accent-soft);
}

.btn--danger {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

.btn--danger:hover {
  background: var(--color-error);
  filter: brightness(1.1);
}

.btn--icon {
  width: 32px;
  height: 32px;
  padding: 0;
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
  color: var(--color-text-secondary);
}

.btn--icon:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Form */
.showcase__form-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 400px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-field__label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.form-field__input {
  padding: var(--space-1) var(--space-2);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-app-bg);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: border-color var(--transition-fast);
}

.form-field__input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus);
}

.form-field__input::placeholder {
  color: var(--color-text-muted);
}

.form-field__input:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.form-field__textarea {
  min-height: 60px;
  resize: vertical;
}

.form-field--error .form-field__input {
  border-color: var(--color-error);
}

.form-field__error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  border-bottom: var(--border-width) solid var(--color-border);
}

.tabs__item {
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  border-bottom: 2px solid transparent;
  transition:
    color var(--transition-fast),
    border-color var(--transition-fast);
}

.tabs__item:hover {
  color: var(--color-text-primary);
  background: var(--color-hover-bg);
}

.tabs__item--active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

/* Messages */
.message {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-width: var(--content-max-width);
}

.message--user {
  align-self: flex-end;
  padding: var(--space-2) var(--space-3);
  background: var(--color-user-message-bg);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg);
}

.message--user .message__content {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
}

.message--user .message__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-align: right;
}

.message--assistant {
  padding: var(--space-3) var(--space-4);
  background: var(--color-assistant-message-bg);
  border-radius: var(--radius-md);
}

/* Assistant content */
.assistant-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  font-family: var(--font-reading);
  line-height: var(--content-line-height);
}

.assistant-content h3 {
  margin-top: var(--space-2);
  font-family: var(--font-ui);
}

.assistant-content ul,
.assistant-content ol {
  padding-left: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.assistant-content li {
  list-style-position: outside;
}

.assistant-content blockquote {
  margin: var(--space-2) 0;
  padding: var(--space-2) var(--space-3);
  border-inline-start: 2px solid var(--color-accent);
  background: var(--color-accent-soft);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.assistant-content blockquote p {
  font-style: italic;
  color: var(--color-text-secondary);
}

/* Code block */
.code-block {
  border: var(--border-width) solid var(--color-code-border);
  border-radius: var(--radius-md);
  background: var(--color-code-bg);
  overflow: hidden;
}

.code-block__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-bottom: var(--border-width) solid var(--color-code-border);
}

.code-block__filename {
  font-family: var(--font-code);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.code-block__copy {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
}

.code-block__copy:hover {
  background: var(--color-hover-bg);
  color: var(--color-text-primary);
}

.code-block__body {
  padding: var(--space-3);
  overflow-x: auto;
}

.code-block__body code {
  font-family: var(--font-code);
  font-size: var(--font-size-sm);
  color: var(--color-code-text);
  background: none;
  border: none;
  padding: 0;
  line-height: 1.5;
}

/* Tool cards */
.showcase__tool-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 500px;
}

.tool-card {
  padding: var(--space-2) var(--space-3);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
  cursor: pointer;
  transition: border-color var(--transition-fast);
}

.tool-card:hover {
  border-color: var(--color-border-strong);
}

.tool-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.tool-card__status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tool-card--running .tool-card__status-dot {
  background: var(--color-tool-running);
  animation: pulse 1.5s ease-in-out infinite;
}

.tool-card--success .tool-card__status-dot {
  background: var(--color-tool-success);
}

.tool-card--error .tool-card__status-dot {
  background: var(--color-tool-error);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.tool-card__name {
  font-family: var(--font-code);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  flex: 1;
}

.tool-card__time {
  font-family: var(--font-code);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.tool-card__params {
  font-family: var(--font-code);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: var(--space-1);
}

.tool-card__output {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: var(--border-width) solid var(--color-divider);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Memory entry */
.memory-entry {
  padding: var(--space-3);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
  margin-bottom: var(--space-2);
}

.memory-entry--archived {
  opacity: 0.5;
}

.memory-entry__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.memory-entry__category {
  font-family: var(--font-code);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  background: var(--color-accent-soft);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.memory-entry__id {
  font-family: var(--font-code);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.memory-entry__summary {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: var(--content-line-height);
}

.memory-entry__meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

/* Context summary */
.context-summary {
  padding: var(--space-3);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel-bg);
  max-width: 400px;
}

.context-summary__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-1) 0;
}

.context-summary__row:not(:last-child) {
  border-bottom: 1px solid var(--color-divider);
}

.context-summary__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.context-summary__value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

/* Status badges */
.showcase__badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.status-badge--success {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.status-badge--warning {
  color: var(--color-warning);
  background: var(--color-warning-soft);
}

.status-badge--error {
  color: var(--color-error);
  background: var(--color-error-soft);
}

.status-badge--neutral {
  color: var(--color-neutral);
  background: var(--color-neutral-soft);
}

.status-badge--running {
  color: var(--color-warning);
  background: var(--color-warning-soft);
}

.status-badge--active {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.status-badge--archived {
  color: var(--color-text-muted);
  background: var(--color-neutral-soft);
}

.status-badge--dev {
  color: var(--color-accent);
  background: var(--color-accent-soft);
}
</style>
