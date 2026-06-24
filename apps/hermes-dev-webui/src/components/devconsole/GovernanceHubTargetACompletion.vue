<script setup lang="ts">
/**
 * Governance Hub → Target A Completion region (Phase 3M).
 *
 * A read-only region inside the Governance Hub that states the **dev-only runtime
 * prototype** (Target A) is COMPLETE — in the dev-only sense ONLY — while every
 * production dimension stays NO-GO. It projects, from frozen static data only:
 *
 *   1. a Target A status banner (COMPLETE, dev-only / fixture-only / read-only
 *      governed, not production, P0 resolved 0, Target B NO-GO);
 *   2. Target A completion cards;
 *   3. the Target A capability matrix (the full Phase 3 capability chain);
 *   4. the Target A readiness checklist (every item pass — never production-ready);
 *   5. a Target A vs Target B boundary panel;
 *   6. the final dev-only prototype acceptance panel (why PASS, why not production).
 *
 * It performs NO approval, NO authorization, NO signoff, NO resolution, NO
 * override, NO production rollout, NO execution, NO plugin loading, NO route
 * change, NO file or network access, and NO production access. There is no
 * Approve / Reject / Authorize / Sign off / Resolve / Override / Enable / Run /
 * Execute / Batch / Upload / Load / Fetch control, no API-key input, no secret
 * input, no file picker, and no JSON execution input. The only controls are
 * harmless UI-only selects: viewing a cross-linked section and copying a
 * read-only Target A summary.
 *
 * Target A COMPLETE is NOT production runtime authorized, NOT P0 resolved, NOT
 * human review approved, NOT arbitrary plugin loading allowed, NOT WebUI
 * execution allowed, and NOT production rollout allowed. No new backend route is
 * introduced.
 */
import { ref } from 'vue'
import { CheckCircle2, Lock, ShieldCheck, ShieldX } from '@lucide/vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import {
  buildTargetACompletionViewModel,
  buildTargetASummaryText,
} from '@/lib/governanceHubViewModel'

const viewModel = buildTargetACompletionViewModel()
const nav = useDevConsoleNavStore()

/** Harmless UI-only state: copy feedback (copied / unavailable / idle). */
const copyState = ref<'idle' | 'copied' | 'unavailable'>('idle')

/** Linked sections the region may cross-link to (a client-only section switch). */
type LinkedSection = 'runtimeGovernance' | 'humanReview'

function onNavigate(target: string | undefined): void {
  if (target === 'runtimeGovernance' || target === 'humanReview') {
    // Client-only section switch — no backend call, no SPA route change.
    nav.setSection(target as LinkedSection)
  }
}

async function onCopySummary(): Promise<void> {
  const text = buildTargetASummaryText()
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
    class="devconsole-card target-a-region"
    aria-label="Target A Dev-only Runtime Prototype completion"
    data-testid="governance-hub-target-a-region"
  >
    <header class="target-a-region__header">
      <h2 data-testid="governance-hub-target-a-heading">
        Target A — Dev-only Runtime Prototype
      </h2>
      <p class="ghub-muted">
        The dev-only runtime prototype capability chain (Static Descriptor Registry
        → Runtime Binding → Fixture Runtime → CLI → read-only Runtime Governance
        WebUI → read-only Human Review Governance WebUI → unified read-only
        Governance Hub) is <strong>COMPLETE as a dev-only, fixture-only,
        read-only-governed prototype</strong>. This completion is <strong>not</strong>
        production authorization.
      </p>
    </header>

    <!-- 1. Target A status banner -->
    <div
      class="target-a-banner"
      data-testid="governance-hub-target-a-banner"
      role="group"
      aria-label="Target A status"
    >
      <div class="target-a-banner__verdict" data-target-a-verdict="COMPLETE">
        <CheckCircle2 :size="16" aria-hidden="true" />
        <span>Target A: COMPLETE</span>
      </div>
      <ul class="target-a-banner__lines" data-testid="governance-hub-target-a-banner-lines">
        <li :data-banner-line="'dev-only-runtime-prototype-complete'">
          Dev-only runtime prototype complete
        </li>
        <li :data-banner-line="'scope'">Dev-only / fixture-only / read-only governed</li>
        <li :data-banner-line="'not-production'">Not production runtime</li>
        <li :data-banner-line="'p0-resolved-0'">P0 resolved remains 0</li>
        <li :data-banner-line="'target-b-nogo'">Target B remains NO-GO</li>
      </ul>
      <div class="target-a-banner__copy">
        <button
          type="button"
          class="ghub-copy-btn"
          :data-copy-state="copyState"
          data-testid="governance-hub-target-a-copy-summary"
          @click="onCopySummary"
        >
          {{ copyState === 'copied' ? 'Copied' : copyState === 'unavailable' ? 'Unavailable' : 'Copy Target A summary' }}
        </button>
      </div>
    </div>

    <!-- 2. Target A completion cards -->
    <h3>Target A completion cards</h3>
    <StatusSummaryCards :cards="viewModel.completionCards" />

    <!-- 3. Capability matrix -->
    <div class="target-a-block" data-testid="governance-hub-target-a-capability-matrix">
      <h3>Target A capability matrix</h3>
      <p class="ghub-muted">
        The full Phase 3 capability chain. Every row contributes to Target A, adds
        no route, and authorizes no production. Target B impact is stated per row.
      </p>
      <div class="ghub-board-scroll" role="region" aria-label="Target A capability rows" tabindex="0">
        <table class="ghub-board" data-testid="governance-hub-target-a-capability-table">
          <caption class="ghub-board__caption">
            Target A capabilities (read-only). Columns: capability, phase, status,
            evidence, tests, route impact, production impact, Target A contribution,
            Target B impact.
          </caption>
          <thead>
            <tr>
              <th scope="col">Capability</th>
              <th scope="col">Phase</th>
              <th scope="col">Status</th>
              <th scope="col">Evidence</th>
              <th scope="col">Tests</th>
              <th scope="col">Route impact</th>
              <th scope="col">Production impact</th>
              <th scope="col">Target A</th>
              <th scope="col">Target B</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in viewModel.capabilityMatrix"
              :key="row.capability"
              :data-capability="row.capability"
              :data-contribution="row.targetAContribution"
            >
              <td><span class="ghub-board__name">{{ row.capability }}</span></td>
              <td><span class="ghub-board__phase">{{ row.phase }}</span></td>
              <td><span class="ghub-board__status" :data-status="row.status">{{ row.status }}</span></td>
              <td class="ghub-board__evidence">{{ row.evidence }}</td>
              <td class="ghub-board__evidence">{{ row.tests }}</td>
              <td>{{ row.routeImpact }}</td>
              <td>
                <span class="ghub-board__verdict" data-production-impact="forbidden">
                  <ShieldX :size="12" aria-hidden="true" />
                  {{ row.productionImpact }}
                </span>
              </td>
              <td><span :data-target-a-contribution="row.targetAContribution">{{ row.targetAContribution }}</span></td>
              <td class="ghub-board__evidence">{{ row.targetBImpact }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 4. Readiness checklist -->
    <div class="target-a-block" data-testid="governance-hub-target-a-readiness">
      <h3>Target A readiness checklist</h3>
      <p class="ghub-muted">
        Every Target A readiness item is pass. <strong>Production readiness remains
        NO-GO</strong> — these items prove the dev-only prototype is complete, not
        that the system is production-ready.
      </p>
      <ul class="target-a-checklist" data-testid="governance-hub-target-a-readiness-list">
        <li
          v-for="item in viewModel.readinessChecklist"
          :key="item.id"
          :data-readiness-id="item.id"
          :data-readiness-status="item.status"
        >
          <ShieldCheck :size="13" aria-hidden="true" />
          <div class="target-a-checklist__body">
            <span class="target-a-checklist__label">
              {{ item.label }}
              <strong class="target-a-checklist__status" :data-status="item.status">{{ item.status }}</strong>
            </span>
            <span class="target-a-checklist__evidence">{{ item.evidenceSummary }}</span>
          </div>
          <button
            v-if="item.linkedSection === 'runtimeGovernance' || item.linkedSection === 'humanReview'"
            type="button"
            class="ghub-board__link"
            :data-testid="`governance-hub-target-a-readiness-link-${item.id}`"
            :aria-label="`View ${item.linkedSection} section`"
            @click="onNavigate(item.linkedSection)"
          >
            View
          </button>
        </li>
      </ul>
    </div>

    <!-- 5. Target A vs Target B boundary -->
    <div class="target-a-block" data-testid="governance-hub-target-a-boundary">
      <h3>Target A vs Target B boundary</h3>
      <div class="target-a-boundary">
        <div class="target-a-boundary__col" data-testid="governance-hub-target-a-boundary-completed">
          <h4 class="target-a-boundary__title target-a-boundary__title--ok">
            Target A — complete
          </h4>
          <ul class="target-a-tags target-a-tags--ok">
            <li v-for="item in viewModel.boundaryCompleted" :key="item" :data-boundary-completed="item">
              <CheckCircle2 :size="12" aria-hidden="true" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
        <div class="target-a-boundary__col" data-testid="governance-hub-target-a-boundary-deferred">
          <h4 class="target-a-boundary__title target-a-boundary__title--ban">
            Target B — deferred / NO-GO
          </h4>
          <ul class="target-a-tags target-a-tags--ban">
            <li v-for="item in viewModel.boundaryDeferred" :key="item" :data-boundary-deferred="item">
              <Lock :size="12" aria-hidden="true" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 6. Final dev-only prototype acceptance -->
    <div class="target-a-block" data-testid="governance-hub-target-a-acceptance">
      <h3>Final dev-only prototype acceptance</h3>
      <p class="target-a-acceptance__verdict" data-testid="governance-hub-target-a-acceptance-verdict">
        <ShieldCheck :size="15" aria-hidden="true" />
        Target A acceptance:
        <strong :data-verdict="viewModel.acceptance.verdict">{{ viewModel.acceptance.verdict }}</strong>
        (dev-only prototype)
      </p>
      <div class="target-a-acceptance">
        <div class="target-a-acceptance__group">
          <h4 class="target-a-boundary__title target-a-boundary__title--ok">Why PASS</h4>
          <ul data-testid="governance-hub-target-a-acceptance-why-pass">
            <li v-for="(line, i) in viewModel.acceptance.whyPass" :key="i">{{ line }}</li>
          </ul>
        </div>
        <div class="target-a-acceptance__group">
          <h4 class="target-a-boundary__title target-a-boundary__title--ban">Why not production</h4>
          <ul data-testid="governance-hub-target-a-acceptance-why-not-production">
            <li v-for="(line, i) in viewModel.acceptance.whyNotProduction" :key="i">{{ line }}</li>
          </ul>
        </div>
      </div>
      <p class="ghub-muted target-a-block__footer">
        This acceptance is a dev-only prototype milestone. It is not a closeout, not
        a signoff, not an archive, and not production authorization. Production
        runtime, arbitrary plugin loading, remote registry, marketplace, external
        network, real API keys, WebUI execution, approval / authorization, and
        production rollout all remain NO-GO.
      </p>
    </div>
  </section>
</template>

<style scoped>
.target-a-region {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.target-a-region__header h2 {
  margin: 0 0 var(--space-2, 8px);
}
.target-a-region__header p {
  margin: 0;
}
.ghub-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
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
.target-a-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-3, 12px);
  background: var(--color-surface, #101015);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.target-a-banner__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  color: var(--color-success, #6ec48e);
  font-weight: 700;
  font-size: var(--font-size-base, 15px);
}
.target-a-banner__lines {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.target-a-banner__lines li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text, #e6e6ec);
}
.target-a-banner__copy {
  margin-top: var(--space-1, 4px);
}
.target-a-block h3 {
  margin: 0 0 var(--space-2, 8px);
}
.target-a-block p.ghub-muted {
  margin: 0 0 var(--space-2, 8px);
}
.target-a-block__footer {
  margin-top: var(--space-2, 8px);
}
.ghub-board-scroll {
  overflow-x: auto;
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
}
.ghub-board {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
  min-width: 820px;
}
.ghub-board__caption {
  text-align: left;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
}
.ghub-board th,
.ghub-board td {
  text-align: left;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-bottom: 1px solid var(--color-border, #2a2a33);
  vertical-align: top;
}
.ghub-board thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
  font-size: var(--font-size-xs, 12px);
}
.ghub-board__name {
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.ghub-board__phase {
  color: var(--color-text-muted, #8a8a94);
  white-space: nowrap;
}
.ghub-board__status {
  font-weight: 600;
  color: var(--color-success, #6ec48e);
}
.ghub-board__evidence {
  color: var(--color-text, #e6e6ec);
  line-height: 1.45;
}
.ghub-board__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  color: var(--color-danger, #e0566a);
  font-weight: 600;
}
.ghub-board__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: 1px var(--space-1, 4px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.ghub-board__link:hover {
  border-color: var(--color-accent, #6f8cff);
}
.ghub-board__link:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.target-a-checklist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.target-a-checklist li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
  color: var(--color-success, #6ec48e);
}
.target-a-checklist__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.target-a-checklist__label {
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.target-a-checklist__status {
  margin-left: var(--space-2, 8px);
  color: var(--color-success, #6ec48e);
  text-transform: uppercase;
}
.target-a-checklist__evidence {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
.target-a-boundary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.target-a-boundary__col {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.target-a-boundary__title {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.target-a-boundary__title--ok {
  color: var(--color-success, #6ec48e);
}
.target-a-boundary__title--ban {
  color: var(--color-danger, #e0566a);
}
.target-a-tags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.target-a-tags li {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
}
.target-a-tags--ok li {
  color: var(--color-text, #e6e6ec);
}
.target-a-tags--ban li {
  color: var(--color-text-muted, #8a8a94);
}
.target-a-acceptance__verdict {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-success, #6ec48e);
  font-size: var(--font-size-sm, 13px);
}
.target-a-acceptance__verdict strong {
  margin-left: var(--space-1, 4px);
}
.target-a-acceptance {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.target-a-acceptance__group {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.target-a-acceptance__group ul {
  margin: 0;
  padding-left: var(--space-4, 16px);
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.6;
}
</style>
