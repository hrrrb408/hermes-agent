<script setup lang="ts">
/**
 * Capability Registry table (Phase 3C).
 *
 * Read-only list of capabilities with badges + a blocked-reason column. Each
 * row is a button that opens the detail drawer. Blocked / forbidden rows are
 * visually marked and carry their blockedReason. Non-color identification is
 * used throughout (icon + label).
 */
import CapabilityPermissionBadge from './CapabilityPermissionBadge.vue'
import CapabilityTrustBadge from './CapabilityTrustBadge.vue'
import CapabilityStatusBadge from './CapabilityStatusBadge.vue'
import type { CapabilityDetail } from '@/types/api/capabilityRegistry'

defineProps<{ capabilities: readonly CapabilityDetail[] }>()

const emit = defineEmits<{ (e: 'select', capabilityId: string): void }>()
</script>

<template>
  <div class="devconsole-card" data-testid="capability-registry-table">
    <h3>Capability Registry — Capabilities</h3>
    <table class="cap-table">
      <thead>
        <tr>
          <th scope="col">Capability</th>
          <th scope="col">Category</th>
          <th scope="col">Status</th>
          <th scope="col">Permission</th>
          <th scope="col">Trust</th>
          <th scope="col">Blocked reason</th>
          <th scope="col"><span class="sr-only">View detail</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="cap in capabilities"
          :key="cap.capabilityId"
          :class="{ 'cap-row--blocked': cap.status === 'blocked' }"
        >
          <th scope="row">
            <div class="cap-table__id">{{ cap.displayName }}</div>
            <code class="cap-table__code">{{ cap.capabilityId }}</code>
          </th>
          <td>{{ cap.category }}</td>
          <td><CapabilityStatusBadge :status="cap.status" /></td>
          <td><CapabilityPermissionBadge :permission-class="cap.permissionClass" /></td>
          <td><CapabilityTrustBadge :trust-level="cap.trustLevel" /></td>
          <td>
            <span v-if="cap.blockedReason" class="cap-blocked-reason">{{ cap.blockedReason }}</span>
            <span v-else class="cap-muted">—</span>
          </td>
          <td>
            <button
              type="button"
              class="cap-view-btn"
              :aria-label="`View detail for ${cap.capabilityId}`"
              @click="emit('select', cap.capabilityId)"
            >
              Detail
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
