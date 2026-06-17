<script setup lang="ts">
/**
 * Capability trust-level badge (Phase 3C).
 *
 * Non-color identification: label + icon, never color alone. Forbidden trust
 * levels render an explicit "Forbidden" marker.
 */
import { computed } from 'vue'
import { BadgeCheck, FileLock2, FlaskConical, ShieldOff, HelpCircle } from '@lucide/vue'
import type { Component } from 'vue'
import type { CapabilityTrustLevel } from '@/types/api/capabilityRegistry'

const props = defineProps<{ trustLevel: CapabilityTrustLevel }>()

interface TrustSpec {
  readonly label: string
  readonly icon: Component
  readonly forbidden: boolean
}

const SPECS: Readonly<Record<CapabilityTrustLevel, TrustSpec>> = {
  BUILTIN_VERIFIED: { label: 'Built-in verified', icon: BadgeCheck, forbidden: false },
  DEV_STATIC_MANIFEST: { label: 'Dev static manifest', icon: FileLock2, forbidden: false },
  EXPERIMENTAL_DISABLED: { label: 'Experimental disabled', icon: FlaskConical, forbidden: false },
  EXTERNAL_FORBIDDEN: { label: 'External forbidden', icon: ShieldOff, forbidden: true },
  UNKNOWN_FORBIDDEN: { label: 'Unknown forbidden', icon: HelpCircle, forbidden: true },
}

const spec = computed<TrustSpec>(() => SPECS[props.trustLevel])
</script>

<template>
  <span
    class="cap-badge cap-badge--trust"
    :class="{ 'cap-badge--forbidden': spec.forbidden }"
    :title="`Trust level: ${props.trustLevel}`"
  >
    <component :is="spec.icon" :size="13" aria-hidden="true" />
    <span class="cap-badge__label">{{ spec.label }}</span>
    <span v-if="spec.forbidden" class="cap-badge__mark" aria-label="not trusted">Forbidden</span>
  </span>
</template>
