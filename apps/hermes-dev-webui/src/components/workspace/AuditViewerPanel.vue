<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import {
  useToolAuditStore,
  AUDIT_KINDS,
  AUDIT_KIND_LABELS,
} from '@/stores/toolAudit'
import { SELECTABLE_TOOLS } from '@/constants/readOnlyTools'
import type {
  AuditEventItem,
  AuditKind,
  StoreAuditEventItem,
} from '@/types/api/toolAudit'

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

function storeCorrelationRows(item: StoreAuditEventItem): { label: string; value: string | null }[] {
  return [
    { label: 'Event ID', value: item.eventId },
    { label: 'Sequence', value: item.sequence !== null ? String(item.sequence) : null },
    { label: 'Tool', value: item.toolId ?? null },
    { label: 'Status', value: item.status ?? null },
    { label: 'Blocked reason', value: item.blockedReason ?? null },
    { label: 'Source', value: item.source ?? null },
    { label: 'Provider mode', value: item.providerMode ?? null },
    { label: 'Execution ID', value: item.executionId ?? null },
    { label: 'Pre-exec audit', value: item.preExecutionAuditId ?? null },
    { label: 'Post-exec audit', value: item.postExecutionAuditId ?? null },
    { label: 'Write plan', value: item.writePlanId ?? null },
    { label: 'Rollback', value: item.rollbackId ?? null },
    { label: 'Confirmation token', value: item.confirmationTokenId ?? null },
  ].filter((row) => row.value !== null && row.value !== undefined)
}

onMounted(() => {
  if (store.state === 'idle' && !store.storeMode) {
    store.loadEvents()
  }
})

onUnmounted(() => {
  store.reset()
})

function refresh(): void {
  if (store.storeMode) {
    store.loadStoreEvents()
  } else {
    store.loadEvents()
  }
}

function switchKind(kind: AuditKind): void {
  store.setAuditKind(kind)
  expanded.value.clear()
  if (store.storeMode) {
    store.loadStoreEvents()
  } else {
    store.loadEvents()
  }
}

function toggleStoreMode(): void {
  store.setStoreMode(!store.storeMode)
  expanded.value.clear()
  if (store.storeMode) {
    store.loadStoreEvents()
  } else {
    store.loadEvents()
  }
}

function applyStoreFilters(): void {
  expanded.value.clear()
  store.loadStoreEvents()
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

    <!-- Phase 2D: durable-store mode toggle + status badges -->
    <div class="audit-viewer__mode-row">
      <button
        id="audit-viewer-store-toggle"
        type="button"
        class="audit-viewer__btn"
        :class="{ 'audit-viewer__btn--active': store.storeMode }"
        :aria-pressed="store.storeMode"
        @click="toggleStoreMode"
      >
        {{ store.storeMode ? 'Store query: ON' : 'Store query: OFF' }}
      </button>
      <span
        v-if="store.storeMode && store.storeStatus"
        id="audit-viewer-store-status"
        class="audit-viewer__badge"
        :class="{ 'audit-viewer__badge--warn': !store.storeStatus.present }"
      >
        Store: {{ store.storeStatus.present ? 'present' : 'absent' }} ·
        {{ store.storeSegmentCount }} segment(s)
      </span>
      <span
        v-if="store.storeMode && store.indexStatus"
        id="audit-viewer-index-status"
        class="audit-viewer__badge"
        :class="{
          'audit-viewer__badge--warn': store.indexStale,
          'audit-viewer__badge--ok': !store.indexStale && store.indexStatus.present,
        }"
      >
        Index: {{ store.indexStatus.present ? (store.indexStale ? 'stale' : 'consistent') : 'missing' }}
      </span>
      <span
        v-if="store.storeMode && store.storeSchemaVersion"
        id="audit-viewer-schema-version"
        class="audit-viewer__badge"
      >{{ store.storeSchemaVersion }}</span>
    </div>

    <p
      v-if="store.storeMode && store.corruptSkipped > 0"
      id="audit-viewer-corrupt-warning"
      class="audit-viewer__warn"
      role="alert"
    >
      ⚠ {{ store.corruptSkipped }} corrupt line(s) detected and safely skipped. Run store repair to quarantine.
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

    <!-- Legacy controls (hidden in store mode) -->
    <div v-if="!store.storeMode" class="audit-viewer__controls">
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

    <!-- Phase 2D store-mode filters -->
    <div v-if="store.storeMode" id="audit-viewer-store-controls" class="audit-viewer__controls audit-viewer__controls--store">
      <label class="audit-viewer__control">
        <span>Limit</span>
        <select
          id="audit-viewer-store-limit"
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
        <span id="audit-viewer-eventtype-label">eventType</span>
        <input
          id="audit-viewer-eventtype-filter"
          class="audit-viewer__input"
          :value="store.eventTypeFilter"
          placeholder="e.g. clarify_execution_completed"
          @input="store.setEventTypeFilter(($event.target as HTMLInputElement).value)"
        />
      </label>
      <label class="audit-viewer__control">
        <span id="audit-viewer-status-label">status</span>
        <select
          id="audit-viewer-status-filter"
          class="audit-viewer__select"
          :value="store.statusFilter"
          @change="store.setStatusFilter(($event.target as HTMLSelectElement).value)"
        >
          <option value="">Any</option>
          <option value="ok">ok</option>
          <option value="blocked">blocked</option>
          <option value="error">error</option>
          <option value="preview">preview</option>
          <option value="completed">completed</option>
        </select>
      </label>
      <label class="audit-viewer__control">
        <span>providerMode</span>
        <select
          id="audit-viewer-provider-mode-filter"
          class="audit-viewer__select"
          :value="store.providerModeFilter"
          @change="store.setProviderModeFilter(($event.target as HTMLSelectElement).value)"
        >
          <option value="">Any</option>
          <option value="disabled">disabled</option>
          <option value="fake">fake</option>
          <option value="real">real</option>
        </select>
      </label>
      <label class="audit-viewer__control">
        <span id="audit-viewer-write-required-label">writeRequired</span>
        <select
          id="audit-viewer-write-required-filter"
          class="audit-viewer__select"
          :value="store.writeRequiredFilter"
          @change="store.setWriteRequiredFilter(($event.target as HTMLSelectElement).value)"
        >
          <option value="">Any</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </label>
      <label class="audit-viewer__control audit-viewer__control--grow">
        <span id="audit-viewer-search-label">safe search</span>
        <input
          id="audit-viewer-search-input"
          class="audit-viewer__input"
          :value="store.searchInput"
          placeholder="search summary / metadata"
          @keydown.enter="applyStoreFilters"
          @input="store.setSearchInput(($event.target as HTMLInputElement).value)"
        />
      </label>
      <button
        id="audit-viewer-store-apply"
        type="button"
        class="audit-viewer__btn"
        :disabled="store.isLoading"
        @click="applyStoreFilters"
      >
        Apply
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

    <!-- Legacy event list -->
    <ul v-if="!store.storeMode && store.items.length > 0" id="audit-viewer-list" class="audit-viewer__list">
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

    <!-- Phase 2D store event list -->
    <ul v-if="store.storeMode && store.storeItems.length > 0" id="audit-viewer-store-list" class="audit-viewer__list">
      <li
        v-for="item in store.storeItems"
        :key="item.eventId ?? item.sequence ?? ''"
        class="audit-viewer__item"
      >
        <button
          type="button"
          class="audit-viewer__item-head"
          :aria-expanded="expanded.has(item.eventId ?? '')"
          @click="toggleExpand(item.eventId)"
        >
          <span class="audit-viewer__item-ts">{{ item.createdAt ?? '—' }}</span>
          <span class="audit-viewer__item-cn">{{ item.eventType ?? '—' }}</span>
          <span class="audit-viewer__item-dec">{{ item.auditKind ?? '—' }}</span>
          <span
            v-if="item.redactionApplied"
            id="audit-viewer-redaction-badge"
            class="audit-viewer__badge audit-viewer__badge--ok"
          >redacted</span>
        </button>
        <dl v-if="expanded.has(item.eventId ?? '')" class="audit-viewer__dl">
          <div v-for="row in storeCorrelationRows(item)" :key="row.label">
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </div>
        </dl>
      </li>
    </ul>

    <!-- Pagination -->
    <button
      v-if="!store.storeMode && store.hasMore"
      id="audit-viewer-load-more"
      type="button"
      class="audit-viewer__btn audit-viewer__btn--ghost"
      :disabled="store.isLoading"
      @click="store.loadMore()"
    >
      Load more
    </button>
    <button
      v-if="store.storeMode && store.storeHasMore"
      id="audit-viewer-store-next"
      type="button"
      class="audit-viewer__btn audit-viewer__btn--ghost"
      :disabled="store.isLoading"
      @click="store.loadStoreNext()"
    >
      Next page (cursor)
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

.audit-viewer__mode-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}

.audit-viewer__badge {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  background: var(--color-surface, transparent);
}

.audit-viewer__badge--ok {
  color: var(--color-success, #5eba7d);
  border-color: var(--color-success, #5eba7d);
}

.audit-viewer__badge--warn {
  color: var(--color-warning, #d9a441);
  border-color: var(--color-warning, #d9a441);
}

.audit-viewer__btn--active {
  border-color: var(--color-accent, #7c8adb);
  color: var(--color-accent, #7c8adb);
}

.audit-viewer__warn {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-warning, #d9a441);
  margin: 0 0 var(--space-2, 8px);
}

.audit-viewer__controls--store {
  align-items: flex-end;
}

.audit-viewer__control--grow {
  flex: 1 1 160px;
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
