<script setup lang="ts">
/**
 * Governance Hub evidence trail summary (Phase 3L).
 *
 * Read-only timeline of the Phase 3 capability-chain evidence sources that feed
 * the partial evidence summarized on this surface. Each source states the
 * completed deliverable, what it proves, and — explicitly — what it does NOT
 * prove. Every source's authorization impact is "partial evidence only — no
 * production authorization". There is no interactive control here.
 */
import { GitBranch } from '@lucide/vue'
import type { GovernanceEvidenceSource } from '@/types/api/governanceHub'

defineProps<{
  sources: readonly GovernanceEvidenceSource[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-evidence-trail">
    <h2>Evidence trail summary (Phase 3 capability chain)</h2>
    <p class="ghub-muted">
      The phases that produced the partial evidence this surface summarizes. Each
      source proves something real — and each one explicitly does NOT authorize
      production. The evidence is partial only: it proves no production
      authorization, resolves no P0 gate, and is no replacement for human approval.
    </p>
    <ol class="ghub-trail" data-testid="governance-hub-evidence-list">
      <li
        v-for="(s, index) in sources"
        :key="s.phase + '-' + s.completedDeliverable"
        class="ghub-trail__item"
        :data-phase="s.phase"
      >
        <div class="ghub-trail__head">
          <GitBranch :size="14" aria-hidden="true" />
          <span class="ghub-trail__index">{{ index + 1 }}</span>
          <span class="ghub-trail__phase">{{ s.phase }}</span>
          <span class="ghub-trail__type">{{ s.evidenceType }}</span>
        </div>
        <p class="ghub-trail__deliverable">
          <span class="ghub-trail__cap">Deliverable</span>
          {{ s.completedDeliverable }}
        </p>
        <dl class="ghub-trail__dl">
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
            <dd class="ghub-trail__impact">{{ s.authorizationImpact }}</dd>
          </div>
        </dl>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.ghub-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-trail {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.ghub-trail__item {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.ghub-trail__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.ghub-trail__index {
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
.ghub-trail__phase {
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-sm, 13px);
}
.ghub-trail__type {
  margin-left: auto;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
.ghub-trail__deliverable {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  line-height: 1.5;
}
.ghub-trail__cap {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  margin-right: var(--space-1, 4px);
}
.ghub-trail__dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-trail__dl div {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.ghub-trail__dl dt {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
.ghub-trail__dl dd {
  margin: 0;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  line-height: 1.5;
}
.ghub-trail__impact {
  color: var(--color-warning, #d9a441);
  font-weight: 600;
}
</style>
