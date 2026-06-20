<script setup lang="ts">
/**
 * Dev Console → Human Review Governance section (Phase 3K).
 *
 * A read-only WebUI surface that unifies the P0 human-review / approval picture
 * across the Phase 3 capability chain. It projects — from frozen static data
 * only — the 24-gate summary, the gate list with client-side filters, the
 * per-gate human-review detail, the evidence trail, the frozen NO-GO decision,
 * and the Runtime-Governance↔Human-Review relationship.
 *
 * It performs NO approval, NO authorization, NO signoff, NO resolution, NO
 * override, NO production rollout, NO execution, NO plugin loading, NO route
 * change, NO file or network access, and NO production access. There is no
 * Approve / Reject / Authorize / Sign off / Resolve / Override / Enable / Run /
 * Execute / Batch / Upload / Fetch control, no API-key input, no secret input,
 * no file picker, and no JSON execution input. The only controls are harmless
 * UI-only selects: filtering gates, inspecting a gate, and copying a gate id.
 *
 * No new HTTP route is introduced: this is a client-side section inside the
 * existing /console view, served by already-approved static data.
 */
import { computed, ref } from 'vue'
import HumanReviewBoundaryBanner from './HumanReviewBoundaryBanner.vue'
import HumanReviewGateTable from './HumanReviewGateTable.vue'
import HumanReviewGateDetail from './HumanReviewGateDetail.vue'
import HumanReviewEvidenceTrail from './HumanReviewEvidenceTrail.vue'
import HumanReviewNogoPanel from './HumanReviewNogoPanel.vue'
import PluginRuntimeDisabledBanner from './PluginRuntimeDisabledBanner.vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import {
  buildHumanReviewViewModel,
  buildHumanReviewSummaryCards,
  buildHumanReviewStatusBadges,
  buildHumanReviewBoundaryItems,
  buildHumanReviewForbiddenActions,
  buildHumanReviewAllowedUiActions,
  filterHumanReviewGates,
  findHumanReviewGate,
  HUMAN_REVIEW_FILTER_OPTIONS,
  DEFAULT_GATE_ID,
} from '@/lib/humanReviewGovernanceViewModel'
import type { HumanReviewFilterKey } from '@/types/api/humanReviewGovernance'

const viewModel = buildHumanReviewViewModel()
const summaryCards = buildHumanReviewSummaryCards()
const statusBadges = buildHumanReviewStatusBadges()
const boundaryItems = buildHumanReviewBoundaryItems()
const forbiddenActions = buildHumanReviewForbiddenActions()
const allowedUiActions = buildHumanReviewAllowedUiActions()

/** Harmless UI-only state: which client-side filter is active. */
const activeFilter = ref<HumanReviewFilterKey>('all')
/** Harmless UI-only state: which gate's read-only detail to inspect. */
const selectedGateId = ref<string>(DEFAULT_GATE_ID)

const filteredGates = computed(() => filterHumanReviewGates(activeFilter.value))
const selectedGate = computed(() => findHumanReviewGate(selectedGateId.value))

function onSelectFilter(key: HumanReviewFilterKey): void {
  activeFilter.value = key
}

function onSelectGate(gateId: string): void {
  selectedGateId.value = gateId
}
</script>

<template>
  <section
    class="devconsole-section"
    aria-label="Human Review Governance"
    data-testid="human-review-governance-section"
  >
    <div class="devconsole-section__intro">
      <h1>Human Review Governance</h1>
      <ul
        class="hrgov-status-badges"
        data-testid="human-review-status-badges"
        aria-label="Human Review Governance status"
      >
        <li
          v-for="badge in statusBadges"
          :key="badge.label"
          class="hrgov-status-badge"
          :data-status-badge="badge.label"
        >
          {{ badge.label }}
        </li>
      </ul>
      <p>
        A read-only projection of the P0 human-review / approval picture. It
        <strong>displays only — it does not approve gates, does not authorize a
        runtime, does not resolve P0, does not enable production, and does not add
        a backend route</strong>. Every gate is unresolved; the resolved count is
        frozen at 0; every authorization verdict is frozen NO-GO /
        not-authorized. Code evidence is partial evidence only — valid approval
        requires an out-of-band trusted human process the dev skeleton cannot
        produce.
      </p>
    </div>

    <HumanReviewBoundaryBanner
      :items="boundaryItems"
      :decisions="viewModel.nogoDecisions"
    />

    <PluginRuntimeDisabledBanner />

    <StatusSummaryCards :cards="summaryCards" />

    <div class="devconsole-card" data-testid="human-review-filter-toolbar">
      <h2>Filter gates</h2>
      <p class="hrgov-muted">
        Client-side filters over static data only — selecting a filter performs no
        fetch and calls no backend.
      </p>
      <div class="hrgov-filters" role="group" aria-label="Filter P0 gates">
        <button
          v-for="opt in HUMAN_REVIEW_FILTER_OPTIONS"
          :key="opt.key"
          type="button"
          class="hrgov-filter-btn"
          :class="{ 'hrgov-filter-btn--active': activeFilter === opt.key }"
          :aria-pressed="activeFilter === opt.key"
          :data-testid="`human-review-filter-${opt.key}`"
          :data-filter-count="filterHumanReviewGates(opt.key).length"
          @click="onSelectFilter(opt.key)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <HumanReviewGateTable
      :gates="filteredGates"
      :selected-id="selectedGateId"
      @select="onSelectGate"
    />

    <HumanReviewGateDetail :gate="selectedGate" />

    <HumanReviewEvidenceTrail :sources="viewModel.evidenceTrail" />

    <HumanReviewNogoPanel
      :decisions="viewModel.nogoDecisions"
      :relationship="viewModel.runtimeRelationship"
    />

    <div class="devconsole-card" data-testid="human-review-actions-panel">
      <h2>What the WebUI can and cannot do</h2>
      <div class="hrgov-actions">
        <div class="hrgov-actions__group">
          <h3>Allowed (read-only)</h3>
          <ul class="hrgov-tags hrgov-tags--ok" data-testid="human-review-allowed-actions">
            <li v-for="action in allowedUiActions" :key="action" :data-allowed-action="action">
              {{ action }}
            </li>
          </ul>
        </div>
        <div class="hrgov-actions__group">
          <h3>Forbidden (never offered)</h3>
          <ul class="hrgov-tags hrgov-tags--ban" data-testid="human-review-forbidden-actions-global">
            <li v-for="action in forbiddenActions" :key="action" :data-forbidden-action="action">
              {{ action }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div class="devconsole-card" data-testid="human-review-route-governance">
      <h2>Route governance status</h2>
      <dl class="hrgov-dl">
        <div class="hrgov-dl__row">
          <dt>Frozen baseline</dt>
          <dd><code>{{ viewModel.routeGovernanceBaseline }}</code></dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Shape</dt>
          <dd>OpenAPI / Runtime / Tool GET / Tool write / dry-run / execute</dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Backend routes changed</dt>
          <dd :data-flag="`backendRoutesChanged-${viewModel.backendRoutesChanged}`">
            {{ viewModel.backendRoutesChanged ? 'yes' : 'no' }}
          </dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>New HTTP route</dt>
          <dd>0</dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>New runtime / plugin route</dt>
          <dd>0</dd>
        </div>
      </dl>
      <p class="hrgov-muted">
        No backend route was added for this section. It is a client-side view
        inside the existing /console page.
      </p>
    </div>
  </section>
</template>

<style scoped>
.hrgov-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.hrgov-status-badges {
  list-style: none;
  margin: 0 0 var(--space-2, 8px);
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.hrgov-status-badge {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  background: var(--color-surface, #101015);
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-xs, 12px);
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}
.hrgov-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.hrgov-filter-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.hrgov-filter-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.hrgov-filter-btn:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.hrgov-filter-btn--active {
  border-color: var(--color-accent, #6f8cff);
  background: var(--color-surface-raised, #1c1c24);
}
.hrgov-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.hrgov-actions__group h3 {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-tags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.hrgov-tags li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
}
.hrgov-tags--ok li {
  color: var(--color-success, #6ec48e);
}
.hrgov-tags--ban li {
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-dl {
  margin: 0 0 var(--space-2, 8px);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.hrgov-dl__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.hrgov-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  text-align: right;
}
</style>
