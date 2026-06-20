<script setup lang="ts">
/**
 * Human Review Governance gate table (Phase 3K).
 *
 * Read-only list of the frozen 24 P0 gates. Each row carries only safe metadata
 * and a single harmless "Inspect gate" action that opens the read-only detail
 * panel. There is NO Approve / Reject / Authorize / Sign off / Resolve /
 * Override / Run / Execute / Enable control — the WebUI approves nothing. Every
 * gate is unresolved (resolved=false, approved=false) and carries a production
 * authorization impact of NO-GO.
 */
import type { HumanReviewGate } from '@/types/api/humanReviewGovernance'

defineProps<{
  gates: readonly HumanReviewGate[]
  selectedId?: string | null
}>()

const emit = defineEmits<{ (e: 'select', gateId: string): void }>()
</script>

<template>
  <div class="devconsole-card" data-testid="human-review-gate-table">
    <h2>P0 gates</h2>
    <p class="hrgov-muted">
      The frozen 24-gate registry. Every gate is unresolved — 19 carry partial
      code/test evidence and 5 are pending human review. None is resolved, none is
      approved, and the production authorization impact of every gate is NO-GO.
    </p>
    <div class="hrgov-table-scroll" role="region" aria-label="P0 gates" tabindex="0">
      <table class="hrgov-table">
        <caption class="sr-only">
          P0 gates — 24 frozen gates, 19 partial evidence, 5 pending human review, 0 resolved.
        </caption>
        <thead>
          <tr>
            <th scope="col">Gate ID</th>
            <th scope="col">Title</th>
            <th scope="col">Category</th>
            <th scope="col">Status</th>
            <th scope="col">Evidence Level</th>
            <th scope="col">Requires Human Review</th>
            <th scope="col">Source Phase</th>
            <th scope="col">Blocked Reason</th>
            <th scope="col"><span class="sr-only">Inspect gate</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="g in gates"
            :key="g.gateId"
            :class="{ 'hrgov-row--selected': g.gateId === selectedId }"
            :aria-current="g.gateId === selectedId ? 'true' : undefined"
            :data-gate-id="g.gateId"
            :data-gate-status="g.status"
          >
            <th scope="row">
              <code class="hrgov-table__code">{{ g.gateId }}</code>
            </th>
            <td>{{ g.title }}</td>
            <td>{{ g.category }}</td>
            <td>
              <span class="hrgov-status" :data-status="g.status">{{ g.statusLabel }}</span>
            </td>
            <td :data-evidence-level="g.evidenceLevel">{{ g.evidenceLevel }}</td>
            <td :data-flag="`requiresHumanReview-${g.requiresHumanReview}`">
              {{ g.requiresHumanReview ? 'Yes' : 'No' }}
            </td>
            <td>{{ g.sourcePhase }}</td>
            <td class="hrgov-table__reason">{{ g.blockedReason }}</td>
            <td>
              <button
                type="button"
                class="hrgov-inspect-btn"
                :aria-pressed="g.gateId === selectedId"
                :aria-label="`Inspect gate ${g.gateId}`"
                :data-testid="`human-review-inspect-${g.gateId}`"
                @click="emit('select', g.gateId)"
              >
                Inspect
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.hrgov-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.hrgov-table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.hrgov-table-scroll:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
  border-radius: var(--radius-sm, 6px);
}
.hrgov-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
  min-width: 820px;
}
.hrgov-table th,
.hrgov-table td {
  border: 1px solid var(--color-border, #2a2a33);
  padding: var(--space-2, 8px);
  text-align: left;
  vertical-align: top;
}
.hrgov-table thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
}
.hrgov-table__code {
  font-family: var(--font-mono, ui-monospace, monospace);
}
.hrgov-table__reason {
  color: var(--color-text-muted, #8a8a94);
  max-width: 320px;
}
.hrgov-status {
  font-weight: 600;
}
.hrgov-status[data-status='blocked_by_human_review'] {
  color: var(--color-danger, #e0566a);
}
.hrgov-status[data-status='partial_evidence'] {
  color: var(--color-warning, #d9a441);
}
.hrgov-row--selected {
  background: var(--color-surface-raised, #1c1c24);
}
.hrgov-inspect-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.hrgov-inspect-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.hrgov-inspect-btn:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
