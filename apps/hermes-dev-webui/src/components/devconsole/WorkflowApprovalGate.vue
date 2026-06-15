<script setup lang="ts">
/**
 * Phase 3A workflow approval gate.
 *
 * Shows whether a step has an active single-use approval token issued by its
 * preview, and when it expires. The raw token itself is never displayed — only
 * its presence, its public approval id, and its expiry. This is the manual
 * human-approval gate that workflow_step_execute consumes.
 */
import { computed } from 'vue'

const props = defineProps<{
  approvalRequired: boolean
  hasToken: boolean
  approvalId: string | null | undefined
  expiresAt: string | null | undefined
}>()

const state = computed<'required' | 'ready' | 'none'>(() => {
  if (!props.approvalRequired) return 'none'
  if (props.hasToken) return 'ready'
  return 'required'
})
const stateLabel = computed(() => {
  switch (state.value) {
    case 'ready':
      return 'Approved — ready to execute'
    case 'required':
      return 'Approval required — preview the step to approve'
    default:
      return 'No approval gate for this step type'
  }
})
</script>

<template>
  <div
    class="wf-gate"
    :data-state="state"
    role="status"
    aria-live="polite"
    data-testid="dev-workflow-approval-gate"
  >
    <span class="wf-gate__label">Approval gate</span>
    <strong class="wf-gate__state" :data-testid="`dev-workflow-approval-${state}`">{{ stateLabel }}</strong>
    <span v-if="approvalId" class="wf-gate__id">approval id: {{ approvalId }}</span>
    <span v-if="expiresAt" class="wf-gate__expiry">expires: {{ expiresAt }}</span>
  </div>
</template>

<style scoped>
.wf-gate {
  display: grid;
  gap: 2px;
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}
.wf-gate[data-state='ready'] {
  border-color: var(--color-success, #6fb98f);
  background: var(--color-success-soft, rgba(111, 185, 143, 0.12));
}
.wf-gate[data-state='required'] {
  border-color: var(--color-warning, #d4a843);
  background: var(--color-warning-soft, rgba(212, 168, 67, 0.12));
}
.wf-gate__label {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #6a6a74);
}
.wf-gate__state {
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-gate__id,
.wf-gate__expiry {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.625rem;
  color: var(--color-text-muted, #6a6a74);
}
</style>
