<script setup lang="ts">
/**
 * Plugin descriptor status badge (Phase 3D).
 *
 * Non-color identification: label + icon, never color alone. No status
 * represents runtime execution — blocked / disabled statuses carry an explicit
 * "Not executable" marker.
 */
import { computed } from 'vue'
import { Clock, FileText, BadgeCheck, Eye, CircleSlash, Ban, Archive, Trash2 } from '@lucide/vue'
import type { Component } from 'vue'
import type { PluginStatus } from '@/types/api/pluginDescriptorRegistry'

const props = defineProps<{ status: PluginStatus }>()

interface StatusSpec {
  readonly label: string
  readonly icon: Component
  readonly tone: 'visible' | 'off' | 'blocked' | 'planned' | 'muted'
}

const SPECS: Readonly<Record<PluginStatus, StatusSpec>> = {
  planned: { label: 'Planned', icon: Clock, tone: 'planned' },
  declared: { label: 'Declared', icon: FileText, tone: 'planned' },
  validated: { label: 'Validated', icon: BadgeCheck, tone: 'planned' },
  visible: { label: 'Visible', icon: Eye, tone: 'visible' },
  disabled: { label: 'Disabled', icon: CircleSlash, tone: 'off' },
  blocked: { label: 'Blocked', icon: Ban, tone: 'blocked' },
  deprecated: { label: 'Deprecated', icon: Archive, tone: 'muted' },
  removed: { label: 'Removed', icon: Trash2, tone: 'muted' },
}

const spec = computed<StatusSpec>(() => SPECS[props.status])
</script>

<template>
  <span
    class="plugin-badge"
    :class="[`plugin-badge--${spec.tone}`, { 'plugin-badge--forbidden': status === 'blocked' }]"
    :title="`Status: ${props.status}`"
  >
    <component :is="spec.icon" :size="13" aria-hidden="true" />
    <span class="plugin-badge__label">{{ spec.label }}</span>
    <span v-if="status !== 'visible'" class="plugin-badge__mark" aria-label="not executable">Not executable</span>
  </span>
</template>
