<script setup lang="ts">
/**
 * Governance Hub boundary banner (Phase 3L).
 *
 * Surfaces the frozen, read-only unified-control-center boundary. Every line is
 * an explicit NO-GO / read-only / no-execution / no-approval / routes-unchanged
 * label (non-color identification). The banner is informational only — it grants
 * nothing, approves nothing, authorizes nothing, executes nothing, and changes no
 * route.
 */
import { Ban, Lock, ShieldAlert, ShieldX } from '@lucide/vue'
import type { Component } from 'vue'
import type {
  GovernanceBoundaryItem,
  GovernanceDecisionRow,
} from '@/types/api/governanceHub'

defineProps<{
  items: readonly GovernanceBoundaryItem[]
  decisions: readonly GovernanceDecisionRow[]
}>()

/** Map a boundary item kind to its icon (status is conveyed by the text label). */
const KIND_ICON: Readonly<Record<GovernanceBoundaryItem['kind'], Component>> = {
  lock: Lock,
  ban: Ban,
}
</script>

<template>
  <aside
    class="ghub-banner"
    role="status"
    aria-live="polite"
    data-testid="governance-hub-boundary-banner"
  >
    <header class="ghub-banner__header">
      <ShieldAlert :size="16" aria-hidden="true" />
      <h2>Governance Hub — read-only unified control center</h2>
    </header>
    <p class="ghub-banner__note">
      This is a <strong>read-only summary</strong> of the governance state. It
      <strong>cannot execute a runtime, cannot approve gates, cannot authorize
      production, and cannot change routes</strong>. It aggregates the Runtime
      Governance and Human Review Governance surfaces read-only; every P0 count is
      frozen (resolved 0, partial 19, pending 5) and every authorization verdict is
      frozen NO-GO / not-authorized.
    </p>
    <ul class="ghub-banner__list" data-testid="governance-hub-boundary-items">
      <li v-for="row in items" :key="row.label" :data-boundary-kind="row.kind">
        <component :is="KIND_ICON[row.kind]" :size="13" aria-hidden="true" />
        <span>{{ row.label }}</span>
      </li>
    </ul>
    <div class="ghub-banner__verdicts" data-testid="governance-hub-boundary-decisions">
      <div
        v-for="d in decisions"
        :key="d.key"
        class="ghub-banner__verdict"
        :data-decision-key="d.key"
      >
        <ShieldX :size="12" aria-hidden="true" />
        <span class="ghub-banner__verdict-label">{{ d.label }}</span>
        <span class="ghub-banner__verdict-value" :data-verdict="d.verdict">{{ d.verdict }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.ghub-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-md, 8px);
  background: var(--color-surface-raised, #16161c);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  margin-bottom: var(--space-4, 16px);
}
.ghub-banner__header {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.ghub-banner__header h2 {
  margin: 0;
  font-size: var(--font-size-md, 14px);
}
.ghub-banner__note {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-banner__list {
  list-style: none;
  margin: 0 0 var(--space-3, 12px);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-banner__list li {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.ghub-banner__verdicts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
  border-top: 1px solid var(--color-border, #2a2a33);
  padding-top: var(--space-2, 8px);
}
.ghub-banner__verdict {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.ghub-banner__verdict-label {
  color: var(--color-text-muted, #8a8a94);
}
.ghub-banner__verdict-value {
  margin-left: auto;
  font-weight: 600;
  color: var(--color-danger, #e0566a);
}
</style>
