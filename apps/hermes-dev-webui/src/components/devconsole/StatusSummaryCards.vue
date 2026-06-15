<script setup lang="ts">
/**
 * Overview status summary cards (Phase 2E).
 *
 * Renders a responsive grid of label/value cards. Each card optionally carries
 * a tone (ok/warn/danger/info) and a sub-label. Used by the Overview dashboard.
 */
withDefaults(
  defineProps<{
    cards: ReadonlyArray<{
      label: string
      value: string | number
      sub?: string
      tone?: 'ok' | 'warn' | 'danger' | 'info'
    }>
  }>(),
  {},
)
</script>

<template>
  <div class="devconsole-summary" data-testid="dev-summary-cards">
    <div
      v-for="card in cards"
      :key="card.label"
      class="devconsole-summary__card"
      :data-tone="card.tone ?? 'info'"
    >
      <div class="devconsole-summary__label">{{ card.label }}</div>
      <div class="devconsole-summary__value">{{ card.value }}</div>
      <div v-if="card.sub" class="devconsole-summary__sub">{{ card.sub }}</div>
    </div>
  </div>
</template>
