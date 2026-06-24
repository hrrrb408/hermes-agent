<script setup lang="ts">
/**
 * Governance Hub cross-links panel (Phase 3L).
 *
 * Read-only navigation to the existing Runtime Governance (Phase 3J) and Human
 * Review (Phase 3K) client-side sections. Clicking a link emits a `navigate`
 * event the parent wires to the devConsoleNav store — a client-only section
 * switch that performs NO backend call, NO SPA route change, and NO runtime call.
 */
import { ArrowRight } from '@lucide/vue'
import type { GovernanceHubCrossLink } from '@/types/api/governanceHub'

defineProps<{
  crossLinks: readonly GovernanceHubCrossLink[]
}>()

const emit = defineEmits<{
  (e: 'navigate', target: 'runtimeGovernance' | 'humanReview'): void
}>()

function onNavigate(target: 'runtimeGovernance' | 'humanReview'): void {
  emit('navigate', target)
}
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-cross-links">
    <h2>Cross-links (read-only navigation)</h2>
    <p class="ghub-muted">
      Open the existing read-only governance sections. These links switch the Dev
      Console section client-side — they perform no backend call, no SPA route
      change, and no runtime call.
    </p>
    <ul class="ghub-links" data-testid="governance-hub-cross-link-list">
      <li v-for="link in crossLinks" :key="link.target" :data-link-target="link.target">
        <button
          type="button"
          class="ghub-link-btn"
          :data-testid="`governance-hub-cross-link-${link.target}`"
          :aria-label="`${link.label} — opens the ${link.target} Dev Console section`"
          @click="onNavigate(link.target)"
        >
          <span class="ghub-link-btn__body">
            <span class="ghub-link-btn__label">{{ link.label }}</span>
            <span class="ghub-link-btn__detail">{{ link.detail }}</span>
          </span>
          <ArrowRight :size="14" aria-hidden="true" />
        </button>
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
.ghub-links {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-2, 8px) var(--space-3, 12px);
}
.ghub-link-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  background: var(--color-surface, #101015);
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  text-align: left;
  cursor: pointer;
}
.ghub-link-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.ghub-link-btn:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.ghub-link-btn__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.ghub-link-btn__label {
  font-weight: 600;
  font-size: var(--font-size-sm, 13px);
}
.ghub-link-btn__detail {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.45;
}
</style>
