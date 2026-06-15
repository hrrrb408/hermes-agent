<script setup lang="ts">
/**
 * Phase 3A workflow create-plan form.
 *
 * Lets the operator compose a workflow plan: title, goal, and an ordered list of
 * draft steps. The form never accepts an API key, secret, token, or password —
 * only public plan metadata and step inputs (tool id, message text, note text,
 * a sandbox-relative target path).
 */
import { computed } from 'vue'
import { useToolWorkflowStore } from '@/stores/toolWorkflow'

const store = useToolWorkflowStore()

const STEP_TYPES = [
  { value: 'read_only_tool', label: 'Read-only tool' },
  { value: 'fake_provider_roundtrip', label: 'Fake provider round-trip' },
  { value: 'sandbox_write_preview', label: 'Sandbox write preview' },
  { value: 'rollback_reference', label: 'Rollback reference' },
  { value: 'manual_note', label: 'Manual note' },
  { value: 'audit_query', label: 'Audit query' },
] as const

const READ_ONLY_TOOLS = [
  'dev_environment_read',
  'tool_policy_read',
  'route_governance_read',
  'audit_events_read',
  'release_status_read',
  'clarify',
] as const

const canBuild = computed(
  () => store.title.trim().length > 0 && store.draftSteps.length > 0 && store.phase !== 'loading',
)
</script>

<template>
  <section
    class="wf-form"
    aria-label="Create workflow plan"
    data-testid="dev-workflow-plan-form"
  >
    <h3 class="wf-form__title">Create plan</h3>
    <div class="wf-form__row">
      <label class="wf-form__field">
        <span class="wf-form__label">Title</span>
        <input
          v-model="store.title"
          class="wf-form__input"
          type="text"
          maxlength="200"
          placeholder="Workflow title"
          data-testid="dev-workflow-title-input"
        />
      </label>
      <label class="wf-form__field">
        <span class="wf-form__label">Goal</span>
        <input
          v-model="store.goal"
          class="wf-form__input"
          type="text"
          maxlength="2000"
          placeholder="Optional goal"
          data-testid="dev-workflow-goal-input"
        />
      </label>
    </div>

    <ol class="wf-form__steps" aria-label="Draft steps">
      <li
        v-for="(row, index) in store.draftSteps"
        :key="index"
        class="wf-form__step"
        :data-testid="`dev-workflow-draft-step-${index}`"
      >
        <select
          class="wf-form__select"
          :value="row.stepType"
          aria-label="Step type"
          @change="store.setDraftStep(index, { stepType: ($event.target as HTMLSelectElement).value })"
        >
          <option v-for="t in STEP_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>

        <select
          v-if="row.stepType === 'read_only_tool'"
          class="wf-form__select"
          :value="row.toolId"
          aria-label="Read-only tool"
          @change="store.setDraftStep(index, { toolId: ($event.target as HTMLSelectElement).value })"
        >
          <option v-for="tool in READ_ONLY_TOOLS" :key="tool" :value="tool">{{ tool }}</option>
        </select>

        <input
          v-if="row.stepType === 'fake_provider_roundtrip'"
          v-model="row.message"
          class="wf-form__input"
          type="text"
          maxlength="4000"
          placeholder="Provider message"
          aria-label="Provider message"
          @input="store.setDraftStep(index, { message: ($event.target as HTMLInputElement).value })"
        />

        <input
          v-if="row.stepType === 'sandbox_write_preview'"
          v-model="row.targetRelativePath"
          class="wf-form__input"
          type="text"
          maxlength="512"
          placeholder="notes/example.md (sandbox-relative)"
          aria-label="Target relative path"
          @input="store.setDraftStep(index, { targetRelativePath: ($event.target as HTMLInputElement).value })"
        />

        <input
          v-if="row.stepType === 'manual_note'"
          v-model="row.note"
          class="wf-form__input"
          type="text"
          maxlength="2000"
          placeholder="Note text"
          aria-label="Manual note text"
          @input="store.setDraftStep(index, { note: ($event.target as HTMLInputElement).value })"
        />

        <span v-if="row.stepType === 'rollback_reference'" class="wf-form__hint">References stored rollback manifests (read-only).</span>
        <span v-if="row.stepType === 'audit_query'" class="wf-form__hint">Read-only dev audit query.</span>

        <button
          type="button"
          class="wf-form__remove"
          :disabled="store.draftSteps.length <= 1"
          :aria-label="`Remove step ${index + 1}`"
          @click="store.removeDraftStep(index)"
        >−</button>
      </li>
    </ol>

    <div class="wf-form__actions">
      <button type="button" class="wf-form__btn" :disabled="store.draftSteps.length >= 8" @click="store.addDraftStep()">+ Add step</button>
      <button
        type="button"
        class="wf-form__btn wf-form__btn--primary"
        :disabled="!canBuild"
        data-testid="dev-workflow-build-plan-btn"
        @click="store.buildPlan()"
      >Build plan</button>
    </div>
  </section>
</template>

<style scoped>
.wf-form {
  display: grid;
  gap: var(--space-3, 12px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}
.wf-form__title {
  margin: 0;
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-form__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2, 8px);
}
.wf-form__field {
  display: grid;
  gap: 2px;
}
.wf-form__label {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #6a6a74);
}
.wf-form__input,
.wf-form__select {
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface, rgba(0, 0, 0, 0.2));
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-xs, 0.75rem);
}
.wf-form__input:focus-visible,
.wf-form__select:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 1px;
}
.wf-form__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-2, 8px);
}
.wf-form__step {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: center;
  flex-wrap: wrap;
}
.wf-form__hint {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
}
.wf-form__remove {
  padding: 2px 8px;
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: transparent;
  color: var(--color-text-secondary, #a0a0aa);
  cursor: pointer;
}
.wf-form__remove:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.wf-form__actions {
  display: flex;
  gap: var(--space-2, 8px);
}
.wf-form__btn {
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-xs, 0.75rem);
  cursor: pointer;
}
.wf-form__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.wf-form__btn--primary {
  border-color: var(--color-accent, #7c8adb);
  color: var(--color-accent, #7c8adb);
}
</style>
