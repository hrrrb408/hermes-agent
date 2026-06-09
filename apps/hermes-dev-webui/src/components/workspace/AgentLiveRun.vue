<script setup lang="ts">
import { useAgentRunStore } from '@/stores/agentRun'

const store = useAgentRunStore()
</script>

<template>
  <section class="live-run" aria-label="Live Agent Run">
    <!-- Kill Switch Disabled Banner -->
    <div v-if="!store.killSwitchEnabled && store.creationState === 'idle'" class="run-banner run-banner--disabled" role="status">
      <span class="run-banner__icon">⚠</span>
      <span>Agent execution is disabled. Set <code>HERMES_AGENT_RUN_ENABLED=true</code> to enable.</span>
    </div>

    <!-- Safety Badges -->
    <div class="run-badges" aria-label="Safety information">
      <span class="run-badge run-badge--info">Dev-only</span>
      <span class="run-badge run-badge--disabled">Tools: Off</span>
      <span class="run-badge run-badge--disabled">Auto Memory: Off</span>
      <span class="run-badge run-badge--info">Streaming: On</span>
    </div>

    <!-- Form (visible when idle or error) -->
    <form
      v-if="store.canCreate && !store.isTerminal"
      class="run-form"
      @submit.prevent="store.createRun()"
    >
      <div class="form-group">
        <label for="lr-session-id">Session ID <span class="form-required">*</span></label>
        <input
          id="lr-session-id"
          v-model="store.form.sessionId"
          type="text"
          class="form-input"
          maxlength="200"
          placeholder="Enter existing session ID"
          required
        />
      </div>

      <div class="form-group">
        <label for="lr-message">Message <span class="form-required">*</span></label>
        <textarea
          id="lr-message"
          v-model="store.form.message"
          class="form-textarea"
          rows="3"
          maxlength="4000"
          placeholder="Enter message for agent (1-4000 characters)"
          required
        ></textarea>
      </div>

      <div class="form-row">
        <div class="form-group form-group--small">
          <label for="lr-model">Model Override</label>
          <input id="lr-model" v-model="store.form.modelOverride" type="text" class="form-input" placeholder="Default" maxlength="100" />
        </div>
        <div class="form-group form-group--small">
          <label for="lr-temp">Temperature</label>
          <input id="lr-temp" v-model.number="store.form.temperature" type="number" class="form-input" min="0" max="2" step="0.1" placeholder="0.0–2.0" />
        </div>
        <div class="form-group form-group--small">
          <label for="lr-tokens">Max Output Tokens</label>
          <input id="lr-tokens" v-model.number="store.form.maxOutputTokens" type="number" class="form-input" min="1" max="4096" placeholder="≤ 4096" />
        </div>
      </div>

      <!-- Confirmation Section -->
      <fieldset class="run-confirmation">
        <legend>Confirmation Required</legend>

        <label class="form-toggle">
          <input v-model="store.form.dryRunPreviewed" type="checkbox" />
          <span>I have previewed the run (Dry Run)</span>
        </label>

        <label class="form-toggle">
          <input v-model="store.form.acknowledgedCallLlm" type="checkbox" />
          <span>I understand this will call the LLM (costs tokens)</span>
        </label>

        <label class="form-toggle">
          <input v-model="store.form.acknowledgedWriteSession" type="checkbox" />
          <span>I understand this will write to the session database</span>
        </label>

        <div class="form-group">
          <label for="lr-confirm">Type <code>RUN</code> to execute</label>
          <input
            id="lr-confirm"
            v-model="store.form.confirmationText"
            type="text"
            class="form-input"
            placeholder="RUN"
            autocomplete="off"
            spellcheck="false"
          />
        </div>
      </fieldset>

      <!-- Creation Error -->
      <div v-if="store.creationError" class="run-error" role="alert">
        {{ store.creationError }}
      </div>

      <!-- Create Button -->
      <div class="form-actions">
        <button
          type="submit"
          class="run-btn run-btn--primary"
          :disabled="store.isCreating || !store.killSwitchEnabled"
        >
          {{ store.isCreating ? 'Creating…' : 'Create Run' }}
        </button>
        <button type="button" class="run-btn run-btn--secondary" @click="store.reset()">Reset</button>
      </div>
    </form>

    <!-- Running / Terminal State -->
    <div v-if="store.runId" class="run-status">
      <!-- Run Info Header -->
      <div class="run-header">
        <div class="run-header__left">
          <span class="run-status-badge" :class="`run-status-badge--${(store.status || 'unknown').toLowerCase()}`">
            {{ store.status || 'Unknown' }}
          </span>
          <span v-if="store.model" class="run-model">{{ store.model.name }} ({{ store.model.provider }})</span>
        </div>
        <span class="run-id" title="Run ID">{{ store.runId }}</span>
      </div>

      <!-- Connection Status -->
      <div class="run-connection" role="status">
        <span class="run-connection__dot" :class="`run-connection__dot--${store.connectionStatus}`"></span>
        <span>{{ store.connectionStatus }}</span>
      </div>

      <!-- Stream Error -->
      <div v-if="store.streamError" class="run-error" role="alert">
        {{ store.streamError }}
        <button v-if="!store.isTerminal" type="button" class="run-btn run-btn--small" @click="store.reconnect()">Reconnect</button>
      </div>

      <!-- Stream Text -->
      <div
        v-if="store.streamText"
        class="run-stream"
        aria-live="polite"
        :aria-busy="store.isRunning"
      >
        <pre class="run-stream__text">{{ store.streamText }}</pre>
      </div>

      <!-- Empty state while running -->
      <div v-else-if="store.isRunning" class="run-stream run-stream--empty" aria-busy="true">
        <span class="run-stream__waiting">Waiting for response…</span>
      </div>

      <!-- Usage -->
      <div v-if="store.usage" class="run-usage" aria-label="Token usage">
        <span v-if="store.usage.inputTokens != null" class="run-usage__item">In: {{ store.usage.inputTokens }}</span>
        <span v-if="store.usage.outputTokens != null" class="run-usage__item">Out: {{ store.usage.outputTokens }}</span>
        <span v-if="store.usage.totalTokens != null" class="run-usage__item">Total: {{ store.usage.totalTokens }}</span>
      </div>

      <!-- Error -->
      <div v-if="store.error" class="run-error" role="alert">
        Error: {{ store.error }}
      </div>

      <!-- Action Buttons -->
      <div class="run-actions">
        <button
          v-if="store.canCancel"
          type="button"
          class="run-btn run-btn--danger"
          :disabled="store.isCancelling"
          @click="store.cancelRun()"
        >
          {{ store.isCancelling ? 'Cancelling…' : 'Cancel Run' }}
        </button>
        <button
          v-if="store.isTerminal"
          type="button"
          class="run-btn run-btn--secondary"
          @click="store.reset()"
        >
          New Run
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.live-run {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

/* ── Banner ── */

.run-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.8125rem;
}

.run-banner--disabled {
  background: var(--color-warning-bg, rgba(234, 179, 8, 0.1));
  border: 1px solid var(--color-warning-border, rgba(234, 179, 8, 0.3));
  color: var(--color-warning-text, #ca8a04);
}

.run-banner code {
  font-family: monospace;
  font-size: 0.75rem;
  background: var(--color-code-bg, rgba(255, 255, 255, 0.08));
  padding: 1px 4px;
  border-radius: 2px;
}

/* ── Badges ── */

.run-badges {
  display: flex;
  gap: var(--space-1, 4px);
  flex-wrap: wrap;
}

.run-badge {
  padding: 2px var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.run-badge--info {
  background: var(--color-badge-info-bg, rgba(59, 130, 246, 0.15));
  color: var(--color-badge-info-text, #60a5fa);
}

.run-badge--disabled {
  background: var(--color-badge-disabled-bg, rgba(255, 255, 255, 0.05));
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.4));
}

/* ── Form ── */

.run-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.form-group--small {
  flex: 1;
}

.form-group label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
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

.form-textarea {
  resize: vertical;
  min-height: 3rem;
}

.form-row {
  display: flex;
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

.form-actions {
  display: flex;
  gap: var(--space-2, 8px);
  margin-top: var(--space-1, 4px);
}

/* ── Confirmation ── */

.run-confirmation {
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.run-confirmation legend {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.6));
  padding: 0 var(--space-1, 4px);
}

/* ── Buttons ── */

.run-btn {
  padding: var(--space-1, 4px) var(--space-3, 12px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.8125rem;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 0.15s;
}

.run-btn:focus-visible {
  outline: 2px solid var(--color-focus, #3b82f6);
  outline-offset: 2px;
}

.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.run-btn--primary {
  background: var(--color-accent, #3b82f6);
  color: white;
  border-color: var(--color-accent, #3b82f6);
}

.run-btn--primary:hover:not(:disabled) {
  opacity: 0.9;
}

.run-btn--secondary {
  background: transparent;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
  border-color: var(--color-border, rgba(255, 255, 255, 0.12));
}

.run-btn--secondary:hover {
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
  border-color: var(--color-text-secondary, rgba(255, 255, 255, 0.3));
}

.run-btn--danger {
  background: var(--color-error-bg, rgba(239, 68, 68, 0.15));
  color: var(--color-error-text, #ef4444);
  border-color: var(--color-error-border, rgba(239, 68, 68, 0.3));
}

.run-btn--danger:hover:not(:disabled) {
  background: var(--color-error-bg, rgba(239, 68, 68, 0.25));
}

.run-btn--small {
  padding: 2px var(--space-2, 8px);
  font-size: 0.75rem;
}

/* ── Run Status ── */

.run-status {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}

.run-header__left {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}

.run-status-badge {
  padding: 2px var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.run-status-badge--created,
.run-status-badge--starting {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.run-status-badge--running {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.run-status-badge--cancelling {
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
}

.run-status-badge--completed {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.run-status-badge--cancelled {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.5);
}

.run-status-badge--failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.run-model {
  font-size: 0.75rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
}

.run-id {
  font-size: 0.6875rem;
  font-family: monospace;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.3));
}

/* ── Connection ── */

.run-connection {
  display: flex;
  align-items: center;
  gap: var(--space-1, 4px);
  font-size: 0.6875rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.4));
}

.run-connection__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-secondary, rgba(255, 255, 255, 0.3));
}

.run-connection__dot--connected {
  background: #22c55e;
}

.run-connection__dot--connecting,
.run-connection__dot--reconnecting {
  background: #facc15;
  animation: pulse 1.5s ease-in-out infinite;
}

.run-connection__dot--error {
  background: #ef4444;
}

.run-connection__dot--disconnected {
  background: rgba(255, 255, 255, 0.2);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── Stream ── */

.run-stream {
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-input-bg, rgba(255, 255, 255, 0.03));
  max-height: 400px;
  overflow-y: auto;
}

.run-stream--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
}

.run-stream__waiting {
  font-size: 0.8125rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.4));
}

.run-stream__text {
  margin: 0;
  font-family: inherit;
  font-size: 0.8125rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-text-primary, rgba(255, 255, 255, 0.9));
}

/* ── Usage ── */

.run-usage {
  display: flex;
  gap: var(--space-3, 12px);
  font-size: 0.75rem;
  color: var(--color-text-secondary, rgba(255, 255, 255, 0.5));
}

.run-usage__item {
  font-family: monospace;
}

/* ── Error ── */

.run-error {
  padding: var(--space-2, 8px);
  background: var(--color-error-bg, rgba(239, 68, 68, 0.1));
  border: 1px solid var(--color-error-border, rgba(239, 68, 68, 0.2));
  border-radius: var(--radius-sm, 4px);
  color: var(--color-error-text, #ef4444);
  font-size: 0.8125rem;
}

/* ── Actions ── */

.run-actions {
  display: flex;
  gap: var(--space-2, 8px);
}
</style>
