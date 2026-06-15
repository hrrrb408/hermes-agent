<script setup lang="ts">
import { computed } from 'vue'
import ProviderRoundtripPanel from '@/components/workspace/ProviderRoundtripPanel.vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import BlockedReasonPanel from '@/components/common/BlockedReasonPanel.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

/**
 * Dev Console → Provider Round-trip section (Phase 2E).
 *
 * Reuses the existing ProviderRoundtripPanel and adds:
 *   - a result→audit cross-reference strip (provider audit ids), and
 *   - a unified BlockedReasonPanel when the round-trip is blocked.
 * The fake provider is an offline deterministic adapter; real mode is blocked
 * by design. The UI never accepts an API key.
 */
const store = useToolProviderStore()
const nav = useDevConsoleNavStore()

const providerAuditIds = computed(() => store.result?.providerAuditIds ?? [])

async function locate(id: string): Promise<void> {
  await nav.prefillAuditSearch(id)
}
</script>

<template>
  <section class="devconsole-section" aria-label="Provider Round-trip">
    <div class="devconsole-section__intro">
      <h2>Provider Round-trip</h2>
      <p>
        Controlled provider schema / API integration. The fake provider is a
        deterministic offline adapter (no external network). Real provider mode
        is blocked by default and requires explicit enablement plus a dev-home +
        PID gate. The provider may request write previews but never auto-execute
        or auto-rollback a write. No API key input is ever accepted by the UI.
      </p>
    </div>

    <ProviderRoundtripPanel />

    <BlockedReasonPanel
      v-if="store.result?.blockedReason"
      :code="store.result.blockedReason"
    />

    <div v-if="providerAuditIds.length > 0" class="devconsole-crossnav" aria-label="Cross-reference to Audit Viewer">
      <h3 class="devconsole-crossnav__title">Provider audit records</h3>
      <div class="devconsole-crossnav__items">
        <AuditIdLink
          v-for="id in providerAuditIds"
          :id="id"
          :key="id"
          label="provider audit"
          @navigate="locate"
        />
      </div>
    </div>
  </section>
</template>
