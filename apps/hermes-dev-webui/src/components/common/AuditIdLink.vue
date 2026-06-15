<script setup lang="ts">
import { computed } from 'vue'
import { truncateHash } from '@/lib/formatters'

/**
 * Clickable audit/correlation id chip (Phase 2E).
 *
 * Renders a short, lossy id as a button. The parent wires the emitted
 * `navigate` event to the dev-console cross-navigation (jump to the Audit
 * Viewer pre-filtered to this id). The full id is never shown for long values
 * — truncation is intentional and lossy.
 */
const props = withDefaults(
  defineProps<{
    /** The id to display + emit (may be null/empty, in which case nothing renders). */
    id: string | null | undefined
    /** Optional prefix label (e.g. "audit", "rollback"). */
    label?: string
    /** Truncation length for the displayed value. */
    max?: number
  }>(),
  {
    label: undefined,
    max: 16,
  },
)

defineEmits<{
  /** Fired with the full (untruncated) id when the chip is clicked. */
  navigate: [id: string]
}>()

const display = computed(() => truncateHash(props.id, props.max))
const shouldRender = computed(() => !!props.id)
</script>

<template>
  <button
    v-if="shouldRender"
    type="button"
    class="audit-id-link"
    data-testid="dev-audit-id-link"
    :aria-label="`Jump to audit viewer for ${label ?? 'id'} ${id}`"
    :title="`Locate ${id} in the Audit Viewer`"
    @click="$emit('navigate', String(id))"
  >
    <span v-if="label" class="audit-id-link__label">{{ label }}:</span>
    <span class="audit-id-link__value">{{ display }}</span>
  </button>
</template>

<style scoped>
.audit-id-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0 6px;
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-pill, 999px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.04));
  color: var(--color-accent, #7c8adb);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.625rem;
  cursor: pointer;
  transition: background-color var(--transition-fast, 120ms ease), border-color var(--transition-fast, 120ms ease);
}

.audit-id-link:hover {
  background: var(--workspace-hover-bg, rgba(255, 255, 255, 0.08));
  border-color: var(--color-accent, #7c8adb);
}

.audit-id-link:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 1px;
}

.audit-id-link__label {
  color: var(--color-text-muted, #6a6a74);
  font-family: inherit;
}
</style>
