<script setup lang="ts">
/**
 * Phase 3A workflow timeline.
 *
 * Renders the execution's append-only timeline as an ordered list. Each event
 * shows its type, timestamp, the step it relates to, and any audit links
 * (cross-navigation chips). No secrets or tokens are rendered — only public
 * correlation ids.
 */
import { computed } from 'vue'
import AuditIdLink from '@/components/common/AuditIdLink.vue'
import { lookupBlockedReason } from '@/lib/blockedReasons'
import { formatStepType } from '@/lib/workflowFormatters'
import type { WorkflowTimelineEvent } from '@/lib/workflowTypes'

const props = defineProps<{
  events: readonly WorkflowTimelineEvent[]
}>()

const emit = defineEmits<{
  navigate: [id: string]
}>()

const ordered = computed(() =>
  [...props.events].map((event) => ({
    ...event,
    blockedTitle: event.blockedReason ? lookupBlockedReason(event.blockedReason).title : null,
  })),
)
</script>

<template>
  <section
    class="wf-timeline"
    aria-label="Workflow timeline"
    data-testid="dev-workflow-timeline"
  >
    <h3 class="wf-timeline__title">Timeline</h3>
    <p v-if="ordered.length === 0" class="wf-timeline__empty">
      No timeline events yet. Execute steps to build the audit trail.
    </p>
    <ol v-else class="wf-timeline__list">
      <li
        v-for="event in ordered"
        :key="event.eventId"
        class="wf-timeline__event"
        :data-event-type="event.eventType"
      >
        <div class="wf-timeline__head">
          <span class="wf-timeline__type" data-testid="dev-workflow-timeline-type">{{ event.eventType }}</span>
          <span v-if="event.stepType" class="wf-timeline__step">{{ formatStepType(event.stepType) }}</span>
        </div>
        <span class="wf-timeline__time">{{ event.createdAt }}</span>
        <p v-if="event.message" class="wf-timeline__msg">{{ event.message }}</p>
        <span
          v-if="event.blockedTitle"
          class="wf-timeline__blocked"
          data-testid="dev-workflow-timeline-blocked"
        >{{ event.blockedTitle }}</span>
        <div
          v-if="event.auditLinks && event.auditLinks.length > 0"
          class="wf-timeline__links"
        >
          <AuditIdLink
            v-for="link in event.auditLinks"
            :id="link.auditId"
            :key="link.auditId"
            :label="link.label || 'audit'"
            @navigate="emit('navigate', $event)"
          />
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.wf-timeline {
  display: grid;
  gap: var(--space-2, 8px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
}
.wf-timeline__title {
  margin: 0;
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-timeline__empty {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
}
.wf-timeline__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-2, 8px);
}
.wf-timeline__event {
  display: grid;
  gap: 2px;
  padding: var(--space-2, 8px);
  border-left: 2px solid var(--color-border, rgba(255, 255, 255, 0.12));
  background: var(--color-surface, transparent);
}
.wf-timeline__head {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: center;
  flex-wrap: wrap;
}
.wf-timeline__type {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-accent, #7c8adb);
}
.wf-timeline__step {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}
.wf-timeline__time {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.625rem;
  color: var(--color-text-muted, #6a6a74);
}
.wf-timeline__msg {
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-primary, #e4e4e8);
}
.wf-timeline__blocked {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-error, #e5656b);
}
.wf-timeline__links {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
