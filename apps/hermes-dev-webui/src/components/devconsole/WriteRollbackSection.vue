<script setup lang="ts">
import { computed } from 'vue'
import ToolWritePanel from '@/components/workspace/ToolWritePanel.vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import BlockedReasonPanel from '@/components/common/BlockedReasonPanel.vue'
import { useToolWriteStore } from '@/stores/toolWrite'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

/**
 * Dev Console → Sandbox Write & Rollback section (Phase 2E).
 *
 * Reuses the existing ToolWritePanel (which carries both the write preview /
 * execute flow and the rollback preview / execute flow) and adds:
 *   - a result→audit cross-reference strip (write + rollback audit ids, plus
 *     a pointer to the rollback manifest), and
 *   - unified BlockedReasonPanel surfaces for blocked write / rollback outcomes.
 * Writes operate only inside the dev sandbox; rollback reuses the write gate.
 */
const store = useToolWriteStore()
const nav = useDevConsoleNavStore()

const crossRefs = computed<{ id: string; label: string }[]>(() => {
  const out: { id: string; label: string }[] = []
  const w = store.executeResult
  if (w) {
    if (w.rollbackId) out.push({ id: w.rollbackId, label: 'rollback manifest' })
    if (w.postExecutionAuditId) out.push({ id: w.postExecutionAuditId, label: 'write post-exec audit' })
    if (w.preExecutionAuditId) out.push({ id: w.preExecutionAuditId, label: 'write pre-exec audit' })
  }
  const r = store.rollbackResult
  if (r) {
    if (r.postExecutionAuditId) out.push({ id: r.postExecutionAuditId, label: 'rollback post-exec audit' })
    if (r.preExecutionAuditId) out.push({ id: r.preExecutionAuditId, label: 'rollback pre-exec audit' })
  }
  return out
})

const writeBlocked = computed(() => store.executeResult?.blockedReason ?? store.preview?.blockedReason ?? null)
const rollbackBlocked = computed(() => store.rollbackResult?.blockedReason ?? store.rollbackPreview?.blockedReason ?? null)

async function locate(id: string): Promise<void> {
  await nav.prefillAuditSearch(id)
}
</script>

<template>
  <section class="devconsole-section" aria-label="Sandbox Write and Rollback">
    <div class="devconsole-section__intro">
      <h2>Sandbox Write &amp; Rollback</h2>
      <p>
        Controlled dev-sandbox write platform. Writes operate only inside the
        dev sandbox root and require HERMES_TOOL_WRITE_EXECUTION_ENABLED. Every
        executed write records a rollback manifest with a file-backed, single-use
        confirmation token + TTL. Rollback reuses the write gate. No write ever
        touches a protected target (.env, .claude, .git, *.db, *.jsonl, …).
      </p>
    </div>

    <ToolWritePanel />

    <BlockedReasonPanel v-if="writeBlocked" :code="writeBlocked" title="Write blocked" />
    <BlockedReasonPanel v-if="rollbackBlocked" :code="rollbackBlocked" title="Rollback blocked" />

    <div v-if="crossRefs.length > 0" class="devconsole-crossnav" aria-label="Cross-reference to Audit Viewer">
      <h3 class="devconsole-crossnav__title">Locate write / rollback records</h3>
      <div class="devconsole-crossnav__items">
        <AuditIdLink
          v-for="ref in crossRefs"
          :id="ref.id"
          :key="ref.id"
          :label="ref.label"
          @navigate="locate"
        />
      </div>
    </div>
  </section>
</template>
