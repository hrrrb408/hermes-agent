<script setup lang="ts">
import { computed, onMounted } from 'vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import SafetyBadgeBar from './SafetyBadgeBar.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import { useToolPolicyStore } from '@/stores/toolPolicy'
import { useToolAuditStore } from '@/stores/toolAudit'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import { FROZEN_ROUTE_GOVERNANCE, FROZEN_PRODUCTION_GATEWAY_PID, FROZEN_RELEASE_IDS } from '@/lib/frozenBaseline'
import { formatTimestamp } from '@/lib/formatters'

/**
 * Dev Console → Overview dashboard (Phase 2E).
 *
 * The at-a-glance landing surface. Sources:
 *   - LIVE: GET /tools/policy (inventory, risk distribution, safety flags) via
 *     the policy store, and GET /tools/audit-events store-mode (store + index
 *     health) via the audit store. Both are read-only GETs — no execution, no
 *     confirmation tokens, no audit pollution.
 *   - FROZEN: route governance baseline, production PID, phase timeline.
 *
 * Makes NO POST calls. The vitest suite asserts this.
 */
const policy = useToolPolicyStore()
const audit = useToolAuditStore()
const nav = useDevConsoleNavStore()

onMounted(async () => {
  if (policy.policyState === 'idle') {
    void policy.loadPolicy()
  }
  if (audit.state === 'idle') {
    // Fetch the durable-store health (storeStatus / indexStatus) WITHOUT
    // flipping the user-visible storeMode flag — loadStoreEvents populates the
    // status from the V2 response regardless of storeMode, so the Overview does
    // not alter the Audit Viewer's chosen view mode.
    void audit.loadStoreEvents()
  }
})

const isLoading = computed(() => policy.isPolicyLoading && audit.isLoading === false && policy.policy === null)
const hasError = computed(() => policy.policyState === 'error')

const summaryCards = computed(() => {
  const cards: { label: string; value: string | number; sub?: string; tone?: 'ok' | 'warn' | 'danger' | 'info' }[] = [
    {
      label: 'Phase 1G',
      value: FROZEN_RELEASE_IDS.phase1gStatus,
      sub: `Phase 2 ${FROZEN_RELEASE_IDS.phase2Status}`,
      tone: 'ok',
    },
    {
      label: 'Phase 2E',
      value: 'In progress',
      sub: 'Frontend UX polish',
      tone: 'info',
    },
    {
      label: 'OpenAPI / runtime routes',
      value: `${FROZEN_ROUTE_GOVERNANCE.openApiPaths} / ${FROZEN_ROUTE_GOVERNANCE.runtimeRoutes}`,
      sub: `tool GET ${FROZEN_ROUTE_GOVERNANCE.toolGetRoutes} · write route ${FROZEN_ROUTE_GOVERNANCE.toolWriteRoutes}`,
      tone: 'ok',
    },
    {
      label: 'Tool dry-run / execute',
      value: `${FROZEN_ROUTE_GOVERNANCE.toolDryRunRoutes} / ${FROZEN_ROUTE_GOVERNANCE.toolExecutionRoutes}`,
      sub: 'No dedicated write HTTP route',
      tone: 'ok',
    },
    {
      label: 'Production gateway',
      value: `PID ${FROZEN_PRODUCTION_GATEWAY_PID}`,
      sub: 'Untouched (read-only)',
      tone: 'ok',
    },
    {
      label: 'Provider mode',
      value: 'Fake (offline)',
      sub: 'Real blocked by default',
      tone: 'warn',
    },
    {
      label: 'Write enablement',
      value: 'Sandbox only',
      sub: 'Requires env gate',
      tone: 'warn',
    },
  ]

  if (policy.policy) {
    cards.push({
      label: 'Tool inventory',
      value: policy.policy.inventoryCount,
      sub: `${policy.policy.candidateAllowlistCount} candidates · ${policy.policy.permanentDenylistCount} denied`,
      tone: 'info',
    })
  }

  if (audit.storeStatus) {
    cards.push({
      label: 'Audit store',
      value: audit.storeStatus.present ? 'Present' : 'Absent',
      sub: `${audit.storeStatus.segmentCount} segment(s) · dev-only`,
      tone: audit.storeStatus.present ? 'ok' : 'warn',
    })
  }
  if (audit.indexStatus) {
    cards.push({
      label: 'Audit index',
      value: audit.indexStatus.consistent && !audit.indexStatus.stale ? 'Consistent' : 'Stale',
      sub: `${audit.indexStatus.eventCount} event(s) indexed`,
      tone: audit.indexStale ? 'warn' : 'ok',
    })
  }

  return cards
})

const recentEvents = computed(() => (audit.storeItems ?? []).slice(0, 5))
const recentBlocked = computed(() =>
  (audit.storeItems ?? []).filter((i) => i.status === 'blocked' || !!i.blockedReason).slice(0, 3),
)

async function locate(id: string): Promise<void> {
  await nav.prefillAuditSearch(id)
}
</script>

<template>
  <section class="devconsole-section" aria-label="Overview">
    <div class="devconsole-section__intro">
      <h2>Overview</h2>
      <p>
        Unified developer console for the Hermes dev instance. The dashboard
        surfaces the current safety status, the available tool surface, the
        provider mode, write enablement, and audit-store health — all sourced
        from read-only endpoints, with no production access.
      </p>
    </div>

    <SafetyBadgeBar />

    <LoadingState v-if="isLoading" message="Loading dev console status…" />
    <ErrorState
      v-else-if="hasError"
      :message="policy.policyError || 'Failed to load tool policy.'"
      @retry="policy.retryPolicy()"
    />

    <StatusSummaryCards v-if="summaryCards.length > 0" :cards="summaryCards" />

    <div class="devconsole-card">
      <h3>Next safe actions</h3>
      <ul class="devconsole-note" style="margin:0; padding-left: var(--space-4, 16px); line-height: 1.7;">
        <li>Run a read-only tool in <strong>Tool Execution</strong> (dry-run → confirm → execute).</li>
        <li>Try a <strong>Provider Round-trip</strong> in fake mode (offline, deterministic).</li>
        <li>Preview a sandbox write in <strong>Sandbox Write &amp; Rollback</strong>, then roll it back.</li>
        <li>Inspect the durable audit trail in <strong>Audit Viewer</strong> with filters + cursor pagination.</li>
      </ul>
    </div>

    <div v-if="recentEvents.length > 0" class="devconsole-card">
      <h3>Recent executions</h3>
      <div class="devconsole-crossnav__items" aria-label="Recent audit events">
        <div v-for="ev in recentEvents" :key="ev.eventId ?? ev.sequence ?? ''" class="devconsole-summary__card" style="flex-direction: column; display: flex; gap: 2px; min-width: 180px;">
          <span class="devconsole-summary__label">{{ ev.eventType ?? ev.auditKind ?? 'event' }}</span>
          <span class="devconsole-summary__value" style="font-size: var(--font-size-xs, 0.75rem);">{{ formatTimestamp(ev.createdAt) }}</span>
          <AuditIdLink :id="ev.eventId" label="id" @navigate="locate" />
        </div>
      </div>
    </div>

    <div v-if="recentBlocked.length > 0" class="devconsole-card" role="status">
      <h3>Recent blocked events</h3>
      <ul class="devconsole-note" style="margin:0; padding-left: var(--space-4, 16px);">
        <li v-for="ev in recentBlocked" :key="ev.eventId ?? ev.sequence ?? ''">
          {{ ev.eventType ?? 'event' }} — {{ ev.blockedReason ?? ev.status }}
          <span v-if="ev.toolId">({{ ev.toolId }})</span>
        </li>
      </ul>
    </div>
  </section>
</template>
