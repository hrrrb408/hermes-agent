<script setup lang="ts">
import { computed } from 'vue'
import { useToolExecuteStore } from '@/stores/toolExecute'

const store = useToolExecuteStore()

const dryRunDecision = computed(() => store.dryRunResult?.decision ?? null)
const dryRunRiskTier = computed(() => store.dryRunResult?.riskTier ?? null)
const dryRunDigestShort = computed(() => {
  const d = store.dryRunDecisionDigest
  if (!d) return null
  return d.length > 20 ? `${d.slice(0, 20)}…` : d
})
const canExecute = computed(
  () => store.status === 'confirmation_required' && !store.isExecuteLoading,
)
const canDryRun = computed(
  () => !store.isDryRunLoading && !store.isExecuteLoading,
)

const sideEffectFlags = computed(() => {
  const se = store.sideEffects
  return [
    { key: 'providerSchemaSent', label: 'Provider schema sent', value: se?.providerSchemaSent ?? false },
    { key: 'providerApiCalled', label: 'Provider API called', value: se?.providerApiCalled ?? false },
    { key: 'externalSideEffects', label: 'External side effects', value: se?.externalSideEffects ?? false },
  ]
})

function statusLabel(): string {
  switch (store.status) {
    case 'idle': return 'Idle'
    case 'dry_run_loading': return 'Running dry-run…'
    case 'dry_run_ready': return 'Dry-run ready'
    case 'confirmation_required': return 'Confirmation required'
    case 'execute_loading': return 'Executing…'
    case 'blocked': return 'Blocked (safe)'
    case 'completed': return 'Completed'
    case 'error': return 'Error'
    default: return store.status
  }
}
</script>

<template>
  <section class="workspace-panel__section" aria-label="Tool Execute">
    <div class="panel-header">
      <span class="panel-badge">Dev-only</span>
      <span class="panel-badge panel-badge--muted">Clarify-only</span>
    </div>

    <p class="tool-execute__intro">
      Controlled execution workbench for the single allowlisted tool
      <code>clarify</code>. Default gates block before any handler call.
      Provider schema is never sent and no provider API is ever called.
    </p>

    <!-- Tool -->
    <div class="tool-execute__field">
      <label class="tool-execute__label" for="tool-execute-canonical">Tool</label>
      <input
        id="tool-execute-canonical"
        class="tool-execute__input tool-execute__input--readonly"
        type="text"
        :value="store.canonicalName"
        readonly
        aria-readonly="true"
      />
    </div>

    <!-- Question -->
    <div class="tool-execute__field">
      <label class="tool-execute__label" for="tool-execute-question">Clarify question</label>
      <textarea
        id="tool-execute-question"
        class="tool-execute__textarea"
        rows="2"
        placeholder="Question to present"
        :value="store.question"
        :disabled="store.isDryRunLoading || store.isExecuteLoading"
        @input="store.setQuestion(($event.target as HTMLTextAreaElement).value)"
      ></textarea>
    </div>

    <!-- Choices -->
    <div class="tool-execute__field">
      <label class="tool-execute__label" for="tool-execute-choices">Choices (optional, comma or newline)</label>
      <textarea
        id="tool-execute-choices"
        class="tool-execute__textarea"
        rows="2"
        placeholder="Option A, Option B"
        :value="store.choicesText"
        :disabled="store.isDryRunLoading || store.isExecuteLoading"
        @input="store.setChoicesText(($event.target as HTMLTextAreaElement).value)"
      ></textarea>
    </div>

    <!-- Actions -->
    <div class="tool-execute__actions">
      <button
        id="tool-execute-dry-run"
        type="button"
        class="tool-execute__btn"
        :disabled="!canDryRun"
        @click="store.runDryRun()"
      >
        Dry Run
      </button>
      <button
        id="tool-execute-run"
        type="button"
        class="tool-execute__btn tool-execute__btn--primary"
        :disabled="!canExecute"
        @click="store.runExecute()"
      >
        Confirm &amp; Execute
      </button>
      <button
        type="button"
        class="tool-execute__btn tool-execute__btn--ghost"
        @click="store.reset()"
      >
        Reset
      </button>
    </div>

    <!-- Status line -->
    <p class="tool-execute__status" :data-status="store.status">
      Status: <strong>{{ statusLabel() }}</strong>
    </p>

    <p v-if="store.error" class="tool-execute__error" role="alert">
      {{ store.error }}
    </p>

    <!-- Dry-run result -->
    <div v-if="store.dryRunResult" class="tool-execute__block" aria-live="polite">
      <h4 class="tool-execute__heading">Dry-run decision</h4>
      <dl class="tool-execute__dl">
        <div><dt>Decision</dt><dd>{{ dryRunDecision }}</dd></div>
        <div><dt>Risk tier</dt><dd>{{ dryRunRiskTier ?? '—' }}</dd></div>
        <div><dt>Digest (short)</dt><dd>{{ dryRunDigestShort ?? '—' }}</dd></div>
        <div><dt>Confirmation token ID</dt><dd>{{ store.confirmationTokenId ?? '—' }}</dd></div>
        <div><dt>Token expires</dt><dd>{{ store.confirmationTokenExpiresAt ?? '—' }}</dd></div>
      </dl>
    </div>

    <!-- Execute result -->
    <div v-if="store.executeResult" class="tool-execute__block" aria-live="polite">
      <h4 class="tool-execute__heading">Execute result</h4>
      <dl class="tool-execute__dl">
        <div><dt>Decision</dt><dd>{{ store.executeDecision }}</dd></div>
        <div v-if="store.executeResult.handlerCallId">
          <dt>Handler call ID</dt><dd>{{ store.executeResult.handlerCallId }}</dd>
        </div>
        <div v-if="store.executeResult.postExecutionAuditId">
          <dt>Post-execution audit ID</dt>
          <dd id="tool-execute-post-audit-id">{{ store.executeResult.postExecutionAuditId }}</dd>
        </div>
        <div v-if="store.executeResult.executionStatus">
          <dt>Execution status</dt><dd>{{ store.executeResult.executionStatus }}</dd>
        </div>
      </dl>

      <!-- Side-effect flags -->
      <ul id="tool-execute-side-effects" class="tool-execute__flags">
        <li v-for="flag in sideEffectFlags" :key="flag.key">
          <span class="tool-execute__flag-label">{{ flag.label }}:</span>
          <span
            class="tool-execute__flag-value"
            :class="{ 'tool-execute__flag-value--false': !flag.value }"
          >{{ flag.value }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.tool-execute__intro {
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-secondary, #a0a0aa);
  margin: 0 0 var(--space-3, 12px);
  line-height: 1.5;
}

.tool-execute__intro code {
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.06));
  padding: 0 4px;
  border-radius: 3px;
}

.tool-execute__field {
  margin-bottom: var(--space-2, 8px);
}

.tool-execute__label {
  display: block;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  margin-bottom: 2px;
}

.tool-execute__input,
.tool-execute__textarea {
  width: 100%;
  box-sizing: border-box;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  background: var(--color-surface, transparent);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-sm, 0.8125rem);
  font-family: inherit;
  resize: vertical;
}

.tool-execute__input--readonly {
  opacity: 0.7;
  cursor: not-allowed;
}

.tool-execute__actions {
  display: flex;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
  margin: var(--space-3, 12px) 0;
}

.tool-execute__btn {
  padding: var(--space-1, 4px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.04));
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-sm, 0.8125rem);
  cursor: pointer;
}

.tool-execute__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tool-execute__btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 1px;
}

.tool-execute__btn--primary {
  background: var(--color-accent, #7c8adb);
  border-color: var(--color-accent, #7c8adb);
  color: var(--color-on-accent, #fff);
}

.tool-execute__btn--ghost {
  background: transparent;
}

.tool-execute__status {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  margin: 0 0 var(--space-2, 8px);
}

.tool-execute__status[data-status="completed"] strong { color: var(--color-success, #5eba7d); }
.tool-execute__status[data-status="blocked"] strong { color: var(--color-warning, #d9a441); }
.tool-execute__status[data-status="error"] strong { color: var(--color-danger, #e5656b); }

.tool-execute__error {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-danger, #e5656b);
  margin: 0 0 var(--space-2, 8px);
}

.tool-execute__block {
  border-top: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  padding-top: var(--space-2, 8px);
  margin-top: var(--space-2, 8px);
}

.tool-execute__heading {
  font-size: var(--font-size-sm, 0.8125rem);
  margin: 0 0 var(--space-2, 8px);
  color: var(--color-text-primary, #e4e4e8);
}

.tool-execute__dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px var(--space-2, 8px);
  font-size: var(--font-size-xs, 0.75rem);
  margin: 0;
}

.tool-execute__dl dt {
  color: var(--color-text-secondary, #a0a0aa);
}

.tool-execute__dl dd {
  margin: 0;
  color: var(--color-text-primary, #e4e4e8);
  word-break: break-all;
}

.tool-execute__flags {
  list-style: none;
  padding: 0;
  margin: var(--space-2, 8px) 0 0;
  font-size: var(--font-size-xs, 0.75rem);
}

.tool-execute__flags li {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
}

.tool-execute__flag-label { color: var(--color-text-secondary, #a0a0aa); }

.tool-execute__flag-value--false {
  color: var(--color-success, #5eba7d);
}
</style>
