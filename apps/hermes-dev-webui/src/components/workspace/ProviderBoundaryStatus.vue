<script setup lang="ts">
/**
 * Phase 3B Real Provider Boundary status panel.
 *
 * Renders the value-free real-provider boundary metadata from
 * GET /api/dev/v1/status data.providerBoundary:
 *   - boundary label: disabled / fake / real blocked / real gated
 *   - API enabled (no/yes, redacted), key env_present / env_missing
 *   - base URL allowlisted / blocked (host only, never a secret URL)
 *   - model (safe string), provider name + implemented flag
 *   - budget / rate-limit caps (safe), read-only tool allowlist
 *   - the permanent blocked flags (write / auto-write / autonomous /
 *     production rollout), and the current gating reason
 *
 * Safety: this component NEVER renders an API-key input, an API-key value,
 * an Authorization / Bearer header, a raw token, a full tokenHash, raw
 * arguments, a callable repr, or a production path. The backend redacts
 * everything before return.
 */
import { computed } from 'vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import { SELECTABLE_TOOL_IDS } from '@/constants/readOnlyTools'

const store = useToolProviderStore()

const boundary = computed(() => store.boundary)

const label = computed(() => {
  switch (store.boundaryLabel) {
    case 'fake': return 'Fake (offline)'
    case 'real_blocked': return 'Real — blocked'
    case 'real_gated': return 'Real — gated on'
    default: return 'Disabled'
  }
})

const labelClass = computed(() => `provider-boundary__label--${store.boundaryLabel}`)

const keyLabel = computed(() => {
  const b = boundary.value
  if (!b) return 'unknown'
  return b.apiKeyPresent ? 'env_present' : 'env_missing'
})

const baseUrlLabel = computed(() => {
  const b = boundary.value
  if (!b) return 'unknown'
  if (!b.baseUrlAllowed) return 'blocked'
  return b.baseUrlHost || 'allowlisted'
})

const flags = computed(() => {
  const b = boundary.value
  return [
    { key: 'mode', label: 'Provider mode', value: b?.providerMode ?? 'disabled' },
    { key: 'apiEnabled', label: 'API enabled', value: b?.apiEnabled ? 'yes (redacted)' : 'no' },
    { key: 'key', label: 'Provider credential', value: keyLabel.value },
    { key: 'baseUrl', label: 'Base URL', value: baseUrlLabel.value },
    { key: 'model', label: 'Model', value: b?.modelAllowed ? (b.model || '—') : 'blocked' },
    { key: 'adapter', label: 'Adapter', value: b?.providerNameImplemented ? b.providerName : 'not implemented' },
    { key: 'budget', label: 'Daily budget', value: b ? `${b.dailyBudgetCents}c` : '—' },
    { key: 'rateLimit', label: 'Rate limit', value: b ? `${b.perMinuteRequestCap}/min · ${b.dailyRequestCap}/day` : '—' },
    { key: 'reachable', label: 'Real reachable', value: b?.realReachable ? 'yes' : 'no' },
  ]
})

const blockedFlags = computed(() => [
  { key: 'write', label: 'Provider write', blocked: boundary.value?.providerWriteBlocked ?? true },
  { key: 'autoWrite', label: 'Provider auto-write', blocked: boundary.value?.providerAutoWriteBlocked ?? true },
  { key: 'autonomous', label: 'Autonomous write', blocked: boundary.value?.autonomousWriteBlocked ?? true },
  { key: 'rollout', label: 'Production rollout', blocked: boundary.value?.productionRolloutBlocked ?? true },
])

const readOnlyAllowlist = computed(() => SELECTABLE_TOOL_IDS)

/**
 * Phase 3B-Live-Enablement: the strict manual one-shot live gate. Live provider
 * stays disabled by default; the UI never accepts an API key. Value-free only.
 */
const live = computed(() => store.liveStatus)

const liveStateLabel = computed(() => {
  const l = live.value
  if (!l) return 'unknown'
  if (l.killSwitchActive) return 'kill switch active'
  if (l.liveEnabled) return 'live enabled'
  return 'disabled by default'
})

const liveCaps = computed(() => {
  const l = live.value
  if (!l) return []
  const b = l.budget
  return [
    { key: 'liveState', label: 'Live state', value: liveStateLabel.value },
    { key: 'approval', label: 'Approval', value: l.approvalRequired ? 'required (single-use, 5 min)' : 'not required' },
    { key: 'requests', label: 'Max requests', value: `${b.maxRequests}` },
    { key: 'tokens', label: 'Max total tokens', value: `${b.maxTotalTokens}` },
    { key: 'output', label: 'Max output tokens', value: `${b.maxOutputTokens}` },
    { key: 'budget', label: 'Max budget', value: `${b.maxBudgetCents}c` },
    { key: 'retry', label: 'Max retries', value: `${b.maxRetries}` },
    { key: 'runtime', label: 'Max runtime', value: `${b.maxRuntimeSeconds}s` },
    { key: 'host', label: 'Allowlisted host', value: 'api.openai.com' },
    { key: 'toolExec', label: 'Tool execution', value: l.toolExecutionDisabled ? 'disabled for first live' : 'ENABLED' },
  ]
})

const liveBlockedFlags = computed(() => {
  const l = live.value
  return [
    { key: 'liveWrite', label: 'Provider write', blocked: l?.providerWriteBlocked ?? true },
    { key: 'liveAutoWrite', label: 'Provider auto-write', blocked: l?.providerAutoWriteBlocked ?? true },
    { key: 'liveAutonomous', label: 'Autonomous write', blocked: l?.autonomousWriteBlocked ?? true },
    { key: 'liveRollout', label: 'Production rollout', blocked: l?.productionRolloutBlocked ?? true },
    { key: 'liveStreaming', label: 'Streaming', blocked: l?.streamingBlocked ?? true },
    { key: 'liveMulti', label: 'Multi-provider', blocked: l?.multiProviderBlocked ?? true },
  ]
})
</script>

<template>
  <section class="provider-boundary" aria-label="Real provider boundary status">
    <header class="provider-boundary__header">
      <h4 class="provider-boundary__title">Real Provider Boundary</h4>
      <span class="provider-boundary__label" :class="labelClass" data-testid="provider-boundary-label">
        {{ label }}
      </span>
    </header>

    <p class="provider-boundary__note">
      Real provider is disabled by default and read-only. No provider
      credential is ever accepted by the UI; the credential is read from the
      environment only, never displayed or stored.
    </p>

    <dl v-if="boundary" class="provider-boundary__flags" data-testid="provider-boundary-flags">
      <div v-for="f in flags" :key="f.key" class="provider-boundary__flag">
        <dt>{{ f.label }}</dt>
        <dd>{{ f.value }}</dd>
      </div>
    </dl>
    <p v-else class="provider-boundary__empty" data-testid="provider-boundary-empty">
      Boundary status unavailable (Dev API not connected).
    </p>

    <div v-if="boundary?.gatingReason" class="provider-boundary__reason" data-testid="provider-boundary-reason">
      <span class="provider-boundary__reason-label">Gating reason:</span>
      <code>{{ boundary.gatingReason }}</code>
    </div>

    <ul class="provider-boundary__blocked" aria-label="Permanently blocked operations">
      <li
        v-for="bf in blockedFlags"
        :key="bf.key"
        class="provider-boundary__blocked-item"
        :data-blocked="bf.blocked ? 'true' : 'false'"
      >
        <span class="provider-boundary__blocked-name">{{ bf.label }}</span>
        <span class="provider-boundary__blocked-state">{{ bf.blocked ? 'blocked' : 'ALLOWED' }}</span>
      </li>
    </ul>

    <div class="provider-boundary__allowlist" aria-label="Read-only tool allowlist">
      <span class="provider-boundary__allowlist-label">Read-only tool allowlist:</span>
      <code v-for="t in readOnlyAllowlist" :key="t" class="provider-boundary__allowlist-tool">{{ t }}</code>
    </div>

    <section
      v-if="live"
      class="provider-live"
      aria-label="Live provider enablement status"
      data-testid="provider-live-status"
    >
      <header class="provider-live__header">
        <h5 class="provider-live__title">Live Provider Enablement</h5>
        <span class="provider-live__label" data-testid="provider-live-label">{{ liveStateLabel }}</span>
      </header>

      <p class="provider-live__note">
        Real provider is disabled by default. First live enablement requires
        explicit human approval. First live request is one-shot. Budget cap:
        5 cents. Retries: 0. Provider tool execution is disabled for the first
        live request. Provider write and autonomous actions are blocked.
        Production rollout is not allowed.
      </p>

      <dl class="provider-live__caps" data-testid="provider-live-caps">
        <div v-for="f in liveCaps" :key="f.key" class="provider-live__cap">
          <dt>{{ f.label }}</dt>
          <dd>{{ f.value }}</dd>
        </div>
      </dl>

      <ul class="provider-live__blocked" aria-label="Live permanently blocked operations">
        <li
          v-for="bf in liveBlockedFlags"
          :key="bf.key"
          class="provider-live__blocked-item"
          :data-blocked="bf.blocked ? 'true' : 'false'"
        >
          <span class="provider-live__blocked-name">{{ bf.label }}</span>
          <span class="provider-live__blocked-state">{{ bf.blocked ? 'blocked' : 'ALLOWED' }}</span>
        </li>
      </ul>

      <p
        v-if="live.killSwitchActive"
        class="provider-live__kill"
        data-testid="provider-live-kill-switch"
      >
        Kill switch active ({{ live.killSwitchTriggeredBy }}). All live requests blocked; a fresh approval is required to re-enable.
      </p>
    </section>
  </section>
</template>

<style scoped>
.provider-boundary {
  border: 1px solid var(--provider-boundary-border, var(--border-color, #2a2a2a));
  border-radius: 8px;
  padding: 12px 14px;
  margin-top: 12px;
  background: var(--provider-boundary-bg, var(--panel-bg, transparent));
}
.provider-boundary__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.provider-boundary__title {
  margin: 0;
  font-size: 0.95rem;
}
.provider-boundary__label {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-color, #333);
}
.provider-boundary__label--disabled { opacity: 0.7; }
.provider-boundary__label--fake { color: var(--ok-fg, #4ade80); }
.provider-boundary__label--real_blocked { color: var(--warn-fg, #fbbf24); }
.provider-boundary__label--real_gated { color: var(--warn-fg, #fbbf24); }
.provider-boundary__note {
  margin: 8px 0 10px;
  font-size: 0.8rem;
  opacity: 0.8;
}
.provider-boundary__flags {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 6px 16px;
  margin: 0 0 10px;
}
.provider-boundary__flag { display: flex; justify-content: space-between; gap: 8px; }
.provider-boundary__flag dt { opacity: 0.7; font-size: 0.78rem; }
.provider-boundary__flag dd { margin: 0; font-size: 0.78rem; font-weight: 600; }
.provider-boundary__empty { opacity: 0.6; font-size: 0.8rem; }
.provider-boundary__reason {
  font-size: 0.78rem;
  margin-bottom: 8px;
}
.provider-boundary__reason-label { opacity: 0.7; margin-right: 4px; }
.provider-boundary__blocked {
  list-style: none;
  margin: 0 0 8px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.provider-boundary__blocked-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color, #333);
}
.provider-boundary__blocked-state {
  color: var(--warn-fg, #fbbf24);
  font-weight: 700;
}
.provider-boundary__allowlist {
  font-size: 0.72rem;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.provider-boundary__allowlist-label { opacity: 0.7; }
.provider-boundary__allowlist-tool {
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--chip-bg, rgba(127, 127, 127, 0.15));
  font-size: 0.7rem;
}

.provider-live {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px dashed var(--border-color, #333);
  border-radius: 8px;
}
.provider-live__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.provider-live__title {
  margin: 0;
  font-size: 0.85rem;
}
.provider-live__label {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-color, #333);
}
.provider-live__note {
  margin: 8px 0;
  font-size: 0.74rem;
  opacity: 0.8;
  line-height: 1.4;
}
.provider-live__caps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 4px 16px;
  margin: 0 0 8px;
}
.provider-live__cap { display: flex; justify-content: space-between; gap: 8px; }
.provider-live__cap dt { opacity: 0.7; font-size: 0.74rem; }
.provider-live__cap dd { margin: 0; font-size: 0.74rem; font-weight: 600; }
.provider-live__blocked {
  list-style: none;
  margin: 0 0 8px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.provider-live__blocked-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color, #333);
}
.provider-live__blocked-state {
  color: var(--warn-fg, #fbbf24);
  font-weight: 700;
}
.provider-live__kill {
  font-size: 0.74rem;
  color: var(--danger-fg, #f87171);
  margin: 0;
}
</style>
