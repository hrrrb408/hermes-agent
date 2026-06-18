<script setup lang="ts">
/**
 * Plugin descriptor detail drawer (Phase 3D).
 *
 * Shows the full safe record for one descriptor — badges, runtime gates,
 * capability bindings, and the explicit "descriptor only / does not grant
 * permission / does not execute a plugin" notice. Read-only. No secret / path
 * / callable / command / URL is ever surfaced.
 */
import { computed } from 'vue'
import { X } from '@lucide/vue'
import PluginDescriptorPermissionBadge from './PluginDescriptorPermissionBadge.vue'
import PluginDescriptorTrustBadge from './PluginDescriptorTrustBadge.vue'
import PluginDescriptorStatusBadge from './PluginDescriptorStatusBadge.vue'
import type { PluginDescriptorDetail } from '@/types/api/pluginDescriptorRegistry'

const props = defineProps<{ descriptor: PluginDescriptorDetail | null }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const gateRows = computed(() => {
  const d = props.descriptor
  if (!d) return []
  return [
    { label: 'Requires approval', value: d.requiresApproval },
    { label: 'Requires dry-run', value: d.requiresDryRun },
    { label: 'Requires confirmation', value: d.requiresConfirmation },
    { label: 'Requires audit', value: d.requiresAudit },
    { label: 'Requires budget', value: d.requiresBudget },
    { label: 'Requires kill switch', value: d.requiresKillSwitch },
    { label: 'Dev-only', value: d.devOnly },
    { label: 'Production allowed', value: d.productionAllowed },
    { label: 'Disabled by default', value: d.disabledByDefault },
  ]
})
</script>

<template>
  <aside
    v-if="descriptor"
    class="plugin-drawer"
    role="dialog"
    aria-modal="true"
    aria-labelledby="plugin-drawer-title"
    data-testid="plugin-descriptor-detail-drawer"
  >
    <header class="plugin-drawer__header">
      <h3 id="plugin-drawer-title">{{ descriptor.displayName }}</h3>
      <button type="button" class="plugin-drawer__close" aria-label="Close detail" @click="emit('close')">
        <X :size="16" aria-hidden="true" />
      </button>
    </header>

    <code class="plugin-drawer__code">{{ descriptor.pluginId }}</code>
    <p class="plugin-drawer__desc">{{ descriptor.description }}</p>

    <div class="plugin-drawer__badges">
      <PluginDescriptorStatusBadge :status="descriptor.status" />
      <PluginDescriptorPermissionBadge :permission-class="descriptor.permissionClass" />
      <PluginDescriptorTrustBadge :trust-level="descriptor.trustLevel" />
    </div>

    <p v-if="descriptor.blockedReason" class="plugin-drawer__blocked">
      Blocked reason: <strong>{{ descriptor.blockedReason }}</strong>
    </p>

    <dl class="devconsole-kv">
      <dt>Source</dt><dd>{{ descriptor.source }}</dd>
      <dt>Execution mode</dt><dd>{{ descriptor.executionMode }}</dd>
      <dt v-if="descriptor.owner">Owner</dt><dd v-if="descriptor.owner">{{ descriptor.owner }}</dd>
      <dt v-if="descriptor.metadataSchema">Metadata schema</dt>
      <dd v-if="descriptor.metadataSchema">{{ descriptor.metadataSchema }}</dd>
    </dl>

    <h4>Capability bindings</h4>
    <ul class="plugin-bindings" data-testid="plugin-capability-bindings">
      <li v-for="cid in descriptor.capabilityBindings" :key="cid"><code>{{ cid }}</code></li>
    </ul>
    <p class="devconsole-note">
      Descriptors bind only to existing Phase 3C capabilityIds. The descriptor
      does not introduce a new capability or permission class.
    </p>

    <h4>Runtime gates</h4>
    <ul class="plugin-gates" data-testid="plugin-runtime-gates">
      <li v-for="row in gateRows" :key="row.label">
        <span>{{ row.label }}:</span>
        <strong>{{ row.value ? 'yes' : 'no' }}</strong>
      </li>
    </ul>

    <p class="plugin-drawer__notice" data-testid="plugin-describes-only-notice">
      Descriptor only — does not grant permission, does not execute a plugin.
      Real execution stays governed by the existing Tool policy, Provider live
      gate, Workflow approval, dry-run, confirmation, and audit requirements.
    </p>
  </aside>
</template>
