<script setup lang="ts">
/**
 * Dev Console → Workflow section (Phase 3A).
 *
 * Composes the create-plan form, plan preview, step list + detail, approval
 * gate, timeline, and safety boundary into the dev-only Agent Workflow MVP. The
 * workflow is manual + approval-gated + audit-linked; write/rollback steps are
 * preview/reference-only. Audit links cross-navigate to the Audit Viewer.
 */
import { computed, onMounted, ref } from 'vue'
import { useToolWorkflowStore } from '@/stores/toolWorkflow'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import WorkflowPlanForm from './WorkflowPlanForm.vue'
import WorkflowPlanPreview from './WorkflowPlanPreview.vue'
import WorkflowStepList from './WorkflowStepList.vue'
import WorkflowStepDetail from './WorkflowStepDetail.vue'
import WorkflowTimeline from './WorkflowTimeline.vue'
import WorkflowSafetyBoundary from './WorkflowSafetyBoundary.vue'

const store = useToolWorkflowStore()
const nav = useDevConsoleNavStore()

const selectedStepId = ref<string | null>(null)

const boundary = computed(
  () =>
    store.execution?.safetyBoundary ??
    store.plan?.safetyBoundary ?? {
      realProvider: 'blocked',
      providerAutoWrite: 'blocked',
      autonomousWrite: 'blocked',
      writeExecute: 'blocked',
      rollbackExecute: 'blocked',
      shellCommand: 'blocked',
      databaseMutation: 'blocked',
      externalServiceWrite: 'blocked',
      productionRollout: 'blocked',
      sandboxWritePreview: 'allowed',
      rollbackReference: 'allowed',
      fakeProvider: 'allowed',
      manualApproval: 'required',
      audit: 'enabled',
    },
)

const steps = computed(() => store.execution?.steps ?? [])
const timeline = computed(() => store.execution?.timeline ?? [])
const selectedStep = computed(
  () => steps.value.find((s) => s.stepId === selectedStepId.value) ?? null,
)
const selectedPreview = computed(() =>
  selectedStepId.value ? store.stepPreviews[selectedStepId.value] ?? null : null,
)
const selectedHasToken = computed(() =>
  selectedStepId.value ? !!store.approvalTokens[selectedStepId.value] : false,
)

function selectStep(stepId: string): void {
  selectedStepId.value = stepId
}

async function previewStep(stepId: string): Promise<void> {
  await store.previewStep(stepId)
}

async function executeStep(stepId: string): Promise<void> {
  await store.executeStep(stepId)
}

async function locate(id: string): Promise<void> {
  await nav.prefillAuditSearch(id)
}

onMounted(() => {
  store.loadExecutions()
})
</script>

<template>
  <section class="devconsole-section wf-section" aria-label="Workflow">
    <div class="devconsole-section__intro">
      <h2>Workflow</h2>
      <p>
        Dev-only Agent Workflow MVP. Manual, approval-gated step execution that
        chains the read-only tool, fake provider, sandbox write preview, and
        rollback reference capabilities into an audited plan.
        <strong>No real provider, no autonomous write, no shell / database /
        external service write, no production rollout.</strong>
        Write and rollback steps are preview / reference only — execute the
        actual write or rollback through its existing confirmation flow.
      </p>
    </div>

    <WorkflowPlanForm />

    <p v-if="store.error" class="wf-section__error" role="alert" data-testid="dev-workflow-error">{{ store.error }}</p>

    <WorkflowPlanPreview v-if="store.plan" :plan="store.plan" />

    <div v-if="store.hasExecution" class="wf-section__grid">
      <div class="wf-section__col">
        <h3 class="wf-section__heading">Steps</h3>
        <WorkflowStepList
          :steps="steps"
          :cursor-step-id="store.execution?.cursorStepId"
          :selected-step-id="selectedStepId"
          @select="selectStep"
        />
      </div>
      <div class="wf-section__col">
        <WorkflowStepDetail
          :step="selectedStep"
          :preview="selectedPreview"
          :has-approval-token="selectedHasToken"
          :loading="store.phase === 'loading'"
          @preview="previewStep"
          @execute="executeStep"
          @navigate="locate"
        />
      </div>
    </div>

    <WorkflowTimeline
      v-if="store.hasExecution"
      :events="timeline"
      @navigate="locate"
    />

    <WorkflowSafetyBoundary :boundary="boundary" />
  </section>
</template>

<style scoped>
.wf-section {
  display: grid;
  gap: var(--space-3, 12px);
}
.wf-section__error {
  margin: 0;
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-error, #e5656b);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-error-soft, rgba(229, 101, 107, 0.12));
  color: var(--color-error, #e5656b);
  font-size: var(--font-size-xs, 0.75rem);
}
.wf-section__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
  gap: var(--space-3, 12px);
}
@media (max-width: 960px) {
  .wf-section__grid {
    grid-template-columns: 1fr;
  }
}
.wf-section__col {
  display: grid;
  gap: var(--space-2, 8px);
  align-content: start;
}
.wf-section__heading {
  margin: 0;
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #6a6a74);
}
</style>
