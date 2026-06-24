<script setup lang="ts">
/**
 * Governance Hub module status board (Phase 3L).
 *
 * Read-only projection of the Phase 3 capability-chain governance modules. Each
 * module carries its phase, lifecycle status, a read-only evidence summary, a
 * frozen route impact (no new route), a frozen production impact (no production
 * authorization), a frozen authorization impact (NO-GO), and a read-only flag.
 * Two modules cross-link to an existing client-side section.
 *
 * There is no execution, no approval, and no route change here. The only controls
 * are harmless client-side status filters and an Inspect toggle (operates on
 * static data only — never fetches, never calls the backend / runtime / CLI).
 */
import { ref } from 'vue'
import { ArrowUpRight, ShieldX } from '@lucide/vue'
import type { GovernanceModuleStatus, GovernanceModuleLifecycle } from '@/types/api/governanceHub'
import {
  GOVERNANCE_HUB_MODULE_FILTER_OPTIONS,
  type GovernanceModuleFilterKey,
} from '@/lib/governanceHubViewModel'

const props = defineProps<{
  modules: readonly GovernanceModuleStatus[]
}>()

/** Harmless UI-only state: which client-side status filter is active. */
const activeFilter = ref<GovernanceModuleFilterKey>('all')
/** Harmless UI-only state: which module's read-only detail to expand. */
const selectedKey = ref<string>('governanceHub')

function onSelectFilter(key: GovernanceModuleFilterKey): void {
  activeFilter.value = key
}

function onSelectModule(key: string): void {
  selectedKey.value = key
}

/**
 * Emit a request to open a cross-linked section. The parent wires this to the
 * devConsoleNav store (a client-only section switch — never a backend / SPA
 * route change). Only emitted for modules that declare a linkTargetSection.
 */
const emit = defineEmits<{
  (e: 'navigate', target: 'runtimeGovernance' | 'humanReview'): void
}>()

function onNavigate(target: GovernanceModuleLifecycle | string | undefined): void {
  if (target === 'runtimeGovernance' || target === 'humanReview') {
    emit('navigate', target)
  }
}

const filtered = () => {
  if (activeFilter.value === 'all') return props.modules
  return props.modules.filter((m) => m.status === activeFilter.value)
}
</script>

<template>
  <div class="devconsole-card" data-testid="governance-hub-module-board">
    <h2>Governance module status board</h2>
    <p class="ghub-muted">
      The Phase 3 capability chain. Every module authorizes no production, adds no
      route, and is read-only. Client-side status filters operate on static data
      only.
    </p>
    <div class="ghub-filters" role="group" aria-label="Filter governance modules">
      <button
        v-for="opt in GOVERNANCE_HUB_MODULE_FILTER_OPTIONS"
        :key="opt.key"
        type="button"
        class="ghub-filter-btn"
        :class="{ 'ghub-filter-btn--active': activeFilter === opt.key }"
        :aria-pressed="activeFilter === opt.key"
        :data-testid="`governance-hub-module-filter-${opt.key}`"
        @click="onSelectFilter(opt.key)"
      >
        {{ opt.label }}
      </button>
    </div>

    <div class="ghub-board-scroll" role="region" aria-label="Governance module rows" tabindex="0">
      <table class="ghub-board" data-testid="governance-hub-module-table">
        <caption class="ghub-board__caption">
          Governance modules (read-only). Columns: module, phase, status, evidence
          summary, route impact, production impact, authorization impact.
        </caption>
        <thead>
          <tr>
            <th scope="col">Module</th>
            <th scope="col">Phase</th>
            <th scope="col">Status</th>
            <th scope="col">Evidence summary</th>
            <th scope="col">Route impact</th>
            <th scope="col">Production impact</th>
            <th scope="col">Authorization</th>
            <th scope="col"><span class="ghub-sr">Inspect</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in filtered()"
            :key="m.key"
            :data-module-key="m.key"
            :data-module-status="m.status"
            :aria-selected="selectedKey === m.key"
          >
            <td>
              <span class="ghub-board__name">{{ m.name }}</span>
              <button
                v-if="m.linkTargetSection"
                type="button"
                class="ghub-board__link"
                :data-testid="`governance-hub-module-link-${m.key}`"
                :aria-label="`View ${m.linkTargetSection} section`"
                @click="onNavigate(m.linkTargetSection)"
              >
                <ArrowUpRight :size="12" aria-hidden="true" />
                View
              </button>
            </td>
            <td><span class="ghub-board__phase">{{ m.phase }}</span></td>
            <td><span class="ghub-board__status" :data-status="m.status">{{ m.status }}</span></td>
            <td class="ghub-board__evidence">{{ m.evidenceSummary }}</td>
            <td>{{ m.routeImpact }}</td>
            <td>{{ m.productionImpact }}</td>
            <td>
              <span class="ghub-board__verdict" :data-verdict="m.authorizationImpact">
                <ShieldX :size="12" aria-hidden="true" />
                {{ m.authorizationImpact }}
              </span>
            </td>
            <td>
              <button
                type="button"
                class="ghub-inspect-btn"
                :class="{ 'ghub-inspect-btn--active': selectedKey === m.key }"
                :aria-pressed="selectedKey === m.key"
                :data-testid="`governance-hub-module-inspect-${m.key}`"
                @click="onSelectModule(m.key)"
              >
                {{ selectedKey === m.key ? 'Selected' : 'Inspect' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="ghub-muted ghub-board__footer">
      None of these modules authorizes production, executes a real plugin, or adds
      a backend route. Every module is read-only.
    </p>
  </div>
</template>

<style scoped>
.ghub-muted {
  margin: 0 0 var(--space-2, 8px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-sr {
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
.ghub-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-bottom: var(--space-3, 12px);
}
.ghub-filter-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.ghub-filter-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.ghub-filter-btn:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.ghub-filter-btn--active {
  border-color: var(--color-accent, #6f8cff);
  background: var(--color-surface-raised, #1c1c24);
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
  min-width: 720px;
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
.ghub-board__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  margin-left: var(--space-2, 8px);
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
.ghub-inspect-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.ghub-inspect-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.ghub-inspect-btn:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.ghub-inspect-btn--active {
  border-color: var(--color-accent, #6f8cff);
  background: var(--color-surface-raised, #1c1c24);
}
.ghub-board__footer {
  margin-top: var(--space-2, 8px);
}
</style>
