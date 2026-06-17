<script setup lang="ts">
/**
 * Dev Console → Capability Registry section (Phase 3C).
 *
 * Read-only surface over the static dev-only Capability Registry. Loads the
 * authoritative validation summary from GET /status data.capabilityRegistry and
 * renders the deterministic static manifest (list + detail). The registry
 * describes capabilities only — it never grants permission, loads a plugin, or
 * performs a side effect. No new HTTP route is introduced.
 */
import { onMounted } from 'vue'
import CapabilityRegistrySummary from './CapabilityRegistrySummary.vue'
import CapabilityRegistryTable from './CapabilityRegistryTable.vue'
import CapabilityRegistryDetailDrawer from './CapabilityRegistryDetailDrawer.vue'
import { useCapabilityRegistryStore } from '@/stores/capabilityRegistry'
import type {
  CapabilityCategory,
  CapabilityPermissionClass,
  CapabilityStatus,
  CapabilityTrustLevel,
} from '@/types/api/capabilityRegistry'

const store = useCapabilityRegistryStore()

onMounted(() => {
  void store.loadSummary()
})

const CATEGORY_OPTIONS: readonly (CapabilityCategory | 'all')[] = [
  'all', 'tool', 'provider', 'workflow', 'sandbox', 'audit', 'registry', 'system',
]
const PERMISSION_OPTIONS: readonly (CapabilityPermissionClass | 'all')[] = [
  'all', 'READ_ONLY', 'WRITE_PREVIEW', 'WRITE_CONFIRM', 'ROLLBACK_CONFIRM',
  'LIVE_PROVIDER_GATED', 'ADMIN_FORBIDDEN', 'EXTERNAL_FORBIDDEN', 'PRODUCTION_FORBIDDEN',
]
const TRUST_OPTIONS: readonly (CapabilityTrustLevel | 'all')[] = [
  'all', 'BUILTIN_VERIFIED', 'DEV_STATIC_MANIFEST', 'EXPERIMENTAL_DISABLED',
  'EXTERNAL_FORBIDDEN', 'UNKNOWN_FORBIDDEN',
]
const STATUS_OPTIONS: readonly (CapabilityStatus | 'all')[] = [
  'all', 'enabled', 'disabled', 'blocked', 'planned', 'deprecated',
]

function onSelect(capabilityId: string): void {
  store.selectCapability(capabilityId)
}
</script>

<template>
  <section class="devconsole-section" aria-label="Capability Registry" data-testid="capability-registry-section">
    <div class="devconsole-section__intro">
      <h2>Capability Registry</h2>
      <p>
        A static dev-only registry that describes the capabilities the dev
        instance knows about. It <strong>describes only — it does not grant
        permission</strong>. No plugin runtime, dynamic loading, remote registry,
        or marketplace. Real execution stays governed by the existing Tool policy,
        Provider live gate, and Workflow approval gates.
      </p>
    </div>

    <CapabilityRegistrySummary :summary="store.liveSummary" />

    <div class="devconsole-card">
      <h3>Filters</h3>
      <div class="cap-filters">
        <label>
          Category
          <select v-model="store.filterCategory" data-testid="cap-filter-category">
            <option v-for="opt in CATEGORY_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label>
          Permission
          <select v-model="store.filterPermission" data-testid="cap-filter-permission">
            <option v-for="opt in PERMISSION_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label>
          Trust
          <select v-model="store.filterTrust" data-testid="cap-filter-trust">
            <option v-for="opt in TRUST_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label>
          Status
          <select v-model="store.filterStatus" data-testid="cap-filter-status">
            <option v-for="opt in STATUS_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <button type="button" class="cap-view-btn" data-testid="cap-filter-reset" @click="store.resetFilters">
          Reset
        </button>
      </div>
    </div>

    <CapabilityRegistryTable :capabilities="store.filteredCapabilities" @select="onSelect" />

    <CapabilityRegistryDetailDrawer
      :capability="store.selectedCapability"
      @close="store.selectCapability(null)"
    />
  </section>
</template>
