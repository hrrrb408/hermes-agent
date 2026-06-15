<script setup lang="ts">
import { computed } from 'vue'
import { lookupBlockedReason, type BlockedReasonSeverity } from '@/lib/blockedReasons'

/**
 * Reusable blocked-reason panel (Phase 2E).
 *
 * Renders a backend `blockedReason` code as a human-readable explanation with a
 * safe next action and a severity badge. Uses `lookupBlockedReason` so unknown
 * or future codes degrade to a safe generic message instead of throwing or
 * rendering raw text. Never suggests bypassing a safety boundary.
 */
const props = defineProps<{
  /** The backend blockedReason code (may be null/empty/unknown). */
  code: string | null | undefined
  /** Optional title override; defaults to the looked-up title. */
  title?: string
}>()

const info = computed(() => lookupBlockedReason(props.code))

const SEVERITY_LABEL: Record<BlockedReasonSeverity, string> = {
  info: 'Info',
  warn: 'Caution',
  danger: 'Blocked',
}
</script>

<template>
  <div
    class="blocked-reason dev-state dev-state--blocked"
    :class="[`dev-state--${info.severity}`]"
    role="alert"
    data-testid="dev-blocked-reason"
  >
    <div class="blocked-reason__head">
      <span class="blocked-reason__severity" :data-severity="info.severity">{{ SEVERITY_LABEL[info.severity] }}</span>
      <strong class="blocked-reason__title">{{ title ?? info.title }}</strong>
    </div>
    <p class="blocked-reason__code" data-testid="dev-blocked-reason-code">{{ info.code }}</p>
    <p class="blocked-reason__explanation">{{ info.explanation }}</p>
    <p class="blocked-reason__action">
      <span class="blocked-reason__action-label">Next safe action:</span>
      {{ info.safeNextAction }}
    </p>
  </div>
</template>

<style scoped>
.blocked-reason {
  display: grid;
  gap: var(--space-1, 4px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}

.dev-state--warn {
  border-color: var(--color-warning, #d4a843);
  background: var(--color-warning-soft, rgba(212, 168, 67, 0.12));
}
.dev-state--danger {
  border-color: var(--color-error, #e5656b);
  background: var(--color-error-soft, rgba(229, 101, 107, 0.12));
}

.blocked-reason__head {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}

.blocked-reason__severity {
  padding: 1px var(--space-2, 8px);
  font-size: 0.625rem;
  font-weight: var(--font-weight-semibold, 600);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-radius: var(--radius-pill, 999px);
  color: var(--color-text-secondary, #a0a0aa);
  background: var(--color-surface, transparent);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
}
.dev-state--warn .blocked-reason__severity {
  color: var(--color-warning, #d4a843);
  border-color: var(--color-warning, #d4a843);
}
.dev-state--danger .blocked-reason__severity {
  color: var(--color-error, #e5656b);
  border-color: var(--color-error, #e5656b);
}

.blocked-reason__title {
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
}

.blocked-reason__code {
  margin: 0;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
  word-break: break-all;
}

.blocked-reason__explanation {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  line-height: 1.5;
}

.blocked-reason__action {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-primary, #e4e4e8);
  line-height: 1.5;
}

.blocked-reason__action-label {
  color: var(--color-text-muted, #6a6a74);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.625rem;
  margin-right: 4px;
}
</style>
