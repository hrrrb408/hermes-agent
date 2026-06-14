<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import {
  useToolAuditStore,
  AUDIT_KINDS,
  AUDIT_KIND_LABELS,
} from '@/stores/toolAudit'
import { SELECTABLE_TOOLS } from '@/constants/readOnlyTools'
import type { AuditEventItem, AuditKind } from '@/types/api/toolAudit'

const store = useToolAuditStore()

const expanded = ref<Set<string>>(new Set())

function toggleExpand(id: string | null): void {
  if (!id) return
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
}

function correlationRows(item: AuditEventItem): { label: string; value: string | null }[] {
  return [
    { label: 'Audit ID', value: item.auditId },
    { label: 'Canonical name', value: item.canonicalName },
    { label: 'Decision', value: item.decision ?? null },
    { label: 'Risk tier', value: item.riskTier ?? null },
    { label: 'Execute request ID', value: item.executeRequestId ?? null },
    { label: 'Dry-run request ID', value: item.dryRunRequestId ?? null },
    { label: 'Pre-execution audit ID', value: item.preExecutionAuditId ?? null },
    { label: 'Handler lookup ID', value: item.handlerLookupId ?? null },
    { label: 'Dispatch ID', value: item.dispatchId ?? null },
    { label: 'Handler call ID', value: item.handlerCallId ?? null },
    { label: 'Digest (short)', value: item.dryRunDecisionDigest ?? null },
    { label: 'Execution status', value: item.executionStatus ?? null },
    { label: 'Handler call status', value: item.handlerCallStatus ?? null },
  ].filter((row) => row.value !== null && row.value !== undefined)
}

function sideEffectRows(item: AuditEventItem): { label: string; value: boolean }[] | null {
  if (!item.sideEffects) return null
  return [
    { label: 'Provider schema sent', value: item.sideEffects.providerSchemaSent },
    { label: 'Provider API called', value: item.sideEffects.providerApiCalled },
    { label: 'External side effects', value: item.sideEffects.externalSideEffects },
  ]
}

onMounted(() => {
  if (store.state === 'idle') {
    store.loadEvents()
  }
})

onUnmounted(() => {
  store.reset()
})

function refresh(): void {
  store.loadEvents()
}

function switchKind(kind: AuditKind): void {
  store.setAuditKind(kind)
  expanded.value.clear()
  store.loadEvents()
}
</script>

<template>
  <section class="workspace-panel__section" aria-label="Audit Viewer">
    <div class="panel-header">
      <span class="panel-badge">Read-only</span>
    </div>

    <p class="audit-viewer__intro">
      Read-only audit events. Raw tokens, full token hashes, raw arguments,
      secrets, and provider payloads are never surfaced.
    </p>

    <!-- Kind tabs -->
    <div class="audit-viewer__tabs" role="tablist" aria-label="Audit kind">
      <button
        v-for="kind in AUDIT_KINDS"
        :id="`audit-viewer-tab-${kind}`"
        :key="kind"
        type="button"
        role="tab"
        class="audit-viewer__tab"
        :class="{ 'audit-viewer__tab--active': store.auditKind === kind }"
        :aria-selected="store.auditKind === kind"
        @click="switchKind(kind)"
      >
        {{ AUDIT_KIND_LABELS[kind] }}
      </button>
    </div>

    <!-- Controls -->
    <div class="audit-viewer__controls">
      <label class="audit-viewer__control">
        <span>Limit</span>
        <select
          class="audit-viewer__select"
          :value="store.limit"
          @change="store.setLimit(Number(($event.target as HTMLSelectElement).value))"
        >
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </label>
      <label class="audit-viewer__control">
        <span>Tool (toolId)</span>
        <select
          id="audit-viewer-tool-filter"
          class="audit-viewer__select"
          :value="store.canonicalNameFilter"
          @change="store.setCanonicalNameFilter(($event.target as HTMLSelectElement).value)"
        >
          <option value="">All tools</option>
          <option v-for="tool in SELECTABLE_TOOLS" :key="tool.id" :value="tool.id">
            {{ tool.displayName }} ({{ tool.id }})
          </option>
        </select>
      </label>
      <button
        id="audit-viewer-refresh"
        type="button"
        class="audit-viewer__btn"
        :disabled="store.isLoading"
        @click="refresh"
      >
        Refresh
      </button>
    </div>

    <p v-if="store.error" class="audit-viewer__error" role="alert">{{ store.error }}</p>

    <!-- Empty state -->
    <p
      v-if="store.state === 'empty'"
      id="audit-viewer-empty"
      class="audit-viewer__empty"
    >
      No {{ AUDIT_KIND_LABELS[store.auditKind] }} audit events recorded yet.
    </p>

    <p v-if="store.skippedMalformed > 0" class="audit-viewer__note">
      {{ store.skippedMalformed }} malformed line(s) safely skipped.
    </p>

    <!-- Event list -->
    <ul v-if="store.items.length > 0" id="audit-viewer-list" class="audit-viewer__list">
      <li
        v-for="item in store.items"
        :key="item.auditId ?? item.timestamp ?? ''"
        class="audit-viewer__item"
      >
        <button
          type="button"
          class="audit-viewer__item-head"
          :aria-expanded="expanded.has(item.auditId ?? '')"
          @click="toggleExpand(item.auditId)"
        >
          <span class="audit-viewer__item-ts">{{ item.timestamp ?? '—' }}</span>
          <span class="audit-viewer__item-cn">{{ item.canonicalName ?? '—' }}</span>
          <span class="audit-viewer__item-dec">{{ item.decision ?? item.executionStatus ?? '—' }}</span>
        </button>
        <dl v-if="expanded.has(item.auditId ?? '')" class="audit-viewer__dl">
          <div v-for="row in correlationRows(item)" :key="row.label">
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </div>
        </dl>
        <ul
          v-if="expanded.has(item.auditId ?? '') && sideEffectRows(item)"
          class="audit-viewer__flags"
        >
          <li v-for="flag in sideEffectRows(item)" :key="flag.label">
            <span>{{ flag.label }}:</span>
            <span
              class="audit-viewer__flag"
              :class="{ 'audit-viewer__flag--false': !flag.value }"
            >{{ flag.value }}</span>
          </li>
        </ul>
      </li>
    </ul>

    <!-- Pagination -->
    <button
      v-if="store.hasMore"
      id="audit-viewer-load-more"
      type="button"
      class="audit-viewer__btn audit-viewer__btn--ghost"
      :disabled="store.isLoading"
      @click="store.loadMore()"
    >
      Load more
    </button>
  </section>
</template>

<style scoped>
.audit-viewer__intro {
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-secondary, #a0a0aa);
  margin: 0 0 var(--space-3, 12px);
  line-height: 1.5;
}

.audit-viewer__tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  margin-bottom: var(--space-2, 8px);
}

.audit-viewer__tab {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: none;
  background: transparent;
  color: var(--color-text-secondary, #a0a0aa);
  font-size: var(--font-size-sm, 0.8125rem);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.audit-viewer__tab--active {
  color: var(--color-text-primary, #e4e4e8);
  border-bottom-color: var(--color-accent, #7c8adb);
}

.audit-viewer__tab:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: -2px;
}

.audit-viewer__controls {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: var(--space-2, 8px);
}

.audit-viewer__control {
  display: flex;
  flex-direction: column;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  gap: 2px;
}

.audit-viewer__select,
.audit-viewer__input {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  background: var(--color-surface, transparent);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-sm, 0.8125rem);
}

.audit-viewer__btn {
  padding: var(--space-1, 4px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.04));
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-sm, 0.8125rem);
  cursor: pointer;
}

.audit-viewer__btn:disabled { opacity: 0.5; cursor: not-allowed; }
.audit-viewer__btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 1px;
}
.audit-viewer__btn--ghost { background: transparent; }

.audit-viewer__error { font-size: var(--font-size-xs, 0.75rem); color: var(--color-danger, #e5656b); }
.audit-viewer__empty { font-size: var(--font-size-sm, 0.8125rem); color: var(--color-text-secondary, #a0a0aa); }
.audit-viewer__note { font-size: var(--font-size-xs, 0.75rem); color: var(--color-text-secondary, #a0a0aa); }

.audit-viewer__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.audit-viewer__item {
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 4px);
  overflow: hidden;
}

.audit-viewer__item-head {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--space-2, 8px);
  width: 100%;
  text-align: left;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: none;
  background: var(--color-surface-raised, rgba(255, 255, 255, 0.03));
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-xs, 0.75rem);
  cursor: pointer;
}

.audit-viewer__item-head:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: -2px;
}

.audit-viewer__item-ts { color: var(--color-text-secondary, #a0a0aa); }
.audit-viewer__item-dec { color: var(--color-text-secondary, #a0a0aa); }

.audit-viewer__dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px var(--space-2, 8px);
  font-size: var(--font-size-xs, 0.75rem);
  margin: 0;
  padding: var(--space-2, 8px);
  border-top: 1px solid var(--color-border, rgba(255, 255, 255, 0.06));
}

.audit-viewer__dl dt { color: var(--color-text-secondary, #a0a0aa); }
.audit-viewer__dl dd { margin: 0; word-break: break-all; }

.audit-viewer__flags {
  list-style: none;
  margin: 0;
  padding: 0 var(--space-2, 8px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 0.75rem);
}

.audit-viewer__flags li {
  display: flex;
  justify-content: space-between;
  padding: 1px 0;
  color: var(--color-text-secondary, #a0a0aa);
}

.audit-viewer__flag--false { color: var(--color-success, #5eba7d); }
</style>
