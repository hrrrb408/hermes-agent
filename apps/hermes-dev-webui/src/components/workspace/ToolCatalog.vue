<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useToolPolicyStore } from '@/stores/toolPolicy'
import {
  TOOL_CAPABILITIES,
  TOOL_POLICY_STATUSES,
  TOOL_RISK_LEVELS,
  RISK_LABELS,
  CAPABILITY_LABELS,
  POLICY_STATUS_LABELS,
} from '@/types/api/toolPolicyConstants'
import type {
  ToolRiskLevel,
  ToolCapability,
  ToolPolicyStatus,
  ToolCatalogSort,
} from '@/types/api/toolPolicy'

const store = useToolPolicyStore()

// Search debounce
const searchInput = ref(store.filters.q)
let searchTimer: number | null = null

function onSearchInput(value: string): void {
  searchInput.value = value
  if (searchTimer !== null) {
    window.clearTimeout(searchTimer)
    searchTimer = null
  }
  searchTimer = window.setTimeout(() => {
    store.setQuery(value)
    store.loadCatalog()
  }, 300)
}

function onRiskChange(value: string): void {
  store.setRisk((value || undefined) as ToolRiskLevel | undefined)
  store.loadCatalog()
}

function onCapabilityChange(value: string): void {
  store.setCapability((value || undefined) as ToolCapability | undefined)
  store.loadCatalog()
}

function onPolicyStatusChange(value: string): void {
  store.setPolicyStatus((value || undefined) as ToolPolicyStatus | undefined)
  store.loadCatalog()
}

function onSortChange(value: string): void {
  store.setSort(value as ToolCatalogSort)
  store.loadCatalog()
}

function onPageSizeChange(value: string): void {
  store.setPageSize(Number(value))
  store.loadCatalog()
}

function goToPage(page: number): void {
  store.setPage(page)
  store.loadCatalog()
}

function nextPage(): void {
  if (!store.catalog) return
  const next = store.catalog.page + 1
  if (next <= store.catalog.totalPages) {
    goToPage(next)
  }
}

function prevPage(): void {
  if (!store.catalog) return
  const prev = store.catalog.page - 1
  if (prev >= 1) {
    goToPage(prev)
  }
}

function clearFilters(): void {
  searchInput.value = ''
  store.setQuery('')
  store.setRisk(undefined)
  store.setCapability(undefined)
  store.setPolicyStatus(undefined)
  store.setSort('nameAsc')
  store.setPageSize(25)
  store.setPage(1)
  store.loadCatalog()
}

// Tool list keyboard navigation
function handleListKeyDown(event: KeyboardEvent): void {
  const items = store.catalogItems
  if (items.length === 0) return

  const currentName = store.selectedToolName
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
    store.selectTool(nextItem.canonicalName)
    document.getElementById(`tool-item-${nextItem.canonicalName}`)?.focus()
  }
}

onMounted(() => {
  if (store.catalogState === 'idle') {
    store.loadCatalog()
  }
})

onUnmounted(() => {
  if (searchTimer !== null) {
    window.clearTimeout(searchTimer)
    searchTimer = null
    searchTimer = null
  }
})
</script>

<template>
  <div class="tool-catalog">
    <!-- Filters -->
    <div class="tc-filters">
      <label for="tc-search" class="tc-sr-only">Search tools</label>
      <input
        id="tc-search"
        type="search"
        class="tc-filter-input"
        :value="searchInput"
        placeholder="Search tools…"
        maxlength="120"
        @input="onSearchInput(($event.target as HTMLInputElement).value)"
      />

      <label for="tc-risk" class="tc-sr-only">Filter by risk level</label>
      <select id="tc-risk" class="tc-filter-select" :value="store.filters.risk ?? ''" @change="onRiskChange(($event.target as HTMLSelectElement).value)">
        <option value="">All risks</option>
        <option v-for="level in TOOL_RISK_LEVELS" :key="level" :value="level">
          {{ level }} — {{ RISK_LABELS[level] }}
        </option>
      </select>

      <label for="tc-capability" class="tc-sr-only">Filter by capability</label>
      <select id="tc-capability" class="tc-filter-select" :value="store.filters.capability ?? ''" @change="onCapabilityChange(($event.target as HTMLSelectElement).value)">
        <option value="">All capabilities</option>
        <option v-for="cap in TOOL_CAPABILITIES" :key="cap" :value="cap">
          {{ CAPABILITY_LABELS[cap] }}
        </option>
      </select>

      <label for="tc-status" class="tc-sr-only">Filter by policy status</label>
      <select id="tc-status" class="tc-filter-select" :value="store.filters.policyStatus ?? ''" @change="onPolicyStatusChange(($event.target as HTMLSelectElement).value)">
        <option value="">All statuses</option>
        <option v-for="status in TOOL_POLICY_STATUSES" :key="status" :value="status">
          {{ POLICY_STATUS_LABELS[status] }}
        </option>
      </select>

      <label for="tc-sort" class="tc-sr-only">Sort order</label>
      <select id="tc-sort" class="tc-filter-select" :value="store.filters.sort" @change="onSortChange(($event.target as HTMLSelectElement).value)">
        <option value="nameAsc">Name A–Z</option>
        <option value="nameDesc">Name Z–A</option>
        <option value="riskAsc">Risk Low–High</option>
        <option value="riskDesc">Risk High–Low</option>
      </select>

      <label for="tc-pagesize" class="tc-sr-only">Page size</label>
      <select id="tc-pagesize" class="tc-filter-select" :value="store.filters.pageSize" @change="onPageSizeChange(($event.target as HTMLSelectElement).value)">
        <option value="10">10 per page</option>
        <option value="25">25 per page</option>
        <option value="50">50 per page</option>
        <option value="100">100 per page</option>
      </select>
    </div>

    <!-- Loading -->
    <div v-if="store.isCatalogLoading" class="panel-loading" aria-busy="true" aria-live="polite">
      Loading tool catalog…
    </div>

    <!-- Error -->
    <div v-else-if="store.catalogState === 'error'" class="panel-error" role="alert">
      <p>{{ store.catalogError }}</p>
      <button type="button" class="panel-retry-btn" aria-label="Retry loading tool catalog" @click="store.retryCatalog()">Retry catalog</button>
    </div>

    <!-- Empty -->
    <div v-else-if="store.isCatalogEmpty" class="panel-empty">
      <p v-if="store.catalog && store.catalog.filters && (store.catalog.filters.q || store.catalog.filters.risk || store.catalog.filters.capability || store.catalog.filters.policyStatus)">
        No tools match the current filters.
      </p>
      <p v-else>0 results</p>
      <button v-if="store.catalog?.filters?.q || store.catalog?.filters?.risk || store.catalog?.filters?.capability || store.catalog?.filters?.policyStatus" type="button" class="panel-retry-btn" @click="clearFilters">Clear filters</button>
    </div>

    <!-- Catalog content -->
    <template v-else-if="store.hasCatalogResults">
      <div class="tc-content" aria-live="polite">
        <!-- Tool list -->
        <div class="tc-list" role="listbox" aria-label="Tool catalog" @keydown="handleListKeyDown">
          <div
            v-for="item in store.catalogItems"
            :id="`tool-item-${item.canonicalName}`"
            :key="item.canonicalName"
            role="option"
            class="tc-item"
            :class="{ 'tc-item--selected': store.selectedToolName === item.canonicalName }"
            :aria-selected="store.selectedToolName === item.canonicalName"
            tabindex="0"
            @click="store.selectTool(item.canonicalName)"
            @keydown.enter="store.selectTool(item.canonicalName)"
            @keydown.space.prevent="store.selectTool(item.canonicalName)"
          >
            <div class="tc-item__header">
              <span class="tc-item__name">{{ item.canonicalName }}</span>
              <span class="tc-item__risk" :class="`tc-item__risk--${item.primaryRisk}`">{{ item.primaryRisk }}</span>
            </div>
            <div class="tc-item__meta">
              <span class="tc-item__status" :class="`tc-item__status--${item.policyStatus}`">
                {{ item.policyStatus === 'CANDIDATE' ? 'Candidate' : item.policyStatus === 'PERMANENTLY_DENIED' ? 'Permanently denied' : item.policyStatus === 'UNLISTED' ? 'Unlisted' : 'Statically allowed' }}
              </span>
              <span class="tc-item__allowed">Allowed: No</span>
            </div>
            <div class="tc-item__capabilities">
              <span v-for="cap in item.capabilities.slice(0, 3)" :key="cap" class="tc-cap-badge">{{ cap }}</span>
              <span v-if="item.capabilities.length > 3" class="tc-cap-badge tc-cap-badge--more">+{{ item.capabilities.length - 3 }}</span>
            </div>
            <span v-if="item.policyStatus === 'CANDIDATE'" class="tc-item__notice">Not enabled</span>
            <span v-else-if="item.policyStatus === 'UNLISTED'" class="tc-item__notice">Not enabled</span>
            <span v-else-if="item.policyStatus === 'PERMANENTLY_DENIED'" class="tc-item__notice">Permanently denied</span>
          </div>
        </div>

        <!-- Detail panel -->
        <div v-if="store.selectedTool" class="tc-detail" role="region" aria-label="Tool detail">
          <h4 class="tc-detail__name">{{ store.selectedTool.canonicalName }}</h4>
          <dl class="context-list">
            <div><dt>Primary Risk</dt><dd><span class="tc-item__risk" :class="`tc-item__risk--${store.selectedTool.primaryRisk}`">{{ store.selectedTool.primaryRisk }}</span> {{ RISK_LABELS[store.selectedTool.primaryRisk] }}</dd></div>
            <div><dt>Risk Rank</dt><dd>{{ store.selectedTool.riskRank }}</dd></div>
            <div><dt>Capabilities</dt><dd>{{ store.selectedTool.capabilities.join(', ') }}</dd></div>
            <div><dt>Policy Status</dt><dd>{{ store.selectedTool.policyStatus }}</dd></div>
            <div><dt>Permanently Denied</dt><dd>{{ store.selectedTool.permanentlyDenied ? 'Yes' : 'No' }}</dd></div>
            <div><dt>Candidate Allowlisted</dt><dd>{{ store.selectedTool.candidateAllowlisted ? 'Yes' : 'No' }}</dd></div>
            <div><dt>Statically Allowed</dt><dd>{{ store.selectedTool.staticallyAllowed ? 'Yes' : 'No' }}</dd></div>
            <div><dt>Allowed</dt><dd class="panel-flag panel-flag--disabled">No</dd></div>
            <div><dt>Reason Code</dt><dd>{{ store.selectedTool.reasonCode }}</dd></div>
            <div><dt>Source Module</dt><dd class="tc-detail__module">{{ store.selectedTool.sourceModule }}</dd></div>
            <div><dt>Rationale</dt><dd>{{ store.selectedTool.rationalePreview }}</dd></div>
            <div><dt>Execution Available</dt><dd class="panel-flag panel-flag--disabled">Unavailable</dd></div>
            <div><dt>Schema Preview Available</dt><dd class="panel-flag panel-flag--disabled">Unavailable</dd></div>
            <div><dt>Dry-Run Available</dt><dd class="panel-flag panel-flag--disabled">Unavailable</dd></div>
          </dl>
        </div>
        <div v-else class="tc-detail tc-detail--empty">
          <p class="tc-detail__placeholder">Select a tool to view details</p>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="store.catalog" class="tc-pagination" role="navigation" aria-label="Catalog pagination">
        <button
          type="button"
          class="tc-page-btn"
          :disabled="store.catalog.page <= 1"
          aria-label="Previous page"
          @click="prevPage"
        >
          ← Prev
        </button>
        <span class="tc-page-info">
          Page {{ store.catalog.page }} of {{ store.catalog.totalPages || 1 }}
          ({{ store.catalog.total }} tools)
        </span>
        <button
          type="button"
          class="tc-page-btn"
          :disabled="store.catalog.page >= store.catalog.totalPages"
          aria-label="Next page"
          @click="nextPage"
        >
          Next →
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tool-catalog {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

/* Screen reader only labels */
.tc-sr-only {
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

/* Filters */
.tc-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
}

.tc-filter-input,
.tc-filter-select {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  color: var(--color-text-primary, #e4e4e8);
  font-size: var(--font-size-xs, 0.75rem);
  font-family: inherit;
}

.tc-filter-input {
  flex: 1;
  min-width: 120px;
}

.tc-filter-input:focus,
.tc-filter-select:focus {
  outline: none;
  border-color: var(--color-focus-ring, var(--color-accent, #7c8adb));
  box-shadow: 0 0 0 1px var(--color-focus-ring, var(--color-accent, #7c8adb));
}

/* Content area: list + detail */
.tc-content {
  display: flex;
  gap: var(--space-3, 12px);
  min-height: 200px;
}

/* Tool list */
.tc-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
  overflow-y: auto;
  max-height: 480px;
}

.tc-item {
  padding: var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  cursor: pointer;
  transition: background var(--transition-fast, 120ms ease), border-color var(--transition-fast, 120ms ease);
}

.tc-item:hover {
  background: var(--color-hover-bg, rgba(255, 255, 255, 0.06));
}

.tc-item:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: -2px;
}

.tc-item--selected {
  background: var(--color-active-bg, rgba(255, 255, 255, 0.10));
  border-color: var(--color-accent, #7c8adb);
}

.tc-item__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-1, 4px);
}

.tc-item__name {
  font-weight: var(--font-weight-medium, 500);
  font-size: var(--font-size-sm, 0.8125rem);
  color: var(--color-text-primary, #e4e4e8);
  overflow-wrap: break-word;
  word-break: break-word;
}

/* Risk badge in list */
.tc-item__risk {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-xs, 0.75rem);
  font-weight: var(--font-weight-semibold, 600);
  font-family: var(--font-code, monospace);
  flex-shrink: 0;
}

.tc-item__risk--R0 { background: var(--color-success-soft, rgba(94, 184, 122, 0.12)); color: var(--color-success, #5eb87a); }
.tc-item__risk--R1 { background: var(--color-success-soft, rgba(94, 184, 122, 0.12)); color: var(--color-success, #5eb87a); }
.tc-item__risk--R2 { background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12)); color: var(--color-neutral, #7a7a84); }
.tc-item__risk--R3 { background: var(--color-warning-soft, rgba(212, 168, 67, 0.12)); color: var(--color-warning, #d4a843); }
.tc-item__risk--R4 { background: var(--color-error-soft, rgba(212, 86, 86, 0.12)); color: var(--color-error, #d45656); }
.tc-item__risk--R5 { background: var(--color-error-soft, rgba(212, 86, 86, 0.12)); color: var(--color-error, #d45656); }

/* Meta row */
.tc-item__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-1, 4px);
  font-size: var(--font-size-xs, 0.75rem);
}

.tc-item__status {
  color: var(--color-text-secondary, #a0a0aa);
}

.tc-item__allowed {
  color: var(--color-text-muted, #6a6a74);
}

.tc-item__notice {
  display: block;
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6a6a74);
  font-style: italic;
}

/* Capability badges */
.tc-item__capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
}

.tc-cap-badge {
  padding: 1px var(--space-1, 4px);
  border-radius: var(--radius-sm, 4px);
  font-size: 0.625rem;
  background: var(--color-neutral-soft, rgba(122, 122, 132, 0.12));
  color: var(--color-text-muted, #6a6a74);
  overflow-wrap: break-word;
  word-break: break-word;
}

.tc-cap-badge--more {
  background: var(--color-accent-soft, rgba(124, 138, 219, 0.15));
  color: var(--color-accent, #7c8adb);
}

/* Detail panel */
.tc-detail {
  width: 240px;
  flex-shrink: 0;
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: var(--color-elevated-bg, #2e2e38);
  overflow-y: auto;
  max-height: 480px;
}

.tc-detail--empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.tc-detail__name {
  font-size: var(--font-size-sm, 0.8125rem);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-primary, #e4e4e8);
  margin: 0 0 var(--space-3, 12px);
  overflow-wrap: break-word;
  word-break: break-word;
}

.tc-detail__module {
  font-family: var(--font-code, monospace);
  font-size: var(--font-size-xs, 0.75rem);
  overflow-wrap: break-word;
  word-break: break-word;
}

.tc-detail__placeholder {
  color: var(--color-text-muted, #6a6a74);
  font-size: var(--font-size-sm, 0.8125rem);
  text-align: center;
}

/* Pagination */
.tc-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3, 12px);
  padding: var(--space-2, 8px) 0;
  border-top: 1px solid var(--color-divider, rgba(255, 255, 255, 0.06));
}

.tc-page-btn {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.10));
  border-radius: var(--radius-sm, 4px);
  background: transparent;
  color: var(--color-text-secondary, #a0a0aa);
  font-size: var(--font-size-xs, 0.75rem);
  cursor: pointer;
  transition: color var(--transition-fast, 120ms ease);
}

.tc-page-btn:hover:not(:disabled) {
  color: var(--color-text-primary, #e4e4e8);
  border-color: var(--color-text-secondary, #a0a0aa);
}

.tc-page-btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, var(--color-accent, #7c8adb));
  outline-offset: 2px;
}

.tc-page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tc-page-info {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-secondary, #a0a0aa);
}

/* Responsive: stack on narrow screens */
@media (max-width: 768px) {
  .tc-content {
    flex-direction: column;
  }

  .tc-detail {
    width: 100%;
  }
}
</style>
