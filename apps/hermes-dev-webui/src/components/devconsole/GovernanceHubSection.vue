<script setup lang="ts">
/**
 * Dev Console → Governance Hub section (Phase 3L).
 *
 * A read-only unified control center that summarizes the governance state already
 * surfaced by the Runtime Governance (Phase 3J) and Human Review Governance
 * (Phase 3K) sections. It projects — from frozen static data only — the
 * governance summary, the module status board, the P0 / human-review summary,
 * the route-governance counts, the production-safety boundary, the evidence
 * trail, the frozen NO-GO decision, and the deferred / still-not-authorized list.
 *
 * It performs NO approval, NO authorization, NO signoff, NO resolution, NO
 * override, NO production rollout, NO execution, NO plugin loading, NO route
 * change, NO file or network access, and NO production access. There is no
 * Approve / Reject / Authorize / Sign off / Resolve / Override / Enable / Run /
 * Execute / Batch / Upload / Load / Fetch control, no API-key input, no secret
 * input, no file picker, and no JSON execution input. The only controls are
 * harmless UI-only selects: filtering modules, inspecting a module, viewing the
 * cross-linked sections, and copying a read-only summary to the clipboard.
 *
 * No new HTTP route is introduced: this is a client-side section inside the
 * existing /console view, served by already-approved static data.
 */
import { ref } from 'vue'
import GovernanceHubBoundaryBanner from './GovernanceHubBoundaryBanner.vue'
import GovernanceHubTargetACompletion from './GovernanceHubTargetACompletion.vue'
import GovernanceHubModuleBoard from './GovernanceHubModuleBoard.vue'
import GovernanceHubRoutePanel from './GovernanceHubRoutePanel.vue'
import GovernanceHubProductionSafetyPanel from './GovernanceHubProductionSafetyPanel.vue'
import GovernanceHubEvidenceTrail from './GovernanceHubEvidenceTrail.vue'
import GovernanceHubNogoPanel from './GovernanceHubNogoPanel.vue'
import GovernanceHubDeferredPanel from './GovernanceHubDeferredPanel.vue'
import GovernanceHubCrossLinks from './GovernanceHubCrossLinks.vue'
import PluginRuntimeDisabledBanner from './PluginRuntimeDisabledBanner.vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import {
  buildGovernanceHubViewModel,
  buildGovernanceHubSummaryCards,
  buildGovernanceHubStatusBadges,
  buildGovernanceHubBoundaryItems,
  buildGovernanceHubForbiddenActions,
  buildGovernanceHubAllowedUiActions,
  buildGovernanceHubSummaryText,
} from '@/lib/governanceHubViewModel'

const viewModel = buildGovernanceHubViewModel()
const summaryCards = buildGovernanceHubSummaryCards()
const statusBadges = buildGovernanceHubStatusBadges()
const boundaryItems = buildGovernanceHubBoundaryItems()
const forbiddenActions = buildGovernanceHubForbiddenActions()
const allowedUiActions = buildGovernanceHubAllowedUiActions()

const nav = useDevConsoleNavStore()

/** Harmless UI-only state: copy feedback (copied / unavailable / idle). */
const copyState = ref<'idle' | 'copied' | 'unavailable'>('idle')

function onNavigate(target: 'runtimeGovernance' | 'humanReview'): void {
  // Client-only section switch — no backend call, no SPA route change.
  nav.setSection(target)
}

async function onCopySummary(): Promise<void> {
  const text = buildGovernanceHubSummaryText()
  try {
    const clipboard = (globalThis.navigator as { clipboard?: { writeText?(t: string): Promise<void> } } | undefined)?.clipboard
    if (!clipboard || typeof clipboard.writeText !== 'function') {
      copyState.value = 'unavailable'
      return
    }
    await clipboard.writeText(text)
    copyState.value = 'copied'
  } catch {
    copyState.value = 'unavailable'
  }
}
</script>

<template>
  <section
    class="devconsole-section"
    aria-label="Governance Hub"
    data-testid="governance-hub-section"
  >
    <div class="devconsole-section__intro">
      <h1>Governance Hub</h1>
      <ul
        class="ghub-status-badges"
        data-testid="governance-hub-status-badges"
        aria-label="Governance Hub status"
      >
        <li
          v-for="badge in statusBadges"
          :key="badge.label"
          class="ghub-status-badge"
          :data-status-badge="badge.label"
        >
          {{ badge.label }}
        </li>
      </ul>
      <p>
        A unified read-only control center. It <strong>summarizes governance state
        only — it cannot execute a runtime, cannot approve gates, cannot authorize
        production, and cannot change routes</strong>. Every P0 count is frozen
        (resolved 0, partial 19, pending 5); every authorization verdict is frozen
        NO-GO / not-authorized; every route count is frozen unchanged
        (34/34/5/0/1/1).
      </p>
      <div class="ghub-intro-actions">
        <button
          type="button"
          class="ghub-copy-btn"
          :data-copy-state="copyState"
          data-testid="governance-hub-copy-summary"
          @click="onCopySummary"
        >
          {{ copyState === 'copied' ? 'Copied' : copyState === 'unavailable' ? 'Unavailable' : 'Copy summary text' }}
        </button>
      </div>
    </div>

    <GovernanceHubBoundaryBanner
      :items="boundaryItems"
      :decisions="viewModel.decisionRows"
    />

    <GovernanceHubTargetACompletion />

    <PluginRuntimeDisabledBanner />

    <StatusSummaryCards :cards="summaryCards" />

    <GovernanceHubModuleBoard
      :modules="viewModel.modules"
      @navigate="onNavigate"
    />

    <div class="devconsole-card" data-testid="governance-hub-p0-summary">
      <h2>P0 / human review summary</h2>
      <p class="ghub-muted">
        The 24 frozen P0 gates: none resolved, 19 with partial code evidence, 5
        blocked by human review. The five pending gates (P0-15, P0-16, P0-18,
        P0-19, P0-22) can only advance via an out-of-band human approval the dev
        skeleton cannot produce.
      </p>
      <dl class="ghub-dl">
        <div class="ghub-dl__row" data-p0-key="total">
          <dt>Total P0 gates</dt>
          <dd>{{ viewModel.summary.p0Total }}</dd>
        </div>
        <div class="ghub-dl__row" data-p0-key="resolved">
          <dt>Resolved / approved</dt>
          <dd :data-p0-value="viewModel.summary.p0Resolved">{{ viewModel.summary.p0Resolved }}</dd>
        </div>
        <div class="ghub-dl__row" data-p0-key="partial">
          <dt>Partial evidence</dt>
          <dd>{{ viewModel.summary.p0Partial }}</dd>
        </div>
        <div class="ghub-dl__row" data-p0-key="pending">
          <dt>Pending human review</dt>
          <dd :data-p0-value="viewModel.summary.p0PendingHumanReview">{{ viewModel.summary.p0PendingHumanReview }}</dd>
        </div>
        <div class="ghub-dl__row" data-p0-key="blocked">
          <dt>Blocked by human review</dt>
          <dd>{{ viewModel.summary.p0PendingHumanReview }}</dd>
        </div>
        <div class="ghub-dl__row" data-p0-key="pendingGates">
          <dt>Pending gates</dt>
          <dd>P0-15 / P0-16 / P0-18 / P0-19 / P0-22</dd>
        </div>
      </dl>
    </div>

    <GovernanceHubRoutePanel
      :route="viewModel.routeSummary"
      :baseline="viewModel.routeGovernanceBaseline"
      :backend-routes-changed="viewModel.backendRoutesChanged"
    />

    <GovernanceHubProductionSafetyPanel :safety="viewModel.productionSafety" />

    <GovernanceHubEvidenceTrail :sources="viewModel.evidenceTrail" />

    <GovernanceHubNogoPanel :decisions="viewModel.decisionRows" />

    <GovernanceHubDeferredPanel :items="viewModel.deferredItems" />

    <div class="devconsole-card" data-testid="governance-hub-actions-panel">
      <h2>What the WebUI can and cannot do</h2>
      <div class="ghub-actions">
        <div class="ghub-actions__group">
          <h3>Allowed (read-only)</h3>
          <ul class="ghub-tags ghub-tags--ok" data-testid="governance-hub-allowed-actions">
            <li v-for="action in allowedUiActions" :key="action" :data-allowed-action="action">
              {{ action }}
            </li>
          </ul>
        </div>
        <div class="ghub-actions__group">
          <h3>Forbidden (never offered)</h3>
          <ul class="ghub-tags ghub-tags--ban" data-testid="governance-hub-forbidden-actions-global">
            <li v-for="action in forbiddenActions" :key="action" :data-forbidden-action="action">
              {{ action }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <GovernanceHubCrossLinks :cross-links="viewModel.crossLinks" @navigate="onNavigate" />
  </section>
</template>

<style scoped>
.ghub-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.ghub-status-badges {
  list-style: none;
  margin: 0 0 var(--space-2, 8px);
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.ghub-status-badge {
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
.ghub-intro-actions {
  margin-top: var(--space-2, 8px);
}
.ghub-copy-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.ghub-copy-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.ghub-copy-btn:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.ghub-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.ghub-actions__group h3 {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
.ghub-tags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.ghub-tags li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
}
.ghub-tags--ok li {
  color: var(--color-success, #6ec48e);
}
.ghub-tags--ban li {
  color: var(--color-text-muted, #8a8a94);
}
.ghub-dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-dl__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.ghub-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.ghub-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  text-align: right;
}
</style>
