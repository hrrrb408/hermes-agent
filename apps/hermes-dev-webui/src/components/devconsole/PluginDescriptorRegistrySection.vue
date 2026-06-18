<script setup lang="ts">
/**
 * Dev Console → Plugin Descriptor Registry section (Phase 3D).
 *
 * Read-only surface over the static dev-only Plugin Descriptor Registry. Loads
 * the authoritative validation summary from GET /status
 * data.pluginDescriptorRegistry and renders the deterministic static manifest
 * (list + detail). The registry describes future plugin descriptors only — it
 * never grants permission, loads a plugin, executes a plugin, or performs a
 * side effect. No new HTTP route is introduced.
 */
import { onMounted } from 'vue'
import PluginDescriptorRegistrySummary from './PluginDescriptorRegistrySummary.vue'
import PluginDescriptorRegistryTable from './PluginDescriptorRegistryTable.vue'
import PluginDescriptorRegistryDetailDrawer from './PluginDescriptorRegistryDetailDrawer.vue'
import PluginRuntimeDisabledBanner from './PluginRuntimeDisabledBanner.vue'
import { usePluginDescriptorRegistryStore } from '@/stores/pluginDescriptorRegistry'
import type {
  PluginPermissionClass,
  PluginSource,
  PluginStatus,
  PluginTrustLevel,
} from '@/types/api/pluginDescriptorRegistry'

const store = usePluginDescriptorRegistryStore()

onMounted(() => {
  void store.loadSummary()
})

const TRUST_OPTIONS: readonly (PluginTrustLevel | 'all')[] = [
  'all',
  'trusted_builtin_code',
  'trusted_static_descriptor',
  'dev_reviewed_descriptor',
  'experimental_disabled_descriptor',
  'external_forbidden',
  'unknown_forbidden',
  'production_forbidden',
]
const PERMISSION_OPTIONS: readonly (PluginPermissionClass | 'all')[] = [
  'all',
  'READ_ONLY',
  'WRITE_PREVIEW',
  'WRITE_CONFIRM',
  'ROLLBACK_CONFIRM',
  'LIVE_PROVIDER_GATED',
  'ADMIN_FORBIDDEN',
  'EXTERNAL_FORBIDDEN',
  'PRODUCTION_FORBIDDEN',
]
const STATUS_OPTIONS: readonly (PluginStatus | 'all')[] = [
  'all',
  'planned',
  'declared',
  'validated',
  'visible',
  'disabled',
  'blocked',
  'deprecated',
  'removed',
]
const SOURCE_OPTIONS: readonly (PluginSource | 'all')[] = [
  'all',
  'builtin_static',
  'tracked_static_descriptor',
  'dev_reviewed_descriptor',
  'experimental_disabled',
  'external_forbidden',
  'unknown_forbidden',
  'production_forbidden',
]

function onSelect(pluginId: string): void {
  store.selectPlugin(pluginId)
}
</script>

<template>
  <section
    class="devconsole-section"
    aria-label="Plugin Descriptor Registry"
    data-testid="plugin-descriptor-registry-section"
  >
    <div class="devconsole-section__intro">
      <h2>Plugin Descriptor Registry</h2>
      <p>
        A static dev-only registry that describes the plugin descriptors the dev
        instance knows about. It <strong>describes only — it does not grant
        permission and does not execute a plugin</strong>. No plugin runtime, no
        plugin loader, no dynamic loading, no local plugin directory loading, no
        remote registry, no marketplace, no external plugin fetch.
      </p>
    </div>

    <PluginRuntimeDisabledBanner />

    <PluginDescriptorRegistrySummary :summary="store.liveSummary" />

    <div class="devconsole-card">
      <h3>Filters</h3>
      <div class="plugin-filters">
        <label>
          Trust
          <select v-model="store.filterTrust" data-testid="plugin-filter-trust">
            <option v-for="opt in TRUST_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label>
          Permission
          <select v-model="store.filterPermission" data-testid="plugin-filter-permission">
            <option v-for="opt in PERMISSION_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label>
          Status
          <select v-model="store.filterStatus" data-testid="plugin-filter-status">
            <option v-for="opt in STATUS_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label>
          Source
          <select v-model="store.filterSource" data-testid="plugin-filter-source">
            <option v-for="opt in SOURCE_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <button
          type="button"
          class="plugin-view-btn"
          data-testid="plugin-filter-reset"
          @click="store.resetFilters"
        >
          Reset
        </button>
      </div>
    </div>

    <PluginDescriptorRegistryTable :descriptors="store.filteredDescriptors" @select="onSelect" />

    <PluginDescriptorRegistryDetailDrawer
      :descriptor="store.selectedDescriptor"
      @close="store.selectPlugin(null)"
    />
  </section>
</template>
