<script setup lang="ts">
/**
 * Capability permission-class badge (Phase 3C).
 *
 * Non-color identification: each class renders a short text label + an icon,
 * never color alone. Forbidden classes carry an explicit "Forbidden" marker so
 * the badge communicates "not executable" without relying on hue.
 */
import { computed } from 'vue'
import { Check, Eye, FileEdit, RotateCcw, ShieldAlert, ShieldOff, ShieldBan, Zap } from '@lucide/vue'
import type { Component } from 'vue'
import type { CapabilityPermissionClass } from '@/types/api/capabilityRegistry'

const props = defineProps<{ permissionClass: CapabilityPermissionClass }>()

interface BadgeSpec {
  readonly label: string
  readonly icon: Component
  readonly forbidden: boolean
  readonly tone: 'read' | 'preview' | 'confirm' | 'rollback' | 'live' | 'forbidden'
}

const SPECS: Readonly<Record<CapabilityPermissionClass, BadgeSpec>> = {
  READ_ONLY: { label: 'Read-only', icon: Eye, forbidden: false, tone: 'read' },
  WRITE_PREVIEW: { label: 'Write preview', icon: FileEdit, forbidden: false, tone: 'preview' },
  WRITE_CONFIRM: { label: 'Write confirm', icon: Check, forbidden: false, tone: 'confirm' },
  ROLLBACK_CONFIRM: { label: 'Rollback confirm', icon: RotateCcw, forbidden: false, tone: 'rollback' },
  LIVE_PROVIDER_GATED: { label: 'Live provider gated', icon: Zap, forbidden: false, tone: 'live' },
  ADMIN_FORBIDDEN: { label: 'Admin forbidden', icon: ShieldAlert, forbidden: true, tone: 'forbidden' },
  EXTERNAL_FORBIDDEN: { label: 'External forbidden', icon: ShieldOff, forbidden: true, tone: 'forbidden' },
  PRODUCTION_FORBIDDEN: { label: 'Production forbidden', icon: ShieldBan, forbidden: true, tone: 'forbidden' },
}

const spec = computed<BadgeSpec>(() => SPECS[props.permissionClass])
</script>

<template>
  <span
    class="cap-badge"
    :class="[`cap-badge--${spec.tone}`, { 'cap-badge--forbidden': spec.forbidden }]"
    :title="`Permission class: ${props.permissionClass}`"
  >
    <component :is="spec.icon" :size="13" aria-hidden="true" />
    <span class="cap-badge__label">{{ spec.label }}</span>
    <span v-if="spec.forbidden" class="cap-badge__mark" aria-label="not executable">Forbidden</span>
  </span>
</template>
