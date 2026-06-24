<script setup lang="ts">
/**
 * Governance Hub NO-GO decision panel (Phase 3L).
 *
 * Read-only projection of the frozen NO-GO decision block. Every decision
 * dimension is frozen NO-GO / not-authorized. There is no interactive control
 * here — the panel only explains why each dimension holds NO-GO.
 */
import { ShieldX } from '@lucide/vue'
import type { GovernanceDecisionRow } from '@/types/api/governanceHub'

defineProps<{
  decisions: readonly GovernanceDecisionRow[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-nogo-panel">
    <h2>NO-GO decision summary</h2>
    <p class="ghub-muted">
      The current authorization decision. Implementation Authorization, Phase 3I
      production authorization, production runtime, every new-route dimension,
      every approval / execution dimension, and production rollout all remain
      NO-GO because resolved_count is 0, five gates are pending human review, no
      trust token is provisioned, and metadata / AI / placeholder approval cannot
      approve a gate.
    </p>
    <ul class="ghub-nogo" data-testid="governance-hub-nogo-list">
      <li v-for="d in decisions" :key="d.key" :data-decision-key="d.key">
        <ShieldX :size="13" aria-hidden="true" />
        <div class="ghub-nogo__body">
          <span class="ghub-nogo__label">
            {{ d.label }}
            <strong class="ghub-nogo__verdict" :data-verdict="d.verdict">{{ d.verdict }}</strong>
          </span>
          <span class="ghub-nogo__reason">{{ d.reason }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ghub-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-nogo {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-nogo li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.ghub-nogo__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.ghub-nogo__label {
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.ghub-nogo__verdict {
  margin-left: var(--space-2, 8px);
  color: var(--color-danger, #e0566a);
}
.ghub-nogo__reason {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
</style>
