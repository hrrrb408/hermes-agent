<script setup lang="ts">
/**
 * Human Review Governance evidence trail (Phase 3K).
 *
 * Read-only timeline of the Phase 3 capability-chain evidence sources that feed
 * the partial evidence shown on this surface. Each source states what it proves
 * and — explicitly — what it does NOT prove. Every source's authorization impact
 * is "partial evidence only — no production authorization". There is no
 * interactive control here; the trail is informational.
 */
import { GitBranch } from '@lucide/vue'
import type { HumanReviewEvidenceSource } from '@/types/api/humanReviewGovernance'

defineProps<{
  sources: readonly HumanReviewEvidenceSource[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="human-review-evidence-trail">
    <h2>Evidence trail (Phase 3 capability chain)</h2>
    <p class="hrgov-muted">
      The phases that produced the partial evidence this surface summarizes. Each
      source proves something real — and each one explicitly does NOT authorize
      production. None of them can approve a gate or provision a trust token.
    </p>
    <ol class="hrgov-trail" data-testid="human-review-evidence-list">
      <li
        v-for="(s, index) in sources"
        :key="s.phase"
        class="hrgov-trail__item"
        :data-phase="s.phase"
      >
        <div class="hrgov-trail__head">
          <GitBranch :size="14" aria-hidden="true" />
          <span class="hrgov-trail__index">{{ index + 1 }}</span>
          <span class="hrgov-trail__phase">{{ s.phase }}</span>
          <span class="hrgov-trail__type">{{ s.evidenceType }}</span>
        </div>
        <dl class="hrgov-trail__dl">
          <div>
            <dt>Proves</dt>
            <dd>{{ s.whatItProves }}</dd>
          </div>
          <div>
            <dt>Does NOT prove</dt>
            <dd>{{ s.whatItDoesNotProve }}</dd>
          </div>
          <div>
            <dt>Authorization impact</dt>
            <dd class="hrgov-trail__impact">{{ s.authorizationImpact }}</dd>
          </div>
        </dl>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.hrgov-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.hrgov-trail {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.hrgov-trail__item {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.hrgov-trail__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.hrgov-trail__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  border-radius: var(--radius-sm, 6px);
  background: var(--color-surface-raised, #1c1c24);
  border: 1px solid var(--color-border, #2a2a33);
  font-size: var(--font-size-xs, 12px);
  font-weight: 600;
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-trail__phase {
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-sm, 13px);
}
.hrgov-trail__type {
  margin-left: auto;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
.hrgov-trail__dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.hrgov-trail__dl div {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.hrgov-trail__dl dt {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
.hrgov-trail__dl dd {
  margin: 0;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  line-height: 1.5;
}
.hrgov-trail__impact {
  color: var(--color-warning, #d9a441);
  font-weight: 600;
}
</style>
