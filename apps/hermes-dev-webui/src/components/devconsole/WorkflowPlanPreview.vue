<script setup lang="ts">
/**
 * Phase 3A workflow plan preview.
 *
 * Renders the built plan: workflow / plan / execution ids, the planned steps,
 * the blocked steps (each with its blocked reason), required approvals, and the
 * audit preview. Blocked steps reuse the unified BlockedReasonPanel.
 */
import BlockedReasonPanel from '@/components/common/BlockedReasonPanel.vue'
import { formatStepType } from '@/lib/workflowFormatters'
import type { WorkflowPlan } from '@/lib/workflowTypes'

defineProps<{
  plan: WorkflowPlan
}>()
</script>

<template>
  <section
    class="wf-planpreview"
    aria-label="Workflow plan preview"
    data-testid="dev-workflow-plan-preview"
  >
    <header class="wf-planpreview__head">
      <h3 class="wf-planpreview__title">{{ plan.title }}</h3>
      <dl class="wf-planpreview__ids">
        <div><dt>workflow</dt><dd data-testid="dev-workflow-id">{{ plan.workflowId }}</dd></div>
        <div><dt>plan</dt><dd>{{ plan.workflowPlanId }}</dd></div>
        <div v-if="plan.workflowExecutionId"><dt>execution</dt><dd data-testid="dev-workflow-execution-id">{{ plan.workflowExecutionId }}</dd></div>
        <div><dt>approvals</dt><dd>{{ plan.requiredApprovals }}</dd></div>
      </dl>
    </header>
    <p v-if="plan.goal" class="wf-planpreview__goal">{{ plan.goal }}</p>
    <p class="wf-planpreview__summary" data-testid="dev-workflow-plan-summary">{{ plan.summary }}</p>

    <h4 class="wf-planpreview__heading">Planned steps ({{ plan.steps.length }})</h4>
    <ol v-if="plan.steps.length > 0" class="wf-planpreview__steps">
      <li
        v-for="step in plan.steps"
        :key="step.stepId"
        class="wf-planpreview__step"
        :data-testid="`dev-workflow-planned-step-${step.stepType}`"
      >
        <span class="wf-planpreview__steptype">{{ formatStepType(step.stepType) }}</span>
        <span class="wf-planpreview__steptitle">{{ step.title }}</span>
        <span v-if="step.toolId" class="wf-planpreview__steptool">{{ step.toolId }}</span>
      </li>
    </ol>
    <p v-else class="wf-planpreview__empty">No runnable steps — the plan is fully blocked.</p>

    <template v-if="plan.blockedSteps.length > 0">
      <h4 class="wf-planpreview__heading">Blocked steps ({{ plan.blockedSteps.length }})</h4>
      <div class="wf-planpreview__blocked">
        <BlockedReasonPanel
          v-for="step in plan.blockedSteps"
          :key="step.stepId"
          :code="step.blockedReason"
          :title="`${formatStepType(step.stepType)} blocked`"
        />
      </div>
    </template>
  </section>
</template>

<style scoped>
.wf-planpreview {
  display: grid;
  gap: var(--space-3, 12px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}
.wf-planpreview__head {
  display: grid;
  gap: var(--space-2, 8px);
}
.wf-planpreview__title {
  margin: 0;
  font-size: var(--font-size-base, 0.9375rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-planpreview__ids {
  display: flex;
  gap: var(--space-3, 12px);
  flex-wrap: wrap;
  margin: 0;
}
.wf-planpreview__ids div {
  display: grid;
  gap: 1px;
}
.wf-planpreview__ids dt {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #6a6a74);
}
.wf-planpreview__ids dd {
  margin: 0;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-planpreview__goal,
.wf-planpreview__summary {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-planpreview__heading {
  margin: 0;
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #6a6a74);
}
.wf-planpreview__steps {
  list-style: decimal inside;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.wf-planpreview__step {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: baseline;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-planpreview__steptype {
  color: var(--color-accent, #7c8adb);
}
.wf-planpreview__steptool {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.625rem;
  color: var(--color-text-muted, #6a6a74);
}
.wf-planpreview__empty {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-warning, #d4a843);
}
.wf-planpreview__blocked {
  display: grid;
  gap: var(--space-2, 8px);
}
</style>
