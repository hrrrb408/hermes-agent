<script setup lang="ts">
/**
 * Tool Schema Preview Panel — read-only UI.
 *
 * Displays a searchable, filterable catalog of tool schema previews
 * with a detail panel for the selected tool's field-level information.
 *
 * Safety:
 *   - Read-only: no execution, dry-run, provider-send, or dispatch.
 *   - No raw schema, handler, callable, path, or secret is displayed.
 *   - No action buttons that could trigger tool execution.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useToolSchemaPreviewStore } from '@/stores/toolSchemaPreview'
import { RISK_LABELS } from '@/types/api/toolPolicyConstants'
import type { ToolSchemaPreviewItem } from '@/types/api/toolSchemaPreview'
import type { ToolRiskLevel } from '@/types/api/toolPolicy'

const store = useToolSchemaPreviewStore()

// ── Client-side filters ──

const searchQuery = ref('')
const availabilityFilter = ref<'all' | 'available' | 'unavailable'>('all')
const riskFilter = ref<ToolRiskLevel | ''>('')

const RISK_LEVELS: readonly ToolRiskLevel[] = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5']

const filteredItems = computed(() => {
  let result = store.items

  // Search filter
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    result = result.filter(item =>
      item.canonicalName.toLowerCase().includes(q) ||
      item.capabilities.some(cap => cap.toLowerCase().includes(q)) ||
      item.reasonCode.toLowerCase().includes(q),
    )
  }

  // Availability filter
  if (availabilityFilter.value === 'available') {
    result = result.filter(item => item.schemaPreviewAvailable)
  } else if (availabilityFilter.value === 'unavailable') {
    result = result.filter(item => !item.schemaPreviewAvailable)
  }

  // Risk filter
  if (riskFilter.value) {
    result = result.filter(item => item.risk === riskFilter.value)
  }

  return result
})

function clearFilters(): void {
  searchQuery.value = ''
  availabilityFilter.value = 'all'
  riskFilter.value = ''
}

const hasActiveFilters = computed(() =>
  searchQuery.value.trim() !== '' ||
  availabilityFilter.value !== 'all' ||
  riskFilter.value !== '',
)

// ── Selection ──

function selectItem(item: ToolSchemaPreviewItem): void {
  store.fetchPreview(item.canonicalName)
}

function handleListKeyDown(event: KeyboardEvent): void {
  const items = filteredItems.value
  if (items.length === 0) return

  const currentName = store.selectedCanonicalName
  const currentIndex = currentName
    ? items.findIndex(item => item.canonicalName === currentName)
    : -1

  let nextIndex = currentIndex

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    nextIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1
  } else if (event.key === 'Home') {
    event.preventDefault()
    nextIndex = 0
  } else if (event.key === 'End') {
    event.preventDefault()
    nextIndex = items.length - 1
  } else {
    return
  }

  const nextItem = items[nextIndex]
  if (nextItem) {
    selectItem(nextItem)
    document.getElementById(`schema-preview-item-${nextItem.canonicalName}`)?.focus()
  }
}

// ── Lifecycle ──

onMounted(() => {
  if (store.catalogState === 'idle') {
    store.fetchCatalog()
  }
})

onUnmounted(() => {
  store.abortAllRequests()
})
</script>

<template>
  <section class="schema-preview" aria-label="Tool Schema Preview">
    <!-- Read-only notice -->
    <div class="sp-notice" role="status">
      <p class="sp-notice__title">Schema Preview is read-only</p>
      <ul class="sp-notice__list">
        <li>Preview availability does not imply execution availability</li>
        <li>Provider schema is not sent</li>
        <li>Tool execution remains disabled</li>
      </ul>
    </div>

    <!-- Summary cards -->
    <div v-if="store.hasCatalog" class="sp-summary" aria-label="Schema preview summary">
      <div class="sp-summary-card">
        <span class="sp-summary-card__value">{{ store.totalCount }}</span>
        <span class="sp-summary-card__label">Total tools</span>
      </div>
      <div class="sp-summary-card sp-summary-card--available">
        <span class="sp-summary-card__value">{{ store.availableCount }}</span>
        <span class="sp-summary-card__label">Available</span>
      </div>
      <div class="sp-summary-card sp-summary-card--unavailable">
        <span class="sp-summary-card__value">{{ store.unavailableCount }}</span>
        <span class="sp-summary-card__label">Unavailable</span>
      </div>
    </div>

    <!-- Catalog loading -->
    <div v-if="store.isCatalogLoading" class="panel-loading" aria-busy="true" aria-live="polite">
      Loading schema previews…
    </div>

    <!-- Catalog error -->
    <div v-else-if="store.catalogState === 'error'" class="panel-error" role="alert">
      <p>{{ store.catalogError }}</p>
      <button type="button" class="panel-retry-btn" aria-label="Retry loading schema previews" @click="store.fetchCatalog()">Retry preview</button>
    </div>

    <!-- Empty catalog -->
    <div v-else-if="store.catalogState === 'empty'" class="panel-empty">
      No schema preview data available.
    </div>

    <!-- Catalog content -->
    <template v-else-if="store.hasCatalog">
      <!-- Filters -->
      <div class="sp-filters">
        <label for="sp-search" class="sp-sr-only">Search tools by name, capability, or reason code</label>
        <input
          id="sp-search"
          v-model="searchQuery"
          type="search"
          class="sp-filter-input"
          placeholder="Search tools…"
          maxlength="120"
        />

        <label for="sp-availability" class="sp-sr-only">Filter by availability</label>
        <select id="sp-availability" v-model="availabilityFilter" class="sp-filter-select">
          <option value="all">All tools</option>
          <option value="available">Available</option>
          <option value="unavailable">Unavailable</option>
        </select>

        <label for="sp-risk" class="sp-sr-only">Filter by risk level</label>
        <select id="sp-risk" v-model="riskFilter" class="sp-filter-select">
          <option value="">All risks</option>
          <option v-for="level in RISK_LEVELS" :key="level" :value="level">
            {{ level }} — {{ RISK_LABELS[level] }}
          </option>
        </select>

        <button
          v-if="hasActiveFilters"
          type="button"
          class="sp-clear-btn"
          aria-label="Clear all filters"
          @click="clearFilters"
        >
          Clear filters
        </button>
      </div>

      <!-- Content: list + detail -->
      <div class="sp-content">
        <!-- Tool list -->
        <div class="sp-list" role="listbox" aria-label="Schema preview tool list" @keydown="handleListKeyDown">
          <div
            v-for="item in filteredItems"
            :id="`schema-preview-item-${item.canonicalName}`"
            :key="item.canonicalName"
            role="option"
            class="sp-item"
            :class="{ 'sp-item--selected': store.selectedCanonicalName === item.canonicalName }"
            :aria-selected="store.selectedCanonicalName === item.canonicalName"
            tabindex="0"
            @click="selectItem(item)"
            @keydown.enter="selectItem(item)"
            @keydown.space.prevent="selectItem(item)"
          >
            <div class="sp-item__header">
              <span class="sp-item__name">{{ item.canonicalName }}</span>
              <span class="sp-item__risk" :class="`sp-item__risk--${item.risk}`">{{ item.risk }}</span>
            </div>
            <div class="sp-item__meta">
              <span
                class="sp-item__status"
                :class="item.schemaPreviewAvailable ? 'sp-item__status--available' : 'sp-item__status--unavailable'"
              >
                {{ item.schemaPreviewAvailable ? 'Preview available' : 'Unavailable' }}
              </span>
              <span v-if="item.redactionStatus !== 'clean'" class="sp-item__redaction">
                {{ item.redactionStatus === 'redacted' ? 'Redacted' : item.redactionStatus }}
              </span>
            </div>
            <div class="sp-item__capabilities">
              <span v-for="cap in item.capabilities.slice(0, 3)" :key="cap" class="sp-cap-badge">{{ cap }}</span>
              <span v-if="item.capabilities.length > 3" class="sp-cap-badge sp-cap-badge--more">+{{ item.capabilities.length - 3 }}</span>
            </div>
            <span v-if="!item.schemaPreviewAvailable && item.unavailableReason" class="sp-item__reason">
              {{ item.unavailableReason }}
            </span>
          </div>

          <!-- Filtered empty -->
          <div v-if="filteredItems.length === 0" class="sp-list__empty">
            <p v-if="hasActiveFilters">No tools match the current filters.</p>
            <p v-else>No schema previews found.</p>
          </div>
        </div>

        <!-- Detail panel -->
        <div class="sp-detail" role="region" aria-label="Schema preview detail">
          <!-- Detail loading -->
          <div v-if="store.isPreviewLoading" class="panel-loading" aria-busy="true" aria-live="polite">
            Loading schema detail…
          </div>

          <!-- Detail error -->
          <div v-else-if="store.previewState === 'error'" role="alert">
            <p class="panel-error">{{ store.previewError }}</p>
            <button
              v-if="store.selectedCanonicalName"
              type="button"
              class="panel-retry-btn"
              aria-label="Retry loading schema detail"
              @click="store.fetchPreview(store.selectedCanonicalName)"
            >
              Retry detail
            </button>
          </div>

          <!-- Detail content -->
          <template v-else-if="store.selectedPreview?.found && store.selectedPreview.preview">
            <h4 class="sp-detail__name">{{ store.selectedPreview.preview.canonicalName }}</h4>

            <dl class="context-list">
              <div><dt>Risk</dt><dd><span class="sp-item__risk" :class="`sp-item__risk--${store.selectedPreview.preview.risk}`">{{ store.selectedPreview.preview.risk }}</span> {{ RISK_LABELS[store.selectedPreview.preview.risk as ToolRiskLevel] ?? '' }}</dd></div>
              <div><dt>Schema Shape</dt><dd>{{ store.selectedPreview.preview.schemaShape }}</dd></div>
              <div><dt>Reason Code</dt><dd>{{ store.selectedPreview.preview.reasonCode }}</dd></div>
              <div><dt>Redaction</dt><dd>{{ store.selectedPreview.preview.redactionStatus }}</dd></div>
              <div><dt>Capabilities</dt><dd>{{ store.selectedPreview.preview.capabilities.join(', ') || 'None' }}</dd></div>
              <div v-if="store.selectedPreview.preview.unavailableReason"><dt>Unavailable Reason</dt><dd>{{ store.selectedPreview.preview.unavailableReason }}</dd></div>
            </dl>

            <!-- Input fields -->
            <div v-if="store.selectedPreview.preview.inputFields.length > 0" class="sp-fields">
              <h5 class="sp-fields__heading">Input Fields ({{ store.selectedPreview.preview.inputFields.length }})</h5>
              <div class="sp-field-list">
                <div
                  v-for="field in store.selectedPreview.preview.inputFields"
                  :key="field.fieldName"
                  class="sp-field"
                >
                  <div class="sp-field__header">
                    <span class="sp-field__name">{{ field.fieldName }}</span>
                    <span class="sp-field__type">{{ field.fieldType }}</span>
                    <span v-if="field.required" class="sp-field__required" title="Required">required</span>
                  </div>
                  <p v-if="field.descriptionPreview" class="sp-field__desc">{{ field.descriptionPreview }}</p>
                  <div v-if="field.enumPreview && field.enumPreview.length > 0" class="sp-field__enums">
                    <span v-for="val in field.enumPreview.slice(0, 8)" :key="val" class="sp-enum-badge">{{ val }}</span>
                    <span v-if="field.enumPreview.length > 8" class="sp-enum-badge sp-enum-badge--more">+{{ field.enumPreview.length - 8 }}</span>
                  </div>
                  <span v-if="field.defaultPresence" class="sp-field__default">has default</span>
                  <span v-if="field.constraintsPreview" class="sp-field__constraints">{{ field.constraintsPreview }}</span>
                </div>
              </div>
            </div>
            <p v-else class="sp-fields__empty">No input fields in this schema preview.</p>
          </template>

          <!-- Placeholder -->
          <div v-else class="sp-detail__placeholder">
            <p>Select a tool to view schema preview details</p>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.schema-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

/* Screen reader only labels */
.sp-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Read-only notice */
.sp-notice {
  padding: var(--space-3, 12px);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-warning-soft, rgba(212, 168, 67, 0.12));
  border: 1px solid var(--color-warning, #d4a843);
}

.sp-notice__title {
  font-weight: var(--font-weight-semibold, 600);
  font-size: var(--font-size-sm, 0.8125rem);
  margin: 0 0 var(--space-1, 4px);
  color: var(--color-text-primary, #e4e4e8);
}

.sp-notice__list {
  margin: 0;
  padding-left: var(--space-4, 16px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  line-height: var(--content-line-height, 1.6);
}

.sp-notice__list li {
  margin-bottom: var(--space-1, 4px);
}

/* Summary cards */
.sp-summary {
  display: flex;
  gap: var(--space-2, 8px);
}

.sp-summary-card {
  flex: 1;
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  text-align: center;
}

.sp-summary-card__value {
  display: block;
  font-size: var(--font-size-md, 1rem);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-primary, #e4e4e8);
}

.sp-summary-card__label {
  display: block;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}

.sp-summary-card--available .sp-summary-card__value {
  color: var(--color-success, #5eb87a);
}

.sp-summary-card--unavailable .sp-summary-card__value {
  color: var(--color-warning, #d4a843);
}

/* Filters */
.sp-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  align-items: center;
}

.sp-filter-input,
.sp-filter-select {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-xs, 0.75rem);
  font-family: inherit;
}

.sp-filter-input {
  flex: 1;
  min-width: 120px;
}

.sp-filter-input:focus,
.sp-filter-select:focus {
  outline: none;
  border-color: var(--color-focus-ring, var(--color-accent, #7c8adb));
  box-shadow: 0 0 0 1px var(--color-focus-ring, var(--color-accent, #7c8adb));
}

.sp-clear-btn {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: transparent;
  color: var(--color-text-secondary, #a0a0aa);
  font-size: var(--font-size-xs, 0.75rem);
  cursor: pointer;
  transition: color var(--transition-fast, 120ms ease);
}

.sp-clear-btn:hover {
  color: var(--color-text-primary, #e4e4e8);
}

.sp-clear-btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 2px;
}

/* Content area: list + detail */
.sp-content {
  display: flex;
  gap: var(--space-3, 12px);
  min-height: 200px;
}

/* Tool list */
.sp-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
  overflow-y: auto;
  max-height: 480px;
}

.sp-list__empty {
  padding: var(--space-4, 16px);
  text-align: center;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
}

.sp-item {
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  cursor: pointer;
  transition: background var(--transition-fast, 120ms ease), border-color var(--transition-fast, 120ms ease);
}

.sp-item:hover {
  background: var(--color-hover-bg, rgba(255, 255, 255, 0.06));
}

.sp-item:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: -2px;
}

.sp-item--selected {
  background: var(--color-active-bg, rgba(255, 255, 255, 0.10));
  border-color: var(--color-accent, #7c8adb);
}

.sp-item__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-1, 4px);
}

.sp-item__name {
  font-weight: var(--font-weight-medium, 500);
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
  overflow-wrap: break-word;
  word-break: break-word;
}

/* Risk badge */
.sp-item__risk {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-xs, 0.75rem);
  font-weight: var(--font-weight-semibold, 600);
  font-family: var(--font-code, monospace);
  flex-shrink: 0;
}

.sp-item__risk--R0 { background: var(--color-success-soft, rgba(94, 184, 122, 0.12)); color: var(--color-success, #5eb87a); }
.sp-item__risk--R1 { background: var(--color-success-soft, rgba(94, 184, 122, 0.12)); color: var(--color-success, #5eb87a); }
.sp-item__risk--R2 { background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12)); color: var(--color-neutral, #7a7a84); }
.sp-item__risk--R3 { background: var(--color-warning-soft, rgba(212, 168, 67, 0.12)); color: var(--color-warning, #d4a843); }
.sp-item__risk--R4 { background: var(--color-error-soft, rgba(212, 86, 86, 0.12)); color: var(--color-error, #d45656); }
.sp-item__risk--R5 { background: var(--color-error-soft, rgba(212, 86, 86, 0.12)); color: var(--color-error, #d45656); }

/* Meta row */
.sp-item__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-1, 4px);
  font-size: var(--font-size-xs, 0.75rem);
}

.sp-item__status {
  color: var(--color-text-secondary, #a0a0aa);
}

.sp-item__status--available {
  color: var(--color-success, #5eb87a);
}

.sp-item__status--unavailable {
  color: var(--color-warning, #d4a843);
}

.sp-item__redaction {
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.625rem;
  background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12));
  color: var(--color-text-muted, #6a6a74);
}

/* Capability badges */
.sp-item__capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
}

.sp-cap-badge {
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.625rem;
  background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12));
  color: var(--color-text-muted, #6a6a74);
  overflow-wrap: break-word;
  word-break: break-word;
}

.sp-cap-badge--more {
  background: var(--color-accent-soft, rgba(124, 138, 219, 0.15));
  color: var(--color-accent, #7c8adb);
}

.sp-item__reason {
  display: block;
  margin-top: var(--space-1, 4px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
  font-style: italic;
  overflow-wrap: break-word;
  word-break: break-word;
}

/* Detail panel */
.sp-detail {
  width: 260px;
  flex-shrink: 0;
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  overflow-y: auto;
  max-height: 480px;
}

.sp-detail__name {
  font-size: var(--font-size-sm, 0.8125rem);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-primary, #e4e4e8);
  margin: 0 0 var(--space-3, 12px);
  overflow-wrap: break-word;
  word-break: break-word;
}

.sp-detail__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
  color: var(--color-text-muted, #6a6a74);
  font-size: var(--font-size-sm, 0.8125rem);
  text-align: center;
}

/* Fields section */
.sp-fields {
  margin-top: var(--space-3, 12px);
}

.sp-fields__heading {
  font-size: var(--font-size-xs, 0.75rem);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-muted, #6a6a74);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 var(--space-2, 8px);
  padding-bottom: var(--space-1, 4px);
  border-bottom: 1px solid var(--color-divider, rgba(255, 255, 255, 0.06));
}

.sp-fields__empty {
  margin-top: var(--space-3, 12px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
}

.sp-field-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.sp-field {
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.06));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface-bg, rgba(0, 0, 0, 0.15));
}

.sp-field__header {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-1, 4px);
}

.sp-field__name {
  font-weight: var(--font-weight-medium, 500);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-primary, #e4e4e8);
  font-family: var(--font-code, monospace);
  overflow-wrap: break-word;
  word-break: break-word;
}

.sp-field__type {
  font-size: 0.625rem;
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12));
  color: var(--color-text-secondary, #a0a0aa);
  font-family: var(--font-code, monospace);
}

.sp-field__required {
  font-size: 0.625rem;
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-error-soft, rgba(212, 86, 86, 0.12));
  color: var(--color-error, #d45656);
}

.sp-field__desc {
  margin: 0 0 var(--space-1, 4px);
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
  overflow-wrap: break-word;
  word-break: break-word;
}

.sp-field__enums {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-bottom: var(--space-1, 4px);
}

.sp-enum-badge {
  padding: 1px 4px;
  font-size: 0.5625rem;
  border-radius: var(--radius-sm, 4px);
  background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12));
  color: var(--color-text-muted, #6a6a74);
  font-family: var(--font-code, monospace);
  overflow-wrap: break-word;
  word-break: break-word;
}

.sp-enum-badge--more {
  background: var(--color-accent-soft, rgba(124, 138, 219, 0.15));
  color: var(--color-accent, #7c8adb);
}

.sp-field__default {
  display: inline-block;
  font-size: 0.625rem;
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-success-soft, rgba(94, 184, 122, 0.12));
  color: var(--color-success, #5eb87a);
}

.sp-field__constraints {
  display: block;
  margin-top: var(--space-1, 4px);
  font-size: 0.625rem;
  color: var(--color-text-muted, #6a6a74);
  font-style: italic;
  overflow-wrap: break-word;
  word-break: break-word;
}

/* Responsive */
@media (max-width: 768px) {
  .sp-content {
    flex-direction: column;
  }

  .sp-detail {
    width: 100%;
  }

  .sp-summary {
    flex-wrap: wrap;
  }

  .sp-summary-card {
    min-width: calc(33% - var(--space-2, 8px));
  }
}
</style>
