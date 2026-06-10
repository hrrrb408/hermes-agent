<script setup lang="ts">
import { useToolPolicyStore } from '@/stores/toolPolicy'
import { RISK_LABELS } from '@/types/api/toolPolicyConstants'
import type { ToolRiskLevel } from '@/types/api/toolPolicy'

const store = useToolPolicyStore()

const riskLevels: readonly ToolRiskLevel[] = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5']

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function formatCount(n: number): string {
  return String(n)
}
</script>

<template>
  <div class="tool-policy-overview">
    <!-- Loading -->
    <div v-if="store.isPolicyLoading" class="panel-loading" aria-busy="true" aria-live="polite">
      Loading tool policy…
    </div>

    <!-- Error -->
    <div v-else-if="store.policyState === 'error'" class="panel-error" role="alert">
      <p>{{ store.policyError }}</p>
      <button type="button" class="panel-retry-btn" aria-label="Retry loading tool policy" @click="store.retryPolicy()">Retry policy</button>
    </div>

    <!-- Policy data -->
    <template v-else-if="store.policy">
      <!-- Safety notice -->
      <div class="tp-notice" role="status">
        <p class="tp-notice__title">Read-only policy view</p>
        <ul class="tp-notice__list">
          <li>No tools are enabled</li>
          <li>No tool calls can be executed</li>
          <li>No provider schemas are sent</li>
        </ul>
      </div>

      <!-- Summary statistics -->
      <article class="panel-card">
        <h4>Policy Summary</h4>
        <dl class="context-list">
          <div><dt>Policy Mode</dt><dd>{{ store.policy.mode }}</dd></div>
          <div><dt>Inventory</dt><dd>{{ formatCount(store.policy.inventoryCount) }}</dd></div>
          <div><dt>Permanent Denylist</dt><dd>{{ formatCount(store.policy.permanentDenylistCount) }}</dd></div>
          <div><dt>Candidate Allowlist</dt><dd>{{ formatCount(store.policy.candidateAllowlistCount) }}</dd></div>
          <div><dt>Enabled Allowlist</dt><dd>{{ formatCount(store.policy.enabledAllowlistCount) }}</dd></div>
        </dl>
      </article>

      <!-- Risk Distribution -->
      <article class="panel-card">
        <h4>Risk Distribution</h4>
        <div class="tp-risk-grid">
          <div v-for="level in riskLevels" :key="level" class="tp-risk-row">
            <span class="tp-risk-code" :class="`tp-risk-code--${level}`">{{ level }}</span>
            <span class="tp-risk-label">{{ RISK_LABELS[level] }}</span>
            <span class="tp-risk-count">{{ formatCount(store.policy.riskCounts[level]) }}</span>
          </div>
        </div>
      </article>

      <!-- Execution Status -->
      <article class="panel-card">
        <h4>Execution Status</h4>
        <dl class="context-list">
          <div>
            <dt>Tool Execution</dt>
            <dd class="panel-flag panel-flag--disabled">{{ store.policy.execution.enabled ? 'Enabled' : 'Disabled' }}</dd>
          </div>
          <div>
            <dt>Provider Schema</dt>
            <dd class="panel-flag panel-flag--disabled">{{ store.policy.execution.providerSchemaSent ? 'Sent' : 'Not sent' }}</dd>
          </div>
          <div>
            <dt>Dispatch</dt>
            <dd class="panel-flag panel-flag--disabled">{{ store.policy.execution.dispatchAvailable ? 'Available' : 'Unavailable' }}</dd>
          </div>
          <div>
            <dt>Audit</dt>
            <dd class="panel-flag panel-flag--disabled">{{ store.policy.execution.auditAvailable ? 'Available' : 'Unavailable' }}</dd>
          </div>
        </dl>
      </article>

      <!-- Safety Status -->
      <article class="panel-card">
        <h4>Safety Status</h4>
        <dl class="context-list">
          <div><dt>Read Only</dt><dd class="panel-flag panel-flag--disabled">{{ store.policy.safety.readOnly ? 'Yes' : 'No' }}</dd></div>
          <div><dt>Side Effects</dt><dd class="panel-flag panel-flag--disabled">{{ store.policy.safety.sideEffects ? 'Yes' : 'No' }}</dd></div>
          <div><dt>Write Enabled</dt><dd class="panel-flag panel-flag--disabled">{{ store.policy.safety.writeEnabled ? 'Yes' : 'No' }}</dd></div>
          <div><dt>Execute Available</dt><dd class="panel-flag panel-flag--disabled">{{ store.policy.safety.executeAvailable ? 'Yes' : 'No' }}</dd></div>
          <div><dt>Policy Mutation</dt><dd class="panel-flag panel-flag--disabled">{{ store.policy.safety.policyMutationAvailable ? 'Available' : 'Unavailable' }}</dd></div>
        </dl>
      </article>

      <!-- Limits -->
      <article class="panel-card">
        <h4>Policy Limits</h4>
        <h5 class="tp-limits-heading">Argument Constraints</h5>
        <dl class="context-list">
          <div><dt>Max Payload</dt><dd>{{ formatBytes(store.policy.limits.maxArgumentPayloadBytes) }}</dd></div>
          <div><dt>Max Nesting Depth</dt><dd>{{ store.policy.limits.maxArgumentNestingDepth }}</dd></div>
          <div><dt>Max String Length</dt><dd>{{ formatBytes(store.policy.limits.maxArgumentStringLength) }}</dd></div>
          <div><dt>Max Array Length</dt><dd>{{ formatCount(store.policy.limits.maxArgumentArrayLength) }}</dd></div>
        </dl>

        <h5 class="tp-limits-heading">Timeout</h5>
        <dl class="context-list">
          <div><dt>R0 Timeout</dt><dd>{{ store.policy.limits.defaultR0TimeoutSeconds }}s</dd></div>
          <div><dt>R1 Timeout</dt><dd>{{ store.policy.limits.defaultR1TimeoutSeconds }}s</dd></div>
          <div><dt>Max Tool Timeout</dt><dd>{{ store.policy.limits.maxToolTimeoutSeconds }}s</dd></div>
        </dl>

        <h5 class="tp-limits-heading">Concurrency</h5>
        <dl class="context-list">
          <div><dt>Calls Per Run</dt><dd>{{ formatCount(store.policy.limits.maxToolCallsPerRun) }}</dd></div>
          <div><dt>Global Concurrency</dt><dd>{{ formatCount(store.policy.limits.maxGlobalConcurrency) }}</dd></div>
          <div><dt>Per-Run Concurrency</dt><dd>{{ formatCount(store.policy.limits.maxConcurrencyPerRun) }}</dd></div>
        </dl>

        <h5 class="tp-limits-heading">Output</h5>
        <dl class="context-list">
          <div><dt>Serialized Output</dt><dd>{{ formatBytes(store.policy.limits.maxSerializedOutputBytes) }}</dd></div>
          <div><dt>Agent-Visible Output</dt><dd>{{ formatBytes(store.policy.limits.maxAgentVisibleOutputBytes) }}</dd></div>
          <div><dt>Web Preview Output</dt><dd>{{ formatBytes(store.policy.limits.maxWebPreviewOutputBytes) }}</dd></div>
        </dl>
      </article>
    </template>

    <!-- Empty / Missing -->
    <div v-else class="panel-empty">
      No tool policy data available.
    </div>
  </div>
</template>

<style scoped>
.tool-policy-overview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

/* Safety notice */
.tp-notice {
  padding: var(--space-3, 12px);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-warning-soft, rgba(212, 168, 67, 0.12));
  border: 1px solid var(--color-warning, #d4a843);
}

.tp-notice__title {
  font-weight: var(--font-weight-semibold, 600);
  font-size: var(--font-size-sm, 0.8125rem);
  margin: 0 0 var(--space-1, 4px);
  color: var(--color-text-primary, #e4e4e8);
}

.tp-notice__list {
  margin: 0;
  padding-left: var(--space-4, 16px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  line-height: var(--content-line-height, 1.6);
}

.tp-notice__list li {
  margin-bottom: var(--space-1, 4px);
}

/* Risk grid */
.tp-risk-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.tp-risk-row {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-1, 4px) 0;
}

.tp-risk-code {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-xs, 0.75rem);
  font-weight: var(--font-weight-semibold, 600);
  font-family: var(--font-code, monospace);
}

.tp-risk-code--R0 { background: var(--color-success-soft, rgba(94, 184, 122, 0.12)); color: var(--color-success, #5eb87a); }
.tp-risk-code--R1 { background: var(--color-success-soft, rgba(94, 184, 122, 0.12)); color: var(--color-success, #5eb87a); }
.tp-risk-code--R2 { background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12)); color: var(--color-neutral, #7a7a84); }
.tp-risk-code--R3 { background: var(--color-warning-soft, rgba(212, 168, 67, 0.12)); color: var(--color-warning, #d4a843); }
.tp-risk-code--R4 { background: var(--color-error-soft, rgba(212, 86, 86, 0.12)); color: var(--color-error, #d45656); }
.tp-risk-code--R5 { background: var(--color-error-soft, rgba(212, 86, 86, 0.12)); color: var(--color-error, #d45656); }

.tp-risk-label {
  flex: 1;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  overflow-wrap: break-word;
}

.tp-risk-count {
  font-size: var(--font-size-sm, 0.8125rem);
  font-weight: var(--font-weight-medium, 500);
  color: var(--color-text-primary, #e4e4e8);
  min-width: 2ch;
  text-align: right;
}

/* Limits heading */
.tp-limits-heading {
  font-size: var(--font-size-xs, 0.75rem);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-muted, #6a6a74);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: var(--space-3, 12px) 0 var(--space-1, 4px);
  padding-bottom: var(--space-1, 4px);
  border-bottom: 1px solid var(--color-divider, rgba(255, 255, 255, 0.06));
}

.tp-limits-heading:first-of-type {
  margin-top: 0;
}

@media (max-width: 768px) {
  .tp-risk-row {
    flex-wrap: wrap;
  }
}
</style>
