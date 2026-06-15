<script setup lang="ts">
/**
 * Phase 3A workflow step list.
 *
 * Renders the ordered steps of the active execution with their status, a
 * non-color tone marker, the cursor indicator, and selection. Selecting a step
 * emits `select` so the detail panel can preview / approve / execute it.
 */
import { computed } from 'vue'
import { formatStepStatus, formatStepType, stepStatusTone } from '@/lib/workflowFormatters'
import type { WorkflowStep } from '@/lib/workflowTypes'

const props = defineProps<{
  steps: readonly WorkflowStep[]
  cursorStepId: string | null | undefined
  selectedStepId?: string | null
}>()

const emit = defineEmits<{
  select: [stepId: string]
}>()

const rows = computed(() =>
  props.steps.map((step, index) => ({
    step,
    index,
    tone: stepStatusTone(step.status),
    isCursor: step.stepId === props.cursorStepId,
    isSelected: step.stepId === props.selectedStepId,
  })),
)
</script>

<template>
  <ul
    class="wf-steplist"
    aria-label="Workflow steps"
    data-testid="dev-workflow-step-list"
  >
    <li
      v-for="row in rows"
      :key="row.step.stepId"
      class="wf-steplist__item"
      :data-tone="row.tone"
      :data-cursor="row.isCursor"
    >
      <button
        type="button"
        class="wf-steplist__btn"
        :class="{ 'wf-steplist__btn--selected': row.isSelected }"
        :aria-current="row.isCursor ? 'step' : undefined"
        :aria-pressed="row.isSelected"
        :data-testid="`dev-workflow-step-row-${row.step.stepType}`"
        @click="emit('select', row.step.stepId)"
      >
        <span class="wf-steplist__index">{{ row.index + 1 }}</span>
        <span class="wf-steplist__body">
          <span class="wf-steplist__type">{{ formatStepType(row.step.stepType) }}</span>
          <span class="wf-steplist__title">{{ row.step.title }}</span>
        </span>
        <span
          class="wf-steplist__status"
          :data-tone="row.tone"
          data-testid="dev-workflow-step-status"
        >{{ formatStepStatus(row.step.status) }}</span>
      </button>
      <span v-if="row.isCursor" class="wf-steplist__cursor" aria-label="current step">◀ current</span>
    </li>
  </ul>
</template>

<style scoped>
.wf-steplist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.wf-steplist__item {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}
.wf-steplist__btn {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
  color: var(--color-text-primary, #e4e4e8);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--transition-fast, 120ms ease);
}
.wf-steplist__btn:hover {
  border-color: var(--color-accent, #7c8adb);
}
.wf-steplist__btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 1px;
}
.wf-steplist__btn--selected {
  border-color: var(--color-accent, #7c8adb);
  background: var(--color-accent-soft, rgba(124, 138, 219, 0.12));
}
.wf-steplist__index {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.625rem;
  color: var(--color-text-muted, #6a6a74);
}
.wf-steplist__body {
  display: grid;
  gap: 1px;
  flex: 1;
}
.wf-steplist__type {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-steplist__title {
  font-size: var(--font-size-sm, 0.8125rem);
}
.wf-steplist__status {
  font-size: 0.625rem;
  font-weight: var(--font-weight-semibold, 600);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 1px 6px;
  border-radius: var(--radius-pill, 999px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
}
.wf-steplist__status[data-tone='positive'] {
  color: var(--color-success, #6fb98f);
  border-color: var(--color-success, #6fb98f);
}
.wf-steplist__status[data-tone='negative'] {
  color: var(--color-error, #e5656b);
  border-color: var(--color-error, #e5656b);
}
.wf-steplist__status[data-tone='progress'] {
  color: var(--color-accent, #7c8adb);
  border-color: var(--color-accent, #7c8adb);
}
.wf-steplist__cursor {
  font-size: 0.625rem;
  color: var(--color-accent, #7c8adb);
}
</style>
