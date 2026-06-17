<script setup lang="ts">
/**
 * Capability status badge (Phase 3C).
 *
 * Non-color identification: label + icon, never color alone. Blocked / disabled
 * statuses carry an explicit "not executable" marker.
 */
import { computed } from 'vue'
import { CircleCheck, CircleSlash, Ban, Clock, Archive } from '@lucide/vue'
import type { Component } from 'vue'
import type { CapabilityStatus } from '@/types/api/capabilityRegistry'

const props = defineProps<{ status: CapabilityStatus }>()

interface StatusSpec {
  readonly label: string
  readonly icon: Component
  readonly executable: boolean
  readonly tone: 'enabled' | 'off' | 'blocked' | 'planned' | 'deprecated'
}

const SPECS: Readonly<Record<CapabilityStatus, StatusSpec>> = {
  enabled: { label: 'Enabled', icon: CircleCheck, executable: true, tone: 'enabled' },
  disabled: { label: 'Disabled', icon: CircleSlash, executable: false, tone: 'off' },
  blocked: { label: 'Blocked', icon: Ban, executable: false, tone: 'blocked' },
  planned: { label: 'Planned', icon: Clock, executable: false, tone: 'planned' },
  deprecated: { label: 'Deprecated', icon: Archive, executable: false, tone: 'deprecated' },
}

const spec = computed<StatusSpec>(() => SPECS[props.status])
</script>

<template>
  <span
    class="cap-badge"
    :class="[`cap-badge--${spec.tone}`, { 'cap-badge--forbidden': !spec.executable && status === 'blocked' }]"
    :title="`Status: ${props.status}`"
  >
    <component :is="spec.icon" :size="13" aria-hidden="true" />
    <span class="cap-badge__label">{{ spec.label }}</span>
    <span v-if="!spec.executable" class="cap-badge__mark" aria-label="not executable">Not executable</span>
  </span>
</template>
