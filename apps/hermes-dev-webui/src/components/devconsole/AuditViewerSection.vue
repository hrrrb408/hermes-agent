<script setup lang="ts">
import { computed } from 'vue'
import AuditViewerPanel from '@/components/workspace/AuditViewerPanel.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

/**
 * Dev Console → Audit Viewer section (Phase 2E).
 *
 * Reuses the existing AuditViewerPanel (Phase 2D durable store: store-mode
 * toggle, filters, cursor pagination, store/index status, redaction badge).
 * The result→audit cross-navigation target: when another section calls
 * `prefillAuditSearch`, the shared toolAudit store is switched to store mode,
 * the search filter is set, and the query is fired — so this panel reactively
 * shows the located event.
 */
const nav = useDevConsoleNavStore()

const prefill = computed(() => nav.pendingAuditPrefill)

function clearPrefill(): void {
  nav.clearPendingPrefill()
}
</script>

<template>
  <section class="devconsole-section" aria-label="Audit Viewer">
    <div class="devconsole-section__intro">
      <h2>Audit Viewer</h2>
      <p>
        Read-only dev audit trail. Raw tokens, full token hashes, raw arguments,
        secrets, and callable reprs are never surfaced — every event is
        sanitized before display. Toggle the durable store to filter by event
        type, status, provider mode, write-required, and safe substring search,
        with opaque cursor pagination.
      </p>
    </div>

    <div v-if="prefill" class="devconsole-card" role="status" aria-live="polite">
      <h3>Located via cross-reference</h3>
      <p class="devconsole-note">
        Filtered to: <code>{{ prefill }}</code>
      </p>
      <button type="button" class="panel-retry-btn" data-testid="dev-audit-clear-prefill" @click="clearPrefill">
        Clear filter focus
      </button>
    </div>

    <AuditViewerPanel />
  </section>
</template>
