<script setup lang="ts">
/**
 * Phase 2B Provider Round-trip panel.
 *
 * Surfaces the controlled Provider Schema / API round-trip:
 *   - provider mode selector (disabled / fake / real)
 *   - user message input
 *   - allowed-tools selector (read-only allowlist only)
 *   - provider schema preview
 *   - run fake provider round-trip button
 *   - tool calls / tool results / final answer / audit IDs
 *   - safety badges (read-only only, write disabled, real blocked)
 *
 * The UI NEVER accepts an API key. Real mode is surfaced but always blocked
 * by the backend unless explicitly enabled.
 */
import { computed, onMounted } from 'vue'
import { useToolProviderStore, PROVIDER_MODES } from '@/stores/toolProvider'
import { SELECTABLE_TOOLS } from '@/constants/readOnlyTools'
import ProviderBoundaryStatus from './ProviderBoundaryStatus.vue'

const store = useToolProviderStore()

// Phase 3B: load the value-free real-provider boundary metadata on mount.
onMounted(() => {
  void store.loadBoundary()
})

const safetyBadges = computed(() => [
  { key: 'readonly', label: 'Read-only only', value: true },
  { key: 'write', label: 'Tool write disabled', value: true },
  { key: 'real', label: 'Real provider blocked unless enabled', value: true },
])

const providerFlags = computed(() => {
  const r = store.result
  if (!r) return []
  return [
    { key: 'providerMode', label: 'Provider mode', value: r.providerMode },
    { key: 'schemaSent', label: 'Provider schema sent', value: r.providerSchemaSent },
    { key: 'apiCalled', label: 'Provider API called', value: r.providerApiCalled },
    { key: 'network', label: 'External network called', value: r.externalNetworkCalled },
    { key: 'readonlyOnly', label: 'Read-only only', value: r.readOnlyOnly },
  ]
})

const toolResultsJson = computed(() => {
  const r = store.result
  if (!r || r.toolResults.length === 0) return null
  try {
    return JSON.stringify(
      r.toolResults.map((tr) => ({
        toolId: tr.toolId,
        executed: tr.executed,
        status: tr.status,
        blockedReason: tr.blockedReason,
      })),
      null,
      2,
    )
  } catch {
    return null
  }
})

function statusLabel(): string {
  switch (store.status) {
    case 'idle': return 'Idle'
    case 'loading': return 'Running provider round-trip…'
    case 'completed': return 'Completed'
    case 'blocked': return 'Blocked'
    case 'error': return 'Error'
    default: return store.status
  }
}

function onRun(): void {
  void store.runRoundtrip()
}
</script>

<template>
  <section class="provider-rt" aria-label="Provider round-trip">
    <header class="provider-rt__header">
      <h3>Provider Round-trip</h3>
      <p class="provider-rt__intro">
        Controlled Provider Schema / API round-trip over the Phase 2A read-only
        tools. Fake mode is deterministic and offline. Real mode is blocked by
        default.
      </p>
    </header>

    <div class="provider-rt__badges" aria-label="Safety badges">
      <span
        v-for="badge in safetyBadges"
        :key="badge.key"
        class="provider-rt__chip provider-rt__chip--safe"
      >
        {{ badge.label }}
      </span>
    </div>

    <ProviderBoundaryStatus data-testid="provider-boundary-status" />

    <div class="provider-rt__block">
      <label class="provider-rt__label" for="provider-mode">Provider mode</label>
      <select
        id="provider-mode"
        class="provider-rt__select"
        :value="store.providerMode"
        @change="store.setProviderMode(($event.target as HTMLSelectElement).value as never)"
      >
        <option v-for="mode in PROVIDER_MODES" :key="mode" :value="mode">{{ mode }}</option>
      </select>
      <p v-if="store.isRealBlocked" class="provider-rt__hint provider-rt__hint--warn">
        Real provider mode is blocked by the backend unless explicitly enabled
        (env key + dev home + production gate). No API key input is accepted.
      </p>
    </div>

    <div class="provider-rt__block">
      <label class="provider-rt__label" for="provider-message">Message</label>
      <textarea
        id="provider-message"
        class="provider-rt__textarea"
        rows="3"
        maxlength="4000"
        placeholder="e.g. check route governance"
        :value="store.message"
        @input="store.setMessage(($event.target as HTMLTextAreaElement).value)"
      />
    </div>

    <div class="provider-rt__block">
      <div class="provider-rt__label-row">
        <span class="provider-rt__label">Allowed tools</span>
        <button class="provider-rt__btn provider-rt__btn--ghost" type="button" @click="store.selectAllTools">All</button>
        <button class="provider-rt__btn provider-rt__btn--ghost" type="button" @click="store.clearAllTools">None</button>
      </div>
      <ul class="provider-rt__tools" aria-label="Allowed tools selector">
        <li v-for="tool in SELECTABLE_TOOLS" :key="tool.id">
          <label class="provider-rt__checkbox">
            <input
              type="checkbox"
              :checked="store.selectedToolIds.includes(tool.id)"
              @change="store.toggleTool(tool.id)"
            />
            <span>{{ tool.displayName }} <em>({{ tool.riskTier }})</em></span>
          </label>
        </li>
      </ul>
    </div>

    <div class="provider-rt__actions">
      <button
        class="provider-rt__btn provider-rt__btn--primary"
        type="button"
        :disabled="!store.canRun"
        @click="onRun"
      >
        Run fake provider round-trip
      </button>
      <button class="provider-rt__btn provider-rt__btn--ghost" type="button" @click="store.reset">
        Reset
      </button>
    </div>

    <p class="provider-rt__status" :data-status="store.status">{{ statusLabel() }}</p>
    <p v-if="store.error" class="provider-rt__error">{{ store.error }}</p>

    <div v-if="store.result" class="provider-rt__result">
      <div class="provider-rt__block">
        <h4 class="provider-rt__heading">Provider flags</h4>
        <dl class="provider-rt__flags">
          <template v-for="flag in providerFlags" :key="flag.key">
            <dt class="provider-rt__flag-label">{{ flag.label }}</dt>
            <dd class="provider-rt__flag-value">{{ String(flag.value) }}</dd>
          </template>
        </dl>
      </div>

      <div v-if="store.result.blockedReason" class="provider-rt__block">
        <h4 class="provider-rt__heading">Blocked reason</h4>
        <p class="provider-rt__hint provider-rt__hint--warn">{{ store.result.blockedReason }}</p>
      </div>

      <div v-if="store.result.toolCalls.length" class="provider-rt__block">
        <h4 class="provider-rt__heading">Tool calls</h4>
        <ul class="provider-rt__list">
          <li v-for="call in store.result.toolCalls" :key="call.id">
            <strong>{{ call.name }}</strong>
            <span class="provider-rt__status-chip" :data-status="call.status">{{ call.status }}</span>
            <pre v-if="Object.keys(call.arguments).length" class="provider-rt__pre">{{ JSON.stringify(call.arguments, null, 2) }}</pre>
          </li>
        </ul>
      </div>

      <div v-if="toolResultsJson" class="provider-rt__block">
        <h4 class="provider-rt__heading">Tool results</h4>
        <pre class="provider-rt__pre">{{ toolResultsJson }}</pre>
      </div>

      <div v-if="store.result.finalAnswer" class="provider-rt__block">
        <h4 class="provider-rt__heading">Final answer</h4>
        <p class="provider-rt__final">{{ store.result.finalAnswer }}</p>
      </div>

      <div v-if="store.result.providerAuditIds.length" class="provider-rt__block">
        <h4 class="provider-rt__heading">Provider audit IDs</h4>
        <p class="provider-rt__meta">{{ store.result.providerAuditIds.length }} event(s)</p>
        <ul class="provider-rt__audit">
          <li v-for="id in store.result.providerAuditIds.slice(0, 12)" :key="id">{{ id }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.provider-rt {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.provider-rt__header h3 {
  margin: 0 0 4px;
  font-size: 1rem;
}
.provider-rt__intro {
  margin: 0;
  color: var(--color-text-muted, #888);
  font-size: 0.82rem;
  line-height: 1.4;
}
.provider-rt__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.provider-rt__chip {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--color-border, #333);
}
.provider-rt__chip--safe {
  color: var(--color-success, #3fb950);
  border-color: var(--color-success, #3fb950);
}
.provider-rt__block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.provider-rt__label {
  font-size: 0.78rem;
  color: var(--color-text-muted, #888);
}
.provider-rt__label-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.provider-rt__select,
.provider-rt__textarea,
.provider-rt__pre {
  width: 100%;
  box-sizing: border-box;
  background: var(--color-surface, #1a1a1a);
  color: var(--color-text, #eee);
  border: 1px solid var(--color-border, #333);
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
}
.provider-rt__pre {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.74rem;
  white-space: pre-wrap;
  max-height: 200px;
  overflow: auto;
}
.provider-rt__tools {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.provider-rt__checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}
.provider-rt__checkbox em {
  color: var(--color-text-muted, #888);
  font-style: normal;
}
.provider-rt__actions {
  display: flex;
  gap: 8px;
}
.provider-rt__btn {
  font: inherit;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--color-border, #333);
  background: var(--color-surface, #1a1a1a);
  color: var(--color-text, #eee);
  cursor: pointer;
}
.provider-rt__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.provider-rt__btn--primary {
  background: var(--color-accent, #4b8);
  border-color: var(--color-accent, #4b8);
  color: #fff;
}
.provider-rt__btn--ghost {
  background: transparent;
  padding: 2px 8px;
  font-size: 0.74rem;
}
.provider-rt__status {
  margin: 0;
  font-size: 0.78rem;
  color: var(--color-text-muted, #888);
}
.provider-rt__status[data-status='completed'] { color: var(--color-success, #3fb950); }
.provider-rt__status[data-status='blocked'],
.provider-rt__status[data-status='error'] { color: var(--color-danger, #f85149); }
.provider-rt__error {
  margin: 0;
  color: var(--color-danger, #f85149);
  font-size: 0.78rem;
}
.provider-rt__result {
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-top: 1px solid var(--color-border, #333);
  padding-top: 12px;
}
.provider-rt__heading {
  margin: 0 0 4px;
  font-size: 0.82rem;
}
.provider-rt__flags {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 10px;
  margin: 0;
  font-size: 0.76rem;
}
.provider-rt__flag-label { color: var(--color-text-muted, #888); }
.provider-rt__hint {
  margin: 0;
  font-size: 0.74rem;
  color: var(--color-text-muted, #888);
}
.provider-rt__hint--warn { color: var(--color-warning, #d29922); }
.provider-rt__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.78rem;
}
.provider-rt__status-chip {
  margin-left: 6px;
  font-size: 0.68rem;
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid var(--color-border, #333);
}
.provider-rt__status-chip[data-status='valid'] { color: var(--color-success, #3fb950); }
.provider-rt__final {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
}
.provider-rt__meta {
  margin: 0;
  font-size: 0.74rem;
  color: var(--color-text-muted, #888);
}
.provider-rt__audit {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.7rem;
  color: var(--color-text-muted, #888);
  max-height: 120px;
  overflow: auto;
}
.provider-rt__audit li {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
