<script setup lang="ts">
import { computed } from 'vue'
import ToolExecutePanel from '@/components/workspace/ToolExecutePanel.vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import { useToolExecuteStore } from '@/stores/toolExecute'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

/**
 * Dev Console → Tool Execution section (Phase 2E).
 *
 * Reuses the existing self-contained ToolExecutePanel (no props, reads its own
 * store) and adds a result→audit cross-reference strip so a completed execute
 * can be located in the Audit Viewer. The existing panel is untouched.
 */
const store = useToolExecuteStore()
const nav = useDevConsoleNavStore()

const crossRefs = computed<{ id: string; label: string }[]>(() => {
  const r = store.executeResult
  if (!r) return []
  const out: { id: string; label: string }[] = []
  if (r.postExecutionAuditId) out.push({ id: r.postExecutionAuditId, label: 'post-exec audit' })
  if (r.preExecutionAuditId) out.push({ id: r.preExecutionAuditId, label: 'pre-exec audit' })
  if (r.executeRequestId) out.push({ id: r.executeRequestId, label: 'execute request' })
  if (r.dryRunRequestId) out.push({ id: r.dryRunRequestId, label: 'dry-run request' })
  return out
})

async function locate(id: string): Promise<void> {
  await nav.prefillAuditSearch(id)
}
</script>

<template>
  <section class="devconsole-section" aria-label="Tool Execution">
    <div class="devconsole-section__intro">
      <h2>Tool Execution</h2>
      <p>
        Controlled execution workbench for the six allowlisted read-only tools.
        Default gates block before any handler call; the provider schema is never
        sent and no provider API is ever called. Every execution is recorded in
        the dev audit trail.
      </p>
    </div>

    <ToolExecutePanel />

    <div v-if="crossRefs.length > 0" class="devconsole-crossnav" aria-label="Cross-reference to Audit Viewer">
      <h3 class="devconsole-crossnav__title">Locate in Audit Viewer</h3>
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
