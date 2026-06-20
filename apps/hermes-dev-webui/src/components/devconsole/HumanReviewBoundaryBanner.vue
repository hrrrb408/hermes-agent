<script setup lang="ts">
/**
 * Human Review Governance boundary banner (Phase 3K).
 *
 * Surfaces the frozen, read-only human-review / approval boundary for the P0
 * gate picture. Every line is an explicit NO-GO / read-only / human-review-only
 * label (non-color identification). The banner is informational only — it grants
 * nothing, approves nothing, toggles nothing, and performs no action.
 */
import { Ban, Lock, ShieldAlert, ShieldX, UserCheck } from '@lucide/vue'
import type { Component } from 'vue'
import type {
  HumanReviewBoundaryItem,
  HumanReviewNogoDecision,
} from '@/types/api/humanReviewGovernance'

defineProps<{
  items: readonly HumanReviewBoundaryItem[]
  decisions: readonly HumanReviewNogoDecision[]
}>()

/** Map a boundary item kind to its icon (status is conveyed by the text label). */
const KIND_ICON: Readonly<Record<HumanReviewBoundaryItem['kind'], Component>> = {
  lock: Lock,
  ban: Ban,
  user: UserCheck,
}
</script>

<template>
  <aside
    class="hrgov-banner"
    role="status"
    aria-live="polite"
    data-testid="human-review-boundary-banner"
  >
    <header class="hrgov-banner__header">
      <ShieldAlert :size="16" aria-hidden="true" />
      <h2>Human Review Governance — read-only, human review required</h2>
    </header>
    <p class="hrgov-banner__note">
      This is a <strong>read-only decision-readiness projection</strong> of the P0
      human-review / approval picture. It displays the gate list, the pending
      human-review gates, the partial evidence, the evidence trail, and the NO-GO
      decision. It <strong>cannot approve gates, cannot authorize a runtime,
      cannot resolve P0, cannot enable production, and cannot replace human
      review</strong>. Code evidence is partial evidence only; valid approval
      requires an out-of-band trusted human process.
    </p>
    <ul class="hrgov-banner__list" data-testid="human-review-boundary-items">
      <li v-for="row in items" :key="row.label" :data-boundary-kind="row.kind">
        <component :is="KIND_ICON[row.kind]" :size="13" aria-hidden="true" />
        <span>{{ row.label }}</span>
      </li>
    </ul>
    <div class="hrgov-banner__verdicts" data-testid="human-review-boundary-decisions">
      <div
        v-for="d in decisions"
        :key="d.key"
        class="hrgov-banner__verdict"
        :data-decision-key="d.key"
      >
        <ShieldX :size="12" aria-hidden="true" />
        <span class="hrgov-banner__verdict-label">{{ d.label }}</span>
        <span class="hrgov-banner__verdict-value" :data-verdict="d.verdict">{{ d.verdict }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.hrgov-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-md, 8px);
  background: var(--color-surface-raised, #16161c);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  margin-bottom: var(--space-4, 16px);
}
.hrgov-banner__header {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.hrgov-banner__header h2 {
  margin: 0;
  font-size: var(--font-size-md, 14px);
}
.hrgov-banner__note {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.hrgov-banner__list {
  list-style: none;
  margin: 0 0 var(--space-3, 12px);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.hrgov-banner__list li {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.hrgov-banner__verdicts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
  border-top: 1px solid var(--color-border, #2a2a33);
  padding-top: var(--space-2, 8px);
}
.hrgov-banner__verdict {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.hrgov-banner__verdict-label {
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-banner__verdict-value {
  margin-left: auto;
  font-weight: 600;
  color: var(--color-danger, #e0566a);
}
</style>
