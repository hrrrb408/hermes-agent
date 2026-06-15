<script setup lang="ts">
/**
 * Phase 3A workflow step detail.
 *
 * Shows the selected step's type, status, safe input summary, preview, result,
 * audit links, the approval gate, and the Preview / Execute controls. Execute
 * is disabled until an approval token exists; write-execute and rollback-execute
 * are never offered (those steps are preview/reference-only by design).
 */
import { computed } from 'vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import WorkflowApprovalGate from './WorkflowApprovalGate.vue'
import { formatStepStatus, formatStepType, isExecutableStepType } from '@/lib/workflowFormatters'
import type { WorkflowStep, WorkflowStepPreviewResponse } from '@/lib/workflowTypes'

const props = defineProps<{
  step: WorkflowStep | null
  preview: WorkflowStepPreviewResponse | null
  hasApprovalToken: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  preview: [stepId: string]
  execute: [stepId: string]
  navigate: [id: string]
}>()

const canPreview = computed(
  () => props.step !== null && props.step.status !== 'completed' && !props.loading,
)
const canExecute = computed(
  () =>
    props.step !== null &&
    isExecutableStepType(props.step.stepType) &&
    props.hasApprovalToken &&
    props.step.status !== 'completed' &&
    !props.loading,
)
const writeExecuteBlocked = computed(
  () => props.step?.stepType === 'sandbox_write_preview' || props.step?.stepType === 'rollback_reference',
)
</script>

<template>
  <section
    v-if="step"
    class="wf-detail"
    aria-label="Workflow step detail"
    data-testid="dev-workflow-step-detail"
  >
    <header class="wf-detail__head">
      <h3 class="wf-detail__title">{{ step.title }}</h3>
      <span class="wf-detail__meta">
        <span class="wf-detail__type">{{ formatStepType(step.stepType) }}</span>
        <span class="wf-detail__status" data-testid="dev-workflow-detail-status">{{ formatStepStatus(step.status) }}</span>
      </span>
    </header>

    <p v-if="step.description" class="wf-detail__desc">{{ step.description }}</p>

    <WorkflowApprovalGate
      :approval-required="step.requiresApproval"
      :has-token="hasApprovalToken"
      :approval-id="preview?.approvalId"
      :expires-at="preview?.approvalExpiresAt"
    />

    <div v-if="writeExecuteBlocked" class="wf-detail__note" data-testid="dev-workflow-write-execute-blocked">
      This step is preview / reference only. The workflow never executes writes
      or rollbacks — use the existing write / rollback confirmation flows for
      actual execution.
    </div>

    <div v-if="step.safeInputSummary && Object.keys(step.safeInputSummary).length > 0" class="wf-detail__block">
      <h4 class="wf-detail__label">Safe input summary</h4>
      <dl class="wf-detail__kv">
        <template v-for="(value, key) in step.safeInputSummary" :key="key">
          <dt>{{ key }}</dt>
          <dd data-testid="dev-workflow-step-input-summary">{{ value }}</dd>
        </template>
      </dl>
    </div>

    <div v-if="preview && preview.preview" class="wf-detail__block">
      <h4 class="wf-detail__label">Preview</h4>
      <pre class="wf-detail__preview" data-testid="dev-workflow-step-preview">{{ JSON.stringify(preview.preview, null, 2) }}</pre>
    </div>

    <div v-if="step.result" class="wf-detail__block">
      <h4 class="wf-detail__label">Result</h4>
      <pre class="wf-detail__result" data-testid="dev-workflow-step-result">{{ JSON.stringify(step.result, null, 2) }}</pre>
    </div>

    <div v-if="step.auditLinks && step.auditLinks.length > 0" class="wf-detail__block">
      <h4 class="wf-detail__label">Audit links</h4>
      <div class="wf-detail__links">
        <AuditIdLink
          v-for="link in step.auditLinks"
          :id="link.auditId"
          :key="link.auditId"
          :label="link.label || 'audit'"
          @navigate="emit('navigate', $event)"
        />
      </div>
    </div>

    <div class="wf-detail__actions">
      <button
        type="button"
        class="wf-detail__btn"
        :disabled="!canPreview"
        data-testid="dev-workflow-preview-btn"
        @click="emit('preview', step.stepId)"
      >Preview step</button>
      <button
        type="button"
        class="wf-detail__btn wf-detail__btn--primary"
        :disabled="!canExecute"
        data-testid="dev-workflow-execute-btn"
        @click="emit('execute', step.stepId)"
      >Execute step</button>
    </div>
  </section>
  <p v-else class="wf-detail__empty" data-testid="dev-workflow-step-detail-empty">
    Select a step to preview, approve, and execute it.
  </p>
</template>

<style scoped>
.wf-detail {
  display: grid;
  gap: var(--space-3, 12px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}
.wf-detail__head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  align-items: baseline;
  flex-wrap: wrap;
}
.wf-detail__title {
  margin: 0;
  font-size: var(--font-size-base, 0.9375rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-detail__meta {
  display: flex;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-detail__desc {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
}
.wf-detail__note {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-warning, #d4a843);
  padding: var(--space-2, 8px);
  border: 1px dashed var(--color-warning, #d4a843);
  border-radius: var(--radius-sm, 4px);
}
.wf-detail__block {
  display: grid;
  gap: 4px;
}
.wf-detail__label {
  margin: 0;
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #6a6a74);
}
.wf-detail__kv {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 2px var(--space-3, 12px);
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
}
.wf-detail__kv dt {
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-detail__kv dd {
  margin: 0;
  color: var(--color-text-primary, #e4e4e8);
}
.wf-detail__preview,
.wf-detail__result {
  margin: 0;
  padding: var(--space-2, 8px);
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface, rgba(0, 0, 0, 0.2));
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.6875rem;
  color: var(--color-text-secondary, #a0a0aa);
  white-space: pre-wrap;
  word-break: break-word;
}
.wf-detail__links {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.wf-detail__actions {
  display: flex;
  gap: var(--space-2, 8px);
}
.wf-detail__btn {
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-xs, 0.75rem);
  cursor: pointer;
  transition: border-color var(--transition-fast, 120ms ease);
}
.wf-detail__btn:hover:not(:disabled) {
  border-color: var(--color-accent, #7c8adb);
}
.wf-detail__btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 1px;
}
.wf-detail__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.wf-detail__btn--primary {
  border-color: var(--color-accent, #7c8adb);
  color: var(--color-accent, #7c8adb);
}
.wf-detail__empty {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
}
</style>
