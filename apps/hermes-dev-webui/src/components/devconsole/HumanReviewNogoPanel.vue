<script setup lang="ts">
/**
 * Human Review Governance NO-GO decision panel (Phase 3K).
 *
 * Read-only projection of the frozen NO-GO decision block plus the
 * Runtime-Governance↔Human-Review relationship. Every decision dimension is
 * frozen NO-GO / not-authorized; the relationship states that neither surface
 * can approve production, execute a production runtime, or change route
 * governance. There is no interactive control here.
 */
import { ShieldX, Link2 } from '@lucide/vue'
import type {
  HumanReviewNogoDecision,
  HumanReviewRelationshipItem,
} from '@/types/api/humanReviewGovernance'

defineProps<{
  decisions: readonly HumanReviewNogoDecision[]
  relationship: readonly HumanReviewRelationshipItem[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="human-review-nogo-panel">
    <h2>NO-GO decision</h2>
    <p class="hrgov-muted">
      The current authorization decision. Implementation Authorization, production
      runtime, new route, and production rollout all remain NO-GO because
      resolved_count is 0, five gates are pending human review, no trust token is
      provisioned, and metadata / AI / placeholder approval cannot approve a gate.
    </p>
    <ul class="hrgov-nogo" data-testid="human-review-nogo-list">
      <li v-for="d in decisions" :key="d.key" :data-decision-key="d.key">
        <ShieldX :size="13" aria-hidden="true" />
        <div class="hrgov-nogo__body">
          <span class="hrgov-nogo__label">
            {{ d.label }}
            <strong class="hrgov-nogo__verdict" :data-verdict="d.verdict">{{ d.verdict }}</strong>
          </span>
          <span class="hrgov-nogo__reason">{{ d.reason }}</span>
        </div>
      </li>
    </ul>

    <h2 class="hrgov-rel__title">Runtime Governance ↔ Human Review</h2>
    <p class="hrgov-muted">
      Runtime Governance (CLI / WebUI) is the <strong>evidence surface</strong>;
      Human Review Governance is the <strong>decision-readiness surface</strong>.
      Neither can approve production.
    </p>
    <ul class="hrgov-rel" data-testid="human-review-relationship-list">
      <li v-for="r in relationship" :key="r.key" :data-relationship-key="r.key">
        <Link2 :size="13" aria-hidden="true" />
        <div class="hrgov-rel__body">
          <span class="hrgov-rel__label">{{ r.label }}</span>
          <span class="hrgov-rel__detail">{{ r.detail }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.hrgov-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.hrgov-nogo {
  list-style: none;
  margin: 0 0 var(--space-3, 12px);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.hrgov-nogo li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.hrgov-nogo__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.hrgov-nogo__label {
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.hrgov-nogo__verdict {
  margin-left: var(--space-2, 8px);
  color: var(--color-danger, #e0566a);
}
.hrgov-nogo__reason {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
.hrgov-rel__title {
  margin: var(--space-3, 12px) 0 var(--space-2, 8px);
  font-size: var(--font-size-md, 14px);
}
.hrgov-rel {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.hrgov-rel li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
}
.hrgov-rel__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.hrgov-rel__label {
  font-size: var(--font-size-sm, 13px);
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.hrgov-rel__detail {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
</style>
