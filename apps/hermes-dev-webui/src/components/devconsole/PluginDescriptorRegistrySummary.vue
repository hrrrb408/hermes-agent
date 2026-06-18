<script setup lang="ts">
/**
 * Plugin Descriptor Registry summary (Phase 3D).
 *
 * Renders the frozen policy flags + live counts from the /status block. The
 * frozen flags (pluginRuntimeImplemented / pluginLoaderImplemented /
 * dynamicLoadingAllowed / localPluginDirectoryLoadingAllowed /
 * remoteRegistryAllowed / marketplaceAllowed / externalPluginFetchAllowed /
 * providerGeneratedPluginAllowed / llmGeneratedPluginInstallAllowed /
 * pluginExecutionAllowed / newRouteIntroduced = false; productionAllowed =
 * false; devOnly = true) are surfaced as explicit badges so the read-only
 * "descriptor only / does not grant permission / does not execute a plugin"
 * invariant is visible at a glance.
 */
import { computed } from 'vue'
import type { PluginDescriptorRegistrySummary } from '@/types/api/pluginDescriptorRegistry'
import { PLUGIN_FROZEN_FLAGS } from '@/stores/pluginDescriptorRegistry'

const props = defineProps<{ summary: PluginDescriptorRegistrySummary | null }>()

const rows = computed(() => {
  const s = props.summary
  return [
    { label: 'Registry status', value: s?.status ?? '—' },
    { label: 'Registry version', value: s?.registryVersion ?? '—' },
    { label: 'Descriptor count', value: s?.descriptorCount ?? 0 },
    { label: 'Visible', value: s?.visibleCount ?? 0 },
    { label: 'Disabled', value: s?.disabledCount ?? 0 },
    { label: 'Blocked', value: s?.blockedCount ?? 0 },
    { label: 'Route governance', value: s?.routeGovernanceExpected ?? '34/34/5/0/1/1' },
    {
      label: 'Validation',
      value: s ? `${s.validation.valid ? 'passed' : 'failed'} (${s.validation.errorCount} errors)` : '—',
    },
  ]
})

const flags = computed(() => [
  { label: 'Dev-only', ok: PLUGIN_FROZEN_FLAGS.devOnly === true, text: PLUGIN_FROZEN_FLAGS.devOnly ? 'yes' : 'no' },
  { label: 'Production allowed', ok: PLUGIN_FROZEN_FLAGS.productionAllowed === false, text: PLUGIN_FROZEN_FLAGS.productionAllowed ? 'yes' : 'no' },
  { label: 'Plugin runtime implemented', ok: PLUGIN_FROZEN_FLAGS.pluginRuntimeImplemented === false, text: PLUGIN_FROZEN_FLAGS.pluginRuntimeImplemented ? 'yes' : 'no' },
  { label: 'Plugin loader implemented', ok: PLUGIN_FROZEN_FLAGS.pluginLoaderImplemented === false, text: PLUGIN_FROZEN_FLAGS.pluginLoaderImplemented ? 'yes' : 'no' },
  { label: 'Dynamic loading', ok: PLUGIN_FROZEN_FLAGS.dynamicLoadingAllowed === false, text: PLUGIN_FROZEN_FLAGS.dynamicLoadingAllowed ? 'yes' : 'no' },
  { label: 'Local plugin directory loading', ok: PLUGIN_FROZEN_FLAGS.localPluginDirectoryLoadingAllowed === false, text: PLUGIN_FROZEN_FLAGS.localPluginDirectoryLoadingAllowed ? 'yes' : 'no' },
  { label: 'Remote registry', ok: PLUGIN_FROZEN_FLAGS.remoteRegistryAllowed === false, text: PLUGIN_FROZEN_FLAGS.remoteRegistryAllowed ? 'yes' : 'no' },
  { label: 'Marketplace', ok: PLUGIN_FROZEN_FLAGS.marketplaceAllowed === false, text: PLUGIN_FROZEN_FLAGS.marketplaceAllowed ? 'yes' : 'no' },
  { label: 'External plugin fetch', ok: PLUGIN_FROZEN_FLAGS.externalPluginFetchAllowed === false, text: PLUGIN_FROZEN_FLAGS.externalPluginFetchAllowed ? 'yes' : 'no' },
  { label: 'Provider-generated plugin', ok: PLUGIN_FROZEN_FLAGS.providerGeneratedPluginAllowed === false, text: PLUGIN_FROZEN_FLAGS.providerGeneratedPluginAllowed ? 'yes' : 'no' },
  { label: 'LLM-generated plugin install', ok: PLUGIN_FROZEN_FLAGS.llmGeneratedPluginInstallAllowed === false, text: PLUGIN_FROZEN_FLAGS.llmGeneratedPluginInstallAllowed ? 'yes' : 'no' },
  { label: 'Plugin execution', ok: PLUGIN_FROZEN_FLAGS.pluginExecutionAllowed === false, text: PLUGIN_FROZEN_FLAGS.pluginExecutionAllowed ? 'yes' : 'no' },
  { label: 'New route introduced', ok: PLUGIN_FROZEN_FLAGS.newRouteIntroduced === false, text: PLUGIN_FROZEN_FLAGS.newRouteIntroduced ? 'yes' : 'no' },
])
</script>

<template>
  <div class="devconsole-card" data-testid="plugin-descriptor-registry-summary">
    <h3>Plugin Descriptor Registry — Summary</h3>
    <p class="devconsole-note" style="margin-top: 0">
      Static dev-only descriptor registry. It describes future plugin
      descriptors only — it does not grant permission, does not load a plugin,
      and does not execute a plugin. No plugin runtime, no plugin loader, no
      dynamic loading, no local plugin directory loading, no remote registry,
      no marketplace, no external plugin fetch.
    </p>

    <dl class="devconsole-kv">
      <template v-for="row in rows" :key="row.label">
        <dt>{{ row.label }}</dt>
        <dd>{{ row.value }}</dd>
      </template>
    </dl>

    <h4 style="margin-top: 1rem">Frozen policy flags</h4>
    <ul class="plugin-flags" data-testid="plugin-frozen-flags">
      <li v-for="flag in flags" :key="flag.label" :class="{ 'plugin-flag--ok': flag.ok }">
        <strong>{{ flag.label }}:</strong>
        <span>{{ flag.text }}</span>
      </li>
    </ul>
  </div>
</template>
