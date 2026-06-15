<script setup lang="ts">
import { computed } from 'vue'
import { SAFETY_BADGES, type SafetyBadge } from '@/lib/safetyBadges'

/**
 * Safety badge bar (Phase 2E).
 *
 * Renders the unified invariant safety badges (defaults to all SAFETY_BADGES).
 * Tone reflects whether the invariant is a hard guarantee (ok) or a deliberate
 * caution (warn). Used by the Overview dashboard and the Safety panel.
 */
const props = withDefaults(
  defineProps<{
    badges?: readonly SafetyBadge[]
  }>(),
  {
    badges: undefined,
  },
)

const rendered = computed(() => props.badges ?? SAFETY_BADGES)
</script>

<template>
  <div class="devconsole-badge-bar" role="list" aria-label="Safety boundary badges" data-testid="dev-safety-badges">
    <span
      v-for="badge in rendered"
      :key="badge.id"
      class="devconsole-badge"
      role="listitem"
      :data-tone="badge.tone"
      :title="badge.description"
    >{{ badge.label }}</span>
  </div>
</template>
