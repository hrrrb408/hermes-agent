<script setup lang="ts">
/**
 * Capability detail drawer (Phase 3C).
 *
 * Shows the full safe record for one capability — badges, runtime gates,
 * bindings, and the explicit "registry describes only / does not grant
 * permission" notice. Read-only. No secret/path/callable is ever surfaced.
 */
import { computed } from 'vue'
import { X } from '@lucide/vue'
import CapabilityPermissionBadge from './CapabilityPermissionBadge.vue'
import CapabilityTrustBadge from './CapabilityTrustBadge.vue'
import CapabilityStatusBadge from './CapabilityStatusBadge.vue'
import type { CapabilityDetail } from '@/types/api/capabilityRegistry'

const props = defineProps<{ capability: CapabilityDetail | null }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const gateRows = computed(() => {
  const c = props.capability
  if (!c) return []
  return [
    { label: 'Requires approval', value: c.requiresApproval },
    { label: 'Requires dry-run', value: c.requiresDryRun },
    { label: 'Requires confirmation', value: c.requiresConfirmation },
    { label: 'Requires audit', value: c.requiresAudit },
    { label: 'Requires budget', value: c.requiresBudget },
    { label: 'Requires kill switch', value: c.requiresKillSwitch },
    { label: 'Dev-only', value: c.devOnly },
    { label: 'Production allowed', value: c.productionAllowed },
    { label: 'Disabled by default', value: c.disabledByDefault },
  ]
})

const bindings = computed(() => {
  const c = props.capability
  if (!c) return []
  const out: { label: string; value: string }[] = []
  if (c.toolBinding) out.push({ label: 'Tool binding', value: c.toolBinding })
  if (c.providerBinding) out.push({ label: 'Provider binding', value: c.providerBinding })
  if (c.workflowBinding) out.push({ label: 'Workflow binding', value: c.workflowBinding })
  return out
})
</script>

<template>
  <aside
    v-if="capability"
    class="cap-drawer"
    role="dialog"
    aria-modal="true"
    aria-labelledby="cap-drawer-title"
    data-testid="capability-detail-drawer"
  >
    <header class="cap-drawer__header">
      <h3 id="cap-drawer-title">{{ capability.displayName }}</h3>
      <button type="button" class="cap-drawer__close" aria-label="Close detail" @click="emit('close')">
        <X :size="16" aria-hidden="true" />
      </button>
    </header>

    <code class="cap-drawer__code">{{ capability.capabilityId }}</code>
    <p class="cap-drawer__desc">{{ capability.description }}</p>

    <div class="cap-drawer__badges">
      <CapabilityStatusBadge :status="capability.status" />
      <CapabilityPermissionBadge :permission-class="capability.permissionClass" />
      <CapabilityTrustBadge :trust-level="capability.trustLevel" />
    </div>

    <p v-if="capability.blockedReason" class="cap-drawer__blocked">
      Blocked reason: <strong>{{ capability.blockedReason }}</strong>
    </p>

    <dl class="devconsole-kv">
      <dt>Category</dt><dd>{{ capability.category }}</dd>
      <dt>Execution mode</dt><dd>{{ capability.executionMode }}</dd>
      <dt>Route exposure</dt><dd>{{ capability.routeExposure }}</dd>
      <template v-for="b in bindings" :key="b.label">
        <dt>{{ b.label }}</dt><dd>{{ b.value }}</dd>
      </template>
    </dl>

    <h4>Runtime gates</h4>
    <ul class="cap-gates" data-testid="capability-runtime-gates">
      <li v-for="row in gateRows" :key="row.label">
        <span>{{ row.label }}:</span>
        <strong>{{ row.value ? 'yes' : 'no' }}</strong>
      </li>
    </ul>

    <p class="cap-drawer__notice" data-testid="capability-describes-only-notice">
      Registry describes only — does not grant permission. Real execution stays
      governed by the existing Tool policy, Provider live gate, Workflow
      approval, dry-run, confirmation, and audit requirements.
    </p>
  </aside>
</template>
