<script setup lang="ts">
/**
 * Plugin Descriptor Registry table (Phase 3D).
 *
 * Read-only list of descriptors with badges + a blocked-reason column. Each
 * row is a button that opens the detail drawer. Blocked / forbidden rows are
 * visually marked and carry their blockedReason. Non-color identification is
 * used throughout (icon + label). The descriptor list is value-free — no
 * secret / callable / path / command / URL is ever surfaced.
 */
import PluginDescriptorPermissionBadge from './PluginDescriptorPermissionBadge.vue'
import PluginDescriptorTrustBadge from './PluginDescriptorTrustBadge.vue'
import PluginDescriptorStatusBadge from './PluginDescriptorStatusBadge.vue'
import type { PluginDescriptorDetail } from '@/types/api/pluginDescriptorRegistry'

defineProps<{ descriptors: readonly PluginDescriptorDetail[] }>()

const emit = defineEmits<{ (e: 'select', pluginId: string): void }>()
</script>

<template>
  <div class="devconsole-card" data-testid="plugin-descriptor-registry-table">
    <h3>Plugin Descriptor Registry — Descriptors</h3>
    <table class="plugin-table">
      <thead>
        <tr>
          <th scope="col">Descriptor</th>
          <th scope="col">Status</th>
          <th scope="col">Permission</th>
          <th scope="col">Trust</th>
          <th scope="col">Capability bindings</th>
          <th scope="col">Blocked reason</th>
          <th scope="col"><span class="sr-only">View detail</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="d in descriptors"
          :key="d.pluginId"
          :class="{ 'plugin-row--blocked': d.status === 'blocked' }"
        >
          <th scope="row">
            <div class="plugin-table__id">{{ d.displayName }}</div>
            <code class="plugin-table__code">{{ d.pluginId }}</code>
          </th>
          <td><PluginDescriptorStatusBadge :status="d.status" /></td>
          <td><PluginDescriptorPermissionBadge :permission-class="d.permissionClass" /></td>
          <td><PluginDescriptorTrustBadge :trust-level="d.trustLevel" /></td>
          <td>
            <ul class="plugin-bindings">
              <li v-for="cid in d.capabilityBindings" :key="cid"><code>{{ cid }}</code></li>
            </ul>
          </td>
          <td>
            <span v-if="d.blockedReason" class="plugin-blocked-reason">{{ d.blockedReason }}</span>
            <span v-else class="plugin-muted">—</span>
          </td>
          <td>
            <button
              type="button"
              class="plugin-view-btn"
              :aria-label="`View detail for ${d.pluginId}`"
              @click="emit('select', d.pluginId)"
            >
              Detail
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
