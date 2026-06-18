<script setup lang="ts">
/**
 * Plugin descriptor trust-level badge (Phase 3D).
 *
 * Non-color identification: label + icon, never color alone. Forbidden trust
 * levels render an explicit "Forbidden" marker.
 */
import { computed } from 'vue'
import { BadgeCheck, FileLock2, FileCheck2, FlaskConical, ShieldOff, HelpCircle, ShieldBan } from '@lucide/vue'
import type { Component } from 'vue'
import type { PluginTrustLevel } from '@/types/api/pluginDescriptorRegistry'

const props = defineProps<{ trustLevel: PluginTrustLevel }>()

interface TrustSpec {
  readonly label: string
  readonly icon: Component
  readonly forbidden: boolean
}

const SPECS: Readonly<Record<PluginTrustLevel, TrustSpec>> = {
  trusted_builtin_code: { label: 'Built-in verified', icon: BadgeCheck, forbidden: false },
  trusted_static_descriptor: { label: 'Static descriptor', icon: FileLock2, forbidden: false },
  dev_reviewed_descriptor: { label: 'Dev reviewed', icon: FileCheck2, forbidden: false },
  experimental_disabled_descriptor: { label: 'Experimental disabled', icon: FlaskConical, forbidden: false },
  external_forbidden: { label: 'External forbidden', icon: ShieldOff, forbidden: true },
  unknown_forbidden: { label: 'Unknown forbidden', icon: HelpCircle, forbidden: true },
  production_forbidden: { label: 'Production forbidden', icon: ShieldBan, forbidden: true },
}

const spec = computed<TrustSpec>(() => SPECS[props.trustLevel])
</script>

<template>
  <span
    class="plugin-badge plugin-badge--trust"
    :class="{ 'plugin-badge--forbidden': spec.forbidden }"
    :title="`Trust level: ${props.trustLevel}`"
  >
    <component :is="spec.icon" :size="13" aria-hidden="true" />
    <span class="plugin-badge__label">{{ spec.label }}</span>
    <span v-if="spec.forbidden" class="plugin-badge__mark" aria-label="not trusted">Forbidden</span>
  </span>
</template>
